# Discovery Questions

## Q1: Will this MVCC key-value store need to support distributed operations across multiple nodes?
**Default if unknown:** No (starting with single-node implementation is simpler and more appropriate for an in-memory store)

## Q2: Should the store provide ACID transaction support beyond MVCC's isolation capabilities?
**Default if unknown:** Yes (MVCC typically works in conjunction with transaction support for consistency)

## Q3: Will this store need to persist data to disk for durability?
**Default if unknown:** No (specified as in-memory store, persistence can be added later if needed)

## Q4: Should the API include advanced query capabilities beyond simple key-value operations?
**Default if unknown:** No (keeping it as a pure key-value store with get/put/delete operations)

## Q5: Will this store need to handle extremely high throughput (>100K ops/sec)?
**Default if unknown:** Yes (in-memory stores are typically used for high-performance scenarios)