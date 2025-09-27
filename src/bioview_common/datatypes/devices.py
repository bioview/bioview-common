from enum import Enum


class DeviceType(Enum):
    INVALID = ""
    USRP = "usrp"
    BIOPAC = "biopac"


SUPPORTED_DEVICES = [x.value for x in DeviceType]
