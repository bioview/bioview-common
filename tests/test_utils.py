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
    hostname = socket.gethostname()
    ip_addr = socket.gethostbyname(hostname)

    assert is_local_request(ip_addr), "Local request misidentified as remote"
    assert is_local_request('127.0.0.1'), "Local request misidentified as remote"
    assert is_local_request('0.0.0.0'), "Local request misidentified as remote"

    assert not is_local_request('8.8.8.8'), "Remote request misidentified as local"

def test_app_info(): 
    app_info = get_app_info() 
    assert 'hostname' in app_info.keys(), "Hostname not found"
    
    assert 'app_name' in app_info.keys(), "Application name not found"    
    assert app_info['app_name'] == 'BioView', f"Invalid application {app_info['app_name']}"
    
    assert 'app_version' in app_info.keys(), "Application version not found"    
    assert app_info['app_version'] == version('bioview_common'), f"Invalid application version {app_info['app_version']}"

def test_validate_message_format(): 
    pass 