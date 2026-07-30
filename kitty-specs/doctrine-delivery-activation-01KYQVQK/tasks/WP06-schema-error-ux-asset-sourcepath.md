---
work_package_id: WP06
title: DRGGraphSchemaError UX + asset source-path
dependencies: []
requirement_refs:
- FR-011
planning_base_branch: feat/doctrine-delivery-activation
merge_target_branch: feat/doctrine-delivery-activation
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-delivery-activation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-delivery-activation unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-doctrine-delivery-activation-01KYQVQK
base_commit: d87b6bb9844e38be4d1cd6d94f3e2568e125074a
created_at: '2026-07-30T05:26:39.168233+00:00'
subtasks:
- T024
- T025
- T026
phase: Phase 3 - DRGGraphSchemaError UX + asset hygiene (Lane C, parallel)
history:
- at: '2026-07-29T22:08:45Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/assets/
create_intent:
- tests/doctrine/test_post_validate_success_hook.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/doctrine/pack_validator.py
- src/doctrine/base.py
- src/doctrine/assets/repository.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP06 – DRGGraphSchemaError UX + asset source-path

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave
according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work
package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or
  the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation
  TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you
  changed.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or
in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

- Surface `DRGGraphSchemaError` as a structured `ValidationIssue` during `doctrine validate` instead of an
  uncaught traceback, at both consumer sites in `pack_validator.py`.
- Fix the `AssetRepository` `_source_paths` split-brain: a manifest that fails validation must NOT get a
  recorded `source_path`. Introduce a base-level `_post_validate` success-path hook so the fix lives at the
  right ownership boundary (shared by every `BaseDoctrineRepository` subclass, not a one-off patch).
- Audit and, if needed, fix the documented "twin" in `AgentProfileRepository` — with a mandatory regression
  test either way (see T026; the outcome may be "already correct," which is itself a valid deliverable when
  proven, not assumed).
- Success = FR-011 acceptance: a pack with a stray top-level graph key produces a structured issue (not a
  traceback); a project-layer asset that fails validation has `source_path(id)` absent, not stale.
- **Ticket closure**: this WP fully covers #3062 — its PR carries `Closes #3062` (both halves land here,
  unlike #3075 which is split across WP04+WP05 and only the second-lander carries the closing keyword).

## Context & Constraints

- Plan: [plan.md](../plan.md) IC-07 · Ledger: [pre-planning-ledger.md](../pre-planning-ledger.md) Scout 2
  "Item 2 — DRGGraphSchemaError UX (#3062)" + POST-PLAN squad R-M8/D-M8 ("`_post_validate` both load
  paths").
- **`DRGGraphSchemaError`** (`src/doctrine/drg/models.py:460`) is raised by `load_graph_document`
  (`models.py:505-520`, specifically at line 519) when a graph document declares a top-level key `DRGGraph`
  does not define. It is **deliberately NOT** a subclass of `doctrine.drg.loader.DRGLoadError`
  (`models.py:468-471`, by design, NFR-006): several call sites `except DRGLoadError` and degrade to an
  empty graph, and a stray top-level key must fail *closed* past those handlers, not be silently swallowed
  — the exact silence this WP's UX fix must not accidentally reintroduce elsewhere.
- `doctrine.drg.loader.load_graph` (`loader.py:50`) calls `load_graph_document` internally (`loader.py:74`),
  so `DRGGraphSchemaError` can propagate from any `load_graph(...)` call site.
- **Two uncaught consumer sites in `pack_validator.py`** (function `_validate_drg`, def at line 478, and
  function `_collect_fragment_edge_intent`, def at line 951) — both currently `except DRGLoadError` only:
  - `_validate_drg`'s fragment loop (lines 523-536): `except DRGLoadError as exc:` (line 526) builds a
    `ValidationIssue(severity="error", artifact_type="drg", artifact_id=None, file=str(fragment),
    message=f"failed to load DRG fragment: {exc}")` (lines 527-535). This is the **structured-issue** site —
    widen its except clause.
  - `_collect_fragment_edge_intent`'s fragment loop (lines 973-977): `except DRGLoadError: continue` — this
    function is explicitly **best-effort by design** (its own docstring, lines 954-962: "unparseable
    fragments are skipped (`_validate_drg` surfaces those load errors)"). Do NOT add a `ValidationIssue`
    here — `_validate_drg` already reports the same fragment independently. Just widen the except so this
    pass doesn't crash.
  - `ValidationIssue` (`pack_validator.py:92-119`, a `@dataclass`) fields: `severity`, `artifact_type`,
    `artifact_id`, `file`, `message`, `category` (optional). The `category` docstring already enumerates
    `"schema_invalid"` as a valid value (line 99) — use it for this issue.
- **`AssetRepository` split-brain** (`src/doctrine/assets/repository.py:121-133`, `_pre_validate`): records
  `self._source_paths[asset_id] = yaml_file` from raw YAML `data` BEFORE `model_validate` runs. The base
  class calls `_pre_validate` at `base.py:174` (built-in) / `base.py:248` (overlay) — both **before** the
  corresponding `model_validate`/`_merge` call at `base.py:175` / `:258` / `:270`. Result: a manifest that
  fails validation still gets a `_source_paths` entry, so `source_path(id)` returns a path while `get(id)`
  returns `None` — a split-brain a caller can observe.
- **`BaseDoctrineRepository`** (`src/doctrine/base.py`) load flow, precisely — THREE places an item enters
  `self._items` / the built-in dict, all currently paired only with the pre-validate hook:
  1. `_load_built_in_items` (lines 164-186): `_pre_validate` at line 174, `model_validate` at line 175,
     write to `built_in[...]` at line 179 (inside the same `try`).
  2. `_apply_overlay_layer` (lines 213-287), MERGE branch (`item_id in built_in`): `_pre_validate` at line
     248, `self._merge(...)` at line 258 (raises inside `_merge`'s own `model_validate` on failure), write to
     `self._items[item_id]` at line 265 — gated by `if self._include_item(merged):` (line 259).
  3. `_apply_overlay_layer`, NEW-ITEM branch (`else`): `model_validate` at line 270, write to
     `self._items[key]` at line 278 — gated by `if self._include_item(obj):` (line 271).
  A `ValidationError`/`YAMLError`/`OSError` anywhere in the `try` is caught at line 180 (built-in) / line 282
  (overlay), which is AFTER `_pre_validate` already ran — this is the ordering bug.
- **The fix**: add a symmetric `_post_validate(obj, yaml_file)` hook fired ONLY on success, at all THREE
  call sites above, gated by the SAME `_include_item` condition that gates the actual `self._items` write
  (so a scope-filtered-but-valid item's recording semantics don't change unexpectedly). Move
  `AssetRepository`'s `_source_paths` write from `_pre_validate` to `_post_validate`.
- **AgentProfileRepository "twin" — read this before touching that file.** The `AssetRepository.__init__`
  docstring (repository.py, near line 94) claims its `_source_paths` bookkeeping "mirrors
  AgentProfileRepository." Grounding check performed during planning: `AgentProfileRepository` does **NOT**
  subclass `BaseDoctrineRepository` — it is a bespoke, standalone class (`src/doctrine/agent_profiles/
  repository.py:223`) with its OWN unified loader `_load_layer` (lines 370-496, explicitly collapsing what
  used to be three duplicated per-layer loops, per its own docstring "R-011-B"), used for built-in, org, AND
  project layers alike (called at lines 343/353/362). In `_load_layer`, `self._source_paths[profile.profile_id]
  = yaml_file` is written at **line 493** — AFTER the `try/except ValidationError` block (lines 463-479,
  which `continue`s past line 493 on a validation failure) and AFTER the `applies_to_languages_match` scope
  gate (lines 481-482). **This means the ordering bug the ledger describes does not currently reproduce
  here** — see T026 for the mandatory verification-or-fix protocol. `src/doctrine/agent_profiles/
  repository.py` is **NOT** in this WP's `owned_files` (WP01 owns that file as the sole consumer of
  `profile_channel_procedure_ids()` on the core delivery lane) — any edit there is a **documented
  out-of-map exception**, scoped to the single `_source_paths` write if a real bug is found, with rationale
  recorded per repo ownership-boundary discipline (memory: rationale-backed leeway outside `owned_files` is
  fine; unexplained silent edits are not).

## Branch Strategy

- **Strategy**: Planning artifacts generated on feat/doctrine-delivery-activation; during implement this WP
  may branch from a dependency-specific base but merges back into feat/doctrine-delivery-activation unless
  the human redirects.
- **Planning base branch**: feat/doctrine-delivery-activation
- **Merge target branch**: feat/doctrine-delivery-activation

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T024 – `except DRGGraphSchemaError` → `ValidationIssue` at both pack_validator sites

- **Purpose**: Close the traceback-vs-structured-issue gap. `DRGGraphSchemaError` is deliberately not a
  `DRGLoadError`, so both existing `except DRGLoadError` catches let it propagate uncaught.
- **Steps**:
  1. Write the red-first test FIRST (see Notes) so the current traceback behavior is captured as evidence.
  2. In `_validate_drg` (line 478), the fragment loop's `except DRGLoadError as exc:` (line 526): add a
     preceding `except DRGGraphSchemaError as exc:` clause (or widen to a tuple and branch on
     `isinstance`) that builds `ValidationIssue(severity="error", artifact_type="drg", artifact_id=None,
     file=str(fragment), message=str(exc), category="schema_invalid")` — mirroring the existing
     `DRGLoadError` branch's shape but with `category="schema_invalid"` set explicitly (the existing
     `DRGLoadError` branch has no category; keep that branch as-is, only the new `DRGGraphSchemaError`
     branch gets the category per the contract's exact wording).
  3. Import `DRGGraphSchemaError` from `doctrine.drg.models` (NOT `doctrine.drg.loader` — it lives in
     `models.py`) inside the same `try: ... except ModuleNotFoundError:` guard block that already imports
     `DRGLoadError`/`load_built_in_graph`/`load_graph` (lines 498-501), so the function keeps degrading
     gracefully when the doctrine package is absent from a test environment.
  4. In `_collect_fragment_edge_intent` (line 951), widen `except DRGLoadError:` (line 976) to `except
     (DRGLoadError, DRGGraphSchemaError):` — do NOT add a `ValidationIssue` here (see Context: this
     function is best-effort by design, `_validate_drg` already reports the same fragment). Add the same
     import inside this function's own `try: from doctrine.drg.loader import DRGLoadError, load_graph`
     guard (lines 966-969).
- **Files**: `src/specify_cli/doctrine/pack_validator.py`.
- **Parallel?**: Yes (independent of every other WP).
- **Notes**: Red-first — construct a pack fixture whose `*.graph.yaml` fragment declares a stray top-level
  key (any key `DRGGraph` doesn't define — triggers `_unknown_top_level_keys` in `load_graph_document`,
  `models.py:486-502`) and assert `validate_pack(...)`'s returned issues contain a `ValidationIssue` with
  `category == "schema_invalid"` instead of the call raising. Extend `tests/specify_cli/doctrine/
  test_pack_validator.py` (existing file; grounding confirmed it currently has no DRG-schema-error
  coverage).

### Subtask T025 – Base `_post_validate` success-path hook (both load paths) + move `AssetRepository`

- **Purpose**: Close the split-brain at the correct ownership boundary — a shared base hook, not a one-off
  patch — so any future `BaseDoctrineRepository` subclass gets the correct semantics by construction.
- **Steps**:
  1. In `base.py`, add `def _post_validate(self, obj: T, yaml_file: Path) -> None:` directly after the
     existing `_pre_validate` (lines 130-134, in the "Virtual hooks" section) with a matching docstring
     ("Called after a successful `model_validate`/merge. Default: no-op.") so the two hooks read as a
     visually paired pre/post contract.
  2. Call `self._post_validate(obj, yaml_file)` at all THREE success points identified in Context:
     - `_load_built_in_items`: right after line 175's `model_validate` succeeds, alongside the write at
       line 179.
     - `_apply_overlay_layer` MERGE branch: right after line 258's `merged = self._merge(...)` succeeds,
       INSIDE the same `if self._include_item(merged):` block that performs the write at line 265 (not
       before it — a scope-filtered item must not get `_post_validate` fired if it never enters `_items`).
     - `_apply_overlay_layer` NEW-ITEM branch: right after line 270's `model_validate` succeeds, INSIDE the
       `if self._include_item(obj):` block, alongside the write at line 278.
  3. In `assets/repository.py`: DELETE the `_pre_validate` override (lines 121-133). ADD a `_post_validate(
     self, obj: AssetManifest, yaml_file: Path) -> None:` override with the SAME recording logic, keyed off
     `obj.id` (a validated `AssetManifest` instance) rather than `data.get("id")` — simpler than the
     original since no `isinstance(data, dict)` guard is needed at this point. Update the `__init__`
     docstring comment (near line 94, "the `_pre_validate` hook records into it") to reference
     `_post_validate`.
  4. Confirm the hook's default no-op means every OTHER `BaseDoctrineRepository` subclass (directives,
     tactics, styleguides, toolguides, paradigms, ...) is behaviorally unaffected.
- **Files**: `src/doctrine/base.py`, `src/doctrine/assets/repository.py`.
- **Parallel?**: Yes.
- **Notes**: Red-first — create `tests/doctrine/test_post_validate_success_hook.py` (new file) proving
  GENERICALLY, via a minimal `BaseDoctrineRepository` subclass that overrides `_post_validate` with a
  recording spy, that the hook fires exactly once per successfully-validated item across all three call
  sites and NEVER fires for a validation failure (a malformed YAML file caught by the existing `except
  (YAMLError, ValidationError, OSError)` blocks at line 180 / line 282). Then extend `tests/doctrine/
  assets/test_repository.py` with the `AssetRepository`-specific regression: a project-layer
  `*.asset.yaml` manifest that fails `AssetManifest.model_validate` (e.g. a required field omitted) →
  `repo.source_path(id)` raises `AssetNotFoundError` (absent), not a stale path. The existing tests in that
  file (`test_source_path_tracks_the_declaring_manifest`, `test_source_path_missing_id_raises_typed_error`)
  are the pattern to follow.

### Subtask T026 – `AgentProfileRepository` twin: verify-then-fix, plus regression (documented out-of-map)

- **Purpose**: Close the twin half of D-M8 with EVIDENCE, not assumption — the pre-planning ledger flags a
  claimed mirror bug; this planning pass's grounding check (see Context) found the claim does not currently
  reproduce. Resolve this with a test, honestly reported either way.
- **Steps**:
  1. Re-verify the grounding check yourself before writing any fix: read `_load_layer` in
     `src/doctrine/agent_profiles/repository.py` (lines 370-496) and confirm (or refute) that
     `self._source_paths[profile.profile_id] = yaml_file` (line 493) is reached only AFTER the
     `try/except ValidationError` (lines 463-479) that would otherwise `continue` past it on a validation
     failure. This is the same function for built-in, org, and project layers (R-011-B collapse) — so
     "check the overlay path" and "check the built-in path" are the SAME code read here.
  2. Write the regression test regardless of what step 1 shows: a project-layer agent-profile YAML that
     fails `AgentProfile.model_validate` (or trips the `InlineReferenceRejectedError` / missing-`profile-id`
     skip paths already at lines 424-461) → assert `repo.get_source_path(profile_id)` returns `None`.
     Extend `tests/doctrine/test_profile_repository.py` (existing file — add alongside the existing
     `TestAgentProfileRepositoryBoundaries` / `TestAgentProfileRepositoryExceptions` classes, following
     their existing `AgentProfileRepository(built_in_dir=..., project_dir=...)` construction pattern).
  3. If the test is RED: the grounding check missed something — fix the exact call site the same way as
     T025 (move whatever premature `_source_paths` write is actually firing to after validation succeeds),
     and record the corrected file:line in the Activity Log, explicitly correcting this prompt's grounding
     claim.
  4. If the test is GREEN immediately: do NOT force a code change to manufacture a diff. Record in the
     Activity Log the exact evidence (file:line + the control-flow read) proving `_load_layer` already gates
     `_source_paths` on validation success, and note that the ledger's "twin bug" claim does not hold under
     this pass's inspection. This is itself the deliverable — an honest verification backed by a passing
     regression test, not a fabricated fix (repo discipline: judge the code by what a real red/green test
     shows, never retry-to-green, never invent a fix for a bug that isn't there).
  5. Either outcome: this is a **documented out-of-map edit** (or verification) — `src/doctrine/
     agent_profiles/repository.py` is not in `owned_files`. Record the rationale (a comment or the Activity
     Log entry) explaining why this WP touched/verified a file it doesn't own, and coordinate with WP01's
     implementer if both WPs are in flight concurrently to avoid a silent merge conflict on this file.
- **Files**: `src/doctrine/agent_profiles/repository.py` (out-of-map, conditional on step 3), `tests/
  doctrine/test_profile_repository.py` (extend).
- **Parallel?**: Yes, but coordinate the out-of-map file touch with WP01 (see Notes).
- **Notes**: Because `AgentProfileRepository` does not subclass `BaseDoctrineRepository`, T025's
  `_post_validate` hook does not apply here directly — there is no shared base to hook into. If step 3 finds
  a real bug, fix it as a local ordering fix inside `_load_layer`; do not retrofit `AgentProfileRepository`
  onto `BaseDoctrineRepository` (that would be a much larger, out-of-scope refactor this WP must not attempt).

## Definition of Done

```bash
uv run pytest tests/specify_cli/doctrine/test_pack_validator.py -q -k "schema"
uv run pytest tests/doctrine/test_post_validate_success_hook.py -q
uv run pytest tests/doctrine/assets/test_repository.py -q -k "source_path"
uv run pytest tests/doctrine/test_profile_repository.py -q -k "source_path"
uv run pytest tests/doctrine/test_base_org_layer.py -q
uv run ruff check src/specify_cli/doctrine/pack_validator.py src/doctrine/base.py src/doctrine/assets/repository.py
uv run mypy --strict src/doctrine/base.py src/doctrine/assets/repository.py
uv run spec-kitty doctrine validate
```

Do NOT run the full `tests/architectural/` suite locally — targeted node-ids only (repo policy; CI owns the
full sweep).

## Risks & Mitigations

- `_post_validate` firing at the wrong point in the merge branch could double-fire or fire for a
  scope-filtered item — gate the call inside the SAME `if self._include_item(...)` block that gates the
  actual `self._items[...] = ...` write, never before it.
- Base-hook must not change ANY other repo's success-path behavior (default no-op) — the DoD's
  `test_base_org_layer.py` run is the regression backstop for that.
- T026's grounding check may contradict the pre-planning ledger — resolve strictly by evidence (a red/green
  test), never by assumption; do not silently "fix" code that isn't broken, and do not silently skip the
  twin check either — the regression test is mandatory either way.
- `pack_validator.py`'s two catch sites have different jobs (one surfaces, one best-effort skips) — do not
  add a `ValidationIssue` to the best-effort site; that would double-report the same fragment error once
  `_validate_drg`'s own pass already reports it.

## Reviewer Guidance

- Confirm `DRGGraphSchemaError` is imported from `doctrine.drg.models`, not `doctrine.drg.loader` (it lives
  in `models.py`; `loader.py` only imports/propagates it via `load_graph`).
- Confirm `_post_validate` fires at all THREE `base.py` call sites (built-in + overlay-merge + overlay-new),
  not just one — a partial wiring would fix only the built-in path and leave the more common overlay/project
  path split-brained.
- Confirm `test_base_org_layer.py` and every other `BaseDoctrineRepository` subclass's existing test suite
  is green and unmodified — the hook must be additive-only.
- For T026, read the Activity Log entry: it must state either the real bug found-and-fixed with file:line,
  or an explicit "verified already correct" with the control-flow evidence — an unexplained absence of the
  regression test is not acceptable either way.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

### How to Add Activity Log Entries

**When adding an entry**:

1. Scroll to the bottom of this Activity Log section
2. **APPEND the new entry at the END** (do NOT prepend or insert in middle)
3. Use exact format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`
4. Timestamp MUST be current time in UTC (check with `date -u "+%Y-%m-%dT%H:%M:%SZ"`)
5. Agent ID should identify who made the change (claude-sonnet-4-5, codex, etc.)

**Format**:

```
- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>
```

**Why this matters**: The acceptance system reads the LAST activity log entry as the current state. If
entries are out of order, acceptance will fail even when the work is complete.

**Initial entry**:

- 2026-07-29T22:08:45Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP06 --to <status>` to
change WP status.

### Optional Phase Subdirectories

For large features, organize prompts under `tasks/` to keep bundles grouped while maintaining lexical
ordering.
