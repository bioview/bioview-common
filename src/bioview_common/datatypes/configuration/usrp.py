from ..devices import DeviceType
from .config import Configuration


"""
We make some general assumptions, specifically -
* Each device has two working channels
* Each device uses the default data formats
* Each device uses internal timing reference and clock
* Each device sends waveforms of amplitude 1
"""

BASE_USRP_CONFIG = {
    "tx_amplitude": [1, 1],
    "rx_channels": [0, 1],
    "tx_channels": [0, 1],
    "rx_subdev": "A:A A:B",
    "tx_subdev": "A:A A:B",
    "cpu_format": "fc32",
    "wire_format": "sc16",
    "clock": "internal",
    "pps": "internal",
    "if_filter_bw": 5e3,
    "save_ds": 100,
    "disp_ds": 10,
}


class USRPConfiguration(Configuration):
    def __init__(self, config_dict: dict):
        # Initialize using default values
        super().__init__(BASE_USRP_CONFIG)

        # Update with provided values
        for key, value in config_dict.items():
            setattr(self, key, value)

        # Set device type
        self.device_type = DeviceType.USRP.value

        # Set-up default absolute channel mapping, assuming single device.
        # This assumes that Tx/Rx are always used in pairs
        # This must be updated if using MIMO with multiple USRPs
        self.absolute_channel_nums = self.tx_channels

    def get_filter_bw(self):
        if not isinstance(self.if_filter_bw, (list, tuple)):
            return [self.if_filter_bw for _ in self.tx_channels]
        elif len(self.if_filter_bw) == len(self.tx_channels):
            return self.if_filter_bw
