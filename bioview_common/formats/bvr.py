"""The ``bioview-raw-v3`` (.bvr) recording format.

One file per session, holding every device's *save-rate* stream. Devices run at
independent rates and emit chunks of different widths, so the file is a sequence
of self-describing per-device records rather than one matrix::

    [magic "BVR3" (4 bytes)]
    [header length (4 bytes, big-endian uint32)]
    [JSON header]
    [record][record]...
    [JSON trailer]
    [trailer length (8 bytes, big-endian uint64)]
    [magic "BVRMETA1" (8 bytes)]

The trailer is written once at close, which is what lets the record region be
appended to for the whole session. A file with no trailer is an unfinished
recording; every complete record before that point is still readable.

Each record is a fixed 24-byte little-endian header (little-endian so the sample
block needs no byteswap on x86) followed by the samples::

    uint16 device_idx    index into header["devices"]
    uint16 flags         bit0: float64 samples (else float32); bit1: complex/IQ
    uint32 n_samples     samples per row in this record
    uint64 t_offset_us   microseconds since header["t0_unix"], wall clock at emit
    uint64 sample_idx    device sample counter of this record's first sample

then ``n_rows * n_samples`` samples, row-major, where ``n_rows`` comes from the
device's header entry.

The two time fields answer different questions and both are load-bearing:

* ``sample_idx`` is exact. A record is contiguous with the previous one from the
  same device iff ``sample_idx == prev_sample_idx + prev_n_samples``; any other
  value says precisely how many samples were dropped.
* ``t_offset_us`` is wall clock, for aligning devices against each other and for
  catching a device that does not achieve its nominal rate.

Only ``t0_unix`` in the header is an absolute time; everything else in the file
is an offset from it.
"""

from __future__ import annotations

import json
import struct


BVR3_MAGIC = b"BVR3"
BVR_TRAILER_MAGIC = b"BVRMETA1"
BVR_FORMAT = "bioview-raw-v3"

#: ``<`` little-endian: H device_idx, H flags, I n_samples, Q t_offset_us, Q sample_idx
RECORD_STRUCT = struct.Struct("<HHIQQ")
RECORD_HEADER_SIZE = RECORD_STRUCT.size  # 24

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
    """Unpack a record header from ``buf`` at ``offset``.

    Returns ``(device_idx, flags, n_samples, t_offset_us, sample_idx)``.
    """
    return RECORD_STRUCT.unpack_from(buf, offset)


def encode_header(header: dict) -> bytes:
    """Magic + length-prefixed JSON header, as written at the start of a file."""
    blob = json.dumps(header, default=str).encode("utf-8")
    return BVR3_MAGIC + struct.pack("!I", len(blob)) + blob


def encode_trailer(trailer: dict) -> bytes:
    """Length-suffixed JSON trailer + magic, as written when a file closes."""
    blob = json.dumps(trailer, default=str).encode("utf-8")
    return blob + struct.pack("!Q", len(blob)) + BVR_TRAILER_MAGIC
