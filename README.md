# MVCC Key-Value Store (Exploratory Implementation)

An experimental in-memory key-value store implementing Multi-Version Concurrency Control (MVCC) with Read Committed isolation level in Python.

## Overview

This is an exploratory implementation designed to understand MVCC concepts and transaction isolation. The store maintains multiple versions of each key-value pair, allowing concurrent transactions to read and write without blocking each other.

### Implementation Variants

This repository contains two implementations:

1. **`mvcc_store.py`** - The original comprehensive implementation (~270 lines) with full feature set
2. **`mvcc_store_o3.py`** - A simplified proof-of-concept version (~130 lines) that demonstrates core MVCC concepts with minimal code

## Key Features

- **Read Committed Isolation**: Each read sees the latest committed data at the time of the read
- **Non-blocking Reads**: Readers never block writers and vice versa
- **ACID Transactions**: Supports atomic commit/rollback with proper isolation
- **Version Management**: Maintains version history for each key with newest-to-oldest ordering
- **Write Buffering**: Changes are buffered in transaction's write set until commit

## Design Decisions

### Why Read Committed (not Snapshot Isolation)?

This implementation specifically provides Read Committed isolation where:
- Transactions see the latest committed values at read time
- Long-running transactions can observe changes from other committed transactions
- This differs from Snapshot Isolation where transactions see a consistent snapshot from their start time

## Usage Example

```python
from mvcc_store import MVCCStore

# Create store
store = MVCCStore()

# Transaction 1: Insert initial value
txn1 = store.begin()
store.put(txn1, "counter", 100)
store.commit(txn1)

# Transaction 2: Read and update
txn2 = store.begin()
value = store.get(txn2, "counter")  # Returns 100
store.put(txn2, "counter", 200)
store.commit(txn2)

# Transaction 3: Delete
txn3 = store.begin()
store.delete(txn3, "counter")
store.commit(txn3)
```

## Read Committed Behavior

```python
# Long-running transaction example
txn_long = store.begin()
print(store.get(txn_long, "key1"))  # Sees value: 10

# Another transaction commits a change
txn_short = store.begin()
store.put(txn_short, "key1", 20)
store.commit(txn_short)

# Long-running transaction sees the new value
print(store.get(txn_long, "key1"))  # Now sees: 20 (Read Committed!)
```

## Implementation Details

### Version Visibility

A version is visible to a transaction if:
1. The version's creating transaction is committed, OR
2. The version was created by the current transaction (read-your-writes)

### Deletion Handling

Deletions create "tombstone" versions that mark keys as deleted. The visibility rules ensure proper deletion semantics.

### Transaction States

- **ACTIVE**: Transaction in progress
- **COMMITTED**: Changes applied to main store
- **ABORTED**: Transaction rolled back

### Simplified Implementation (mvcc_store_o3.py)

The `o3` variant makes these simplifications for clarity:

- **No timestamps**: Visibility is based solely on transaction commit status
- **Simpler deletion**: Uses a `deleted` boolean flag instead of `deleted_txn_id`
- **No conflict detection**: Implements pure "last-write-wins" behavior
- **Minimal data structures**: Just transaction IDs, version chains, and a committed set
- **No optimization**: Focuses on correctness over performance

This makes it ideal for understanding MVCC fundamentals without implementation complexity.

## Testing

Run the test suites:

```bash
# Test the original implementation
uv run python -m pytest test_mvcc_store.py -v

# Test the simplified implementation
uv run python -m pytest test_mvcc_store_o3.py -v
```

Tests cover:
- Basic CRUD operations
- Transaction isolation scenarios
- Concurrent transaction handling
- Edge cases and error conditions
- Read Committed specific behaviors

Note: The simplified `o3` version has a minimal test suite focusing on core functionality.

## Known Issues

### Write-Write Conflict Detection
The current implementation does not detect write-write conflicts. The test `test_concurrent_read_modify_write` in `test_mvcc_store.py` is currently failing because it expects proper conflict detection where only one of two concurrent transactions modifying the same key should succeed.

Currently, both transactions succeed with a "last-write-wins" behavior, which can lead to lost updates. The failing test demonstrates that when T2 and T3 both read key1=100 and perform calculations, T3's commit overwrites T2's changes without detecting the conflict.

To fix this issue, the implementation needs to:
1. Add a `WriteConflictError` exception class
2. Implement conflict detection in the `commit()` method by checking if any keys being written were read at an earlier version than the current committed version
3. Abort transactions that would cause lost updates

## Limitations & Future Work

This is an **exploratory implementation** with several limitations:

1. **Single-threaded**: No actual concurrency control (no locks)
2. **No Garbage Collection**: Old versions accumulate indefinitely
3. **In-memory Only**: No persistence
4. **Simple Types**: Values are integers only
5. **No Performance Optimization**: Not optimized for high throughput
6. **No Write-Write Conflict Detection**: Currently uses last-write-wins instead of detecting conflicts (see Known Issues above)

### Choosing Between Implementations

- **Use `mvcc_store.py`** when you need:
  - Full transaction tracking with timestamps
  - Detailed version management
  - A foundation for adding conflict detection
  - More comprehensive error handling

- **Use `mvcc_store_o3.py`** when you need:
  - Minimal code to understand MVCC concepts
  - A clean proof-of-concept for teaching/learning
  - Quick prototyping without extra complexity
  - Pure demonstration of Read Committed isolation

Potential extensions:
- Add thread safety with proper locking
- Implement garbage collection for old versions
- Support additional isolation levels
- Add performance optimizations
- Implement write-write conflict detection

## Requirements

- Python 3.8+
- pytest (for testing)

## Installation

```bash
# Using uv (recommended)
uv add pytest
uv run python -m pytest test_mvcc_store.py

# Or with pip
pip install pytest
python -m pytest test_mvcc_store.py
```

## References

Based on concepts from:
- PostgreSQL MVCC implementation
- Database transaction isolation levels
- ACID properties in database systems

## License

This is exploratory code for learning purposes. Use at your own discretion.