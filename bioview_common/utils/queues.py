"""Bounded-queue put policies.

Every streaming queue is bounded, so each producer must declare what happens
when its consumer falls behind. Blocking forever is never right on a real-time
path -- on the receive path it stalls UHD into an overflow.

- :func:`put_or_drop` waits briefly, then drops the *new* item. For paths where
  every item matters (saving) and a short stall beats losing one.
- :func:`put_drop_oldest` evicts the oldest to make room. For paths where only
  the newest item matters (display), keeping latency bounded.

Both return False when the item was dropped, so callers can count drops instead
of logging each one.
"""

from __future__ import annotations

import contextlib
import queue
from typing import Any


def put_or_drop(q, item: Any, timeout: float = 0.1) -> bool:
    """Block up to ``timeout`` for room, then drop ``item``.

    Returns False when the item was dropped.
    """
    if q is None:
        return False
    try:
        q.put(item, timeout=timeout)
        return True
    except queue.Full:
        return False


def put_drop_oldest(q, item: Any) -> bool:
    """Make room by discarding the oldest item, then enqueue ``item``.

    Returns False when the item still could not be queued (another producer
    refilled the queue in between), which callers may count as a drop.
    """
    if q is None:
        return False
    for _ in range(3):
        try:
            q.put_nowait(item)
            return True
        except queue.Full:
            with contextlib.suppress(queue.Empty):
                q.get_nowait()
    return False


def drain(q) -> int:
    """Discard everything currently queued. Returns the number of items dropped."""
    if q is None:
        return 0
    dropped = 0
    while True:
        try:
            q.get_nowait()
        except (queue.Empty, OSError, ValueError):
            return dropped
        dropped += 1
