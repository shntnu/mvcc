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
```go
// Core version structure
type Version struct {
    Value        interface{}
    CreatedTxnID uint64
    DeletedTxnID uint64  // 0 means not deleted
    Timestamp    uint64
}

// Main store structure
type MVCCStore struct {
    data        map[string][]*Version  // Key -> version chain
    txnCounter  atomic.Uint64         // Global transaction counter
    activeTxns  sync.Map              // Active transactions
    mu          sync.RWMutex          // For data protection
}

// Transaction structure
type Transaction struct {
    ID          uint64
    BeginTime   uint64
    State       TxnState  // Active, Committed, Aborted
    ReadSet     map[string]uint64  // Keys read -> version
    WriteSet    map[string]*Version // Keys written
}
```

### 2. Concurrency
- Thread-safe for multiple concurrent readers and writers
- Use atomic operations for transaction ID generation
- Fine-grained locking or lock-free algorithms where possible
- No global locks for read operations

### 3. Memory Management
- Version chains stored as slices for each key
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
```go
func (s *MVCCStore) nextTxnID() uint64 {
    return s.txnCounter.Add(1)
}
```

### 2. Version Visibility Check
```go
func (v *Version) isVisibleTo(txn *Transaction) bool {
    // Version is visible if:
    // 1. Created before or by this transaction
    // 2. Not deleted, or deleted after this transaction started
    return v.CreatedTxnID <= txn.BeginTime && 
           (v.DeletedTxnID == 0 || v.DeletedTxnID > txn.BeginTime)
}
```

### 3. Finding Visible Version
```go
func (s *MVCCStore) findVersion(key string, txn *Transaction) *Version {
    versions := s.data[key]
    // Iterate newest to oldest (N2O order)
    for i := len(versions) - 1; i >= 0; i-- {
        if versions[i].isVisibleTo(txn) {
            return versions[i]
        }
    }
    return nil
}
```

### 4. Commit Process
1. Validate transaction (no conflicts for Read Committed)
2. Get commit timestamp
3. Apply all writes to main store
4. Mark transaction as committed
5. Make changes visible to other transactions

## API Design

```go
// Store interface
type Store interface {
    Begin() *Transaction
    Get(txn *Transaction, key string) (interface{}, error)
    Put(txn *Transaction, key string, value interface{}) error
    Delete(txn *Transaction, key string) error
    Commit(txn *Transaction) error
    Rollback(txn *Transaction) error
}

// Error types
var (
    ErrKeyNotFound = errors.New("key not found")
    ErrTxnAborted  = errors.New("transaction aborted")
    ErrTxnCommitted = errors.New("transaction already committed")
)
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

1. Values can be any type (interface{})
2. Keys are strings
3. No persistence required
4. No size limits on values
5. Transaction IDs never wrap (64-bit)
6. Version chains ordered N2O as discussed
7. No automatic garbage collection initially