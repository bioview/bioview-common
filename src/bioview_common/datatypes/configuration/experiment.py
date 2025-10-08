from .config import Configuration


# Generic configuration for any experiment
BASE_EXPERIMENT_CONFIG = {
    "enable_save": False,
    "display_sources": [],
    "file_name": "default",
    "save_dir": None,
    "data_sources": [],
    "enable_instructions": False,
    "instruction_type": None,
}

SAVE_PARAMS = ["enable_save", "save_dir", "file_name"]


class ExperimentConfiguration(Configuration):
    def __init__(self, config_dict: dict):
        # Initialize using default values
        super().__init__(BASE_EXPERIMENT_CONFIG)

        # Update with provided values
        for key, value in config_dict.items():
            setattr(self, key, value)

    def get_save_config(self):
        return {
            "enable_save": self.enable_save,
            "save_dir": self.save_path,
            "file_name": self.file_name,
        }

    def get_display_config(self):
        return {"display_sources": getattr(self, "display_sources", [])}
