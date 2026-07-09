"""
Template: Python optimizations for Controller-Handle architecture.

This module provides reusable building blocks for production-grade controller
subsystems: lifecycle hooks, an event bus, a circuit breaker, hot-reload
support, an enhanced controller base with metrics, and a singleton registry
wired to the event bus.

All identifiers use abstract placeholder names (DOMAIN_A_*, DOMAIN_B_*, etc.)
so the template can be adapted to any project without leaking domain
assumptions.
"""

# === Lifecycle Protocol ===

from typing import Protocol, runtime_checkable


@runtime_checkable
class HandleLifecycle(Protocol):
    """Protocol for handles that participate in lifecycle events."""

    def on_register(self) -> None:
        """Called once when the handle is registered with a controller."""
        ...

    def on_disable(self) -> None:
        """Called once when the handle is unregistered or disabled."""
        ...


# === EventBus ===

from collections import defaultdict
from typing import Callable, Any


class EventBus:
    """Lightweight publish/subscribe event bus.

    Channels are plain strings.  Handlers are called synchronously in
    subscription order.  Exceptions raised by a handler propagate to the
    caller of ``emit`` — wrap handlers if you need isolation.
    """

    def __init__(self):
        self._listeners: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, channel: str, handler: Callable) -> None:
        """Register *handler* to receive events published on *channel*."""
        self._listeners[channel].append(handler)

    def emit(self, channel: str, *args: Any, **kwargs: Any) -> None:
        """Dispatch an event to every subscriber of *channel*."""
        for handler in self._listeners.get(channel, []):
            handler(*args, **kwargs)

    def unsubscribe(self, channel: str, handler: Callable) -> None:
        """Remove *handler* from *channel* if previously subscribed."""
        if channel in self._listeners:
            self._listeners[channel] = [
                h for h in self._listeners[channel] if h != handler
            ]


# === CircuitBreaker ===

import time
from collections import deque


class CircuitBreaker:
    """Sliding-window circuit breaker for a single handle.

    States
    -----
    closed   : calls pass through; failures are counted.
    open     : after *threshold* failures within *window_sec* the breaker
               trips and stays open for *cooldown_sec*.
    half-open: once *cooldown_sec* elapses, ``is_tripped`` returns False so
               the next call is allowed through.  A success resets the
               breaker; a failure re-arms it immediately.
    """

    def __init__(self, threshold: int = 3, window_sec: int = 30, cooldown_sec: int = 60):
        self._threshold = threshold
        self._window_sec = window_sec
        self._cooldown_sec = cooldown_sec
        self._errors: deque = deque()
        self._tripped_until: float = 0.0

    def record_failure(self) -> None:
        """Record a failure and trip the breaker if the threshold is hit."""
        now = time.time()
        self._errors.append(now)
        while self._errors and now - self._errors[0] > self._window_sec:
            self._errors.popleft()
        if len(self._errors) >= self._threshold:
            self._tripped_until = now + self._cooldown_sec

    def record_success(self) -> None:
        """Clear the failure window and reset the breaker."""
        self._errors.clear()
        self._tripped_until = 0.0

    def is_tripped(self) -> bool:
        """True while the breaker is open and calls should be rejected."""
        return time.time() < self._tripped_until


# === Reloadable Protocol ===

@runtime_checkable
class Reloadable(Protocol):
    """Protocol for controllers/handles that support hot reloading."""

    def reload(self) -> None:
        """Reload configuration, caches, or dependent resources in place."""
        ...


# === HandleIds Constants ===

class HandleIds:
    """Abstract handle identifiers.

    Replace these placeholder constants with your project's real IDs.
    The grouping below is deliberately generic so the template carries no
    domain assumptions.
    """

    # --- Domain A: primary workloads ---
    DOMAIN_A_PRIMARY = "domain_a_primary"
    DOMAIN_A_SECONDARY = "domain_a_secondary"
    DOMAIN_A_FALLBACK = "domain_a_fallback"

    # --- Domain B: supporting services ---
    DOMAIN_B_PRIMARY = "domain_b_primary"
    DOMAIN_B_SECONDARY = "domain_b_secondary"

    # --- Domain C: indexing / retrieval ---
    DOMAIN_C_INDEX = "domain_c_index"
    DOMAIN_C_RETRIEVAL = "domain_c_retrieval"
    DOMAIN_C_GENERIC = "domain_c_generic"

    # --- Cross-cutting: content generation ---
    CONTENT_FORMATTER = "content_formatter"
    CONTENT_RENDERER = "content_renderer"

    # --- Cross-cutting: synchronization ---
    SYNC_FORWARD = "sync_forward"
    SYNC_REVERSE = "sync_reverse"
    SYNC_BIDIRECTIONAL = "sync_bidirectional"


# === Generic Controller base class ===

from typing import TypeVar, Generic, Dict, List, Optional
import logging

H = TypeVar("H")
logger = logging.getLogger(__name__)


class Controller(Generic[H]):
    """Minimal controller base.

    Subclass :class:`EnhancedController` instead of this class when you need
    circuit breaker integration, metrics, and lifecycle hooks.  This base is
    kept here so the registry can type-hint controllers without forcing every
    implementation to inherit the enhanced behaviour.
    """

    def __init__(self, name: str = ""):
        self._name = name or self.__class__.__name__
        self._handles: Dict[str, H] = {}

    def register(self, handle: H) -> None:
        hid = handle.get_id()  # type: ignore[attr-defined]
        if hid in self._handles:
            raise ValueError(f"{self._name}: Handle '{hid}' already registered")
        self._handles[hid] = handle

    def get_handle(self, handle_id: str) -> H:
        if handle_id not in self._handles:
            raise KeyError(f"{self._name}: Unknown handle '{handle_id}'")
        return self._handles[handle_id]

    def get_handle_ids(self) -> List[str]:
        return list(self._handles.keys())


# === EnhancedController (Lifecycle + Metrics + CircuitBreaker) ===


class EnhancedController(Generic[H]):
    """Controller with lifecycle hooks, call metrics, and circuit breaker.

    This is the recommended base for production controllers.  It tracks per
    handle call/error counts, opens a :class:`CircuitBreaker` when a handle
    starts failing, and invokes ``on_register`` / ``on_disable`` lifecycle
    callbacks on handles that implement :class:`HandleLifecycle`.
    """

    def __init__(self, name: str = ""):
        self._name = name or self.__class__.__name__
        self._handles: Dict[str, H] = {}
        self._call_counts: Dict[str, int] = {}
        self._error_counts: Dict[str, int] = {}
        self._breakers: Dict[str, CircuitBreaker] = {}

    # --- registration ------------------------------------------------

    def register(self, handle: H) -> None:
        hid = handle.get_id()  # type: ignore[attr-defined]
        if hid in self._handles:
            raise ValueError(f"{self._name}: Handle '{hid}' already registered")
        self._handles[hid] = handle
        self._breakers[hid] = CircuitBreaker()
        # Lifecycle hook
        if hasattr(handle, "on_register"):
            handle.on_register()  # type: ignore[attr-defined]
        logger.debug("%s: registered handle '%s'", self._name, hid)

    def unregister(self, handle_id: str) -> None:
        handle = self._handles.pop(handle_id, None)
        if handle is not None:
            if hasattr(handle, "on_disable"):
                handle.on_disable()  # type: ignore[attr-defined]
            self._breakers.pop(handle_id, None)
            logger.debug("%s: unregistered handle '%s'", self._name, handle_id)

    # --- lookups -----------------------------------------------------

    def get_handle(self, handle_id: str) -> H:
        if handle_id not in self._handles:
            raise KeyError(f"{self._name}: Unknown handle '{handle_id}'")
        return self._handles[handle_id]

    def has_handle(self, handle_id: str) -> bool:
        return handle_id in self._handles

    def is_handle_available(self, handle_id: str) -> bool:
        """True when the handle exists and its breaker is closed."""
        if not self.has_handle(handle_id):
            return False
        breaker = self._breakers.get(handle_id)
        if breaker and breaker.is_tripped():
            return False
        return True

    def get_handles(self) -> List[H]:
        return list(self._handles.values())

    def get_handle_ids(self) -> List[str]:
        return list(self._handles.keys())

    # --- invocation with metrics + breaker ---------------------------

    def call(self, handle_id: str, method_name: str, *args: Any, **kwargs: Any) -> Any:
        """Invoke *method_name* on *handle_id*, tracking metrics and breaker."""
        self._call_counts[handle_id] = self._call_counts.get(handle_id, 0) + 1
        handle = self.get_handle(handle_id)
        method = getattr(handle, method_name)
        try:
            result = method(*args, **kwargs)
            self._breakers[handle_id].record_success()
            return result
        except Exception:
            self._error_counts[handle_id] = self._error_counts.get(handle_id, 0) + 1
            self._breakers[handle_id].record_failure()
            raise

    def get_metrics(self) -> Dict[str, Any]:
        """Return per-handle call/error counts and current breaker state."""
        return {
            hid: {
                "calls": self._call_counts.get(hid, 0),
                "errors": self._error_counts.get(hid, 0),
                "tripped": self._breakers[hid].is_tripped() if hid in self._breakers else False,
            }
            for hid in self.get_handle_ids()
        }

    # --- capability resolution --------------------------------------

    def find_handle(self, **criteria: Any) -> Optional[H]:
        """Capability resolution: find a handle by criteria instead of ID.

        Handles that expose a ``matches(**criteria)`` method are queried; the
        first match is returned.  This decouples callers from concrete IDs.
        """
        for h in self.get_handles():
            if hasattr(h, "matches") and h.matches(**criteria):  # type: ignore
                return h
        return None


# === ControllerRegistry with EventBus ===


class ControllerRegistry:
    """Process-wide singleton registry of controllers.

    The registry owns a shared :class:`EventBus` so controllers can
    communicate without holding direct references to each other.  Obtain the
    instance via :func:`get_controller_registry`.
    """

    _instance: Optional["ControllerRegistry"] = None

    def __init__(self):
        self._controllers: Dict[str, Controller] = {}
        self._event_bus = EventBus()

    @classmethod
    def get_instance(cls) -> "ControllerRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, controller: Controller) -> None:
        cid = controller._name
        if cid in self._controllers:
            raise ValueError(f"Controller '{cid}' already registered")
        self._controllers[cid] = controller
        self._event_bus.emit("controller.registered", cid)

    def unregister(self, controller_id: str) -> None:
        if controller_id in self._controllers:
            del self._controllers[controller_id]
            self._event_bus.emit("controller.unregistered", controller_id)

    def get(self, controller_id: str) -> Controller:
        if controller_id not in self._controllers:
            raise KeyError(f"Unknown controller '{controller_id}'")
        return self._controllers[controller_id]

    def list_ids(self) -> List[str]:
        return list(self._controllers.keys())

    def get_event_bus(self) -> EventBus:
        return self._event_bus


def get_controller_registry() -> ControllerRegistry:
    """Convenience accessor for the singleton ControllerRegistry."""
    return ControllerRegistry.get_instance()


# === reload_all() for ControllerRegistry ===


def reload_all() -> None:
    """Call ``reload()`` on every registered controller that implements Reloadable."""
    reg = get_controller_registry()
    for ctrl in reg._controllers.values():
        if hasattr(ctrl, "reload"):
            ctrl.reload()
            logger.info("Reloaded controller: %s", ctrl._name)