import json

from bioview_common.constants import SUPPORTED_CONFIGURATION_TYPES

from .biopac import BiopacConfiguration
from .config import (
    Configuration,
    configuration_for_cfg_type,
    register_device_configuration,
)
from .experiment import FEATURE_DEFAULTS, ExperimentConfiguration
from .microphone import MicrophoneConfiguration
from .usrp import USRPConfiguration


def get_configuration_callback(cfg_type: str):
    """The class that reads one wire-format ``type``, or ``None``."""
    if cfg_type == SUPPORTED_CONFIGURATION_TYPES.EXPERIMENT.value:
        return ExperimentConfiguration

    return configuration_for_cfg_type(cfg_type)


def parse_configuration_file(file_path: str) -> dict:
    data = {}

    try:
        with open(file_path, encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            return {}
    except (json.JSONDecodeError, FileNotFoundError, PermissionError):
        return {}

    parsed = {}
    for k, v in data.items():
        config_cls = get_configuration_callback(v.get("type", None))
        if config_cls is None:
            continue

        parsed[k] = config_cls.from_dict(v)

    return parsed


__all__ = [
    "Configuration",
    "parse_configuration_file",
    "register_device_configuration",
    "SUPPORTED_CONFIGURATION_TYPES",
    "ExperimentConfiguration",
    "FEATURE_DEFAULTS",
    "USRPConfiguration",
    "BiopacConfiguration",
    "MicrophoneConfiguration",
]
