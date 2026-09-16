"""The ``bioview-raw-v3`` (.bvr) recording format."""

from __future__ import annotations

import json
import struct


BVR3_MAGIC = b"BVR3"
BVR_TRAILER_MAGIC = b"BVRMETA1"
BVR_FORMAT = "bioview-raw-v3"

RECORD_STRUCT = struct.Struct("<HHIQQ")
RECORD_HEADER_SIZE = RECORD_STRUCT.size

FLAG_FLOAT64 = 1 << 0
FLAG_COMPLEX = 1 << 1


def pack_record(device_idx, n_samples, t_offset_us, sample_idx, flags=0):
    """Pack one record header. The sample block follows it verbatim."""
    return RECORD_STRUCT.pack(
        int(device_idx) & 0xFFFF,
        int(flags) & 0xFFFF,
        int(n_samples) & 0xFFFFFFFF,
        max(0, int(t_offset_us)),
        max(0, int(sample_idx)),
    )


def unpack_record(buf, offset=0):
    """Unpack a record header from ``buf`` at ``offset``."""
    return RECORD_STRUCT.unpack_from(buf, offset)


def encode_header(header: dict) -> bytes:
    """Magic + length-prefixed JSON header, as written at the start of a file."""
    blob = json.dumps(header, default=str).encode("utf-8")
    return BVR3_MAGIC + struct.pack("!I", len(blob)) + blob


def encode_trailer(trailer: dict) -> bytes:
    """Length-suffixed JSON trailer + magic, as written when a file closes."""
    blob = json.dumps(trailer, default=str).encode("utf-8")
    return blob + struct.pack("!Q", len(blob)) + BVR_TRAILER_MAGIC
