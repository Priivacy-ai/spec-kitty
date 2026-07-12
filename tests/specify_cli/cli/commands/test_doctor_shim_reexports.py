"""Re-export closeout for the ``doctor`` orchestration shim (WP11, #2059).

The #2059 decomposition moved every subcommand's logic into ``_*_doctor`` /
``_*`` siblings. The public ``doctor`` import surface MUST stay byte-stable so the
58 doctor test files (and any external importer) keep resolving the contracted
symbols ``from specify_cli.cli.commands.doctor import ...`` — this test pins that
contract (FR-006, I-5).
"""

from __future__ import annotations

import importlib

import pytest

pytestmark = [pytest.mark.fast]

# The contracted public + test-facing private symbols (cli-surface-contract.md +
# the WP07 coordination helpers the doctor test files import).
_CONTRACTED_SYMBOLS = [
    # Public
    "app",
    "SlashCommandGap",
    # Slash / command-skill (WP05)
    "_load_slash_command_state",
    "_repair_slash_command_state",
    # Doctrine collectors (WP03)
    "_collect_profile_health",
    "_collect_org_layer_data",
    "_build_pack_entries",
    "_count_pack_artifacts",
    "_resolve_pack_version",
    # Doctrine render (pre-existing #1623 extraction)
    "_render_org_layer_section",
    # Shim-registry render (stays in doctor.py)
    "_print_overdue_details",
    # Coordination (WP07)
    "DoctorFinding",
    "_check_git_version",
    "_check_coordination_worktree_health",
    "_check_lane_sparse_checkout_drift",
]


@pytest.mark.parametrize("name", _CONTRACTED_SYMBOLS)
def test_contracted_symbol_resolves_from_doctor(name: str) -> None:
    module = importlib.import_module("specify_cli.cli.commands.doctor")
    assert hasattr(module, name), (
        f"{name!r} must remain importable from specify_cli.cli.commands.doctor"
    )


# ``test_app_is_a_typer_group_with_seventeen_commands`` (count-only) and
# ``test_pointer_comment_references_issue_2059`` (source-header string pin) were
# retired here (#2076, WP03): the command count is strictly subsumed by
# ``test_doctor_cli_surface_golden.py::test_registered_command_names_match_frozen_subcommands``,
# which asserts frozenset-equality (a stronger, name-aware contract that implies
# the count); the pointer-comment test asserted a source string with no
# behavioural contract.
