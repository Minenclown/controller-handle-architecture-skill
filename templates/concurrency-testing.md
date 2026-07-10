# Concurrency-Testing Template (Controller+Handle)

<!-- Python tests use EnhancedController from python_optimizations.py.
     It synchronizes handle/breaker state, metrics, and Copy-on-Write swaps.
     EventBus and ControllerRegistry remain reference implementations and need
     project-specific synchronization when shared concurrently. Java examples
     assume an equivalent thread-safe controller API. -->

Race-condition tests for Controller+Handle with shared concurrent state.
Use them whenever controller state can be read or mutated from multiple
threads, tasks, workers, or request handlers. User count is not the deciding
factor — a desktop app with workers or timers can race, while a truly
single-threaded server path may not.

See also: O4 (Circuit Breaker), O8 (Metrics/Observability),
Scaling Axes — Axis 3 (functional/concurrent access).

## What to Test

1. **Concurrent Register** — Multiple threads register handles
   simultaneously. Expected: all handles registered, no duplicate IDs,
   no lost registrations.

2. **Concurrent Get** — Multiple threads call `get_handle()`
   simultaneously. Expected: correct handle returned, no exceptions
   for valid IDs.

3. **Concurrent Metrics Increment** — Multiple threads call `call()` on
   the same handle. Expected: counter increments match exactly
   (O8 thread safety).

4. **Concurrent Circuit Breaker** — Multiple threads trigger
   `record_failure()` and `record_success()` simultaneously. Expected:
   breaker does not trip falsely on concurrent success, trips correctly
   at threshold crossing (O4).

5. **Concurrent Reload** — One thread calls `reload()` while other
   threads call `get_handle()`. Expected: no exception, no lost
   handles (S2 Copy-on-Write).

## Python Test Patterns

```python
import threading
import time
import pytest


class FakeSearchHandle:
    def __init__(self, name):
        self._name = name
    def get_id(self):
        return self._name
    def get_display_name(self):
        return self._name.title()
    def search(self, query, limit=20, **kwargs):
        return [{"id": self._name, "query": query}]


# --- 1. Concurrent Register ---

def test_concurrent_register():
    from python_optimizations import EnhancedController

    ctrl = EnhancedController("TestController")
    barrier = threading.Barrier(3)
    errors = []

    def register_and_get(name):
        barrier.wait()
        try:
            ctrl.register(FakeSearchHandle(name))
            h = ctrl.get_handle(name)
            assert h.get_id() == name
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=register_and_get, args=(f"h{i}",))
               for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Race condition errors: {errors}"
    assert len(ctrl.get_handles()) == 3


def test_concurrent_duplicate_register_allows_exactly_one():
    from python_optimizations import EnhancedController

    ctrl = EnhancedController("TestController")
    barrier = threading.Barrier(8)
    successes = []
    duplicate_errors = []
    unexpected_errors = []

    def register_same_id():
        barrier.wait()
        try:
            ctrl.register(FakeSearchHandle("same"))
            successes.append(True)
        except ValueError as exc:
            duplicate_errors.append(exc)
        except Exception as exc:
            unexpected_errors.append(exc)

    threads = [threading.Thread(target=register_same_id) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not unexpected_errors
    assert len(successes) == 1
    assert len(duplicate_errors) == 7
    assert ctrl.get_handle("same").get_id() == "same"


# --- 2. Concurrent Get ---

def test_concurrent_get():
    from python_optimizations import EnhancedController

    ctrl = EnhancedController("TestController")
    for i in range(5):
        ctrl.register(FakeSearchHandle(f"h{i}"))

    barrier = threading.Barrier(5)
    errors = []

    def get_handle(name):
        barrier.wait()
        try:
            h = ctrl.get_handle(name)
            assert h.get_id() == name
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=get_handle, args=(f"h{i}",))
               for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Race condition errors: {errors}"


# --- 3. Concurrent Metrics Increment ---
# Note: call() and get_metrics() are EnhancedController methods
# from python_optimizations.py, not in the basic Controller.

def test_concurrent_metrics_increment():
    from python_optimizations import EnhancedController

    ctrl = EnhancedController("TestController")
    ctrl.register(FakeSearchHandle("test"))
    barrier = threading.Barrier(10)

    def call_and_check():
        barrier.wait()
        ctrl.call("test", "search", "query")

    threads = [threading.Thread(target=call_and_check) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    metrics = ctrl.get_metrics()
    # EnhancedController.get_metrics() returns {handle_id: {"calls": N, "errors": N, "tripped": bool}}
    assert metrics["test"]["calls"] == 10


# --- 4. Concurrent Circuit Breaker ---

def test_concurrent_circuit_breaker():
    from python_optimizations import CircuitBreaker

    breaker = CircuitBreaker(threshold=3, window_sec=30, cooldown_sec=60)
    barrier = threading.Barrier(5)
    errors = []

    def record_failure():
        barrier.wait()
        try:
            breaker.record_failure()
        except Exception as e:
            errors.append(e)

    # 5 concurrent failures, threshold=3 → should trip
    threads = [threading.Thread(target=record_failure) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Circuit breaker race errors: {errors}"
    assert breaker.is_tripped(), "Breaker should be tripped after 3+ failures"


def test_concurrent_circuit_breaker_success():
    from python_optimizations import CircuitBreaker

    breaker = CircuitBreaker(threshold=3, window_sec=30, cooldown_sec=60)
    barrier = threading.Barrier(5)
    errors = []

    # Record 2 failures (below threshold)
    breaker.record_failure()
    breaker.record_failure()

    def record_success():
        barrier.wait()
        try:
            breaker.record_success()
        except Exception as e:
            errors.append(e)

    # 5 concurrent successes should clear the breaker
    threads = [threading.Thread(target=record_success) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Circuit breaker race errors: {errors}"
    assert not breaker.is_tripped(), "Breaker should not trip on successes"


# --- 5. Concurrent Reload (Copy-on-Write) ---

def test_concurrent_reload_and_get():
    from python_optimizations import EnhancedController

    ctrl = EnhancedController("TestController")
    ctrl.register(FakeSearchHandle("h0"))

    barrier = threading.Barrier(2)
    errors = []

    def reload_loop():
        barrier.wait()
        try:
            # Build a complete replacement map, then swap it atomically.
            ctrl.swap_handles({"h0": FakeSearchHandle("h0")})
        except Exception as e:
            errors.append(e)

    def get_loop():
        barrier.wait()
        try:
            for _ in range(500):
                h = ctrl.get_handle("h0")
                assert h.get_id() == "h0"
                time.sleep(0)  # encourage thread interleaving
        except Exception as e:
            errors.append(e)

    threads = [
        threading.Thread(target=reload_loop),
        threading.Thread(target=get_loop),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # With COW, no errors should occur — the handle is always present.
    assert not errors, f"Unexpected errors: {errors}"
```

## Java Test Patterns

```java
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.RepeatedTest;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.Collection;
import java.util.IntSummaryStatistics;
import static org.junit.jupiter.api.Assertions.*;

// FakeHandle for tests
class FakeXHandle implements XHandle {
    private final String id;
    FakeXHandle(String id) { this.id = id; }
    @Override public String getId() { return id; }
}


class ConcurrencyTest {

    // --- 1. Concurrent Register ---

    @Test
    void concurrentRegister() throws Exception {
        var ctrl = new XController(plugin);
        var latch = new CountDownLatch(1);
        var errors = new ConcurrentLinkedQueue<Throwable>();
        int threadCount = 5;

        var threads = new Thread[threadCount];
        for (int i = 0; i < threadCount; i++) {
            final int idx = i;
            threads[i] = Thread.startVirtualThread(() -> {
                try { latch.await(); } catch (InterruptedException e) { return; }
                try {
                    ctrl.registerHandle(new FakeXHandle("h" + idx));
                    var h = ctrl.getHandle("h" + idx);
                    assertEquals("h" + idx, h.getId());
                } catch (Throwable t) { errors.add(t); }
            });
        }

        latch.countDown();
        for (var t : threads) t.join();

        assertTrue(errors.isEmpty(), "Race condition errors: " + errors);
        assertEquals(threadCount, ctrl.getHandles().size());
    }


    // --- 2. Concurrent Get ---

    @Test
    void concurrentGet() throws Exception {
        var ctrl = new XController(plugin);
        int handleCount = 5;
        for (int i = 0; i < handleCount; i++) {
            ctrl.registerHandle(new FakeXHandle("h" + i));
        }

        var latch = new CountDownLatch(1);
        var errors = new ConcurrentLinkedQueue<Throwable>();

        var threads = new Thread[handleCount];
        for (int i = 0; i < handleCount; i++) {
            final int idx = i;
            threads[i] = Thread.startVirtualThread(() -> {
                try { latch.await(); } catch (InterruptedException e) { return; }
                try {
                    var h = ctrl.getHandle("h" + idx);
                    assertEquals("h" + idx, h.getId());
                } catch (Throwable t) { errors.add(t); }
            });
        }

        latch.countDown();
        for (var t : threads) t.join();

        assertTrue(errors.isEmpty(), "Race condition errors: " + errors);
    }


    // --- 3. Concurrent Metrics Increment ---

    @Test
    void concurrentMetricsIncrement() throws Exception {
        var ctrl = new XController(plugin);
        ctrl.registerHandle(new FakeXHandle("test"));

        var metrics = new ControllerMetrics();
        var latch = new CountDownLatch(1);
        int callCount = 100;

        var threads = new Thread[callCount];
        for (int i = 0; i < callCount; i++) {
            threads[i] = Thread.startVirtualThread(() -> {
                try { latch.await(); } catch (InterruptedException e) { return; }
                metrics.recordCall("test");
            });
        }

        latch.countDown();
        for (var t : threads) t.join();

        var snapshot = metrics.snapshot();
        assertEquals(callCount, snapshot.get("test")[0],
            "Call count must match concurrent calls exactly");
    }


    // --- 4. Concurrent Circuit Breaker ---

    @Test
    void concurrentCircuitBreakerTrip() throws Exception {
        var breaker = new CircuitBreaker(3, 30_000, 60_000);
        var latch = new CountDownLatch(1);
        var errors = new ConcurrentLinkedQueue<Throwable>();
        int threadCount = 5;

        var threads = new Thread[threadCount];
        for (int i = 0; i < threadCount; i++) {
            threads[i] = Thread.startVirtualThread(() -> {
                try { latch.await(); } catch (InterruptedException e) { return; }
                try { breaker.recordFailure(); }
                catch (Throwable t) { errors.add(t); }
            });
        }

        latch.countDown();
        for (var t : threads) t.join();

        assertTrue(errors.isEmpty(), "Breaker race errors: " + errors);
        assertTrue(breaker.isTripped(),
            "Breaker should trip after 3+ concurrent failures");
    }


    // --- 5. Concurrent Reload (Copy-on-Write) ---

    @RepeatedTest(5) // Flaky tests need multiple runs
    void concurrentReloadAndGet() throws Exception {
        var ctrl = new XController(plugin);
        ctrl.registerHandle(new FakeXHandle("h0"));

        var latch = new CountDownLatch(1);
        var errors = new ConcurrentLinkedQueue<Throwable>();

        Runnable reloadTask = () -> {
            try { latch.await(); } catch (InterruptedException e) { return; }
            try {
                // Copy-on-Write: build new map, atomically swap reference.
                // Readers always see a consistent map — no window where
                // the handle is briefly absent.
                var oldHandles = ctrl.getHandles(); // snapshot current
                var newHandles = new java.util.concurrent.ConcurrentHashMap<String, XHandle>();
                for (var h : oldHandles) newHandles.put(h.getId(), h);
                newHandles.put("h0", new FakeXHandle("h0")); // replacement
                // Atomic reference swap — controller must expose a swap method
                // or use AtomicReference internally for true COW.
                // NOTE: swapHandles() is not on EnhancedController or DomainController.
                // To use this pattern, add to your controller:
                //   public void swapHandles(Map<String, DomainHandle> newMap) {
                //       this.handles = newMap;
                //   }
                // Or use AtomicReference<Map<String, DomainHandle>> internally:
                //   handlesRef.set(newMap);
                ctrl.swapHandles(newHandles); // requires swapHandles() on controller
            } catch (Throwable t) { errors.add(t); }
        };

        Runnable getTask = () -> {
            try { latch.await(); } catch (InterruptedException e) { return; }
            try {
                // Slight delay so reload interleaves with gets
                Thread.sleep(1);
                var h = ctrl.getHandle("h0");
                assertEquals("h0", h.getId());
            } catch (Throwable t) { errors.add(t); }
        };

        var threads = new Thread[] {
            Thread.startVirtualThread(reloadTask),
            Thread.startVirtualThread(getTask),
        };

        latch.countDown();
        for (var t : threads) t.join();

        assertTrue(errors.isEmpty(), "Unexpected errors: " + errors);
    }
}
```

## When to Write These Tests

The deciding factor is not user count, but whether multiple threads,
tasks, workers, or request handlers access shared controller state.

| Execution Model | Concurrency Tests Needed? | Reason |
|-----------------|---------------------------|--------|
| One execution context, no background work | Usually no | No concurrent access to controller state |
| Multiple threads with shared state | Yes | Register/get/reload can interleave |
| Async tasks | When mutation can interleave across awaits or thread-pool calls | Use async-specific tests in addition to these thread tests |
| Multiple processes | Controller memory is isolated | Test external coordination/service discovery separately |

## Thread-Safety Primitives Reference

| Language | Map | Counter | Atomic Swap |
|----------|-----|---------|-------------|
| Python | `dict` + `threading.RLock` | `collections.Counter` or `Lock` | Swap under the same state lock via `swap_handles()` |
| Java | `ConcurrentHashMap` | `AtomicInteger` / `AtomicLong` | `AtomicReference<Map>` for COW |
| Rust | `DashMap` or `RwLock<HashMap>` | `AtomicUsize` | `Arc<Swap<Map>>` |
| Go | `sync.Map` | `atomic.Int64` | Swap via `atomic.Value` |

See also O4 (Circuit Breaker), O8 (Metrics), S2 (Copy-on-Write for Reload)
in SKILL.md.