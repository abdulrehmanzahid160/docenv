"""Family-level split. FROZEN: do not change after any model run has been scored.
Every episode, and therefore every prefix, belongs to exactly one split."""
from .scenarios import FAMILIES

HELD_OUT_FAMILIES = frozenset({"audit_request", "recruiter_reference"})
DEV_FAMILIES = frozenset(FAMILIES) - HELD_OUT_FAMILIES


def split_of(family_id: str) -> str:
    if family_id in HELD_OUT_FAMILIES:
        return "test"
    if family_id in DEV_FAMILIES:
        return "dev"
    raise KeyError(family_id)
