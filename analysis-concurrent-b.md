# Concurrency Models: Tradeoff Analysis

A comparison of four major concurrency models — thread-based, event-loop, actor model, and CSP (Communicating Sequential Processes) — with concrete tradeoffs and examples.

---

## Models at a Glance

| Model | Core Abstraction | Coordination Mechanism | Representative Languages/Runtimes |
|---|---|---|---|
| **Thread-based** | OS/green thread per task | Shared memory + locks | Java, C++, Python (threading), Rust (std::thread) |
| **Event-loop** | Single thread + callbacks | Non-blocking I/O queue | Node.js, browser JavaScript, nginx |
| **Actor model** | Independent actor per entity | Message passing (mailboxes) | Erlang/Elixir, Akka (JVM), Pony |
| **CSP** | Goroutines / lightweight processes | Synchronous channels | Go, Clojure (core.async), Crystal |

---

## Tradeoff 1: Shared State vs. Isolation

**Thread-based** threads share heap memory by default, which makes passing data cheap but requires explicit synchronization to avoid data races.

**Actor model** and **CSP** prohibit shared state: data crosses boundaries only through messages or channels, eliminating entire classes of race conditions at the cost of copying or serializing data.

**Event-loop** occupies a middle ground — single-threaded execution eliminates races within the loop, but shared mutable variables are still accessible and can be corrupted across async callbacks.

### Concrete Example

A banking application tracks account balances.

- **Thread-based (Java):** Two threads call `account.withdraw()` simultaneously. Without a `synchronized` block or `ReentrantLock`, both threads read the same balance, each subtract $100, and write the result — losing one debit. Adding a lock fixes correctness but introduces contention under high load.

- **Actor model (Elixir):** Each account is an `Agent` or `GenServer` process. Withdrawals are sent as messages and processed one at a time from the mailbox. No lock is needed; the process is the serialization point. If the process crashes, the supervisor restarts it with clean state.

---

## Tradeoff 2: Throughput on CPU-Bound vs. I/O-Bound Work

**Event-loop** excels at I/O-bound workloads (network, disk) because a single thread can handle thousands of concurrent connections while waiting on the OS. However, one CPU-intensive operation blocks the entire loop, freezing all other requests.

**Thread-based** parallelism uses multiple cores natively, making it the natural fit for CPU-bound computation. The penalty is memory overhead: each OS thread typically uses 1–8 MB of stack space.

**CSP (Go)** goroutines are multiplexed onto OS threads by the runtime scheduler, giving low-memory concurrency (2 KB initial stack) that scales from I/O-bound to CPU-bound work without a model change.

### Concrete Example

A web server handles both streaming file uploads and image resizing.

- **Node.js (event-loop):** File uploads succeed easily — each chunk arrives as an event, no thread needed. But a synchronous `sharp.resize()` call on a large image blocks the loop for 200 ms, during which all other requests stall. The fix is to offload to a worker thread via `worker_threads`, partially defeating the single-threaded model.

- **Go (CSP):** Both operations use goroutines. The runtime parks the upload goroutine while waiting for network bytes and schedules the resize goroutine on a free OS thread, exploiting available CPU cores. No special offloading logic is needed.

---

## Tradeoff 3: Failure Isolation and Fault Tolerance

**Actor model** treats failure as a first-class concern: each actor is supervised, and a crash in one actor does not propagate to its siblings. Supervisors can restart, stop, or escalate based on configurable strategies.

**Thread-based** systems have no standard supervision mechanism. An uncaught exception on a thread typically terminates the thread (and in many runtimes the whole process), unless the programmer manually wraps every thread entry point in a try/catch.

**CSP** sits in between: goroutines or fibers can recover from panics locally, but there is no built-in supervision tree — libraries like `tomb` or `errgroup` in Go handle lifetime management by convention.

**Event-loop** failures in async callbacks that go unhandled emit an `unhandledRejection` event (Node.js) or silently swallow errors, making fault isolation the programmer's burden.

### Concrete Example

A distributed job queue processes payments in batches.

- **Erlang (actor model):** Each payment is processed by a short-lived actor under a `one_for_one` supervisor. If a payment actor crashes due to a malformed record, the supervisor logs the failure and restarts a fresh actor for the next job. The rest of the queue is unaffected. Erlang systems routinely achieve "nine nines" uptime this way.

- **Java thread pool:** An uncaught `NullPointerException` in a `Runnable` silently terminates the worker thread. If the pool shrinks to zero threads over time, no new jobs execute — a silent starvation bug that requires monitoring and explicit `UncaughtExceptionHandler` configuration to surface.

---

## Tradeoff 4: Backpressure and Flow Control

When a producer generates work faster than consumers can handle it, the system needs a mechanism to slow the producer (backpressure) or buffer and shed load. The models differ sharply here.

**CSP channels** are synchronous by design: a sender blocks until a receiver is ready (or a buffer fills). This natural synchronization applies backpressure automatically without extra code.

**Actor mailboxes** are asynchronous and unbounded by default. Without an explicit bounded mailbox or demand signal (as in Akka Streams), a slow consumer accumulates an ever-growing mailbox, eventually causing an out-of-memory crash.

**Thread-based** systems rely on blocking queues (`java.util.concurrent.BlockingQueue`) to propagate backpressure; getting this right requires careful capacity tuning.

**Event-loop** systems use high-watermark pausing (`readable.pause()` / `writable.cork()` in Node.js streams) to signal the producer, but the logic is non-obvious and easy to omit.

### Concrete Example

A log aggregation pipeline reads from Kafka and writes to a slow database.

- **Go (CSP):** The pipeline connects stages with buffered channels: `reader -> channel(cap=1000) -> writer`. When the channel fills, `reader` blocks on the next send, naturally slowing Kafka consumption. No additional logic needed.

- **Akka (actor model):** An unbounded `ActorRef` mailbox allows the reader actor to enqueue millions of records before the writer catches up. Memory exhausts and the JVM crashes. The fix requires switching to `Akka Streams` with explicit `Source.queue(1000, OverflowStrategy.backpressure)` — essentially bolting CSP semantics on top of the actor model.

---

## Tradeoff 5: Debugging and Observability

**Thread-based** programs produce familiar stack traces: when a deadlock or race occurs, a thread dump shows exactly which thread holds which lock, at which line. Tools like `jstack`, `gdb`, and Valgrind are mature.

**Event-loop** programs collapse all concurrency into a single call stack, so async stack traces fragment across callbacks. A promise chain five levels deep shows `anonymous` frames and a `<anonymous>` top-level, making it difficult to trace the original trigger. `async_hooks` (Node.js) and `Error.captureStackTrace` partially restore context at a performance cost.

**Actor model** programs distribute logic across many short-lived processes. Log correlation requires propagating a trace ID through every message, and observing an actor's mailbox requires instrumenting the runtime (Erlang's `:sys.trace/2` or Akka's `EventStream`).

**CSP** goroutine dumps (`SIGQUIT` in Go) show all goroutine stacks simultaneously and identify goroutines blocked on channels — which is usually the right starting point for a deadlock investigation.

### Concrete Example

A production incident: requests are timing out.

- **Node.js (event-loop):** The event loop is lagging 500 ms. `clinic.js flame` reveals a regex in a middleware that runs in O(n²) time on certain inputs. The single-threaded model makes the culprit easy to find once you have the right profiler, but the async stack traces initially obscure which HTTP handler triggered the regex.

- **Go (CSP):** Requests are timing out because all goroutines are blocked on a database channel that has no receivers. `go tool pprof` shows a goroutine profile with hundreds of goroutines in `chan send`. The channel name and source location are visible in the dump, pointing directly to the unread channel within seconds.

---

## Tradeoff 6: Composability and Modularity

**CSP channels** are values: they can be stored in variables, passed to functions, and returned from constructors. This makes it straightforward to wire concurrent components together without coupling them through a shared scheduler or registry.

**Actor model** requires actors to know each other's `ActorRef`/`PID` to communicate, introducing a registry or dependency-injection concern. Dynamic actor hierarchies (Erlang's `gproc`, Akka's `ActorSelection`) add runtime coupling that is hard to test statically.

**Event-loop** callback-based code resists composition: nesting callbacks to sequence async operations creates "callback hell." Promises and `async/await` restore linear-looking code but still compose poorly across library boundaries when one library uses callbacks and another uses promises.

**Thread-based** shared-memory composition is the most flexible but the most dangerous: any function can read or mutate global state, making module boundaries easy to violate and hard to enforce.

### Concrete Example

A CLI tool chains three async stages: fetch remote data, transform it, write to disk.

- **Go (CSP):** Each stage is a function that reads from one channel and writes to another. Composing three stages is wiring three channel pairs:
  ```go
  raw   := fetch(url)
  xform := transform(raw)
  done  := write(xform, outFile)
  <-done
  ```
  Adding a fourth stage means adding one more channel variable — no other code changes.

- **Node.js (event-loop, callback style):** Adding a fourth async step means nesting another callback inside the `write` callback, pushing the entire block one indentation level deeper and making error propagation require an additional `if (err) return cb(err)` at every layer. Refactoring to streams or `async/await` fixes the readability but requires rewriting all four stages.

---

## Summary Matrix

| Tradeoff | Thread-based | Event-loop | Actor model | CSP |
|---|---|---|---|---|
| Shared state safety | Requires locks | Safe within loop | Isolated by design | Isolated by design |
| CPU-bound throughput | Excellent | Poor (blocks loop) | Good (many processes) | Excellent (goroutines) |
| Fault isolation | Manual | Manual | Built-in supervision | Convention-based |
| Backpressure | Blocking queues | Manual signals | Manual (unbounded mailbox) | Automatic (blocking send) |
| Debuggability | Mature tools | Fragmented traces | Distributed logs | Full goroutine dumps |
| Composability | Flexible but risky | Callback hell | Registry coupling | First-class channels |

No model is universally superior. The practical choice depends on workload profile (I/O vs. CPU), fault-tolerance requirements, team familiarity, and the maturity of tooling in the target ecosystem.
