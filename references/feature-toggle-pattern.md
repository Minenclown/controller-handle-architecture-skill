# Feature-Toggle via Controller-Handle

> Pattern: Each feature is independently switchable. Removing a feature
> only affects explicitly dependent functions, not the whole system.

## When to Apply

This pattern extends Controller-Handle to **feature toggling** — not just
provider dispatch. Use when:

- A codebase has optional features that should be independently enabled/disabled
- Features have different dependency chains (some need GUI, some need
  network APIs, some need hardware libraries)
- You want "Library Mode" (core only, no GUI) vs "Desktop Mode" (full
  features)
- New features should be addable without modifying existing code

This is NOT the same as the O1 Lifecycle Hooks or O6 Reload patterns —
those manage Handle instances. This manages entire **feature modules**
that may contain their own Controllers, Handles, and business logic.

## Pattern

### Feature Protocol

```python
@runtime_checkable
class Feature(HandleBase, Protocol):
    def get_id(self) -> str: ...
    def get_display_name(self) -> str: ...
    def is_available(self) -> bool: ...    # deps satisfied?
    def is_enabled(self) -> bool: ...      # config says ON?
    def enable(self) -> None: ...
    def disable(self) -> None: ...
    def get_dependencies(self) -> list[str]: ...  # feature IDs this needs
```

### FeatureController

```python
class FeatureController(Controller[Feature]):
    """Central toggle switch for all optional features."""

    def get_enabled_features(self) -> list[Feature]:
        return [f for f in self.get_handles() if f.is_enabled() and f.is_available()]

    def can_enable(self, feature_id: str) -> bool:
        """Check if a feature AND all its dependencies are available."""
        if not self.has_handle(feature_id):
            return False
        feature = self.get_handle(feature_id)
        if not feature.is_available():
            return False
        for dep_id in feature.get_dependencies():
            if not self.can_enable(dep_id):
                return False
        return True
```

### Toggle Behavior

| State | Behavior |
|-------|----------|
| Feature OFF + available | Code not loaded, no resource use |
| Feature ON + available | Code lazy-loaded, self-registers |
| Feature ON + NOT available | Graceful degradation, log warning |
| Feature OFF + dep missing | No error — feature was OFF anyway |
| Feature ON + dep missing | Error only when feature is actually used |

### Isolation Rule

No cross-references between features. If Feature A needs Feature B,
mediate through the FeatureController:

```python
# BAD — direct import between features
from app.features.feature_a import do_thing

# GOOD — via FeatureController
if feature_ctrl.has_handle("feature_a"):
    feature_a = feature_ctrl.get_handle("feature_a")
    result = feature_a.do_thing(input)
```

### GUI as Feature Toggle

The GUI itself can be a feature toggle. In "Library Mode" (embedded in
another application), the GUI framework is not imported at all. In
"Desktop Mode", the GUI feature is enabled.

### Feature Config (YAML)

```yaml
features:
  feature_a:
    enabled: true
  feature_b:
    enabled: false
  gui:
    enabled: true   # Desktop Mode
```

Default config is auto-created when the config file is missing.

## Implementation Details

### BaseFeature Class

```python
class BaseFeature:
    def __init__(self, feature_id, display_name, description,
                 dependencies=None, config_key=None):
        self._id = feature_id
        self._display_name = display_name
        self._description = description
        self._dependencies = dependencies or []
        self._config_key = config_key or f"use_{feature_id}"
        self._enabled = False

    def is_available(self) -> bool:
        return True  # Override to check deps

    def is_enabled(self) -> bool:
        return self._enabled and self.is_available()

    def enable(self) -> None:
        if not self.is_available():
            return  # graceful: no-op + warning
        if self._enabled:
            return
        self._enabled = True
        self.on_enable()

    def disable(self) -> None:
        if not self._enabled:
            return
        self.on_disable()
        self._enabled = False

    def on_enable(self) -> None: pass  # Override for init logic
    def on_disable(self) -> None: pass  # Override for cleanup
```

### Dependency-Aware Enable/Disable

```python
def enable(self, feature_id: str) -> None:
    feature = self.get_feature(feature_id)
    for dep_id in feature.get_dependencies():
        if not self.is_enabled(dep_id):
            return  # can't enable — dependency not met
    feature.enable()

def disable(self, feature_id: str) -> None:
    for other in self._features.values():
        if feature_id in other.get_dependencies() and other.is_enabled():
            return  # can't disable — dependent still active
    self.get_feature(feature_id).disable()
```

### Test Coverage

register/get, unknown→KeyError, duplicate→ValueError, unregister
(disables first), enable/disable with lifecycle hooks, enable
unavailable→no-op, enable with unmet dependency→blocked, disable with
dependent active→blocked, get_enabled/get_available lists, idempotent
init, load/save YAML config, default config creation,
is_enabled/is_available for unknown→False (not crash).

## Relationship to Main Skill Patterns

| Main Skill Pattern | Feature-Toggle Extension |
|--------------------|--------------------------|
| Controller (Registry) | FeatureController (toggle registry) |
| Handle (Strategy Interface) | Feature Protocol (toggleable lifecycle) |
| O1: Lifecycle Hooks | enable()/disable() are the lifecycle |
| O6: Unified Reload | Feature ON/OFF = subset of reload |
| O3: Capability Resolution | is_available() = capability check |
| O4: Circuit Breaker | Not needed — Feature OFF = harder than tripped breaker |

Feature-Toggle is a **higher-level application** of Controller-Handle:
instead of managing provider instances within a domain, it manages entire
feature modules that may themselves contain Controllers and Handles.