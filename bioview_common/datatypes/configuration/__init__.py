import json 
from typing import Dict

from .config import Configuration
from .biopac import BiopacConfiguration
from .dummy import DummyConfiguration
from .experiment import ExperimentConfiguration
from .usrp import USRPConfiguration

from bioview_common.constants import SUPPORTED_CONFIGURATION_TYPES

def get_configuration_callback(cfg_type: str) -> Configuration: 
    if cfg_type == SUPPORTED_CONFIGURATION_TYPES.USRP.value: 
        return USRPConfiguration
    
    if cfg_type == SUPPORTED_CONFIGURATION_TYPES.BIOPAC.value: 
        return BiopacConfiguration

    if cfg_type == SUPPORTED_CONFIGURATION_TYPES.DUMMY.value: 
        return DummyConfiguration
    
    if cfg_type == SUPPORTED_CONFIGURATION_TYPES.EXPERIMENT.value: 
        return ExperimentConfiguration

def parse_configuration_file(file_path: str) -> Dict: 
    data = {} 
    
    try:
        data = json.load(open(file_path, encoding = 'utf-8'))
        if not isinstance(data, dict): return {}  
    except (json.JSONDecodeError, FileNotFoundError, PermissionError) as e:
        return {} 

    # For valid configurations, convert them into the appropriate object and return 
    parsed = {} 
    for k, v in data.items(): 
        cfg_type = v.get('type', None)
        if cfg_type not in SUPPORTED_CONFIGURATION_TYPES.__members__: 
            continue # Drop all unsupported types 
        
        parsed[k] = get_configuration_callback(cfg_type).from_dict(v)

    return parsed 

__all__ = [
    "Configuration", 
    "parse_configuration_file", 
    "SUPPORTED_CONFIGURATION_TYPES",
    "ExperimentConfiguration",
    "USRPConfiguration",
    "BiopacConfiguration",
    "DummyConfiguration"
]