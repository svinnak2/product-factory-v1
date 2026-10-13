"""Concurrent approval-and-resumption integration test."""

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


def resume_worker(runtime_root, identity, queue):
    try:
        controller_module = load_module("execution_controller")
        controller = controller_module.ProductExecutionController(
            make_adapter(runtime_root)
        )

        result = controller.review_and_resume(
            identity,
            "APPROVED",
            "Approved for isolated concurrency testing",
            "mock-concurrency-reviewer",
        )

        execution = result.get("execution")

        queue.put({
            "success": True,
            "resumed": result["resumed"],
            "artifact_type": (
                execution["execution_history"][0].get("artifact_type")
                if execution and execution["execution_history"]
                else None
            ),
            "workflow_state": (
                execution["workflow_state"]
                if execution else None
            ),
        })
    except Exception as exc:
        queue.put({
            "success": False,
            "error": str(exc),
        })


class ConcurrentResumeTests(unittest.TestCase):

    def test_only_one_approval_resumes_execution(self):
        identity = {
            "request_id": "REQ-RESUME-RACE-001",
            "run_id": "RUN-RESUME-RACE-001",
            "work_id": "WORK-RESUME-RACE-001",
            "initiative_id": "INIT-RESUME-RACE-001",
            "session_id": "SESSION-RESUME-RACE-001",
        }

        initiative = {
            "initiative_id": identity["initiative_id"],
            "title": "Concurrent Resume Test",
            "problem_or_opportunity": (
                "Concurrent approval requests must not duplicate "
                "downstream artifact generation."
            ),
            "desired_outcome": (
                "Exactly one Product Brief is generated after "
                "approval of the Product Charter."
            ),
        }

        mapping = load_module("initiative_mapping")
        initializer_module = load_module("session_initializer")

        normalized = mapping.normalize_initiative(
            "new-product", initiative
        )

        with tempfile.TemporaryDirectory(
            prefix="product-resume-race-"
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
                    target=resume_worker,
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
                        "Resume worker timed out",
                    )
                    self.assertEqual(process.exitcode, 0)

                results = [
                    queue.get(timeout=5)
                    for _ in processes
                ]

                print("Worker results:", results)

                successful = [
                    r for r in results if r["success"]
                ]
                rejected = [
                    r for r in results if not r["success"]
                ]

                self.assertEqual(len(successful), 1, results)
                self.assertEqual(len(rejected), 1, results)

                self.assertTrue(successful[0]["resumed"])
                self.assertEqual(
                    successful[0]["artifact_type"],
                    "PRODUCT_BRIEF",
                )
                self.assertEqual(
                    successful[0]["workflow_state"],
                    "PAUSED_WAITING_FOR_HUMAN",
                )

                print("PASS: Exactly one approval resumed execution")
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
                    "PAUSED_WAITING_FOR_HUMAN",
                )
                self.assertEqual(
                    saved["artifacts"]["PRODUCT_CHARTER"]["status"],
                    "APPROVED",
                )
                self.assertEqual(
                    saved["artifacts"]["PRODUCT_BRIEF"]["version"],
                    "1",
                )
                self.assertEqual(
                    saved["artifacts"]["PRODUCT_BRIEF"]["status"],
                    "HUMAN_REVIEW_REQUIRED",
                )

                brief_files = list(
                    (
                        store.session_root
                        / "artifacts"
                        / "PRODUCT_BRIEF"
                    ).glob("*__v1.json")
                )

                self.assertEqual(len(brief_files), 1)

                print("PASS: Exactly one PRODUCT_BRIEF v1 persisted")
                print("PASS: Workflow paused at next human review")

            finally:
                for process in processes:
                    if process.is_alive():
                        process.terminate()
                        process.join()

                queue.close()
                queue.join_thread()


if __name__ == "__main__":
    unittest.main()
