import socket 
import ipaddress

from typing import Dict, Any

from bioview_common.constants import APP_VERSION

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # Doesn't even have to be reachable
        s.connect(('8.8.8.8', 80)) # Google DNS servers
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1' # localhost
    finally:
        s.close()
    
    return IP

# Checks if connection request comes from a local origin or a remote origin: This is used for enabling local-only server mode.
def is_local_request(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
        return (ip.is_loopback or ip.is_private or str(ip) in ['127.0.0.1', '::1', '0.0.0.0'])
    except ValueError:
        # If it's not a valid IP, treat as external for safety
        return False

def get_hostname() -> str:
    # Attempt to get host-name
    try:
        hostname = socket.gethostname()
        # Validate hostname is not empty or generic
        if hostname and hostname != 'localhost' and not hostname.startswith('ip-'):
            return hostname
    except Exception:
        pass
    
    # Fallback to IP address
    ip_address = get_ip()
    return ip_address
    
def get_app_info(): 
    # Information to be broadcasted 
    return {
        "ip": get_ip(),
        "hostname": get_hostname(),
        "name": "BioView", 
        "version": APP_VERSION
    }

# Validation for received responses to ensure integrity
def validate_message_format(data: Dict[str, Any], expected_fields: list) -> bool:
    """Validate that message contains required fields and proper format"""
    if not isinstance(data, dict):
        return False
    
    for field in expected_fields:
        if field not in data:
            return False
    
    return True