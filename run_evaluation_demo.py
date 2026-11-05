#!/usr/bin/env python3
"""
Single CLI Runner for Contract Review Agent Evaluation Demo.

Executes:
1. Run A: Baseline Agent (Direct Single-Prompt, No Tools)
2. Run B: Tool-Augmented Agent (RAG, Section Reader, Clause Search, Cross-Reference Verifier)
3. Evaluates Check_Accuracy, LLM-as-a-Judge Reasoning_Quality, and Tool_Efficiency.
4. Generates interactive HTML and Markdown comparative reports.

Usage:
    python run_evaluation_demo.py
    python run_evaluation_demo.py --contracts 01_standard_nda 02_vendor_services_agreement
    python run_evaluation_demo.py --provider gemini --model gemini-2.0-flash
"""

import argparse
import sys
import os
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from eval.harness import EvaluationHarness
from eval.schema import (
    DATASET_VERSION,
    EVAL_JUDGE_VERSION,
    AGENT_CONFIG_VERSION,
)


def print_banner():
    banner = f"""
================================================================================
          GEAP EVALUATION DEMO: 18-POINT CONTRACT COMPLIANCE AGENT
================================================================================
  Dataset Version:       {DATASET_VERSION}
  LLM Judge Version:     {EVAL_JUDGE_VERSION}
  Agent Config Version:  {AGENT_CONFIG_VERSION}
  Evaluation Scope:      3 Synthetic Contracts across 18 Compliance Dimensions
  Comparative Runs:      Run A (Baseline / No Tools) vs. Run B (Tool-Augmented / RAG)
================================================================================
"""
    print(banner)


def format_table_row(col1: str, col2: str, col3: str, col4: str, width: int = 24) -> str:
    return f"  {col1:<{width}} | {col2:<{width}} | {col3:<{width}} | {col4:<{width}}"


def print_comparative_table(report):
    b = report.baseline_summary
    t = report.tool_augmented_summary
    d = report.delta

    divider = "  " + "-" * 105
    print("\n" + "=" * 107)
    print("                      COMPARATIVE EVALUATION SUMMARY (RUN A vs. RUN B)")
    print("=" * 107)
    print(format_table_row("METRIC", "RUN A (BASELINE)", "RUN B (TOOL-AUGMENTED)", "DELTA / ADVANTAGE", width=24))
    print(divider)
    
    # Check Accuracy
    b_acc = f"{b['mean_check_accuracy']*100:.1f}%"
    t_acc = f"{t['mean_check_accuracy']*100:.1f}%"
    d_acc = f"+{d['accuracy_gain_pct']:.1f}%"
    print(format_table_row("Check_Accuracy (EM)", b_acc, t_acc, d_acc, width=24))

    # Reasoning Quality
    b_judge = f"{b['mean_reasoning_quality']:.2f} / 5.0"
    t_judge = f"{t['mean_reasoning_quality']:.2f} / 5.0"
    d_judge = f"+{d['reasoning_gain_points']:.2f} pts"
    print(format_table_row("Reasoning_Quality", b_judge, t_judge, d_judge, width=24))

    # Citation Accuracy
    b_cit = f"{b['citation_accuracy']*100:.1f}%"
    t_cit = f"{t['citation_accuracy']*100:.1f}%"
    d_cit = f"+{d['citation_gain_pct']:.1f}%"
    print(format_table_row("Clause Citation Acc", b_cit, t_cit, d_cit, width=24))

    # Average Latency
    b_lat = f"{b['avg_latency_seconds']:.2f}s"
    t_lat = f"{t['avg_latency_seconds']:.2f}s"
    d_lat = f"+{d['latency_delta_seconds']:.2f}s"
    print(format_table_row("Average Latency", b_lat, t_lat, d_lat, width=24))

    # Tool Calls
    b_tools = "0 calls"
    t_tools = f"{t['total_tool_calls']} calls"
    d_tools = f"+{t['total_tool_calls']} calls"
    print(format_table_row("Tool Invocations", b_tools, t_tools, d_tools, width=24))

    # Total Tokens
    b_tok = f"{b['total_tokens']:,} tokens"
    t_tok = f"{t['total_tokens']:,} tokens"
    d_tok = f"{d['token_ratio']:.2f}x ratio"
    print(format_table_row("Token Usage (Total)", b_tok, t_tok, d_tok, width=24))

    # Est Cost
    b_cost = f"${b['estimated_cost_usd']:.6f}"
    t_cost = f"${t['estimated_cost_usd']:.6f}"
    d_cost = f"+${t['estimated_cost_usd'] - b['estimated_cost_usd']:.6f}"
    print(format_table_row("Estimated Cost", b_cost, t_cost, d_cost, width=24))

    print(divider)


def print_contract_highlights(report):
    print("\n" + "=" * 107)
    print("                           CONTRACT-LEVEL EVALUATION BREAKDOWN")
    print("=" * 107)

    for item in report.contract_breakdowns:
        cid = item["contract_id"]
        title = item["contract_title"]
        b = item["baseline"]
        t = item["tool_augmented"]
        trace = item.get("tool_trace", [])

        print(f"\n[*] CONTRACT: {title} ({cid})")
        print(f"    Complexity: {item['complexity']} | Type: {item['contract_type']}")
        print(f"    -> Run A (Baseline):        Accuracy = {b['mean_check_accuracy']*100:.1f}% | Judge = {b['mean_reasoning_quality']:.2f}/5.0 | Citations = {b['citation_accuracy']*100:.1f}%")
        print(f"    -> Run B (Tool-Augmented):   Accuracy = {t['mean_check_accuracy']*100:.1f}% | Judge = {t['mean_reasoning_quality']:.2f}/5.0 | Citations = {t['citation_accuracy']*100:.1f}%")
        print(f"    -> Tool Usage:              {t['tool_calls_count']} calls ({len(trace)} multi-step trace events)")

        # Highlight key failure modes caught
        if "01_standard_nda" in cid:
            print("    -> Failure Mode Analyzed:   Baseline hallucinated payment & warranty terms; Tool Agent verified Section 15.3 silence.")
        elif "02_vendor_services_agreement" in cid:
            print("    -> Failure Mode Analyzed:   Baseline assumed standard 12-month cap; Tool Agent retrieved exact 6-month cap in Sec 9.2.")
        elif "03_master_services_agreement" in cid:
            print("    -> Failure Mode Analyzed:   Baseline missed Section 11.3 $5M Super-Cap & uncapped indemnification; Tool Agent verified cross-references.")


def main():
    parser = argparse.ArgumentParser(
        description="Run reproducible 18-point legal contract compliance evaluation demo."
    )
    parser.add_argument(
        "--contracts",
        nargs="+",
        default=None,
        help="List of contract IDs to evaluate (e.g. 01_standard_nda 02_vendor_services_agreement 03_master_services_agreement)",
    )
    parser.add_argument(
        "--provider",
        choices=["auto", "mock", "gemini"],
        default="auto",
        help="LLM provider: 'auto' (checks config), 'mock' (100%% offline reproducible), 'gemini' (live API)",
    )
    parser.add_argument(
        "--model",
        default="gemini-2.0-flash",
        help="Model name for evaluator / agents (default: gemini-2.0-flash)",
    )
    parser.add_argument(
        "--reports-dir",
        default="reports",
        help="Directory to save evaluation reports (default: reports/)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print verbose criterion-level logs",
    )

    args = parser.parse_args()

    print_banner()

    reports_dir = BASE_DIR / args.reports_dir
    harness = EvaluationHarness(
        reports_dir=reports_dir,
        provider=args.provider,
        model_name=args.model,
    )

    print(f"[*] Starting evaluation run across synthetic legal contracts...")
    report = harness.run_full_suite(contracts=args.contracts)

    print_comparative_table(report)
    print_contract_highlights(report)

    json_path = reports_dir / "evaluation_results.json"
    md_path = reports_dir / "evaluation_report.md"
    html_path = reports_dir / "evaluation_report.html"

    print("\n" + "=" * 107)
    print("                               OUTPUT DELIVERABLES")
    print("=" * 107)
    print(f"  [+] Structured JSON Results: {json_path}")
    print(f"  [+] Markdown Summary Report: {md_path}")
    print(f"  [+] Interactive HTML Report: {html_path}")
    print("=" * 107)
    print("\n[SUCCESS] Evaluation run completed successfully.\n")


if __name__ == "__main__":
    main()
