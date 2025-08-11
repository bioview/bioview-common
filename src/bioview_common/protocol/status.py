from enum import Enum, auto

class DeviceStatus(Enum): 
    NOINIT = "Not Initialized"
    CONNECTING = "Connecting"
    CONNECTED = "Connected" # Not streaming
    STREAMING = "Streaming"
    DISCONNECTED = "Not Connected"

class ServerStatus(Enum): 
    DEFAULT = auto      # Nothing is going on
    CLIENT_CONNECTED = auto
    CLIENT_DISCONNECTED = auto
    DEVICES_CONNECTED = auto
    DEVICES_DISCONNECTED = auto 
    STREAMING = auto

class ClientStatus(Enum):
    DEFAULT = auto      # Nothing is going on
    SCANNING = auto
    SERVER_CONNECTED = auto
    SERVER_DISCONNECTED = auto
    STREAMING = auto