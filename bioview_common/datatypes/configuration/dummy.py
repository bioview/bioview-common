from ..devices import DeviceType
from .config import BaseConfig

from bioview_common.constants import SUPPORTED_CONFIGURATION_TYPES

"""
Configuration for the virtual "dummy" device. It synthesizes a configurable
number of phase-shifted sine waves at a given sampling rate, which is enough to
exercise the whole client-server-display-save pipeline without any hardware.
"""

BASE_DUMMY_CONFIG = {
    "samp_rate": 500,        # Samples per second per channel
    "num_channels": 4,       # Number of phase-shifted sine waves to generate
    "signal_freq": 1.0,      # Frequency (Hz) of the generated sine waves
    "amplitude": 1.0,        # Peak amplitude of the generated sine waves
    "noise_std": 0.0,        # Std-dev of optional additive Gaussian noise
    "chunk_duration": 0.05,  # Seconds of data produced per emitted chunk
}


class DummyConfiguration(BaseConfig):
    def __init__(self, config_dict: dict):
        # Initialize using default values
        super().__init__(BASE_DUMMY_CONFIG)
        self.cfg_type = SUPPORTED_CONFIGURATION_TYPES.DUMMY

        # Update with provided values
        for key, value in (config_dict or {}).items():
            setattr(self, key, value)

        # Set device type so the server backend registry can route correctly
        self.device_type = DeviceType.DUMMY.value
