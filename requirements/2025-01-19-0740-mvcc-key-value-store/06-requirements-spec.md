# Requirements Specification: In-Memory MVCC Key-Value Store

## Problem Statement
Implement an in-memory key-value store with Multi-Version Concurrency Control (MVCC) that allows multiple threads to read and write concurrently without blocking each other. The store should provide ACID transaction support and maintain data consistency through versioning.

## Solution Overview
Build a thread-safe, in-memory key-value store that:
- Maintains multiple versions of each key-value pair
- Supports concurrent transactions without read-write blocking
- Provides ACID guarantees with focus on isolation through MVCC
- Implements Read Committed isolation level with extensibility for more levels
- Uses 64-bit transaction IDs to avoid wraparound issues

## Functional Requirements

### 1. Core Operations
- **Get(key)**: Retrieve value for a key within a transaction context
- **Put(key, value)**: Store/update a key-value pair within a transaction
- **Delete(key)**: Mark a key as deleted within a transaction
- **Begin()**: Start a new transaction
- **Commit()**: Commit all changes made in a transaction
- **Rollback()**: Abort a transaction and discard all changes

### 2. Transaction Support
- Full ACID compliance:
  - **Atomicity**: All operations in a transaction succeed or fail together
  - **Consistency**: Data remains valid according to application rules
  - **Isolation**: Read Committed level initially
  - **Durability**: Not required (in-memory only)
- Support for multiple concurrent transactions
- No blocking between readers and writers

### 3. Versioning
- Each key can have multiple versions
- Versions ordered newest-to-oldest (N2O) for optimal recent data access
- Each version tracks:
  - The value
  - Creating transaction ID
  - Deleting transaction ID (if deleted)
  - Timestamp

### 4. Visibility Rules
- Transactions see a consistent view of data
- Read Committed isolation: see latest committed data at statement start
- Deleted keys return "not found" to transactions that can't see the deletion

## Technical Requirements

### 1. Data Structures
```python
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from enum import Enum
import threading

class TxnState(Enum):
    ACTIVE = "active"
    COMMITTED = "committed"
    ABORTED = "aborted"

@dataclass
class Version:
    """Core version structure"""
    value: Any
    created_txn_id: int
    deleted_txn_id: int = 0  # 0 means not deleted
    timestamp: int = 0

class MVCCStore:
    """Main store structure"""
    def __init__(self):
        self.data: Dict[str, List[Version]] = {}  # Key -> version chain
        self._txn_counter = 0  # Global transaction counter
        self._txn_counter_lock = threading.Lock()
        self.active_txns: Dict[int, 'Transaction'] = {}  # Active transactions
        self._data_lock = threading.RWLock()  # For data protection

@dataclass
class Transaction:
    """Transaction structure"""
    id: int
    begin_time: int
    state: TxnState = TxnState.ACTIVE
    read_set: Dict[str, int] = None  # Keys read -> version timestamp
    write_set: Dict[str, Version] = None  # Keys written
    
    def __post_init__(self):
        if self.read_set is None:
            self.read_set = {}
        if self.write_set is None:
            self.write_set = {}
```

### 2. Concurrency
- Thread-safe for multiple concurrent readers and writers
- Use threading locks for transaction ID generation
- Consider using threading.RLock() for reader-writer scenarios
- Minimize lock contention for read operations

### 3. Memory Management
- Version chains stored as lists for each key
- No automatic garbage collection initially (per user requirement)
- Design should allow easy addition of GC later
- Consider memory pooling for version objects

### 4. Performance Targets
- Not targeting >100K ops/sec initially
- Design should not preclude future optimization
- Optimize for read-heavy workloads
- Keep version lookup efficient

## Implementation Hints

### 1. Transaction ID Management
```python
def next_txn_id(self) -> int:
    """Get next transaction ID atomically"""
    with self._txn_counter_lock:
        self._txn_counter += 1
        return self._txn_counter
```

### 2. Version Visibility Check
```python
def is_visible_to(self, txn: Transaction) -> bool:
    """Check if version is visible to transaction"""
    # Version is visible if:
    # 1. Created before or by this transaction
    # 2. Not deleted, or deleted after this transaction started
    return (self.created_txn_id <= txn.begin_time and 
            (self.deleted_txn_id == 0 or self.deleted_txn_id > txn.begin_time))
```

### 3. Finding Visible Version
```python
def find_version(self, key: str, txn: Transaction) -> Optional[Version]:
    """Find visible version for transaction"""
    versions = self.data.get(key, [])
    # Iterate newest to oldest (N2O order)
    for version in reversed(versions):
        if version.is_visible_to(txn):
            return version
    return None
```

### 4. Commit Process
1. Validate transaction (no conflicts for Read Committed)
2. Get commit timestamp
3. Apply all writes to main store
4. Mark transaction as committed
5. Make changes visible to other transactions

## API Design

```python
from abc import ABC, abstractmethod

class Store(ABC):
    """Store interface"""
    
    @abstractmethod
    def begin(self) -> Transaction:
        """Start a new transaction"""
        pass
    
    @abstractmethod
    def get(self, txn: Transaction, key: str) -> Any:
        """Get value for key in transaction context"""
        pass
    
    @abstractmethod
    def put(self, txn: Transaction, key: str, value: Any) -> None:
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

# Exception types
class KeyNotFoundError(Exception):
    """Raised when key is not found"""
    pass

class TransactionAbortedError(Exception):
    """Raised when transaction is aborted"""
    pass

class TransactionCommittedError(Exception):
    """Raised when operating on already committed transaction"""
    pass
```

## Acceptance Criteria

1. **Correctness**
   - Transactions maintain ACID properties
   - Read Committed isolation level properly implemented
   - No lost updates or dirty reads

2. **Concurrency**
   - Multiple threads can read/write simultaneously
   - No deadlocks possible
   - Readers never block writers and vice versa

3. **Performance**
   - Sub-millisecond response for simple operations
   - Linear scaling with number of readers
   - Reasonable memory usage per version

4. **Testing**
   - Unit tests for all operations
   - Concurrent transaction tests
   - Isolation level verification tests
   - Stress tests with multiple threads

## Future Extensions

Based on user requirements, design should support:
1. Additional isolation levels (Repeatable Read, Serializable)
2. Garbage collection for old versions
3. Performance optimizations for >100K ops/sec
4. Potential distributed operation (though not required now)

## Assumptions

1. Values can be any type (Python's Any type)
2. Keys are strings
3. No persistence required
4. No size limits on values
5. Transaction IDs never wrap (64-bit)
6. Version chains ordered N2O as discussed
7. No automatic garbage collection initially