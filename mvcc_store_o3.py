# mvcc_store.py
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class TxnState(Enum):
    ACTIVE = "active"
    COMMITTED = "committed"
    ABORTED = "aborted"


@dataclass
class Version:
    value: Optional[int]  # None means tombstone (delete)
    created_by: int  # txn id
    deleted: bool = False  # True = this version is a delete


@dataclass
class Transaction:
    id: int
    state: TxnState = TxnState.ACTIVE
    read_set: Dict[str, int] = field(
        default_factory=dict
    )  # key → index in version chain
    write_set: Dict[str, Version] = field(default_factory=dict)


# --- errors -------------------------------------------------------------


class KeyNotFoundError(Exception): ...


class TransactionCommittedError(Exception): ...


class TransactionAbortedError(Exception): ...


# --- store --------------------------------------------------------------


class MVCCStore:
    """A **minimal** in-memory MVCC key-value store (Read Committed)."""

    def __init__(self) -> None:
        self._next_txn = 0
        self._data: Dict[str, List[Version]] = {}  # key → [newest … oldest]
        self._committed: set[int] = set()
        self._active: Dict[int, Transaction] = {}

    # ---- txn helpers ----
    def _new_txn_id(self) -> int:
        self._next_txn += 1
        return self._next_txn

    def _check_active(self, txn: Transaction) -> None:
        if txn.state is TxnState.COMMITTED:
            raise TransactionCommittedError
        if txn.state is TxnState.ABORTED:
            raise TransactionAbortedError

    # ---- public API ----
    def begin(self) -> Transaction:
        txn = Transaction(id=self._new_txn_id())
        self._active[txn.id] = txn
        return txn

    def get(self, txn: Transaction, key: str) -> int:
        self._check_active(txn)

        # uncommitted write?
        if key in txn.write_set:
            ver = txn.write_set[key]
            if ver.deleted:
                raise KeyNotFoundError(key)
            return ver.value  # type: ignore

        # search committed versions (newest-first)
        chain = self._data.get(key, [])
        for idx, ver in enumerate(chain):
            if ver.created_by in self._committed:
                if ver.deleted:
                    raise KeyNotFoundError(key)
                txn.read_set[key] = idx
                return ver.value  # type: ignore
        raise KeyNotFoundError(key)

    def put(self, txn: Transaction, key: str, value: int) -> None:
        self._check_active(txn)
        txn.write_set[key] = Version(value=value, created_by=txn.id)

    def delete(self, txn: Transaction, key: str) -> None:
        self._check_active(txn)
        # ensure key exists *somewhere* (write set or committed data)
        if key not in txn.write_set:
            self.get(txn, key)  # will raise if not found
        txn.write_set[key] = Version(value=None, created_by=txn.id, deleted=True)

    def commit(self, txn: Transaction) -> None:
        self._check_active(txn)
        # apply writes
        for k, ver in txn.write_set.items():
            self._data.setdefault(k, []).insert(0, ver)
        txn.state = TxnState.COMMITTED
        self._committed.add(txn.id)
        self._active.pop(txn.id, None)

    def rollback(self, txn: Transaction) -> None:
        if txn.state is TxnState.COMMITTED:
            raise TransactionCommittedError
        txn.state = TxnState.ABORTED
        txn.read_set.clear()
        txn.write_set.clear()
        self._active.pop(txn.id, None)

    # ---- debug helpers ----
    @property
    def data(self):  # expose for tests
        return self._data
