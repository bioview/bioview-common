import json
from enum import Enum
from typing import Dict, Any, Optional

class BaseConfig:
    def __init__(self, config_dict=None):
        if not config_dict:
            config_dict = {}

        # Load all parameters from dictionary as attributes
        for param, value in config_dict.items():
            setattr(self, param, value)

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]):
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
            # Enum values (e.g. cfg_type) are not JSON serializable, so store their value.
            if isinstance(value, Enum):
                value = value.value
            result[key] = value
        return result

class Configuration:
    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        self.experiment = None
        self.devices = {}  # device_id -> BaseConfig subclass instance
        
        if config_dict:
            self.load_from_dict(config_dict)

    def load_from_dict(self, config_dict: Dict[str, Any]):
        from .experiment import ExperimentConfiguration
        from .usrp import USRPConfiguration
        from .biopac import BiopacConfiguration
        from .dummy import DummyConfiguration
        from ..devices import DeviceType

        for key, value in config_dict.items():
            if key.lower() == "experiment":
                self.experiment = ExperimentConfiguration(value)
            else:
                # It is a device key
                device_type = value.get("device_type")
                if device_type == DeviceType.USRP.value:
                    self.devices[key] = USRPConfiguration(value)
                elif device_type == DeviceType.BIOPAC.value:
                    self.devices[key] = BiopacConfiguration(value)
                elif device_type == DeviceType.DUMMY.value:
                    self.devices[key] = DummyConfiguration(value)
                else:
                    # Generic configuration
                    self.devices[key] = BaseConfig(value)

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        if self.experiment:
            result["Experiment"] = self.experiment.to_dict()
        
        for device_id, device_cfg in self.devices.items():
            result[device_id] = device_cfg.to_dict()
        
        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str):
        return cls(json.loads(json_str))

    @classmethod
    def from_dict(cls, data_dict: Dict[str, Any]):
        return cls(data_dict)

    def get_device_config(self, device_id: str):
        return self.devices.get(device_id)

    def update_device_param(self, device_id: str, param: str, value: Any):
        if device_id in self.devices:
            self.devices[device_id].set_param(param, value)
