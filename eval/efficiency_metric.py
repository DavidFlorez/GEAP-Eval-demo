"""
Efficiency and Observability Metric Engine.
Tracks latency, token consumption, tool invocations, and estimated operational cost.
"""

from typing import Dict, Any
from eval.schema import AgentRunResult


class EfficiencyMetricEvaluator:
    """Computes runtime performance, token economics, and tool efficiency."""

    # Pricing benchmark: Gemini 2.0 Flash / GPT-4o-mini scale ($/1M tokens)
    INPUT_COST_PER_MILLION: float = 0.15
    OUTPUT_COST_PER_MILLION: float = 0.60

    @classmethod
    def compute_metrics(cls, run_result: AgentRunResult) -> Dict[str, Any]:
        prompt_cost = (run_result.prompt_tokens / 1_000_000) * cls.INPUT_COST_PER_MILLION
        completion_cost = (run_result.completion_tokens / 1_000_000) * cls.OUTPUT_COST_PER_MILLION
        total_cost = prompt_cost + completion_cost

        tool_intensity = (
            run_result.tool_calls_count / max(1, len(run_result.reviews))
            if run_result.reviews
            else 0.0
        )

        return {
            "latency_seconds": round(run_result.latency_seconds, 3),
            "prompt_tokens": run_result.prompt_tokens,
            "completion_tokens": run_result.completion_tokens,
            "total_tokens": run_result.total_tokens,
            "tool_calls_count": run_result.tool_calls_count,
            "tool_calls_breakdown": run_result.tool_calls_breakdown,
            "tool_call_intensity": round(tool_intensity, 2),
            "estimated_cost_usd": round(total_cost, 6),
        }
