# Import checks 
from bioview_common.constants import CONTROL_PORT, DATA_PORT, AUTH_TIMEOUT, RESPONSE_TIMEOUT, APP_VERSION

# Validate constant types 
assert isinstance(CONTROL_PORT, int), "CONTROL_PORT must be an integer"
assert isinstance(DATA_PORT, int), "CONTROL_PORT must be an integer"

assert isinstance(AUTH_TIMEOUT, int) or isinstance(AUTH_TIMEOUT, float), "AUTH_TIMEOUT must be numeric"
assert isinstance(RESPONSE_TIMEOUT, int) or isinstance(AUTH_TIMEOUT, float), "AUTH_TIMEOUT must be numeric"

# Validate app version
from importlib.metadata import version
assert APP_VERSION == version('bioview_common'), f"APP_VERSION {APP_VERSION} does not match installed version: {version('bioview_common')}"