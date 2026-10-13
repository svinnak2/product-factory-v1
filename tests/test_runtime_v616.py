"""v6.1.6 regression tests for blocker-resolution integrity."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.stores.local import LocalStore
from runtime.orchestrator.product import ProductOrchestrator
from runtime.adapters.mock import MockAdapter


def test_multiple_human_decisions_remain_pending():
    """
    Answering one question must not resume blocker resolution
    while other material human decisions remain unanswered.
    """

    with tempfile.TemporaryDirectory() as directory:
        initiative_id = "INIT-TEST-616"
        session_id = "RUN-TEST-616"

        store = LocalStore(
            Path(directory),
            initiative_id,
            session_id,
        )

        orchestrator = ProductOrchestrator(
            ROOT,
            store,
            MockAdapter(),
        )

        blocker_id = "DEP-PRD-001"

        questions = [
            {
                "question_id": "Q-001",
                "question": "Who approves the budget?",
                "blocking": True,
                "classification": "HUMAN_DECISION",
                "blocker_id": blocker_id,
                "artifact_type": "PRD",
                "status": "OPEN",
            },
            {
                "question_id": "Q-002",
                "question": "What is the maximum budget?",
                "blocking": True,
                "classification": "HUMAN_DECISION",
                "blocker_id": blocker_id,
                "artifact_type": "PRD",
                "status": "OPEN",
            },
            {
                "question_id": "Q-003",
                "question": "Who can override the limit?",
                "blocking": True,
                "classification": "HUMAN_DECISION",
                "blocker_id": blocker_id,
                "artifact_type": "PRD",
                "status": "OPEN",
            },
        ]

        state = {
            "initiative_id": initiative_id,
            "session_id": session_id,
            "correlation_id": "test-correlation",
            "initiative": {
                "initiative_id": initiative_id,
                "title": "Resolution Integrity Test",
                "development_context": "PRODUCT_CREATION",
            },
            "factory_id": "product-factory",
            "adapter": "mock",
            "workflow_state": "PAUSED_WAITING_FOR_HUMAN",
            "stage": "HUMAN_DECISION_REQUIRED",
            "required_outputs": ["PRD"],
            "artifacts": {},
            "pending_approvals": [],
            "pending_actions": [
                {
                    "type": "DECISION_REQUIRED",
                    "question_id": question["question_id"],
                    "blocker_id": blocker_id,
                }
                for question in questions
            ],
            "open_questions": questions,
            "open_alerts": [],
            "final_product_review_passed": False,
            "rework_feedback": {},
            "active_generation": {
                "artifact_type": "PRD",
                "agent_id": "product-lead",
                "failure_type": "HUMAN_DECISION_REQUIRED",
                "blocker_id": blocker_id,
            },
            "resolution_workflow": {
                "status": "ACTIVE",
                "artifact_type": "PRD",
                "source_alert_id": "ALERT-001",
            },
        }

        store.save_state(state)

        store.save_resolution(
            "PRD",
            blocker_id,
            {
                "blocker_id": blocker_id,
                "artifact_type": "PRD",
                "status": "WAITING_FOR_HUMAN",
                "human_decisions": [],
                "pending_human_decisions": questions,
            },
        )

        # Answer only the first question.
        orchestrator.answer(
            store.load_state(),
            "Product Owner",
            actor="tester",
        )

        updated_state = store.load_state()

        # Two material decisions must remain outstanding.
        assert len(updated_state["open_questions"]) == 2

        assert [
            q["question_id"]
            for q in updated_state["open_questions"]
        ] == ["Q-002", "Q-003"]

        # The workflow must remain paused.
        assert (
            updated_state["workflow_state"]
            == "PAUSED_WAITING_FOR_HUMAN"
        )

        assert (
            updated_state["stage"]
            == "HUMAN_DECISION_REQUIRED"
        )

        # Remaining decisions must still require action.
        assert len(updated_state["pending_actions"]) == 2

        # The parent blocker must not be resolved.
        resolution = store.load_resolution("PRD", blocker_id)

        assert resolution["status"] == "WAITING_FOR_HUMAN"

        assert len(
            resolution["pending_human_decisions"]
        ) == 2

        # The answered decision must be auditable.
        assert len(resolution["human_decisions"]) == 1

        assert (
            resolution["human_decisions"][0]["question_id"]
            == "Q-001"
        )
                # Answer the second decision after reloading state.
        orchestrator.answer(
            store.load_state(),
            "5000 USD",
            actor="tester",
        )

        state_after_second = store.load_state()

        assert len(state_after_second["open_questions"]) == 1
        assert state_after_second["workflow_state"] == (
            "PAUSED_WAITING_FOR_HUMAN"
        )

        # Answer the final decision.
        orchestrator.answer(
            store.load_state(),
            "Executive Sponsor",
            actor="tester",
        )

        final_state = store.load_state()
        final_resolution = store.load_resolution(
            "PRD", blocker_id
        )

        # All questions have been answered.
        assert final_state["open_questions"] == []
        assert final_state["pending_actions"] == []

        # The workflow can resume resolution.
        assert final_state["workflow_state"] == "READY_TO_RUN"
        assert final_state["stage"] == "BACKWARD_RESOLUTION"

        # The parent blocker is not automatically resolved.
        assert final_resolution["status"] == "IN_PROGRESS"
        assert final_resolution["pending_human_decisions"] == []

        # All three human decisions remain auditable.
        assert len(final_resolution["human_decisions"]) == 3

        assert {
            decision["question_id"]
            for decision in final_resolution["human_decisions"]
        } == {"Q-001", "Q-002", "Q-003"}
def test_blocker_cannot_resolve_with_pending_human_decisions():
    """
    A resolver's RESOLVED response must not override
    an outstanding material human decision.
    """
    from test_runtime_v615 import make_runtime

    store, orchestrator = make_runtime()

    class PrematureResolutionAdapter:
        def generate(self, *, system, user):
            return {
                "resolution_status": "RESOLVED",
                "resolution_summary": "Claimed complete",
                "authoritative_business_rules": [],
                "acceptance_intent": [],
                "human_decisions": [],
                "downstream_dependencies": [],
                "evidence_refs": [],
            }

    orchestrator.adapter = PrematureResolutionAdapter()

    # Initialize the backward-resolution workflow.
    orchestrator.start_blocker_resolution(
        store.load_state(),
        actor="tester",
    )

    state = store.load_state()
    blocker_id = "DEP-PRD-001"

    pending_question = {
        "question_id": "Q-UNANSWERED",
        "question": "Who can authorize the budget override?",
        "blocking": True,
        "classification": "HUMAN_DECISION",
        "status": "OPEN",
        "blocker_id": blocker_id,
        "artifact_type": "PRD",
    }

    store.save_resolution(
        "PRD",
        blocker_id,
        {
            "blocker_id": blocker_id,
            "artifact_type": "PRD",
            "status": "WAITING_FOR_HUMAN",
            "human_decisions": [],
            "pending_human_decisions": [pending_question],
        },
    )

    state["open_questions"] = [pending_question]
    state["pending_actions"] = [{
        "type": "DECISION_REQUIRED",
        "question_id": "Q-UNANSWERED",
        "blocker_id": blocker_id,
    }]
    state["workflow_state"] = "PAUSED_WAITING_FOR_HUMAN"
    state["stage"] = "HUMAN_DECISION_REQUIRED"
    store.save_state(state)

    # Simulate an attempt to resume resolution prematurely.
    orchestrator.resolve_blockers(
        store.load_state(),
        actor="tester",
    )

    resolution = store.load_resolution("PRD", blocker_id)
    plan = store.load_resolution_plan("PRD")
    updated_state = store.load_state()

    assert resolution["status"] != "RESOLVED"
    assert plan["status"] != "RESOLVED"
    assert updated_state["resolution_workflow"]["status"] != "RESOLVED"
    assert len(updated_state["open_questions"]) == 1
def test_retry_cannot_bypass_active_human_decision():
    """Generic retry must not discard mandatory Product Owner decisions."""
    import pytest
    from test_runtime_v615 import make_runtime

    store, orchestrator = make_runtime()

    orchestrator.start_blocker_resolution(
        store.load_state(),
        actor="tester",
    )

    state = store.load_state()
    blocker_id = "DEP-PRD-001"

    question = {
        "question_id": "Q-RETRY-001",
        "question": "Who approves the budget override?",
        "blocking": True,
        "classification": "HUMAN_DECISION",
        "status": "OPEN",
        "blocker_id": blocker_id,
        "artifact_type": "PRD",
    }

    store.save_resolution(
        "PRD",
        blocker_id,
        {
            "blocker_id": blocker_id,
            "artifact_type": "PRD",
            "status": "WAITING_FOR_HUMAN",
            "human_decisions": [],
            "pending_human_decisions": [question],
        },
    )

    state["open_questions"] = [question]
    state["pending_actions"] = [{
        "type": "DECISION_REQUIRED",
        "question_id": question["question_id"],
        "blocker_id": blocker_id,
    }]
    state["workflow_state"] = "PAUSED_WAITING_FOR_HUMAN"
    state["stage"] = "HUMAN_DECISION_REQUIRED"

    store.save_state(state)

    with pytest.raises(ValueError, match="human decision"):
        orchestrator.retry_pending_generation(
            store.load_state(),
            actor="tester",
        )

    updated_state = store.load_state()
    resolution = store.load_resolution("PRD", blocker_id)

    assert updated_state["stage"] == "HUMAN_DECISION_REQUIRED"
    assert updated_state["workflow_state"] == "PAUSED_WAITING_FOR_HUMAN"
    assert len(updated_state["open_questions"]) == 1
    assert len(updated_state["pending_actions"]) == 1
    assert resolution["status"] == "WAITING_FOR_HUMAN"
    assert len(resolution["pending_human_decisions"]) == 1
def test_transitive_approved_dependencies_include_full_payload():
    """Approved transitive ancestors must not be reduced to summaries."""
    from unittest.mock import Mock

    from runtime.orchestrator.product import ProductOrchestrator

    orchestrator = ProductOrchestrator.__new__(ProductOrchestrator)

    orchestrator.catalog = {
        "PRODUCT_CHARTER": {"owner": "product-lead", "depends_on": []},
        "PRODUCT_BRIEF": {
            "owner": "product-lead",
            "depends_on": ["PRODUCT_CHARTER"],
        },
        "PERSONAS": {
            "owner": "product-discovery",
            "depends_on": ["PRODUCT_BRIEF"],
        },
        "PRD": {
            "owner": "requirements",
            "depends_on": ["PERSONAS"],
        },
        "RISK_REGISTER": {
            "owner": "product-lead",
            "depends_on": [],
        },
    }

    approved = {
        "PRODUCT_CHARTER",
        "PRODUCT_BRIEF",
        "PERSONAS",
        "RISK_REGISTER",
    }

    state = {
        "initiative_id": "INIT-CONTEXT-001",
        "session_id": "RUN-CONTEXT-001",
        "artifacts": {
            typ: {
                "artifact_id": f"ART-{typ}",
                "version": "1",
                "status": "APPROVED",
            }
            for typ in approved
        },
    }

    def approval_envelope(s, typ, include_artifact=True):
        envelope = {
            "governance": {
                "artifact_id": f"ART-{typ}",
                "artifact_type": typ,
                "version": "1",
                "status": "APPROVED",
                "approval_id": f"APPROVAL-{typ}",
            }
        }

        if include_artifact:
            envelope["artifact"] = {
                "title": typ,
                "content": {
                    "authoritative_rule": f"RULE-{typ}",
                },
            }

        return envelope

    orchestrator._approval_envelope = Mock(
        side_effect=approval_envelope
    )

    orchestrator.store = Mock()
    orchestrator.store.load_artifact.side_effect = (
        lambda initiative_id, artifact_id, version: {
            "payload": {
                "title": artifact_id,
                "summary": f"Summary for {artifact_id}",
                "content": {
                    "authoritative_rule": f"RULE-{artifact_id.removeprefix('ART-')}",
                },
            }
        }
    )
    orchestrator.store.list_resolutions.return_value = []

    orchestrator.pf = __import__("pathlib").Path("/tmp/product-factory")
    orchestrator.schema = __import__("pathlib").Path("/tmp/schema.json")
    orchestrator.quality = {"minimum_quality": {"all": []}}

    context = orchestrator._context_package(state, "PRD")

    # Direct dependency has complete approved content.
    assert (
        context["direct_dependencies"]["PERSONAS"]["artifact"]
        ["content"]["authoritative_rule"]
        == "RULE-PERSONAS"
    )

    # Transitive dependencies must also have complete approved content.
    for typ in ("PRODUCT_CHARTER", "PRODUCT_BRIEF"):
        assert (
            context["approved_provenance"][typ]["artifact"]
            ["content"]["authoritative_rule"]
            == f"RULE-{typ}"
        )

        assert (
            context["approved_provenance"][typ]["governance"]
            ["approval_id"]
            == f"APPROVAL-{typ}"
        )

    # An unrelated approved artifact should remain summarized.
    assert "artifact" not in context["approved_provenance"]["RISK_REGISTER"]
    assert "summary" in context["approved_provenance"]["RISK_REGISTER"]
def test_circular_artifact_dependency_is_rejected():
    import pytest
    from runtime.orchestrator.product import ProductOrchestrator

    orchestrator = ProductOrchestrator.__new__(ProductOrchestrator)

    orchestrator.catalog = {
        "PRODUCT_CHARTER": {
            "owner": "product-lead",
            "depends_on": ["PRODUCT_BRIEF"],
        },
        "PRODUCT_BRIEF": {
            "owner": "product-lead",
            "depends_on": ["PERSONAS"],
        },
        "PERSONAS": {
            "owner": "product-discovery",
            "depends_on": ["PRODUCT_CHARTER"],
        },
    }

    with pytest.raises(
        ValueError,
        match="Circular artifact dependency detected",
    ):
        orchestrator._upstream_dependencies("PRODUCT_CHARTER")
def test_missing_upstream_artifact_is_rejected():
    import pytest
    from unittest.mock import Mock
    from pathlib import Path

    from runtime.orchestrator.product import ProductOrchestrator

    orchestrator = ProductOrchestrator.__new__(ProductOrchestrator)

    orchestrator.catalog = {
        "PRODUCT_CHARTER": {
            "owner": "product-lead",
            "depends_on": [],
        },
        "PRODUCT_BRIEF": {
            "owner": "product-lead",
            "depends_on": ["PRODUCT_CHARTER"],
        },
        "PRD": {
            "owner": "requirements",
            "depends_on": ["PRODUCT_BRIEF"],
        },
    }

    orchestrator.store = Mock()
    orchestrator.store.list_resolutions.return_value = []
    orchestrator.pf = Path("/tmp/product-factory")
    orchestrator.schema = Path("/tmp/schema.json")
    orchestrator.quality = {"minimum_quality": {"all": []}}

    state = {
        "initiative_id": "INIT-CONTEXT-002",
        "session_id": "RUN-CONTEXT-002",
        "artifacts": {
            "PRODUCT_BRIEF": {
                "artifact_id": "ART-PRODUCT_BRIEF",
                "version": "1",
                "status": "APPROVED",
            }
        },
    }

    with pytest.raises(
        ValueError,
        match="Required upstream artifact is missing: PRODUCT_CHARTER",
    ):
        orchestrator._context_package(state, "PRD")
def test_approved_dependency_without_approval_record_is_rejected():
    import pytest
    from pathlib import Path
    from unittest.mock import Mock

    from runtime.orchestrator.product import ProductOrchestrator

    orchestrator = ProductOrchestrator.__new__(ProductOrchestrator)

    orchestrator.catalog = {
        "PRODUCT_CHARTER": {
            "owner": "product-lead",
            "depends_on": [],
        },
        "PRODUCT_BRIEF": {
            "owner": "product-lead",
            "depends_on": ["PRODUCT_CHARTER"],
        },
    }

    orchestrator.store = Mock()

    orchestrator.store.load_artifact.return_value = {
        "payload": {
            "title": "Product Charter",
            "summary": "Approved business direction",
            "content": {
                "business_rule": "Human authorization required"
            },
        }
    }

    # Simulate an artifact with no durable approval record.
    orchestrator.store.latest_approval.return_value = None

    orchestrator.pf = Path("/tmp/product-factory")
    orchestrator.schema = Path("/tmp/schema.json")
    orchestrator.quality = {
        "minimum_quality": {"all": []}
    }

    state = {
        "initiative_id": "INIT-CONTEXT-003",
        "session_id": "RUN-CONTEXT-003",
        "artifacts": {
            "PRODUCT_CHARTER": {
                "artifact_id": "ART-PRODUCT_CHARTER",
                "version": "1",
                "status": "APPROVED",
            }
        },
    }

    with pytest.raises(
        ValueError,
        match="missing its immutable runtime approval record",
    ):
        orchestrator._context_package(
            state,
            "PRODUCT_BRIEF",
        )

    orchestrator.store.latest_approval.assert_called_once_with(
        "ART-PRODUCT_CHARTER",
        "1",
        "APPROVED",
    )
def test_blocker_resolution_failure_returns_structured_result():
    from tests.test_runtime_v615 import make_runtime

    store, orchestrator = make_runtime()

    # Remove a required upstream artifact to trigger
    # the context-integrity failure.
    state = store.load_state()
    state["artifacts"].pop("PRODUCT_CHARTER")
    store.save_state(state)

    result = orchestrator.resolve_blockers(
        store.load_state(),
        actor="tester",
    )

    assert isinstance(result, dict)
    assert result["status"] == "BLOCKED"
    assert result["artifact_type"] == "PRD"
    assert result["blocker_id"] == "DEP-PRD-001"
    assert "PRODUCT_CHARTER" in result["message"]

    updated_state = store.load_state()

    assert updated_state["workflow_state"] == "PAUSED_BLOCKED"
    assert updated_state["stage"] == "GENERATION_FAILED"

    # The original Product Definition blocker must remain unresolved.
    original_alert = next(
        alert
        for alert in updated_state["open_alerts"]
        if alert["type"] == "QUALITY_REVIEW_FAILED"
    )

    assert original_alert["resolved"] is False
def test_invalid_blocker_resolution_returns_structured_failure():
    from tests.test_runtime_v615 import make_runtime

    store, orchestrator = make_runtime()

    # Return an invalid response instead of a resolution JSON object.
    orchestrator.adapter.generate = lambda **kwargs: "invalid response"

    result = orchestrator.resolve_blockers(
        store.load_state(),
        actor="tester",
    )

    assert isinstance(result, dict)
    assert result["status"] == "BLOCKED"
    assert result["artifact_type"] == "PRD"
    assert result["blocker_id"] == "DEP-PRD-001"
    assert result["failure_type"] == "INVALID_MODEL_RESPONSE"

    state = store.load_state()

    assert state["workflow_state"] == "PAUSED_BLOCKED"
    assert state["stage"] == "INVALID_MODEL_RESPONSE"

    original_alert = next(
        alert
        for alert in state["open_alerts"]
        if alert["type"] == "QUALITY_REVIEW_FAILED"
    )

    assert original_alert["resolved"] is False

def test_generic_retry_cannot_bypass_failed_backward_resolution():
    """Generic retry must preserve an active failed BACKWARD resolution."""
    import pytest
    from tests.test_runtime_v615 import make_runtime

    store, orchestrator = make_runtime()

    # Simulate an invalid response from the resolution agent.
    orchestrator.adapter.generate = lambda **kwargs: "invalid response"

    result = orchestrator.resolve_blockers(
        store.load_state(),
        actor="tester",
    )

    assert result["status"] == "BLOCKED"
    assert result["failure_type"] == "INVALID_MODEL_RESPONSE"

    before = store.load_state()

    assert before["workflow_state"] == "PAUSED_BLOCKED"
    assert before["resolution_workflow"]["status"] == "ACTIVE"

    original_alert = next(
        alert
        for alert in before["open_alerts"]
        if alert["type"] == "QUALITY_REVIEW_FAILED"
    )

    assert original_alert["resolved"] is False

    # Generic retry must not clear the active resolution workflow.
    with pytest.raises(ValueError, match="resolve-blockers"):
        orchestrator.retry_pending_generation(
            store.load_state(),
            actor="tester",
        )

    after = store.load_state()

    assert after["workflow_state"] == before["workflow_state"]
    assert after["stage"] == before["stage"]
    assert after["resolution_workflow"] == before["resolution_workflow"]

    preserved_alert = next(
        alert
        for alert in after["open_alerts"]
        if alert["alert_id"] == original_alert["alert_id"]
    )

    assert preserved_alert["resolved"] is False

    plan = store.load_resolution_plan("PRD")

    assert plan["status"] == "ACTIVE"


def test_failed_backward_resolution_recovers_using_existing_plan():
    """Technical failure recovery must reuse the governed resolution plan."""
    from tests.test_runtime_v615 import make_runtime

    store, orchestrator = make_runtime()

    # Simulate a technical failure in the resolution adapter.
    orchestrator.adapter.generate = lambda **kwargs: "invalid response"

    failed = orchestrator.resolve_blockers(
        store.load_state(),
        actor="tester",
    )

    assert failed["status"] == "BLOCKED"
    assert failed["failure_type"] == "INVALID_MODEL_RESPONSE"

    blocked_state = store.load_state()

    assert blocked_state["workflow_state"] == "PAUSED_BLOCKED"
    assert blocked_state["resolution_workflow"]["status"] == "ACTIVE"

    original_plan = store.load_resolution_plan("PRD")
    original_created_at = original_plan["created_at"]
    original_blocker_ids = [
        item["blocker_id"]
        for item in original_plan["items"]
    ]

    assert len(original_blocker_ids) == 4

    # Correct the simulated technical failure.
    # This response is test-only and does not represent business approval.
    def valid_resolution(*, system, user):
        return {
            "resolution_status": "RESOLVED",
            "resolution_summary": "Technical recovery test resolution.",
            "authoritative_business_rules": [
                "Synthetic test rule; not production-approved."
            ],
            "acceptance_intent": [
                "Synthetic test acceptance intent."
            ],
            "human_decisions": [],
            "downstream_dependencies": [],
            "evidence_refs": ["SYNTHETIC_TEST_EVIDENCE"],
        }

    orchestrator.adapter.generate = valid_resolution

    recovered = orchestrator.resolve_blockers(
        store.load_state(),
        actor="tester",
    )

    assert recovered["status"] == "RESOLVED"
    assert recovered["artifact_type"] == "PRD"
    assert set(recovered["resolution_refs"]) == set(original_blocker_ids)

    recovered_state = store.load_state()
    recovered_plan = store.load_resolution_plan("PRD")

    assert recovered_state["workflow_state"] == "READY_TO_RUN"
    assert recovered_state["stage"] == "PRODUCT_DEFINITION"
    assert recovered_state["resolution_workflow"]["status"] == "RESOLVED"

    # The original plan must have been reused, not replaced.
    assert recovered_plan["created_at"] == original_created_at
    assert [
        item["blocker_id"]
        for item in recovered_plan["items"]
    ] == original_blocker_ids

    assert recovered_plan["status"] == "RESOLVED"
    assert all(
        item["status"] == "RESOLVED"
        for item in recovered_plan["items"]
    )

    for blocker_id in original_blocker_ids:
        resolution = store.load_resolution("PRD", blocker_id)
        assert resolution["status"] == "RESOLVED"
