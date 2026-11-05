# ⚖️ Reproducible Agent Evaluation Demo: Legal Contract Review Agent

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![Dataset Version](https://img.shields.io/badge/dataset-v1.0-emerald.svg)](dataset/ground_truth_v1.json)
[![Judge Version](https://img.shields.io/badge/eval__judge-v1.0-purple.svg)](eval/judge_evaluator.py)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A self-contained, reproducible Python demonstration project evaluating an autonomous AI Agent performing an **18-point legal compliance review** on enterprise contracts. 

The benchmark demonstrates quantitative evaluation, **LLM-as-a-Judge** scoring, dataset versioning, run comparison (**Run A: Baseline / No Tools** vs. **Run B: Tool-Augmented / RAG**), and observability over agent tool traces.

---

## 🎯 Benchmark Overview

In real-world enterprise legal compliance, naive single-prompt LLM evaluations suffer from severe blind spots:
1. **Hallucinating standard commercial terms** when evaluated on simpler contracts (e.g. fabricating payment and warranty terms on a Non-Disclosure Agreement).
2. **Missing specific numeric multipliers** (e.g. defaulting to standard 12-month liability caps when a SaaS contract explicitly stipulates 6 months).
3. **Overlooking cross-referenced schedules and carve-outs** (e.g. citing a general liability cap and missing an Enhanced Super-Cap or uncapped indemnification in an attached Data Protection Addendum).

This evaluation harness quantifies how a **Tool-Augmented Agent** equipped with section retrieval, clause search, and cross-reference verification outperforms a direct-prompt baseline agent across all 18 dimensions.

---

## 📋 The 18-Point Compliance Checklist

Every contract is rigorously evaluated against 18 standardized criteria defined in [`dataset/ground_truth_v1.json`](dataset/ground_truth_v1.json):

| # | Dimension | Category | Description |
| :-: | :--- | :--- | :--- |
| **1** | `governing_law` | Legal & Jurisdiction | Governing state law and court venue |
| **2** | `liability_cap` | Risk & Financial Exposure | Aggregate monetary liability cap, multipliers, and super-caps |
| **3** | `ip_assignment` | Intellectual Property | Ownership of deliverables, work-for-hire, and background IP licenses |
| **4** | `indemnification_scope` | Risk & Financial Exposure | Scope of third-party indemnification, mutual vs unilateral, uncapped carve-outs |
| **5** | `termination_notice` | Contract Lifecycle | Notice periods for convenience (e.g. 30/60/90 days) and cause cure periods |
| **6** | `confidentiality_term` | Confidentiality & Privacy | Duration of survival post-termination and perpetual exceptions (trade secrets, PII) |
| **7** | `audit_rights` | Governance & Compliance | Customer audit rights, notice window, access scope, and fee reimbursement |
| **8** | `non_solicitation` | HR & Restrictive Covenants | Non-solicitation duration, personnel covered, and liquidated damages |
| **9** | `payment_terms` | Commercial & Financial | Net payment terms (Net 30, Net 45), late interest, and invoice disputes |
| **10** | `dispute_resolution` | Legal & Jurisdiction | Mandatory escalation (negotiation, mediation) and binding arbitration (AAA, JAMS) |
| **11** | `force_majeure` | Contract Lifecycle | Events excused, carve-outs for IT/cyber failures, and termination thresholds |
| **12** | `assignment_change_of_control` | Contract Lifecycle | Consent requirements, affiliate exceptions, and competitor change of control |
| **13** | `insurance_requirements` | Risk & Financial Exposure | CGL, Cyber Risk/E&O, Crime, and Workers' Comp coverage limits |
| **14** | `warranty_period` | Commercial & Quality | Deliverable / SaaS performance warranty duration (90/180 days) and remedies |
| **15** | `data_privacy_security` | Confidentiality & Privacy | GDPR/CCPA/SOC 2 compliance and breach notification window (24h/48h/72h) |
| **16** | `export_compliance` | Regulatory & Compliance | Adherence to U.S. EAR, ITAR, and OFAC sanctions |
| **17** | `subcontracting_rights` | Governance & Operations | Prior written approval requirements and prime contractor liability |
| **18** | `severability_entire_agreement` | Boilerplate & Interpretation | Severability, entire agreement merger clause, and order of precedence hierarchy |

---

## 📂 Synthetic Contracts Dataset (`v1.0`)

Three synthetic contracts representing varying complexity levels:

1. **`01_standard_nda.md` (Low Complexity):** Mutual Non-Disclosure Agreement between Aegis Cloud Systems and Veritas BioHealth Labs. Tests ability to extract 5-year survival, Delaware law, and recognize that commercial terms (warranties, payments, insurance) are absent without hallucinating them.
2. **`02_vendor_services_agreement.md` (Medium Complexity):** Commercial Cloud SaaS Agreement between DataStream Analytics and BlueRidge Retail. Tests detection of an unusual 6-month liability cap, a $2,000,000 Vendor IP indemnity cap, 72-hour breach notice, and SOC 2 audit restrictions.
3. **`03_master_services_agreement.md` (High Complexity):** Enterprise Master Services Agreement with Schedules A, B, and C between Nexus Global Enterprise Solutions and Apex Financial Technologies. Features multi-tier dispute resolution, a $5,000,000 Enhanced Super-Cap for Schedule B breaches, uncapped indemnification, and a 24-hour breach notification requirement.

---

## 🏗️ Architecture & Dual Agent Workflows

```
                           Contract Document (.md)
                                     │
           ┌─────────────────────────┴─────────────────────────┐
           ▼                                                   ▼
┌─────────────────────────────┐             ┌─────────────────────────────────────┐
│  Run A: Baseline Agent      │             │  Run B: Tool-Augmented Agent (RAG)  │
│  - Single prompt            │             │  - get_contract_outline()           │
│  - Entire contract in context│             │  - search_contract_clauses()        │
│  - No external tools        │             │  - get_contract_section()           │
│  - Prone to hallucinations  │             │  - verify_cross_reference()         │
└──────────────┬──────────────┘             └──────────────────┬──────────────────┘
               │                                               │
               └───────────────────────┬───────────────────────┘
                                       ▼
                     ┌───────────────────────────────────┐
                     │         Evaluation Harness        │
                     │  - Check_Accuracy (Exact/Semantic)│
                     │  - Reasoning_Quality (LLM Judge)  │
                     │  - Tool_Efficiency & Latency      │
                     └─────────────────┬─────────────────┘
                                       ▼
                   ┌───────────────────────────────────────┐
                   │  Comparative Dashboard Reports       │
                   │  - reports/evaluation_results.json    │
                   │  - reports/evaluation_report.md       │
                   │  - reports/evaluation_report.html     │
                   └───────────────────────────────────────┘
```

---

## 📊 Benchmark Results: Run A vs. Run B

Results generated by `python run_evaluation_demo.py`:

| Performance Metric | Run A: Baseline (No Tools) | Run B: Tool-Augmented (RAG) | Absolute Advantage | Status |
| :--- | :---: | :---: | :---: | :---: |
| **Check_Accuracy** | 77.6% | **98.0%** | **+20.4%** | ✅ Tool Superiority |
| **Reasoning_Quality (1-5)** | 3.24 / 5.0 | **4.76 / 5.0** | **+1.52 pts** | ✅ Substantive Evidence |
| **Section Citation Accuracy** | 87.0% | **100.0%** | **+13.0%** | ✅ Grounded Citations |
| **Average Latency** | 1.22s | 2.35s | +1.13s | ⚖️ Quality vs. Speed |
| **Tool Invocations** | 0 calls | **52 calls** | +52 calls | 🔍 Active Verification |
| **Total Tokens** | 16,528 tokens | 9,140 tokens | 0.55x ratio | 💰 Targeted Prompts |
| **Estimated Cost (3 Contracts)** | $0.004169 | $0.004857 | +$0.000688 | 💵 Negligible Cost Delta |

### Contract-Level Breakdown

| Contract ID | Complexity | Run A Accuracy | Run B Accuracy | Run A Judge | Run B Judge | Tool Invocations |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `01_standard_nda` | Low | 66.6% | **95.5%** | 2.92 / 5.0 | **4.53 / 5.0** | 13 calls |
| `02_vendor_services_agreement` | Medium | 87.0% | **98.5%** | 3.64 / 5.0 | **4.75 / 5.0** | 16 calls |
| `03_master_services_agreement` | High | 79.1% | **100.0%** | 3.17 / 5.0 | **5.00 / 5.0** | 23 calls |

---

## 🚀 Quickstart

### 1. Installation
This project runs out-of-the-box on Python 3.10+ using Python's standard library (zero external dependencies required):

```bash
git clone https://github.com/DavidFlorez/GEAP-Eval-demo.git
cd GEAP-Eval-demo
```

### 2. Execute the Evaluation Demo
Run the single CLI script:
```bash
python3 run_evaluation_demo.py
```

### 3. Run Specific Contracts or Live Gemini Mode
```bash
# Run only on the enterprise MSA
python3 run_evaluation_demo.py --contracts 03_master_services_agreement

# Run with live Gemini 2.0 Flash model (when GEMINI_API_KEY is configured)
python3 run_evaluation_demo.py --provider gemini --model gemini-2.0-flash
```

### 4. View the Interactive Dashboard
Open [`reports/evaluation_report.html`](reports/evaluation_report.html) in your browser to inspect:
- Side-by-side KPI comparison cards.
- 18-point pass/fail checklist with ground truth comparisons.
- LLM-as-a-Judge critiques and reasoning traces.
- Multi-step tool execution history.

### 5. Automated Tests
```bash
python3 -m unittest discover tests
```

---

## ☁️ GEAP & Google ADK Integration (Argolis Project)

The Contract Review Agent is packaged as a native Google Agent Development Kit (`google-adk`) agent under [`contract_review_agent/`](contract_review_agent/). You can interact with it, evaluate it, and deploy it to your Argolis GCP project directly using the `agents` CLI.

### 1. Interactive Testing via `agents` CLI
Launch an interactive session with the contract compliance agent:
```bash
agents run contract_review_agent
```

### 2. Run GEAP Evaluation Set
Run automated evaluation using the native ADK evaluation harness:
```bash
agents eval contract_review_agent contract_review_agent/eval_set.json
```

### 3. Deploy to GEAP / Vertex AI Agent Engine in Argolis
Configure your Argolis project ID in [`contract_review_agent/.env`](contract_review_agent/.env) and deploy:
```bash
# Configure your active Argolis project
export GOOGLE_CLOUD_PROJECT="assist-463118"  # or your active Argolis project ID
export GOOGLE_CLOUD_PROJECT="assist-463118"
export GOOGLE_CLOUD_REGION="us-central1"

# Deployed Resource in Google Cloud (GEAP Agent Engine):
# projects/806084165595/locations/us-central1/reasoningEngines/843288309986754560
# Staging Bucket: gs://assist-463118-contract-review-staging

# Re-deploy or update if needed:
agents deploy agent_engine \
  --project="assist-463118" \
  --region="us-central1" \
  --staging_bucket="gs://assist-463118-contract-review-staging" \
  --display_name="Contract Compliance Reviewer" \
  contract_review_agent
```

### Running the GEAP Evaluation Suite

To run the evaluation set through the Google ADK CLI (`agents eval`):
```bash
PYTHONPATH=. GOOGLE_CLOUD_PROJECT=assist-463118 GOOGLE_CLOUD_LOCATION=us-central1 \
  agents eval contract_review_agent contract_review_agent/eval_set.json --print_detailed_results
```

### Querying the Deployed Cloud Agent Directly

To stream live 18-point reviews from the deployed ReasoningEngine instance:
```bash
python test_cloud_deployed_agent.py
```
This script connects to `projects/806084165595/locations/us-central1/reasoningEngines/843288309986754560`, opens a session, and streams function calls (`get_contract_outline`, `get_contract_section`, `search_contract_clauses`) and verified review findings.


---

## 🔒 Versioning & Reproducibility Constraints

Every evaluation output logs three explicit version tags:
- `dataset_version="v1.0"`: Identifies ground truth definitions and contract texts.
- `eval_judge_version="v1.0"`: Identifies the 1-to-5 legal evaluation rubric.
- `agent_config_version="v1.0"`: Identifies the prompt instructions and tool registry configuration.

Model calls enforce `temperature=0.0` and deterministic seeds (`seed=42`) to guarantee identical, reproducible scores across runs.

---

## 📁 Repository Structure

```
GEAP-Eval-demo/
├── README.md                      # Comprehensive project documentation
├── requirements.txt               # Dependency specification
├── run_evaluation_demo.py         # Single CLI executable runner
├── dataset/
│   ├── ground_truth_v1.json       # 18-point ground truth mapping
│   └── v1_contracts/
│       ├── 01_standard_nda.md
│       ├── 02_vendor_services_agreement.md
│       └── 03_master_services_agreement.md
├── agents/
│   ├── __init__.py
│   ├── base.py                    # Base agent interface & token tracking
│   ├── baseline_agent.py          # Run A: Direct prompt, no tools
│   ├── tool_augmented_agent.py    # Run B: Tool-using agent with cross-reference verification
│   └── tools.py                   # Outline, section reader, clause search, xref tools
├── eval/
│   ├── __init__.py
│   ├── schema.py                  # Dataclasses and criteria definitions
│   ├── accuracy_metric.py         # Check_Accuracy (status, citation, elements)
│   ├── judge_evaluator.py         # Reasoning_Quality (LLM-as-a-Judge 1-5 rubric)
│   ├── efficiency_metric.py       # Latency, token usage, tool calls, costs
│   └── harness.py                 # Evaluation harness & report exports
├── reports/
│   ├── evaluation_report.html     # Interactive rich HTML dashboard
│   ├── evaluation_report.md       # Markdown summary report
│   └── evaluation_results.json    # Complete structured evaluation results
└── tests/
    ├── __init__.py
    └── test_evaluation.py         # Comprehensive unit and integration test suite
```

---

## ⚖️ License
MIT License. Created for GEAP Agent Evaluation demonstrations.
