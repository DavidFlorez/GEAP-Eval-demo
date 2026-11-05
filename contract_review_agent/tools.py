"""
ADK Tools for Contract Review Agent.
Exposes contract inspection functions to google.adk.agents.LlmAgent.
"""

from pathlib import Path
from typing import Dict, Any, List
from agents.tools import ContractToolRegistry

# Initialize shared registry pointing to project dataset
DATASET_CONTRACTS = Path(__file__).resolve().parent.parent / "dataset" / "v1_contracts"
_registry = ContractToolRegistry(contracts_dir=DATASET_CONTRACTS)


def get_contract_outline(contract_id: str) -> Dict[str, Any]:
    """
    Returns the table of contents, sections, and schedules of a contract.
    
    Args:
        contract_id: The ID of the contract (e.g. '01_standard_nda', '02_vendor_services_agreement', '03_master_services_agreement').
    """
    return _registry.get_contract_outline(contract_id)


def get_contract_section(contract_id: str, section_id: str) -> Dict[str, Any]:
    """
    Retrieves the verbatim content of a specific section or schedule from the contract.
    
    Args:
        contract_id: The ID of the contract.
        section_id: The section or schedule identifier (e.g. 'SECTION 11', 'SECTION 6', 'SCHEDULE B').
    """
    return _registry.get_contract_section(contract_id, section_id)


def search_contract_clauses(contract_id: str, query: str, top_k: int = 3) -> Dict[str, Any]:
    """
    Searches the contract clauses for specific terms or concepts.
    
    Args:
        contract_id: The ID of the contract.
        query: Search keywords or phrases (e.g. 'limitation of liability', 'audit rights', 'breach notification', 'super-cap').
        top_k: Maximum number of matching clauses to return.
    """
    return _registry.search_contract_clauses(contract_id, query, top_k=top_k)


def verify_cross_reference(contract_id: str, source_section: str, reference_pointer: str) -> Dict[str, Any]:
    """
    Verifies cross-references mentioned in a clause (e.g. 'subject to Section 11.3', 'governed by Schedule B').
    Retrieves the target section to ensure carve-outs, super-caps, or priority exceptions are captured.
    
    Args:
        contract_id: The ID of the contract.
        source_section: The section containing the cross-reference (e.g. 'SECTION 11').
        reference_pointer: The cited cross-reference (e.g. 'Section 11.3', 'Schedule B', 'Section 12').
    """
    return _registry.verify_cross_reference(contract_id, source_section, reference_pointer)
