from enum import Enum, IntEnum


class DeviceStatus(Enum):
    NOINIT = "Not Initialized"
    AVAILABLE = "Available"
    UNAVAILABLE = "Unavailable"
    CONNECTING = "Connecting"
    CONNECTED = "Connected"
    STREAMING = "Streaming"
    DISCONNECTED = "Disconnected"


class ServerStatus(Enum):
    DEFAULT = "default"  # Nothing is going on
    CLIENT_CONNECTED = "client_connected"
    CLIENT_DISCONNECTED = "client_disconnected"
    DEVICES_CONNECTED = "devices_connected"
    DEVICES_DISCONNECTED = "devices_disconnected"
    STREAMING = "streaming"


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
