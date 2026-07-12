"""Shard registry — ``next`` group row (data-model E1, FR-002).

Mission ``ci-test-topology-performance-01KXBJRT`` WP01. Registers the
``next`` row into the SAME :data:`tests._arch_shard_map.SHARD_GROUPS` registry
``tests/_arch_shard_map.py`` owns — one shard mechanism (registry + conftest
hook + parametrized completeness guard) shared by ``arch`` and ``next``, not a
cloned second one (D-044/C-003). ``tests/_arch_shard_map.py`` stays
``arch``-only; this sibling module owns the ``next`` row exclusively.

``roots`` are the exact 3 paths ``integration-tests-next`` runs today
(``.github/workflows/ci-quality.yml`` — the ``Run integration tests — next``
step): ``tests/next``, ``tests/specify_cli/next``, ``tests/runtime``. Note
this is scoped to the ``next`` *subdirectory* of ``tests/specify_cli`` only —
the sibling ``specify-cli-rest`` shard already ``--ignore``s
``tests/specify_cli/next`` (``ci-quality.yml``), so this registration does not
widen that job's selection; the rest of ``tests/specify_cli/`` is untouched.

The assignment below is a **placeholder** — a greedy bin-pack over a
``def test_`` count proxy (mirroring ``_arch_shard_map.py``'s own method),
covering every eligible ``test_*.py`` file under the 3 roots. It is
provisional pending WP06's real ``--durations=25`` evidence (T014), which
rebalances this table from measured wall-clock, not re-derives a different
split here.
"""

from __future__ import annotations

from tests._arch_shard_map import SHARD_GROUPS, ShardGroup

# Whole-file assignments under ``tests/next``.
_NEXT_SHARD_1_FILES: tuple[str, ...] = (
    "tests/next/test_composition_gate_widening.py",
    "tests/next/test_internal_runtime_coverage.py",
    "tests/next/test_next_claimable_payload.py",
    "tests/next/test_occurrence_gate_next_loop.py",
    "tests/next/test_prompt_file_invariant.py",
)
_NEXT_SHARD_2_FILES: tuple[str, ...] = (
    "tests/next/test_finalized_task_routing.py",
    "tests/next/test_internal_runtime_parity.py",
    "tests/next/test_mission_run_back_reference.py",
    "tests/next/test_next_command_integration.py",
    "tests/next/test_prompt_builder_unit.py",
    "tests/next/test_retrospective_terminus_wiring.py",
    "tests/next/test_runtime_bridge_unit.py",
)
_NEXT_SHARD_3_FILES: tuple[str, ...] = (
    "tests/next/test_decision_unit.py",
    "tests/next/test_internal_runtime_engine_coverage.py",
    "tests/next/test_next_package_unit.py",
    "tests/next/test_next_replay_parity_integration.py",
    "tests/next/test_plan_mission_runtime.py",
    "tests/next/test_prompt_step_schema_extensions.py",
    "tests/next/test_query_mode_unit.py",
    "tests/next/test_runtime_bridge_blocked_paths.py",
    "tests/next/test_runtime_pkg_notice_unit.py",
)

# Whole-file assignments under ``tests/specify_cli/next``.
_SPECIFY_CLI_NEXT_SHARD_1_FILES: tuple[str, ...] = (
    "tests/specify_cli/next/test_decision_validation.py",
    "tests/specify_cli/next/test_runtime_bridge.py",
    "tests/specify_cli/next/test_runtime_bridge_dispatch.py",
    "tests/specify_cli/next/test_workflow_software_dev_default_is_byte_stable.py",
)
_SPECIFY_CLI_NEXT_SHARD_2_FILES: tuple[str, ...] = (
    "tests/specify_cli/next/test_decision_dispatch.py",
    "tests/specify_cli/next/test_workflow_command.py",
    "tests/specify_cli/next/test_workflow_registry.py",
)
_SPECIFY_CLI_NEXT_SHARD_3_FILES: tuple[str, ...] = (
    "tests/specify_cli/next/test_runtime_bridge_composition.py",
    "tests/specify_cli/next/test_runtime_bridge_documentation_composition.py",
    "tests/specify_cli/next/test_runtime_bridge_research_composition.py",
    "tests/specify_cli/next/test_wp_prompt_governance_contract.py",
)

# Whole-file assignments under ``tests/runtime`` (including its ``next/``
# subdirectory — ``tests/runtime/next/test_import_paths.py`` is still under
# the ``tests/runtime`` root the CI step runs).
_RUNTIME_SHARD_1_FILES: tuple[str, ...] = (
    "tests/runtime/next/test_import_paths.py",
    "tests/runtime/test_agent_skills.py",
    "tests/runtime/test_bridge_cores.py",
    "tests/runtime/test_bridge_decide_next.py",
    "tests/runtime/test_config.py",
    "tests/runtime/test_global_runtime_convergence_unit.py",
    "tests/runtime/test_paths_unit.py",
    "tests/runtime/test_runtime_bridge_identity.py",
    "tests/runtime/test_runtime_identity_seam_wiring.py",
    "tests/runtime/test_setup_plan_sync_evidence.py",
    "tests/runtime/test_template_source_consolidation.py",
    "tests/runtime/test_utils.py",
    "tests/runtime/test_workspace_context_unit.py",
)
_RUNTIME_SHARD_2_FILES: tuple[str, ...] = (
    "tests/runtime/test_banner_visibility.py",
    "tests/runtime/test_bridge_compat_surface.py",
    "tests/runtime/test_bridge_composition.py",
    "tests/runtime/test_bridge_decision_builder.py",
    "tests/runtime/test_bridge_io.py",
    "tests/runtime/test_config_show_origin_integration.py",
    "tests/runtime/test_doctor_command_file_health.py",
    "tests/runtime/test_doctor_unit.py",
    "tests/runtime/test_e2e_runtime_integration.py",
    "tests/runtime/test_package_exports.py",
    "tests/runtime/test_resolver_unit.py",
    "tests/runtime/test_runtime_bridge_family_arch.py",
)
_RUNTIME_SHARD_3_FILES: tuple[str, ...] = (
    "tests/runtime/test_bootstrap_unit.py",
    "tests/runtime/test_bootstrap_version_fallback.py",
    "tests/runtime/test_bridge_engine.py",
    "tests/runtime/test_bridge_parity.py",
    "tests/runtime/test_bridge_retrospective.py",
    "tests/runtime/test_home_unit.py",
    "tests/runtime/test_project_resolver.py",
    "tests/runtime/test_runtime_identity_resolution.py",
    "tests/runtime/test_show_origin_unit.py",
    "tests/runtime/test_tmp_prompt_namespace.py",
    "tests/runtime/test_tool_checker.py",
)

# ``relpath -> shard`` for the whole ``next`` group (all 3 roots are whole-file
# units — none of ``tests/next`` / ``tests/specify_cli/next`` / ``tests/runtime``
# is folded in as a single whole-directory unit the way arch's adversarial /
# architecture / lint pole roots are).
_NEXT_FILE_ASSIGNMENT: dict[str, int] = {
    **dict.fromkeys(_NEXT_SHARD_1_FILES, 1),
    **dict.fromkeys(_SPECIFY_CLI_NEXT_SHARD_1_FILES, 1),
    **dict.fromkeys(_RUNTIME_SHARD_1_FILES, 1),
    **dict.fromkeys(_NEXT_SHARD_2_FILES, 2),
    **dict.fromkeys(_SPECIFY_CLI_NEXT_SHARD_2_FILES, 2),
    **dict.fromkeys(_RUNTIME_SHARD_2_FILES, 2),
    **dict.fromkeys(_NEXT_SHARD_3_FILES, 3),
    **dict.fromkeys(_SPECIFY_CLI_NEXT_SHARD_3_FILES, 3),
    **dict.fromkeys(_RUNTIME_SHARD_3_FILES, 3),
}

# The 3 ``integration-tests-next`` roots this group (and the collection hook,
# for this group) is scoped to.
_NEXT_ROOTS: tuple[str, ...] = (
    "tests/next",
    "tests/specify_cli/next",
    "tests/runtime",
)

# Register the ``next`` row into the shared registry (import-time side
# effect — this is the one place ``SHARD_GROUPS["next"]`` is assigned).
SHARD_GROUPS["next"] = ShardGroup(
    group="next",
    roots=_NEXT_ROOTS,
    shard_count=3,
    marker_prefix="next_shard",
    file_assignment=_NEXT_FILE_ASSIGNMENT,
)
