from __future__ import annotations

import json
import urllib.parse
import urllib.request
from collections.abc import Callable

from agents.schemas import ToolExecutionResult

ToolFn = Callable[[str], ToolExecutionResult]


def _echo(input_text: str) -> ToolExecutionResult:
    return ToolExecutionResult(tool_name="echo", ok=True, output=input_text)


def _noop_workflow(input_text: str) -> ToolExecutionResult:
    payload = {
        "workflow": "noop_workflow",
        "received": input_text,
        "steps": ["accepted", "validated", "completed"],
    }
    return ToolExecutionResult(tool_name="noop_workflow", ok=True, output=json.dumps(payload))


def _http_get(input_text: str) -> ToolExecutionResult:
    target = input_text.replace("get ", "").replace("http ", "").strip()
    if not target.startswith("http"):
        target = f"http://{target}"

    parsed = urllib.parse.urlparse(target)
    if parsed.hostname not in {"example.com", "localhost", "127.0.0.1"}:
        return ToolExecutionResult(
            tool_name="http_get",
            ok=False,
            output="",
            error="http_get blocked: host not in allowlist.",
        )

    try:
        with urllib.request.urlopen(target, timeout=5) as response:
            body = response.read(500).decode("utf-8", errors="ignore")
            return ToolExecutionResult(
                tool_name="http_get",
                ok=True,
                output=f"status={response.status}; body={body}",
            )
    except Exception as exc:  # noqa: BLE001
        return ToolExecutionResult(tool_name="http_get", ok=False, output="", error=str(exc))


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolFn] = {
            "echo": _echo,
            "noop_workflow": _noop_workflow,
            "http_get": _http_get,
        }

    def execute(self, tool_name: str, input_text: str) -> ToolExecutionResult:
        if tool_name not in self._tools:
            return ToolExecutionResult(
                tool_name=tool_name,
                ok=False,
                output="",
                error="Unknown tool requested.",
            )
        return self._tools[tool_name](input_text)
