"""Durable execution-attempt identity for platform requests."""

import hashlib
import json
import os
import tempfile
import uuid
from pathlib import Path


class ExecutionAttemptRegistry:
    """Create or retrieve the initial attempt for a platform request."""

    def __init__(self, root):
        self.root = Path(root)

    def mark_waiting_for_human(self, request):
        """Persist a human-review pause without creating a new attempt."""
        import fcntl

        request_id = str(uuid.UUID(request["request_id"]))
        self.root.mkdir(parents=True, exist_ok=True)

        lock_path = self.root / f"{request_id}.lock"

        with lock_path.open("a+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)

            record, _ = self.get_or_create_initial(request)

            if record["status"] == "waiting_for_human":
                return record

            if record["status"] != "active":
                raise RuntimeError(
                    "Attempt is not eligible for human-review pause"
                )

            updated = {
                **record,
                "status": "waiting_for_human",
            }

            path = self.root / f"{request_id}.json"

            fd, temporary = tempfile.mkstemp(
                prefix=f".{request_id}-",
                suffix=".tmp",
                dir=self.root,
            )

            try:
                with os.fdopen(
                    fd, "w", encoding="utf-8"
                ) as handle:
                    json.dump(updated, handle, indent=2)
                    handle.flush()
                    os.fsync(handle.fileno())

                os.replace(temporary, path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)

            return updated

    def resume_after_human(self, request):
        """Resume a paused attempt without consuming a retry."""
        import fcntl

        request_id = str(uuid.UUID(request["request_id"]))
        self.root.mkdir(parents=True, exist_ok=True)

        lock_path = self.root / f"{request_id}.lock"

        with lock_path.open("a+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)

            path = self.root / f"{request_id}.json"

            if not path.is_file():
                raise RuntimeError(
                    "Cannot resume an attempt that was never paused"
                )

            record, created = self.get_or_create_initial(request)

            if created:
                raise RuntimeError(
                    "Cannot resume an attempt that was never paused"
                )

            if record["status"] != "waiting_for_human":
                raise RuntimeError(
                    "Attempt is not waiting for human review"
                )

            updated = {
                **record,
                "status": "active",
            }

            path = self.root / f"{request_id}.json"

            fd, temporary = tempfile.mkstemp(
                prefix=f".{request_id}-",
                suffix=".tmp",
                dir=self.root,
            )

            try:
                with os.fdopen(
                    fd, "w", encoding="utf-8"
                ) as handle:
                    json.dump(updated, handle, indent=2)
                    handle.flush()
                    os.fsync(handle.fileno())

                os.replace(temporary, path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)

            return updated

    def get_or_create_initial(self, request):
        request_id = str(uuid.UUID(request["request_id"]))
        run_id = str(uuid.UUID(request["run_id"]))
        work_id = str(uuid.UUID(request["work"]["work_id"]))

        retry = request["retry"]
        max_attempts = retry["max_attempts"]

        if (
            type(max_attempts) is not int
            or not 1 <= max_attempts <= 3
        ):
            raise ValueError("Invalid maximum attempt count")

        encoded_request = json.dumps(
            request,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")

        request_sha256 = hashlib.sha256(
            encoded_request
        ).hexdigest()

        record = {
            "request_sha256": request_sha256,
            "request_id": request_id,
            "run_id": run_id,
            "work_id": work_id,
            "attempt_id": str(uuid.uuid4()),
            "attempt_number": 1,
            "status": "active",
        }

        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{request_id}.json"

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
                return record, True
            except FileExistsError:
                pass
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

        try:
            existing = json.loads(
                path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                "Existing execution attempt is unreadable"
            ) from exc

        expected = {
            "request_sha256": request_sha256,
            "request_id": request_id,
            "run_id": run_id,
            "work_id": work_id,
            "attempt_number": 1,
        }

        allowed_statuses = {
            "active",
            "waiting_for_human",
        }

        if (
            not isinstance(existing, dict)
            or set(existing) != (
                set(expected) | {"attempt_id", "status"}
            )
            or any(
                existing.get(key) != value
                for key, value in expected.items()
            )
            or existing.get("status") not in allowed_statuses
        ):
            raise RuntimeError(
                "Existing execution attempt has conflicting identity "
                "or is not active"
            )

        try:
            attempt_id = existing["attempt_id"]
            canonical_id = str(uuid.UUID(attempt_id))
            if attempt_id != canonical_id:
                raise ValueError("Noncanonical attempt UUID")
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(
                "Existing execution attempt ID is invalid"
            ) from exc

        return existing, False
