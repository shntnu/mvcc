"""
In-memory MVCC Key-Value Store Implementation

A multi-version concurrency control store that maintains multiple versions
of each key-value pair to enable concurrent transactions without blocking.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
from abc import ABC, abstractmethod
import time


class TxnState(Enum):
    """Transaction states"""
    ACTIVE = "active"
    COMMITTED = "committed"
    ABORTED = "aborted"


@dataclass
class Version:
    """
    Represents a single version of a value.
    
    Attributes:
        value: The actual value (int type for simplicity)
        created_txn_id: Transaction ID that created this version
        deleted_txn_id: Transaction ID that deleted this version (0 if not deleted)
        timestamp: Creation timestamp
    """
    value: int
    created_txn_id: int
    deleted_txn_id: int = 0  # 0 means not deleted
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000000))  # microseconds
    
    def is_visible_to(self, txn_begin_time: int) -> bool:
        """
        Check if this version is visible to a transaction that began at given time.
        
        A version is visible if it was created before or at the transaction's begin time.
        Whether it's deleted is checked separately.
        """
        return self.created_txn_id <= txn_begin_time


@dataclass
class Transaction:
    """
    Represents a database transaction.
    
    Attributes:
        id: Unique transaction ID
        begin_time: Transaction start timestamp (used for visibility)
        state: Current transaction state
        read_set: Keys read during transaction (for future conflict detection)
        write_set: Buffered writes waiting to be committed
    """
    id: int
    begin_time: int
    state: TxnState = TxnState.ACTIVE
    read_set: Dict[str, int] = field(default_factory=dict)  # key -> version timestamp
    write_set: Dict[str, Version] = field(default_factory=dict)  # key -> new version


# Custom Exceptions
class KeyNotFoundError(Exception):
    """Raised when a key is not found in the store"""
    pass


class TransactionAbortedError(Exception):
    """Raised when operating on an aborted transaction"""
    pass


class TransactionCommittedError(Exception):
    """Raised when operating on an already committed transaction"""
    pass


class Store(ABC):
    """Abstract base class for key-value store"""
    
    @abstractmethod
    def begin(self) -> Transaction:
        """Start a new transaction"""
        pass
    
    @abstractmethod
    def get(self, txn: Transaction, key: str) -> int:
        """Get value for key in transaction context"""
        pass
    
    @abstractmethod
    def put(self, txn: Transaction, key: str, value: int) -> None:
        """Put key-value pair in transaction context"""
        pass
    
    @abstractmethod
    def delete(self, txn: Transaction, key: str) -> None:
        """Delete key in transaction context"""
        pass
    
    @abstractmethod
    def commit(self, txn: Transaction) -> None:
        """Commit transaction"""
        pass
    
    @abstractmethod
    def rollback(self, txn: Transaction) -> None:
        """Rollback transaction"""
        pass


class MVCCStore(Store):
    """
    Main MVCC key-value store implementation.
    
    This implementation provides:
    - Multi-version storage for each key
    - Transaction isolation through versioning
    - Read Committed isolation level
    - Non-blocking reads and writes
    """
    
    def __init__(self):
        """Initialize the MVCC store"""
        self.data: Dict[str, List[Version]] = {}  # key -> list of versions (newest first)
        self._txn_counter = 0  # Global transaction counter
        self.active_txns: Dict[int, Transaction] = {}  # Currently active transactions
        self._timestamp_counter = 0  # Global timestamp counter
    
    def _next_txn_id(self) -> int:
        """Generate next transaction ID"""
        self._txn_counter += 1
        return self._txn_counter
    
    def _next_timestamp(self) -> int:
        """Generate next timestamp"""
        self._timestamp_counter += 1
        return self._timestamp_counter
    
    def begin(self) -> Transaction:
        """Start a new transaction"""
        txn_id = self._next_txn_id()
        txn = Transaction(
            id=txn_id,
            begin_time=txn_id,  # Using txn_id as logical timestamp for simplicity
            state=TxnState.ACTIVE
        )
        self.active_txns[txn_id] = txn
        return txn
    
    def _check_txn_state(self, txn: Transaction) -> None:
        """Verify transaction is in valid state for operations"""
        if txn.state == TxnState.COMMITTED:
            raise TransactionCommittedError(f"Transaction {txn.id} is already committed")
        if txn.state == TxnState.ABORTED:
            raise TransactionAbortedError(f"Transaction {txn.id} is aborted")
    
    def _find_visible_version(self, key: str, txn: Transaction) -> Optional[Version]:
        """Find the visible version of a key for a transaction"""
        versions = self.data.get(key, [])
        
        # Iterate through versions (newest to oldest due to N2O ordering)
        for version in versions:
            if version.is_visible_to(txn.begin_time):
                # Check if this version represents a deletion
                if version.deleted_txn_id != 0 and version.deleted_txn_id <= txn.begin_time:
                    # This version is a tombstone that's visible to us
                    return None
                return version
        
        return None
    
    def get(self, txn: Transaction, key: str) -> int:
        """Get value for key in transaction context"""
        self._check_txn_state(txn)
        
        # Check write set first (uncommitted changes)
        if key in txn.write_set:
            version = txn.write_set[key]
            if version.deleted_txn_id != 0:
                raise KeyNotFoundError(f"Key '{key}' not found")
            return version.value
        
        # Check committed versions
        version = self._find_visible_version(key, txn)
        if version is None:
            raise KeyNotFoundError(f"Key '{key}' not found")
        
        # Track read for future conflict detection
        txn.read_set[key] = version.timestamp
        
        return version.value
    
    def put(self, txn: Transaction, key: str, value: int) -> None:
        """Put key-value pair in transaction context"""
        self._check_txn_state(txn)
        
        # Create new version in write set
        new_version = Version(
            value=value,
            created_txn_id=txn.id,
            deleted_txn_id=0,
            timestamp=self._next_timestamp()
        )
        
        txn.write_set[key] = new_version
    
    def delete(self, txn: Transaction, key: str) -> None:
        """Delete key in transaction context"""
        self._check_txn_state(txn)
        
        # Check if key exists (either in write set or committed data)
        if key in txn.write_set:
            # Mark the write set version as deleted
            txn.write_set[key].deleted_txn_id = txn.id
        else:
            # Check if key exists in committed data
            version = self._find_visible_version(key, txn)
            if version is None:
                raise KeyNotFoundError(f"Key '{key}' not found")
            
            # Create tombstone version in write set
            # For deletes, we create a new version with the same created_txn_id
            # but with deleted_txn_id set
            tombstone = Version(
                value=version.value,  # Keep the value for history
                created_txn_id=txn.id,  # This delete operation creates a new version
                deleted_txn_id=txn.id,  # And immediately marks it as deleted
                timestamp=self._next_timestamp()
            )
            txn.write_set[key] = tombstone
    
    def commit(self, txn: Transaction) -> None:
        """Commit transaction"""
        self._check_txn_state(txn)
        
        # Apply all writes to the main store
        for key, version in txn.write_set.items():
            if key not in self.data:
                self.data[key] = []
            
            # Insert at beginning (newest first - N2O order)
            self.data[key].insert(0, version)
        
        # Update transaction state
        txn.state = TxnState.COMMITTED
        
        # Remove from active transactions
        if txn.id in self.active_txns:
            del self.active_txns[txn.id]
    
    def rollback(self, txn: Transaction) -> None:
        """Rollback transaction"""
        if txn.state == TxnState.COMMITTED:
            raise TransactionCommittedError(f"Cannot rollback committed transaction {txn.id}")
        
        # Clear write set
        txn.write_set.clear()
        txn.read_set.clear()
        
        # Update state
        txn.state = TxnState.ABORTED
        
        # Remove from active transactions
        if txn.id in self.active_txns:
            del self.active_txns[txn.id]