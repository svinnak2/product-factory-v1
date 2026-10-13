"""Verify recovery of a persisted artifact through human approval."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

from runtime.stores.local import LocalStore


ROOT = Path(__file__).resolve().parents[1]


def load_module(name):
    path = ROOT / "platform-integration/runtime" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RecoveryApprovalTests(unittest.TestCase):

    def test_recovered_artifact_can_be_approved(self):
        identity = {
            "request_id": "REQ-RECOVERY-APPROVAL-TEST",
            "run_id": "RUN-RECOVERY-APPROVAL-TEST",
            "work_id": "WORK-RECOVERY-APPROVAL-TEST",
            "initiative_id": "INIT-RECOVERY-APPROVAL-TEST",
            "session_id": "SESSION-RECOVERY-APPROVAL-TEST",
        }

        initiative = {
            "initiative_id": identity["initiative_id"],
            "title": "Recovery Approval Integration Test",
            "problem_or_opportunity": (
                "Interrupted generation must not require "
                "regenerating a persisted artifact."
            ),
            "desired_outcome": (
                "Recover and approve the existing Product Charter."
            ),
        }

        mapping = load_module("initiative_mapping")
        initializer_module = load_module("session_initializer")
        adapter_module = load_module("platform_execution_adapter")
        recovery_module = load_module("artifact_recovery")

        normalized = mapping.normalize_initiative(
            "new-product", initiative
        )

        with tempfile.TemporaryDirectory(
            prefix="product-recovery-approval-test-"
        ) as temp:
            runtime_root = Path(temp)

            initializer = initializer_module.SessionInitializer(
                ROOT, runtime_root
            )

            _, created = initializer.initialize(
                identity,
                normalized,
                model_adapter="mock",
            )
            self.assertTrue(created)

            adapter = object.__new__(
                adapter_module.PlatformExecutionAdapter
            )
            adapter.factory_root = ROOT
            adapter.runtime_root = runtime_root
            adapter.model_adapter = "mock"

            generated = adapter.execute_next(identity)

            self.assertTrue(generated["artifact_generated"])
            self.assertEqual(
                generated["artifact_type"], "PRODUCT_CHARTER"
            )
            self.assertEqual(
                generated["workflow_state"],
                "PAUSED_WAITING_FOR_HUMAN",
            )

            store = LocalStore(
                runtime_root,
                identity["initiative_id"],
                identity["session_id"],
            )

            state = store.load_state()
            pending = state["pending_approvals"][0]
            artifact_id = pending["artifact_id"]
            version = pending["version"]

            artifact_path = (
                store.session_root
                / "artifacts"
                / "PRODUCT_CHARTER"
                / f"{artifact_id}__v{version}.json"
            )

            self.assertTrue(artifact_path.exists())
            original_artifact = artifact_path.read_bytes()

            # Simulate interruption after artifact persistence,
            # before the human-review checkpoint was saved.
            state["workflow_state"] = "RUNNING"
            state["stage"] = "PRODUCT_DEFINITION"
            state["active_generation"] = {
                "artifact_type": "PRODUCT_CHARTER",
                "attempt": 1,
            }
            state["artifacts"].pop("PRODUCT_CHARTER", None)
            state["pending_approvals"] = []
            state["pending_actions"] = []

            store.save_state(state)

            preflight = recovery_module.recovery_preflight(
                ROOT, runtime_root, identity
            )
            self.assertTrue(preflight["eligible"], preflight)

            recovered = (
                recovery_module.recover_human_review_checkpoint(
                    ROOT, runtime_root, identity
                )
            )

            self.assertTrue(recovered["recovered"])
            self.assertFalse(recovered["model_invoked"])
            self.assertFalse(recovered["approval_created"])

            restored = store.load_state()

            self.assertEqual(
                restored["workflow_state"],
                "PAUSED_WAITING_FOR_HUMAN",
            )
            self.assertEqual(len(restored["pending_approvals"]), 1)
            self.assertEqual(
                artifact_path.read_bytes(), original_artifact
            )

            reviewed = adapter.submit_review(
                identity,
                "APPROVED",
                "Approved for isolated recovery regression testing",
                "mock-recovery-reviewer",
            )

            self.assertEqual(reviewed["decision"], "APPROVED")
            self.assertEqual(
                reviewed["workflow_state"], "READY_TO_RUN"
            )

            final_state = store.load_state()

            self.assertEqual(
                final_state["workflow_state"], "READY_TO_RUN"
            )
            self.assertEqual(
                final_state["artifacts"]["PRODUCT_CHARTER"]["status"],
                "APPROVED",
            )
            self.assertEqual(final_state["pending_approvals"], [])
            self.assertEqual(final_state["pending_actions"], [])
            self.assertEqual(
                artifact_path.read_bytes(), original_artifact
            )

            print(
                "PASS: Recovered artifact approved without regeneration"
            )
            print("PASS: Workflow returned to READY_TO_RUN")
            print("PASS: Original persisted artifact unchanged")


if __name__ == "__main__":
    unittest.main()
