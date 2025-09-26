import ipaddress
import socket

from bioview_common.constants import APP_VERSION


SHARED_SECRET = 42  # TODO: REPLACE, this is only a placeholder for now


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


# Checks if connection request comes from a local origin or a remote origin
# This is used for enabling local-only server mode.
def is_local_request(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
        return (
            ip.is_loopback or ip.is_private or str(ip) in ["127.0.0.1", "::1", "0.0.0.0"]
        )
    except ValueError:
        # If it's not a valid IP, treat as external for safety
        return False


def get_hostname() -> str:
    # Attempt to get host-name
    try:
        hostname = socket.gethostname()
        # Validate hostname is not empty or generic
        if hostname and hostname != "localhost" and not hostname.startswith("ip-"):
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
        "version": APP_VERSION,
    }
