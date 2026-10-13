"""Durable identity mapping for platform-to-Product Factory execution."""

import hashlib
import json
import os
import re
import uuid
from pathlib import Path


def request_fingerprint(request):
    """Stable SHA-256 digest of the complete execution request."""
    encoded = json.dumps(
        request,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class ExecutionIdentityRegistry:
    """Persist request-to-session identity without replacing existing records."""

    def __init__(self, root):
        self.root = Path(root)

    def register(self, request, initiative_id):
        request_id = str(uuid.UUID(request["request_id"]))
        run_id = str(uuid.UUID(request["run_id"]))

        if not isinstance(initiative_id, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", initiative_id
        ):
            raise ValueError("Unsafe or invalid initiative_id")

        fingerprint = request_fingerprint(request)

        record = {
            "request_id": request_id,
            "run_id": run_id,
            "work_id": request["work"]["work_id"],
            "initiative_id": initiative_id,
            "session_id": f"PLATFORM-{run_id}",
            "request_sha256": fingerprint,
            "execution_request": json.loads(
                json.dumps(request, allow_nan=False)
            ),
        }

        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{request_id}.json"

        import tempfile

        fd, temporary = tempfile.mkstemp(
            prefix=f".{request_id}-",
            suffix=".tmp",
            dir=self.root,
        )

        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(record, handle, indent=2)
                handle.flush()
                os.fsync(handle.fileno())

            try:
                os.link(temporary, path)
                created = True
            except FileExistsError:
                created = False
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

        if created:
            return record, True

        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                "Existing execution identity record is unreadable; "
                "manual recovery is required"
            ) from exc

        if "execution_request" in existing:
            if existing != record:
                raise ValueError(
                    "Request ID already registered with different execution data"
                )
        else:
            # Legacy records remain unchanged and retain their
            # original identity and fingerprint collision checks.
            legacy_record = {
                key: value
                for key, value in record.items()
                if key != "execution_request"
            }
            if existing != legacy_record:
                raise ValueError(
                    "Request ID already registered with different execution data"
                )

        return existing, False

    def load_execution_request(self, request_id):
        """Load and verify the original persisted execution request."""
        canonical_id = str(uuid.UUID(request_id))
        path = self.root / f"{canonical_id}.json"

        try:
            record = json.loads(
                path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                "Execution identity record is missing or unreadable"
            ) from exc

        if not isinstance(record, dict):
            raise RuntimeError(
                "Execution identity record is invalid"
            )

        request = record.get("execution_request")

        if not isinstance(request, dict):
            raise RuntimeError(
                "Original execution request is unavailable; "
                "legacy identity requires explicit recovery"
            )

        if record.get("request_id") != canonical_id:
            raise RuntimeError(
                "Persisted execution request identity mismatch"
            )

        if request.get("request_id") != canonical_id:
            raise RuntimeError(
                "Original execution request ID mismatch"
            )

        if request.get("run_id") != record.get("run_id"):
            raise RuntimeError(
                "Original execution request run ID mismatch"
            )

        work = request.get("work")
        if not isinstance(work, dict) or (
            work.get("work_id") != record.get("work_id")
        ):
            raise RuntimeError(
                "Original execution request work ID mismatch"
            )

        if request_fingerprint(request) != record.get(
            "request_sha256"
        ):
            raise RuntimeError(
                "Persisted execution request fingerprint mismatch"
            )

        return request
