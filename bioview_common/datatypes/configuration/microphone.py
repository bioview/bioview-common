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
    # Host input to open. ``"default"`` takes whatever PortAudio calls the
    # default input; anything else is matched against the discovered device
    # names (substring, case-insensitive) and then against their indices.
    "device": "default",
    # Frames per PortAudio callback. Sets capture latency and chunk size; 0
    # lets PortAudio choose, which on Windows/WASAPI is usually ~10 ms.
    "blocksize": 0,
    # Applied to the captured signal before it is emitted. A line-level input
    # at conversational distance is often 20-30 dB down on full scale.
    "gain": 1.0,
    "labels": None,
    # Present for parity with the other devices. Audio is emitted at full rate:
    # saving is fed from the display stream, so decimating for display would
    # decimate the recording too.
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

    #: Read from the nested ``hardware`` entry in preference to the top level,
    #: so a UI edit has to be written to both. Mirrors BiopacConfiguration.
    _HARDWARE_MIRRORED_PARAMS = (
        "samp_rate",
        "channels",
        "device",
        "blocksize",
        "gain",
        "labels",
    )

    def get_channel_count(self) -> int:
        """Number of captured channels.

        ``channels`` is a count here, not the enable mask BIOPAC uses: a sound
        card's channels are not individually selectable, so a list is accepted
        only so a config written against the BIOPAC shape still loads.
        """
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
