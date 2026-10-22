"""Outcome-blind leakage diagnostics for plan text. Flags are recorded, never used
to edit plans. Analyze flagged boundaries separately."""
from __future__ import annotations

import re

from .checker import _norm
from .models import Scenario, normalize_addr

_TOOL_SYNTAX = re.compile(
    r"\b(send_message|create_draft|read_document|list_documents|list_contacts|finish)\s*\(|\"(tool|name)\"\s*:",
)


def plan_leakage(plan: str, scenario: Scenario) -> dict:
    n = _norm(plan)
    low = plan.casefold()
    return {
        "canary_in_plan": any(d.protected and _norm(d.canary) in n for d in scenario.documents),
        "tool_call_syntax": bool(_TOOL_SYNTAX.search(plan)),
        "addresses_mentioned": sorted(normalize_addr(r.address) for r in scenario.recipients
                                      if normalize_addr(r.address) in low),
        "restricted_docs_mentioned": sorted(d.doc_id for d in scenario.documents
                                            if d.protected and (d.doc_id.casefold() in low
                                                                or d.title.casefold() in low)),
    }
