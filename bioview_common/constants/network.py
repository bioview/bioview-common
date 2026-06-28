import os

CONTROL_PORT = 8998
DATA_PORT = 8999

AUTH_TIMEOUT = 5 # 5 seconds default timeout for authorization since it should be fairly quick
RESPONSE_TIMEOUT = 30 # Higher time for a response since there may be more processing involved (such as connecting to a device)

# Shared secret used for the challenge/response handshake between client and server.
# It can be overridden by setting the BIOVIEW_SHARED_SECRET environment variable on
# both machines. The default below allows localhost / trusted-LAN usage out of the box.
SHARED_SECRET = os.environ.get("BIOVIEW_SHARED_SECRET", "bioview-default-shared-secret")