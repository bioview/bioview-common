import contextlib
import ipaddress
import socket
from importlib.metadata import version

from bioview_common.utils import get_ip, get_app_info, is_local_request

def test_ip(): 
    try:
        ipaddress.ip_address(get_ip()) 
    except ValueError as e: 
        raise AssertionError(f'Invalid IP address format: {e}')

def test_local_address():
    # Resolving the machine's own hostname can fail in sandboxed/CI environments
    # with no DNS; when it works the resolved address must be recognised as local.
    with contextlib.suppress(OSError):
        ip_addr = socket.gethostbyname(socket.gethostname())
        assert is_local_request(ip_addr), "Local request misidentified as remote"

    assert is_local_request('127.0.0.1'), "Local request misidentified as remote"
    assert is_local_request('0.0.0.0'), "Local request misidentified as remote"

    assert not is_local_request('8.8.8.8'), "Remote request misidentified as local"

def test_app_info():
    app_info = get_app_info()
    assert 'hostname' in app_info.keys(), "Hostname not found"

    assert 'name' in app_info.keys(), "Application name not found"
    assert app_info['name'] == 'BioView', f"Invalid application {app_info['name']}"

    assert 'version' in app_info.keys(), "Application version not found"
    assert app_info['version'] == version('bioview_common'), (
        f"Invalid application version {app_info['version']}"
    ) 