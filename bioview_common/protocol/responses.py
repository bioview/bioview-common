from enum import Enum


class Response(Enum):
    SERVER_CHALLENGE = "server_challenge"
    AUTHENTICATION_SUCCESS = "authentication_success"

    SUCCESS = "success"

    ERROR = "error"
    WARNING = "warning"

    DEVICE_CONNECTING = "device_connecting"
    DEVICE_LIST = "device_list"
    DEVICE_CONFIG_UPDATED = "device_config_updated"


SUPPORTED_RESPONSES = [x.name for x in Response]
