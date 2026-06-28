import ipaddress
import socket
import json
import time
import struct
from typing import List, Dict, Any, Tuple

from ..protocol import (
    Command, 
    Response, 
    SUPPORTED_COMMANDS, 
    SUPPORTED_RESPONSES, 
    MAX_BUFFER_SIZE
)
from ..constants import APP_VERSION
from .logs import log_print

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # Doesn't even have to be reachable
        s.connect(("8.8.8.8", 80))  # Google DNS servers
        IP = s.getsockname()[0]
    except Exception:
        IP = "127.0.0.1"  # localhost
    finally:
        s.close()

    return IP

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
    """Read exactly num_bytes from the socket. Returns the bytes, or None if the
    connection was closed before all bytes were received. Any socket timeout or
    error is allowed to propagate to the caller so it can decide how to react."""
    chunks = []
    remaining = num_bytes
    while remaining > 0:
        chunk = sock.recv(min(remaining, 65536))
        if not chunk:
            return None
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)

def recv_message(sock: socket.socket, logger = None):
    """Receive a single length-framed control message and return its raw JSON
    bytes (or None if the connection was closed). Control messages are framed as
    [Length (4 bytes, big-endian)][JSON payload] so they survive TCP coalescing
    and fragmentation and are not limited to MAX_BUFFER_SIZE."""
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
    params: Dict = None, 
    logger = None, 
    buffer_size: int = MAX_BUFFER_SIZE
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
    sock: socket.socket, 
    response: Response, 
    params: Dict = None, 
    logger = None
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

        response_dict = {
            "type": response.name,
            "payload": processed_params
        }
        response_json = json.dumps(response_dict).encode("utf-8")
        _send_framed(sock, response_json)
    except Exception as e: 
        log_print(logger, "error", f"Error occurred while sending response: {e}")

def send_datachunk(sock: socket.socket, data: Any, meta: Dict = None, logger = None): 
    """
    Sends a numpy data chunk in a binary format:
    [Total Length (4 bytes)] [Header Length (4 bytes)] [JSON Header] [Raw Data]

    The streaming data path only ever carries numpy arrays. Optional metadata
    (e.g. the ordered list of data sources describing each row) is merged into
    the JSON header so the client can route rows without relying on global order.
    """
    if not hasattr(data, "tobytes"):
        log_print(
            logger, "error",
            f"send_datachunk expects a numpy array on the data path, got {type(data)}"
        )
        return

    try:
        raw_data = data.tobytes()
        header = {
            "shape": data.shape,
            "dtype": str(data.dtype),
            "timestamp": time.time()
        }
        if meta:
            header.update(meta)

        header_bytes = json.dumps(header).encode("utf-8")
        header_len = len(header_bytes)
        total_len = 4 + header_len + len(raw_data)
        
        # Pack everything
        packet = struct.pack("!II", total_len, header_len) + header_bytes + raw_data
        sock.sendall(packet)
    except Exception as e: 
        log_print(logger, "error", f"Error occurred while sending data: {e}")

def parse_and_validate_message(data: bytes, expected_type_list: List[str], logger = None) -> Tuple[str, Dict]:
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

def parse_and_validate_command(data: bytes, logger = None) -> Tuple[str, Dict]:
    return parse_and_validate_message(data, SUPPORTED_COMMANDS, logger)

def parse_and_validate_response(data: bytes, logger = None) -> Tuple[str, Dict]:
    return parse_and_validate_message(data, SUPPORTED_RESPONSES, logger)
