"""Bounded-queue put policies."""

import queue

from bioview_common import drain, put_drop_oldest, put_or_drop


def test_put_or_drop_succeeds_when_there_is_room():
    q = queue.Queue(maxsize=2)
    assert put_or_drop(q, "a", timeout=0.01)
    assert put_or_drop(q, "b", timeout=0.01)
    assert q.qsize() == 2


def test_put_or_drop_drops_the_new_item_when_full():
    """The save path prefers losing the newest chunk to stalling the producer."""
    q = queue.Queue(maxsize=1)
    assert put_or_drop(q, "keep", timeout=0.01)
    assert not put_or_drop(q, "drop", timeout=0.01)
    assert q.get_nowait() == "keep"
    assert q.empty()


def test_put_drop_oldest_evicts_to_make_room():
    """The display path prefers losing the oldest chunk to adding latency."""
    q = queue.Queue(maxsize=2)
    for item in ("a", "b", "c", "d"):
        assert put_drop_oldest(q, item)
    assert [q.get_nowait(), q.get_nowait()] == ["c", "d"]


def test_put_policies_tolerate_a_missing_queue():
    assert not put_or_drop(None, "x")
    assert not put_drop_oldest(None, "x")
    assert drain(None) == 0


def test_drain_empties_the_whole_queue():
    """stop_saving/stop_display used to remove exactly one item."""
    q = queue.Queue()
    for i in range(5):
        q.put(i)
    assert drain(q) == 5
    assert q.empty()
