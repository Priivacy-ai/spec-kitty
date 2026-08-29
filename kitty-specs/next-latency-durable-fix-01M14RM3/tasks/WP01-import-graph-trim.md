---
work_package_id: WP01
title: Import-graph trim on the next read path
dependencies: []
requirement_refs:
- FR-001
- NFR-001
- NFR-004
planning_base_branch: perf/next-latency-durable-fix
merge_target_branch: perf/next-latency-durable-fix
branch_strategy: Planning artifacts for this mission were generated on perf/next-latency-durable-fix. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into perf/next-latency-durable-fix unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-next-latency-durable-fix-01M14RM3
base_commit: 8453b376cc9279a332ee70ae750f7fac677755eb
created_at: '2026-08-28T20:59:17.212779+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Implementation
history:
- timestamp: '2026-08-28T18:24:17Z'
  agent: system
  action: Prompt generated via tasks phase authoring
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/next_cmd.py
create_intent:
- tests/specify_cli/next/test_next_import_footprint.py
- tests/specify_cli/next/test_next_output_preservation.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/next_cmd.py
- src/specify_cli/__init__.py
- tests/specify_cli/next/test_next_import_footprint.py
- tests/specify_cli/next/test_next_output_preservation.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match.

---

## Objective

**Honest-hygiene scope** (operator decision after the post-tasks squad). Defer the one *movable*
eager import on the `next` no-op/startup path so `--help`/error/no-mission invocations pay less
import cost. The step-projection the brief blamed is ~0ms and already cached — do NOT touch it.

**Read this first — the ceiling this WP cannot break (squad B2):** a *real* `next --json` query runs
`_run_query_mode → runtime_bridge` (`next_cmd.py:185`), and `runtime_bridge` re-pulls the entire
heavy foundation (doctrine/charter/events/pydantic/status.models). So deferring imports in
`next_cmd.py` yields ~0 on a real query (and on the CI fixture benchmark, which runs a real query).
NFR-001's ≥50% is therefore NOT claimed for the fixture here — that real import-floor reduction
lives in `runtime_bridge`/`doctrine`/`status.models` (shared-package boundary) and is a separate
architect-led follow-up (**#3789**). This WP's honest deliverable is the no-op-path win + a footprint
regression guard, not a fixture speedup.

## Context

- Movable import (the real anchor): `src/specify_cli/cli/commands/next_cmd.py:37` imports
  `specify_cli.core.checkout_ownership`, whose symbol runs only `if owned_checkout is not None`
  (`:161`) — so it is genuinely deferrable for the common no-op/query path. (The heavy trees enter
  transitively through this and `runtime_bridge`, NOT through module-scope `charter`/`status.models`
  imports at `:21-48` — those lines are lean.)
- Already done (do NOT re-implement): `src/specify_cli/cli/commands/__init__.py:176`
  `register_commands` already branches on `_is_next_fast_path(sys.argv)` and imports only `next_cmd`
  on the `next` path. The "503ms `_build_app`" figure was an isolation artifact. T003 is now
  "verify + regression-test that fast-path," not a new lever.
- Evidence: `research/post-spec-squad-findings.md`, `research/post-tasks-squad-findings.md` (B2),
  `quickstart.md`. **Force `PYTHONPATH=src`** for every measurement (global `spec-kitty` resolves the
  sibling fork).
- Contract: `contracts/next-output-preservation-contract.md` (NFR-004).

## Subtasks

T001 Profile with `PYTHONPATH=src python -X importtime -m specify_cli next …` (real query) AND a no-op path (`--help` / a no-mission invocation). Confirm empirically: (a) deferring `checkout_ownership` (`next_cmd.py:37`) removes its sub-chain from the no-op path; (b) a real query still imports `runtime_bridge`'s foundation regardless (documents why the fixture number won't move — B2). Record the no-op-path module-count / self-import delta you can actually achieve. (WP01)

T002 Defer the `checkout_ownership` import (and any other genuinely no-op-path-unreachable module T001 identifies) from module scope to function-local scope inside `next_cmd.py`, so no-op/startup invocations stop importing it. Preserve behavior: the deferred symbol must import identically at its first real use. ruff/mypy clean; one-line rationale comment. Do NOT chase the foundation `runtime_bridge` pulls — that's out of scope (B2). (WP01)

T003 Verify the existing `next` fast-path in `src/specify_cli/cli/commands/__init__.py:176` `register_commands` (`_is_next_fast_path`) is intact — that on the `next` path only `next_cmd` is registered, not sibling command modules. Add a small regression test locking that behavior so a future refactor can't silently re-import all commands on `next`. (Do NOT edit `__init__.py:161 _build_app` to "add" laziness — it already exists.) (WP01)

T004 Add `tests/specify_cli/next/test_next_import_footprint.py`: assert a **measured no-op-path footprint delta** — spawn `python -X importtime -m specify_cli --help` (or the no-mission path) and assert the deferred module (`specify_cli.core.checkout_ownership` and its sub-chain) is ABSENT / the module-count is at/under a pinned threshold. Do NOT assert absence of `runtime_bridge`'s foundation on a real query (B2 — unsatisfiable/misleading). Declare a `pytestmark` marker. This is the honest in-diff DoD. (WP01)

T005 Add `tests/specify_cli/next/test_next_output_preservation.py` implementing the NFR-004 byte-identical contract for the no-charter fixture: run `next --json` twice via subprocess, JSON-load, normalize only the `timestamp` field, assert equality. Do NOT reuse the masked `canonical()` oracle from `tests/runtime/test_bridge_parity.py`. Declare a `pytestmark` marker. (WP01)

## Branch Strategy

Planning branch and final merge target: `perf/next-latency-durable-fix`. `/spec-kitty.implement`
allocates this WP's execution worktree from `lanes.json`; completed changes merge back into
`perf/next-latency-durable-fix`.

## Definition of Done (observable in this diff)

- `-X importtime` on the **no-op path** shows a measurably lighter graph vs baseline (state the module-count / self-import delta). No claim of a real-query / CI-fixture speedup (B2).
- `test_next_import_footprint.py` passes and would fail if `checkout_ownership` were re-added at module scope; it does NOT assert absence of `runtime_bridge`'s foundation on a real query.
- The `register_commands` fast-path regression test passes.
- `test_next_output_preservation.py` passes (byte-identical `next` JSON except `timestamp`).
- `PYTHONPATH=src ruff check` and `mypy` clean on touched files. No projection cache added; `runtime_bridge`/`doctrine`/`status.models` untouched.

## Risks / Reviewer guidance

- **B2 honesty**: the win is real only for no-op/startup paths; a real query re-pulls the foundation via `runtime_bridge`. Reviewer: reject any footprint test that pretends to assert a real-query speedup, and any out-of-scope edit to `runtime_bridge`/`doctrine`/`status.models` (that's the deferred follow-up).
- A deferred import needed on the path just moves cost — verify T001's reachability.
- Circular-import hazards when moving imports to function scope — run the full `next` path once.
- Reviewer: output-preservation must use literal byte-identity (not the masked oracle).
