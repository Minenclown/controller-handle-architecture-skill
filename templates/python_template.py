# === Controller Base (Python) ===
#
# Generic controller-handle architecture template.
# All names are abstract/generic — replace DomainController, DomainHandle,
# ConcreteDomainHandle, and ProviderEngine with your own domain concepts.
#
# WARNING: get_controller_registry() and similar global getters are for
# the COMPOSITION ROOT only. Handles must NOT call them. Use constructor
# injection for handle dependencies.

from typing import TypeVar, Generic, Dict, List, Optional, Protocol, runtime_checkable, Callable, Any
import logging

H = TypeVar("H")
logger = logging.getLogger(__name__)


class Controller(Generic[H]):
    """Generic handle registry. Type parameter H is the handle protocol."""

    def __init__(self, name: str = ""):
        self._name = name or self.__class__.__name__
        self._handles: Dict[str, H] = {}

    def register(self, handle: H) -> None:
        hid = handle.get_id()
        if hid in self._handles:
            raise ValueError(f"{self._name}: handle '{hid}' already registered")
        self._handles[hid] = handle
        logger.debug(f"{self._name}: registered handle '{hid}'")

    def get_handle(self, handle_id: str) -> H:
        if handle_id not in self._handles:
            raise KeyError(f"{self._name}: unknown handle '{handle_id}'")
        return self._handles[handle_id]

    def has_handle(self, handle_id: str) -> bool:
        return handle_id in self._handles

    def get_handles(self) -> List[H]:
        return list(self._handles.values())

    def get_handle_ids(self) -> List[str]:
        return list(self._handles.keys())

    def unregister(self, handle_id: str) -> None:
        if handle_id in self._handles:
            del self._handles[handle_id]
            logger.debug(f"{self._name}: unregistered handle '{handle_id}'")


# === HandleBase Protocol ===


@runtime_checkable
class HandleBase(Protocol):
    """Base protocol every handle must satisfy."""

    def get_id(self) -> str: ...
    # Only get_id() is part of the base contract.
    # get_display_name() is optional for UI/logging — add it to
    # domain-specific handle protocols where it's actually needed.


# === Domain-Specific Handle Protocol ===
# Only get_id() is required. get_display_name() is NOT in the protocol
# because Python Protocol methods are mandatory. If you need display names,
# use a separate optional protocol:

@runtime_checkable
class DisplayNamedHandle(Protocol):
    def get_display_name(self) -> str: ...

@runtime_checkable
class DomainHandle(HandleBase, Protocol):
    """Protocol for handles that expose a domain operation."""
    def execute(self, query: str, limit: int = 20, **kwargs) -> list[dict]: ...


# === Domain Controller ===


class DomainController(Controller[DomainHandle]):
    """Controller specialised for the generic domain handle protocol."""

    def __init__(self) -> None:
        super().__init__("DomainController")

    def execute(self, handle_id: str, query: str, limit: int = 20, **kwargs) -> list[dict]:
        return self.get_handle(handle_id).execute(query, limit, **kwargs)

    def execute_all(self, query: str, limit: int = 20, **kwargs) -> dict:
        """Run the same query across every registered handle."""
        return {h.get_id(): h.execute(query, limit, **kwargs) for h in self.get_handles()}


# === Concrete Handle (Lazy Delegation) ===
#
# The concrete handle defers importing and instantiating the heavy
# ProviderEngine until the first call.  This keeps startup fast and avoids
# requiring optional dependencies to be installed until they are actually
# needed.


class ProviderEngine:
    """Placeholder for the real engine class you supply.

    In a real application this would be imported from your provider
    package.  It is kept inline here so the template is self-contained.

    Note: The class itself is passed as a factory callable to handles.
    Remove get_instance() if you don't need a global singleton — the
    handle gets the engine via the injected factory, not via a lookup.
    """

    _instance: Optional["ProviderEngine"] = None

    @classmethod
    def get_instance(cls) -> "ProviderEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def execute(self, query: str, **kwargs) -> dict:
        # Replace with real provider logic.
        return {"query": query, "result": "stub"}


class ConcreteDomainHandle:
    """Concrete handle that lazily delegates to a ProviderEngine.

    The engine is provided via a factory callable injected at construction
    time, making the dependency explicit and testable — no global lookup."""

    def __init__(self, engine_factory: Callable[[], Any]) -> None:
        self._engine_factory = engine_factory
        self._engine: Any = None

    def _get_engine(self):
        # Lazy init via injected factory — dependency is explicit, not a global lookup
        if self._engine is None:
            self._engine = self._engine_factory()
        return self._engine

    def get_id(self) -> str:
        return "provider"

    def get_display_name(self) -> str:
        return "Provider Engine"

    def execute(self, query: str, limit: int = 20, **kwargs) -> list[dict]:
        engine = self._get_engine()
        return [engine.execute(query, limit=limit, **kwargs)]

    def is_available(self) -> bool:
        """Best-effort availability check without instantiating the engine eagerly."""
        try:
            self._get_engine()
            return True
        except Exception:
            return False


# === ControllerRegistry (Composition Root) ===


class ControllerRegistry:
    """Process-wide singleton that holds every controller."""

    _instance: Optional["ControllerRegistry"] = None

    def __init__(self) -> None:
        self._controllers: Dict[str, Controller] = {}

    @classmethod
    def get_instance(cls) -> "ControllerRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_controller(self, name: str, controller: Controller) -> None:
        if name in self._controllers:
            raise ValueError(f"Controller '{name}' already registered")
        self._controllers[name] = controller

    def get_controller(self, name: str) -> Controller:
        if name not in self._controllers:
            raise KeyError(f"Unknown controller: {name}")
        return self._controllers[name]

    def has_controller(self, name: str) -> bool:
        return name in self._controllers

    def list_controllers(self) -> list[str]:
        return list(self._controllers.keys())

    def reset(self) -> None:
        self._controllers.clear()


def get_controller_registry() -> ControllerRegistry:
    return ControllerRegistry.get_instance()


# === init_controllers() — idempotent ===

_initialized = False


def init_controllers() -> None:
    """Register all controllers and their handles.

    Safe to call multiple times; only the first call performs registration.
    """
    global _initialized
    if _initialized:
        return

    reg = get_controller_registry()
    reg.register_controller("domain", DomainController())

    _register_domain_handles(reg.get_controller("domain"))

    _initialized = True


def _register_domain_handles(ctrl: DomainController) -> None:
    # Factory injection: pass the factory callable, not a global singleton lookup.
    # The handle lazily calls engine_factory() on first use.
    ctrl.register(ConcreteDomainHandle(engine_factory=ProviderEngine))


def reset_controllers() -> None:
    """Tear down the registry and allow init_controllers() to run again."""
    global _initialized
    get_controller_registry().reset()
    _initialized = False