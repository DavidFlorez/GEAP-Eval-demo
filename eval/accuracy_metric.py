"""
Accuracy Metric Engine for 18-Point Contract Review Evaluation.
Computes:
- Status Match (present / silent / compliant / risk_flag)
- Section Citation Match (exact section, multi-section, and schedule references)
- Required Elements Coverage (substring/keyword recall against ground truth)
- Composite Check_Accuracy (0.0 to 1.0)
"""

import re
from typing import Dict, Any, List, Tuple
from eval.schema import CriterionReview, CriterionScore


class AccuracyMetricEvaluator:
    """Evaluates factual extraction and citation accuracy against ground truth."""

    def __init__(self, ground_truth: Dict[str, Any]):
        self.ground_truth = ground_truth

    def evaluate_criterion(
        self,
        contract_id: str,
        criterion_id: str,
        review: CriterionReview,
    ) -> Tuple[bool, bool, float, float]:
        """
        Evaluate a single criterion review.
        Returns:
            (status_match, citation_match, element_coverage, composite_accuracy)
        """
        contract_gt = self.ground_truth.get("contracts", {}).get(contract_id, {})
        checklist = contract_gt.get("checklist", {})
        gt_item = checklist.get(criterion_id, {})

        if not gt_item:
            # If not in ground truth, neutral defaults
            return (True, True, 1.0, 1.0)

        expected_status = gt_item.get("status", "present")
        expected_section = gt_item.get("target_section", "")
        required_elements = gt_item.get("required_elements", [])

        # 1. Status Match
        # Accept 'silent' or 'silent_or_not_applicable' or 'not_applicable' equivalence
        agent_status = review.status.lower()
        if "silent" in expected_status or "not_applicable" in expected_status:
            status_match = "silent" in agent_status or "not_applicable" in agent_status or "absent" in agent_status
        else:
            status_match = agent_status == expected_status.lower() or agent_status in ("present", "compliant")

        # 2. Section Citation Match
        citation_match = self._evaluate_citation(review.cited_section, expected_section)

        # 3. Required Elements Coverage
        element_coverage = self._evaluate_elements(
            f"{review.findings} {review.exact_quote} {review.cited_section}",
            required_elements,
        )

        # 4. Composite Check_Accuracy
        # Weighting: 35% Status match, 30% Citation accuracy, 35% Element coverage
        composite_accuracy = (
            (0.35 if status_match else 0.0)
            + (0.30 if citation_match else 0.0)
            + (0.35 * element_coverage)
        )

        return (status_match, citation_match, element_coverage, round(composite_accuracy, 4))

    def _evaluate_citation(self, agent_citation: str, expected_section: str) -> bool:
        if not expected_section or expected_section.lower() in ("general", "n/a"):
            return True

        if not agent_citation:
            return False

        agent_clean = agent_citation.lower().replace("section", "").replace("schedule", "sched")
        expected_clean = expected_section.lower().replace("section", "").replace("schedule", "sched")

        # Check for numbers and schedules present
        expected_tokens = re.findall(r"\b\d+\.?\d*|\bsched\s+[a-z]", expected_clean)
        agent_tokens = re.findall(r"\b\d+\.?\d*|\bsched\s+[a-z]", agent_clean)

        if not expected_tokens:
            return expected_clean.strip() in agent_clean

        # If any primary expected section matches, count as match or partial
        matches = [tok for tok in expected_tokens if tok in agent_tokens or any(tok in a for a in agent_tokens)]
        return len(matches) >= max(1, len(expected_tokens) // 2)

    def _evaluate_elements(self, text: str, required_elements: List[str]) -> float:
        if not required_elements:
            return 1.0

        text_lower = text.lower()
        matched = 0
        for elem in required_elements:
            elem_clean = elem.lower().strip()
            # Normalize punctuation
            elem_tokens = [t for t in re.split(r"\W+", elem_clean) if t]
            if not elem_tokens:
                continue
            if elem_clean in text_lower or all(t in text_lower for t in elem_tokens):
                matched += 1

        return round(matched / len(required_elements), 4)
