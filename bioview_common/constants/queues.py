"""Depths for the bounded streaming queues, in chunks.

One chunk is one receive buffer (~40 ms at 1 MSps). See
bioview-docs/architecture/streaming.md for the drop policies these imply.
"""

#: Raw Rx buffers waiting for demodulation, per device.
RX_QUEUE_DEPTH = 8

#: Demodulated chunks waiting to be written to disk. Deepest of the set: disk
#: writes are bursty and dropping here means losing recorded data.
SAVE_QUEUE_DEPTH = 64

# Shallow on purpose: stale display data is evicted, not queued behind.
DISPLAY_QUEUE_DEPTH = 16

#: Chunks waiting on the server's socket writer.
DATA_OUTPUT_QUEUE_DEPTH = 32

#: How long a producer waits for room before it counts a drop.
QUEUE_PUT_TIMEOUT_S = 0.1
