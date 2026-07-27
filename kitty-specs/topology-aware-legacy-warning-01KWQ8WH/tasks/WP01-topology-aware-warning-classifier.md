---
work_package_id: WP01
title: Topology-aware warning-only classifier + coupled runbook
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
tracker_refs: []
planning_base_branch: fix/topology-aware-legacy-warning
merge_target_branch: fix/topology-aware-legacy-warning
branch_strategy: Planning artifacts for this mission were generated on fix/topology-aware-legacy-warning. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/topology-aware-legacy-warning unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 1 - Warning classifier
assignee: ''
agent: "claude"
shell_pid: "1739073"
history:
- at: '2026-07-04T19:38:20Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/coordination/transaction.py
create_intent:
- tests/specify_cli/coordination/test_legacy_warning_classifier.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/coordination/transaction.py
- tests/integration/test_legacy_mission_fallback.py
- tests/specify_cli/coordination/test_legacy_warning_classifier.py
- docs/migrations/legacy-to-coordination.md
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Topology-aware warning-only classifier + coupled runbook

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

Follow Pedro's discipline: TDD (red first), Python 3.12+ idiom, `mypy --strict`, no suppressions.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

Stop the once-per-mission legacy-topology warning from over-firing on intentional coordination-less (`single_branch`/`lanes`) and `flattened` missions, while still warning on genuinely pre-SSOT legacy missions — **without touching worktree routing or write-contract selection**.

Done when:
- `single_branch`, `lanes`, `flattened`, `coord`, `lanes_with_coord` missions emit **no** legacy warning.
- A mission with no stored `topology` and no `coordination_branch` still warns once, and the message cites **both** the runbook **and** `spec-kitty migrate backfill-topology`.
- A malformed/unknown `topology` value → warns (documented default).
- `single_branch`/`lanes` still take the legacy lane-worktree + `primary_checkout_append` path (routing/write-contract unchanged) — proven by test.
- `mypy --strict` + `ruff` clean (no new suppressions); terminology gate passes.

## Context & Constraints

- Charter: `.kittify/charter/charter.md`. Plan: [../plan.md](../plan.md). **Full live-code evidence: [../research.md](../research.md) — read it.**
- **CRITICAL — split, don't repurpose (C-005)**: `_is_legacy_mission()` (`src/specify_cli/coordination/transaction.py:200-230`) is a SHARED predicate feeding routing (`:719-729`), write-contract (`:909` via `_legacy_mode` set at `:831`), AND the warning (`:730`). **Leave it, the routing block, `:831`, and `:909` UNCHANGED.** Add a separate warning-only classifier and gate only the emit.
- **CRITICAL — reader-choice trap (C-001)**: read topology via the **non-deriving** `stored_topology_from_meta` (`src/specify_cli/missions/_read_path_resolver.py:117`), which returns `None` for absent/malformed. Do **NOT** use `read_topology`/`resolve_topology`/`_derive_topology` — they DERIVE `SINGLE_BRANCH` for absent topology, which would silence genuine-legacy warnings.
- `MissionTopology` (`src/mission_runtime/context.py:64-67`) has four members: `single_branch`, `lanes`, `coord`, `lanes_with_coord`. `flattened` is a separate `meta.json` bool (`_FLATTENED_KEY = "flattened"`, `migration/backfill_topology.py:38`); read it inline via `meta.get("flattened")`.
- Trigger (from the issue's debugger-debbie refinement): warn iff `coordination_branch` falsy AND `stored_topology_from_meta(meta) is None` AND `meta.get("flattened")` falsy.
- No `__init__.py` change → no version bump.

## Branch Strategy

- **Strategy**: pr-bound (already-confirmed)
- **Planning base branch**: `fix/topology-aware-legacy-warning`
- **Merge target branch**: `fix/topology-aware-legacy-warning`

> Execution worktrees are allocated per computed lane from `lanes.json`. Do not edit these fields.

## Subtasks & Detailed Guidance

### Subtask T001 – Red: full test matrix

- **Files**: extend `tests/integration/test_legacy_mission_fallback.py`; create `tests/specify_cli/coordination/test_legacy_warning_classifier.py`.
- **Steps**:
  1. Parametrize the existing `_make_legacy_mission` fixture (`:70-123`) to accept `topology=` / `flattened=` kwargs, injecting `"topology": <value>` / `"flattened": True` into the `meta.json` dict.
  2. Warning matrix (assert stderr contains / does not contain the "legacy topology" line + marker file behavior):

     | Case | meta shape | Expected |
     |------|-----------|----------|
     | genuine-legacy | no coord_branch, no topology, no flattened | **WARN** + stderr cites runbook AND `spec-kitty migrate backfill-topology` |
     | single_branch | `topology: single_branch`, no coord_branch | no warn |
     | lanes | `topology: lanes`, no coord_branch | no warn |
     | flattened | `flattened: true` (+ topology single_branch) | no warn |
     | coord | coord_branch set (+ `topology: coord`) | no warn |
     | lanes_with_coord | coord_branch set (+ `topology: lanes_with_coord`) | no warn |
     | malformed | `topology: "garbage"`, no coord_branch, not flattened | **WARN** |

  3. Unit-test `_warrants_legacy_warning` directly (new file) for each shape.
  4. **Routing/write-contract invariance test**: assert a `single_branch`/`lanes` mission still resolves the legacy lane-worktree destination and `append_event` still selects `primary_checkout_append` (i.e. only the warning changed). This guards against a future collapse back into `_is_legacy_mission`.
  5. **Backfill-suppression test**: take a genuine-legacy mission (warns), write `topology` into its meta (simulating `backfill-topology`), re-run → no new warning.
- **Notes**: preserve the existing `test_legacy_mission_warning_emitted_once` (`:183-219`) behavior for the genuine-legacy case (regression guard) — extend its assertion to also require the backfill command string.

### Subtask T002 – Add `_warrants_legacy_warning` classifier

- **Files**: `transaction.py`.
- **Steps**: add near `_coordination_branch_from_meta` (`~:233`):
  ```python
  def _warrants_legacy_warning(repo_root: Path, mission_slug: str, mid8: str) -> bool:
      meta = _load_mission_meta(repo_root, mission_slug, mid8)  # same read _is_legacy_mission does
      if not isinstance(meta, dict):
          return False
      if meta.get("coordination_branch"):   # defensive; legacy_mode already excludes
          return False
      if meta.get("flattened"):
          return False
      from specify_cli.missions._read_path_resolver import stored_topology_from_meta
      return stored_topology_from_meta(meta) is None
  ```
  Optionally hoist a shared `_load_mission_meta(repo_root, slug, mid8) -> dict | None` (the meta-read that `_is_legacy_mission` `:217-227` and `_coordination_branch_from_meta` currently do inline) and route all three through it (S1192/DRY). Use a **function-local import** for `stored_topology_from_meta` (avoid import cycles; the module already uses late imports).

### Subtask T003 – Re-point the emit

- **Files**: `transaction.py`.
- **Steps**: at `:730`, replace the unconditional `_emit_legacy_warning_once(...)` with:
  ```python
  if _warrants_legacy_warning(repo_root, safe_mission_slug, safe_mid8):
      _emit_legacy_warning_once(repo_root, mission_id, safe_mission_slug)
  ```
  Do not alter `legacy_mode` (`:718`), the routing branch, `_legacy_mode` (`:831`), or the write-contract branch (`:909`).

### Subtask T004 – Amend the warning message

- **Files**: `transaction.py:341-347` (`_emit_legacy_warning_once` message string).
- **Steps**: extend the printed message so it cites **both** the runbook (`docs/migrations/legacy-to-coordination.md`) **and** the command `spec-kitty migrate backfill-topology`. Message-only change; do not touch the marker/idempotency logic. Keep terminology-canon-clean.

### Subtask T005 – Update the coupled runbook

- **Files**: `docs/migrations/legacy-to-coordination.md`.
- **Steps**: rewrite three spots to match the shipped behavior:
  - Bullet `:61-65`: `single_branch`/`lanes` **no longer** see the warning (topology-aware now).
  - Flattened bullet `:66-69`: clarify flattened missions do not warn.
  - Path A note `:125-127`: backfilling a genuine-legacy mission now **suppresses** future warnings (a deliberate contract change).
  Then run `.venv/bin/python -m pytest tests/architectural/test_no_legacy_terminology.py -q`.

### Subtask T006 – Green + quality gates

- **Steps**:
  1. `.venv/bin/python -m pytest tests/integration/test_legacy_mission_fallback.py tests/specify_cli/coordination/test_legacy_warning_classifier.py -q` → green.
  2. `.venv/bin/python -m pytest tests/architectural/test_no_legacy_terminology.py -q` → green.
  3. `.venv/bin/mypy --strict src/specify_cli/coordination/transaction.py` and `.venv/bin/ruff check <changed files>` → zero issues, no new suppressions.

## Test Strategy

Tests REQUIRED (ATDD, NFR-002). The reader-choice trap (research residual #1) is pinned by the **genuine-legacy** + **single_branch** cases together — both mandatory. The routing-invariance and backfill-suppression tests are mandatory (plan residuals #2/#3).

## Risks & Mitigations

- **Reader-choice trap**: using a deriving reader silences genuine-legacy → the genuine-legacy + single_branch tests pin it.
- **Routing regression**: never edit `_is_legacy_mission`/`:719-729`/`:909` → the invariance test proves it.
- **Import cycle**: function-local import of `stored_topology_from_meta`.
- **Terminology gate**: runs only in CI's `integration-tests-core-misc` — run locally (T005).

## Review Guidance

- Confirm `_is_legacy_mission`, routing (`:719-729`), and write-contract (`:909`) are byte-for-byte unchanged; only the warning gate + message + runbook changed.
- Confirm the classifier uses `stored_topology_from_meta` (non-deriving), not `read_topology`/`resolve_topology`.
- Confirm the genuine-legacy test asserts BOTH the runbook and `spec-kitty migrate backfill-topology`; confirm routing-invariance + backfill-suppression tests exist and pass.
- Confirm all four topology members + flattened + malformed are covered; `mypy --strict` + `ruff` + terminology gate clean.

## Activity Log

- 2026-07-04T19:38:20Z – system – Prompt created.
- 2026-07-04T19:48:18Z – claude – shell_pid=1606922 – Assigned agent via action command
- 2026-07-04T20:02:19Z – claude – shell_pid=1606922 – Ready for review: topology-aware classifier + tests + docs, all green
- 2026-07-04T20:02:54Z – claude – shell_pid=1670598 – Started review via action command
- 2026-07-04T20:09:36Z – user – shell_pid=1670598 – Moved to planned
- 2026-07-04T20:10:38Z – claude – shell_pid=1702379 – Started implementation via action command
- 2026-07-04T20:16:51Z – claude – shell_pid=1702379 – Moved to for_review
- 2026-07-04T20:17:32Z – claude – shell_pid=1739073 – Started review via action command
