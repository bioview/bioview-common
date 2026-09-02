"""Depths for the bounded streaming queues.

All of these used to be unbounded. On an unbounded queue a consumer that stalls
(or, as happened during DPIC balance, is never started) grows RAM without limit
and pushes latency up with it, while every ``except queue.Full`` handler in the
codebase sits there as dead code. Bounding them converts that failure mode into
a bounded, *countable* drop.

Depths are expressed in chunks. One chunk is one receive buffer -- roughly
40 ms at 1 MSps with the default USRP buffering -- so the numbers below are
about a third of a second of slack on the live paths and a couple of seconds on
the save path, which is the one that must ride out disk hiccups.
"""

#: Raw Rx buffers waiting for demodulation, per device.
RX_QUEUE_DEPTH = 8

#: Demodulated chunks waiting to be written to disk. Deepest of the set: disk
#: writes are bursty and dropping here means losing recorded data.
SAVE_QUEUE_DEPTH = 64

#: Demodulated chunks waiting to be forwarded to the client. Shallow on purpose
#: -- stale display data has no value, so old chunks are evicted rather than
#: queued behind.
DISPLAY_QUEUE_DEPTH = 16

#: Chunks waiting on the server's socket writer.
DATA_OUTPUT_QUEUE_DEPTH = 32

#: How long a producer waits for room before it counts a drop.
QUEUE_PUT_TIMEOUT_S = 0.1
