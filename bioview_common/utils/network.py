import contextlib
import ipaddress
import json
import os
import socket
import struct
import time
from typing import Any

from ..constants import APP_VERSION
from ..protocol import SUPPORTED_COMMANDS, SUPPORTED_RESPONSES, Command, Response
from .logs import log_print


def set_exclusive_bind(sock: socket.socket) -> None:
    """Configure a listener so bind() fails if another process serves the port."""
    if os.name == "nt":
        with contextlib.suppress(AttributeError, OSError):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    else:
        with contextlib.suppress(OSError):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        s.connect(("8.8.8.8", 80))
        IP = s.getsockname()[0]
    except Exception:
        IP = "127.0.0.1"
    finally:
        s.close()

    return IP


_LOCAL_ADDR_CACHE = {"addrs": None, "at": 0.0}
_LOCAL_ADDR_TTL = 30.0


def get_local_addresses() -> set:
    """Every IPv4 address belonging to this machine (loopback plus each NIC)."""
    now = time.time()
    if (
        _LOCAL_ADDR_CACHE["addrs"] is not None
        and now - _LOCAL_ADDR_CACHE["at"] < _LOCAL_ADDR_TTL
    ):
        return _LOCAL_ADDR_CACHE["addrs"]

    addrs = {"127.0.0.1", "0.0.0.0", "::1"}
    with contextlib.suppress(Exception):
        addrs.update(socket.gethostbyname_ex(socket.gethostname())[2])
    with contextlib.suppress(Exception):
        addrs.add(get_ip())

    _LOCAL_ADDR_CACHE["addrs"] = addrs
    _LOCAL_ADDR_CACHE["at"] = now
    return addrs


def is_local_request(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
        return (
            ip.is_loopback or ip.is_private or str(ip) in ["127.0.0.1", "::1", "0.0.0.0"]
        )
    except ValueError:
        return False


def get_hostname() -> str:
    try:
        hostname = socket.gethostname()
        if hostname and hostname != "localhost" and not hostname.startswith("ip-"):
            return hostname
    except Exception:
        pass
    return get_ip()


def get_app_info():
    return {
        "ip": get_ip(),
        "hostname": get_hostname(),
        "name": "BioView",
        "version": APP_VERSION,
    }


def recv_exactly(sock: socket.socket, num_bytes: int):
    """Read exactly num_bytes from the socket. Returns the bytes, or None if the"""
    chunks = []
    remaining = num_bytes
    while remaining > 0:
        chunk = sock.recv(min(remaining, 65536))
        if not chunk:
            return None
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def recv_message(sock: socket.socket, logger=None):
    """Receive one length-framed control message, or None if the peer closed."""
    header = recv_exactly(sock, 4)
    if not header:
        return None
    (length,) = struct.unpack("!I", header)
    if length == 0:
        return b""
    return recv_exactly(sock, length)


def _send_framed(sock: socket.socket, payload: bytes):
    """Length-prefix and send a control payload atomically."""
    sock.sendall(struct.pack("!I", len(payload)) + payload)


def send_command(
    sock: socket.socket,
    command: Command,
    params: dict = None,
    logger=None,
) -> bytes:
    if not isinstance(command, Command) or command.name not in SUPPORTED_COMMANDS:
        log_print(logger, "error", f"Invalid command: {command}")
        return None

    try:
        processed_params = {}
        if params:
            for k, v in params.items():
                if hasattr(v, "to_dict"):
                    processed_params[k] = v.to_dict()
                else:
                    processed_params[k] = v

        command_dict = {"type": command.name, "payload": processed_params}
        command_json = json.dumps(command_dict).encode("utf-8")
        _send_framed(sock, command_json)
    except Exception as e:
        log_print(logger, "error", f"Error occurred while sending command: {e}")
        return None

    try:
        return recv_message(sock, logger)
    except Exception as e:
        log_print(logger, "error", f"Error occurred while receiving response: {e}")
        return None


def send_response(
    sock: socket.socket, response: Response, params: dict = None, logger=None
):
    if not isinstance(response, Response) or response.name not in SUPPORTED_RESPONSES:
        log_print(logger, "error", f"Invalid response: {response}")
        return None

    try:
        processed_params = {}
        if params:
            for k, v in params.items():
                if hasattr(v, "to_dict"):
                    processed_params[k] = v.to_dict()
                else:
                    processed_params[k] = v

        response_dict = {"type": response.name, "payload": processed_params}
        response_json = json.dumps(response_dict).encode("utf-8")
        _send_framed(sock, response_json)
    except Exception as e:
        log_print(logger, "error", f"Error occurred while sending response: {e}")


def send_datachunk(sock: socket.socket, data: Any, meta: dict = None, logger=None):
    """Send a numpy chunk as"""
    if not hasattr(data, "tobytes"):
        log_print(
            logger,
            "error",
            f"send_datachunk expects a numpy array on the data path, got {type(data)}",
        )
        return

    try:
        raw_data = data.tobytes()
        header = {
            "shape": data.shape,
            "dtype": str(data.dtype),
            "timestamp": time.time(),
        }
        if meta:
            header.update(meta)

        header_bytes = json.dumps(header).encode("utf-8")
        header_len = len(header_bytes)
        total_len = 4 + header_len + len(raw_data)

        packet = struct.pack("!II", total_len, header_len) + header_bytes + raw_data
        sock.sendall(packet)
    except Exception as e:
        log_print(logger, "error", f"Error occurred while sending data: {e}")


def parse_and_validate_message(
    data: bytes, expected_type_list: list[str], logger=None
) -> tuple[str, dict]:
    if not data:
        return None, None

    try:
        message = json.loads(data.decode("utf-8"))
    except json.JSONDecodeError as e:
        log_print(logger, "error", f"Invalid JSON format: {e}")
        return None, None

    msg_type = message.get("type", None)
    if not msg_type or msg_type not in expected_type_list:
        log_print(logger, "error", f"Invalid message type: {msg_type}")
        return None, None

    payload = message.get("payload")
    if not isinstance(payload, dict):
        log_print(logger, "error", f"Payload must be a dict but got {type(payload)}")
        return None, None

    return msg_type, payload


def parse_and_validate_command(data: bytes, logger=None) -> tuple[str, dict]:
    return parse_and_validate_message(data, SUPPORTED_COMMANDS, logger)


def parse_and_validate_response(data: bytes, logger=None) -> tuple[str, dict]:
    return parse_and_validate_message(data, SUPPORTED_RESPONSES, logger)
