# Expert Requirements Answers

## Q6: Should transaction IDs be 64-bit to avoid wraparound issues that 32-bit systems face?
**Answer:** Yes

## Q7: Should the version chain be ordered newest-to-oldest (N2O) with the head pointing to the latest version?
**Answer:** I don't know what this means so do whatever (will use default: Yes - N2O ordering)

## Q8: Should we implement automatic garbage collection for obsolete versions that no active transaction can see?
**Answer:** No for now

## Q9: Should the initial implementation support all three major isolation levels (Read Committed, Repeatable Read, Serializable)?
**Answer:** Read committed and keep open for adding more options later

## Q10: Should we use a global transaction counter with atomic operations for assigning transaction IDs?
**Answer:** Yes