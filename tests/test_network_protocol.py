"""Protocol-level tests for the wire framing, command/response round-trips, the
authentication handshake, and numpy data-chunk framing used between the BioView
client and server. These run entirely in-process over a socketpair (no server or
hardware required)."""
import socket
import struct
import threading

import numpy as np
import pytest

from bioview_common import (
    Command,
    Response,
    generate_challenge,
    get_challenge_response,
    parse_and_validate_command,
    parse_and_validate_response,
    recv_message,
    send_command,
    send_response,
    send_datachunk,
    validate_token,
)


@pytest.fixture
def sockpair():
    a, b = socket.socketpair()
    yield a, b
    a.close()
    b.close()


def test_command_response_roundtrip(sockpair):
    client, server = sockpair

    # Server side: read the command, reply with a SUCCESS response.
    def server_side():
        raw = recv_message(server)
        cmd_type, payload = parse_and_validate_command(raw)
        assert cmd_type == Command.START_STREAMING.name
        assert payload == {"foo": "bar"}
        send_response(server, Response.SUCCESS, {"message": "ok"})

    t = threading.Thread(target=server_side)
    t.start()

    # send_command sends the framed command and returns the framed response bytes
    raw_resp = send_command(client, Command.START_STREAMING, {"foo": "bar"})
    t.join(timeout=5)

    resp_type, resp_payload = parse_and_validate_response(raw_resp)
    assert resp_type == Response.SUCCESS.name
    assert resp_payload["message"] == "ok"


def test_invalid_command_is_rejected():
    # A non-Command object is not sent on the wire.
    a, b = socket.socketpair()
    try:
        assert send_command(a, "NOT_A_COMMAND", {}) is None
    finally:
        a.close()
        b.close()


def test_auth_challenge_response_matches():
    challenge = generate_challenge()
    token = get_challenge_response(challenge)
    assert validate_token(challenge, token)
    assert not validate_token(challenge, "not-the-right-token")


def test_auth_handshake_over_socket(sockpair):
    """Full CONNECT_SERVER -> SERVER_CHALLENGE -> AUTHENTICATE_CLIENT flow."""
    client, server = sockpair
    result = {}

    def server_side():
        raw = recv_message(server)
        cmd, _ = parse_and_validate_command(raw)
        assert cmd == Command.CONNECT_SERVER.name
        challenge = generate_challenge()
        send_response(server, Response.SERVER_CHALLENGE, {"challenge": challenge})

        raw = recv_message(server)
        cmd, payload = parse_and_validate_command(raw)
        assert cmd == Command.AUTHENTICATE_CLIENT.name
        result["ok"] = validate_token(challenge, payload["token"])
        send_response(
            server,
            Response.AUTHENTICATION_SUCCESS if result["ok"] else Response.ERROR,
            {},
        )

    t = threading.Thread(target=server_side)
    t.start()

    raw = send_command(client, Command.CONNECT_SERVER, {"client_info": {}})
    resp_type, payload = parse_and_validate_response(raw)
    assert resp_type == Response.SERVER_CHALLENGE.name

    token = get_challenge_response(payload["challenge"])
    raw = send_command(client, Command.AUTHENTICATE_CLIENT, {"token": token})
    resp_type, _ = parse_and_validate_response(raw)

    t.join(timeout=5)
    assert result.get("ok") is True
    assert resp_type == Response.AUTHENTICATION_SUCCESS.name


def test_datachunk_framing_roundtrip(sockpair):
    """A numpy chunk sent with send_datachunk can be reconstructed on the other
    end using the same [total][header_len][header][raw] framing the client uses."""
    client, server = sockpair
    data = np.arange(12, dtype=np.float32).reshape(3, 4)
    sources = [{"group_id": "DummyDevice", "channel": i} for i in range(3)]

    send_datachunk(client, data, meta={"sources": sources})

    # Read [total_len (4)][header_len (4)]
    prefix = _recv_exactly(server, 8)
    total_len, header_len = struct.unpack("!II", prefix)
    body = _recv_exactly(server, total_len - 4)  # total_len counts header_len(4)+header+raw
    import json

    header = json.loads(body[:header_len].decode("utf-8"))
    raw = body[header_len:]

    assert tuple(header["shape"]) == (3, 4)
    assert header["dtype"] == "float32"
    assert header["sources"] == sources
    recovered = np.frombuffer(raw, dtype=np.float32).reshape(header["shape"])
    assert np.array_equal(recovered, data)


def _recv_exactly(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            break
        buf += chunk
    return buf
