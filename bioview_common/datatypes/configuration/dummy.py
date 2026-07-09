from ..devices import DeviceType
from .config import BaseConfig

from bioview_common.constants import SUPPORTED_CONFIGURATION_TYPES

"""
Configuration for the virtual "dummy" device.

Legacy mode synthesizes phase-shifted sine waves. When ``hardware`` and
``channel_map`` are provided, the dummy backend runs the same CW / calibration /
DPIC pipeline as USRP using a virtual MIMO channel model.
"""

BASE_DUMMY_CONFIG = {
    "samp_rate": 500,
    "num_channels": 4,
    "signal_freq": 1.0,
    "amplitude": 1.0,
    "noise_std": 0.0,
    "chunk_duration": 0.05,
    # RF simulation (optional — enables MIMO / DPIC / calibration testing)
    "signal_scheme": "cw",
    "tx_gain": [30, 30],
    "tx_amplitude": [1, 1],
    "tx_phase": [0.0, 0.0],
    "if_freq": [100e3, 110e3],
    "if_filter_bw": 5e3,
    "save_ds": 100,
    "disp_ds": 10,
    "calibration": {
        "enabled": False,
        "shape": "triangle",
        "num_pulses": 5,
        "pulse_duration_s": 0.1,
        "packet_spacing_s": 1.0,
        "envelope_freq_hz": 10.0,
        "modulation_depth": 0.2,
        "envelope_offset": 0.0,
        "inject_channels": [0],
        "record_reference": True,
    },
    "dpic_balance": {
        "auto_on_start": False,
        "amp_target": 0.5,
        "phase_step_deg": 1.0,
        "amp_step": 0.05,
        "settle_time_s": 0.1,
    },
    "channel_map": None,
    "hardware": None,
    "rf_simulation": {
        "cross_coupling": 0.08,
        "on_axis_gain": 0.4,
        "direct_leak": 0.4,
        "dpic_coupling": 0.4,
    },
}


class DummyConfiguration(BaseConfig):
    def __init__(self, config_dict: dict):
        super().__init__(BASE_DUMMY_CONFIG)
        self.cfg_type = SUPPORTED_CONFIGURATION_TYPES.DUMMY

        for key, value in (config_dict or {}).items():
            setattr(self, key, value)

        self.device_type = DeviceType.DUMMY.value
