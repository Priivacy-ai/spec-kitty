# Mission Specification: Retire Standalone Tasks CLI

**Mission**: retire-standalone-tasks-cli-01KWAMQ3
**Mission type**: software-dev
**Closes**: #2167 (parent #1057)
**Status**: Draft (post-spec gate remediated 2026-06-29)

## Summary

Close the codebase-wide retirement of pre-3.0 status/task readers that #1057
began. #1057 retired the *shipped* legacy readers but left a parallel,
non-shipped **standalone tasks CLI** (`scripts/tasks/`) that still reads the
pre-3.0 lane-directory layout. This surface exists in three drifted copies, runs
only under tests (no `[project.scripts]` entry, no `subprocess`/`runpy`/`exec`
invocation, zero *production* importers), and stays alive solely because test
scaffolding binds to it — which also shields a block of stale dead-symbols from
the architectural ratchet.

This mission removes the standalone tasks CLI surface entirely (all three
copies), repoints or removes every *test* that references it, preserves its one
genuinely useful and otherwise-unreachable capability — opt-in
acceptance-artifact encoding normalization — on the **supported**
`spec-kitty accept` command, and sheds the grandfathered architectural-ratchet
entries the deletion unblocks. The supported surfaces
(`spec-kitty agent tasks` / `accept` / `merge`) keep their behavior; their
coverage is provided by the real-surface suites, not by the standalone CLI.

## Domain Language

- **Standalone tasks CLI** — the argparse program at `scripts/tasks/tasks_cli.py`
  (and its `task_helpers.py` / `acceptance_support.py` siblings) in three copies.
  Not a product surface; never invoked outside tests.
- **Supported surface** — the product commands `spec-kitty agent tasks`,
  `spec-kitty accept`, `spec-kitty merge`, `spec-kitty validate-encoding`.
- **Real-surface suites** — the canonical product-behavior tests this mission
  relies on for coverage: `tests/status/*`, `tests/agent/test_commands.py`,
  `tests/specify_cli/cli/commands/test_accept_*`, `tests/lanes/test_merge*.py`.
- **Pre-3.0 lane-directory layout** — legacy `tasks/{lane}/WP*.md` directories,
  retired from active runtime by #1057 (canonical model: flat `tasks/WP*.md` +
  `status.events.jsonl`).
- **Three copies** — `scripts/tasks/` (repo root), `.kittify/overrides/scripts/tasks/`
  (override snapshot), `src/specify_cli/scripts/tasks/` (packaged copy).

## User Scenarios & Testing

### Primary scenario — supported workflow is unchanged
A contributor (or CI) runs `spec-kitty agent tasks …`, `spec-kitty accept …`,
and `spec-kitty merge …` to drive task/status/accept/merge work. After this
mission these commands behave exactly as before. The `python scripts/tasks/tasks_cli.py …`
path no longer exists, but nothing in any documented workflow, command template,
doctrine, or CI job invoked it, so no user-facing flow breaks.

### Encoding-normalization scenario — capability preserved on the supported surface
A contributor whose acceptance artifacts contain mojibake (Windows-1252 / Latin-1
bytes, smart quotes/dashes) runs `spec-kitty accept --normalize-encoding`. The
command repairs the affected artifacts to clean UTF-8 before validating, then
proceeds. Previously this was reachable only through the standalone CLI's
`accept --normalize-encoding`; the capability now lives on the supported command,
delegating to the already-canonical `specify_cli.acceptance.normalize_feature_encoding`.
- With the flag absent (default), `spec-kitty accept` does **not** rewrite artifacts.
- With the flag absent **and** an artifact carrying invalid encoding, `accept`
  surfaces a clear, non-crashing encoding error (preserving the retired
  surface's "Invalid UTF-8 encoding → re-run with --normalize-encoding" UX),
  or — if the supported `accept` already handles malformed input gracefully —
  the existing behavior is documented and tested as-is (resolved in plan).

### Edge case — pre-3.0 lane-directory project
A pre-3.0 project with `tasks/{lane}/` directories is no longer silently read by
the deleted standalone legacy reader. The **canonical** pre-3.0 detection and
hard-reject on the supported surface (`upgrade/legacy_detector.is_legacy_format`,
`upgrade/pre30_guard`, the dashboard scanner, and the `m_0_9_0` migration) is
**retained unchanged** — that is exactly the runtime behavior #1057 kept. This
mission removes only the *standalone* surface's duplicate legacy reader.

### Invariant that must always hold
No legacy lane-directory reading or writing remains **in the standalone
`scripts/tasks/` surface** after this mission (the surface is gone), and no
production import path is broken. The canonical `is_legacy_format` detector and
the migration/dashboard paths that legitimately use it are preserved.

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Delete the repo-root standalone tasks CLI copy: `scripts/tasks/tasks_cli.py`, `task_helpers.py`, `acceptance_support.py`. | Proposed |
| FR-002 | Delete the override snapshot copy `.kittify/overrides/scripts/tasks/` (all three files). | Proposed |
| FR-003 | Delete the packaged copy `src/specify_cli/scripts/tasks/` (all three files), confirmed test-only with zero *production* importers, so the wheel no longer ships `specify_cli.scripts.tasks`. | Proposed |
| FR-004 | Resolve **every** test reference to the standalone surface — not a fixed list. Discover the complete set via grep (`specify_cli.scripts.tasks`, `scripts/tasks`, `ROOT_TASKS_CLI`/`SRC_TASKS_CLI`, `run_tasks_cli`) and classify each file into exactly one of: (a) **delete** — pure standalone scaffolding (e.g. `tests/cross_cutting/misc/test_tasks_cli_commands.py`, `tests/specify_cli/test_standalone_tasks_cli_canonical.py`, `tests/cross_cutting/misc/test_task_helpers.py`, `tests/specify_cli/scripts/test_task_helpers.py`, `tests/cross_cutting/misc/test_acceptance_support.py`, `tests/specify_cli/scripts/tasks/test_tasks_cli.py` + its `tests/specify_cli/scripts/**/__init__.py` package dirs); (b) **surgical edit** — files asserting a canonical-relevant contract via the dead module (see FR-009); (c) **leave** — files asserting the *absence* of the surface (e.g. `tests/cross_cutting/misc/test_template_compliance.py`); and remove the `scripts/tasks` `sys.path` injection plus the `run_tasks_cli` helper from `tests/utils.py`. The classification table is produced in plan; after this mission no test imports `specify_cli.scripts.tasks.*`. | Proposed |
| FR-005 | Preserve acceptance-artifact encoding normalization on the supported surface: add an opt-in `--normalize-encoding` flag to `spec-kitty accept` that repairs artifacts before validation by delegating to the canonical `specify_cli.acceptance.normalize_feature_encoding`; default (flag absent) performs no rewrite; and define the default malformed-input behavior per the encoding scenario above (graceful error, not a crash). | Proposed |
| FR-006 | Update build/lint configuration in `pyproject.toml` to drop the now-dangling references to the removed modules (the `scripts/tasks/*` and `.kittify/overrides/scripts/tasks/*` ruff per-file-ignores at `pyproject.toml:231-232` and the `specify_cli.scripts.tasks.*` mypy/module entries at `:341-343`). | Proposed |
| FR-007 | Shed **all** architectural-ratchet allowlist and audit entries that reference the deleted surface, across every gate file (discover via grep over `tests/architectural/`): the grandfathered `specify_cli.scripts.tasks.{task_helpers,acceptance_support}::*` symbols in `test_no_dead_symbols.py`; **all three** `specify_cli.scripts.tasks.*` module entries in `test_no_dead_modules.py`; the `scripts/tasks/tasks_cli.py::list_command` entry in `test_gate_read_literal_ban.py`; the `scripts/tasks/tasks_cli.py` write-site entry in `resolution_gate_allowlist.yaml`; any reference in `test_coord_read_residuals_closeout.py`; and the stale audit artifacts under `surface_resolution_audit/`. Lock in the matching `_baselines.yaml` shrinks to the new live sizes. | Proposed |
| FR-008 | Consumer-project upgrade migration scope is deferred to the plan phase. [NEEDS CLARIFICATION: whether to add an auto-discovered upgrade migration removing `scripts/tasks/` + `.kittify/overrides/scripts/tasks/` from already-initialized consumer projects (anchor: `m_0_10_0_python_only.py:235-251` already removes `.kittify/scripts/tasks/` but not the override snapshot), or limit the mission to this repository] <!-- decision_id: 01KWAMRNK3THM82XRK1FAH8J8A --> | Deferred |
| FR-009 | For each behavior-bearing test that reaches a canonical contract *through* the dead module, either repoint it to the canonical surface or record the coverage as genuinely dead-only. Known cases: (a) `tests/specify_cli/test_feature_metadata.py` asserts `_prepare_merge_metadata`/`_finalize_merge_metadata` malformed-JSON tolerance — functions defined **only** in `tasks_cli.py`; the plan must prove the canonical merge path (`merge/done_bookkeeping`, `merge/executor`) covers the same tolerance and repoint/delete accordingly, or document the loss and decide whether to port it; (b) `tests/specify_cli/acceptance/test_accept_pre30_hard_reject.py` mixes a canonical `collect_feature_summary` pre-3.0 test (must survive) with `tasks_cli.accept_command`/`verify_command` tests (must be split out), and the canonical hard-reject contract must retain a real-surface test; (c) `tests/specify_cli/test_acceptance_regressions.py` and `tests/upgrade/test_pre30_guard_wiring.py` import dead symbols and must be retargeted or trimmed. | Proposed |

### Non-Functional Requirements

| ID | Requirement | Measurable threshold | Status |
|----|-------------|----------------------|--------|
| NFR-001 | No change to the **real-surface suites'** behavior. | The four named real-surface suites pass with **zero** modifications to their assertions. (Test files that only *imported* the dead module — FR-004/FR-009 — are explicitly in scope for deletion/retargeting and are NOT "real-surface suites"; editing them does not violate this NFR.) | Proposed |
| NFR-002 | No net loss of *product* behavioral coverage. | A coverage map enumerates each retired standalone behavior → the real-surface test that still covers it, with **0** product behaviors left uncovered. The map MUST explicitly resolve the FR-009 cases (merge-metadata malformed-JSON tolerance; pre-3.0 hard-reject) — either naming the canonical test that covers them or recording an accepted, justified loss. | Proposed |
| NFR-003 | Quality gates pass. | `ruff` and `mypy` report **0** issues on changed files; the full test suite **collects and runs green** with **0** new failures (no collection-time `ImportError` from a missed importer; pre-existing/unrelated failures reported per the charter's Pre-existing Failure Reporting Rule). | Proposed |
| NFR-004 | The `accept` encoding behavior is directly tested on the supported surface. | ≥1 test asserts `--normalize-encoding` repairs a mojibake artifact; ≥1 test asserts default-off (no rewrite); ≥1 test asserts the without-flag malformed-input path surfaces a clear, non-crashing encoding error (FR-005). | Proposed |

### Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | No production importer of `specify_cli.scripts.tasks.*` exists or may be introduced; the deletions must not break any shipped code path or `[project.scripts]` entry. | Active |
| C-002 | Architectural-ratchet baselines must equal their live frozenset/file-list sizes after the change (burn-down policy, charter C-004); every touched allowlist only shrinks, never grows, and no dangling entry pointing at a deleted file remains. | Active |
| C-003 | The encoding-normalization preservation (FR-005) must reuse the canonical `specify_cli.acceptance.normalize_feature_encoding` — no re-implementation, and no standalone code (including the `rollback` / `--normalize-encoding` retry-path defect from coordination-topology-stabilization-01KTZVQ2) is carried over. | Active |
| C-004 | Terminology canon: use **Mission**, never "feature"; introduce no new legacy terminology in code or prose. | Active |
| C-005 | The canonical `is_legacy_format` detector and the supported-surface pre-3.0 detection/hard-reject/migration paths (`upgrade/legacy_detector`, `upgrade/pre30_guard`, `dashboard/scanner`, `m_0_9_0`) are **out of scope and must remain unchanged** — #1057 deliberately keeps them. | Active |

## Success Criteria

- **SC-1**: All three standalone `scripts/tasks/` copies are absent; no test imports `specify_cli.scripts.tasks.*`; the packaged wheel no longer contains `specify_cli.scripts.tasks`.
- **SC-2**: The full test suite **collects and passes**; the four named real-surface suites are unchanged in their assertions; the NFR-002 coverage map shows 0 product behaviors uncovered.
- **SC-3**: `spec-kitty accept --normalize-encoding` repairs mojibake acceptance artifacts on the supported surface; without the flag, `accept` performs no rewrite and surfaces a clear error on malformed input.
- **SC-4**: Every architectural ratchet/audit surface that referenced the deleted code is shrunk to its new live size (dead-symbol, dead-module, literal-ban, resolution-gate allowlists + audit artifacts); no dangling allowlist entry points at a deleted file.
- **SC-5**: No legacy lane-directory reading or writing remains **in the (now-removed) standalone surface**; the canonical `is_legacy_format` migration/dashboard paths are intact; no production import path is broken.

## Assumptions

- The standalone tasks CLI is dead at *product* runtime in all three copies: no `[project.scripts]` entry, no `subprocess`/`runpy`/`exec` invocation, and zero production importers (verified during investigation; re-verified at implementation as an ATDD guard). *Test* importers exist and are handled by FR-004/FR-009.
- The canonical `specify_cli.acceptance.normalize_feature_encoding` (and `specify_cli.text_sanitization`, used by `validate-encoding` and the dashboard scanner) remain in production and are unaffected by the deletion. The deleted `acceptance_support.py` is already a thin delegation shim to canonical, so FR-005 carries over no standalone logic.

## Out of Scope

- Any change to the canonical `specify_cli.acceptance` / `specify_cli.text_sanitization` encoding modules beyond wiring FR-005's opt-in flag.
- Any change to the canonical `is_legacy_format` / pre-3.0 guard / migration / dashboard paths (C-005).
- The consumer-project upgrade migration, pending the FR-008 decision in the plan phase.
- Any change to `category_4_backcompat_shims` or unrelated ratchet categories.
