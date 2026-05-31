"""No-dead-modules architectural gate (Mission B / Process Gap 2).

The Mission B post-merge review surfaced a process gap:

    WP08 cycle 1 shipped 370 lines + 14 ATDD tests with **zero live
    callers in `src/`**. The "no live caller" anti-pattern slipped past
    both the implementer's self-check and the cycle-1 reviewer's initial
    scan.

That cycle-1 failure was structural, not human:

    src/charter/mission_type_profiles.py exported MissionTypeProfile,
    resolve_governance, UnknownMissionTypeError. 14 tests called those
    symbols directly. Zero src/ files imported them. The cycle-2 fix
    wired resolve_governance into prompt_builder.py; a hard CI gate
    would have caught the missing wiring in cycle 1.

This test is that hard gate. It walks every `*.py` file under `src/`,
derives the module's dotted name (e.g. ``src/charter/mission_type_profiles.py``
→ ``charter.mission_type_profiles``), and verifies that **at least one
other file under `src/` imports it** -- via any of:

* ``from charter.mission_type_profiles import resolve_governance``
* ``from charter import mission_type_profiles``
* ``import charter.mission_type_profiles``
* ``from charter.mission_type_profiles.submodule import X``
* relative-import equivalents (``from . import X``, ``from .X import Y``)

Modules with zero such callers MUST appear in ``_ALLOWLIST`` with a
documented rationale. The allowlist categories are:

1. Auto-discovered packages -- ``upgrade.migrations.m_*`` modules loaded
   by ``pkgutil.iter_modules`` glob in
   ``src/specify_cli/upgrade/migrations/__init__.py``.

2. Build-script schema generators -- ``doctrine.*.models`` and
   ``doctrine.*.schema_models`` modules consumed by
   ``scripts/generate_schemas.py`` via dotted-string
   ``importlib.import_module``.

3. External CLI entry points -- modules invoked as
   ``python -m specify_cli.<path>`` from outside the import graph
   (e.g. the git pre-commit hook installed by ``hook_installer.py``).

4. Documented backward-compatibility shims -- top-level files whose
   module docstring is ``Backward-compat shim -- canonical home is
   ...``. Their role is to keep legacy import paths green.

5. WP-in-flight slot-holder adapters -- ``compat/_adapters/*`` files
   carrying the ``# adapter:no-logic`` marker, reserved for the WP07
   compat-planner wiring.

6. Frozen-contract internal re-exports -- ``next/_internal_runtime/
   {emitter,lifecycle,models}.py`` re-export modules from the
   shared-package-boundary-cutover internalization.

7. Grandfathered orphans -- modules that *should* have a runtime
   caller but currently don't (legitimate WP08-style "library written
   but never wired" cases). Each carries a ``# TODO(triage):`` comment;
   a follow-up mission must either wire them or delete them.

The ratchet is bidirectional: if a new file under ``src/`` lands with
zero callers and is not in the allowlist, the test fails. If an
allowlisted file gains a caller (good news -- the wiring landed), the
test ALSO fails so the maintainer remembers to shrink the allowlist.

See ``work/process-gap-2-no-dead-modules.md`` for the assessment that
produced this list.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


pytestmark = [pytest.mark.architectural]


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src"

# Files we never count as candidates because they cannot have a meaningful
# "caller" relationship -- package init shims are imported implicitly when
# the package is referenced, and CLI entry shims are referenced via
# pyproject.toml [project.scripts] rather than via Python imports.
_SKIP_FILENAMES: frozenset[str] = frozenset({"__init__.py", "__main__.py"})

# File-name prefixes to skip -- ``_compat*`` files are intentional
# re-export shims whose absence of static callers is the point.
_SKIP_FILENAME_PREFIXES: tuple[str, ...] = ("_compat",)


# Allowlist of modules whose lack of static src/ callers is documented and
# intentional. The allowlist is split into per-category frozensets so the
# ratchet-baseline meta-test (`tests/architectural/test_ratchet_baselines.py`)
# can track Cat-7 (grandfathered orphans) separately from the auto-discovery
# categories. See Slice F FR-112 for the refactor rationale.
#
# THIS ALLOWLIST IS A RATCHET. When an entry gains a real caller, remove
# it from this set -- the test enforces shrinkage. When a new orphan
# appears, do NOT add it here as a reflex: investigate first, then
# either wire it from runtime, delete it, or add it under category 7
# with a ``# TODO(triage):`` comment and a follow-up tracker ticket.

# ---------- 1. Auto-discovered via pkgutil.iter_modules ----------
# Loaded by src/specify_cli/upgrade/migrations/__init__.py's
# auto_discover_migrations() which scans the directory for
# m_*.py files. No static import; the @MigrationRegistry.register
# decorator fires at import time. base.py is excluded from this
# list because it IS imported statically (every migration does
# `from .base import BaseMigration`).
_CATEGORY_1_AUTO_DISCOVERED_MIGRATIONS: frozenset[str] = frozenset(
    {
        "specify_cli.upgrade.migrations.m_0_10_0_python_only",
        "specify_cli.upgrade.migrations.m_0_10_12_charter_cleanup",
        "specify_cli.upgrade.migrations.m_0_10_14_update_implement_slash_command",
        "specify_cli.upgrade.migrations.m_0_10_1_populate_slash_commands",
        "specify_cli.upgrade.migrations.m_0_10_2_update_slash_commands",
        "specify_cli.upgrade.migrations.m_0_10_6_workflow_simplification",
        "specify_cli.upgrade.migrations.m_0_10_8_fix_memory_structure",
        "specify_cli.upgrade.migrations.m_0_10_9_repair_templates",
        "specify_cli.upgrade.migrations.m_0_11_1_improved_workflow_templates",
        "specify_cli.upgrade.migrations.m_0_11_1_update_implement_slash_command",
        "specify_cli.upgrade.migrations.m_0_11_2_improved_workflow_templates",
        "specify_cli.upgrade.migrations.m_0_11_3_workflow_agent_flag",
        "specify_cli.upgrade.migrations.m_0_12_0_documentation_mission",
        "specify_cli.upgrade.migrations.m_0_12_1_remove_kitty_specs_from_gitignore",
        "specify_cli.upgrade.migrations.m_0_13_0_research_csv_schema_check",
        "specify_cli.upgrade.migrations.m_0_13_0_update_charter_templates",
        "specify_cli.upgrade.migrations.m_0_13_0_update_research_implement_templates",
        "specify_cli.upgrade.migrations.m_0_13_1_exclude_worktrees",
        "specify_cli.upgrade.migrations.m_0_13_5_add_commit_workflow_to_templates",
        "specify_cli.upgrade.migrations.m_0_13_8_target_branch",
        "specify_cli.upgrade.migrations.m_0_14_0_centralized_feature_detection",
        "specify_cli.upgrade.migrations.m_0_16_2_remove_wp_status_gitignore_rule",
        "specify_cli.upgrade.migrations.m_0_2_0_specify_to_kittify",
        "specify_cli.upgrade.migrations.m_0_4_8_gitignore_agents",
        "specify_cli.upgrade.migrations.m_0_6_5_commands_rename",
        "specify_cli.upgrade.migrations.m_0_6_7_ensure_missions",
        "specify_cli.upgrade.migrations.m_0_7_2_worktree_commands_dedup",
        "specify_cli.upgrade.migrations.m_0_7_3_update_scripts",
        "specify_cli.upgrade.migrations.m_0_8_0_remove_active_mission",
        "specify_cli.upgrade.migrations.m_0_8_0_worktree_agents_symlink",
        "specify_cli.upgrade.migrations.m_0_9_0_frontmatter_only_lanes",
        "specify_cli.upgrade.migrations.m_0_9_2_research_mission_templates",
        "specify_cli.upgrade.migrations.m_2_0_0_charter_directory",
        "specify_cli.upgrade.migrations.m_2_0_0_historical_status_migration",
        "specify_cli.upgrade.migrations.m_2_0_0_retire_git_hooks",
        "specify_cli.upgrade.migrations.m_2_0_11_install_skills",
        "specify_cli.upgrade.migrations.m_2_0_11_remove_clarify_command",
        "specify_cli.upgrade.migrations.m_2_0_1_fix_generated_command_templates",
        "specify_cli.upgrade.migrations.m_2_0_1_tool_config_key_rename",
        "specify_cli.upgrade.migrations.m_2_0_2_charter_context_bootstrap",
        "specify_cli.upgrade.migrations.m_2_0_6_consistency_sweep",
        "specify_cli.upgrade.migrations.m_2_0_7_fix_stale_overrides",
        "specify_cli.upgrade.migrations.m_2_0_9_state_gitignore",
        "specify_cli.upgrade.migrations.m_2_1_1_repair_skill_pack",
        "specify_cli.upgrade.migrations.m_2_1_2_fix_charter_doctrine_skill",
        "specify_cli.upgrade.migrations.m_2_1_2_fix_glossary_context_skill",
        "specify_cli.upgrade.migrations.m_2_1_2_fix_orchestrator_api_skill",
        "specify_cli.upgrade.migrations.m_2_1_2_fix_runtime_next_skill",
        "specify_cli.upgrade.migrations.m_2_1_2_install_git_workflow_skill",
        "specify_cli.upgrade.migrations.m_2_1_2_install_mission_system_skill",
        "specify_cli.upgrade.migrations.m_2_1_2_remove_release_skill",
        "specify_cli.upgrade.migrations.m_2_1_3_fix_planning_repository_terminology",
        "specify_cli.upgrade.migrations.m_2_1_4_enforce_command_file_state",
        "specify_cli.upgrade.migrations.m_2_2_0_profile_context_deployment",
        "specify_cli.upgrade.migrations.m_3_0_0_canonical_context",
        "specify_cli.upgrade.migrations.m_3_0_2_restore_prompt_commands",
        "specify_cli.upgrade.migrations.m_3_0_3_globalize_skill_pack",
        "specify_cli.upgrade.migrations.m_3_1_1_charter_rename",
        "specify_cli.upgrade.migrations.m_3_1_1_direct_canonical_commands",
        "specify_cli.upgrade.migrations.m_3_1_1_event_log_merge_driver",
        "specify_cli.upgrade.migrations.m_3_1_1_normalize_status_json",
        "specify_cli.upgrade.migrations.m_3_2_0_codex_to_skills",
        "specify_cli.upgrade.migrations.m_3_2_0_update_planning_templates",
        "specify_cli.upgrade.migrations.m_3_2_0a4_normalize_mission_lifecycle",
        "specify_cli.upgrade.migrations.m_3_2_0a4_safe_globalize_commands",
        "specify_cli.upgrade.migrations.m_3_2_1_strip_selection_config",
        "specify_cli.upgrade.migrations.m_3_2_3_unified_bundle",
        "specify_cli.upgrade.migrations.m_3_2_4_kittify_profile_handoff",
        "specify_cli.upgrade.migrations.m_3_2_4_repository_root_checkout_terminology",
        "specify_cli.upgrade.migrations.m_3_2_5_fix_prompt_file_workaround",
        "specify_cli.upgrade.migrations.m_3_2_6_charter_bundle_v2",
        # NOTE: WP01 (charter-pack-activation-layer-01KSYE4V) was expected to
        # add the three entries below.  They are added here as a WP01 gap fix
        # so the WP05 architectural gate passes before lanes are merged.
        "specify_cli.upgrade.migrations.m_3_2_0rc28_github_diff_attributes",
        "specify_cli.upgrade.migrations.m_3_2_7_activate_builtin_mission_types",
        # WP05 (charter-pack-activation-layer-01KSYE4V) migration added here.
        "specify_cli.upgrade.migrations.m_3_2_8_default_charter_pack",
    }
)

# ---------- 2. Build-script schema generators ----------
# Loaded by scripts/generate_schemas.py via dotted-string
# importlib.import_module to derive JSON schemas from Pydantic
# models. Never imported by runtime code.
_CATEGORY_2_BUILD_SCHEMA_GENERATORS: frozenset[str] = frozenset(
    {
        "doctrine.agent_profiles.schema_models",
        "doctrine.import_candidates.models",
        "doctrine.model_task_routing.models",
    }
)

# ---------- 3. External CLI / hook entry points ----------
# Invoked as `python -m specify_cli.policy.commit_guard_hook`
# from the git pre-commit hook script installed by
# src/specify_cli/policy/hook_installer.py. The module path
# appears only as the string literal MODULE in hook_installer.
# Stand-alone task helper scripts are invoked outside the spec-kitty
# import graph (legacy /scripts/tasks/ entry points kept for the
# acceptance_support compatibility wrapper).
_CATEGORY_3_EXTERNAL_CLI_ENTRYPOINTS: frozenset[str] = frozenset(
    {
        "specify_cli.policy.commit_guard_hook",
        "specify_cli.scripts.tasks.acceptance_support",
        "specify_cli.scripts.tasks.task_helpers",
        "specify_cli.scripts.tasks.tasks_cli",
    }
)

# ---------- 4. Documented backward-compat shims ----------
# Re-export modules whose docstring starts with
# ``Backward-compat shim -- canonical home is ...``. Tests pin
# the re-export contract; the lack of src/ callers is the point.
_CATEGORY_4_BACKCOMPAT_SHIMS: frozenset[str] = frozenset(
    {
        "specify_cli.acceptance_matrix",
        "specify_cli.core.identity_aliases",
        "specify_cli.doc_generators",
        "specify_cli.doc_state",
        "specify_cli.gap_analysis",
        "specify_cli.state_contract",
        "specify_cli.tasks_support",
        "specify_cli.workspace_context",
    }
)

# ---------- 5. WP-in-flight slot-holder adapters ----------
# Carry the `# adapter:no-logic` marker; reserved for the WP07
# compat-planner wiring. Removing them now would break
# tests/architectural/test_compat_shims.py's slot-presence
# assertion. See src/specify_cli/compat/__init__.py for the
# compat-shim mission context.
#
# charter.scope_router removed (post-merge remediation cycle 1, 2026-05-19):
# prompt_builder.py now imports build_with_scope from charter.scope_router,
# giving scope_router a live src/ caller. The WP09→WP11 wiring trigger has
# been reached; the allowlist entry is removed. See HIGH-1 in
# mission-review-report.md.
_CATEGORY_5_WP_IN_FLIGHT_ADAPTERS: frozenset[str] = frozenset(
    {
        "specify_cli.compat._adapters.detector",
        "specify_cli.compat._adapters.gate",
        "specify_cli.compat._adapters.version_checker",
        # specify_cli.next._internal_runtime.workflow_registry removed:
        # WP11 wired get_workflow() into planner.py (planner imports it
        # via workflow_registry at module scope), so the module now has a
        # live src/ caller.  WP11 removal trigger reached.
        # charter.scope_router removed: post-merge remediation cycle 1
        # wired prompt_builder._governance_context through build_with_scope.
        #
        # specify_cli.coordination.outbound: new SaaS-fanout deferral
        # helper landed by mission #1348 WP05/WP09. The new code path
        # (``BookkeepingTransaction.queue_saas_emission``) is tested by
        # ``tests/specify_cli/coordination/test_outbound.py`` but the 30+
        # production callers of ``emit_status_transition`` have NOT
        # been migrated yet (DRIFT-6 in mission #1348's post-merge
        # review). Migration is tracked under
        # Priivacy-ai/spec-kitty#1356; once landed, the module gains a
        # runtime caller and this entry can be removed.
        "specify_cli.coordination.outbound",
        # NOTE: WP01 (charter-pack-activation-layer-01KSYE4V) was expected to
        # add the entry below.  doctrine.missions.mission_step_repository
        # landed in charter-doctrine-mission-type-configuration-01KSWJVX as
        # the compound-key layered resolver for MissionStep definitions.  WP02
        # of charter-pack-activation-layer-01KSYE4V is the wiring trigger; once
        # WP02 merges and a live src/ caller exists, remove this entry.
        "doctrine.missions.mission_step_repository",
    }
)

# ---------- 6. Frozen-contract internal re-exports ----------
# Internalized from spec-kitty-runtime under
# shared-package-boundary-cutover-01KQ22DS. The CLI imports
# the implementation files (engine.py, events.py); these three
# exist as the per-task-layout public surface frozen in
# kitty-specs/.../contracts/internal_runtime_surface.md.
_CATEGORY_6_FROZEN_RUNTIME_REEXPORTS: frozenset[str] = frozenset(
    {
        "specify_cli.next._internal_runtime.emitter",
        "specify_cli.next._internal_runtime.lifecycle",
        "specify_cli.next._internal_runtime.models",
    }
)

# ---------- 7. Grandfathered orphans (HiC triage queue) ----------
# Modules that look like genuine "library written but never
# wired" cases. Tests exercise them, but no runtime caller does.
# Each MUST eventually be wired, deleted, or formally adopted
# into one of the categories above. Do not add new entries to
# this category without filing a follow-up tracker ticket.
#
# Per Slice F C-006 (binding), Cat-7 MUST shrink by >= 2 entries
# per major release; target = 0 by 4.0. WP01 of Slice F shrinks
# this list from 10 -> 7 by deleting three modules outright
# (doctrine.templates.repository, specify_cli.glossary.prompts,
# specify_cli.glossary.rendering) per DM-01KRX6N0YAFBY7MTJC0CN3D3E4.
_CATEGORY_7_GRANDFATHERED_ORPHANS: frozenset[str] = frozenset(
    {
        # TODO(triage): hidden_feature_option / LEGACY_FEATURE_HELP
        # landed in mission stability-and-hygiene-hardening-2026-04
        # WP07 but no CLI command adopted them.
        "specify_cli.missions._legacy_aliases",
        # TODO(triage): TaskProfile suggestion engine has unit tests
        # but no integration with `spec-kitty agent tasks`.
        "specify_cli.task_profile",
        # TODO(triage): centralized auth transport module covered only
        # by integration tests; production code paths still construct
        # transports inline.
        "specify_cli.auth.transport",
        # TODO(triage): replay / tracker-glue surfaces exercised only
        # by their dedicated integration tests; not invoked from any
        # runtime entry point.
        "specify_cli.sync.replay",
        "specify_cli.sync.tracker_client_glue",
        # TODO(triage): policy.audit append-only log is written by tests
        # only -- no runtime emission of PolicyAuditEvent objects yet.
        "specify_cli.policy.audit",
        # TODO(triage): documented stub awaiting the retrospective
        # lifecycle terminus runner (WP06 of a future mission).
        "specify_cli.retrospective.lifecycle",
    }
)


# Aggregate of every per-category set. The existing
# `test_no_new_dead_modules_under_src` check below treats this as the
# effective allowlist; the per-category frozensets above are the surface
# inspected by the ratchet-baseline meta-test
# (tests/architectural/test_ratchet_baselines.py).
_ALLOWLIST: frozenset[str] = (
    _CATEGORY_1_AUTO_DISCOVERED_MIGRATIONS
    | _CATEGORY_2_BUILD_SCHEMA_GENERATORS
    | _CATEGORY_3_EXTERNAL_CLI_ENTRYPOINTS
    | _CATEGORY_4_BACKCOMPAT_SHIMS
    | _CATEGORY_5_WP_IN_FLIGHT_ADAPTERS
    | _CATEGORY_6_FROZEN_RUNTIME_REEXPORTS
    | _CATEGORY_7_GRANDFATHERED_ORPHANS
)


def _is_candidate(path: Path) -> bool:
    """True iff *path* is a python module we want to gate on."""
    if "__pycache__" in path.parts:
        return False
    name = path.name
    if name in _SKIP_FILENAMES:
        return False
    return not any(name.startswith(prefix) for prefix in _SKIP_FILENAME_PREFIXES)


def _module_dotted(path: Path) -> str:
    """Return the dotted module name for *path* relative to ``src/``.

    Example: ``src/charter/mission_type_profiles.py`` →
    ``charter.mission_type_profiles``.
    """
    rel = path.relative_to(_SRC_ROOT).with_suffix("")
    return ".".join(rel.parts)


def _package_of(path: Path) -> str:
    """Return the dotted package containing *path* (for relative imports).

    For ``src/cli/commands/foo.py`` returns ``cli.commands``. For
    ``src/cli/commands/__init__.py`` also returns ``cli.commands`` (the
    init file's "containing package" is itself).
    """
    rel = path.relative_to(_SRC_ROOT).with_suffix("")
    parts = list(rel.parts)
    # Drop the final segment (either the module name or "__init__"); both
    # cases resolve relative imports against the same parent.
    return ".".join(parts[:-1])


def _resolve_import_from(node: ast.ImportFrom, containing_pkg: str) -> str:
    """Return the fully-resolved dotted module for an ``ImportFrom`` node.

    Handles absolute imports (level=0) and relative imports (level>=1)
    by trimming ``level-1`` segments from the containing package.
    """
    level = node.level or 0
    mod = node.module or ""
    if level == 0:
        return mod
    pkg_parts = containing_pkg.split(".") if containing_pkg else []
    # level=1 means "from this package", level=2 means "from parent",
    # etc. We drop (level-1) trailing parts from pkg_parts.
    base_parts = pkg_parts[: len(pkg_parts) - (level - 1)] if level > 1 else pkg_parts[:]
    if mod:
        base_parts = base_parts + mod.split(".")
    return ".".join(base_parts)


def _collect_import_targets(
    tree: ast.Module,
    containing_pkg: str,
) -> list[tuple[str, str, tuple[str, ...] | None]]:
    """Walk *tree* and yield ``(kind, resolved_module, imported_names)``.

    ``kind`` is ``"from"`` for ``ImportFrom`` and ``"import"`` for ``Import``.
    ``imported_names`` is a tuple of names for ``from X import a, b`` and
    ``None`` for plain ``import X``.

    We walk the FULL tree (including nested / function-level imports) so
    that lazy import patterns -- common in this codebase for keeping CLI
    startup fast -- still count as callers.
    """
    out: list[tuple[str, str, tuple[str, ...] | None]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            resolved = _resolve_import_from(node, containing_pkg)
            names = tuple(alias.name for alias in node.names)
            out.append(("from", resolved, names))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                out.append(("import", alias.name, None))
    return out


def _iter_src_python_files() -> list[Path]:
    """Yield every ``*.py`` file under ``src/`` (sorted, deterministic)."""
    return sorted(p for p in _SRC_ROOT.rglob("*.py") if "__pycache__" not in p.parts)


def _has_caller(
    target_path: Path,
    target_dotted: str,
    file_imports: list[tuple[Path, list[tuple[str, str, tuple[str, ...] | None]]]],
) -> bool:
    """Return True iff any OTHER file in *file_imports* imports *target_dotted*.

    A "caller" is any of:

    * ``from <target_dotted> import X`` (with any X)
    * ``from <parent> import <leaf>`` where parent.leaf == target_dotted
    * ``from <target_dotted>.<sub> import X`` (sub-module import)
    * ``import <target_dotted>`` / ``import <target_dotted>.<sub>``

    Relative imports inside the importer's tree have already been
    resolved to absolute form by ``_resolve_import_from``.
    """
    parts = target_dotted.split(".")
    parent = ".".join(parts[:-1])
    leaf = parts[-1]
    dotted_prefix = target_dotted + "."

    for caller_path, imports in file_imports:
        if caller_path == target_path:
            continue
        for kind, mod, names in imports:
            if kind == "from":
                if mod == target_dotted:
                    return True
                if mod == parent and names is not None and leaf in names:
                    return True
                if mod.startswith(dotted_prefix):
                    return True
            else:  # plain ``import X``
                if mod == target_dotted or mod.startswith(dotted_prefix):
                    return True
    return False


def _format_failure(
    *,
    new_orphans: list[str],
    stale_allowlist_entries: list[str],
) -> str:
    parts: list[str] = []
    if new_orphans:
        bullets = "\n  - ".join(sorted(new_orphans))
        parts.append(
            "No-dead-modules gate FAILED. The following src/ modules have\n"
            "ZERO non-test callers (no other src/ file imports them):\n"
            f"  - {bullets}\n"
            "\n"
            "This is the 'library written but never wired' anti-pattern\n"
            "(Mission B post-merge review, Process Gap 2). Fix options:\n"
            "\n"
            "  1) Wire the module from a runtime caller (best -- the code\n"
            "     ships AND is exercised in production paths).\n"
            "  2) Delete the module if it's not needed (preferred over\n"
            "     allowlisting if the module has no real consumer).\n"
            "  3) Add the module to `_ALLOWLIST` in this file under the\n"
            "     correct category, with a one-line rationale. Use\n"
            "     category 7 (`# TODO(triage):`) for genuinely orphaned\n"
            "     modules that need follow-up.\n"
            "\n"
            "See tests/architectural/test_no_dead_modules.py for the\n"
            "category guide and the WP08 cycle-1 case study that\n"
            "motivated this gate."
        )
    if stale_allowlist_entries:
        bullets = "\n  - ".join(sorted(stale_allowlist_entries))
        parts.append(
            "Stale `_ALLOWLIST` entries detected. The following modules\n"
            "are listed in the allowlist but now have at least one real\n"
            "src/ caller (good news -- the wiring landed):\n"
            f"  - {bullets}\n"
            "\n"
            "Fix: remove these entries from `_ALLOWLIST` in\n"
            "tests/architectural/test_no_dead_modules.py so the ratchet\n"
            "correctly reflects the smaller orphan surface."
        )
    return "\n\n".join(parts)


def test_no_new_dead_modules_under_src() -> None:
    """Pin the no-dead-modules invariant as a one-way ratchet.

    Every ``*.py`` file under ``src/`` (excluding ``__init__.py``,
    ``__main__.py``, and ``_compat*`` shims) must have at least one
    non-test caller in ``src/``, or appear in ``_ALLOWLIST`` with a
    documented rationale.

    The test fails on BOTH directions:

    * a new orphan appears (new module without a caller and not in the
      allowlist) -- this catches the WP08-style failure;
    * an allowlist entry gains a caller (the wiring landed but the
      entry was not removed) -- this keeps the ratchet honest.
    """
    candidate_files = [p for p in _iter_src_python_files() if _is_candidate(p)]

    # Build the import index over ALL src files (including __init__/__main__,
    # since they perform package-level imports that legitimately wire
    # submodules) but excluding files we can't parse.
    file_imports: list[
        tuple[Path, list[tuple[str, str, tuple[str, ...] | None]]]
    ] = []
    for path in _iter_src_python_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, OSError):
            # A parse failure is a different defect; skip rather than
            # mask the no-dead-modules signal.
            continue
        containing_pkg = _package_of(path)
        file_imports.append((path, _collect_import_targets(tree, containing_pkg)))

    actual_orphans: set[str] = set()
    for path in candidate_files:
        dotted = _module_dotted(path)
        if not _has_caller(path, dotted, file_imports):
            actual_orphans.add(dotted)

    new_orphans = sorted(actual_orphans - _ALLOWLIST)
    stale_allowlist_entries = sorted(_ALLOWLIST - actual_orphans)

    assert not new_orphans and not stale_allowlist_entries, _format_failure(
        new_orphans=new_orphans,
        stale_allowlist_entries=stale_allowlist_entries,
    )


def test_category_7_grandfathered_at_most_seven_entries() -> None:
    """AC-7 (Slice F WP01): Cat-7 grandfathered orphans MUST be <= 7.

    The Slice F mission shrank Cat-7 from 10 -> 7 by deleting
    ``doctrine.templates.repository`` (WP01 T005),
    ``specify_cli.glossary.prompts`` and
    ``specify_cli.glossary.rendering`` (WP01 T006). This assertion
    locks in the new ceiling so any regression that re-adds a Cat-7
    entry without further burn-down is caught immediately, independently
    of the per-category baseline in ``_baselines.yaml``.

    Per C-006 (binding), Cat-7 MUST shrink by >= 2 entries per major
    release; target = 0 by 4.0. This assertion is the floor side of
    that ratchet for the Slice F mission.
    """
    current = len(_CATEGORY_7_GRANDFATHERED_ORPHANS)
    assert current <= 7, (
        f"_CATEGORY_7_GRANDFATHERED_ORPHANS has {current} entries; "
        f"the Slice F WP01 AC-7 invariant caps it at 7. Either wire "
        f"or delete the regressed entry, OR if growth is unavoidable "
        f"escalate per the C-006 burn-down policy and update this "
        f"assertion together with _baselines.yaml and the charter."
    )
