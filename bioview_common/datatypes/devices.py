from enum import Enum


class DeviceType(Enum):
    INVALID = ""
    USRP = "usrp"
    BIOPAC = "biopac"
    MICROPHONE = "microphone"


SUPPORTED_DEVICES = [x.value for x in DeviceType]
