from enum import Enum

# Response from server to client   
class Response(Enum): 
    SUCCESS = "success"
    # Logger responses
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"
    # Device responses
    DEVICE_STATUS_CHANGED = "device_status_changed"

SUPPORTED_RESPONSES = [x.name for x in Response]