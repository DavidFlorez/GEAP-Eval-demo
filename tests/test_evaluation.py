"""
Unit and Integration Tests for Contract Review Evaluation Demo.
Verifies:
- 18 criteria ground truth integrity and contract file availability
- Tool functionality (outline, section reader, clause search, cross-reference verifier)
- Baseline Agent and Tool-Augmented Agent execution
- Evaluation metrics (Accuracy, LLM Judge, Efficiency)
- Report exports (JSON, Markdown, HTML)
"""

import unittest
from pathlib import Path
import json

from eval.schema import (
    DATASET_VERSION,
    EVAL_JUDGE_VERSION,
    AGENT_CONFIG_VERSION,
    CHECKLIST_18_CRITERIA,
)
from eval.accuracy_metric import AccuracyMetricEvaluator
from eval.judge_evaluator import LLMJudgeEvaluator
from eval.efficiency_metric import EfficiencyMetricEvaluator
from eval.harness import EvaluationHarness
from agents.tools import ContractToolRegistry
from agents.baseline_agent import BaselineAgent
from agents.tool_augmented_agent import ToolAugmentedAgent


class TestContractEvaluationSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_dir = Path(__file__).resolve().parent.parent
        cls.dataset_dir = cls.base_dir / "dataset"
        cls.contracts_dir = cls.dataset_dir / "v1_contracts"
        cls.reports_dir = cls.base_dir / "reports"

        gt_path = cls.dataset_dir / "ground_truth_v1.json"
        with open(gt_path, "r", encoding="utf-8") as f:
            cls.ground_truth = json.load(f)

    def test_checklist_criteria_count(self):
        """Verify that exactly 18 compliance criteria are defined."""
        self.assertEqual(len(CHECKLIST_18_CRITERIA), 18)
        self.assertEqual(len(self.ground_truth["criteria_definitions"]), 18)

    def test_contracts_exist(self):
        """Verify all 3 synthetic contracts are present and non-empty."""
        expected_contracts = [
            "01_standard_nda",
            "02_vendor_services_agreement",
            "03_master_services_agreement",
        ]
        for cid in expected_contracts:
            matches = list(self.contracts_dir.glob(f"*{cid}*.md"))
            self.assertTrue(len(matches) > 0, f"Contract {cid} not found")
            content = matches[0].read_text(encoding="utf-8")
            self.assertTrue(len(content) > 500, f"Contract {cid} is too short")

    def test_ground_truth_covers_all_criteria(self):
        """Verify ground truth contains expected values for each contract across all 18 points."""
        contracts = self.ground_truth["contracts"]
        self.assertEqual(len(contracts), 3)

        for cid, data in contracts.items():
            checklist = data["checklist"]
            self.assertEqual(len(checklist), 18, f"Contract {cid} does not have 18 checklist items")
            for crit in CHECKLIST_18_CRITERIA:
                c_id = crit["id"]
                self.assertIn(c_id, checklist, f"Missing {c_id} in {cid}")
                item = checklist[c_id]
                self.assertIn("target_section", item)
                self.assertIn("expected_value", item)
                self.assertIn("required_elements", item)

    def test_tools_functionality(self):
        """Verify outline, section reader, clause search, and cross-reference verification."""
        registry = ContractToolRegistry(contracts_dir=self.contracts_dir)

        # 1. Outline
        outline_res = registry.get_contract_outline("01_standard_nda")
        self.assertGreater(outline_res["total_sections"], 5)

        # 2. Section Reader
        sec_res = registry.get_contract_section("01_standard_nda", "SECTION 6")
        self.assertTrue(sec_res["found"])
        self.assertIn("$50,000", sec_res["content"])

        # 3. Clause Search
        search_res = registry.search_contract_clauses("02_vendor_services_agreement", "Cyber Risk", top_k=2)
        self.assertGreater(search_res["matches_count"], 0)

        # 4. Cross Reference Verifier
        xref_res = registry.verify_cross_reference(
            "03_master_services_agreement",
            "SECTION 11",
            "Schedule B",
        )
        self.assertTrue(xref_res["verified"])
        self.assertIn("SCHEDULE B", xref_res["target_title"])

    def test_baseline_agent_run(self):
        """Verify Baseline Agent runs and outputs 18 reviews."""
        agent = BaselineAgent(provider="mock")
        text = (self.contracts_dir / "01_standard_nda.md").read_text(encoding="utf-8")
        result = agent.review_contract("01_standard_nda", text)

        self.assertEqual(result.agent_type, "baseline")
        self.assertEqual(len(result.reviews), 18)
        self.assertEqual(result.tool_calls_count, 0)
        self.assertGreater(result.total_tokens, 0)

    def test_tool_augmented_agent_run(self):
        """Verify Tool-Augmented Agent uses tools and outputs 18 grounded reviews."""
        agent = ToolAugmentedAgent(contracts_dir=self.contracts_dir, provider="mock")
        text = (self.contracts_dir / "03_master_services_agreement.md").read_text(encoding="utf-8")
        result = agent.review_contract("03_master_services_agreement", text)

        self.assertEqual(result.agent_type, "tool_augmented")
        self.assertEqual(len(result.reviews), 18)
        self.assertGreater(result.tool_calls_count, 10)
        self.assertGreater(len(result.tool_trace), 3)

    def test_accuracy_and_judge_evaluators(self):
        """Test accuracy evaluation and LLM-as-a-judge rubric scoring."""
        acc_eval = AccuracyMetricEvaluator(self.ground_truth)
        judge_eval = LLMJudgeEvaluator(provider="mock")

        # Test accurate review
        from eval.schema import CriterionReview
        good_review = CriterionReview(
            criterion_id="liability_cap",
            status="present",
            findings="Direct damages capped at $50,000 USD; excludes breach of Section 2 or Section 8. Consequential damages waived.",
            cited_section="Section 6.1",
            exact_quote="SHALL EXCEED FIFTY THOUSAND U.S. DOLLARS ($50,000 USD)",
            confidence=0.95,
        )

        status_match, cit_match, elem_cov, comp_acc = acc_eval.evaluate_criterion(
            "01_standard_nda", "liability_cap", good_review
        )
        self.assertTrue(status_match)
        self.assertTrue(cit_match)
        self.assertGreaterEqual(comp_acc, 0.90)

        score, rationale = judge_eval.judge_criterion(
            contract_title="Mutual NDA",
            criterion_name="Limitation of Liability",
            expected_value="Direct damages capped at $50,000 USD",
            expected_section="Section 6.1",
            review=good_review,
            status_match=status_match,
            citation_match=cit_match,
            element_coverage=elem_cov,
        )
        self.assertGreaterEqual(score, 4.0)

    def test_full_evaluation_harness(self):
        """Verify complete evaluation harness execution and report file generation."""
        harness = EvaluationHarness(
            dataset_dir=self.dataset_dir,
            reports_dir=self.reports_dir,
            provider="mock",
        )
        report = harness.run_full_suite()

        self.assertEqual(report.dataset_version, DATASET_VERSION)
        self.assertEqual(report.eval_judge_version, EVAL_JUDGE_VERSION)
        self.assertEqual(report.agent_config_version, AGENT_CONFIG_VERSION)
        self.assertEqual(len(report.contract_breakdowns), 3)

        # Tool-Augmented should outperform Baseline on accuracy and judge score
        self.assertGreater(
            report.tool_augmented_summary["mean_check_accuracy"],
            report.baseline_summary["mean_check_accuracy"],
        )
        self.assertGreater(
            report.tool_augmented_summary["mean_reasoning_quality"],
            report.baseline_summary["mean_reasoning_quality"],
        )

        # Verify output files exist
        self.assertTrue((self.reports_dir / "evaluation_results.json").exists())
        self.assertTrue((self.reports_dir / "evaluation_report.md").exists())
        self.assertTrue((self.reports_dir / "evaluation_report.html").exists())


if __name__ == "__main__":
    unittest.main()
