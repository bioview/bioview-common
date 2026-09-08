from bioview_common.constants import SUPPORTED_CONFIGURATION_TYPES

from .config import BaseConfig


# Free-running by default, plus any routines under "timed_modes".
# Schema: bioview-docs/reference/configuration.md
BASE_EXPERIMENT_CONFIG = {
    "enable_save": False,
    "display_sources": [],
    "file_name": "",
    "save_dir": None,
    "data_sources": [],
    "timed_modes": [],
}


class ExperimentConfiguration(BaseConfig):
    def __init__(self, config_dict: dict):
        # Initialize using default values
        super().__init__(BASE_EXPERIMENT_CONFIG)
        self.cfg_type = SUPPORTED_CONFIGURATION_TYPES.EXPERIMENT

        # Update with provided values
        for key, value in config_dict.items():
            setattr(self, key, value)

    def get_timed_modes(self):
        """Return the list of pre-defined timed-mode routine descriptors (raw
        dicts). Empty when only unlimited mode is in use."""
        modes = getattr(self, "timed_modes", []) or []
        return modes if isinstance(modes, list) else []
