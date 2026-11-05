"""Evaluation package for Contract Review Agent Evaluation Demo."""

from eval.schema import (
    DATASET_VERSION,
    EVAL_JUDGE_VERSION,
    AGENT_CONFIG_VERSION,
    CHECKLIST_18_CRITERIA,
    CriterionReview,
    CriterionScore,
    AgentRunResult,
    ContractEvaluationSummary,
    ComparativeRunReport,
)
from eval.accuracy_metric import AccuracyMetricEvaluator
from eval.judge_evaluator import LLMJudgeEvaluator
from eval.efficiency_metric import EfficiencyMetricEvaluator
from eval.harness import EvaluationHarness

__all__ = [
    "DATASET_VERSION",
    "EVAL_JUDGE_VERSION",
    "AGENT_CONFIG_VERSION",
    "CHECKLIST_18_CRITERIA",
    "CriterionReview",
    "CriterionScore",
    "AgentRunResult",
    "ContractEvaluationSummary",
    "ComparativeRunReport",
    "AccuracyMetricEvaluator",
    "LLMJudgeEvaluator",
    "EfficiencyMetricEvaluator",
    "EvaluationHarness",
]
