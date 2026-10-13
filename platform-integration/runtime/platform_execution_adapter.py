"""Platform-to-Product Factory execution adapter."""

import importlib.util
from pathlib import Path


MODULE_DIRECTORY = Path(__file__).resolve().parent


def load_module(name):
    """Load an integration module without importing the CLI."""
    path = MODULE_DIRECTORY / f"{name}.py"

    spec = importlib.util.spec_from_file_location(
        f"product_integration_{name}", path
    )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


mapping = load_module("initiative_mapping")
validation = load_module("contract_validation")
requests = load_module("execution_request")
identities = load_module("execution_identity")
sessions = load_module("session_initializer")


class PlatformExecutionAdapter:
    """Validate platform requests and initialize Product Factory sessions."""

    def __init__(self, factory_root, platform_zip, runtime_root=None, model_adapter='mock'):
        if model_adapter not in ("mock", "codex"):
            raise ValueError("Unsupported model adapter")

        self.model_adapter = model_adapter
        self.factory_root = Path(factory_root).resolve()

        self.runtime_root = (
            Path(runtime_root).resolve()
            if runtime_root is not None
            else self.factory_root / ".runtime"
        )

        self.validator = validation.PlatformContractValidator(
            platform_zip
        )

        self.registry = identities.ExecutionIdentityRegistry(
            self.runtime_root / "platform-execution-identities"
        )

        self.initializer = sessions.SessionInitializer(
            self.factory_root,
            self.runtime_root,
        )

    def initialize(self, request, initiative):
        """Initialize or retrieve the session for a platform request."""

        requests.validate_execution_request(
            request,
            self.validator,
        )

        normalized = mapping.normalize_initiative(
            request["work"]["work_type"],
            initiative,
        )

        identity, registered = self.registry.register(
            request,
            normalized["initiative"]["initiative_id"],
        )

        state, created = self.initializer.initialize(
            identity,
            normalized,
            model_adapter=self.model_adapter,
        )

        return {
            "request_id": identity["request_id"],
            "run_id": identity["run_id"],
            "work_id": identity["work_id"],
            "initiative_id": identity["initiative_id"],
            "session_id": identity["session_id"],
            "workflow_state": state["workflow_state"],
            "stage": state["stage"],
            "session_created": created,
            "identity_registered": registered,
            "required_output_count": len(
                state["required_outputs"]
            ),
        }

    def _execute_next_unlocked(self, identity):
        """Generate at most one artifact using the Product Factory."""

        from runtime.orchestrator.product import ProductOrchestrator
        from runtime.stores.local import LocalStore

        store = LocalStore(
            self.runtime_root,
            identity["initiative_id"],
            identity["session_id"],
        )

        state = store.load_state()

        binding_path = (
            store.session_root / "platform-identity.json"
        )

        import json

        binding = json.loads(binding_path.read_text())

        expected = {
            key: identity[key]
            for key in (
                "request_id",
                "run_id",
                "work_id",
                "initiative_id",
                "session_id",
            )
        }

        if binding != expected:
            raise ValueError(
                "Platform execution identity does not match session"
            )

        if state["workflow_state"] not in (
            "READY_TO_RUN",
            "RUNNING",
        ):
            return {
                "workflow_state": state["workflow_state"],
                "stage": state["stage"],
                "artifact_generated": False,
                "pending_actions": state.get(
                    "pending_actions", []
                ),
            }

        if state.get("active_generation"):
            raise RuntimeError(
                "Existing generation is active; "
                "explicit recovery is required"
            )

        orchestrator = ProductOrchestrator(
            self.factory_root,
            store,
            self._make_model_adapter(state),
        )

        artifact_type = orchestrator.next_ready(state)

        if artifact_type is None:
            return {
                "workflow_state": state["workflow_state"],
                "stage": state["stage"],
                "artifact_generated": False,
                "pending_actions": state.get(
                    "pending_actions", []
                ),
            }

        artifact = orchestrator.generate_next(state)
        updated = store.load_state()

        return {
            "workflow_state": updated["workflow_state"],
            "stage": updated["stage"],
            "artifact_generated": artifact is not None,
            "artifact_type": (
                artifact["artifact_type"]
                if artifact else None
            ),
            "artifact_version": (
                artifact["version"]
                if artifact else None
            ),
            "pending_actions": updated.get(
                "pending_actions", []
            ),
        }

    def _submit_review_unlocked(self, identity, decision, comments, actor):
        """Apply a human artifact-review decision to an existing session."""

        import json

        from runtime.orchestrator.product import ProductOrchestrator
        from runtime.stores.local import LocalStore

        allowed = {
            "APPROVED",
            "CHANGES_REQUESTED",
            "REJECTED",
        }

        if decision not in allowed:
            raise ValueError("Unsupported review decision")

        if not isinstance(actor, str) or not actor.strip():
            raise ValueError("A human reviewer identity is required")

        if decision != "APPROVED" and (
            not isinstance(comments, str) or not comments.strip()
        ):
            raise ValueError(
                "Review comments are required for changes or rejection"
            )

        store = LocalStore(
            self.runtime_root,
            identity["initiative_id"],
            identity["session_id"],
        )

        binding_path = store.session_root / "platform-identity.json"
        binding = json.loads(binding_path.read_text())

        expected = {
            key: identity[key]
            for key in (
                "request_id",
                "run_id",
                "work_id",
                "initiative_id",
                "session_id",
            )
        }

        if binding != expected:
            raise ValueError(
                "Platform execution identity does not match session"
            )

        state = store.load_state()

        if state["workflow_state"] != "PAUSED_WAITING_FOR_HUMAN":
            raise ValueError(
                "Session is not waiting for human review"
            )

        if not state.get("pending_approvals"):
            raise ValueError(
                "No artifact is pending approval"
            )

        orchestrator = ProductOrchestrator(
            self.factory_root,
            store,
            self._make_model_adapter(state),
        )

        orchestrator.decide(
            state,
            decision,
            comments,
            actor,
        )

        updated = store.load_state()

        return {
            "initiative_id": identity["initiative_id"],
            "session_id": identity["session_id"],
            "decision": decision,
            "workflow_state": updated["workflow_state"],
            "stage": updated["stage"],
            "pending_actions": updated.get(
                "pending_actions", []
            ),
        }


    def _make_model_adapter(self, state):
        """Create the configured Product Factory model adapter."""

        name = state.get("adapter")
        configured = getattr(self, "model_adapter", "mock")

        if name != configured:
            raise ValueError(
                "Configured model adapter differs from session adapter"
            )

        if name == "mock":
            from runtime.adapters.mock import MockAdapter
            return MockAdapter()

        if name == "codex":
            from runtime.adapters.codex import CodexAdapter
            return CodexAdapter()

        raise ValueError(
            f"Unsupported Product Factory model adapter: {name}"
        )

    def _lock_session(self, identity):
        """Acquire the shared Product Factory session lock."""
        locking = load_module("session_lock")
        return locking.session_lock(
            self.runtime_root,
            identity["initiative_id"],
            identity["session_id"],
        )

    def execute_next(self, identity):
        """Generate at most one artifact under an exclusive session lock."""
        with self._lock_session(identity):
            return self._execute_next_unlocked(identity)

    def submit_review(self, identity, decision, comments, actor):
        """Apply a review decision under an exclusive session lock."""
        with self._lock_session(identity):
            return self._submit_review_unlocked(
                identity, decision, comments, actor
            )
