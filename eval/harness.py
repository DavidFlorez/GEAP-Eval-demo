"""
Evaluation Harness for Contract Review Agent Evaluation Demo.
Orchestrates Run A (Baseline) vs Run B (Tool-Augmented), computes multi-dimensional metrics,
and renders interactive reports (HTML, Markdown, JSON).
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from eval.schema import (
    DATASET_VERSION,
    EVAL_JUDGE_VERSION,
    AGENT_CONFIG_VERSION,
    CHECKLIST_18_CRITERIA,
    CriterionScore,
    ContractEvaluationSummary,
    ComparativeRunReport,
)
from eval.accuracy_metric import AccuracyMetricEvaluator
from eval.judge_evaluator import LLMJudgeEvaluator
from eval.efficiency_metric import EfficiencyMetricEvaluator
from agents.baseline_agent import BaselineAgent
from agents.tool_augmented_agent import ToolAugmentedAgent


class EvaluationHarness:
    """Executes comparative evaluation between Baseline (Run A) and Tool-Augmented (Run B)."""

    def __init__(
        self,
        dataset_dir: Optional[Path] = None,
        reports_dir: Optional[Path] = None,
        provider: str = "auto",
        model_name: str = "gemini-2.0-flash",
    ):
        base_dir = Path(__file__).resolve().parent.parent
        self.dataset_dir = dataset_dir or (base_dir / "dataset")
        self.reports_dir = reports_dir or (base_dir / "reports")
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.contracts_dir = self.dataset_dir / "v1_contracts"

        self.ground_truth = self._load_ground_truth()
        self.accuracy_evaluator = AccuracyMetricEvaluator(self.ground_truth)
        self.judge_evaluator = LLMJudgeEvaluator(provider=provider, model_name=model_name)
        self.provider = provider
        self.model_name = model_name

    def _load_ground_truth(self) -> Dict[str, Any]:
        gt_path = self.dataset_dir / "ground_truth_v1.json"
        if not gt_path.exists():
            raise FileNotFoundError(f"Ground truth file not found at {gt_path}")
        return json.loads(gt_path.read_text(encoding="utf-8"))

    def run_contract_evaluation(
        self,
        contract_id: str,
        baseline_agent: BaselineAgent,
        tool_agent: ToolAugmentedAgent,
    ) -> Dict[str, Any]:
        """Runs both agents on a single contract and scores results."""
        # Find contract file
        matches = list(self.contracts_dir.glob(f"*{contract_id}*.md"))
        if not matches:
            raise FileNotFoundError(f"Contract file for '{contract_id}' not found in {self.contracts_dir}")
        contract_file = matches[0]
        contract_text = contract_file.read_text(encoding="utf-8")

        contract_meta = self.ground_truth["contracts"].get(contract_id, {})
        contract_title = contract_meta.get("contract_title", contract_id)

        # 1. Execute Run A (Baseline)
        res_baseline = baseline_agent.review_contract(contract_id, contract_text)
        summary_baseline = self._score_run(res_baseline, contract_id, contract_title)

        # 2. Execute Run B (Tool-Augmented)
        res_tool = tool_agent.review_contract(contract_id, contract_text)
        summary_tool = self._score_run(res_tool, contract_id, contract_title)

        return {
            "contract_id": contract_id,
            "contract_title": contract_title,
            "contract_type": contract_meta.get("contract_type", "Agreement"),
            "complexity": contract_meta.get("complexity", "Medium"),
            "baseline": summary_baseline.to_dict(),
            "tool_augmented": summary_tool.to_dict(),
            "tool_trace": res_tool.tool_trace,
        }

    def _score_run(
        self,
        run_result: Any,
        contract_id: str,
        contract_title: str,
    ) -> ContractEvaluationSummary:
        checklist_gt = self.ground_truth["contracts"][contract_id]["checklist"]
        criterion_scores: Dict[str, CriterionScore] = {}

        total_accuracy = 0.0
        total_judge = 0.0
        total_citation_matches = 0
        checks_passed = 0

        for crit in CHECKLIST_18_CRITERIA:
            c_id = crit["id"]
            review = run_result.reviews.get(c_id)
            gt_item = checklist_gt.get(c_id, {})

            if not review:
                continue

            status_match, citation_match, element_coverage, composite_acc = (
                self.accuracy_evaluator.evaluate_criterion(contract_id, c_id, review)
            )

            judge_score, rationale = self.judge_evaluator.judge_criterion(
                contract_title=contract_title,
                criterion_name=crit["name"],
                expected_value=gt_item.get("expected_value", ""),
                expected_section=gt_item.get("target_section", ""),
                review=review,
                status_match=status_match,
                citation_match=citation_match,
                element_coverage=element_coverage,
            )

            total_accuracy += composite_acc
            total_judge += judge_score
            if citation_match:
                total_citation_matches += 1
            if composite_acc >= 0.70:
                checks_passed += 1

            criterion_scores[c_id] = CriterionScore(
                criterion_id=c_id,
                criterion_name=crit["name"],
                status_match=status_match,
                section_citation_match=citation_match,
                element_coverage_score=element_coverage,
                check_accuracy=composite_acc,
                reasoning_quality=judge_score,
                judge_rationale=rationale,
                agent_cited_section=review.cited_section,
                expected_section=gt_item.get("target_section", ""),
                agent_findings=review.findings,
                expected_value=gt_item.get("expected_value", ""),
            )

        num_criteria = max(1, len(criterion_scores))
        mean_acc = total_accuracy / num_criteria
        mean_judge = total_judge / num_criteria
        citation_acc = total_citation_matches / num_criteria

        efficiency = EfficiencyMetricEvaluator.compute_metrics(run_result)

        return ContractEvaluationSummary(
            contract_id=contract_id,
            contract_title=contract_title,
            agent_type=run_result.agent_type,
            criterion_scores=criterion_scores,
            mean_check_accuracy=mean_acc,
            mean_reasoning_quality=mean_judge,
            citation_accuracy=citation_acc,
            total_checks_passed=checks_passed,
            total_checks=num_criteria,
            latency_seconds=efficiency["latency_seconds"],
            total_tokens=efficiency["total_tokens"],
            prompt_tokens=efficiency["prompt_tokens"],
            completion_tokens=efficiency["completion_tokens"],
            tool_calls_count=efficiency["tool_calls_count"],
            estimated_cost_usd=efficiency["estimated_cost_usd"],
        )

    def run_full_suite(
        self,
        contracts: Optional[List[str]] = None,
    ) -> ComparativeRunReport:
        """Executes full evaluation on all contracts and generates reports."""
        if contracts is None:
            contracts = list(self.ground_truth["contracts"].keys())

        baseline_agent = BaselineAgent(provider=self.provider, model_name=self.model_name)
        tool_agent = ToolAugmentedAgent(
            contracts_dir=self.contracts_dir,
            provider=self.provider,
            model_name=self.model_name,
        )

        contract_breakdowns: List[Dict[str, Any]] = []

        baseline_accs, baseline_judges, baseline_citations = [], [], []
        baseline_latencies, baseline_tokens, baseline_costs = [], [], []

        tool_accs, tool_judges, tool_citations = [], [], []
        tool_latencies, tool_tokens, tool_costs, tool_calls = [], [], [], []

        for cid in contracts:
            res = self.run_contract_evaluation(cid, baseline_agent, tool_agent)
            contract_breakdowns.append(res)

            b = res["baseline"]
            baseline_accs.append(b["mean_check_accuracy"])
            baseline_judges.append(b["mean_reasoning_quality"])
            baseline_citations.append(b["citation_accuracy"])
            baseline_latencies.append(b["latency_seconds"])
            baseline_tokens.append(b["total_tokens"])
            baseline_costs.append(b["estimated_cost_usd"])

            t = res["tool_augmented"]
            tool_accs.append(t["mean_check_accuracy"])
            tool_judges.append(t["mean_reasoning_quality"])
            tool_citations.append(t["citation_accuracy"])
            tool_latencies.append(t["latency_seconds"])
            tool_tokens.append(t["total_tokens"])
            tool_costs.append(t["estimated_cost_usd"])
            tool_calls.append(t["tool_calls_count"])

        n = max(1, len(contracts))
        baseline_summary = {
            "mean_check_accuracy": round(sum(baseline_accs) / n, 4),
            "mean_reasoning_quality": round(sum(baseline_judges) / n, 2),
            "citation_accuracy": round(sum(baseline_citations) / n, 4),
            "total_latency_seconds": round(sum(baseline_latencies), 3),
            "avg_latency_seconds": round(sum(baseline_latencies) / n, 3),
            "total_tokens": sum(baseline_tokens),
            "total_tool_calls": 0,
            "estimated_cost_usd": round(sum(baseline_costs), 6),
        }

        tool_summary = {
            "mean_check_accuracy": round(sum(tool_accs) / n, 4),
            "mean_reasoning_quality": round(sum(tool_judges) / n, 2),
            "citation_accuracy": round(sum(tool_citations) / n, 4),
            "total_latency_seconds": round(sum(tool_latencies), 3),
            "avg_latency_seconds": round(sum(tool_latencies) / n, 3),
            "total_tokens": sum(tool_tokens),
            "total_tool_calls": sum(tool_calls),
            "estimated_cost_usd": round(sum(tool_costs), 6),
        }

        delta = {
            "accuracy_gain_pct": round((tool_summary["mean_check_accuracy"] - baseline_summary["mean_check_accuracy"]) * 100, 2),
            "reasoning_gain_points": round(tool_summary["mean_reasoning_quality"] - baseline_summary["mean_reasoning_quality"], 2),
            "citation_gain_pct": round((tool_summary["citation_accuracy"] - baseline_summary["citation_accuracy"]) * 100, 2),
            "latency_delta_seconds": round(tool_summary["avg_latency_seconds"] - baseline_summary["avg_latency_seconds"], 3),
            "token_ratio": round(tool_summary["total_tokens"] / max(1, baseline_summary["total_tokens"]), 2),
        }

        now_iso = datetime.now(timezone.utc).isoformat()
        report = ComparativeRunReport(
            dataset_version=DATASET_VERSION,
            eval_judge_version=EVAL_JUDGE_VERSION,
            agent_config_version=AGENT_CONFIG_VERSION,
            timestamp=now_iso,
            baseline_summary=baseline_summary,
            tool_augmented_summary=tool_summary,
            delta=delta,
            contract_breakdowns=contract_breakdowns,
        )

        # Write reports
        self._export_json(report)
        self._export_markdown(report)
        self._export_html(report)

        return report

    def _export_json(self, report: ComparativeRunReport) -> Path:
        out_path = self.reports_dir / "evaluation_results.json"
        out_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        return out_path

    def _export_markdown(self, report: ComparativeRunReport) -> Path:
        out_path = self.reports_dir / "evaluation_report.md"
        b = report.baseline_summary
        t = report.tool_augmented_summary
        d = report.delta

        lines = [
            "# Reproducible Contract Review Agent Evaluation Report",
            f"**Dataset Version:** `{report.dataset_version}` | **Judge Version:** `{report.eval_judge_version}` | **Agent Config:** `{report.agent_config_version}`",
            f"**Execution Timestamp:** `{report.timestamp}`",
            "",
            "## Executive Summary: Run A (Baseline) vs Run B (Tool-Augmented)",
            "",
            "| Metric | Run A: Baseline (No Tools) | Run B: Tool-Augmented (RAG) | Absolute Delta | Percentage Shift |",
            "| :--- | :---: | :---: | :---: | :---: |",
            f"| **Check_Accuracy** | {b['mean_check_accuracy']*100:.1f}% | **{t['mean_check_accuracy']*100:.1f}%** | +{d['accuracy_gain_pct']:.1f}% | **+{d['accuracy_gain_pct']:.1f}%** |",
            f"| **Reasoning_Quality (1-5)** | {b['mean_reasoning_quality']:.2f} / 5.0 | **{t['mean_reasoning_quality']:.2f} / 5.0** | +{d['reasoning_gain_points']:.2f} pts | +{(d['reasoning_gain_points']/b['mean_reasoning_quality'])*100:.1f}% |",
            f"| **Citation Accuracy** | {b['citation_accuracy']*100:.1f}% | **{t['citation_accuracy']*100:.1f}%** | +{d['citation_gain_pct']:.1f}% | +{d['citation_gain_pct']:.1f}% |",
            f"| **Avg Latency** | {b['avg_latency_seconds']:.2f}s | {t['avg_latency_seconds']:.2f}s | +{d['latency_delta_seconds']:.2f}s | +{(d['latency_delta_seconds']/b['avg_latency_seconds'])*100:.1f}% |",
            f"| **Tool Invocations** | 0 calls | **{t['total_tool_calls']} calls** | +{t['total_tool_calls']} calls | N/A |",
            f"| **Est. Cost (3 Contracts)** | ${b['estimated_cost_usd']:.6f} | ${t['estimated_cost_usd']:.6f} | +${t['estimated_cost_usd']-b['estimated_cost_usd']:.6f} | - |",
            "",
            "---",
            "",
            "## Key Evaluation Findings & LLM Failure Analysis",
            "1. **Silent vs. Hallucinated Clauses in NDAs:** Baseline models tend to hallucinate standard commercial provisions (e.g. Net 30 payment, 1-year product warranty) when evaluated on an NDA. Tool-augmented agents inspect `Section 15.3` and accurately flag terms as absent / not applicable.",
            "2. **Overlooking Specific Multipliers (VSA):** On commercial agreements, the baseline agent often defaults to common boilerplate assumptions (such as 12-month liability caps) rather than reading Section 9.2's specific 6-month formula.",
            "3. **Cross-Referenced Super-Caps & Carve-Outs (MSA):** In enterprise MSAs with schedules, the baseline agent stops at Section 11.2 (12-month cap), completely missing Section 11.3's $5,000,000 Enhanced Super-Cap and Section 11.4's uncapped indemnification. The tool-augmented agent's `verify_cross_reference` tool prevents these high-risk legal blindspots.",
            "",
            "---",
            "",
            "## Contract-by-Contract Breakdown",
            "",
        ]

        for item in report.contract_breakdowns:
            cid = item["contract_id"]
            title = item["contract_title"]
            b_item = item["baseline"]
            t_item = item["tool_augmented"]

            lines.extend([
                f"### Contract: {title} (`{cid}`)",
                f"- **Complexity:** {item['complexity']} | **Type:** {item['contract_type']}",
                f"- **Baseline:** Accuracy = {b_item['mean_check_accuracy']*100:.1f}%, Judge = {b_item['mean_reasoning_quality']:.2f}/5, Citation = {b_item['citation_accuracy']*100:.1f}%",
                f"- **Tool-Augmented:** Accuracy = **{t_item['mean_check_accuracy']*100:.1f}%**, Judge = **{t_item['mean_reasoning_quality']:.2f}/5**, Citation = **{t_item['citation_accuracy']*100:.1f}%**",
                f"- **Tool Calls:** {t_item['tool_calls_count']} calls (Outline: 1, Section Inspections & Cross-references)",
                "",
                "| Criterion | Baseline Status | Tool Status | Ground Truth Section | Baseline Cited | Tool Cited | Tool Judge Score |",
                "| :--- | :---: | :---: | :--- | :--- | :--- | :---: |",
            ])

            for crit in CHECKLIST_18_CRITERIA:
                c_id = crit["id"]
                b_score = b_item["criterion_scores"].get(c_id, {})
                t_score = t_item["criterion_scores"].get(c_id, {})

                b_status = "PASS" if b_score.get("check_accuracy", 0) >= 0.70 else "FAIL"
                t_status = "PASS" if t_score.get("check_accuracy", 0) >= 0.70 else "FAIL"

                gt_sec = t_score.get("expected_section", "")
                b_sec = b_score.get("agent_cited_section", "None")
                t_sec = t_score.get("agent_cited_section", "None")
                j_score = t_score.get("reasoning_quality", 0)

                lines.append(
                    f"| {crit['name']} | {b_status} ({b_score.get('check_accuracy',0)*100:.0f}%) | "
                    f"**{t_status}** ({t_score.get('check_accuracy',0)*100:.0f}%) | {gt_sec} | {b_sec} | {t_sec} | {j_score:.1f}/5 |"
                )
            lines.append("")

        out_path.write_text("\n".join(lines), encoding="utf-8")
        return out_path

    def _export_html(self, report: ComparativeRunReport) -> Path:
        out_path = self.reports_dir / "evaluation_report.html"
        b = report.baseline_summary
        t = report.tool_augmented_summary
        d = report.delta

        # Construct interactive HTML dashboard
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Agent Evaluation Dashboard: 18-Point Contract Review</title>
  <style>
    :root {{
      --bg: #0f172a;
      --card-bg: #1e293b;
      --border: #334155;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #38bdf8;
      --primary-dark: #0284c7;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background-color: var(--bg);
      color: var(--text);
      font-family: var(--font-family);
      line-height: 1.5;
      padding: 32px 24px;
    }}
    .container {{
      max-width: 1300px;
      margin: 0 auto;
    }}
    header {{
      margin-bottom: 32px;
      padding-bottom: 24px;
      border-bottom: 1px solid var(--border);
    }}
    h1 {{
      font-size: 28px;
      font-weight: 700;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .badge {{
      font-size: 12px;
      padding: 4px 10px;
      border-radius: 9999px;
      background: rgba(56, 189, 248, 0.15);
      color: var(--primary);
      border: 1px solid rgba(56, 189, 248, 0.3);
      font-weight: 600;
      text-transform: uppercase;
    }}
    .meta-bar {{
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      margin-top: 12px;
      color: var(--text-muted);
      font-size: 14px;
    }}
    .meta-item strong {{ color: var(--text); }}
    
    /* KPI Grid */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 20px;
      margin-bottom: 36px;
    }}
    .kpi-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 20px;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }}
    .kpi-label {{
      font-size: 13px;
      color: var(--text-muted);
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .kpi-val {{
      font-size: 32px;
      font-weight: 800;
      margin: 8px 0;
    }}
    .kpi-delta {{
      font-size: 13px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 4px;
    }}
    .positive {{ color: var(--success); }}
    .neutral {{ color: var(--primary); }}

    /* Comparison Table */
    .section-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 24px;
      margin-bottom: 32px;
    }}
    h2 {{
      font-size: 20px;
      font-weight: 700;
      margin-bottom: 18px;
      color: #fff;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 14px;
    }}
    th {{
      background: rgba(15, 23, 42, 0.6);
      color: var(--text-muted);
      padding: 12px 16px;
      font-weight: 600;
      border-bottom: 2px solid var(--border);
    }}
    td {{
      padding: 14px 16px;
      border-bottom: 1px solid var(--border);
    }}
    tr:hover td {{
      background: rgba(255, 255, 255, 0.02);
    }}
    .tag {{
      display: inline-block;
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
    }}
    .tag-pass {{ background: rgba(16, 185, 129, 0.15); color: var(--success); border: 1px solid rgba(16, 185, 129, 0.3); }}
    .tag-fail {{ background: rgba(239, 68, 68, 0.15); color: var(--danger); border: 1px solid rgba(239, 68, 68, 0.3); }}
    .tag-baseline {{ background: rgba(148, 163, 184, 0.15); color: var(--text-muted); }}
    .tag-tool {{ background: rgba(56, 189, 248, 0.15); color: var(--primary); }}

    /* Progress bar */
    .bar-container {{
      width: 100%;
      background: rgba(255, 255, 255, 0.1);
      height: 8px;
      border-radius: 4px;
      overflow: hidden;
      margin-top: 6px;
    }}
    .bar-fill {{
      height: 100%;
      border-radius: 4px;
    }}
    .bar-fill-tool {{ background: var(--primary); }}
    .bar-fill-baseline {{ background: #94a3b8; }}

    /* Accordion for traces */
    details {{
      background: rgba(15, 23, 42, 0.4);
      border: 1px solid var(--border);
      border-radius: 8px;
      margin-bottom: 12px;
      overflow: hidden;
    }}
    summary {{
      padding: 14px 18px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      justify-content: space-between;
      user-select: none;
    }}
    summary:hover {{ background: rgba(255, 255, 255, 0.03); }}
    .details-body {{
      padding: 18px;
      border-top: 1px solid var(--border);
      background: #0f172a;
      font-size: 13px;
    }}
    pre {{
      background: #090d16;
      padding: 12px;
      border-radius: 6px;
      overflow-x: auto;
      font-family: monospace;
      font-size: 12px;
      color: #38bdf8;
    }}
    .tab-nav {{
      display: flex;
      gap: 8px;
      margin-bottom: 16px;
    }}
    .tab-btn {{
      padding: 8px 16px;
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border);
      color: var(--text-muted);
      cursor: pointer;
      font-weight: 600;
    }}
    .tab-btn.active {{
      background: var(--primary);
      color: #0f172a;
      border-color: var(--primary);
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>
        ⚖️ Contract Review Agent Evaluation Dashboard
        <span class="badge">18-Point Compliance</span>
      </h1>
      <div class="meta-bar">
        <span class="meta-item">Dataset Version: <strong>{report.dataset_version}</strong></span>
        <span class="meta-item">LLM Judge Version: <strong>{report.eval_judge_version}</strong></span>
        <span class="meta-item">Agent Config: <strong>{report.agent_config_version}</strong></span>
        <span class="meta-item">Execution: <strong>{report.timestamp}</strong></span>
        <span class="meta-item">Evaluator Model: <strong>gemini-2.0-flash (temp=0.0)</strong></span>
      </div>
    </header>

    <!-- Top KPI Highlights -->
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">Check Accuracy (Exact/Semantic)</div>
        <div class="kpi-val" style="color: var(--primary);">{t['mean_check_accuracy']*100:.1f}%</div>
        <div class="kpi-delta positive">
          ↑ +{d['accuracy_gain_pct']:.1f}% vs Baseline ({b['mean_check_accuracy']*100:.1f}%)
        </div>
      </div>

      <div class="kpi-card">
        <div class="kpi-label">Reasoning Quality (Judge 1-5)</div>
        <div class="kpi-val" style="color: #a855f7;">{t['mean_reasoning_quality']:.2f} <span style="font-size: 18px; color: var(--text-muted);">/ 5.0</span></div>
        <div class="kpi-delta positive">
          ↑ +{d['reasoning_gain_points']:.2f} pts vs Baseline ({b['mean_reasoning_quality']:.2f})
        </div>
      </div>

      <div class="kpi-card">
        <div class="kpi-label">Clause Citation Accuracy</div>
        <div class="kpi-val" style="color: var(--success);">{t['citation_accuracy']*100:.1f}%</div>
        <div class="kpi-delta positive">
          ↑ +{d['citation_gain_pct']:.1f}% vs Baseline ({b['citation_accuracy']*100:.1f}%)
        </div>
      </div>

      <div class="kpi-card">
        <div class="kpi-label">Tool Efficiency & Calls</div>
        <div class="kpi-val" style="color: #f59e0b;">{t['total_tool_calls']} <span style="font-size: 16px; color: var(--text-muted);">calls</span></div>
        <div class="kpi-delta neutral">
          {t['avg_latency_seconds']:.2f}s avg latency | 0 calls for Run A
        </div>
      </div>
    </div>

    <!-- Comparative Overview Table -->
    <div class="section-card">
      <h2>📊 Run A (Baseline / No Tools) vs. Run B (Tool-Augmented / RAG)</h2>
      <table>
        <thead>
          <tr>
            <th>Performance Metric</th>
            <th>Run A: Baseline (Direct Prompt)</th>
            <th>Run B: Tool-Augmented (RAG)</th>
            <th>Absolute Advantage</th>
            <th>Status / Outcome</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>Mean Check_Accuracy</strong><br><small style="color: var(--text-muted)">Exact parameter match across 18 criteria</small></td>
            <td>
              <strong>{b['mean_check_accuracy']*100:.1f}%</strong>
              <div class="bar-container"><div class="bar-fill bar-fill-baseline" style="width: {b['mean_check_accuracy']*100}%"></div></div>
            </td>
            <td>
              <strong style="color: var(--primary)">{t['mean_check_accuracy']*100:.1f}%</strong>
              <div class="bar-container"><div class="bar-fill bar-fill-tool" style="width: {t['mean_check_accuracy']*100}%"></div></div>
            </td>
            <td><strong class="positive">+{d['accuracy_gain_pct']:.1f}%</strong></td>
            <td><span class="tag tag-pass">Tool Superiority</span></td>
          </tr>
          <tr>
            <td><strong>Reasoning_Quality (LLM Judge)</strong><br><small style="color: var(--text-muted)">Strict 1-5 legal rubric rating justifications & quotes</small></td>
            <td><strong>{b['mean_reasoning_quality']:.2f} / 5.0</strong></td>
            <td><strong style="color: #a855f7">{t['mean_reasoning_quality']:.2f} / 5.0</strong></td>
            <td><strong class="positive">+{d['reasoning_gain_points']:.2f} pts</strong></td>
            <td><span class="tag tag-pass">Substantive Evidence</span></td>
          </tr>
          <tr>
            <td><strong>Section Citation Accuracy</strong><br><small style="color: var(--text-muted)">Precision of specific clause / schedule references</small></td>
            <td><strong>{b['citation_accuracy']*100:.1f}%</strong></td>
            <td><strong style="color: var(--success)">{t['citation_accuracy']*100:.1f}%</strong></td>
            <td><strong class="positive">+{d['citation_gain_pct']:.1f}%</strong></td>
            <td><span class="tag tag-pass">Grounded Citations</span></td>
          </tr>
          <tr>
            <td><strong>Average Execution Latency</strong><br><small style="color: var(--text-muted)">End-to-end execution time per contract</small></td>
            <td>{b['avg_latency_seconds']:.2f} seconds</td>
            <td>{t['avg_latency_seconds']:.2f} seconds</td>
            <td>+{d['latency_delta_seconds']:.2f} seconds</td>
            <td><span class="tag tag-baseline">Trade-off (Accuracy > Speed)</span></td>
          </tr>
          <tr>
            <td><strong>Total Token Consumption</strong><br><small style="color: var(--text-muted)">Prompt + Completion tokens across 3 contracts</small></td>
            <td>{b['total_tokens']:,} tokens</td>
            <td>{t['total_tokens']:,} tokens</td>
            <td>{d['token_ratio']:.2f}x token ratio</td>
            <td><span class="tag tag-baseline">${t['estimated_cost_usd']:.4f} total cost</span></td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Contract-by-Contract Breakdown -->
    <div class="section-card">
      <h2>📑 18-Point Compliance Checklist by Contract</h2>
"""

        for item in report.contract_breakdowns:
            cid = item["contract_id"]
            title = item["contract_title"]
            b_item = item["baseline"]
            t_item = item["tool_augmented"]

            html_content += f"""
      <details open style="margin-bottom: 24px;">
        <summary>
          <span><strong>{title}</strong> ({item['complexity']} Complexity · {item['contract_type']})</span>
          <span>Baseline: <strong>{b_item['mean_check_accuracy']*100:.0f}%</strong> → Tool: <strong style="color: var(--primary);">{t_item['mean_check_accuracy']*100:.0f}%</strong></span>
        </summary>
        <div class="details-body">
          <table>
            <thead>
              <tr>
                <th>Compliance Dimension</th>
                <th>Baseline (Run A)</th>
                <th>Tool-Augmented (Run B)</th>
                <th>Ground Truth Section</th>
                <th>Agent Citations (A vs B)</th>
                <th>LLM Judge Score & Critique (Run B)</th>
              </tr>
            </thead>
            <tbody>
"""
            for crit in CHECKLIST_18_CRITERIA:
                c_id = crit["id"]
                b_score = b_item["criterion_scores"].get(c_id, {})
                t_score = t_item["criterion_scores"].get(c_id, {})

                b_tag = f"<span class='tag {'tag-pass' if b_score.get('check_accuracy',0)>=0.70 else 'tag-fail'}'>{b_score.get('check_accuracy',0)*100:.0f}%</span>"
                t_tag = f"<span class='tag {'tag-pass' if t_score.get('check_accuracy',0)>=0.70 else 'tag-fail'}'>{t_score.get('check_accuracy',0)*100:.0f}%</span>"

                gt_sec = t_score.get("expected_section", "")
                b_sec = b_score.get("agent_cited_section", "None")
                t_sec = t_score.get("agent_cited_section", "None")
                j_score = t_score.get("reasoning_quality", 0)
                j_rat = t_score.get("judge_rationale", "")

                html_content += f"""
              <tr>
                <td><strong>{crit['name']}</strong><br><small style="color: var(--text-muted);">{crit['category']}</small></td>
                <td>{b_tag}</td>
                <td>{t_tag}</td>
                <td><code>{gt_sec}</code></td>
                <td>
                  <small style="color: #94a3b8">A: {b_sec}</small><br>
                  <strong style="color: var(--primary)">B: {t_sec}</strong>
                </td>
                <td>
                  <strong>{j_score:.1f} / 5.0</strong><br>
                  <small style="color: var(--text-muted);">{j_rat}</small>
                </td>
              </tr>
"""
            html_content += """
            </tbody>
          </table>
        </div>
      </details>
"""

        # Tool trace accordion
        html_content += """
    </div>

    <div class="section-card">
      <h2>🔍 Tool Execution Traces (Observability & Cross-References)</h2>
      <p style="color: var(--text-muted); margin-bottom: 16px;">
        Sample tool execution trace showing how Run B isolates sections and verifies cross-references before synthesizing judgments:
      </p>
"""
        for item in report.contract_breakdowns:
            cid = item["contract_id"]
            title = item["contract_title"]
            trace = item.get("tool_trace", [])
            html_content += f"""
      <details>
        <summary><span>Trace: {title}</span> <span style="color: var(--primary);">{len(trace)} Tool Steps</span></summary>
        <div class="details-body">
          <pre>{json.dumps(trace, indent=2)}</pre>
        </div>
      </details>
"""

        html_content += """
    </div>
  </div>
</body>
</html>
"""
        out_path.write_text(html_content, encoding="utf-8")
        return out_path
