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
import importlib
import json
from types import NoneType


class Configuration:
    def __init__(self, config_dict=None):
        self.type = None
        self._ui_parameters = {}

        if config_dict:
            self.type = config_dict.get("type")

            # Set parameters as attributes
            parameters = config_dict.get("parameters", {})
            for param, value in parameters.items():
                setattr(self, param, value)

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
        data = {
            key: value
            for key, value in self.__dict__.items()
            if not key.startswith("_") and not callable(value)
        }

        # Extract parameters (excluding type and special attributes)
        parameters = {k: v for k, v in data.items() if k != "type"}

        result = {
            "type": self.type,
            "parameters": parameters,
        }

        # Store class information for serialization
        result["__class__"] = self.__class__.__name__
        result["__module__"] = self.__class__.__module__
        return result

    @classmethod
    def from_dict(cls, data):
        class_name = data.get("__class__")
        module_name = data.get("__module__")

        if class_name and module_name:
            try:
                module = importlib.import_module(module_name)
                target_class = getattr(module, class_name)

                # Remove class info for clean initialization
                config_data = {
                    k: v for k, v in data.items() if k not in ["__class__", "__module__"]
                }

                return target_class(config_data)
            except (ImportError, AttributeError):
                print(
                    f"Warning: Could not instantiate {class_name}, \
                        falling back to base Configuration"
                )
                config_data = {
                    k: v for k, v in data.items() if k not in ["__class__", "__module__"]
                }
                return cls(config_data)
        else:
            config_data = {
                k: v for k, v in data.items() if k not in ["__class__", "__module__"]
            }
            return cls(config_data)

    def to_json(self):
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str):
        return cls.from_dict(json.loads(json_str))
