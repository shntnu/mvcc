# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an exploratory Python implementation of a Multi-Version Concurrency Control (MVCC) key-value store with Read Committed isolation level. The project is educational in nature, designed to understand MVCC concepts and transaction isolation.

## Development Commands

### Testing
```bash
# Run all tests with verbose output
uv run python -m pytest test_mvcc_store.py -v

# Run a specific test class
uv run python -m pytest test_mvcc_store.py::TestBasicOperations -v

# Run a specific test
uv run python -m pytest test_mvcc_store.py::TestBasicOperations::test_simple_put_and_get -v
```

### Dependencies
The project uses `uv` as the package manager. Dependencies are defined in `pyproject.toml`:
- `click>=8.2.1` - CLI framework
- `pytest>=8.4.1` - Testing framework

## Architecture Overview

### Core Components

1. **MVCCStore** (`mvcc_store.py`): Main store implementation that manages:
   - `data`: Dictionary mapping keys to version chains (newest-to-oldest ordering)
   - `active_txns`: Currently active transactions
   - `_txn_counter`: Auto-incrementing transaction ID generator

2. **Transaction** (`mvcc_store.py`): Represents a database transaction with:
   - State management (ACTIVE, COMMITTED, ABORTED)
   - Write buffering via `write_set` dictionary
   - Read tracking via `read_set` (currently unused but available for future isolation levels)

3. **Version** (`mvcc_store.py`): Represents a single version of a value with:
   - `value`: The actual data (integer or None for tombstones)
   - `txn_id`: Creating transaction ID
   - `is_tombstone`: Flag for deleted versions

### Key Design Decisions

1. **Read Committed Isolation**: Transactions always see the latest committed data at read time, not a snapshot from transaction start. This is intentionally different from Snapshot Isolation.

2. **Version Visibility**: A version is visible if:
   - Its creating transaction is committed, OR
   - It was created by the current transaction (read-your-writes)

3. **Write Buffering**: All changes are buffered in the transaction's `write_set` until commit, providing atomicity.

4. **Tombstone Deletions**: Deletions create special "tombstone" versions rather than removing data, maintaining version history.

5. **Single-threaded**: No actual concurrency control or locking - this is a conceptual implementation.

## Testing Strategy

The test suite (`test_mvcc_store.py`) is organized into focused test classes:
- `TestBasicOperations`: CRUD operations and basic functionality
- `TestTransactionStates`: Transaction lifecycle and state transitions
- `TestVersionVisibility`: Version visibility rules and isolation
- `TestWriteSetBehavior`: Write buffering and read-your-writes
- `TestReadCommittedBehavior`: Specific Read Committed isolation scenarios
- `TestComplexScenarios`: Multi-transaction interaction patterns
- `TestEdgeCases`: Error conditions and boundary cases

## Important Implementation Notes

1. **No Garbage Collection**: Old versions accumulate indefinitely - this is a known limitation.

2. **Integer Values Only**: For simplicity, the store only supports integer values.

3. **In-Memory Only**: No persistence layer - all data is lost on process exit.

4. **Version Chain Ordering**: Versions are stored newest-to-oldest for optimal read performance of latest values.

5. **Transaction State Validation**: All operations check transaction state and raise appropriate errors (TransactionAbortedError, TransactionCommittedError).

## Common Development Tasks

When modifying the MVCC implementation:
1. Ensure version visibility rules remain consistent
2. Maintain proper transaction state transitions
3. Update tests for any new behaviors
4. Consider how changes affect Read Committed semantics

When adding new features:
1. Check if they require changes to version visibility logic
2. Consider impact on transaction isolation
3. Add comprehensive tests covering edge cases
4. Update this documentation if architecture changes