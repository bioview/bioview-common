from ..devices import DeviceType
from .config import BaseConfig


# Assuming an MP36R device
BASE_BIOPAC_CONFIG = {
    "channels": [1, 1, 1, 1],
    "samp_rate": 1000,
    "model": "MP36",
    "mpdev_path": None,
}

MODEL_CODE_MAPPING = {"MP36": 103}
from bioview_common.constants import SUPPORTED_CONFIGURATION_TYPES

class BiopacConfiguration(BaseConfig):
    def __init__(self, config_dict: dict):
        # Initialize using default values
        super().__init__(BASE_BIOPAC_CONFIG)
        self.cfg_type = SUPPORTED_CONFIGURATION_TYPES.BIOPAC
        
        # Update with provided values
        for key, value in config_dict.items():
            setattr(self, key, value)

        # Set device type
        self.device_code = MODEL_CODE_MAPPING[self.model]
        self.device_type = DeviceType.BIOPAC
        self.absolute_channel_nums = self.channels

    def get_channels(self):
        # Since the API expects 16 channels, ensure we always pad
        # to return in the appropriate format
        return self.channels + [0] * (16 - len(self.channels))
