'''
An abstraction for how different levels of configuration files are handled throughout both the server and client. 
```Configuration``` objects may be created by the use of dictionaries/JSON formats specified in the format - 
{
    "type":
    "parameters": {
        // List of specific parameters for functionality
        param: value (any type)
    }, 
    "ui_parameters": {
        // Subset of parameters which can be exposed via UI for modification
        param: {
                display_label: '' # (string, specifying what label to show)
                display_type: '' # (text, slider, file picker)
                multipler: '' # (number, specifies base unit)
                range: '' # (optional) but specifies valid range of values 
                step: '' # (optional) step by which values change in case text/slider elements are picked
        }
    }
}
'''

import json
import importlib

class Configuration:
    def __init__(self, config_dict=None):
        self.type = None
        self._ui_parameters = {}
        
        if config_dict:
            self.type = config_dict.get('type')
            
            # Set parameters as attributes
            parameters = config_dict.get('parameters', {})
            for param, value in parameters.items():
                setattr(self, param, value)
            
            # Store UI parameters
            self._ui_parameters = config_dict.get('ui_parameters', {})
    
    def get_param(self, param, default_value=None):
        try:
            value = getattr(self, param)
        except AttributeError:
            value = default_value
        return value
    
    def set_param(self, param, value): 
        current_type = type(getattr(self, param, None))
        if current_type is not None:
            setattr(self, param, current_type(value))
        else:
            setattr(self, param, value)
    
    def get_ui_params(self): 
        ui_params = {}
        for param, ui_config in self._ui_parameters.items():
            ui_params[param] = ui_config.copy()
            ui_params[param]['value'] = self.get_param(param)
        return ui_params

    def to_dict(self):
        data = {key: value for key, value in self.__dict__.items() 
                if not key.startswith('_') and not callable(value)}
        
        # Extract parameters (excluding type and special attributes)
        parameters = {k: v for k, v in data.items() if k != 'type'}
        
        result = {
            'type': self.type,
            'parameters': parameters,
            'ui_parameters': self._ui_parameters
        }
        
        # Store class information for serialization
        result['__class__'] = self.__class__.__name__
        result['__module__'] = self.__class__.__module__
        return result
    
    @classmethod
    def from_dict(cls, data):
        class_name = data.get('__class__')
        module_name = data.get('__module__')
        
        if class_name and module_name:
            try:
                module = importlib.import_module(module_name)
                target_class = getattr(module, class_name)
                
                # Remove class info for clean initialization
                config_data = {k: v for k, v in data.items() 
                              if k not in ['__class__', '__module__']}
                
                return target_class(config_data)
            except (ImportError, AttributeError) as e:
                print(f"Warning: Could not instantiate {class_name}, falling back to base Configuration")
                config_data = {k: v for k, v in data.items() 
                              if k not in ['__class__', '__module__']}
                return cls(config_data)
        else:
            config_data = {k: v for k, v in data.items() 
                          if k not in ['__class__', '__module__']}
            return cls(config_data)
    
    def to_json(self):
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str):
        return cls.from_dict(json.loads(json_str))