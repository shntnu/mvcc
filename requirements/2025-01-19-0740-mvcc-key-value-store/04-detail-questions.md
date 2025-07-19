# Expert Requirements Questions

## Q6: Should transaction IDs be 64-bit to avoid wraparound issues that 32-bit systems face?
**Default if unknown:** Yes (64-bit avoids the 4 billion transaction limit and simplifies long-running system design)

## Q7: Should the version chain be ordered newest-to-oldest (N2O) with the head pointing to the latest version?
**Default if unknown:** Yes (N2O ordering optimizes for recent data access which is the common case)

## Q8: Should we implement automatic garbage collection for obsolete versions that no active transaction can see?
**Default if unknown:** Yes (prevents unbounded memory growth and maintains performance)

## Q9: Should the initial implementation support all three major isolation levels (Read Committed, Repeatable Read, Serializable)?
**Default if unknown:** No (start with Snapshot Isolation/Repeatable Read as it's the most commonly used and simpler to implement correctly)

## Q10: Should we use a global transaction counter with atomic operations for assigning transaction IDs?
**Default if unknown:** Yes (provides simple, correct ordering and is standard practice for in-memory stores)