import os


CONTROL_PORT = 8998
DATA_PORT = 8999

AUTH_TIMEOUT = (
    5  # 5 seconds default timeout for authorization since it should be fairly quick
)
# Higher time for a response since there may be more processing involved
# (such as connecting to a device)
RESPONSE_TIMEOUT = 30

# Device discovery / initialization (UHD can be very slow)
DISCOVER_TIMEOUT = 120
INIT_TIMEOUT_USRP = 300
INIT_TIMEOUT_DEFAULT = 120
DEVICE_OP_POLL_INTERVAL = 2.0
DEVICE_OP_COMMAND_TIMEOUT = 30
DISCOVERY_CACHE_TTL = 60

# Outer bound on a Start/Stop round trip. The server starts devices in sequence
# and bounds each one itself (see START_STREAMING_TIMEOUT in the server's
# Backend), so it answers -- with an error naming the device -- long before this
# fires. This is the backstop for a server that has stopped answering at all,
# not the budget for a slow device, so it only has to clear the server's own
# worst case across a handful of device groups.
STREAMING_COMMAND_TIMEOUT = 45

# Challenge/response secret; override with BIOVIEW_SHARED_SECRET on both
# machines. The default suits localhost and trusted-LAN use.
SHARED_SECRET = os.environ.get("BIOVIEW_SHARED_SECRET", "bioview-default-shared-secret")
