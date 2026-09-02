import ipaddress
from importlib.metadata import version

from bioview_common.utils import get_app_info, get_ip, is_local_request


def test_ip():
    try:
        ipaddress.ip_address(get_ip())
    except ValueError as e:
        raise AssertionError(f"Invalid IP address format: {e}") from e


def test_local_address():
    # is_local_request answers "is this peer on this machine or its LAN", which
    # is loopback plus the RFC1918 ranges. It deliberately does NOT mean "this
    # host": a machine on a routable network has a public address of its own,
    # so asserting that gethostbyname(gethostname()) is local fails there.
    assert is_local_request("127.0.0.1"), "Local request misidentified as remote"
    assert is_local_request("192.168.1.10"), "LAN request misidentified as remote"
    assert is_local_request("10.0.0.5"), "LAN request misidentified as remote"
    assert is_local_request("0.0.0.0"), "Local request misidentified as remote"

    assert not is_local_request("8.8.8.8"), "Remote request misidentified as local"
    assert not is_local_request("not-an-ip"), "Malformed address must not be local"


def test_app_info():
    app_info = get_app_info()
    assert "hostname" in app_info, "Hostname not found"

    assert "name" in app_info, "Application name not found"
    assert app_info["name"] == "BioView", f"Invalid application {app_info['name']}"

    assert "version" in app_info, "Application version not found"
    assert app_info["version"] == version(
        "bioview_common"
    ), f"Invalid application version {app_info['version']}"
