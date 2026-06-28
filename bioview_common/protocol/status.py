from enum import Enum, IntEnum


class DeviceStatus(Enum):
    NOINIT = "Not Initialized"
    AVAILABLE = "Available"
    UNAVAILABLE = "Unavailable"
    CONNECTING = "Connecting"
    CONNECTED = "Connected"
    STREAMING = "Streaming"
    DISCONNECTED = "Disconnected"


class ServerStatus(IntEnum):
    SHUTDOWN_SERVER = -2  # Signal server to shutdown
    RESET_SERVER = -1 # Signal server reset
    CLIENT_DISCONNECTED = 0
    CLIENT_CONNECTED = 1
    DEVICES_DISCONNECTED = 2
    DEVICES_CONNECTED = 3
    STREAMING = 4
    

class ClientStatus(IntEnum):
    """
    Level numbers are assigned on the basis of connectivity.
    This helps make logic for connection checks easier.
    """

    DEFAULT = -1
    SERVER_DISCONNECTED = 0
    SCANNING = 1
    SERVER_CONNECTED = 2
    DEVICES_DISCOVERED = 3
    DEVICES_CONNECTED = 4
    STREAMING = 5
