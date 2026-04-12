# Locking Strategies Analysis: Optimistic vs. Pessimistic Locking

A comparison of optimistic and pessimistic locking strategies for distributed systems, covering key tradeoffs with concrete examples.

---

## Background

When multiple processes or nodes need to read and modify shared data concurrently, a locking strategy determines how conflicts are prevented or resolved.

- **Pessimistic locking** assumes conflicts are likely. It acquires an exclusive lock before reading or modifying data, blocking other actors until the lock is released.
- **Optimistic locking** assumes conflicts are rare. It reads data without locking, tracks a version identifier, and detects conflicts at write time — retrying or aborting if the data changed.

---

## Tradeoff 1: Throughput Under Low Contention

| Dimension | Optimistic | Pessimistic |
|-----------|-----------|-------------|
| Lock overhead | None during read | Lock acquired on every read |
| Throughput | High | Reduced by serialization |

**Analysis.** Optimistic locking pays no coordination cost unless a conflict actually occurs. In read-heavy workloads where writes are infrequent, this yields significantly higher throughput.

**Concrete example.** An e-commerce product catalog where hundreds of users browse items simultaneously but only a handful of admins update prices. Under pessimistic locking, every catalog read would contend on the same row-level lock. With optimistic locking (using a `version` column), reads are lock-free and only the rare admin update triggers a conflict check. Benchmark measurements from systems like PostgreSQL have shown 2–5× throughput improvements on read-dominated workloads by switching from `SELECT FOR UPDATE` to version-based conflict detection.

---

## Tradeoff 2: Conflict Cost Under High Contention

| Dimension | Optimistic | Pessimistic |
|-----------|-----------|-------------|
| Wasted work | High (all work discarded on conflict) | None (blocked work never starts) |
| Retry storms | Possible | Impossible — waiters queue |

**Analysis.** Optimistic locking performs all processing work before detecting a conflict. If a conflict is detected, every step since the initial read is discarded and must be repeated. Under heavy write contention this can cause cascading retries that degrade the system worse than blocking would.

**Concrete example.** A flash-sale inventory counter where thousands of buyers simultaneously try to decrement the same `stock_count` row. With optimistic locking, nearly every transaction reads version N, does its work, then fails the version check because another transaction already committed. The system enters a retry storm. With pessimistic locking (`SELECT FOR UPDATE`), transactions queue at the database and execute serially — slower per-request, but the total throughput is predictable and no work is discarded.

---

## Tradeoff 3: Deadlock Risk

| Dimension | Optimistic | Pessimistic |
|-----------|-----------|-------------|
| Deadlock possible | No | Yes, if lock ordering is not enforced |
| Detection/recovery overhead | N/A | Requires timeout or cycle detection |

**Analysis.** Pessimistic locking can deadlock when two transactions each hold a lock the other needs. Databases must detect cycles or rely on timeouts, adding latency and recovery complexity. Optimistic locking never acquires locks ahead of time, so deadlocks are structurally impossible.

**Concrete example.** A banking system transfers funds between accounts A and B. Transaction T1 locks account A then tries to lock B; Transaction T2 locks account B then tries to lock A. Both block indefinitely — a classic deadlock. The fix requires consistent lock ordering (always lock the lower account ID first), which is easy to miss. An optimistic approach would instead read both balances, compute the new values, then attempt a conditional update: `UPDATE accounts SET balance = ... WHERE id = A AND balance = <expected>`. No deadlock can occur because no locks are held during computation.

---

## Tradeoff 4: Latency for Long-Running Transactions

| Dimension | Optimistic | Pessimistic |
|-----------|-----------|-------------|
| Lock hold duration | Zero | Entire transaction duration |
| Impact on other readers/writers | None until commit | Blocked for full duration |

**Analysis.** Pessimistic locking holds locks for the entire transaction lifetime. A slow transaction — one involving external API calls, user interaction, or heavy computation — starves other actors for the full duration. Optimistic locking holds no locks during computation, so other transactions proceed freely; only the commit itself is serialized.

**Concrete example.** A document editing workflow where a user opens a record, reads its content, edits it in a rich-text editor (15–30 seconds of user think time), then saves. With pessimistic locking, the row lock is held for the entire editing session, blocking other editors from even reading the document. With optimistic locking, all users read freely; only on save does the system check whether anyone else committed a change since the user opened the document. If so, a merge conflict UI is shown — the same approach used by Google Docs and most modern collaborative editors.

---

## Tradeoff 5: Simplicity of Implementation

| Dimension | Optimistic | Pessimistic |
|-----------|-----------|-------------|
| Schema changes required | Yes (version/timestamp column) | No |
| Application retry logic | Required | Not required |
| Distributed coordination | Stateless | Requires distributed lock manager |

**Analysis.** Pessimistic locking leverages the database's built-in lock machinery and requires no application-level retry logic. Optimistic locking requires a version column, correct propagation of that version through every code path, and retry loops wherever writes occur. In distributed environments, pessimistic locking is harder because row-level locks don't span services — requiring a distributed lock manager (e.g., Redis `SET NX`, ZooKeeper, etcd), which introduces its own failure modes.

**Concrete example.** A microservices order-processing pipeline where Order Service and Inventory Service must both update state atomically. Pessimistic locking across services would require a distributed lock in Redis: `SET lock:order:{id} 1 NX EX 30`. This lock must handle expiry, renewal, and crash recovery (what happens if the holder dies mid-transaction?). Optimistic locking instead versions each service's record independently, detects conflicts at commit time, and relies on idempotent compensating transactions (sagas) to handle rollback — more code upfront, but no single lock manager becomes a bottleneck or single point of failure.

---

## Tradeoff 6: Suitability for Distributed and Cloud-Native Systems

| Dimension | Optimistic | Pessimistic |
|-----------|-----------|-------------|
| Works across stateless replicas | Yes | Requires shared lock store |
| Network partition tolerance | Continues (conflict detected at sync) | May block indefinitely |
| Horizontal scalability | Straightforward | Lock manager becomes bottleneck |

**Analysis.** Modern cloud architectures run many stateless replicas behind load balancers. Pessimistic locking requires all replicas to consult the same lock manager, creating a distributed coordination bottleneck. Optimistic locking uses version vectors or timestamps that travel with the data itself, requiring no shared lock state.

**Concrete example.** A globally distributed user-profile service deployed across AWS regions us-east-1 and eu-west-1. With pessimistic locking, a write lock on a profile record in us-east-1 must be visible to eu-west-1 before that region can update the same record — adding cross-region latency (50–150 ms) to every write and making the lock manager a global bottleneck. Systems like Amazon DynamoDB and Google Spanner instead use optimistic concurrency (conditional writes with `ConditionExpression` / `@Version`) that scales horizontally without a central lock service.

---

## Summary Matrix

| Tradeoff | Winner Under Low Contention | Winner Under High Contention |
|---|---|---|
| Throughput | Optimistic | Pessimistic |
| Conflict cost / wasted work | Optimistic | Pessimistic |
| Deadlock risk | Optimistic | Optimistic |
| Long-running transaction impact | Optimistic | Optimistic |
| Implementation simplicity | Pessimistic | Pessimistic |
| Distributed/cloud scalability | Optimistic | Optimistic |

**General guidance:**
- Default to **optimistic locking** for read-heavy, low-contention, distributed, or long-running workflows.
- Prefer **pessimistic locking** for high-contention write-heavy scenarios, short transactions, or when retry storms are unacceptable.
- Many production systems use **hybrid approaches**: optimistic locking at the application layer with selective pessimistic locks (`SELECT FOR UPDATE SKIP LOCKED`) for specific hot-row scenarios like queue processing.
