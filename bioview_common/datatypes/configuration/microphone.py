from bioview_common.constants import SUPPORTED_CONFIGURATION_TYPES

from ..devices import DeviceType
from .config import BaseConfig, register_device_configuration


"""Host audio-input configuration.

The microphone is an ordinary streaming device: it emits one row per captured
channel at ``samp_rate`` and those rows travel the same display/save path as
BIOPAC and USRP rows, so speech lands in the ``.bvr`` sample-aligned with
everything else recorded in the same session.

``samp_rate`` therefore doubles as the recorded rate. Speech is intelligible
well below CD rates and every extra kilohertz is a row in the recording and a
point on the plot, so the default is 16 kHz rather than the 44.1/48 kHz a
sound card offers by default.
"""

BASE_MICROPHONE_CONFIG = {
    "samp_rate": 16000,
    "channels": 1,
    "device": "default",
    "blocksize": 0,
    "gain": 1.0,
    "labels": None,
    "disp_ds": 1,
    "save_ds": 1,
    "hardware": None,
    "channel_map": None,
}


class MicrophoneConfiguration(BaseConfig):
    def __init__(self, config_dict: dict):
        super().__init__(BASE_MICROPHONE_CONFIG)
        self.cfg_type = SUPPORTED_CONFIGURATION_TYPES.MICROPHONE

        for key, value in (config_dict or {}).items():
            setattr(self, key, value)

        self.device_type = DeviceType.MICROPHONE.value
        self.absolute_channel_nums = list(range(int(self.get_channel_count())))

    _HARDWARE_MIRRORED_PARAMS = (
        "samp_rate",
        "channels",
        "device",
        "blocksize",
        "gain",
        "labels",
    )

    def get_channel_count(self) -> int:
        """Number of captured channels."""
        raw = getattr(self, "channels", 1)
        if isinstance(raw, list | tuple):
            enabled = sum(1 for entry in raw if entry)
            return max(1, enabled)
        try:
            return max(1, int(raw))
        except (TypeError, ValueError):
            return 1

    def set_param(self, param, value):
        super().set_param(param, value)

        if param == "channels":
            self.absolute_channel_nums = list(range(int(self.get_channel_count())))

        if param not in self._HARDWARE_MIRRORED_PARAMS:
            return

        hardware = getattr(self, "hardware", None)
        if not isinstance(hardware, dict):
            return
        for entry in hardware.values():
            if isinstance(entry, dict):
                entry[param] = value


register_device_configuration(
    DeviceType.MICROPHONE.value,
    SUPPORTED_CONFIGURATION_TYPES.MICROPHONE.value,
    MicrophoneConfiguration,
)
