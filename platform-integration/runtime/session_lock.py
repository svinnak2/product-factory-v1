"""Shared filesystem locking for Product Factory sessions."""

import fcntl
import hashlib
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def session_lock(runtime_root, initiative_id, session_id):
    """Exclusively lock one Product Factory session."""

    if not isinstance(initiative_id, str) or not initiative_id:
        raise ValueError("Valid initiative_id is required")

    if not isinstance(session_id, str) or not session_id:
        raise ValueError("Valid session_id is required")

    lock_directory = Path(runtime_root) / "integration-locks"
    lock_directory.mkdir(parents=True, exist_ok=True)

    lock_key = hashlib.sha256(
        f"{initiative_id}:{session_id}".encode("utf-8")
    ).hexdigest()

    lock_path = lock_directory / f"{lock_key}.lock"

    with lock_path.open("a+b") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
