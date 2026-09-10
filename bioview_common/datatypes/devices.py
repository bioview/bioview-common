from enum import Enum


class DeviceType(Enum):
    INVALID = ""
    USRP = "usrp"
    BIOPAC = "biopac"
    # Host audio input (PortAudio). One row per captured channel, streamed
    # through the same pipeline as every other device so a recording is
    # sample-aligned with the RF and physiological rows beside it.
    MICROPHONE = "microphone"


SUPPORTED_DEVICES = [x.value for x in DeviceType]
