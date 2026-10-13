"""Conservative recovery preflight for interrupted artifact persistence."""

import json
import importlib.util
from pathlib import Path

from runtime.stores.local import LocalStore
_lock_path = Path(__file__).resolve().with_name("session_lock.py")
_lock_spec = importlib.util.spec_from_file_location(
    "_product_factory_session_lock",
    _lock_path,
)

if _lock_spec is None or _lock_spec.loader is None:
    raise ImportError("Cannot load Product Factory session lock")

_lock_module = importlib.util.module_from_spec(_lock_spec)
_lock_spec.loader.exec_module(_lock_module)

session_lock = _lock_module.session_lock


_integrity_path = Path(__file__).resolve().with_name("artifact_integrity.py")
_integrity_spec = importlib.util.spec_from_file_location(
    "_product_factory_artifact_integrity",
    _integrity_path,
)

if _integrity_spec is None or _integrity_spec.loader is None:
    raise ImportError("Cannot load Product Factory artifact integrity validator")

_integrity_module = importlib.util.module_from_spec(_integrity_spec)
_integrity_spec.loader.exec_module(_integrity_module)

validate_persisted_artifact = _integrity_module.validate_persisted_artifact


def recovery_preflight(factory_root, runtime_root, identity):
    """Check recovery eligibility without modifying session state."""

    required = (
        "request_id",
        "run_id",
        "work_id",
        "initiative_id",
        "session_id",
    )

    if not isinstance(identity, dict):
        raise ValueError("Execution identity must be an object")

    if any(not isinstance(identity.get(k), str) or not identity[k] for k in required):
        raise ValueError("Incomplete execution identity")

    initiative_id = identity["initiative_id"]
    session_id = identity["session_id"]

    if not all(
        value.replace("-", "").replace("_", "").isalnum()
        for value in (initiative_id, session_id)
    ):
        raise ValueError("Unsafe session identifier")

    root = Path(runtime_root)
    session_dir = root / "sessions" / initiative_id / session_id

    binding_path = session_dir / "platform-identity.json"
    state_path = session_dir / "state.json"

    if not binding_path.is_file() or not state_path.is_file():
        raise RuntimeError("Session binding or state is missing")

    binding = json.loads(binding_path.read_text())
    expected_binding = {k: identity[k] for k in required}

    if binding != expected_binding:
        raise ValueError("Platform execution identity mismatch")

    state = json.loads(state_path.read_text())

    if (
        state.get("initiative_id") != initiative_id
        or state.get("session_id") != session_id
    ):
        raise ValueError("Session state identity mismatch")

    if state.get("workflow_state") != "RUNNING":
        raise RuntimeError("Session is not in interrupted RUNNING state")

    if state.get("pending_approvals") or state.get("pending_actions"):
        raise RuntimeError("Session already has pending human actions")

    active = state.get("active_generation")

    if not isinstance(active, dict):
        raise RuntimeError("No active generation to recover")

    if active.get("failure_type") is not None:
        raise RuntimeError("Generation has a recorded failure")

    artifact_type = active.get("artifact_type")

    if not isinstance(artifact_type, str) or not artifact_type:
        raise RuntimeError("Missing active artifact type")

    if not artifact_type.replace("_", "").isalnum():
        raise RuntimeError("Unsafe artifact type")

    recorded = state.get("artifacts", {}).get(artifact_type)
    version = str(int(recorded["version"]) + 1) if recorded else "1"

    artifact_id = f"{initiative_id}-{session_id}-{artifact_type}"

    artifact_path = (
        session_dir
        / "artifacts"
        / artifact_type
        / f"{artifact_id}__v{version}.json"
    )

    if not artifact_path.is_file():
        raise RuntimeError("Expected persisted artifact is missing")

    artifact_dir = artifact_path.parent
    artifact_files = sorted(artifact_dir.glob("*.json"))

    expected_filename = artifact_path.name

    for candidate in artifact_files:
        if candidate.name == expected_filename:
            continue

        if not recorded:
            raise RuntimeError(
                "Unexpected artifact version requires manual review"
            )

        expected_previous = (
            f"{artifact_id}__v{recorded['version']}.json"
        )

        if candidate.name != expected_previous:
            raise RuntimeError(
                "Conflicting artifact file requires manual review"
            )

    if recorded:
        previous_path = artifact_dir / (
            f"{artifact_id}__v{recorded['version']}.json"
        )

        if not previous_path.is_file():
            raise RuntimeError(
                "Previously recorded artifact is missing"
            )

    artifact = json.loads(artifact_path.read_text())

    expected_fields = {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "version": version,
        "initiative_id": initiative_id,
        "session_id": session_id,
        "status": "HUMAN_REVIEW_REQUIRED",
    }

    if any(artifact.get(k) != v for k, v in expected_fields.items()):
        raise RuntimeError("Persisted artifact metadata mismatch")

    errors = validate_persisted_artifact(
        artifact_path=artifact_path,
        factory_root=factory_root,
        initiative_id=initiative_id,
        session_id=session_id,
        artifact_type=artifact_type,
        version=version,
    )

    if errors:
        raise RuntimeError(
            f"Persisted artifact integrity validation failed: {errors}"
        )

    # Verify the human-readable representation before restoring
    # an interrupted artifact to human review.
    markdown_path = artifact_path.with_suffix(".md")

    if not markdown_path.is_file():
        raise RuntimeError(
            "Persisted artifact Markdown integrity validation failed: "
            "Markdown file is missing"
        )

    store = LocalStore(
        runtime_root,
        initiative_id,
        session_id,
    )

    try:
        expected_markdown = store._markdown(artifact)
        persisted_markdown = markdown_path.read_text(
            encoding="utf-8"
        )
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        raise RuntimeError(
            "Persisted artifact Markdown integrity validation failed"
        ) from exc

    if persisted_markdown != expected_markdown:
        raise RuntimeError(
            "Persisted artifact Markdown integrity validation failed: "
            "Markdown content does not match validated JSON"
        )

    quality_review = artifact.get("quality_review")

    if (
        not isinstance(quality_review, dict)
        or quality_review.get("pass") is not True
        or quality_review.get("runtime_error")
    ):
        raise RuntimeError(
            "Artifact has not passed Product Definition quality review"
        )

    findings = quality_review.get("findings")

    if not isinstance(findings, list):
        raise RuntimeError(
            "Artifact quality-review findings are missing or invalid"
        )

    if any(
        not isinstance(finding, dict)
        or (
            finding.get("blocks_product_definition") is True
            and finding.get("severity") in ("BLOCKER", "MAJOR")
        )
        for finding in findings
    ):
        raise RuntimeError(
            "Artifact contains blocking Product Definition findings"
        )

    approval_dir = session_dir / "approvals"

    for approval_path in sorted(approval_dir.glob("*.json")):
        try:
            approval = json.loads(approval_path.read_text())
        except (OSError, ValueError) as exc:
            raise RuntimeError(
                "Unreadable approval record requires manual review"
            ) from exc

        if not isinstance(approval, dict):
            raise RuntimeError(
                "Malformed approval record requires manual review"
            )

        if (
            not approval.get("approval_id")
            or approval_path.stem != approval["approval_id"]
            or approval.get("initiative_id") != initiative_id
            or approval.get("session_id") != session_id
            or not approval.get("artifact_id")
            or not approval.get("artifact_version")
            or not approval.get("decision")
        ):
            raise RuntimeError(
                "Inconsistent approval record requires manual review"
            )

        if (
            approval["artifact_id"] == artifact_id
            and str(approval["artifact_version"]) == version
        ):
            raise RuntimeError(
                "Existing approval record requires manual review"
            )

    return {
        "eligible": True,
        "initiative_id": initiative_id,
        "session_id": session_id,
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "version": version,
        "artifact_path": str(artifact_path),
        "action": "RESTORE_HUMAN_REVIEW_CHECKPOINT",
        "state_modified": False,
    }


def recover_human_review_checkpoint(factory_root, runtime_root, identity):
    """Restore a validated interrupted artifact to human review.

    The caller must be authorized by the surrounding platform.
    All validation and state changes occur under the session lock.
    """

    if not isinstance(identity, dict):
        raise ValueError("Execution identity must be an object")

    initiative_id = identity.get("initiative_id")
    session_id = identity.get("session_id")

    if not isinstance(initiative_id, str) or not initiative_id:
        raise ValueError("Valid initiative_id is required")

    if not isinstance(session_id, str) or not session_id:
        raise ValueError("Valid session_id is required")

    with session_lock(runtime_root, initiative_id, session_id):
        assessment = recovery_preflight(
            factory_root,
            runtime_root,
            identity,
        )

        store = LocalStore(
            runtime_root,
            initiative_id,
            session_id,
        )

        state = store.load_state()

        artifact_id = assessment["artifact_id"]
        artifact_type = assessment["artifact_type"]
        version = assessment["version"]

        if state.get("workflow_state") != "RUNNING":
            raise RuntimeError(
                "Session changed before recovery reconciliation"
            )

        if state.get("pending_approvals") or state.get("pending_actions"):
            raise RuntimeError(
                "Human-review checkpoint already exists"
            )

        state.setdefault("artifacts", {})[artifact_type] = {
            "artifact_id": artifact_id,
            "version": version,
            "status": "HUMAN_REVIEW_REQUIRED",
        }

        state["pending_approvals"] = [{
            "artifact_id": artifact_id,
            "artifact_type": artifact_type,
            "version": version,
            "human_review_requested_at": store.now(),
        }]

        state["pending_actions"] = [{
            "type": "ARTIFACT_REVIEW_REQUIRED",
            "artifact_id": artifact_id,
            "artifact_type": artifact_type,
            "version": version,
        }]

        state["workflow_state"] = "PAUSED_WAITING_FOR_HUMAN"
        state["stage"] = "HUMAN_REVIEW"
        state["active_generation"] = None

        store.save_state(state)

        return {
            "recovered": True,
            "initiative_id": initiative_id,
            "session_id": session_id,
            "artifact_id": artifact_id,
            "artifact_type": artifact_type,
            "version": version,
            "workflow_state": state["workflow_state"],
            "pending_actions": state["pending_actions"],
            "model_invoked": False,
            "approval_created": False,
        }
