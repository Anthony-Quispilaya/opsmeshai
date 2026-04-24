from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from agents.evaluation import EvaluationAgent
from agents.guardrail import GuardrailAgent, GuardrailViolation
from agents.llm import LLMResponder
from agents.retrieval import RetrievalAgent
from agents.router import RouterAgent
from agents.schemas import OrchestratorResult, OrchestratorTrace
from agents.tools import ToolRegistry


class OrchestratorError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class AgentOrchestrator:
    def __init__(self) -> None:
        self.router = RouterAgent()
        self.guardrail = GuardrailAgent()
        self.retrieval = RetrievalAgent()
        self.evaluation = EvaluationAgent()
        self.tools = ToolRegistry()
        self.llm = LLMResponder()

    def run_turn(
        self,
        user_message: str,
        timeout_seconds: int = 8,
        history: list[dict] | None = None,
    ) -> OrchestratorResult:
        decision = self.router.route(user_message)
        steps: list[str] = [f"router:{decision.intent}:{decision.selected_agent}"]

        try:
            guardrail_action = self.guardrail.check(user_message, decision)
        except GuardrailViolation as exc:
            raise OrchestratorError("guardrail_blocked", str(exc)) from exc

        tool_result = None
        assistant_message = ""

        if decision.requires_retrieval:
            retrieved = self.retrieval.retrieve(user_message)
            steps.append("retrieval:stub")
            assistant_message = retrieved
        elif decision.tool_name:
            steps.append(f"tool:{decision.tool_name}")
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self.tools.execute, decision.tool_name, user_message)
                    tool_result = future.result(timeout=timeout_seconds)
            except FuturesTimeoutError as exc:
                raise OrchestratorError("tool_timeout", f"Tool '{decision.tool_name}' timed out.") from exc

            if tool_result is None or not tool_result.ok:
                error = tool_result.error if tool_result else "Tool execution failed."
                raise OrchestratorError("tool_error", error or "Tool execution failed.")

            assistant_message = f"Tool {tool_result.tool_name} executed successfully.\n{tool_result.output}"
        else:
            if self.llm.enabled:
                try:
                    assistant_message = self.llm.generate_reply(user_message, history=history)
                    steps.append("llm:openai:provider-default")
                except Exception as exc:  # noqa: BLE001
                    steps.append("llm:fallback")
                    assistant_message = (
                        "Router response fallback (LLM unavailable). "
                        f"You said: '{user_message}'. Error: {exc}"
                    )
            else:
                assistant_message = (
                    "Router response: no tool execution required. "
                    f"You said: '{user_message}'"
                )

        eval_sample = self.evaluation.sample_trace(steps)
        steps.append(f"evaluation:sampled={eval_sample['sampled']}")

        trace = OrchestratorTrace(
            router=decision,
            guardrail_action=guardrail_action,
            tool=tool_result,
            steps=steps,
        )
        return OrchestratorResult(assistant_message=assistant_message, trace=trace)
