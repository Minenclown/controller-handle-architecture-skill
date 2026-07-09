# Multi-Instance Session Routing

## Problem

A web server serves multiple user instances on a single port. A global
cache holds the "default" instance path. With multiple users, they
overwrite each other's cached paths.

## Solution: Session-to-Instance Mapping

```python
import threading
from pathlib import Path
from typing import Dict, Optional

_SESSION_INSTANCES: Dict[str, dict] = {}
_SESSION_LOCK = threading.Lock()


def _register_session(session_id: str, instance_path: str) -> None:
    with _SESSION_LOCK:
        _SESSION_INSTANCES[session_id] = {
            "path": instance_path,
            "db_path": str(Path(instance_path) / "data" / "database.db"),
            "content_path": str(Path(instance_path) / "data" / "content"),
        }


def _unregister_session(session_id: str) -> None:
    with _SESSION_LOCK:
        _SESSION_INSTANCES.pop(session_id, None)


def _get_db_path(session_id: Optional[str] = None) -> Path:
    # 1. Session-based (multi-user mode)
    if session_id:
        with _SESSION_LOCK:
            info = _SESSION_INSTANCES.get(session_id)
            if info:
                return Path(info["db_path"])
    # 2. Global fallback (single-user mode)
    return Path(_get_default_instance_path() / "data" / "database.db")
```

## Login: Registry Lookup

```python
@app.post("/api/login")
async def api_login(req: LoginRequest):
    session_id = str(uuid.uuid4())
    if req.username:
        path = resolve_instance_path(req.username) or get_default_path()
        if path:
            _register_session(session_id, str(path))
    return {"session_id": session_id, "instance_path": str(path)}
```

## Endpoints: session_id as Parameter

All data endpoints accept `session_id: str = ""` and pass it to
`_get_db_path(session_id or None)`. With `session_id=""` the global
fallback applies (single-user mode). Backward compatible.

## Logout

```python
@app.post("/api/logout")
async def api_logout(session_id: str = ""):
    _unregister_session(session_id)
    return {"success": True}
```

## Thread Safety

- `_SESSION_LOCK` (`threading.Lock`) protects the mapping against
  concurrent requests. Web frameworks (FastAPI/uvicorn, Spring Boot,
  Express) run multi-threaded.
- The lock is fine-grained: only the session dict is protected, not
  the entire request pipeline.
- Session registration/unregistration is rare (login/logout), so lock
  contention is negligible.

## Controllers Remain Instance-Neutral

Controllers and handles do NOT know about sessions. They accept
`db_path` (or equivalent) as a method parameter:

```python
# Handle method — instance-neutral
def search(self, query: str, db_path: str, limit: int = 20):
    ...

# Controller convenience method — also instance-neutral
def search(self, handle_id: str, query: str, db_path: str, limit: int = 20):
    return self.get_handle(handle_id).search(query, db_path, limit)

# Web layer — resolves session to path, passes to controller
@app.get("/api/search")
async def api_search(q: str, session_id: str = ""):
    db_path = _get_db_path(session_id or None)
    return ctrl.search("primary", q, str(db_path))
```

This separation is critical: the architecture pattern stays clean
(controllers know nothing about HTTP sessions), and the web layer is
the only place that translates session → instance path.

## Fallback for Single-User Mode

When `session_id` is empty or None, `_get_db_path()` falls back to a
default instance path (e.g., from a config file or a global registry).
This allows the same codebase to serve both single-user desktop and
multi-user server deployments without changes to controllers or handles.