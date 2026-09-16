from bioview_common.constants import SUPPORTED_CONFIGURATION_TYPES

from ..devices import DeviceType
from .config import BaseConfig, register_device_configuration


BASE_BIOPAC_CONFIG = {
    "channels": [1, 1, 1, 1],
    "samp_rate": 1000,
    "model": "MP36",
    "mpdev_path": None,
    "connection_type": 10,
    "port": "auto",
    "disp_ds": 10,
    "save_ds": 1,
    "hardware": None,
    "channel_map": None,
}

MODEL_CODE_MAPPING = {"MP36": 103, "MP150": 150, "MP160": 160}


class BiopacConfiguration(BaseConfig):
    def __init__(self, config_dict: dict):
        super().__init__(BASE_BIOPAC_CONFIG)
        self.cfg_type = SUPPORTED_CONFIGURATION_TYPES.BIOPAC

        for key, value in (config_dict or {}).items():
            setattr(self, key, value)

        model = getattr(self, "model", "MP36")
        self.device_code = MODEL_CODE_MAPPING.get(model, MODEL_CODE_MAPPING["MP36"])
        self.device_type = DeviceType.BIOPAC.value
        self.absolute_channel_nums = self.channels

    _HARDWARE_MIRRORED_PARAMS = (
        "channels",
        "samp_rate",
        "model",
        "connection_type",
        "port",
        "labels",
    )

    def set_param(self, param, value):
        super().set_param(param, value)

        if param == "channels":
            self.absolute_channel_nums = value
        if param == "model":
            self.device_code = MODEL_CODE_MAPPING.get(value, MODEL_CODE_MAPPING["MP36"])

        if param not in self._HARDWARE_MIRRORED_PARAMS:
            return

        hardware = getattr(self, "hardware", None)
        if not isinstance(hardware, dict):
            return
        for entry in hardware.values():
            if isinstance(entry, dict):
                entry[param] = value

    def get_channels(self):
        channels = list(self.channels)
        return channels + [0] * (16 - len(channels))


register_device_configuration(
    DeviceType.BIOPAC.value,
    SUPPORTED_CONFIGURATION_TYPES.BIOPAC.value,
    BiopacConfiguration,
)
