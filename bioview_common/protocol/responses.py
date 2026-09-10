from enum import Enum


# Response from server to client. Only the member *name* travels on the wire
# (see SUPPORTED_RESPONSES / send_response), so this list is the vocabulary a
# client is willing to parse -- keep it to what is actually sent.
class Response(Enum):
    # Client-Server connection responses
    SERVER_CHALLENGE = "server_challenge"
    AUTHENTICATION_SUCCESS = "authentication_success"

    # Command execution responses
    SUCCESS = "success"

    # Logger responses
    ERROR = "error"
    WARNING = "warning"

    # Device responses
    DEVICE_CONNECTING = "device_connecting"
    DEVICE_LIST = "device_list"
    DEVICE_CONFIG_UPDATED = "device_config_updated"


SUPPORTED_RESPONSES = [x.name for x in Response]
