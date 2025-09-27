from enum import Enum


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


class ClientStatus(Enum):
    DEFAULT = "default"  # Nothing is going on
    SCANNING = "scanning_network"
    SERVER_CONNECTED = "server_connected"
    SERVER_DISCONNECTED = "server_disconnected"
    STREAMING = "streaming"
