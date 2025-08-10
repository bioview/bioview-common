from enum import Enum

# Response from server to client   
class Response(Enum): 
    # Client-Server connection responses 
    CONNECTION_ACCEPTED = "connection_accepted"
    CONNECTION_REFUSED = "connection_refused"
    AUTHENTICATION_SUCCESS = "authentication_success"

    # Command execution responses
    SUCCESS = "success"
    
    # Logger responses
    ERROR = "error" 
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"
    
    # Device responses
    DEVICE_STATUS_CHANGED = "device_status_changed"

SUPPORTED_RESPONSES = [x.name for x in Response] 