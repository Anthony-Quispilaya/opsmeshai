from agents.schemas import RouterDecision

BLOCKLIST = ["drop table", "delete user", "rm -rf", "shutdown system"]


class GuardrailViolation(ValueError):
    pass


class GuardrailAgent:
    def check(self, user_message: str, decision: RouterDecision) -> str:
        text = user_message.lower()
        if any(token in text for token in BLOCKLIST):
            raise GuardrailViolation("Guardrail blocked destructive or unsafe request.")

        # Default deny unknown tools before execution.
        known_tools = {"echo", "http_get", "noop_workflow", None}
        if decision.tool_name not in known_tools:
            raise GuardrailViolation(f"Unknown tool '{decision.tool_name}' blocked by default-deny policy.")

        return "allow"
