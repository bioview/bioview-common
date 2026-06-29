from .config import BaseConfig


# Generic configuration for any experiment
#
# Two operational modes are supported:
#   * Unlimited mode (default): free-running acquisition with optional saving.
#   * Timed mode(s): pre-defined routines declared under "timed_modes". Each
#     routine runs streaming (saving on by default) for a fixed duration and may
#     present accompanying instructions (audio/video/text). A timed mode is a
#     dict of the form:
#       {
#         "label": "Routine 1",
#         "duration": "3m",            # number (seconds) or "3m"/"90s"/"mm:ss"
#         "instruction": {
#           "type": "audio" | "video" | "text",
#           "file": "instructions/intro.mp3",
#           "loop": false,             # audio/video only (default: play once)
#           "font_size": 28,           # text only
#           "line_gap": 2.0            # text only; omit => show all at once
#         }
#       }
BASE_EXPERIMENT_CONFIG = {
    "enable_save": False,
    "display_sources": [],
    "file_name": "",
    "save_dir": None,
    "data_sources": [],
    "timed_modes": [],
}

SAVE_PARAMS = ["enable_save", "save_dir", "file_name"]
from bioview_common.constants import SUPPORTED_CONFIGURATION_TYPES

class ExperimentConfiguration(BaseConfig):
    def __init__(self, config_dict: dict):
        # Initialize using default values
        super().__init__(BASE_EXPERIMENT_CONFIG)
        self.cfg_type = SUPPORTED_CONFIGURATION_TYPES.EXPERIMENT

        # Update with provided values
        for key, value in config_dict.items():
            setattr(self, key, value)

    def get_save_config(self):
        return {
            "enable_save": self.enable_save,
            "save_dir": self.save_dir,
            "file_name": self.file_name,
        }

    def get_display_config(self):
        return {"display_sources": getattr(self, "display_sources", [])}

    def get_timed_modes(self):
        """Return the list of pre-defined timed-mode routine descriptors (raw
        dicts). Empty when only unlimited mode is in use."""
        modes = getattr(self, "timed_modes", []) or []
        return modes if isinstance(modes, list) else []
