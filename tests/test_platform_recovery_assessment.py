"""Tests for read-only Product Factory recovery assessment."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_assessor():
    path = (
        ROOT
        / "platform-integration"
        / "runtime"
        / "recovery_assessment.py"
    )
    spec = importlib.util.spec_from_file_location(
        "recovery_assessment", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ProductRecoveryAssessor


class RecoveryAssessmentTests(unittest.TestCase):

    def test_recovery_classifications(self):
        Assessor = load_assessor()

        scenarios = [
            (
                "ready",
                {
                    "workflow_state": "READY_TO_RUN",
                    "active_generation": None,
                    "pending_approvals": [],
                },
                "READY_FOR_EXECUTION",
                True,
            ),
            (
                "human_review",
                {
                    "workflow_state": "PAUSED_WAITING_FOR_HUMAN",
                    "active_generation": None,
                    "pending_approvals": [
                        {"artifact_type": "PRODUCT_CHARTER"}
                    ],
                },
                "WAITING_FOR_HUMAN",
                False,
            ),
            (
                "interrupted",
                {
                    "workflow_state": "RUNNING",
                    "active_generation": {
                        "artifact_type": "PRODUCT_CHARTER",
                        "attempt": 1,
                    },
                    "pending_approvals": [],
                },
                "INTERRUPTED_GENERATION_NO_ARTIFACT",
                False,
            ),
            (
                "persisted",
                {
                    "workflow_state": "RUNNING",
                    "active_generation": {
                        "artifact_type": "PRODUCT_CHARTER",
                        "attempt": 1,
                    },
                    "pending_approvals": [],
                },
                "INTERRUPTED_GENERATION_ARTIFACT_INVALID",
                False,
            ),
        ]

        with tempfile.TemporaryDirectory(
            prefix="product-recovery-test-"
        ) as temp:
            root = Path(temp)
            assessor = Assessor(root)

            for name, state, expected, safe in scenarios:
                with self.subTest(scenario=name):
                    initiative_id = "INIT-RECOVERY-001"
                    session_id = f"SESSION-{name}"

                    session_root = (
                        root
                        / "sessions"
                        / initiative_id
                        / session_id
                    )
                    session_root.mkdir(parents=True)

                    state_path = session_root / "state.json"
                    original = json.dumps(state, indent=2)
                    state_path.write_text(original)

                    if name == "persisted":
                        artifact_dir = (
                            session_root
                            / "artifacts"
                            / "PRODUCT_CHARTER"
                        )
                        artifact_dir.mkdir(parents=True)
                        (
                            artifact_dir
                            / (
                                f"{initiative_id}-{session_id}-"
                                "PRODUCT_CHARTER__v1.json"
                            )
                        ).write_text(
                            json.dumps({
                                "artifact_id": (
                                    "INIT-RECOVERY-001-"
                                    "SESSION-persisted-PRODUCT_CHARTER"
                                ),
                                "artifact_type": "PRODUCT_CHARTER",
                                "version": "1",
                            })
                        )

                    result = assessor.assess(
                        initiative_id,
                        session_id,
                    )

                    self.assertEqual(
                        result["classification"],
                        expected,
                    )
                    self.assertEqual(
                        result["safe_to_execute"],
                        safe,
                    )

                    self.assertEqual(
                        state_path.read_text(),
                        original,
                    )

                    print(
                        f"PASS: {name} -> "
                        f"{result['classification']}"
                    )

            missing = assessor.assess(
                "INIT-RECOVERY-001",
                "SESSION-MISSING",
            )

            self.assertEqual(
                missing["classification"],
                "MISSING_STATE",
            )
            self.assertFalse(missing["safe_to_execute"])

            print("PASS: Missing state classified safely")
            print("PASS: All assessments preserved session state")


if __name__ == "__main__":
    unittest.main()
