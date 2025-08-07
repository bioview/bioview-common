from enum import Enum 

# Command from client to server 
class Command(Enum): 
    ## Server specific controls 
    PING_SERVER = 'ping_server' # Client - DONE, Server - Needs info TLC 
    DISCOVER_SERVERS = 'discover_servers' # PARTIAL - Needs server info TLC
    CONNECT_SERVER = 'connect_server' # Client - DONE, Server - Needs test
    DISCONNECT_SERVER = 'disconnect_server' # Client - DONE    

    ## Device specific controls
    DISCOVER_DEVICES = 'discover_devices'
    # Synchronous
    INITIALIZE_DEVICES = 'initialize_devices'
    CONNECT_DEVICES = 'connect_devices'
    DISCONNECT_DEVICES = 'disconnect_device'
    START_STREAMING = 'start_streaming'
    STOP_STREAMING = 'stop_streaming'
    # Individual 
    GET_DEVICE_STATUS = 'get_device_status'
    UPDATE_DEVICE_FIRMWARE = 'update_device_firmware'
    UPDATE_RUNNING_PARAMETER = 'update_running_parameter' # Only one parameter update at a time
 
SUPPORTED_COMMANDS = [x.name for x in Command]