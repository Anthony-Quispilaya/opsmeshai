from agents.router import RouterAgent


def test_router_returns_schema_for_echo() -> None:
    decision = RouterAgent().route("echo hello world")
    assert decision.intent == "action"
    assert decision.selected_agent == "workflow"
    assert decision.tool_name == "echo"


def test_router_blocks_unsafe_prompt() -> None:
    decision = RouterAgent().route("please drop table users")
    assert decision.intent == "unsafe"
    assert decision.selected_agent == "guardrail"
