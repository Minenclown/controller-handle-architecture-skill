# Concurrency-Testing Template (Controller+Handle)

Race-Condition-Tests für Controller+Handle im Multi-User-Kontext.
Nur relevant für Server-Deployments (5+ gleichzeitige User).
Single-User-Desktops brauchen diese Tests nicht.

Siehe auch: O4 (Circuit Breaker), O8 (Metrics/Observability),
Skalierungs-Achsen — Achse 3 (funktional/mehr User).

## Was zu testen

1. **Concurrent Register** — Mehrere Threads registrieren gleichzeitig
   Handles. Ergebnis: alle Handles registriert, keine doppelten IDs,
   keine verlorenen Registrationen.

2. **Concurrent Get** — Mehrere Threads rufen gleichzeitig `get_handle()`
   auf. Ergebnis: korrekter Handle zurückgegeben, keine Exceptions
   bei valid IDs.

3. **Concurrent Metrics Increment** — Mehrere Threads rufen `call()` auf
   demselben Handle. Ergebnis: Counter-Inkremente stimmen exakt
   (O8 Thread-Safety).

4. **Concurrent Circuit Breaker** — Mehrere Threads triggern gleichzeitig
   `record_failure()` und `record_success()`. Ergebnis: Breaker tripped
   nicht fälschlich bei concurrent success, trippt korrekt bei
   threshold-Kreuzung (O4).

5. **Concurrent Reload** — Ein Thread ruft `reload()` während andere
   Threads `get_handle()` aufrufen. Ergebnis: keine Exception, keine
   verlorenen Handles (S2 Copy-on-Write).

## Python Test-Patterns

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
    from kb.controllers.base import Controller

    ctrl = Controller("TestController")
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


# --- 2. Concurrent Get ---

def test_concurrent_get():
    from kb.controllers.base import Controller

    ctrl = Controller("TestController")
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

def test_concurrent_metrics_increment():
    from kb.controllers.base import Controller

    ctrl = Controller("TestController")
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
    assert metrics["calls"]["test.search"] == 10


# --- 4. Concurrent Circuit Breaker ---

def test_concurrent_circuit_breaker():
    from kb.controllers.circuit_breaker import CircuitBreaker

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
    from kb.controllers.circuit_breaker import CircuitBreaker

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
    from kb.controllers.base import Controller

    ctrl = Controller("TestController")
    ctrl.register(FakeSearchHandle("h0"))

    barrier = threading.Barrier(2)
    errors = []

    def reload_loop():
        barrier.wait()
        try:
            # Simulate reload: clear and re-register
            ctrl.unregister("h0")
            ctrl.register(FakeSearchHandle("h0"))
        except Exception as e:
            errors.append(e)

    def get_loop():
        barrier.wait()
        time.sleep(0.001)  # slight delay so reload happens during gets
        try:
            h = ctrl.get_handle("h0")
            assert h.get_id() == "h0"
        except KeyError:
            pass  # expected: handle briefly unregistered during reload
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

    # No uncaught exceptions (KeyError from get is expected during reload)
    assert not errors, f"Unexpected errors: {errors}"
```

## Java Test-Patterns

```java
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.RepeatedTest;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.Collection;
import java.util.IntSummaryStatistics;
import static org.junit.jupiter.api.Assertions.*;

// FakeHandle für Tests
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
                metrics.recordCall("test.search");
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
                ctrl.unregister("h0");
                ctrl.registerHandle(new FakeXHandle("h0"));
            } catch (Throwable t) { errors.add(t); }
        };

        Runnable getTask = () -> {
            try { latch.await(); } catch (InterruptedException e) { return; }
            try {
                // Slight delay so reload interleaves with gets
                Thread.sleep(1);
                var h = ctrl.getHandle("h0");
                assertEquals("h0", h.getId());
            } catch (IllegalArgumentException e) {
                // Expected: handle briefly unregistered during reload
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

## Wann diese Tests geschrieben werden

| Deployment | Concurrency-Tests nötig? | Begründung |
|------------|--------------------------|------------|
| Single-User Desktop (Private) | Nein | GIL/Single-Thread reicht |
| Multi-User Server (Professional) | Ja | 5+ User = Race Conditions möglich |
| Gameserver (10+ gleichzeitige Spieler) | Ja | Concurrent register/get/getHandle |
| REST API mit Multi-Tenant | Ja | Session-Routing + Reload + Metrics |

## Thread-Safety-Primitives Referenz

| Sprache | Map | Counter | Atomic Swap |
|---------|-----|---------|-------------|
| Python | `dict` + `threading.Lock` | `collections.Counter` oder `Lock` | `self._handles = new_handles` (GIL-atomar für Dict-Referenz) |
| Java | `ConcurrentHashMap` | `AtomicInteger` / `AtomicLong` | `AtomicReference<Map>` für COW |
| Rust | `DashMap` oder `RwLock<HashMap>` | `AtomicUsize` | `Arc<Swap<Map>>` |
| Go | `sync.Map` | `atomic.Int64` | Wertetausch per `atomic.Value` |

Siehe auch O4 (Circuit Breaker), O8 (Metrics), S2 (Copy-on-Write für Reload)
in der SKILL.md.