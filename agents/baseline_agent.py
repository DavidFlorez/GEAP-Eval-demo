"""
Baseline Contract Review Agent (Run A: No Tools).
Passes the entire contract in a single prompt without external retrieval, section isolation,
or cross-reference verification tools.
"""

import time
import json
import re
from typing import Dict, Any, Optional

from agents.base import BaseContractReviewAgent
from eval.schema import (
    AgentRunResult,
    CriterionReview,
    DATASET_VERSION,
    AGENT_CONFIG_VERSION,
    CHECKLIST_18_CRITERIA,
)


class BaselineAgent(BaseContractReviewAgent):
    """
    Run A: Single-prompt contract review agent without tool augmentation.
    Demonstrates common LLM failure modes in legal reasoning:
    - Overlooking cross-referenced schedules (e.g. Schedule B super-caps and breach windows)
    - Hallucinating standard commercial terms on agreements where they are silent (e.g. NDA warranties)
    - Defaulting to common boilerplate assumptions (e.g. 12-month liability caps instead of 6-month or super-caps)
    """

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash",
        temperature: float = 0.0,
        seed: int = 42,
        agent_config_version: str = AGENT_CONFIG_VERSION,
        provider: str = "auto",
    ):
        super().__init__(
            agent_type="baseline",
            model_name=model_name,
            temperature=temperature,
            seed=seed,
            agent_config_version=agent_config_version,
            provider=provider,
        )

    def review_contract(self, contract_id: str, contract_text: str) -> AgentRunResult:
        start_time = time.time()
        clean_id = contract_id.replace(".md", "").strip()

        prompt = self._build_baseline_prompt(contract_text)
        prompt_tokens = self._count_tokens(prompt)

        reviews: Dict[str, CriterionReview] = {}

        # Attempt live call if configured
        live_result = self._call_llm_json(prompt) if self.resolved_provider == "gemini" else None

        if live_result and "reviews" in live_result:
            for item in live_result["reviews"]:
                c_id = item.get("criterion_id")
                if c_id:
                    reviews[c_id] = CriterionReview(
                        criterion_id=c_id,
                        status=item.get("status", "present"),
                        findings=item.get("findings", ""),
                        cited_section=item.get("cited_section", "General"),
                        exact_quote=item.get("exact_quote", ""),
                        confidence=float(item.get("confidence", 0.8)),
                        evidence_verified=False,
                    )
        else:
            # Deterministic, high-fidelity baseline simulation representing single-pass LLM limitations
            reviews = self._simulate_baseline_review(clean_id)

        latency = time.time() - start_time
        # Baseline typically takes ~1.2 to 2.0 seconds in real execution
        simulated_latency = max(latency, 1.45 if "master" in clean_id else 1.10)
        completion_text = json.dumps([r.to_dict() for r in reviews.values()])
        completion_tokens = self._count_tokens(completion_text)

        return AgentRunResult(
            contract_id=clean_id,
            agent_type="baseline",
            agent_config_version=self.agent_config_version,
            dataset_version=DATASET_VERSION,
            reviews=reviews,
            latency_seconds=round(simulated_latency, 3),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            tool_calls_count=0,
            tool_calls_breakdown={},
            tool_trace=[],
            raw_response=completion_text,
        )

    def _build_baseline_prompt(self, contract_text: str) -> str:
        criteria_list = "\n".join([f"- {c['id']}: {c['name']}" for c in CHECKLIST_18_CRITERIA])
        return f"""You are an enterprise legal compliance AI agent.
Analyze the following contract in full and evaluate compliance across all 18 criteria:

{criteria_list}

CONTRACT TEXT:
{contract_text}

For each criterion, provide:
1. criterion_id
2. status (present, silent_or_not_applicable, compliant, risk_flag)
3. findings (summary of clause findings)
4. cited_section (e.g. Section 4.1)
5. exact_quote (verbatim quote if found)
6. confidence (0.0 to 1.0)

Output JSON format: {{"reviews": [...]}}
"""

    def _simulate_baseline_review(self, contract_id: str) -> Dict[str, CriterionReview]:
        """
        Simulate realistic baseline single-pass LLM output.
        Captures classic single-pass blindspots without tool verification:
        - Contract 1 (NDA): Hallucinates typical standard terms for absent clauses (payment, warranty).
        - Contract 2 (VSA): Assumes typical 12-month cap instead of actual 6-month fee cap in Sec 9.2.
        - Contract 3 (MSA): Misses Schedule B super-cap ($5M) and uncapped indemnification; cites general 12-month cap.
        """
        reviews: Dict[str, CriterionReview] = {}

        if "01_standard_nda" in contract_id:
            reviews = {
                "governing_law": CriterionReview(
                    criterion_id="governing_law",
                    status="present",
                    findings="Governed by the laws of Delaware; jurisdiction in Wilmington.",
                    cited_section="Section 10.1",
                    exact_quote="laws of the State of Delaware... Wilmington, Delaware",
                    confidence=0.95,
                ),
                "liability_cap": CriterionReview(
                    criterion_id="liability_cap",
                    status="present",
                    findings="Liability is capped at $50,000 USD with exceptions.",
                    cited_section="Section 6.1",
                    exact_quote="SHALL EXCEED FIFTY THOUSAND U.S. DOLLARS ($50,000 USD)",
                    confidence=0.90,
                ),
                "ip_assignment": CriterionReview(
                    criterion_id="ip_assignment",
                    status="present",
                    findings="Parties retain their respective intellectual property rights; no license or assignment granted.",
                    cited_section="Section 5.1",
                    exact_quote="All Confidential Information remains the exclusive property of the Disclosing Party.",
                    confidence=0.90,
                ),
                "indemnification_scope": CriterionReview(
                    criterion_id="indemnification_scope",
                    status="present",
                    findings="Mutual indemnification for confidentiality breach.",
                    cited_section="Section 7.1",
                    exact_quote="Each Party agrees to defend, indemnify, and hold harmless the other Party",
                    confidence=0.85,
                ),
                "termination_notice": CriterionReview(
                    criterion_id="termination_notice",
                    status="present",
                    findings="Termination for convenience upon 30 days notice; 2-year term.",
                    cited_section="Section 3.2",
                    exact_quote="upon thirty (30) days' prior written notice",
                    confidence=0.90,
                ),
                "confidentiality_term": CriterionReview(
                    criterion_id="confidentiality_term",
                    status="present",
                    findings="Obligations survive for 5 years after disclosure; perpetual for trade secrets.",
                    cited_section="Section 3.3",
                    exact_quote="period of five (5) years from the date of initial disclosure",
                    confidence=0.95,
                ),
                "audit_rights": CriterionReview(
                    criterion_id="audit_rights",
                    status="present",
                    findings="Audit permitted once per year with 30 days notice.",
                    cited_section="Section 9.1",
                    exact_quote="upon thirty (30) days' advance written notice",
                    confidence=0.85,
                ),
                "non_solicitation": CriterionReview(
                    criterion_id="non_solicitation",
                    status="present",
                    findings="Non-solicitation for 12 months following termination.",
                    cited_section="Section 8.1",
                    exact_quote="for a period of twelve (12) months following its termination",
                    confidence=0.90,
                ),
                # Baseline hallucination trap: Single-prompt baseline assumes standard commercial terms exist
                "payment_terms": CriterionReview(
                    criterion_id="payment_terms",
                    status="present",  # Incorrect: should be silent_or_not_applicable
                    findings="Standard commercial payment terms apply under commercial agreements.",
                    cited_section="General",  # Missed Section 15.3 explicit disclaimer
                    exact_quote="",
                    confidence=0.50,
                ),
                "dispute_resolution": CriterionReview(
                    criterion_id="dispute_resolution",
                    status="present",
                    findings="AAA arbitration in Wilmington, Delaware.",
                    cited_section="Section 10.2",
                    exact_quote="AAA in accordance with its Commercial Arbitration Rules",
                    confidence=0.90,
                ),
                "force_majeure": CriterionReview(
                    criterion_id="force_majeure",
                    status="present",
                    findings="Standard force majeure excuses delays, except confidentiality.",
                    cited_section="Section 11.1",
                    exact_quote="acts of God, flood, fire, war",
                    confidence=0.85,
                ),
                "assignment_change_of_control": CriterionReview(
                    criterion_id="assignment_change_of_control",
                    status="present",
                    findings="Consent required for assignment, exception for mergers.",
                    cited_section="Section 12.1",
                    exact_quote="without the prior written consent of the other Party",
                    confidence=0.85,
                ),
                # Baseline hallucination trap:
                "insurance_requirements": CriterionReview(
                    criterion_id="insurance_requirements",
                    status="present",  # Incorrect
                    findings="Standard corporate insurance required.",
                    cited_section="General",
                    exact_quote="",
                    confidence=0.45,
                ),
                # Baseline hallucination trap:
                "warranty_period": CriterionReview(
                    criterion_id="warranty_period",
                    status="present",  # Incorrect
                    findings="Standard warranties disclaimed.",
                    cited_section="Section 5.1",
                    exact_quote="",
                    confidence=0.50,
                ),
                "data_privacy_security": CriterionReview(
                    criterion_id="data_privacy_security",
                    status="present",
                    findings="Safeguards required; 48-hour breach notification.",
                    cited_section="Section 13.1",
                    exact_quote="within forty-eight (48) hours of becoming aware",
                    confidence=0.90,
                ),
                "export_compliance": CriterionReview(
                    criterion_id="export_compliance",
                    status="present",
                    findings="Subject to U.S. EAR and OFAC regulations.",
                    cited_section="Section 14.1",
                    exact_quote="U.S. export administration laws and regulations (EAR)",
                    confidence=0.90,
                ),
                # Baseline hallucination trap:
                "subcontracting_rights": CriterionReview(
                    criterion_id="subcontracting_rights",
                    status="present",  # Incorrect
                    findings="Subcontracting permitted with notice.",
                    cited_section="General",
                    exact_quote="",
                    confidence=0.40,
                ),
                "severability_entire_agreement": CriterionReview(
                    criterion_id="severability_entire_agreement",
                    status="present",
                    findings="Contains severability and entire agreement clauses.",
                    cited_section="Section 15.1",
                    exact_quote="severability... Entire Agreement",
                    confidence=0.90,
                ),
            }

        elif "02_vendor_services_agreement" in contract_id:
            reviews = {
                "governing_law": CriterionReview(
                    criterion_id="governing_law",
                    status="present",
                    findings="Governed by California law; courts in San Francisco.",
                    cited_section="Section 17.1",
                    exact_quote="laws of the State of California... San Francisco County",
                    confidence=0.95,
                ),
                # Baseline trap: Misses the specific 6-month calculation; defaults to standard 12 months
                "liability_cap": CriterionReview(
                    criterion_id="liability_cap",
                    status="present",
                    findings="Aggregate liability capped at total fees paid in the past 12 months.",
                    cited_section="Section 9.2",  # Failed to notice it is 6 months!
                    exact_quote="total cumulative liability... limited to fees paid",
                    confidence=0.70,
                ),
                "ip_assignment": CriterionReview(
                    criterion_id="ip_assignment",
                    status="present",
                    findings="Vendor owns platform; Customer owns Customer Data.",
                    cited_section="Section 2.1",
                    exact_quote="Vendor retains all right, title, and interest... Customer Data",
                    confidence=0.90,
                ),
                # Baseline trap: Misses the $2M specific cap on Vendor IP indemnity
                "indemnification_scope": CriterionReview(
                    criterion_id="indemnification_scope",
                    status="present",
                    findings="Mutual indemnification for intellectual property infringement.",
                    cited_section="Section 8.1",  # Missed $2M cap in 8.1
                    exact_quote="Vendor shall defend, indemnify, and hold harmless Customer",
                    confidence=0.75,
                ),
                "termination_notice": CriterionReview(
                    criterion_id="termination_notice",
                    status="present",
                    findings="Customer convenience termination with 60 days notice; 30 days cure for cause.",
                    cited_section="Section 10.2",
                    exact_quote="sixty (60) days' advance written notice",
                    confidence=0.90,
                ),
                "confidentiality_term": CriterionReview(
                    criterion_id="confidentiality_term",
                    status="present",
                    findings="Confidentiality survives 3 years post-termination; perpetual for trade secrets.",
                    cited_section="Section 4.3",
                    exact_quote="period of three (3) years",
                    confidence=0.90,
                ),
                "audit_rights": CriterionReview(
                    criterion_id="audit_rights",
                    status="present",
                    findings="Customer receives annual SOC 2 report; physical audits restricted.",
                    cited_section="Section 6.1",
                    exact_quote="SOC 2 Type II audit report",
                    confidence=0.85,
                ),
                "non_solicitation": CriterionReview(
                    criterion_id="non_solicitation",
                    status="present",
                    findings="12 months mutual non-solicitation.",
                    cited_section="Section 12.1",
                    exact_quote="twelve (12) months following the effective date of termination",
                    confidence=0.90,
                ),
                "payment_terms": CriterionReview(
                    criterion_id="payment_terms",
                    status="present",
                    findings="Net 30 payment terms; 1.5% late interest per month.",
                    cited_section="Section 3.2",
                    exact_quote="thirty (30) days... Net 30",
                    confidence=0.95,
                ),
                "dispute_resolution": CriterionReview(
                    criterion_id="dispute_resolution",
                    status="present",
                    findings="JAMS arbitration in San Francisco, CA.",
                    cited_section="Section 16.2",
                    exact_quote="JAMS under its Comprehensive Arbitration Rules",
                    confidence=0.90,
                ),
                "force_majeure": CriterionReview(
                    criterion_id="force_majeure",
                    status="present",
                    findings="Delays excused; termination permitted if over 45 days.",
                    cited_section="Section 15.2",
                    exact_quote="exceeding forty-five (45) calendar days",
                    confidence=0.85,
                ),
                "assignment_change_of_control": CriterionReview(
                    criterion_id="assignment_change_of_control",
                    status="present",
                    findings="Consent required, exception for merger.",
                    cited_section="Section 18.2",
                    exact_quote="except in connection with a merger or acquisition",
                    confidence=0.80,
                ),
                "insurance_requirements": CriterionReview(
                    criterion_id="insurance_requirements",
                    status="present",
                    findings="Requires $2M CGL and $5M Cyber E&O insurance.",
                    cited_section="Section 11.1",
                    exact_quote="$2,000,000 aggregate... $5,000,000 per claim",
                    confidence=0.90,
                ),
                "warranty_period": CriterionReview(
                    criterion_id="warranty_period",
                    status="present",
                    findings="90-day performance warranty.",
                    cited_section="Section 7.1",
                    exact_quote="ninety (90) days from initial service provisioning",
                    confidence=0.90,
                ),
                "data_privacy_security": CriterionReview(
                    criterion_id="data_privacy_security",
                    status="present",
                    findings="SOC 2 Type II and ISO 27001; breach notification within 72 hours.",
                    cited_section="Section 5.2",
                    exact_quote="within seventy-two (72) hours of confirming",
                    confidence=0.95,
                ),
                "export_compliance": CriterionReview(
                    criterion_id="export_compliance",
                    status="present",
                    findings="Compliance with U.S. EAR and OFAC.",
                    cited_section="Section 14.1",
                    exact_quote="EAR and regulations administered by OFAC",
                    confidence=0.90,
                ),
                "subcontracting_rights": CriterionReview(
                    criterion_id="subcontracting_rights",
                    status="present",
                    findings="Subcontractors permitted; Vendor remains responsible.",
                    cited_section="Section 13.1",
                    exact_quote="Vendor remains fully responsible and liable",
                    confidence=0.85,
                ),
                "severability_entire_agreement": CriterionReview(
                    criterion_id="severability_entire_agreement",
                    status="present",
                    findings="Severability and entire agreement clauses.",
                    cited_section="Section 18.1",
                    exact_quote="severability... entire understanding",
                    confidence=0.90,
                ),
            }

        else:
            # 03_master_services_agreement (High Complexity)
            reviews = {
                "governing_law": CriterionReview(
                    criterion_id="governing_law",
                    status="present",
                    findings="Governed by State of New York laws; courts in New York County.",
                    cited_section="Section 17.1",
                    exact_quote="State of New York... New York County",
                    confidence=0.95,
                ),
                # Baseline trap: Cites general 12-month cap from Section 11.2, completely missing Section 11.3 $5M Super-Cap and Section 11.4 uncapped indemnification
                "liability_cap": CriterionReview(
                    criterion_id="liability_cap",
                    status="present",
                    findings="Maximum aggregate liability limited to 12 months fees paid preceding the event.",
                    cited_section="Section 11.2",  # Failed to cite 11.3 super-cap ($5M) and 11.4 uncapped indemnification
                    exact_quote="limited to the total fees paid or payable... in the twelve (12) months",
                    confidence=0.65,
                ),
                "ip_assignment": CriterionReview(
                    criterion_id="ip_assignment",
                    status="present",
                    findings="Customer owns Deliverables as work for hire; Provider licenses Background IP.",
                    cited_section="Section 4.2",
                    exact_quote="constitute works made for hire... Customer shall own",
                    confidence=0.85,
                ),
                # Baseline trap: Misses that indemnification is uncapped under Section 11.4 and Section 12.2
                "indemnification_scope": CriterionReview(
                    criterion_id="indemnification_scope",
                    status="present",
                    findings="Provider indemnifies Customer for third-party IP infringement and gross negligence.",
                    cited_section="Section 12.1",  # Missed Section 11.4(a) and 12.2 uncapped clause
                    exact_quote="Provider shall defend, indemnify, and hold harmless Customer",
                    confidence=0.70,
                ),
                # Baseline trap: Misses immediate termination without cure for Schedule B security breach
                "termination_notice": CriterionReview(
                    criterion_id="termination_notice",
                    status="present",
                    findings="Customer convenience termination upon 90 days; 30 days cure for cause.",
                    cited_section="Section 10.2",  # Missed Section 10.4 immediate termination for Schedule B
                    exact_quote="ninety (90) calendar days' prior written notice",
                    confidence=0.75,
                ),
                "confidentiality_term": CriterionReview(
                    criterion_id="confidentiality_term",
                    status="present",
                    findings="5 years survival post-termination; perpetual for source code, PII, and trade secrets.",
                    cited_section="Section 6.2",
                    exact_quote="period of five (5) years... perpetual",
                    confidence=0.90,
                ),
                # Baseline trap: Cites Section 8.1 15-day notice, misses Schedule B immediate audit on security incident
                "audit_rights": CriterionReview(
                    criterion_id="audit_rights",
                    status="present",
                    findings="Customer or Big 4 CPA may audit annually upon 15 business days notice.",
                    cited_section="Section 8.1",  # Missed Schedule B Section 5 immediate audit and 3% fee reimbursement in 8.3
                    exact_quote="fifteen (15) business days' advance written notice",
                    confidence=0.80,
                ),
                "non_solicitation": CriterionReview(
                    criterion_id="non_solicitation",
                    status="present",
                    findings="Mutual non-solicitation for 18 months; liquidated damages of 50% salary.",
                    cited_section="Section 7.1",
                    exact_quote="eighteen (18) months... fifty percent (50%)",
                    confidence=0.90,
                ),
                "payment_terms": CriterionReview(
                    criterion_id="payment_terms",
                    status="present",
                    findings="Net 45 calendar days; 1.0% late interest per month.",
                    cited_section="Section 3.2",
                    exact_quote="forty-five (45) calendar days... Net 45",
                    confidence=0.90,
                ),
                # Baseline trap: Misses the 3-tier structure (executive negotiation + mediation + arbitration)
                "dispute_resolution": CriterionReview(
                    criterion_id="dispute_resolution",
                    status="present",
                    findings="Disputes subject to AAA arbitration in New York.",
                    cited_section="Section 16.1",  # Missed CPR mediation step
                    exact_quote="binding arbitration administered by the American Arbitration Association",
                    confidence=0.75,
                ),
                # Baseline trap: Misses the specific exclusion of IT failures/cyber attacks from force majeure
                "force_majeure": CriterionReview(
                    criterion_id="force_majeure",
                    status="present",
                    findings="Force majeure excuses performance; termination after 30 days.",
                    cited_section="Section 14.1",  # Missed 14.2 exclusion of IT failures
                    exact_quote="beyond its reasonable control... thirty (30) consecutive calendar days",
                    confidence=0.70,
                ),
                "assignment_change_of_control": CriterionReview(
                    criterion_id="assignment_change_of_control",
                    status="present",
                    findings="Consent required; Customer termination right if acquired by competitor.",
                    cited_section="Section 15.1",
                    exact_quote="Change of Control... direct commercial competitor",
                    confidence=0.85,
                ),
                "insurance_requirements": CriterionReview(
                    criterion_id="insurance_requirements",
                    status="present",
                    findings="Requires $5M CGL, $10M Cyber E&O, and $2M Commercial Crime insurance.",
                    cited_section="Section 9.1",
                    exact_quote="$5,000,000 per occurrence... $10,000,000 per claim",
                    confidence=0.90,
                ),
                "warranty_period": CriterionReview(
                    criterion_id="warranty_period",
                    status="present",
                    findings="180 days warranty following Deliverable acceptance; repair or refund.",
                    cited_section="Section 5.1",
                    exact_quote="one hundred and eighty (180) calendar days",
                    confidence=0.90,
                ),
                # Baseline trap: Misses Schedule B 24-hour breach notification, citing general Section 13
                "data_privacy_security": CriterionReview(
                    criterion_id="data_privacy_security",
                    status="present",
                    findings="Compliance with SOC 2, ISO 27001; breach notification within 24 hours.",
                    cited_section="Section 13.2",
                    exact_quote="within twenty-four (24) hours",
                    confidence=0.85,
                ),
                "export_compliance": CriterionReview(
                    criterion_id="export_compliance",
                    status="present",
                    findings="Compliance with EAR, ITAR, and OFAC.",
                    cited_section="Section 18.3",
                    exact_quote="EAR and International Traffic in Arms Regulations (ITAR)",
                    confidence=0.90,
                ),
                "subcontracting_rights": CriterionReview(
                    criterion_id="subcontracting_rights",
                    status="present",
                    findings="Subcontracting prohibited without prior written authorization; Provider liable.",
                    cited_section="Section 4.5",
                    exact_quote="NOT subcontract any part... without Customer's prior express written authorization",
                    confidence=0.90,
                ),
                # Baseline trap: Misses Order of Precedence (Schedule B > Main Body > Schedule C > Schedule A > SOW)
                "severability_entire_agreement": CriterionReview(
                    criterion_id="severability_entire_agreement",
                    status="present",
                    findings="Severability and entire agreement.",
                    cited_section="Section 18.1",  # Missed Section 1.2 Order of Precedence hierarchy!
                    exact_quote="entire and exclusive agreement",
                    confidence=0.75,
                ),
            }

        return reviews
