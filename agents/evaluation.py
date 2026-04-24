class EvaluationAgent:
    """Evaluation stub to keep orchestration surface complete in Sprint 3."""

    def sample_trace(self, trace_steps: list[str]) -> dict:
        return {"sampled": False, "steps_count": len(trace_steps)}
