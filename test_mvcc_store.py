"""
Tests for MVCC Key-Value Store
"""

import pytest
from mvcc_store import (
    MVCCStore, Transaction, TxnState, Version,
    KeyNotFoundError, TransactionAbortedError, TransactionCommittedError
)


class TestBasicOperations:
    """Test basic store operations"""
    
    def test_store_initialization(self):
        """Test store can be initialized"""
        store = MVCCStore()
        assert store.data == {}
        assert store._txn_counter == 0
        assert store.active_txns == {}
    
    def test_begin_transaction(self):
        """Test transaction creation"""
        store = MVCCStore()
        txn = store.begin()
        
        assert txn.id == 1
        assert txn.begin_time == 1
        assert txn.state == TxnState.ACTIVE
        assert txn.read_set == {}
        assert txn.write_set == {}
        assert txn.id in store.active_txns
    
    def test_simple_put_and_get(self):
        """Test basic put and get operations"""
        store = MVCCStore()
        txn = store.begin()
        
        # Put a value
        store.put(txn, "key1", 100)
        
        # Should be visible in same transaction before commit
        assert store.get(txn, "key1") == 100
        
        # Commit the transaction
        store.commit(txn)
        
        # Start new transaction and verify value is visible
        txn2 = store.begin()
        assert store.get(txn2, "key1") == 100
    
    def test_get_nonexistent_key(self):
        """Test getting a key that doesn't exist"""
        store = MVCCStore()
        txn = store.begin()
        
        with pytest.raises(KeyNotFoundError, match="Key 'missing' not found"):
            store.get(txn, "missing")
    
    def test_update_existing_key(self):
        """Test updating an existing key"""
        store = MVCCStore()
        
        # First transaction: insert key
        txn1 = store.begin()
        store.put(txn1, "key1", 100)
        store.commit(txn1)
        
        # Second transaction: update key
        txn2 = store.begin()
        store.put(txn2, "key1", 200)
        assert store.get(txn2, "key1") == 200  # See own write
        store.commit(txn2)
        
        # Third transaction: verify update
        txn3 = store.begin()
        assert store.get(txn3, "key1") == 200
    
    def test_delete_key(self):
        """Test deleting a key"""
        store = MVCCStore()
        
        # Insert key
        txn1 = store.begin()
        store.put(txn1, "key1", 100)
        store.commit(txn1)
        
        # Delete key
        txn2 = store.begin()
        store.delete(txn2, "key1")
        
        # Should not be visible in same transaction after delete
        with pytest.raises(KeyNotFoundError):
            store.get(txn2, "key1")
        
        store.commit(txn2)
        
        # Should not be visible in new transaction
        txn3 = store.begin()
        with pytest.raises(KeyNotFoundError):
            store.get(txn3, "key1")
    
    def test_delete_nonexistent_key(self):
        """Test deleting a key that doesn't exist"""
        store = MVCCStore()
        txn = store.begin()
        
        with pytest.raises(KeyNotFoundError):
            store.delete(txn, "missing")
    
    def test_rollback_transaction(self):
        """Test rolling back a transaction"""
        store = MVCCStore()
        
        # Insert initial value
        txn1 = store.begin()
        store.put(txn1, "key1", 100)
        store.commit(txn1)
        
        # Start transaction that will be rolled back
        txn2 = store.begin()
        store.put(txn2, "key1", 200)
        store.put(txn2, "key2", 300)
        
        # Rollback
        store.rollback(txn2)
        assert txn2.state == TxnState.ABORTED
        assert txn2.write_set == {}
        assert txn2.id not in store.active_txns
        
        # Verify changes were not applied
        txn3 = store.begin()
        assert store.get(txn3, "key1") == 100
        with pytest.raises(KeyNotFoundError):
            store.get(txn3, "key2")


class TestTransactionStates:
    """Test transaction state management"""
    
    def test_cannot_use_committed_transaction(self):
        """Test that operations fail on committed transaction"""
        store = MVCCStore()
        txn = store.begin()
        store.put(txn, "key1", 100)
        store.commit(txn)
        
        # All operations should fail
        with pytest.raises(TransactionCommittedError):
            store.get(txn, "key1")
        
        with pytest.raises(TransactionCommittedError):
            store.put(txn, "key2", 200)
        
        with pytest.raises(TransactionCommittedError):
            store.delete(txn, "key1")
        
        with pytest.raises(TransactionCommittedError):
            store.commit(txn)
    
    def test_cannot_use_aborted_transaction(self):
        """Test that operations fail on aborted transaction"""
        store = MVCCStore()
        txn = store.begin()
        store.rollback(txn)
        
        # All operations should fail
        with pytest.raises(TransactionAbortedError):
            store.get(txn, "key1")
        
        with pytest.raises(TransactionAbortedError):
            store.put(txn, "key1", 100)
        
        with pytest.raises(TransactionAbortedError):
            store.delete(txn, "key1")
        
        with pytest.raises(TransactionAbortedError):
            store.commit(txn)
    
    def test_cannot_rollback_committed_transaction(self):
        """Test that rollback fails on committed transaction"""
        store = MVCCStore()
        txn = store.begin()
        store.commit(txn)
        
        with pytest.raises(TransactionCommittedError):
            store.rollback(txn)


class TestVersionVisibility:
    """Test version visibility and isolation"""
    
    def test_snapshot_isolation(self):
        """Test snapshot isolation behavior (despite being called Read Committed)"""
        store = MVCCStore()
        
        # T1: Insert initial value
        txn1 = store.begin()
        store.put(txn1, "key1", 100)
        store.commit(txn1)
        
        # T2: Start transaction (sees committed value)
        txn2 = store.begin()
        assert store.get(txn2, "key1") == 100
        
        # T3: Update value and commit
        txn3 = store.begin()
        store.put(txn3, "key1", 200)
        store.commit(txn3)
        
        # T2: Still sees old value (snapshot at begin time)
        assert store.get(txn2, "key1") == 100
        
        # T4: New transaction sees new value
        txn4 = store.begin()
        assert store.get(txn4, "key1") == 200
    
    def test_uncommitted_changes_not_visible(self):
        """Test that uncommitted changes are not visible to other transactions"""
        store = MVCCStore()
        
        # T1: Insert but don't commit
        txn1 = store.begin()
        store.put(txn1, "key1", 100)
        
        # T2: Should not see uncommitted change
        txn2 = store.begin()
        with pytest.raises(KeyNotFoundError):
            store.get(txn2, "key1")
        
        # T1: Commit
        store.commit(txn1)
        
        # T2: Still doesn't see it (snapshot isolation)
        with pytest.raises(KeyNotFoundError):
            store.get(txn2, "key1")
        
        # T3: New transaction sees it
        txn3 = store.begin()
        assert store.get(txn3, "key1") == 100
    
    def test_deleted_version_visibility(self):
        """Test visibility of deleted versions"""
        store = MVCCStore()
        
        # T1: Insert value
        txn1 = store.begin()
        store.put(txn1, "key1", 100)
        store.commit(txn1)
        
        # T2: Start transaction (sees value)
        txn2 = store.begin()
        assert store.get(txn2, "key1") == 100
        
        # T3: Delete value
        txn3 = store.begin()
        store.delete(txn3, "key1")
        store.commit(txn3)
        
        # T2: Still sees value (not deleted at T2's begin time)
        assert store.get(txn2, "key1") == 100
        
        # T4: New transaction doesn't see deleted value
        txn4 = store.begin()
        with pytest.raises(KeyNotFoundError):
            store.get(txn4, "key1")
    
    def test_multiple_versions(self):
        """Test handling of multiple versions of same key"""
        store = MVCCStore()
        
        # Create multiple versions
        for i in range(5):
            txn = store.begin()
            store.put(txn, "key1", i * 100)
            store.commit(txn)
        
        # Verify version chain exists
        assert len(store.data["key1"]) == 5
        
        # Latest transaction sees latest value
        txn = store.begin()
        assert store.get(txn, "key1") == 400


class TestWriteSetBehavior:
    """Test write set buffering behavior"""
    
    def test_write_set_overrides_committed_data(self):
        """Test that write set takes precedence over committed data"""
        store = MVCCStore()
        
        # Commit initial value
        txn1 = store.begin()
        store.put(txn1, "key1", 100)
        store.commit(txn1)
        
        # New transaction modifies in write set
        txn2 = store.begin()
        assert store.get(txn2, "key1") == 100  # See committed value
        store.put(txn2, "key1", 200)
        assert store.get(txn2, "key1") == 200  # See own write
        
        # Don't commit - value should not persist
        store.rollback(txn2)
        
        txn3 = store.begin()
        assert store.get(txn3, "key1") == 100  # Still see original
    
    def test_delete_in_write_set(self):
        """Test delete behavior in write set"""
        store = MVCCStore()
        
        # Create and delete in same transaction
        txn1 = store.begin()
        store.put(txn1, "key1", 100)
        store.delete(txn1, "key1")
        
        with pytest.raises(KeyNotFoundError):
            store.get(txn1, "key1")
        
        store.commit(txn1)
        
        # Verify key doesn't exist after commit
        txn2 = store.begin()
        with pytest.raises(KeyNotFoundError):
            store.get(txn2, "key1")
    
    def test_update_then_delete_in_write_set(self):
        """Test updating then deleting in same transaction"""
        store = MVCCStore()
        
        # Initial value
        txn1 = store.begin()
        store.put(txn1, "key1", 100)
        store.commit(txn1)
        
        # Update then delete
        txn2 = store.begin()
        store.put(txn2, "key1", 200)
        assert store.get(txn2, "key1") == 200
        store.delete(txn2, "key1")
        
        with pytest.raises(KeyNotFoundError):
            store.get(txn2, "key1")
        
        store.commit(txn2)
        
        # Verify deletion persisted
        txn3 = store.begin()
        with pytest.raises(KeyNotFoundError):
            store.get(txn3, "key1")


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_empty_store_operations(self):
        """Test operations on empty store"""
        store = MVCCStore()
        txn = store.begin()
        
        # Get from empty store
        with pytest.raises(KeyNotFoundError):
            store.get(txn, "any_key")
        
        # Delete from empty store
        with pytest.raises(KeyNotFoundError):
            store.delete(txn, "any_key")
        
        # Commit empty transaction
        store.commit(txn)  # Should not fail
    
    def test_large_transaction(self):
        """Test transaction with many operations"""
        store = MVCCStore()
        txn = store.begin()
        
        # Insert many keys
        for i in range(1000):
            store.put(txn, f"key{i}", i)
        
        # Verify all readable before commit
        for i in range(1000):
            assert store.get(txn, f"key{i}") == i
        
        store.commit(txn)
        
        # Verify all readable after commit
        txn2 = store.begin()
        for i in range(1000):
            assert store.get(txn2, f"key{i}") == i
    
    def test_transaction_id_increments(self):
        """Test that transaction IDs increment properly"""
        store = MVCCStore()
        
        txn_ids = []
        for _ in range(10):
            txn = store.begin()
            txn_ids.append(txn.id)
            store.commit(txn)
        
        # Verify IDs are sequential
        for i in range(1, len(txn_ids)):
            assert txn_ids[i] == txn_ids[i-1] + 1


class TestComplexScenarios:
    """Test complex multi-transaction scenarios"""
    
    def test_concurrent_updates(self):
        """Test multiple transactions updating same key"""
        store = MVCCStore()
        
        # Initial value
        txn0 = store.begin()
        store.put(txn0, "counter", 0)
        store.commit(txn0)
        
        # Start three transactions
        txn1 = store.begin()
        txn2 = store.begin()
        txn3 = store.begin()
        
        # All see initial value
        assert store.get(txn1, "counter") == 0
        assert store.get(txn2, "counter") == 0
        assert store.get(txn3, "counter") == 0
        
        # Each updates the counter
        store.put(txn1, "counter", 1)
        store.put(txn2, "counter", 2)
        store.put(txn3, "counter", 3)
        
        # Commit in order
        store.commit(txn1)
        store.commit(txn2)
        store.commit(txn3)
        
        # New transaction sees last write wins
        txn4 = store.begin()
        assert store.get(txn4, "counter") == 3
        
        # Verify version chain
        assert len(store.data["counter"]) == 4  # initial + 3 updates
    
    def test_read_write_delete_pattern(self):
        """Test complex read-write-delete patterns"""
        store = MVCCStore()
        
        # Setup initial data
        setup_txn = store.begin()
        for i in range(5):
            store.put(setup_txn, f"key{i}", i * 10)
        store.commit(setup_txn)
        
        # T1: Read all, update some
        txn1 = store.begin()
        values = [store.get(txn1, f"key{i}") for i in range(5)]
        assert values == [0, 10, 20, 30, 40]
        store.put(txn1, "key1", 100)
        store.put(txn1, "key3", 300)
        
        # T2: Delete some keys
        txn2 = store.begin()
        store.delete(txn2, "key0")
        store.delete(txn2, "key4")
        store.commit(txn2)
        
        # T1: Can still see all keys (started before deletes)
        for i in range(5):
            if i == 1:
                assert store.get(txn1, f"key{i}") == 100
            elif i == 3:
                assert store.get(txn1, f"key{i}") == 300
            else:
                assert store.get(txn1, f"key{i}") == i * 10
        
        store.commit(txn1)
        
        # T3: Sees updates and deletes
        txn3 = store.begin()
        with pytest.raises(KeyNotFoundError):
            store.get(txn3, "key0")
        assert store.get(txn3, "key1") == 100
        assert store.get(txn3, "key2") == 20
        assert store.get(txn3, "key3") == 300
        with pytest.raises(KeyNotFoundError):
            store.get(txn3, "key4")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])