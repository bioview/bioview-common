from enum import Enum

# Response from server to client   
class Response(Enum): 
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"

SUPPORTED_RESPONSES = [x.name for x in Response]