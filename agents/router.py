from agents.schemas import RouterDecision


class RouterAgent:
    """Deterministic router for Sprint 3 MVP."""

    def route(self, user_message: str) -> RouterDecision:
        text = user_message.strip().lower()
        if any(token in text for token in ["drop table", "delete user", "rm -rf"]):
            return RouterDecision(
                intent="unsafe",
                selected_agent="guardrail",
                tool_name=None,
                requires_retrieval=False,
                reasoning="Message includes destructive command patterns.",
            )

        if text.startswith("http ") or text.startswith("get http"):
            return RouterDecision(
                intent="action",
                selected_agent="workflow",
                tool_name="http_get",
                requires_retrieval=False,
                reasoning="Message asks for HTTP fetch behavior.",
            )

        if "echo " in text:
            return RouterDecision(
                intent="action",
                selected_agent="workflow",
                tool_name="echo",
                requires_retrieval=False,
                reasoning="Message explicitly requests echo behavior.",
            )

        if any(token in text for token in ["workflow", "run step", "execute"]):
            return RouterDecision(
                intent="action",
                selected_agent="workflow",
                tool_name="noop_workflow",
                requires_retrieval=False,
                reasoning="Message requests workflow execution.",
            )

        if any(token in text for token in ["search", "retrieve", "document", "knowledge"]):
            return RouterDecision(
                intent="retrieve",
                selected_agent="retrieval",
                tool_name=None,
                requires_retrieval=True,
                reasoning="Message is retrieval-oriented.",
            )

        return RouterDecision(
            intent="question",
            selected_agent="router",
            tool_name=None,
            requires_retrieval=False,
            reasoning="Default conversational path.",
        )
