from enum import Enum

# Response from server to client   
class Response(Enum): 
    SUCCESS = "success"
    ERROR = "error"
    INFO = "info"
    DEBUG = "debug"

SUPPORTED_COMMANDS = [x.name for x in Response]