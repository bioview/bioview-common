from enum import Enum


# Response from server to client
class Response(Enum):
    # Client-Server connection responses
    CONNECTION_ACCEPTED = "connection_accepted"
    CONNECTION_REFUSED = "connection_refused"
    SERVER_CHALLENGE = "server_challenge"
    AUTHENTICATION_SUCCESS = "authentication_success"
    AUTHENTICATION_FAILURE = "authentication_failure"

    # Command execution responses
    SUCCESS = "success"

    # Logger responses
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"

    # Device responses
    DEVICE_STATUS_CHANGED = "device_status_changed"
    # More fine-grained device lifecycle responses
    DEVICE_DISCOVERY_COMPLETED = "device_discovery_completed"
    DEVICE_CONNECTING = "device_connecting"
    DEVICE_CONNECTED = "device_connected"
    DEVICE_DISCONNECTED = "device_disconnected"


SUPPORTED_RESPONSES = [x.name for x in Response]
