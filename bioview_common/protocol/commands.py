from enum import Enum


class Command(Enum):
    AUTHENTICATE_CLIENT = "authenticate_client"
    DISCOVER_SERVERS = "discover_servers"
    CONNECT_SERVER = "connect_server"
    DISCONNECT_SERVER = "disconnect_server"
    SHUTDOWN_SERVER = "shutdown_server"

    DISCOVER_DEVICES = "discover_devices"
    LIST_DEVICES = "list_devices"
    SET_DEVICE_CONFIG = "set_device_config"

    INITIALIZE_DEVICES = "initialize_devices"
    DISCONNECT_DEVICES = "disconnect_devices"
    START_STREAMING = "start_streaming"
    STOP_STREAMING = "stop_streaming"

    GET_DEVICE_STATUS = "get_device_status"
    UPDATE_RUNNING_PARAMETER = "update_running_parameter"
    RUN_DPIC_BALANCE = "run_dpic_balance"
    MARK_EVENT = "mark_event"


class IPCCommand(Enum):
    CONNECT_DEVICES = "connect_devices"
    START_STREAMING = "start_streaming"
    STOP_STREAMING = "stop_streaming"
    DISCONNECT_DEVICES = "disconnect_devices"
    UPDATE_RUNNING_PARAMETER = "update_running_parameter"
    RUN_DPIC_BALANCE = "run_dpic_balance"
    SHUTDOWN = "shutdown"


SUPPORTED_COMMANDS = [x.name for x in Command]
