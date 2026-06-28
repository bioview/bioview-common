from enum import Enum


class DeviceType(Enum):
    INVALID = ""
    USRP = "usrp"
    BIOPAC = "biopac"
    # Virtual device that synthesizes phase-shifted sine waves. Useful for testing
    # the full connect -> stream -> display -> save pipeline without hardware.
    DUMMY = "dummy"


SUPPORTED_DEVICES = [x.value for x in DeviceType]
