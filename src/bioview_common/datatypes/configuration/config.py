"""
An abstraction for how different levels of configuration files are handled
throughout both the server and client. Configuration objects may be created
by the use of dictionaries/JSON in formats specified below -
{
    "type":
    "parameters": {
        // List of specific parameters for functionality
        param: value (any type)
    }
}
"""
import json
from types import NoneType

from ..devices import SUPPORTED_DEVICES, DeviceType


class Configuration:
    def __init__(self, config_dict=None):
        if not config_dict:
            config_dict = {}

        # Load all parameters from dictionary as attributes
        for param, value in config_dict.items():
            setattr(self, param, value)

        device_type = config_dict.get("device_type", None)
        if device_type and device_type in SUPPORTED_DEVICES:
            self.device_type = DeviceType(device_type).value
        else:
            self.device_type = DeviceType.INVALID.value

    def get_param(self, param, default_value=None):
        try:
            value = getattr(self, param)
        except AttributeError:
            value = default_value
        return value

    def set_param(self, param, value):
        current_type = type(getattr(self, param, None))
        if current_type is not NoneType:
            setattr(self, param, current_type(value))
        else:
            setattr(self, param, value)

    def to_dict(self):
        result = {
            key: value
            for key, value in self.__dict__.items()
            if not key.startswith("_") and not callable(value)
        }

        return result

    @classmethod
    def from_dict(self, data_dict, config_type=None):
        """
        While we can construct a configuration for any dictionary, we check if a
        special class-based configuration can be restored to enable extra features.
        """
        if not config_type:
            config_type = data_dict.get("device_type", None)

        if config_type == DeviceType.USRP.value:
            from .usrp import USRPConfiguration as cls
        elif config_type == DeviceType.BIOPAC.value:
            from .biopac import BiopacConfiguration as cls
        else:
            cls = self

        return cls(data_dict)

    def to_json(self):
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str):
        return cls.from_dict(json.loads(json_str))
