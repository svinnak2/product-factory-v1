"""Read-only recovery assessment for Product Factory sessions."""

import fcntl
import hashlib
import json
from pathlib import Path

from importlib.util import module_from_spec, spec_from_file_location

def _load_integrity_validator():
    module_path = Path(__file__).with_name('artifact_integrity.py')
    spec = spec_from_file_location('product_artifact_integrity', module_path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_persisted_artifact


class ProductRecoveryAssessor:
    """Inspect session persistence without changing workflow state."""

    def __init__(self, runtime_root, factory_root=None):
        self.runtime_root = Path(runtime_root)
        self.factory_root = (
            Path(factory_root) if factory_root is not None
            else Path(__file__).resolve().parents[2]
        )

    def assess(self, initiative_id, session_id):
        session_root = (
            self.runtime_root
            / "sessions"
            / initiative_id
            / session_id
        )

        state_path = session_root / "state.json"

        if not state_path.is_file():
            return {
                "classification": "MISSING_STATE",
                "safe_to_execute": False,
                "requires_manual_review": True,
            }

        state = json.loads(state_path.read_text())

        workflow_state = state.get("workflow_state")
        active = state.get("active_generation")
        pending = state.get("pending_approvals", [])

        result = {
            "initiative_id": initiative_id,
            "session_id": session_id,
            "workflow_state": workflow_state,
            "active_generation": active,
            "pending_approval_count": len(pending),
            "safe_to_execute": False,
            "requires_manual_review": False,
        }

        if pending or workflow_state == "PAUSED_WAITING_FOR_HUMAN":
            result["classification"] = "WAITING_FOR_HUMAN"
            return result

        if workflow_state == "PAUSED_BLOCKED":
            result["classification"] = "BLOCKED_REQUIRES_RETRY"
            result["requires_manual_review"] = True
            return result

        if active:
            lock_directory = self.runtime_root / "integration-locks"
            lock_directory.mkdir(parents=True, exist_ok=True)

            lock_key = hashlib.sha256(
                f"{initiative_id}:{session_id}".encode("utf-8")
            ).hexdigest()

            lock_path = lock_directory / f"{lock_key}.lock"

            with lock_path.open("a+b") as lock_file:
                try:
                    fcntl.flock(
                        lock_file.fileno(),
                        fcntl.LOCK_EX | fcntl.LOCK_NB,
                    )
                except BlockingIOError:
                    result["classification"] = "EXECUTION_IN_PROGRESS"
                    return result
                else:
                    fcntl.flock(
                        lock_file.fileno(),
                        fcntl.LOCK_UN,
                    )

            artifact_type = active.get("artifact_type")
            result["artifact_type"] = artifact_type

            if not artifact_type:
                result["classification"] = "UNKNOWN_ACTIVE_GENERATION"
                result["requires_manual_review"] = True
                return result

            artifact_dir = (
                session_root / "artifacts" / artifact_type
            )

            artifact_files = sorted(
                artifact_dir.glob("*.json")
            ) if artifact_dir.exists() else []

            result["persisted_artifact_count"] = len(artifact_files)

            recorded = state.get("artifacts", {}).get(
                artifact_type, {}
            )
            recorded_version = recorded.get("version")
            result["recorded_version"] = recorded_version

            try:
                expected_version = str(
                    int(recorded_version) + 1
                ) if recorded_version is not None else "1"
            except (TypeError, ValueError):
                result["classification"] = "INVALID_RECORDED_VERSION"
                result["requires_manual_review"] = True
                return result

            result["expected_next_version"] = expected_version

            artifact_id = (
                f"{initiative_id}-{session_id}-{artifact_type}"
            )
            persisted_versions = []
            unreadable_files = []

            for artifact_file in artifact_files:
                try:
                    artifact = json.loads(artifact_file.read_text())
                except (OSError, ValueError):
                    unreadable_files.append(artifact_file.name)
                    continue

                if (
                    artifact.get("artifact_id") == artifact_id
                    and artifact.get("artifact_type") == artifact_type
                    and str(artifact.get("version", "")).isdigit()
                ):
                    persisted_versions.append(
                        str(artifact["version"])
                    )

            result["unreadable_artifact_files"] = sorted(
                unreadable_files
            )

            result["persisted_versions"] = sorted(
                set(persisted_versions), key=int
            )
            result["expected_version_persisted"] = (
                expected_version in persisted_versions
            )

            if unreadable_files:
                result["classification"] = (
                    "INTERRUPTED_GENERATION_CORRUPTED_ARTIFACT"
                )
                result["integrity_errors"] = [
                    f"Unreadable artifact JSON: {name}"
                    for name in unreadable_files
                ]
            elif result["expected_version_persisted"]:
                expected_file = (
                    artifact_dir
                    / f"{artifact_id}__v{expected_version}.json"
                )

                if not expected_file.is_file():
                    result["classification"] = (
                        "INTERRUPTED_GENERATION_ARTIFACT_INCONSISTENT"
                    )
                    result["integrity_errors"] = [
                        "Expected artifact filename is missing"
                    ]
                else:
                    validate = _load_integrity_validator()
                    errors = validate(
                        expected_file,
                        self.factory_root,
                        initiative_id,
                        session_id,
                        artifact_type,
                        expected_version,
                    )
                    result["integrity_errors"] = errors
                    result["classification"] = (
                        "INTERRUPTED_GENERATION_ARTIFACT_INVALID"
                        if errors
                        else "INTERRUPTED_GENERATION_ARTIFACT_VALID"
                    )
            elif artifact_files:
                result["classification"] = (
                    "INTERRUPTED_GENERATION_EXPECTED_ARTIFACT_MISSING"
                )
            else:
                result["classification"] = (
                    "INTERRUPTED_GENERATION_NO_ARTIFACT"
                )

            result["requires_manual_review"] = True
            return result

        if workflow_state == "READY_TO_RUN":
            result["classification"] = "READY_FOR_EXECUTION"
            result["safe_to_execute"] = True
            return result

        result["classification"] = "NOT_ELIGIBLE_FOR_EXECUTION"
        return result
