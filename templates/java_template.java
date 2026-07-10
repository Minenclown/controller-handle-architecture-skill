// === Controller-Handle-Interface Architecture — Java Template ===
// Generic, domain-agnostic reference implementation.
// Replace DomainController / DomainHandle / ConcreteDomainHandle with your
// own domain-specific names (e.g. UserController, UserHandle, …).
// NOTE: In real Java projects, split each public type into its own file.

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

// ---------------------------------------------------------------------------
// 1. Controller
//    Holds a registry of handles keyed by a string id. A LinkedHashMap is used
//    so that iteration order matches registration order (important when the
//    order of handles has semantic meaning — e.g. UI tabs, pipeline stages).
// ---------------------------------------------------------------------------

public class DomainController {

    private final Map<String, DomainHandle> handles = new LinkedHashMap<>();

    public DomainController() {
    }

    /** Register a handle. Throws on duplicate ids — no silent overwrite. */
    public void registerHandle(DomainHandle handle) {
        String id = handle.getId();
        if (handles.containsKey(id)) {
            throw new IllegalArgumentException("Handle already registered: " + id);
        }
        handles.put(id, handle);
    }

    /** Look up a handle by id; throws if the id is not registered. */
    public DomainHandle getHandle(String id) {
        DomainHandle handle = handles.get(id);
        if (handle == null) {
            throw new IllegalArgumentException("Unknown handle: " + id);
        }
        return handle;
    }

    /** True when a handle with the given id is registered. */
    public boolean hasHandle(String id) {
        return handles.containsKey(id);
    }

    /** All registered handles, in registration order. */
    public List<DomainHandle> getHandles() {
        return new ArrayList<>(handles.values());
    }

    /** Remove a handle by id. Throws if not registered. */
    public void unregisterHandle(String id) {
        if (handles.remove(id) == null) {
            throw new IllegalArgumentException("Unknown handle: " + id);
        }
    }
}

// ---------------------------------------------------------------------------
// 2. Handle Interface
//    Every handle exposes at minimum a stable string id. Add domain-specific
//    method signatures here — e.g. execute(), render(), validate(), …
// ---------------------------------------------------------------------------

public interface DomainHandle {
    String getId();
    // Add domain-specific methods here, e.g.:
    // void execute(Context ctx);
    // Result process(Input input);
}

// ---------------------------------------------------------------------------
// 3. Concrete Handle (ExistingService-Wrapping)
//    A concrete handle typically wraps an existing service/manager and
//    delegates domain operations to it. The handle adapts the service's API to
//    the DomainHandle contract.
// ---------------------------------------------------------------------------

public class ConcreteDomainHandle implements DomainHandle {

    private final ExistingService service;

    public ConcreteDomainHandle(ExistingService service) {
        this.service = service;
    }

    @Override
    public String getId() {
        return "concrete_domain_id";
    }

    // Delegates to the wrapped service, or implements the operation directly.
    // Example:
    // public void execute(Context ctx) {
    //     service.doWork(ctx);
    // }
}

// ---------------------------------------------------------------------------
// 4. Composition Root
//    The Application class wires controllers, handles, and services together.
//    initControllers() is the single place where the object graph is built.
// ---------------------------------------------------------------------------

public class Application {

    private DomainController domainController;
    private boolean controllersInitialized = false;

    // Reference to an existing service that handles will wrap.
    private final ExistingService existingService = new ExistingService();

    /** Build and wire all controllers and their handles. Idempotent. */
    public void initControllers() {
        if (controllersInitialized) return;

        this.domainController = new DomainController();
        this.domainController.registerHandle(
            new ConcreteDomainHandle(existingService)
        );
        // Register additional handles as needed:
        // this.domainController.registerHandle(new AnotherDomainHandle(otherService));

        controllersInitialized = true;
    }

    /** Public access to the controller for consumers. */
    public DomainController getDomainController() {
        return domainController;
    }
}