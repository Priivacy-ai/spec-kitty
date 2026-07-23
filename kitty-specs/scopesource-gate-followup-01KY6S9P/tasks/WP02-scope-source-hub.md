---
work_package_id: WP02
title: 'scope_source.py hub: factory, selection, predicates, mixin, identity helper'
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-005
- FR-006
- FR-007
- FR-013
- FR-014
- NFR-002
- NFR-005
planning_base_branch: fix/scopesource-gate-followup
merge_target_branch: fix/scopesource-gate-followup
branch_strategy: Planning artifacts for this mission were generated on fix/scopesource-gate-followup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/scopesource-gate-followup unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
- T012
phase: Phase 2 - scope_source additive surface
history:
- at: '2026-07-23T10:19:53Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/review/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/review/scope_source.py
- tests/review/test_scope_source.py
- docs/development/review-gates.md
role: implementer
tags: []
task_type: implement
tracker_refs:
- '#2873'
---

# Work Package Prompt: WP02 – scope_source.py hub

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its
guidance before parsing the rest.

- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for `implement`
on `src/specify_cli/review/`.

---

## ⚠️ IMPORTANT: Review Feedback

Check `review_ref` (via `spec-kitty agent status` / the Activity Log) before starting; address all feedback.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in fenced code blocks.

---

## Objectives & Success Criteria

Land **every additive change to `scope_source.py`** that WP03/WP04 consume, all behavior-preserving for
the two shipped sources (guarded by WP01's NFR-001 golden). This WP owns `scope_source.py` and its
dedicated test outright — no other WP edits it.

Complete when:

- **`resolve_scope_source` factory** (FR-003) is hoisted into `scope_source.py`, config-selective
  (FR-014), importable by both the head hook and the implement-time baseline path — no import cycle.
- **`scope_source_identity(scope_source, raw)` helper** (FR-009 producer / NFR-005) exists as the SINGLE
  function both baseline capture (WP03) and head diff (WP04) will call to derive the `source class +
  parse-mode` token.
- **Two independent predicates** (FR-005) — `empty_scope_is_coverage_gap` (policy) and
  `exposes_scope_breakdown` (capability) — back onto **distinct** signals; a synthetic source can satisfy
  one without the other.
- **`ScopeBreakdownMixin`** (FR-006) provides `file_to_scope` as a projection over `scope_breakdown`;
  `GateCoverageScopeSource` inherits it and implements only `scope_breakdown`; `DeclaredCommandScopeSource`
  stays a structural implementer with neither.
- The stale `scope_source.py:51-55` "lands with #2873" comment and `docs/development/review-gates.md:174`
  single-authority line are corrected (FR-014/FR-013).
- Tests: intent-encoding migration (FR-007) + NFR-005 dual-root equivalence, all green; the WP01 NFR-001
  golden still replays byte-identical (the mixin refactor is behavior-preserving).

Requirements covered: **FR-003, FR-005, FR-006, FR-007, FR-014, NFR-005**; FR-009/FR-013 (in part).
Carrier for IC-04, IC-06, IC-07, IC-08, IC-14 + the `scope_source_identity` producer.

## Context & Constraints

- **Design authorities**: [data-model.md §3 (factory), §4 (predicates+mixin), §1 (identity token)](../data-model.md);
  [contracts/scope-source-contract.md](../contracts/scope-source-contract.md);
  [plan.md IC-04/06/07/08/14](../plan.md); [research.md D-2..D-5](../research.md);
  [post-plan-squad.md B-sel / M-nfr5s / M-nfr5r / mixin-rename / carla-2](../reviews/post-plan-squad.md).
- **Factory home + no-cycle rule** (data-model §3): `resolve_scope_source(repo_root, *,
  filter_groups_override=None, composite_routing_override=None) -> ScopeSource`. Both current consumers
  already import `scope_source.py`, so no new edge. The factory MUST NOT import back into
  `tasks_move_task.py`; the two monkeypatch seams (`_pre_review_gate_filter_groups` /
  `_pre_review_gate_composite_routing`, `tasks_move_task.py:828-847`) stay in `tasks_move_task.py` and are
  **passed as parameters** — WP04 updates the thin `_mt_resolve_scope_source` wrapper to thread them.
- **Selection policy** (FR-014, B-sel — the load-bearing operator decision): `DeclaredCommandScopeSource`
  when `review.test_command` is present (a non-pytest consumer), else `GateCoverageScopeSource`. Read the
  SAME config surface `baseline._get_test_command` reads (`baseline.py:124-148`) — do NOT invent a key.
  **spec-kitty itself has no `review.test_command` → must still route to `GateCoverageScopeSource`.** A
  wrong policy silently re-routes every consumer's gate — test BOTH branches explicitly.
- **`scope_source_identity` token** (data-model §1): `"<SourceClass>/<parse-mode>"`, parse-mode ∈
  `{junit_xml, text, none, unknown}`, sourced from the **source-owned `parse_mode(raw)`** authority
  (T007) — NOT a second re-inspection of `raw`. `GateCoverageScopeSource` is junit-only (`:413-427`);
  `DeclaredCommandScopeSource` is the three-way decision (`:527-540`). The token **excludes the command
  by design** (NFR-005 carries command equality separately). Compute it here so WP03/WP04 share ONE
  function.
- **Two-signal predicates** (data-model §4, carla-2 trap): `exposes_scope_breakdown` backs onto
  `isinstance(source, ScopeBreakdownSource)`; `empty_scope_is_coverage_gap` backs onto a **distinct**
  `getattr(source, "treats_empty_scope_as_coverage_gap", False)` `ClassVar` marker. They MUST read
  different signals — that independence is the US3 AS3 weld-is-gone proof; making both read the same
  `isinstance` is the failure mode.
- **Mixin, not Protocol default** (FR-006): a `Protocol` default body never reaches a structural
  implementer. `ScopeBreakdownMixin(abc.ABC)` with `treats_empty_scope_as_coverage_gap: ClassVar[bool] =
  True`, `@abc.abstractmethod scope_breakdown(...)`, and a concrete `file_to_scope` projection.
  `GateCoverageScopeSource` (`scope_source.py:288-433`) inherits it, drops its hand-written `file_to_scope`
  (`:355-362`), keeps `scope_breakdown` (`:364-411`). `DeclaredCommandScopeSource` (`:481-540`) inherits
  NEITHER → `empty_scope_is_coverage_gap` → `False`.
- **Behavior preservation**: the mixin refactor changes NO verdict. The WP01 golden is the guard — run it
  after T009.
- **Quality bars (NFR-002)**: `mypy --strict` + `ruff` zero issues, complexity ≤15, ≥90% new-code
  coverage; each new predicate/helper/branch has a focused test. No `# noqa` / `# type: ignore`.
- **Do NOT edit** `pre_review_gate.py` (WP04 swaps the predicate call-sites), `baseline.py` /
  `workflow_executor.py` (WP03 consumes the factory + helper), or `tasks_move_task.py` (WP04 owns the
  wrapper). Expose everything downstream needs as importable symbols on `scope_source.py`.

## Branch Strategy

- **Strategy**: single mission branch (file-partitioned ownership)
- **Planning base branch**: `fix/scopesource-gate-followup`
- **Merge target branch**: `fix/scopesource-gate-followup`

## Subtasks & Detailed Guidance

### Subtask T006 – Hoist `resolve_scope_source` factory

- **Purpose**: One factory both baseline capture and the head hook import.
- **File**: `src/specify_cli/review/scope_source.py`.
- **Steps**: Extract the core of `_mt_resolve_scope_source` (`tasks_move_task.py:1250-1264`) into
  `resolve_scope_source(repo_root, *, filter_groups_override=None, composite_routing_override=None)`. For
  now it constructs `GateCoverageScopeSource(repo_root, filter_groups_override=…,
  composite_routing_override=…)` — T010 adds the selection branch. Keep it dependency-light; no import
  back into `tasks_move_task`.
- **Red-first**: add a `test_scope_source.py` test asserting `resolve_scope_source(repo_root)` returns a
  `GateCoverageScopeSource` for a pytest/spec-kitty-shaped repo, and threads the override params.
- **Notes**: WP04 will rewrite the `tasks_move_task.py` wrapper to call this; do not touch that file here.

### Subtask T007 – Source-owned `parse_mode` + `scope_source_identity` single-source helper

- **Purpose**: The ONE authority for a source's parse-mode, and the ONE function computing the `source
  class + parse-mode` token (NFR-005, FR-009). **Anti-duplication non-negotiable (post-plan squad paula
  GAP)**: this mission RETIRES a duplicated decision — it must NOT ship a new one. Do **NOT** re-inspect
  `raw` inside `scope_source_identity`; the parse-mode decision already lives inside each source's
  `parse_results`, and re-deriving it in a second place re-creates the exact lock-step-drift pattern
  (present divergence: `GateCoverageScopeSource.parse_results` `:413-427` is junit-only — a *missing*
  artifact still yields a junit-shaped synthetic failure — so a uniform `raw` re-inspection would
  mislabel its no-artifact case as `text`/`none`).
- **File**: `scope_source.py`.
- **Steps**:
  1. Make parse-mode a **source-owned single authority**: add `parse_mode(self, raw) -> str` to each
     source (and, so structural implementers are covered, to the `ScopeSource` surface or a small shared
     default). `GateCoverageScopeSource.parse_mode` → always `"junit_xml"` (matches its junit-only
     `parse_results`, including the no-artifact synthetic case). `DeclaredCommandScopeSource.parse_mode`
     → the three-way decision it already makes at `:527-540` (`junit_xml` / `text` / `none`).
  2. **Dispatch `parse_results` through `parse_mode`** so the branch condition has ONE owner per source
     (behavior-preserving — the WP01 golden guards `GateCoverageScopeSource`; keep `DeclaredCommandScopeSource`
     byte-identical).
  3. `scope_source_identity(scope_source, raw) -> str` returns `f"{type(scope_source).__name__}/
     {scope_source.parse_mode(raw)}"` — it NEVER re-inspects `raw` itself. The command is deliberately
     absent from the token.
- **Red-first**: unit tests pinning `parse_mode` (hence the token) for `GateCoverageScopeSource` (JUnit
  present AND absent → `junit_xml` both) and `DeclaredCommandScopeSource` (worktree-relative JUnit →
  `junit_xml`; FAIL-text → `text`; garbage non-zero → `none`); plus a test proving `parse_results` and
  `scope_source_identity` agree on the mode for the same `raw` (one-authority guard).
- **Notes**: Keep it pure/deterministic — WP03 sets the token into `BaselineTestResult.source_identity`,
  WP04 reads it at diff time. `[P]` — independent of T006.

### Subtask T008 – Two independent predicates + distinct `ClassVar` marker

- **Purpose**: Un-weld the single `isinstance` decision into policy vs capability (FR-005).
- **File**: `scope_source.py`.
- **Steps**: Add `exposes_scope_breakdown(source) -> bool` (backs `isinstance(source,
  ScopeBreakdownSource)`) and `empty_scope_is_coverage_gap(source) -> bool` (backs `getattr(source,
  "treats_empty_scope_as_coverage_gap", False)`). Add the `ClassVar` marker to the mixin in T009 (so
  `GateCoverageScopeSource` inherits `True`); `DeclaredCommandScopeSource` never sets it → `False`.
- **Red-first**: a `test_scope_source.py` test with a **synthetic** source setting the `ClassVar` `True`
  without `scope_breakdown` (policy without capability) AND one implementing `scope_breakdown` with the
  marker `False` (capability without policy) — each predicate returns the declared value independently.
- **Notes**: `[P]` — independent of T006/T007. The call-sites (`pre_review_gate.py:881,:1013`) are swapped
  by WP04; here you only DEFINE the predicates.

### Subtask T009 – `ScopeBreakdownMixin` + `GateCoverageScopeSource` inheritance

- **Purpose**: `file_to_scope` as a default projection so a breakdown-capable source implements one method
  (FR-006).
- **File**: `scope_source.py`.
- **Steps**: Add `class ScopeBreakdownMixin(abc.ABC)` with `treats_empty_scope_as_coverage_gap:
  ClassVar[bool] = True`, `@abc.abstractmethod def scope_breakdown(self, path) -> FileScopeBreakdown`, and
  `def file_to_scope(self, path) -> tuple[str, ...]: return self.scope_breakdown(path).test_targets`.
  Make `GateCoverageScopeSource` inherit it; DELETE its hand-written `file_to_scope` (`:355-362`); keep
  `scope_breakdown` (`:364-411`). Do NOT make `DeclaredCommandScopeSource` inherit it.
- **Behavior-preservation gate**: after this change, replay the WP01 golden —
  `PYTHONPATH=$(pwd)/src pytest tests/review/test_transition_gate_parity.py -q` MUST stay green. If it
  breaks, the projection is not byte-identical to the deleted `file_to_scope` — fix the mixin, not the
  golden.
- **Notes**: name is `ScopeBreakdownMixin` (post-plan rename from `BreakdownScopeSource`, which was too
  close to the `ScopeBreakdownSource` Protocol).

### Subtask T010 – Config-driven selection (FR-014) + stale comment/doc fix

- **Purpose**: Make SC-001 real — a non-pytest consumer runs baseline+head through ONE authority.
- **Files**: `scope_source.py`, `docs/development/review-gates.md`.
- **Steps**: In `resolve_scope_source`, branch: if `review.test_command` is present (read the
  `baseline._get_test_command` config surface, `baseline.py:124-148`) → construct
  `DeclaredCommandScopeSource`; else → `GateCoverageScopeSource`. Fix the now-stale `scope_source.py:51-55`
  comment ("selection wiring lands with #2873" — it lands HERE) and the `review-gates.md:174` single
  command-authority line.
- **Red-first**: two tests — (a) a config with a non-pytest `review.test_command` →
  `DeclaredCommandScopeSource`; (b) spec-kitty's config (no `review.test_command`) →
  `GateCoverageScopeSource`. The second guards against silently re-routing spec-kitty itself.
- **Notes**: keep `_capture_baseline_via_config` reachable via the portable source (do not delete it).

### Subtask T011 – Migrate the intent-encoding test (FR-007)

- **Purpose**: Pin "membership ⇒ empty-is-gap" onto the two predicates, not the raw `isinstance`.
- **File**: `tests/review/test_scope_source.py`.
- **Steps**: Repoint the test at `test_scope_source.py:121-128` (the `isinstance`-membership intent test)
  onto `empty_scope_is_coverage_gap` / `exposes_scope_breakdown`, including the synthetic one-not-the-other
  source (US3 AS3). Also repoint any `derive_test_scope`-oracle assertions in THIS file onto
  `GateCoverageScopeSource` / `_scope_result_from_source` (FR-004b) — but do NOT touch the oracle tests in
  `test_pre_review_gate_engine.py` (WP05 owns that file).
- **Notes**: the migrated test must FAIL against the old `isinstance`-only path and pass only post-T008.

### Subtask T012 – NFR-005 dual-root equivalence + structural same-helper assertion

- **Purpose**: Prove the factory yields command-equivalent sources under BOTH real call-site roots, and
  that capture+diff reference the SAME identity helper (M-nfr5r / M-nfr5s).
- **File**: `tests/review/test_scope_source.py`.
- **Steps**:
  1. Assert `resolve_scope_source(main_repo_root).test_command() == resolve_scope_source(gate_repo_root)
     .test_command()` under two DISTINCT roots (mirroring baseline's `main_repo_root` vs head's
     `gate_repo_root`), plus equal parse-mode/identity — so a `repo_root`-driven `test_command()`
     divergence is caught.
  2. A **structural** assertion that the symbol WP03's baseline capture and WP04's head diff both call is
     the single `scope_source.scope_source_identity` (e.g. assert the qualified name / identity so the
     split cannot silently re-open).
- **Notes**: `source_identity` EXCLUDES the command by design — state this in the test docstring; NFR-005
  carries command equality via T012.1, not via the identity token.

## Test Strategy

- **ATDD red-first**: author each subtask's test to fail against the not-yet-written code, then implement.
- **Run**:
  ```bash
  PYTHONPATH=$(pwd)/src PWHEADLESS=1 pytest tests/review/test_scope_source.py tests/review/test_transition_gate_parity.py -q
  ```
- **Quality**: `ruff check src/specify_cli/review/scope_source.py`; `mypy --strict
  src/specify_cli/review/scope_source.py`; ≥90% new-code coverage; complexity ≤15 (extract helpers for
  the selection + identity derivation).
- **Named guards**: predicate independence (synthetic one-not-other); selection routes spec-kitty →
  `GateCoverageScopeSource`; dual-root command equality; mixin refactor keeps the WP01 golden green.

## Risks & Mitigations

- **carla-2 (both predicates one signal)**: distinct `ClassVar` marker; synthetic one-not-other test.
- **Selection re-routes spec-kitty**: explicit `GateCoverageScopeSource` branch test for no-`review.test_command`.
- **Import cycle**: factory takes seams as params; never imports `tasks_move_task`.
- **Mixin drift**: replay the WP01 golden after T009 — behavior must be byte-identical.

## Review Guidance

- Factory config-selective, cycle-free, seams parameterized; spec-kitty routes to `GateCoverageScopeSource`.
- Predicates back onto DISTINCT signals (proven by the synthetic one-not-other test).
- `GateCoverageScopeSource` implements exactly `scope_breakdown`; `DeclaredCommandScopeSource` has neither.
- `scope_source_identity` is the single token producer; parse-mode mirrors `parse_results`' branch.
- WP01 golden still green; stale comment + `review-gates.md:174` fixed; zero suppressions.

## Activity Log

> **CRITICAL**: chronological order, append at the END. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`.

- 2026-07-23T10:19:53Z – system – Prompt created.

### Updating Status

`spec-kitty agent tasks move-task WP02 --to <status>`.
