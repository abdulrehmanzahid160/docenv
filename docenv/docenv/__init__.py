"""docenv: a deterministic document-assistant sandbox for forecasting the first
safety-rule violation of an LLM agent, with and without access to its plan."""

from .models import Document, Recipient, Scenario, Tier, RULES_TEXT
from .env import DocEnv, ToolCall, Transition
from .checker import CHECKER_VERSION, check_transition, first_violation_index, policy_fingerprint
from .labels import PrefixLabel, label_prefix
from .views import monitor_view, render_history
from .leakage import plan_leakage
from .scenarios import FAMILIES, build_scenario, all_scenarios
from .splits import HELD_OUT_FAMILIES, DEV_FAMILIES, split_of
from .runner import Actor, ScriptedActor, EpisodeRecord, run_episode

__version__ = "0.1.0"
