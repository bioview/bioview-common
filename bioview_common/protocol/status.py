from enum import Enum, IntEnum


class DeviceStatus(Enum):
    NOINIT = "Not Initialized"
    AVAILABLE = "Available"
    UNAVAILABLE = "Unavailable"
    CONNECTING = "Connecting"
    CONNECTED = "Connected"
    STREAMING = "Streaming"
    DISCONNECTED = "Disconnected"


class ClientStatus(IntEnum):
    """Ordered by connectivity, so connection checks can compare levels."""

    DEFAULT = -1
    SERVER_DISCONNECTED = 0
    SCANNING = 1
    SERVER_CONNECTED = 2
    DEVICES_DISCOVERED = 3
    DEVICES_CONNECTED = 4
    STREAMING = 5
