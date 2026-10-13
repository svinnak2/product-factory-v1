"""Tests for durable platform execution-attempt identity."""

import importlib.util
import tempfile
import unittest
import uuid
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "platform-integration/runtime/execution_attempt.py"
)

spec = importlib.util.spec_from_file_location(
    "product_execution_attempt_tests",
    MODULE_PATH,
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

ExecutionAttemptRegistry = module.ExecutionAttemptRegistry


def make_request():
    return {
        "request_id": str(uuid.uuid4()),
        "run_id": str(uuid.uuid4()),
        "work": {"work_id": str(uuid.uuid4())},
        "retry": {"max_attempts": 3},
    }


class ExecutionAttemptTests(unittest.TestCase):

    def test_initial_attempt_survives_registry_restart(self):
        request = make_request()

        with tempfile.TemporaryDirectory() as directory:
            first_registry = ExecutionAttemptRegistry(directory)

            first, created = (
                first_registry.get_or_create_initial(request)
            )

            second_registry = ExecutionAttemptRegistry(directory)

            second, created_again = (
                second_registry.get_or_create_initial(request)
            )

            self.assertTrue(created)
            self.assertFalse(created_again)
            self.assertEqual(first, second)
            self.assertEqual(first["attempt_number"], 1)
            self.assertEqual(first["status"], "active")
            uuid.UUID(first["attempt_id"])


    def test_changed_request_cannot_reuse_attempt(self):
        request = make_request()

        with tempfile.TemporaryDirectory() as directory:
            registry = ExecutionAttemptRegistry(directory)
            original, created = registry.get_or_create_initial(
                request
            )

            self.assertTrue(created)

            changed = {
                **request,
                "retry": {"max_attempts": 2},
            }

            with self.assertRaisesRegex(
                RuntimeError, "conflicting identity"
            ):
                registry.get_or_create_initial(changed)

            unchanged, created_again = (
                registry.get_or_create_initial(request)
            )

            self.assertFalse(created_again)
            self.assertEqual(unchanged, original)

    def test_collision_does_not_modify_persisted_attempt(self):
        request = make_request()

        with tempfile.TemporaryDirectory() as directory:
            registry = ExecutionAttemptRegistry(directory)
            registry.get_or_create_initial(request)

            path = (
                Path(directory)
                / f"{request['request_id']}.json"
            )
            before = path.read_bytes()

            changed = {
                **request,
                "run_id": str(uuid.uuid4()),
            }

            with self.assertRaises(RuntimeError):
                registry.get_or_create_initial(changed)

            self.assertEqual(path.read_bytes(), before)


    def test_rejects_malformed_persisted_attempts(self):
        import json

        corruptions = {
            "unexpected field": (
                lambda record: record.update(
                    {"unexpected": "not-allowed"}
                ),
                "conflicting identity",
            ),
            "invalid UUID": (
                lambda record: record.update(
                    {"attempt_id": "not-a-uuid"}
                ),
                "attempt ID is invalid",
            ),
            "noncanonical UUID": (
                lambda record: record.update(
                    {"attempt_id": record["attempt_id"].upper()}
                ),
                "attempt ID is invalid",
            ),
        }

        for label, (corrupt, expected_error) in corruptions.items():
            with self.subTest(case=label):
                request = make_request()

                with tempfile.TemporaryDirectory() as directory:
                    registry = ExecutionAttemptRegistry(directory)
                    registry.get_or_create_initial(request)

                    path = (
                        Path(directory)
                        / f"{request['request_id']}.json"
                    )

                    record = json.loads(
                        path.read_text(encoding="utf-8")
                    )

                    corrupt(record)

                    path.write_text(
                        json.dumps(record, indent=2),
                        encoding="utf-8",
                    )

                    before = path.read_bytes()

                    with self.assertRaisesRegex(
                        RuntimeError, expected_error
                    ):
                        registry.get_or_create_initial(request)

                    self.assertEqual(path.read_bytes(), before)

    def test_human_review_continuation_preserves_attempt(self):
        request = make_request()

        with tempfile.TemporaryDirectory() as directory:
            registry = ExecutionAttemptRegistry(directory)

            initial, created = (
                registry.get_or_create_initial(request)
            )

            self.assertTrue(created)

            # Human review is a workflow pause, not a retry.
            paused_registry = ExecutionAttemptRegistry(directory)

            during_review, created_during_review = (
                paused_registry.get_or_create_initial(request)
            )

            self.assertFalse(created_during_review)
            self.assertEqual(
                during_review["attempt_id"],
                initial["attempt_id"],
            )
            self.assertEqual(
                during_review["attempt_number"],
                1,
            )

            # After approval, execution resumes under the same attempt.
            resumed_registry = ExecutionAttemptRegistry(directory)

            resumed, created_after_approval = (
                resumed_registry.get_or_create_initial(request)
            )

            self.assertFalse(created_after_approval)
            self.assertEqual(
                resumed["attempt_id"],
                initial["attempt_id"],
            )
            self.assertEqual(
                resumed["attempt_number"],
                1,
            )
            self.assertEqual(resumed["status"], "active")


    def test_human_review_pause_is_durable_and_idempotent(self):
        request = make_request()

        with tempfile.TemporaryDirectory() as directory:
            registry = ExecutionAttemptRegistry(directory)

            initial, created = (
                registry.get_or_create_initial(request)
            )

            self.assertTrue(created)
            self.assertEqual(initial["status"], "active")

            paused = registry.mark_waiting_for_human(request)

            self.assertEqual(
                paused["status"],
                "waiting_for_human",
            )
            self.assertEqual(
                paused["attempt_id"],
                initial["attempt_id"],
            )
            self.assertEqual(
                paused["attempt_number"],
                1,
            )

            restarted = ExecutionAttemptRegistry(directory)

            persisted, created_again = (
                restarted.get_or_create_initial(request)
            )

            self.assertFalse(created_again)
            self.assertEqual(persisted, paused)

            paused_again = (
                restarted.mark_waiting_for_human(request)
            )

            self.assertEqual(paused_again, paused)

            final, created_final = (
                restarted.get_or_create_initial(request)
            )

            self.assertFalse(created_final)
            self.assertEqual(final, paused)


    def test_resume_after_human_preserves_attempt_identity(self):
        request = make_request()

        with tempfile.TemporaryDirectory() as directory:
            registry = ExecutionAttemptRegistry(directory)

            initial, _ = registry.get_or_create_initial(request)
            paused = registry.mark_waiting_for_human(request)

            restarted = ExecutionAttemptRegistry(directory)
            resumed = restarted.resume_after_human(request)

            self.assertEqual(resumed["status"], "active")
            self.assertEqual(
                resumed["attempt_id"],
                initial["attempt_id"],
            )
            self.assertEqual(
                resumed["attempt_number"],
                1,
            )
            self.assertEqual(
                resumed["request_sha256"],
                paused["request_sha256"],
            )

            persisted, created = (
                ExecutionAttemptRegistry(
                    directory
                ).get_or_create_initial(request)
            )

            self.assertFalse(created)
            self.assertEqual(persisted, resumed)

    def test_rejects_resume_when_attempt_is_active(self):
        request = make_request()

        with tempfile.TemporaryDirectory() as directory:
            registry = ExecutionAttemptRegistry(directory)
            initial, _ = registry.get_or_create_initial(request)

            with self.assertRaisesRegex(
                RuntimeError,
                "not waiting for human review",
            ):
                registry.resume_after_human(request)

            persisted, created = registry.get_or_create_initial(
                request
            )

            self.assertFalse(created)
            self.assertEqual(persisted, initial)

    def test_rejects_duplicate_resume(self):
        request = make_request()

        with tempfile.TemporaryDirectory() as directory:
            registry = ExecutionAttemptRegistry(directory)

            registry.mark_waiting_for_human(request)
            resumed = registry.resume_after_human(request)

            with self.assertRaisesRegex(
                RuntimeError,
                "not waiting for human review",
            ):
                registry.resume_after_human(request)

            persisted, _ = registry.get_or_create_initial(
                request
            )

            self.assertEqual(persisted, resumed)

    def test_rejects_resume_for_missing_attempt(self):
        request = make_request()

        with tempfile.TemporaryDirectory() as directory:
            registry = ExecutionAttemptRegistry(directory)

            with self.assertRaisesRegex(
                RuntimeError,
                "never paused",
            ):
                registry.resume_after_human(request)


if __name__ == "__main__":
    unittest.main()
