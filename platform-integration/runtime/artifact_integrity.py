"""Read-only integrity validation for persisted Product Factory artifacts."""

import json
from pathlib import Path

from runtime.validators.core import (
    Draft202012Validator,
    validate_artifact,
)


def validate_persisted_artifact(
    artifact_path,
    factory_root,
    initiative_id,
    session_id,
    artifact_type,
    version,
):
    """Return validation errors without modifying the artifact."""

    path = Path(artifact_path)
    errors = []

    expected_id = (
        f"{initiative_id}-{session_id}-{artifact_type}"
    )
    expected_version = str(version)

    expected_filename = (
        f"{expected_id}__v{expected_version}.json"
    )

    if path.name != expected_filename:
        errors.append("Artifact filename does not match identity")

    try:
        artifact = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        return [f"Artifact cannot be read as JSON: {exc}"]

    if not isinstance(artifact, dict):
        return ["Artifact envelope must be a JSON object"]

    expected_fields = {
        "artifact_id": expected_id,
        "artifact_type": artifact_type,
        "version": expected_version,
        "initiative_id": initiative_id,
        "session_id": session_id,
    }

    for field, expected in expected_fields.items():
        if artifact.get(field) != expected:
            errors.append(
                f"{field} does not match expected value"
            )

    payload = artifact.get("payload")

    if not isinstance(payload, dict):
        errors.append("Artifact payload must be a JSON object")
        return sorted(set(errors))

    schema_path = (
        Path(factory_root)
        / "product-factory"
        / "schemas"
        / "executable-artifact.schema.json"
    )

    if Draft202012Validator is None:
        errors.append(
            "Full artifact validation unavailable: "
            "jsonschema is not installed"
        )
        return sorted(set(errors))

    if not schema_path.is_file():
        errors.append("Artifact schema file is missing")
        return sorted(set(errors))

    try:
        errors.extend(
            validate_artifact(
                payload,
                schema_path,
                artifact_type,
            )
        )
    except (OSError, ValueError, TypeError) as exc:
        errors.append(f"Artifact schema validation failed: {exc}")

    return sorted(set(errors))
