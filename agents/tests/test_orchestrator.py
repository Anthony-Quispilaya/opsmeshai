import pytest

from agents.orchestrator import AgentOrchestrator, OrchestratorError


def test_orchestrator_raises_when_llm_is_unavailable() -> None:
    orchestrator = AgentOrchestrator()
    orchestrator.llm.api_key = ""

    with pytest.raises(OrchestratorError) as exc:
        orchestrator.run_turn("what do you do?")

    assert exc.value.code == "llm_not_configured"
