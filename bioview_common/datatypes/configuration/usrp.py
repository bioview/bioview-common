from bioview_common.constants import SUPPORTED_CONFIGURATION_TYPES

from ..devices import DeviceType
from .config import BaseConfig, merged_with_defaults, register_device_configuration


"""USRP device configuration.

Assumes two working channels per device, default data formats, an internal
clock reference, and unit-amplitude waveforms.
"""

BASE_USRP_CONFIG = {
    "tx_gain": [30, 30],
    "samp_rate": 1e6,
    "carrier_freq": 9e8,
    "rx_gain": [30, 30],
    "if_freq": [100e3, 110e3],
    "tx_amplitude": [1, 1],
    "tx_phase": [0.0, 0.0],
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
    "signal_scheme": "cw",
    "calibration": {
        "enabled": False,
        "shape": "triangle",
        # The three burst timings, all editable from the settings panel and
        # from a .bvi file: how many pulses one burst contains, how long each
        # of them lasts, and how often the burst repeats.
        "num_pulses": 5,
        "pulse_duration_s": 0.1,
        "packet_spacing_s": 1.0,
        # Only used when "pulse_duration_s" is absent or zero, which is how
        # the reference B210_2CHANNEL names the same quantity.
        "envelope_freq_hz": 10.0,
        "modulation_depth": 0.2,
        "envelope_offset": 0.0,
        "inject_channels": [0],
        "record_reference": True,
    },
    "dpic_balance": {
        "auto_on_start": False,
        "amp_target": 0.5,
        # Digital phase/amplitude changes land on the next Tx buffer, so the
        # settle is short; the real wait is for fresh Rx chunks.
        "settle_time_s": 0.02,
        "time_budget_s": 120.0,
        # Grid resolution. The coarse steps are the LabVIEW VI's 60 phase and
        # 20 amplitude points; the fine steps sweep +/- one coarse step.
        "coarse_phase_step_deg": 6.0,
        "coarse_amp_step": 0.05,
        "coarse_probe_amplitude": 0.1,
        "phase_step_deg": 0.2,
        "amp_step": 0.001,
        # Balance every radio in the group at once. The loops on different
        # USRPs are physically independent, so running them in series only
        # multiplied the wait.
        "parallel_devices": True,
    },
    "fmcw": {
        "chirp_start_hz": 50e3,
        "chirp_end_hz": 150e3,
        "chirp_duration_s": 0.001,
        "idle_time_s": 0.001,
    },
    "pulsed_doppler": {
        "pulse_width_s": 1e-5,
        "pri_s": 1e-3,
        "doppler_if_hz": 100e3,
    },
    # Per-Tx/Rx-pair quantities to stream. ["amplitude", "phase"] advertises
    # two rows per pair; see usrp_channel_map.STREAM_COMPONENTS.
    "components": ["amplitude"],
    "channel_map": None,
    "hardware": None,
}


class USRPConfiguration(BaseConfig):
    def __init__(self, config_dict: dict):
        self.cfg_type = SUPPORTED_CONFIGURATION_TYPES.USRP

        # Initialize using default values
        super().__init__(BASE_USRP_CONFIG)

        # Update with provided values. Merged, not replaced: a config that
        # names one calibration key keeps the defaults for the rest.
        for key, value in merged_with_defaults(BASE_USRP_CONFIG, config_dict).items():
            setattr(self, key, value)

        # Set device type. TODO: Remove
        self.device_type = DeviceType.USRP.value

        # Default absolute channel map for a single device with paired Tx/Rx;
        # multi-device MIMO must override it.
        self.absolute_channel_nums = self.tx_channels


register_device_configuration(
    DeviceType.USRP.value,
    SUPPORTED_CONFIGURATION_TYPES.USRP.value,
    USRPConfiguration,
)
