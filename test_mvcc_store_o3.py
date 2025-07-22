# test_mvcc_store.py
import pytest
from mvcc_store_o3 import (
    MVCCStore,
    KeyNotFoundError,
    TransactionCommittedError,
    TransactionAbortedError,
)


def test_basic_put_get_commit():
    s = MVCCStore()
    t1 = s.begin()
    s.put(t1, "k", 1)
    assert s.get(t1, "k") == 1
    s.commit(t1)

    t2 = s.begin()
    assert s.get(t2, "k") == 1


def test_delete():
    s = MVCCStore()
    t1 = s.begin()
    s.put(t1, "x", 7)
    s.commit(t1)

    t2 = s.begin()
    s.delete(t2, "x")
    s.commit(t2)

    t3 = s.begin()
    with pytest.raises(KeyNotFoundError):
        s.get(t3, "x")


def test_last_write_wins():
    s = MVCCStore()
    t0 = s.begin()
    s.put(t0, "cnt", 0)
    s.commit(t0)

    t1, t2 = s.begin(), s.begin()
    s.put(t1, "cnt", 1)
    s.put(t2, "cnt", 2)
    s.commit(t1)
    s.commit(t2)  # t2 wins

    t3 = s.begin()
    assert s.get(t3, "cnt") == 2


def test_state_errors():
    s = MVCCStore()
    t = s.begin()
    s.commit(t)

    with pytest.raises(TransactionCommittedError):
        s.get(t, "absent")
    with pytest.raises(TransactionCommittedError):
        s.put(t, "k", 1)
    with pytest.raises(TransactionCommittedError):
        s.delete(t, "k")
    with pytest.raises(TransactionCommittedError):
        s.commit(t)

    t2 = s.begin()
    s.rollback(t2)
    with pytest.raises(TransactionAbortedError):
        s.get(t2, "k")
