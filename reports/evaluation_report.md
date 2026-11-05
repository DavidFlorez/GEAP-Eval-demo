# Reproducible Contract Review Agent Evaluation Report
**Dataset Version:** `v1.0` | **Judge Version:** `v1.0` | **Agent Config:** `v1.0`
**Execution Timestamp:** `2026-11-05T19:39:01.025823+00:00`

## Executive Summary: Run A (Baseline) vs Run B (Tool-Augmented)

| Metric | Run A: Baseline (No Tools) | Run B: Tool-Augmented (RAG) | Absolute Delta | Percentage Shift |
| :--- | :---: | :---: | :---: | :---: |
| **Check_Accuracy** | 77.6% | **98.0%** | +20.4% | **+20.4%** |
| **Reasoning_Quality (1-5)** | 3.24 / 5.0 | **4.76 / 5.0** | +1.52 pts | +46.9% |
| **Citation Accuracy** | 87.0% | **100.0%** | +13.0% | +13.0% |
| **Avg Latency** | 1.22s | 2.35s | +1.13s | +93.1% |
| **Tool Invocations** | 0 calls | **52 calls** | +52 calls | N/A |
| **Est. Cost (3 Contracts)** | $0.004169 | $0.004857 | +$0.000688 | - |

---

## Key Evaluation Findings & LLM Failure Analysis
1. **Silent vs. Hallucinated Clauses in NDAs:** Baseline models tend to hallucinate standard commercial provisions (e.g. Net 30 payment, 1-year product warranty) when evaluated on an NDA. Tool-augmented agents inspect `Section 15.3` and accurately flag terms as absent / not applicable.
2. **Overlooking Specific Multipliers (VSA):** On commercial agreements, the baseline agent often defaults to common boilerplate assumptions (such as 12-month liability caps) rather than reading Section 9.2's specific 6-month formula.
3. **Cross-Referenced Super-Caps & Carve-Outs (MSA):** In enterprise MSAs with schedules, the baseline agent stops at Section 11.2 (12-month cap), completely missing Section 11.3's $5,000,000 Enhanced Super-Cap and Section 11.4's uncapped indemnification. The tool-augmented agent's `verify_cross_reference` tool prevents these high-risk legal blindspots.

---

## Contract-by-Contract Breakdown

### Contract: Mutual Non-Disclosure and Confidentiality Agreement (`01_standard_nda`)
- **Complexity:** Low | **Type:** Mutual NDA
- **Baseline:** Accuracy = 66.6%, Judge = 2.92/5, Citation = 77.8%
- **Tool-Augmented:** Accuracy = **95.5%**, Judge = **4.53/5**, Citation = **100.0%**
- **Tool Calls:** 13 calls (Outline: 1, Section Inspections & Cross-references)

| Criterion | Baseline Status | Tool Status | Ground Truth Section | Baseline Cited | Tool Cited | Tool Judge Score |
| :--- | :---: | :---: | :--- | :--- | :--- | :---: |
| Governing Law & Jurisdiction | PASS (88%) | **PASS** (100%) | Section 10.1 | Section 10.1 | Section 10.1 | 5.0/5 |
| Limitation of Liability & Caps | PASS (74%) | **PASS** (100%) | Section 6.1 | Section 6.1 | Section 6.1 | 5.0/5 |
| IP Ownership & Work-for-Hire | PASS (88%) | **PASS** (88%) | Section 5.1, Section 5.2 | Section 5.1 | Section 5.1, Section 5.2 | 3.5/5 |
| Indemnification Obligations & Limits | PASS (74%) | **PASS** (100%) | Section 7.1, Section 7.2 | Section 7.1 | Section 7.1, Section 7.2 | 5.0/5 |
| Termination Notice Periods | PASS (88%) | **PASS** (100%) | Section 3.1, Section 3.2 | Section 3.2 | Section 3.1, Section 3.2 | 5.0/5 |
| Confidentiality Duration & Survival | PASS (88%) | **PASS** (100%) | Section 3.3 | Section 3.3 | Section 3.3 | 5.0/5 |
| Audit Rights & Compliance Inspection | PASS (77%) | **PASS** (100%) | Section 9.1 | Section 9.1 | Section 9.1 | 5.0/5 |
| Non-Solicitation of Personnel | PASS (88%) | **PASS** (100%) | Section 8.1 | Section 8.1 | Section 8.1 | 5.0/5 |
| Payment Timing & Late Fees | FAIL (12%) | **PASS** (100%) | Section 15.3 | General | Section 15.3 | 5.0/5 |
| Dispute Resolution & Arbitration | PASS (82%) | **PASS** (100%) | Section 10.2 | Section 10.2 | Section 10.2 | 5.0/5 |
| Force Majeure & Suspension Rights | PASS (88%) | **PASS** (77%) | Section 11.1 | Section 11.1 | Section 11.1 | 2.5/5 |
| Assignment & Change of Control | PASS (88%) | **PASS** (100%) | Section 12.1 | Section 12.1 | Section 12.1 | 5.0/5 |
| Insurance Coverage Requirements | FAIL (0%) | **PASS** (88%) | Section 15.3 | General | Section 15.3 | 3.5/5 |
| Warranties & Warranty Period | FAIL (0%) | **PASS** (82%) | Section 15.3 | Section 5.1 | Section 15.3 | 3.5/5 |
| Data Privacy & Breach Notification | PASS (74%) | **PASS** (100%) | Section 13.1 | Section 13.1 | Section 13.1 | 5.0/5 |
| Export Control & Sanctions | PASS (100%) | **PASS** (100%) | Section 14.1 | Section 14.1 | Section 14.1 | 5.0/5 |
| Subcontracting Permissions & Liability | FAIL (0%) | **PASS** (82%) | Section 15.3 | General | Section 15.3 | 3.5/5 |
| Severability & Entire Agreement | PASS (88%) | **PASS** (100%) | Section 15.1, Section 15.2 | Section 15.1 | Section 15.1, Section 15.2 | 5.0/5 |

### Contract: Cloud Vendor Services Agreement (`02_vendor_services_agreement`)
- **Complexity:** Medium | **Type:** SaaS / Vendor Services Agreement
- **Baseline:** Accuracy = 87.0%, Judge = 3.64/5, Citation = 100.0%
- **Tool-Augmented:** Accuracy = **98.5%**, Judge = **4.75/5**, Citation = **100.0%**
- **Tool Calls:** 16 calls (Outline: 1, Section Inspections & Cross-references)

| Criterion | Baseline Status | Tool Status | Ground Truth Section | Baseline Cited | Tool Cited | Tool Judge Score |
| :--- | :---: | :---: | :--- | :--- | :--- | :---: |
| Governing Law & Jurisdiction | PASS (100%) | **PASS** (100%) | Section 17.1 | Section 17.1 | Section 17.1 | 5.0/5 |
| Limitation of Liability & Caps | FAIL (65%) | **PASS** (93%) | Section 9.2 | Section 9.2 | Section 9.2 | 3.5/5 |
| IP Ownership & Work-for-Hire | PASS (91%) | **PASS** (100%) | Section 2.1, Section 2.2, Section 2.3 | Section 2.1 | Section 2.1, Section 2.2, Section 2.3 | 5.0/5 |
| Indemnification Obligations & Limits | FAIL (65%) | **PASS** (100%) | Section 8.1, Section 8.2 | Section 8.1 | Section 8.1, Section 8.2 | 5.0/5 |
| Termination Notice Periods | PASS (88%) | **PASS** (100%) | Section 10.2, Section 10.3 | Section 10.2 | Section 10.2, Section 10.3 | 5.0/5 |
| Confidentiality Duration & Survival | PASS (91%) | **PASS** (100%) | Section 4.3 | Section 4.3 | Section 4.3 | 5.0/5 |
| Audit Rights & Compliance Inspection | PASS (82%) | **PASS** (91%) | Section 6.1, Section 6.2 | Section 6.1 | Section 6.1, Section 6.2 | 3.5/5 |
| Non-Solicitation of Personnel | PASS (100%) | **PASS** (100%) | Section 12.1 | Section 12.1 | Section 12.1 | 5.0/5 |
| Payment Timing & Late Fees | PASS (100%) | **PASS** (100%) | Section 3.2, Section 3.3 | Section 3.2 | Section 3.2, Section 3.3 | 5.0/5 |
| Dispute Resolution & Arbitration | PASS (82%) | **PASS** (100%) | Section 16.1, Section 16.2 | Section 16.2 | Section 16.1, Section 16.2 | 5.0/5 |
| Force Majeure & Suspension Rights | PASS (82%) | **PASS** (100%) | Section 15.1, Section 15.2 | Section 15.2 | Section 15.1, Section 15.2 | 5.0/5 |
| Assignment & Change of Control | PASS (77%) | **PASS** (100%) | Section 18.2, Section 17 | Section 18.2 | Section 18.2, Section 17 | 5.0/5 |
| Insurance Coverage Requirements | PASS (91%) | **PASS** (100%) | Section 11.1, Section 11.2 | Section 11.1 | Section 11.1, Section 11.2 | 5.0/5 |
| Warranties & Warranty Period | PASS (82%) | **PASS** (100%) | Section 7.1, Section 7.2 | Section 7.1 | Section 7.1, Section 7.2 | 5.0/5 |
| Data Privacy & Breach Notification | PASS (91%) | **PASS** (100%) | Section 5.1, Section 5.2, Section 5.3 | Section 5.2 | Section 5.1, Section 5.2, Section 5.3 | 5.0/5 |
| Export Control & Sanctions | PASS (88%) | **PASS** (100%) | Section 14.1 | Section 14.1 | Section 14.1 | 5.0/5 |
| Subcontracting Permissions & Liability | PASS (100%) | **PASS** (100%) | Section 13.1 | Section 13.1 | Section 13.1 | 5.0/5 |
| Severability & Entire Agreement | PASS (88%) | **PASS** (88%) | Section 18.1, Section 18.2 | Section 18.1 | Section 18.1, Section 18.2 | 3.5/5 |

### Contract: Enterprise Master Services Agreement (`03_master_services_agreement`)
- **Complexity:** High | **Type:** Enterprise Master Services Agreement (MSA)
- **Baseline:** Accuracy = 79.1%, Judge = 3.17/5, Citation = 83.3%
- **Tool-Augmented:** Accuracy = **100.0%**, Judge = **5.00/5**, Citation = **100.0%**
- **Tool Calls:** 23 calls (Outline: 1, Section Inspections & Cross-references)

| Criterion | Baseline Status | Tool Status | Ground Truth Section | Baseline Cited | Tool Cited | Tool Judge Score |
| :--- | :---: | :---: | :--- | :--- | :--- | :---: |
| Governing Law & Jurisdiction | PASS (88%) | **PASS** (100%) | Section 17.1, Section 17.2 | Section 17.1 | Section 17.1, Section 17.2 | 5.0/5 |
| Limitation of Liability & Caps | FAIL (47%) | **PASS** (100%) | Section 11.2, Section 11.3, Section 11.4, Schedule B Section 4 | Section 11.2 | Section 11.2, Section 11.3, Section 11.4, Schedule B Section 4 | 5.0/5 |
| IP Ownership & Work-for-Hire | PASS (86%) | **PASS** (100%) | Section 4.1, Section 4.2, Section 4.3, Schedule A Section 2 | Section 4.2 | Section 4.1, Section 4.2, Section 4.3, Schedule A Section 2 | 5.0/5 |
| Indemnification Obligations & Limits | PASS (79%) | **PASS** (100%) | Section 12.1, Section 12.2, Section 11.4(a) | Section 12.1 | Section 12.1, Section 12.2, Section 11.4(a) | 5.0/5 |
| Termination Notice Periods | PASS (79%) | **PASS** (100%) | Section 10.2, Section 10.3, Section 10.4 | Section 10.2 | Section 10.2, Section 10.3, Section 10.4 | 5.0/5 |
| Confidentiality Duration & Survival | PASS (93%) | **PASS** (100%) | Section 6.2 | Section 6.2 | Section 6.2 | 5.0/5 |
| Audit Rights & Compliance Inspection | FAIL (42%) | **PASS** (100%) | Section 8.1, Section 8.2, Section 8.3, Schedule B Section 5 | Section 8.1 | Section 8.1, Section 8.2, Section 8.3, Schedule B Section 5 | 5.0/5 |
| Non-Solicitation of Personnel | PASS (100%) | **PASS** (100%) | Section 7.1, Section 7.2 | Section 7.1 | Section 7.1, Section 7.2 | 5.0/5 |
| Payment Timing & Late Fees | PASS (82%) | **PASS** (100%) | Section 3.2, Section 3.3, Section 3.4 | Section 3.2 | Section 3.2, Section 3.3, Section 3.4 | 5.0/5 |
| Dispute Resolution & Arbitration | PASS (79%) | **PASS** (100%) | Section 16.1 | Section 16.1 | Section 16.1 | 5.0/5 |
| Force Majeure & Suspension Rights | PASS (79%) | **PASS** (100%) | Section 14.1, Section 14.2, Section 14.3 | Section 14.1 | Section 14.1, Section 14.2, Section 14.3 | 5.0/5 |
| Assignment & Change of Control | PASS (82%) | **PASS** (100%) | Section 15.1, Section 15.2 | Section 15.1 | Section 15.1, Section 15.2 | 5.0/5 |
| Insurance Coverage Requirements | PASS (88%) | **PASS** (100%) | Section 9.1, Section 9.2 | Section 9.1 | Section 9.1, Section 9.2 | 5.0/5 |
| Warranties & Warranty Period | FAIL (63%) | **PASS** (100%) | Section 5.1, Section 5.2, Schedule C Section 2 | Section 5.1 | Section 5.1, Section 5.2, Schedule C Section 2 | 5.0/5 |
| Data Privacy & Breach Notification | PASS (79%) | **PASS** (100%) | Section 13.1, Section 13.2, Schedule B Sections 1-3 | Section 13.2 | Section 13.1, Section 13.2, Schedule B Sections 1-3 | 5.0/5 |
| Export Control & Sanctions | PASS (91%) | **PASS** (100%) | Section 18.3 | Section 18.3 | Section 18.3 | 5.0/5 |
| Subcontracting Permissions & Liability | PASS (82%) | **PASS** (100%) | Section 4.5 | Section 4.5 | Section 4.5 | 5.0/5 |
| Severability & Entire Agreement | PASS (82%) | **PASS** (100%) | Section 1.2, Section 18.1, Section 18.2 | Section 18.1 | Section 1.2, Section 18.1, Section 18.2 | 5.0/5 |
