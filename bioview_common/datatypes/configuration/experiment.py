from bioview_common.constants import SUPPORTED_CONFIGURATION_TYPES

from .config import BaseConfig


BASE_EXPERIMENT_CONFIG = {
    "enable_save": False,
    "display_sources": [],
    "file_name": "",
    "save_dir": None,
    "data_sources": [],
    "timed_modes": [],
    "audio_output_device": None,
    "features": {
        "statistics_snr": True,
        "statistics_harmonics": True,
    },
}

FEATURE_DEFAULTS = dict(BASE_EXPERIMENT_CONFIG["features"])


class ExperimentConfiguration(BaseConfig):
    def __init__(self, config_dict: dict):
        super().__init__(BASE_EXPERIMENT_CONFIG)
        self.cfg_type = SUPPORTED_CONFIGURATION_TYPES.EXPERIMENT

        for key, value in config_dict.items():
            setattr(self, key, value)

    def get_feature(self, name: str, default: bool = None) -> bool:
        """Whether an optional readout is on for this session."""
        features = getattr(self, "features", None) or {}
        if name in features:
            return bool(features[name])
        if default is not None:
            return bool(default)
        return bool(FEATURE_DEFAULTS.get(name, False))

    def set_feature(self, name: str, enabled: bool):
        """Turn an optional readout on or off for the rest of the session."""
        features = dict(getattr(self, "features", None) or {})
        features[name] = bool(enabled)
        self.features = features

    def get_timed_modes(self):
        """Return the list of pre-defined timed-mode routine descriptors (raw"""
        modes = getattr(self, "timed_modes", []) or []
        return modes if isinstance(modes, list) else []
