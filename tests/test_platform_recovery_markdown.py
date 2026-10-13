"""Verify Markdown integrity before recovering persisted artifacts."""

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


class RecoveryMarkdownTests(unittest.TestCase):

    def check_scenario(self, scenario):
        identity = {
            "request_id": f"REQ-MD-REG-{scenario}",
            "run_id": f"RUN-MD-REG-{scenario}",
            "work_id": f"WORK-MD-REG-{scenario}",
            "initiative_id": f"INIT-MD-REG-{scenario}",
            "session_id": f"SESSION-MD-REG-{scenario}",
        }

        initiative = {
            "initiative_id": identity["initiative_id"],
            "title": f"Markdown Recovery {scenario}",
            "problem_or_opportunity": (
                "Interrupted generation may leave inconsistent "
                "artifact representations."
            ),
            "desired_outcome": (
                "Allow recovery only when persisted "
                "artifact representations match."
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
            prefix=f"product-md-reg-{scenario.lower()}-"
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
                generated["artifact_type"],
                "PRODUCT_CHARTER",
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

            directory = (
                store.session_root
                / "artifacts"
                / "PRODUCT_CHARTER"
            )

            json_path = (
                directory / f"{artifact_id}__v{version}.json"
            )
            markdown_path = (
                directory / f"{artifact_id}__v{version}.md"
            )

            self.assertTrue(json_path.exists())
            self.assertTrue(markdown_path.exists())

            original_json = json_path.read_bytes()

            # Simulate an interruption after artifact persistence.
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

            if scenario == "MISSING":
                markdown_path.unlink()
            elif scenario == "CORRUPTED":
                markdown_path.write_text(
                    "INCOMPLETE MARKDOWN CONTENT\n"
                )

            if scenario == "VALID":
                assessment = recovery_module.recovery_preflight(
                    ROOT, runtime_root, identity
                )

                self.assertTrue(assessment["eligible"])
                print("PASS: Matching Markdown accepted")

            else:
                with self.assertRaisesRegex(
                    RuntimeError,
                    "Markdown integrity validation failed",
                ):
                    recovery_module.recovery_preflight(
                        ROOT, runtime_root, identity
                    )

                print(f"PASS: {scenario} Markdown rejected")

            self.assertEqual(
                json_path.read_bytes(),
                original_json,
            )

            unchanged = store.load_state()

            self.assertEqual(
                unchanged["workflow_state"],
                "RUNNING",
            )
            self.assertEqual(
                unchanged["pending_approvals"],
                [],
            )

            print("PASS: Artifact JSON and session state unchanged")

    def test_valid_markdown_accepted(self):
        self.check_scenario("VALID")

    def test_missing_markdown_rejected(self):
        self.check_scenario("MISSING")

    def test_corrupted_markdown_rejected(self):
        self.check_scenario("CORRUPTED")


if __name__ == "__main__":
    unittest.main()
