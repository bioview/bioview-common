"""Bounded-queue put policies.

:func:`put_or_drop` waits briefly then drops the new item (save paths);
:func:`put_drop_oldest` evicts the oldest (display paths). Both return False
when an item was dropped, so callers can count rather than log.
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
    """Discard the oldest item, then enqueue ``item``. False if still full."""
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
