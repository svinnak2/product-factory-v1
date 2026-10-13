"""Multiprocess concurrency test for Product Factory platform execution."""

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


def worker(runtime_root, identity, queue):
    try:
        adapter_module = load_module("platform_execution_adapter")

        adapter = object.__new__(
            adapter_module.PlatformExecutionAdapter
        )
        adapter.factory_root = ROOT
        adapter.runtime_root = Path(runtime_root)
        adapter.model_adapter = "mock"

        result = adapter.execute_next(identity)

        queue.put({
            "ok": True,
            "generated": result["artifact_generated"],
            "state": result["workflow_state"],
        })
    except Exception as exc:
        queue.put({
            "ok": False,
            "error": repr(exc),
        })


class PlatformControllerConcurrencyTests(unittest.TestCase):

    def test_two_workers_generate_only_one_charter(self):
        identity = {
            "request_id": "REQ-CONCURRENCY-001",
            "run_id": "RUN-CONCURRENCY-001",
            "work_id": "WORK-CONCURRENCY-001",
            "initiative_id": "INIT-CONCURRENCY-001",
            "session_id": "SESSION-CONCURRENCY-001",
        }

        initiative = {
            "initiative_id": identity["initiative_id"],
            "title": "Product Factory Concurrency Test",
            "problem_or_opportunity": (
                "Concurrent workers must not generate duplicate artifacts."
            ),
            "desired_outcome": (
                "Generate exactly one charter and pause for human approval."
            ),
        }

        mapping = load_module("initiative_mapping")
        initializer_module = load_module("session_initializer")

        normalized = mapping.normalize_initiative(
            "new-product",
            initiative,
        )

        with tempfile.TemporaryDirectory(
            prefix="product-concurrency-"
        ) as temp:
            runtime_root = Path(temp)

            initializer = initializer_module.SessionInitializer(
                ROOT,
                runtime_root,
            )

            state, created = initializer.initialize(
                identity,
                normalized,
                model_adapter="mock",
            )

            self.assertTrue(created)
            self.assertEqual(
                state["workflow_state"],
                "READY_TO_RUN",
            )

            ctx = multiprocessing.get_context("fork")
            queue = ctx.Queue()

            processes = [
                ctx.Process(
                    target=worker,
                    args=(runtime_root, identity, queue),
                )
                for _ in range(2)
            ]

            for process in processes:
                process.start()

            try:
                for process in processes:
                    process.join(timeout=30)

                for process in processes:
                    self.assertFalse(
                        process.is_alive(),
                        "Concurrent worker timed out",
                    )
                    self.assertEqual(process.exitcode, 0)

                results = [
                    queue.get(timeout=5)
                    for _ in processes
                ]

                print("Worker results:", results)

                self.assertTrue(
                    all(result["ok"] for result in results),
                    results,
                )

                self.assertEqual(
                    sum(result["generated"] for result in results),
                    1,
                )

                self.assertTrue(
                    all(
                        result["state"] == "PAUSED_WAITING_FOR_HUMAN"
                        for result in results
                    )
                )

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

                # Product Factory versions are strings.
                self.assertEqual(
                    saved["artifacts"]["PRODUCT_CHARTER"]["version"],
                    "1",
                )

                artifact_files = list(
                    (
                        store.session_root
                        / "artifacts"
                        / "PRODUCT_CHARTER"
                    ).glob("*__v1.json")
                )

                self.assertEqual(len(artifact_files), 1)

            finally:
                for process in processes:
                    if process.is_alive():
                        process.terminate()
                        process.join()

                queue.close()
                queue.join_thread()


if __name__ == "__main__":
    unittest.main()
