"""Regression tests for Product Factory v6.1.6 CLI blocker handling."""

import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


CLI_PATH = Path(__file__).resolve().parents[1] / "cli" / "ai_pdlc.py"


def load_resolution_function():
    """Load only the function, without executing the CLI parser."""
    tree = ast.parse(CLI_PATH.read_text())

    matches = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "run_blocker_resolution"
    ]

    assert len(matches) == 1

    module = ast.Module(body=matches, type_ignores=[])
    ast.fix_missing_locations(module)

    namespace = {
        "json": __import__("json"),
        "show": Mock(),
        "run_until_pause": Mock(),
    }

    exec(compile(module, str(CLI_PATH), "exec"), namespace)

    return namespace


def setup_case(result):
    namespace = load_resolution_function()

    store = Mock()
    store.load_state.return_value = {
        "workflow_state": "PAUSED_WAITING_FOR_HUMAN"
    }

    orchestrator = Mock()
    orchestrator.resolve_blockers.return_value = result

    return namespace, store, orchestrator


def test_blocked_does_not_resume(capsys):
    namespace, store, orchestrator = setup_case({
        "status": "BLOCKED",
        "artifact_type": "PRD",
        "blocker_id": "BLOCKER-001",
        "failure_type": "INVALID_RESOLUTION",
        "message": "Resolution validation failed",
    })

    result = namespace["run_blocker_resolution"](
        store, orchestrator, {}, "PRD"
    )

    output = capsys.readouterr().out

    assert result is False
    assert "BACKWARD resolution blocked" in output
    assert "INVALID_RESOLUTION" in output
    assert "Resolution validation failed" in output
    assert "BACKWARD resolution complete" not in output

    namespace["run_until_pause"].assert_not_called()


def test_waiting_for_human_does_not_resume(capsys):
    namespace, store, orchestrator = setup_case({
        "status": "WAITING_FOR_HUMAN",
        "artifact_type": "PRD",
        "blocker_id": "BLOCKER-002",
        "questions": [{
            "question": "Which business rule applies?",
            "recommendation": "Ask the Product Owner",
            "options": ["Option A", "Option B"],
        }],
    })

    result = namespace["run_blocker_resolution"](
        store, orchestrator, {}, "PRD"
    )

    output = capsys.readouterr().out

    assert result is False
    assert "HUMAN DECISION REQUIRED" in output
    assert "Which business rule applies?" in output

    namespace["run_until_pause"].assert_not_called()


def test_unexpected_status_does_not_resume(capsys):
    namespace, store, orchestrator = setup_case({
        "status": "UNKNOWN_STATUS",
        "artifact_type": "PRD",
    })

    result = namespace["run_blocker_resolution"](
        store, orchestrator, {}, "PRD"
    )

    output = capsys.readouterr().out

    assert result is False
    assert "Unexpected blocker-resolution status" in output

    namespace["run_until_pause"].assert_not_called()


def test_resolved_resumes_generation(capsys):
    namespace, store, orchestrator = setup_case({
        "status": "RESOLVED",
        "artifact_type": "PRD",
        "resolution_refs": ["BLOCKER-003"],
    })

    result = namespace["run_blocker_resolution"](
        store, orchestrator, {}, "PRD"
    )

    output = capsys.readouterr().out

    assert result is True
    assert "BACKWARD resolution complete" in output

    namespace["run_until_pause"].assert_called_once_with(
        store,
        orchestrator,
        store.load_state.return_value,
    )
