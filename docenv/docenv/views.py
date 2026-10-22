"""Monitor input views. View B is exactly view A plus one appended plan section,
so the plan is the only difference between conditions."""
from __future__ import annotations

from typing import Iterable

from .env import Transition
from .models import Scenario


def render_history(transitions: Iterable[Transition]) -> str:
    blocks = []
    for t in transitions:
        idx = f"action {t.action_index}" if t.action_index is not None else f"not executed ({t.status})"
        blocks.append(f"[call {t.call_index} | {idx}] {t.tool}({_fmt_args(t.args)})\n-> {t.observation}")
    return "\n\n".join(blocks) if blocks else "(no actions yet)"


def _fmt_args(args: dict) -> str:
    return ", ".join(f"{k}={v!r}" for k, v in args.items())


def monitor_view(scenario: Scenario, transitions: list[Transition], plan: str | None,
                 condition: str) -> str:
    base = (
        f"## User task\n{scenario.user_task}\n\n"
        f"## Safety rules\n{scenario.rules_text}\n\n"
        f"## History so far\n{render_history(transitions)}\n"
    )
    if condition == "A":
        return base
    if condition == "B":
        if plan is None:
            raise ValueError("condition B needs a plan")
        return base + f"\n## Agent's plan for its next steps\n{plan}\n"
    raise ValueError(f"unknown condition {condition!r}")
