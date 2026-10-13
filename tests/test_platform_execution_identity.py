"""Regression tests for platform execution identity registration."""

import importlib.util
import json
import tempfile
import unittest
import uuid
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "platform-integration/runtime/execution_identity.py"
)

spec = importlib.util.spec_from_file_location(
    "product_execution_identity_tests",
    MODULE_PATH,
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

ExecutionIdentityRegistry = module.ExecutionIdentityRegistry
request_fingerprint = module.request_fingerprint


def make_request():
    return {
        "contract_version": "0.1.0",
        "request_id": str(uuid.uuid4()),
        "run_id": str(uuid.uuid4()),
        "work": {"work_id": str(uuid.uuid4())},
        "target": {
            "factory_id": "factory.product-factory",
            "capability_id": "capability.product-definition",
        },
        "inputs": [],
        "required_outputs": [],
        "retry": {
            "max_attempts": 1,
            "safety": "safe",
            "eligible_errors": [],
        },
    }


class ExecutionIdentityTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.registry = ExecutionIdentityRegistry(self.root)

    def test_registration_is_idempotent(self):
        request = make_request()

        first, created = self.registry.register(
            request, "INIT-IDENTITY-TEST"
        )
        second, created_again = self.registry.register(
            request, "INIT-IDENTITY-TEST"
        )

        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(first, second)
        self.assertEqual(
            first["request_sha256"],
            request_fingerprint(request),
        )

    def test_changed_request_cannot_reuse_request_id(self):
        request = make_request()
        self.registry.register(request, "INIT-IDENTITY-TEST")

        changed = json.loads(json.dumps(request))
        changed["retry"]["max_attempts"] = 2

        with self.assertRaises(ValueError):
            self.registry.register(
                changed, "INIT-IDENTITY-TEST"
            )

    def test_legacy_record_remains_unchanged(self):
        request = make_request()

        original, _ = self.registry.register(
            request, "INIT-IDENTITY-TEST"
        )

        path = self.root / f"{request['request_id']}.json"
        before = path.read_bytes()

        repeated, created = self.registry.register(
            request, "INIT-IDENTITY-TEST"
        )

        self.assertFalse(created)
        self.assertEqual(repeated, original)
        self.assertEqual(path.read_bytes(), before)

    def test_complete_execution_request_is_persisted(self):
        request = make_request()

        record, created = self.registry.register(
            request, "INIT-IDENTITY-TEST"
        )

        self.assertTrue(created)
        self.assertEqual(record["execution_request"], request)

        path = self.root / f"{request['request_id']}.json"
        persisted = json.loads(
            path.read_text(encoding="utf-8")
        )

        self.assertEqual(
            persisted["execution_request"],
            request,
        )
        self.assertEqual(
            persisted["request_sha256"],
            request_fingerprint(
                persisted["execution_request"]
            ),
        )

    def test_preexisting_legacy_identity_is_not_modified(self):
        request = make_request()

        legacy = {
            "request_id": request["request_id"],
            "run_id": request["run_id"],
            "work_id": request["work"]["work_id"],
            "initiative_id": "INIT-IDENTITY-TEST",
            "session_id": f"PLATFORM-{request['run_id']}",
            "request_sha256": request_fingerprint(request),
        }

        path = self.root / f"{request['request_id']}.json"
        path.write_text(
            json.dumps(legacy, indent=2),
            encoding="utf-8",
        )
        before = path.read_bytes()

        record, created = self.registry.register(
            request, "INIT-IDENTITY-TEST"
        )

        self.assertFalse(created)
        self.assertEqual(record, legacy)
        self.assertEqual(path.read_bytes(), before)
        self.assertNotIn("execution_request", record)

    def test_load_execution_request_successfully(self):
        request = make_request()
        self.registry.register(request, "INIT-IDENTITY-TEST")

        loaded = self.registry.load_execution_request(
            request["request_id"]
        )

        self.assertEqual(loaded, request)

    def test_loader_rejects_modified_request(self):
        request = make_request()
        self.registry.register(request, "INIT-IDENTITY-TEST")

        path = self.root / f"{request['request_id']}.json"
        record = json.loads(path.read_text(encoding="utf-8"))

        record["execution_request"]["retry"]["max_attempts"] = 3
        path.write_text(
            json.dumps(record, indent=2),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(
            RuntimeError, "fingerprint mismatch"
        ):
            self.registry.load_execution_request(
                request["request_id"]
            )

    def test_loader_rejects_mismatched_run_identity(self):
        request = make_request()
        self.registry.register(request, "INIT-IDENTITY-TEST")

        path = self.root / f"{request['request_id']}.json"
        record = json.loads(path.read_text(encoding="utf-8"))

        record["run_id"] = str(uuid.uuid4())
        path.write_text(
            json.dumps(record, indent=2),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(
            RuntimeError, "run ID mismatch"
        ):
            self.registry.load_execution_request(
                request["request_id"]
            )

    def test_loader_rejects_legacy_record(self):
        request = make_request()

        legacy = {
            "request_id": request["request_id"],
            "run_id": request["run_id"],
            "work_id": request["work"]["work_id"],
            "initiative_id": "INIT-IDENTITY-TEST",
            "session_id": f"PLATFORM-{request['run_id']}",
            "request_sha256": request_fingerprint(request),
        }

        path = self.root / f"{request['request_id']}.json"
        path.write_text(
            json.dumps(legacy, indent=2),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(
            RuntimeError, "legacy identity"
        ):
            self.registry.load_execution_request(
                request["request_id"]
            )

    def test_distinct_requests_remain_isolated(self):
        first = make_request()
        second = make_request()

        first_record, _ = self.registry.register(
            first, "INIT-ONE"
        )
        second_record, _ = self.registry.register(
            second, "INIT-TWO"
        )

        self.assertNotEqual(
            first_record["session_id"],
            second_record["session_id"],
        )
        self.assertEqual(
            len(list(self.root.glob("*.json"))),
            2,
        )


if __name__ == "__main__":
    unittest.main()
