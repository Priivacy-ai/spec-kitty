"""runtime — Spec Kitty execution core (FR-001).

Canonical top-level package for mission discovery, state-transition
decisioning, execution sequencing, profile/action invocation,
active-mode handling (HiC vs autonomous), and charter-artefact retrieval.

Mission: runtime-mission-execution-extraction-01KPDYGW
Extracted from: specify_cli.next, specify_cli.runtime (3.2.x)
"""
from __future__ import annotations

# Seam protocols (importable before WP03/WP04 move the implementations)
from runtime.seams.presentation_sink import PresentationSink
from runtime.seams.step_contract_executor import StepContractExecutor
from runtime.seams.profile_invocation_executor import ProfileInvocationExecutor

# NOTE: The following symbols will be re-exported once WP03/WP04 complete
# the module moves. Uncomment as each move lands:
#
# from runtime.decisioning.decision import Decision, DecisionKind, decide_next
# from runtime.bridge.runtime_bridge import RuntimeBridge
# from runtime.discovery.resolver import resolve_mission, ResolutionResult, ResolutionTier
# from runtime.discovery.home import get_kittify_home, get_package_asset_root

__all__ = [
    "PresentationSink",
    "StepContractExecutor",
    "ProfileInvocationExecutor",
]
