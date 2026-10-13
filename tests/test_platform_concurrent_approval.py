"""Verify that concurrent human review submissions cannot both succeed."""

import importlib.util
import multiprocessing
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def load_module(name):
    path = ROOT / "platform-integration/runtime" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_adapter(runtime_root):
    module = load_module("platform_execution_adapter")
    adapter = object.__new__(module.PlatformExecutionAdapter)
    adapter.factory_root = ROOT
    adapter.runtime_root = Path(runtime_root)
    adapter.model_adapter = "mock"
    return adapter


def approval_worker(runtime_root, identity, queue):
    try:
        adapter = make_adapter(runtime_root)
        result = adapter.submit_review(
            identity,
            "APPROVED",
            "Approved for isolated concurrency testing",
            "mock-concurrency-reviewer",
        )
        queue.put({
            "success": True,
            "decision": result["decision"],
            "state": result["workflow_state"],
        })
    except Exception as exc:
        queue.put({
            "success": False,
            "error": str(exc),
        })


class ConcurrentApprovalTests(unittest.TestCase):

    def test_only_one_approval_succeeds(self):
        identity = {
            "request_id": "REQ-APPROVAL-RACE-001",
            "run_id": "RUN-APPROVAL-RACE-001",
            "work_id": "WORK-APPROVAL-RACE-001",
            "initiative_id": "INIT-APPROVAL-RACE-001",
            "session_id": "SESSION-APPROVAL-RACE-001",
        }

        initiative = {
            "initiative_id": identity["initiative_id"],
            "title": "Concurrent Approval Test",
            "problem_or_opportunity": (
                "Simultaneous reviewers must not create "
                "duplicate approval decisions."
            ),
            "desired_outcome": (
                "Exactly one approval is accepted for "
                "the pending Product Charter."
            ),
        }

        mapping = load_module("initiative_mapping")
        initializer_module = load_module("session_initializer")

        normalized = mapping.normalize_initiative(
            "new-product", initiative
        )

        with tempfile.TemporaryDirectory(
            prefix="product-approval-race-"
        ) as temp:
            runtime_root = Path(temp)

            initializer = initializer_module.SessionInitializer(
                ROOT, runtime_root
            )

            state, created = initializer.initialize(
                identity,
                normalized,
                model_adapter="mock",
            )

            self.assertTrue(created)

            adapter = make_adapter(runtime_root)
            generated = adapter.execute_next(identity)

            self.assertTrue(generated["artifact_generated"])
            self.assertEqual(
                generated["artifact_type"],
                "PRODUCT_CHARTER",
            )
            self.assertEqual(
                generated["workflow_state"],
                "PAUSED_WAITING_FOR_HUMAN",
            )

            print("PASS: Product Charter awaiting approval")

            ctx = multiprocessing.get_context("fork")
            queue = ctx.Queue()

            processes = [
                ctx.Process(
                    target=approval_worker,
                    args=(runtime_root, identity, queue),
                )
                for _ in range(2)
            ]

            try:
                for process in processes:
                    process.start()

                for process in processes:
                    process.join(timeout=30)

                for process in processes:
                    self.assertFalse(
                        process.is_alive(),
                        "Approval worker timed out",
                    )
                    self.assertEqual(process.exitcode, 0)

                results = [
                    queue.get(timeout=5)
                    for _ in processes
                ]

                print("Approval results:", results)

                successful = [
                    r for r in results if r["success"]
                ]
                rejected = [
                    r for r in results if not r["success"]
                ]

                self.assertEqual(len(successful), 1)
                self.assertEqual(len(rejected), 1)

                self.assertEqual(
                    successful[0]["decision"],
                    "APPROVED",
                )
                self.assertEqual(
                    successful[0]["state"],
                    "READY_TO_RUN",
                )

                print("PASS: Exactly one approval accepted")
                print("PASS: Duplicate approval rejected")

                from runtime.stores.local import LocalStore

                store = LocalStore(
                    runtime_root,
                    identity["initiative_id"],
                    identity["session_id"],
                )

                saved = store.load_state()

                self.assertEqual(
                    saved["workflow_state"],
                    "READY_TO_RUN",
                )
                self.assertEqual(
                    saved["artifacts"]["PRODUCT_CHARTER"]["status"],
                    "APPROVED",
                )

                self.assertEqual(
                    saved.get("pending_approvals", []),
                    [],
                )

                print("PASS: Persistent approval state valid")

            finally:
                for process in processes:
                    if process.is_alive():
                        process.terminate()
                        process.join()

                queue.close()
                queue.join_thread()


if __name__ == "__main__":
    unittest.main()
