"""
Schema and data models for 18-point legal contract compliance review.
Includes criteria definitions, evaluation metrics data models, and version tags.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import json
from pathlib import Path

DATASET_VERSION = "v1.0"
EVAL_JUDGE_VERSION = "v1.0"
AGENT_CONFIG_VERSION = "v1.0"

CHECKLIST_18_CRITERIA: List[Dict[str, str]] = [
    {"id": "governing_law", "name": "Governing Law & Jurisdiction", "category": "Legal & Jurisdiction"},
    {"id": "liability_cap", "name": "Limitation of Liability & Caps", "category": "Risk & Financial Exposure"},
    {"id": "ip_assignment", "name": "IP Ownership & Work-for-Hire", "category": "Intellectual Property"},
    {"id": "indemnification_scope", "name": "Indemnification Obligations & Limits", "category": "Risk & Financial Exposure"},
    {"id": "termination_notice", "name": "Termination Notice Periods", "category": "Contract Lifecycle"},
    {"id": "confidentiality_term", "name": "Confidentiality Duration & Survival", "category": "Confidentiality & Privacy"},
    {"id": "audit_rights", "name": "Audit Rights & Compliance Inspection", "category": "Governance & Compliance"},
    {"id": "non_solicitation", "name": "Non-Solicitation of Personnel", "category": "Human Resources & Restrictive Covenants"},
    {"id": "payment_terms", "name": "Payment Timing & Late Fees", "category": "Commercial & Financial"},
    {"id": "dispute_resolution", "name": "Dispute Resolution & Arbitration", "category": "Legal & Jurisdiction"},
    {"id": "force_majeure", "name": "Force Majeure & Suspension Rights", "category": "Contract Lifecycle"},
    {"id": "assignment_change_of_control", "name": "Assignment & Change of Control", "category": "Contract Lifecycle"},
    {"id": "insurance_requirements", "name": "Insurance Coverage Requirements", "category": "Risk & Financial Exposure"},
    {"id": "warranty_period", "name": "Warranties & Warranty Period", "category": "Commercial & Quality"},
    {"id": "data_privacy_security", "name": "Data Privacy & Breach Notification", "category": "Confidentiality & Privacy"},
    {"id": "export_compliance", "name": "Export Control & Sanctions", "category": "Regulatory & Compliance"},
    {"id": "subcontracting_rights", "name": "Subcontracting Permissions & Liability", "category": "Governance & Operations"},
    {"id": "severability_entire_agreement", "name": "Severability & Entire Agreement", "category": "Boilerplate & Interpretation"},
]


@dataclass
class CriterionReview:
    criterion_id: str
    status: str  # "present", "silent_or_not_applicable", "compliant", "risk_flag"
    findings: str
    cited_section: str
    exact_quote: str = ""
    confidence: float = 1.0
    evidence_verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "criterion_id": self.criterion_id,
            "status": self.status,
            "findings": self.findings,
            "cited_section": self.cited_section,
            "exact_quote": self.exact_quote,
            "confidence": self.confidence,
            "evidence_verified": self.evidence_verified,
        }


@dataclass
class AgentRunResult:
    contract_id: str
    agent_type: str  # "baseline" or "tool_augmented"
    agent_config_version: str
    dataset_version: str
    reviews: Dict[str, CriterionReview]
    latency_seconds: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    tool_calls_count: int = 0
    tool_calls_breakdown: Dict[str, int] = field(default_factory=dict)
    tool_trace: List[Dict[str, Any]] = field(default_factory=list)
    raw_response: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "agent_type": self.agent_type,
            "agent_config_version": self.agent_config_version,
            "dataset_version": self.dataset_version,
            "reviews": {k: v.to_dict() for k, v in self.reviews.items()},
            "latency_seconds": self.latency_seconds,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "tool_calls_count": self.tool_calls_count,
            "tool_calls_breakdown": self.tool_calls_breakdown,
            "tool_trace": self.tool_trace,
        }


@dataclass
class CriterionScore:
    criterion_id: str
    criterion_name: str
    status_match: bool
    section_citation_match: bool
    element_coverage_score: float  # 0.0 to 1.0 (proportion of required ground-truth elements identified)
    check_accuracy: float  # 0.0 to 1.0 composite accuracy
    reasoning_quality: float  # 1.0 to 5.0 LLM-as-a-Judge score
    judge_rationale: str
    agent_cited_section: str
    expected_section: str
    agent_findings: str
    expected_value: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "criterion_id": self.criterion_id,
            "criterion_name": self.criterion_name,
            "status_match": self.status_match,
            "section_citation_match": self.section_citation_match,
            "element_coverage_score": self.element_coverage_score,
            "check_accuracy": self.check_accuracy,
            "reasoning_quality": self.reasoning_quality,
            "judge_rationale": self.judge_rationale,
            "agent_cited_section": self.agent_cited_section,
            "expected_section": self.expected_section,
            "agent_findings": self.agent_findings,
            "expected_value": self.expected_value,
        }


@dataclass
class ContractEvaluationSummary:
    contract_id: str
    contract_title: str
    agent_type: str
    criterion_scores: Dict[str, CriterionScore]
    mean_check_accuracy: float
    mean_reasoning_quality: float
    citation_accuracy: float
    total_checks_passed: int
    total_checks: int
    latency_seconds: float
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    tool_calls_count: int
    estimated_cost_usd: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_title": self.contract_title,
            "agent_type": self.agent_type,
            "criterion_scores": {k: v.to_dict() for k, v in self.criterion_scores.items()},
            "mean_check_accuracy": round(self.mean_check_accuracy, 4),
            "mean_reasoning_quality": round(self.mean_reasoning_quality, 2),
            "citation_accuracy": round(self.citation_accuracy, 4),
            "total_checks_passed": self.total_checks_passed,
            "total_checks": self.total_checks,
            "latency_seconds": round(self.latency_seconds, 3),
            "total_tokens": self.total_tokens,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "tool_calls_count": self.tool_calls_count,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
        }


@dataclass
class ComparativeRunReport:
    dataset_version: str
    eval_judge_version: str
    agent_config_version: str
    timestamp: str
    baseline_summary: Dict[str, Any]
    tool_augmented_summary: Dict[str, Any]
    delta: Dict[str, Any]
    contract_breakdowns: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_version": self.dataset_version,
            "eval_judge_version": self.eval_judge_version,
            "agent_config_version": self.agent_config_version,
            "timestamp": self.timestamp,
            "baseline_summary": self.baseline_summary,
            "tool_augmented_summary": self.tool_augmented_summary,
            "delta": self.delta,
            "contract_breakdowns": self.contract_breakdowns,
        }
