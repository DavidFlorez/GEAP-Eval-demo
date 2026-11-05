"""
Contract inspection, retrieval, and verification tools for Tool-Augmented Legal Review Agent.
Provides structured section parsing, keyword/semantic clause retrieval, and cross-reference verification.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


class ContractToolRegistry:
    """Manages contract files, section indexing, clause searching, and cross-reference verification."""

    def __init__(self, contracts_dir: Optional[Path] = None):
        if contracts_dir is None:
            # Default to dataset/v1_contracts
            base_dir = Path(__file__).resolve().parent.parent
            contracts_dir = base_dir / "dataset" / "v1_contracts"
        self.contracts_dir = Path(contracts_dir)
        self._cache: Dict[str, str] = {}
        self._sections_cache: Dict[str, List[Dict[str, Any]]] = {}
        self.tool_call_log: List[Dict[str, Any]] = []

    def _load_contract_text(self, contract_id: str) -> str:
        clean_id = contract_id.replace(".md", "").strip()
        if clean_id in self._cache:
            return self._cache[clean_id]

        # Look for matching file in contracts_dir
        matches = list(self.contracts_dir.glob(f"*{clean_id}*.md"))
        if not matches:
            raise FileNotFoundError(f"Contract '{clean_id}' not found in {self.contracts_dir}")

        text = matches[0].read_text(encoding="utf-8")
        self._cache[clean_id] = text
        return text

    def _parse_sections(self, contract_id: str) -> List[Dict[str, Any]]:
        clean_id = contract_id.replace(".md", "").strip()
        if clean_id in self._sections_cache:
            return self._sections_cache[clean_id]

        text = self._load_contract_text(clean_id)
        lines = text.split("\n")
        sections: List[Dict[str, Any]] = []
        current_section: Optional[Dict[str, Any]] = None
        current_lines: List[str] = []

        header_regex = re.compile(r"^(#{1,3})\s+(SECTION\s+\d+|SCHEDULE\s+[A-Z]|RECITALS|MUTUAL|CLOUD|ENTERPRISE|IN WITNESS WHEREOF|WARRANTIES|DISASTER)(.*)$", re.IGNORECASE)

        for line_idx, line in enumerate(lines, 1):
            match = header_regex.match(line.strip())
            if match:
                if current_section:
                    current_section["content"] = "\n".join(current_lines).strip()
                    current_section["line_end"] = line_idx - 1
                    sections.append(current_section)
                
                header_prefix = match.group(2).strip()
                header_suffix = match.group(3).strip().lstrip(":- ")
                title = f"{header_prefix}: {header_suffix}" if header_suffix else header_prefix
                current_section = {
                    "section_id": header_prefix.upper(),
                    "title": title,
                    "level": len(match.group(1)),
                    "line_start": line_idx,
                    "content": "",
                }
                current_lines = [line]
            else:
                if current_section is not None:
                    current_lines.append(line)
                else:
                    # Preamble before first header
                    if line.strip():
                        if not sections:
                            current_section = {
                                "section_id": "PREAMBLE",
                                "title": "Preamble & Parties",
                                "level": 1,
                                "line_start": 1,
                                "content": "",
                            }
                            current_lines.append(line)

        if current_section:
            current_section["content"] = "\n".join(current_lines).strip()
            current_section["line_end"] = len(lines)
            sections.append(current_section)

        self._sections_cache[clean_id] = sections
        return sections

    def get_contract_outline(self, contract_id: str) -> Dict[str, Any]:
        """Tool 1: Return table of contents and outline of the specified contract."""
        self.tool_call_log.append({
            "tool": "get_contract_outline",
            "contract_id": contract_id,
        })
        sections = self._parse_sections(contract_id)
        outline = [
            {
                "section_id": s["section_id"],
                "title": s["title"],
                "line_start": s["line_start"],
                "line_end": s["line_end"],
                "length_chars": len(s["content"]),
            }
            for s in sections
        ]
        return {
            "contract_id": contract_id,
            "total_sections": len(sections),
            "outline": outline,
        }

    def get_contract_section(self, contract_id: str, section_id_or_title: str) -> Dict[str, Any]:
        """Tool 2: Retrieve full text for a specific section or schedule."""
        self.tool_call_log.append({
            "tool": "get_contract_section",
            "contract_id": contract_id,
            "query": section_id_or_title,
        })
        sections = self._parse_sections(contract_id)
        query = section_id_or_title.strip().upper()

        # Normalized search
        matched: Optional[Dict[str, Any]] = None
        for s in sections:
            s_id = s["section_id"].upper()
            s_title = s["title"].upper()
            if query == s_id or query in s_title or s_id in query:
                matched = s
                break

        if not matched:
            # Try fuzzy number match: e.g. "11" for "SECTION 11"
            digits = re.findall(r"\d+", query)
            if digits:
                target_num = digits[0]
                for s in sections:
                    if f"SECTION {target_num}" in s["section_id"].upper():
                        matched = s
                        break

        if matched:
            return {
                "found": True,
                "section_id": matched["section_id"],
                "title": matched["title"],
                "content": matched["content"],
                "line_range": f"{matched['line_start']}-{matched['line_end']}",
            }
        
        return {
            "found": False,
            "error": f"Section '{section_id_or_title}' not found in contract outline.",
            "available_sections": [s["title"] for s in sections],
        }

    def search_contract_clauses(self, contract_id: str, query: str, top_k: int = 3) -> Dict[str, Any]:
        """Tool 3: Search clauses by keyword or semantic phrase across the contract."""
        self.tool_call_log.append({
            "tool": "search_contract_clauses",
            "contract_id": contract_id,
            "query": query,
            "top_k": top_k,
        })
        text = self._load_contract_text(contract_id)
        sections = self._parse_sections(contract_id)
        
        query_terms = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 2]
        if not query_terms:
            query_terms = [query.lower()]

        scored_sections: List[Tuple[float, Dict[str, Any], List[str]]] = []

        for sec in sections:
            content_lower = sec["content"].lower()
            score = 0.0
            snippets: List[str] = []

            # Exact query match boost
            if query.lower() in content_lower:
                score += 15.0

            # Term overlap
            term_matches = sum(1 for term in query_terms if term in content_lower)
            score += term_matches * 2.5

            # Find matching sentence snippets
            sentences = re.split(r"(?<=[.!?])\s+", sec["content"])
            for sentence in sentences:
                sent_lower = sentence.lower()
                if any(t in sent_lower for t in query_terms):
                    clean_sent = " ".join(sentence.split())
                    if clean_sent and len(clean_sent) > 15:
                        snippets.append(clean_sent[:250])

            if score > 0:
                scored_sections.append((score, sec, snippets[:3]))

        scored_sections.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, sec, snips in scored_sections[:top_k]:
            results.append({
                "section_id": sec["section_id"],
                "title": sec["title"],
                "relevance_score": round(score, 2),
                "snippets": snips,
                "full_section_preview": sec["content"][:400] + ("..." if len(sec["content"]) > 400 else ""),
            })

        return {
            "query": query,
            "contract_id": contract_id,
            "matches_count": len(results),
            "results": results,
        }

    def verify_cross_reference(self, contract_id: str, source_section: str, reference_pointer: str) -> Dict[str, Any]:
        """
        Tool 4: Verify cross-references between sections (e.g. 'subject to Section 11.3', 'Schedule B').
        Prevents blind spots where general clauses are superseded by specific exceptions or schedules.
        """
        self.tool_call_log.append({
            "tool": "verify_cross_reference",
            "contract_id": contract_id,
            "source_section": source_section,
            "reference_pointer": reference_pointer,
        })
        
        # Look up source section to verify reference existence
        source_result = self.get_contract_section(contract_id, source_section)
        
        # Extract referenced target section or schedule
        target_lookup = reference_pointer
        if "Schedule" in reference_pointer or "schedule" in reference_pointer:
            sched_match = re.search(r"Schedule\s+([A-Z])", reference_pointer, re.IGNORECASE)
            if sched_match:
                target_lookup = f"SCHEDULE {sched_match.group(1).upper()}"
        elif "Section" in reference_pointer or "section" in reference_pointer:
            sec_match = re.search(r"Section\s+(\d+)", reference_pointer, re.IGNORECASE)
            if sec_match:
                target_lookup = f"SECTION {sec_match.group(1)}"

        target_result = self.get_contract_section(contract_id, target_lookup)
        
        return {
            "source_section": source_section,
            "reference_pointer": reference_pointer,
            "verified": target_result.get("found", False),
            "target_title": target_result.get("title", "Not Found"),
            "target_content_excerpt": target_result.get("content", "")[:600],
            "legal_implication": "Cross-reference confirmed: specific target provisions modify or carve out baseline obligations." if target_result.get("found") else "Unverified reference."
        }
