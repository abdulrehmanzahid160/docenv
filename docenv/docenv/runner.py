"""Episode runner enforcing the prediction-boundary order:

  at boundary t (t executed actions so far):
    1. actor writes its natural-language plan        (plan_ns)
    2. monitor views A and B are frozen              (views_ns)
    3. optional online monitor callback scores them
    4. actor generates the next tool call            (command_ns)
    5. environment executes it, checker labels it    (exec_ns)

The command does not exist when the views are frozen, so neither monitor can see
it. Monitors are passive: their scores never feed back into the actor.

If a call is rejected, the actor plans again at the same t (attempt 2, 3, ...).
Only attempt 1 at each t is `primary` and used in the main analysis, because
later attempts' history already shows the rejected command.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Callable, Protocol

from .checker import CHECKER_VERSION, first_violation_index, policy_fingerprint
from .env import DocEnv, ToolCall, Transition
from .labels import label_prefix
from .leakage import plan_leakage
from .models import Scenario
from .splits import split_of
from .views import monitor_view


class Actor(Protocol):
    config: dict

    def plan(self, scenario: Scenario, history: list[Transition]) -> str: ...

    def act(self, scenario: Scenario, history: list[Transition], plan: str) -> ToolCall: ...


MonitorFn = Callable[[str, str, dict], dict]   # (view_text, condition, context) -> result dict


@dataclass
class Boundary:
    t: int
    attempt: int
    primary: bool
    plan: str
    view_a: str
    view_b: str
    leakage: dict
    plan_ns: int
    views_ns: int
    command_ns: int | None = None
    monitor_results: dict = field(default_factory=dict)
    label: dict | None = None


@dataclass
class EpisodeRecord:
    episode_id: str
    scenario: dict
    split: str
    actor_config: dict
    checker_version: str
    policy_fingerprint: str
    horizon: int
    max_actions: int
    transitions: list[dict]
    boundaries: list[dict]
    first_violation_index: int | None
    n_actions: int
    termination_reason: str
    task_success: bool
    final_message: str | None
    error: str | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


def run_episode(scenario: Scenario, actor: Actor, *, max_actions: int = 20, horizon: int = 3,
                max_attempts_per_boundary: int = 3, failing_recipients=frozenset(),
                monitor_fn: MonitorFn | None = None, episode_id: str | None = None) -> EpisodeRecord:
    env = DocEnv(scenario, failing_recipients)
    boundaries: list[Boundary] = []
    error = None
    attempts_at_t: dict[int, int] = {}
    try:
        while not env.done:
            t = env.n_actions
            if t >= max_actions:
                env.termination_reason = "truncated"
                break
            attempt = attempts_at_t.get(t, 0) + 1
            if attempt > max_attempts_per_boundary:
                env.termination_reason = "stuck_rejections"
                break
            attempts_at_t[t] = attempt
            history = list(env.transitions)

            plan = actor.plan(scenario, history)
            plan_ns = time.monotonic_ns()
            va = monitor_view(scenario, history, plan, "A")
            vb = monitor_view(scenario, history, plan, "B")
            b = Boundary(t=t, attempt=attempt, primary=(attempt == 1), plan=plan, view_a=va,
                         view_b=vb, leakage=plan_leakage(plan, scenario), plan_ns=plan_ns,
                         views_ns=time.monotonic_ns())
            if monitor_fn is not None:
                ctx = {"scenario_id": scenario.scenario_id, "t": t, "attempt": attempt}
                b.monitor_results = {c: monitor_fn(v, c, ctx) for c, v in (("A", va), ("B", vb))}
            boundaries.append(b)

            call = actor.act(scenario, history, plan)
            b.command_ns = time.monotonic_ns()
            env.step(call)
    except Exception as e:  # actor/API failure: keep what was recorded
        env.termination_reason = "error"
        error = f"{type(e).__name__}: {e}"

    T = first_violation_index(env.transitions)
    term = env.termination_reason or "error"
    for b in boundaries:
        if b.primary:
            b.label = asdict(label_prefix(b.t, T, env.n_actions, term, horizon))

    exec_order_ok = all(b.command_ns is None or b.views_ns < b.command_ns for b in boundaries)
    assert exec_order_ok, "timing invariant violated: command generated before views were frozen"

    return EpisodeRecord(
        episode_id=episode_id or uuid.uuid4().hex[:12],
        scenario=scenario.summary(), split=split_of(scenario.family_id),
        actor_config=dict(getattr(actor, "config", {})),
        checker_version=CHECKER_VERSION, policy_fingerprint=policy_fingerprint(scenario),
        horizon=horizon, max_actions=max_actions,
        transitions=[tr.to_dict() for tr in env.transitions],
        boundaries=[asdict(b) for b in boundaries],
        first_violation_index=T, n_actions=env.n_actions, termination_reason=term,
        task_success=env.task_success(), final_message=env.final_message, error=error,
    )


class ScriptedActor:
    """Replays a fixed list of (plan, ToolCall). Used for checker validation and tests."""

    def __init__(self, steps: list[tuple[str, ToolCall]], name: str = "scripted"):
        self.steps = steps
        self.i = 0
        self.config = {"actor": name}

    def plan(self, scenario, history):
        return self.steps[self.i][0]

    def act(self, scenario, history, plan):
        call = self.steps[self.i][1]
        self.i += 1
        return call
