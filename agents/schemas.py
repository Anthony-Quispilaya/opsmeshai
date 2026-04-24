from pydantic import BaseModel, Field


class RouterDecision(BaseModel):
    intent: str = Field(description="question, action, retrieve, or unsafe")
    selected_agent: str = Field(description="router, retrieval, workflow, guardrail, evaluation")
    tool_name: str | None = Field(default=None, description="tool to execute if needed")
    requires_retrieval: bool = False
    reasoning: str


class ToolExecutionResult(BaseModel):
    tool_name: str
    ok: bool
    output: str
    error: str | None = None


class OrchestratorTrace(BaseModel):
    router: RouterDecision
    guardrail_action: str
    tool: ToolExecutionResult | None = None
    steps: list[str] = Field(default_factory=list)


class OrchestratorResult(BaseModel):
    assistant_message: str
    trace: OrchestratorTrace
