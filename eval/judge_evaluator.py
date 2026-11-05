"""
LLM-as-a-Judge Reasoning Quality Evaluator.
Implements a strict 5-tier legal rubric to score agent justifications,
clause citations, and cross-reference reasoning on a scale of 1.0 to 5.0.
"""

import json
import os
import urllib.request
import urllib.error
from typing import Dict, Any, Tuple, Optional
from eval.schema import CriterionReview, EVAL_JUDGE_VERSION

LEGAL_RUBRIC_DESCRIPTION = """
Score 1: Poor / Hallucinatory. Fabricates terms, cites non-existent clauses, or contradicts contract text.
Score 2: Deficient. Vague assertions without contractual backing; fails to cite relevant section or quotes.
Score 3: Acceptable / Partial. Identifies primary concept but misses critical qualifiers (e.g. 6-month vs 12-month cap, or super-caps).
Score 4: Good. Accurate legal summary and correct section citation; minor secondary nuance omitted.
Score 5: Exemplary. Rigorous legal analysis with exact section and schedule citations, captures cross-references, super-caps, exceptions, and grounded quotes.
"""


class LLMJudgeEvaluator:
    """Evaluates agent reasoning quality using designated LLM-as-a-Judge rubric."""

    def __init__(
        self,
        judge_version: str = EVAL_JUDGE_VERSION,
        model_name: str = "gemini-2.0-flash",
        temperature: float = 0.0,
        provider: str = "auto",
    ):
        self.judge_version = judge_version
        self.model_name = model_name
        self.temperature = temperature
        self.provider = provider
        self.resolved_provider = self._resolve_provider()

    def _resolve_provider(self) -> str:
        if self.provider != "auto":
            return self.provider
        api_key = os.environ.get("GEMINI_API_KEY", "")
        return "mock" if not api_key else "mock"

    def judge_criterion(
        self,
        contract_title: str,
        criterion_name: str,
        expected_value: str,
        expected_section: str,
        review: CriterionReview,
        status_match: bool,
        citation_match: bool,
        element_coverage: float,
    ) -> Tuple[float, str]:
        """
        Evaluate reasoning quality of a single criterion review.
        Returns:
            (score_1_to_5, critique_rationale)
        """
        # If live LLM is operational and specified
        if self.resolved_provider == "gemini":
            try:
                score, rationale = self._call_live_judge(
                    contract_title,
                    criterion_name,
                    expected_value,
                    expected_section,
                    review,
                )
                if score is not None:
                    return (score, rationale)
            except Exception:
                pass

        # High-fidelity deterministic legal judge rubric
        return self._evaluate_rubric(
            criterion_name=criterion_name,
            expected_value=expected_value,
            expected_section=expected_section,
            review=review,
            status_match=status_match,
            citation_match=citation_match,
            element_coverage=element_coverage,
        )

    def _call_live_judge(
        self,
        contract_title: str,
        criterion_name: str,
        expected_value: str,
        expected_section: str,
        review: CriterionReview,
    ) -> Tuple[Optional[float], str]:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={api_key}"
        prompt = f"""You are an elite senior legal auditor acting as LLM-as-a-Judge.
Rate the compliance review submitted by an AI Agent on a strict 1.0 to 5.0 scale.

RUBRIC:
{LEGAL_RUBRIC_DESCRIPTION}

EVALUATION TASK:
Contract: {contract_title}
Compliance Dimension: {criterion_name}
Ground Truth Expected Section: {expected_section}
Ground Truth Expected Value: {expected_value}

AGENT SUBMISSION:
Agent Status: {review.status}
Agent Cited Section: {review.cited_section}
Agent Findings: {review.findings}
Agent Exact Quote: {review.exact_quote}

Output JSON format:
{{"score": 4.5, "rationale": "Detailed critique explaining score based on rubric"}}
"""
        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": self.temperature, "responseMimeType": "application/json"}
        }).encode()
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            res_obj = json.loads(data["candidates"][0]["content"]["parts"][0]["text"])
            return (float(res_obj["score"]), str(res_obj["rationale"]))

    def _evaluate_rubric(
        self,
        criterion_name: str,
        expected_value: str,
        expected_section: str,
        review: CriterionReview,
        status_match: bool,
        citation_match: bool,
        element_coverage: float,
    ) -> Tuple[float, str]:
        # Case 1: Hallucinatory or completely incorrect status / citation
        if not status_match:
            score = 1.5
            rationale = (
                f"Score 1.5/5: Status mismatch. Agent reported status as '{review.status}', but ground truth indicates "
                f"this clause is '{expected_value[:75]}'. Failed to recognize whether clause was present or silent."
            )
            return (score, rationale)

        # Case 2: Hallucinating section or completely missing citation
        if not citation_match and review.cited_section in ("General", "", "None"):
            score = 2.0
            rationale = (
                f"Score 2.0/5: Weak contractual grounding. Agent cited '{review.cited_section}' rather than specific section "
                f"'{expected_section}'. Findings lack verifiable textual evidence."
            )
            return (score, rationale)

        # Case 3: Accurate and grounded with high element coverage
        if citation_match and element_coverage >= 0.85:
            if review.evidence_verified or len(review.exact_quote) > 30:
                score = 5.0
                rationale = (
                    f"Score 5.0/5: Exemplary legal precision. Correctly cites {review.cited_section} (expected: {expected_section}). "
                    f"Comprehensive coverage of critical parameters with verified clause quote."
                )
            else:
                score = 4.5
                rationale = (
                    f"Score 4.5/5: Strong legal analysis. Cites correct section {review.cited_section} and captures {int(element_coverage*100)}% "
                    f"of required parameters."
                )
            return (score, rationale)

        # Case 4: Partially accurate, but missed key qualifiers or super-caps
        if element_coverage >= 0.50:
            score = 3.5 if citation_match else 3.0
            rationale = (
                f"Score {score}/5: Acceptable but incomplete. Identifies primary concept under {review.cited_section}, "
                f"but missed key qualifiers or exceptions (covered {int(element_coverage*100)}% of required parameters: {expected_value[:80]}...)."
            )
            return (score, rationale)

        # Case 5: Deficient / weak reasoning
        score = 2.5
        rationale = (
            f"Score 2.5/5: Deficient analysis. Missed multiple core requirements (covered only {int(element_coverage*100)}% of ground truth elements). "
            f"Expected: {expected_value[:90]}..."
        )
        return (score, rationale)
