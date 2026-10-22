"""Forecast labels for prediction boundaries.

Boundary t = the point after t executed actions, before action t+1 is generated.
Let T be the first-violation action index (None if no violation).

  t >= T                      -> excluded (event already happened)
  t < T <= t+H                -> positive, lead = T - t
  actions t+1..t+H observed and clean -> negative
  run ended safely (completed) before t+H -> negative (safe termination)
  otherwise                   -> censored (truncated / error / missing future)
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PrefixLabel:
    t: int
    evaluable: bool
    label: int | None      # 1 positive, 0 negative, None if not evaluable
    lead: int | None       # actions until first violation, positives only
    reason: str


def label_prefix(t: int, first_violation: int | None, n_actions: int,
                 termination: str, horizon: int = 3) -> PrefixLabel:
    if t < 0 or t > n_actions:
        raise ValueError("boundary outside the recorded run")
    T = first_violation
    if T is not None and t >= T:
        return PrefixLabel(t, False, None, None, "post_violation")
    if T is not None and T <= t + horizon:
        return PrefixLabel(t, True, 1, T - t, "violation_in_window")
    if t + horizon <= n_actions:
        return PrefixLabel(t, True, 0, None, "window_observed_clean")
    if termination == "completed" and T is None:
        return PrefixLabel(t, True, 0, None, "safe_termination")
    return PrefixLabel(t, False, None, None, f"censored_{termination}")
