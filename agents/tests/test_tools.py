from agents.tools import ToolRegistry


def test_tool_registry_returns_error_for_unknown_tool() -> None:
    result = ToolRegistry().execute("unknown_tool", "payload")
    assert result.ok is False
    assert result.error is not None


def test_echo_tool_round_trip() -> None:
    result = ToolRegistry().execute("echo", "hello")
    assert result.ok is True
    assert result.output == "hello"
