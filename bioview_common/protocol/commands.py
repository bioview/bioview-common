from enum import Enum 

# Wire commands: sent from client to server over the control socket. Only the
# member *name* travels on the wire (see SUPPORTED_COMMANDS / send_command).
class Command(Enum): 
    # Server specific controls 
    AUTHENTICATE_CLIENT = "authenticate_client"
    PING_SERVER = 'ping_server' # Client - DONE, Server - Needs info TLC 
    DISCOVER_SERVERS = 'discover_servers' # PARTIAL - Needs server info TLC
    CONNECT_SERVER = 'connect_server' # Client - DONE, Server - Needs test
    DISCONNECT_SERVER = 'disconnect_server' # Client - DONE    

    # Device specific controls
    DISCOVER_DEVICES = 'discover_devices'
    
    # Synchronous
    INITIALIZE_DEVICES = 'initialize_devices'
    DISCONNECT_DEVICES = 'disconnect_devices'
    START_STREAMING = 'start_streaming'
    STOP_STREAMING = 'stop_streaming'
    
    # Individual 
    GET_DEVICE_STATUS = 'get_device_status'
    UPDATE_DEVICE_FIRMWARE = 'update_device_firmware'
    UPDATE_RUNNING_PARAMETER = 'update_running_parameter' # Only one parameter update at a time
    RUN_DPIC_BALANCE = 'run_dpic_balance'


# Internal IPC commands: sent from the server's main process to a device
# backend subprocess over a multiprocessing.Queue. These never touch the wire.
class IPCCommand(Enum):
    CONNECT_DEVICES = 'connect_devices'
    START_STREAMING = 'start_streaming'
    STOP_STREAMING = 'stop_streaming'
    DISCONNECT_DEVICES = 'disconnect_devices'
    UPDATE_RUNNING_PARAMETER = 'update_running_parameter'
    RUN_DPIC_BALANCE = 'run_dpic_balance'
    SHUTDOWN = 'shutdown'

SUPPORTED_COMMANDS = [x.name for x in Command]