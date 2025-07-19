# Discovery Answers

## Q1: Will this MVCC key-value store need to support distributed operations across multiple nodes?
**Answer:** No, single process but can be multiple threads

## Q2: Should the store provide ACID transaction support beyond MVCC's isolation capabilities?
**Answer:** Yes

## Q3: Will this store need to persist data to disk for durability?
**Answer:** No

## Q4: Should the API include advanced query capabilities beyond simple key-value operations?
**Answer:** No

## Q5: Will this store need to handle extremely high throughput (>100K ops/sec)?
**Answer:** No for now, but want to keep options open for later