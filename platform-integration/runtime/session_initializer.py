"""Safely initialize or retrieve Product Factory sessions."""

import fcntl
import json
import os
from pathlib import Path

from runtime.adapters.mock import MockAdapter
from runtime.orchestrator.product import ProductOrchestrator
from runtime.stores.local import LocalStore


class SessionInitializer:
    """Coordinate session initialization without overwriting existing state."""

    def __init__(self, factory_root, runtime_root=None):
        self.factory_root = Path(factory_root).resolve()
        self.runtime_root = (
            Path(runtime_root).resolve()
            if runtime_root is not None
            else self.factory_root / ".runtime"
        )

    def initialize(self, identity, normalized_initiative, model_adapter='mock'):
        """Return (state, created) for a registered platform execution."""
        if model_adapter not in ("mock", "codex"):
            raise ValueError("Unsupported model adapter")

        initiative_id = identity["initiative_id"]
        session_id = identity["session_id"]

        if normalized_initiative["initiative"]["initiative_id"] != initiative_id:
            raise ValueError("Initiative ID does not match execution identity")

        if normalized_initiative["initiative"]["development_context"] not in (
            "PRODUCT_CREATION",
            "PRODUCT_EVOLUTION",
        ):
            raise ValueError("Unsupported development context")

        # Serialize initialization across cooperating local processes.
        lock_dir = self.runtime_root / "integration-locks"
        lock_dir.mkdir(parents=True, exist_ok=True)

        import hashlib

        lock_key = hashlib.sha256(
            f"{initiative_id}:{session_id}".encode("utf-8")
        ).hexdigest()

        lock_path = lock_dir / f"{lock_key}.lock"

        with lock_path.open("a+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)

            try:
                store = LocalStore(
                    self.runtime_root,
                    initiative_id,
                    session_id,
                )

                state_path = store.session_root / "state.json"
                binding_path = store.session_root / "platform-identity.json"

                expected_binding = {
                    "request_id": identity["request_id"],
                    "run_id": identity["run_id"],
                    "work_id": identity["work_id"],
                    "initiative_id": initiative_id,
                    "session_id": session_id,
                }

                if state_path.exists():
                    if not binding_path.exists():
                        raise RuntimeError(
                            "Existing session has no platform identity binding; "
                            "manual recovery is required"
                        )

                    binding = json.loads(binding_path.read_text())

                    if binding != expected_binding:
                        raise ValueError(
                            "Existing session belongs to a different "
                            "platform execution"
                        )

                    state = json.loads(state_path.read_text())

                    if (
                        state.get("initiative_id") != initiative_id
                        or state.get("session_id") != session_id
                    ):
                        raise ValueError(
                            "Existing session identity does not match request"
                        )

                    if state.get("adapter") != model_adapter:
                        raise ValueError(
                            "Existing session uses a different model adapter"
                        )

                    if state.get("initiative") != normalized_initiative["initiative"]:
                        raise ValueError(
                            "Existing session initiative differs from request"
                        )

                    return state, False

                store.session_root.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                if model_adapter == "mock":
                    adapter = MockAdapter()
                else:
                    from runtime.adapters.codex import CodexAdapter
                    adapter = CodexAdapter()

                # Reserve the session for exactly one platform execution.
                # Exclusive creation prevents replacing an existing binding.
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
                try:
                    fd = os.open(binding_path, flags, 0o600)
                except FileExistsError as exc:
                    raise RuntimeError(
                        "Session binding already exists without session "
                        "state; manual recovery is required"
                    ) from exc

                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(expected_binding, handle, indent=2)
                    handle.flush()
                    os.fsync(handle.fileno())

                orchestrator = ProductOrchestrator(
                    self.factory_root,
                    store,
                    adapter,
                )

                state = orchestrator.start(
                    normalized_initiative,
                    session_id,
                    model_adapter,
                )

                return state, True

            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
