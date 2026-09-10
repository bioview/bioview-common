from enum import Enum
from typing import Any


def merged_with_defaults(defaults: dict[str, Any], overrides: dict[str, Any]):
    """``overrides`` applied over ``defaults``, merging one level of nesting.

    A config file that sets only ``calibration.enabled`` used to replace the
    whole default calibration block, so every key it did not mention vanished
    and the value the panel showed came from a fallback buried in the backend
    rather than from the configuration. Nested blocks (``calibration``,
    ``dpic_balance``, ``fmcw``, ...) are flat, so one level is all that is
    needed and a deeper walk would only make ``channel_map`` harder to reason
    about.
    """
    merged: dict[str, Any] = {}
    for key, value in (overrides or {}).items():
        base = defaults.get(key)
        if isinstance(base, dict) and isinstance(value, dict):
            value = {**base, **value}
        merged[key] = value
    return merged


class BaseConfig:
    def __init__(self, config_dict=None):
        if not config_dict:
            config_dict = {}

        # Load all parameters from dictionary as attributes
        for param, value in config_dict.items():
            setattr(self, param, value)

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]):
        return cls(config_dict)

    def get_param(self, param, default_value=None):
        return getattr(self, param, default_value)

    def set_param(self, param, value):
        setattr(self, param, value)

    def get_type(self):
        """Return the configuration type (a SUPPORTED_CONFIGURATION_TYPES member)."""
        return getattr(self, "cfg_type", None)

    def to_dict(self):
        result = {}
        for key, value in self.__dict__.items():
            if key.startswith("_") or callable(value):
                continue
            # Enum values (e.g. cfg_type) are not JSON serializable, so
            # store their value.
            if isinstance(value, Enum):
                value = value.value
            result[key] = value
        cfg_type = result.get("cfg_type")
        if cfg_type and "type" not in result:
            result["type"] = cfg_type
        return result


#: ``device_type`` -> (wire ``type`` name, configuration class). Populated by
#: ``register_device_configuration`` as each shipped configuration module is
#: imported, so adding a device means adding one registration rather than
#: editing a mapping here, a branch in ``load_from_dict`` and a branch in
#: ``get_configuration_callback``.
_DEVICE_CONFIGURATIONS: dict[str, tuple[str, type]] = {}


def register_device_configuration(device_type: str, cfg_type: str, config_cls: type):
    """Teach the parser about one device type and the class that reads it."""
    _DEVICE_CONFIGURATIONS[str(device_type)] = (str(cfg_type), config_cls)


def configuration_for_cfg_type(cfg_type: str):
    """The configuration class for a wire-format ``type`` (e.g. ``"USRP"``)."""
    for name, config_cls in _DEVICE_CONFIGURATIONS.values():
        if name == cfg_type:
            return config_cls
    return None


def _resolve_device_type(value: dict[str, Any]) -> str | None:
    """Map wire-format ``type`` / ``cfg_type`` fields to backend ``device_type``."""
    device_type = value.get("device_type")
    if device_type in _DEVICE_CONFIGURATIONS:
        return device_type

    cfg_type = value.get("type") or value.get("cfg_type")
    if not cfg_type:
        return None

    if isinstance(cfg_type, Enum):
        cfg_type = cfg_type.value

    # A config file may spell the type in either case ("USRP" or "usrp"), and
    # older files carry the device_type value in the ``type`` field.
    key = str(cfg_type).lower()
    for device_type, (name, _) in _DEVICE_CONFIGURATIONS.items():
        if key in {name.lower(), device_type.lower()}:
            return device_type
    return None


class Configuration:
    def __init__(self, config_dict: dict[str, Any] | None = None):
        self.experiment = None
        self.devices = {}  # device_id -> BaseConfig subclass instance

        if config_dict:
            self.load_from_dict(config_dict)

    def load_from_dict(self, config_dict: dict[str, Any]):
        # Deferred: the configuration package imports this module, and
        # importing it is what fills _DEVICE_CONFIGURATIONS.
        from . import ExperimentConfiguration

        for key, value in config_dict.items():
            if key.lower() == "experiment":
                self.experiment = ExperimentConfiguration(value)
                continue

            device_type = _resolve_device_type(value)
            if device_type is None:
                self.devices[key] = BaseConfig(value)
                continue

            payload = dict(value)
            payload["device_type"] = device_type
            _, config_cls = _DEVICE_CONFIGURATIONS[device_type]
            self.devices[key] = config_cls(payload)

    def to_dict(self) -> dict[str, Any]:
        result = {}
        if self.experiment:
            result["Experiment"] = self.experiment.to_dict()

        for device_id, device_cfg in self.devices.items():
            result[device_id] = device_cfg.to_dict()

        return result

    @classmethod
    def from_dict(cls, data_dict: dict[str, Any]):
        return cls(data_dict)

    def update_device_param(self, device_id: str, param: str, value: Any):
        if device_id not in self.devices:
            return
        from .hardware_params import (
            GLOBAL_RX_PARAMS,
            GLOBAL_TX_PARAMS,
            update_device_param,
        )

        cfg = self.devices[device_id]
        if param in GLOBAL_TX_PARAMS:
            update_device_param(cfg, param, value, kind="tx")
        elif param in GLOBAL_RX_PARAMS:
            update_device_param(cfg, param, value, kind="rx")
        else:
            cfg.set_param(param, value)
