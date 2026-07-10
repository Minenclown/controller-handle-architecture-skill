// REFERENCE SNIPPETS — not a compilable Java source file.
// Split each type into its own file and adapt placeholders.

// === Lifecycle Interface ===

public interface HandleLifecycle {
    void onRegister();   // Setup, load config, initialize resources
    void onDisable();    // Cleanup, close connections, persist state
}

// === EventBus ===

import java.util.*;
import java.util.function.Consumer;

public class EventBus {
    private final Map<String, List<Consumer<Object[]>>> listeners = new HashMap<>();

    public void subscribe(String channel, Consumer<Object[]> listener) {
        listeners.computeIfAbsent(channel, k -> new ArrayList<>()).add(listener);
    }

    public void emit(String channel, Object... data) {
        for (Consumer<Object[]> l : listeners.getOrDefault(channel, new ArrayList<>())) {
            l.accept(data);
        }
    }
}

// === CircuitBreaker ===

import java.util.*;

public class CircuitBreaker {
    private final int threshold;
    private final long windowMs;
    private final long cooldownMs;
    private final Deque<Long> errors = new ArrayDeque<>();
    private long trippedUntil = 0;

    public CircuitBreaker(int threshold, long windowMs, long cooldownMs) {
        this.threshold = threshold;
        this.windowMs = windowMs;
        this.cooldownMs = cooldownMs;
    }

    public synchronized void recordFailure() {
        long now = System.currentTimeMillis();
        errors.addLast(now);
        while (!errors.isEmpty() && now - errors.peekFirst() > windowMs) {
            errors.pollFirst();
        }
        if (errors.size() >= threshold) {
            trippedUntil = now + cooldownMs;
        }
    }

    public synchronized void recordSuccess() {
        errors.clear();
        trippedUntil = 0;
    }

    public synchronized boolean isTripped() {
        return System.currentTimeMillis() < trippedUntil;
    }
}

// === Reloadable Interface ===

public interface Reloadable {
    void reload();
}

// === HandleIds Constants ===

public final class HandleIds {
    // Domain A — primary feature group
    public static final String DOMAIN_A_PRIMARY = "domain_a_primary";
    public static final String DOMAIN_A_SECONDARY = "domain_a_secondary";
    // Domain B — secondary feature group
    public static final String DOMAIN_B_ALPHA = "domain_b_alpha";
    public static final String DOMAIN_B_BETA = "domain_b_beta";
    // Domain C — utility group
    public static final String DOMAIN_C_UTILITY = "domain_c_utility";
    public static final String DOMAIN_C_SUPPORT = "domain_c_support";
    // Domain D — infrastructure group
    public static final String DOMAIN_D_INFRA = "domain_d_infra";
    public static final String DOMAIN_D_AUX = "domain_d_aux";
    // Domain E — optional feature group
    public static final String DOMAIN_E_OPTIONAL = "domain_e_optional";
    public static final String DOMAIN_E_EXTRAS = "domain_e_extras";
    // Domain F — data / persistence group
    public static final String DOMAIN_F_STORE = "domain_f_store";
    public static final String DOMAIN_F_CACHE = "domain_f_cache";
    // Domain G — integration / external group
    public static final String DOMAIN_G_EXTERNAL = "domain_g_external";
    public static final String DOMAIN_G_GATEWAY = "domain_g_gateway";
    // Domain H — analytics / reporting group
    public static final String DOMAIN_H_METRICS = "domain_h_metrics";
    public static final String DOMAIN_H_REPORTS = "domain_h_reports";

    private HandleIds() {}
}

// === ControllerMetrics ===

import java.util.*;
import java.util.concurrent.*;

public class ControllerMetrics {
    private final Map<String, Long> callCounts = new ConcurrentHashMap<>();
    private final Map<String, Long> errorCounts = new ConcurrentHashMap<>();

    public void recordCall(String handleId) {
        callCounts.merge(handleId, 1L, Long::sum);
    }

    public void recordError(String handleId) {
        errorCounts.merge(handleId, 1L, Long::sum);
    }

    public Map<String, long[]> snapshot() {
        Map<String, long[]> result = new LinkedHashMap<>();
        for (String id : callCounts.keySet()) {
            result.put(id, new long[]{callCounts.get(id), errorCounts.getOrDefault(id, 0L)});
        }
        return result;
    }
}

// === EnhancedController with Lifecycle + Metrics Integration ===

public abstract class EnhancedController implements Reloadable {
    protected final Application plugin;
    protected final Map<String, DomainHandle> handles = new LinkedHashMap<>();
    protected final ControllerMetrics metrics = new ControllerMetrics();
    protected final Map<String, CircuitBreaker> breakers = new HashMap<>();

    public void registerHandle(DomainHandle handle) {
        String id = handle.getId();
        if (handles.containsKey(id)) {
            throw new IllegalArgumentException("Handle already registered: " + id);
        }
        handles.put(id, handle);
        if (handle instanceof HandleLifecycle) {
            ((HandleLifecycle) handle).onRegister();
        }
        breakers.put(handle.getId(), new CircuitBreaker(3, 30000, 60000));
    }

    public void unregisterHandle(String id) {
        DomainHandle handle = handles.remove(id);
        if (handle instanceof HandleLifecycle) {
            ((HandleLifecycle) handle).onDisable();
        }
        breakers.remove(id);
    }

    public DomainHandle getHandle(String id) {
        DomainHandle handle = handles.get(id);
        if (handle == null) {
            throw new IllegalArgumentException("Unknown handle: " + id);
        }
        return handle;
    }

    public boolean isHandleAvailable(String id) {
        if (!handles.containsKey(id)) return false;
        CircuitBreaker breaker = breakers.get(id);
        return breaker == null || !breaker.isTripped();
    }

    public ControllerMetrics getMetrics() { return metrics; }
}