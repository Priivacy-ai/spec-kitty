---
work_package_id: WP04
title: context.py extraction + ArtifactRepository Protocol typing
dependencies:
- WP01
requirement_refs:
- FR-010
- FR-012
- NFR-001
- NFR-005
planning_base_branch: feat/doctrine-delivery-activation
merge_target_branch: feat/doctrine-delivery-activation
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-delivery-activation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-delivery-activation unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
phase: Phase 2 - context.py extraction + Protocol typing
history:
- at: '2026-07-29T22:04:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/charter/context_renderers/
create_intent:
- src/charter/context_renderers/reference_pointers.py
- src/charter/context_renderers/delivery_table.py
- src/charter/repository_protocol.py
execution_mode: code_change
model: ''
owned_files:
- src/charter/context.py
- src/charter/context_renderers/reference_pointers.py
- src/charter/context_renderers/delivery_table.py
- src/charter/repository_protocol.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP04 – context.py extraction + ArtifactRepository Protocol typing

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and
behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for
this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via
  `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your
  implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what
  you changed.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

`src/charter/context.py` is a 3528-line module. This WP does two behaviour-preserving things to it,
both sliced from larger backlog tickets so they land as a bounded, reviewable unit:

1. **Extract two independent helper groups** to `context_renderers/` sibling modules — the
   reference-pointer helpers (their own module-global cache in tow) and the delivery-table
   helpers (with a re-export shim so their three external test importers keep working) — following
   the existing sibling pattern already used by `authority_paths.py`, `fetch_stanza.py`,
   `section_bodies.py`, `token_budget.py`, and `profile_sections.py`.
2. **Replace the `object`-typed repository parameters** at all 12 `# type: ignore[attr-defined]`
   sites (across `context.py` and `progressive_disclosure.py`) with a new `ArtifactRepository`
   Protocol, net-removing all 12 ignores.

- **SC-005/NFR-001 (spec.md)**: every `context.py` consumer test stays green after extraction;
  rendered payloads are byte-identical for exercised consumers (0 regressions).
- **SC-006/NFR-005**: `mypy --strict` passes with the 12 `# type: ignore[attr-defined]` sites
  removed and zero new ignores added anywhere in the touched files.
- This WP `Refs #2532` (a bounded slice of the full context.py de-god effort — NOT `Closes`, per
  D8/tasks.md) and is one half of `#3075`'s typing debt (its closure also depends on WP05's writer
  half landing — C-007; do not claim #3075 closed from this WP alone).

## Context & Constraints

- **Grounding documents**: `kitty-specs/doctrine-delivery-activation-01KYQVQK/plan.md` §IC-08
  (extraction) and §IC-06b (Protocol typing) — note these were originally one concern (IC-06) that
  the post-plan squad **split** (D12/R-B3) specifically because the typing edits land inside
  WP01's and this WP's own extraction hunks and are therefore NOT parallel with the rest of the
  mission; `pre-planning-ledger.md` Scout 2 "Item 3" (extraction) and "Protocol typing debt"
  paragraph, plus D8/D12/R-M7; `spec.md` FR-012, FR-010(typing half), NFR-001, NFR-005;
  `tasks.md` WP04 section.
- **Hard dependency ordering (D12, critical)**: this WP depends on **WP01 only**, but the
  dependency is real and sequential, not advisory. WP01 rewrites the exact cadence this WP
  extracts and the exact ignore sites this WP retypes:
  - The delivery-table extraction and the requires-closure render cadence both touch the region
    around `context.py:1202-1253` (`_render_action_doctrine_lines`) that WP01 is expected to shape
    into its final form (per R-M7, WP01's profile-channel `when`-projection lands in a
    `progressive_disclosure` sibling, NOT inline in `context.py` — but the cadence call sites in
    `context.py` still change).
  - The Protocol-typing ignore sites at `context.py:3515-3518` sit **inside** the block WP01
    modifies at `context.py:3513-3525` (`_ActionDoctrineBundle` assembly / bundle cadence).
  - **Do not start this WP against a base that predates WP01's merge** — extracting or retyping
    code that WP01 is about to change means redoing the work, or worse, silently reverting WP01's
    changes. Confirm your worktree base includes WP01 before touching either file.
  - This ordering is a deliberate, documented **inversion of tidy-first** (normally you'd extract
    before adding new logic) — justified here because the code shape this WP extracts doesn't
    exist in its final form until WP01 lands (ledger IC-08 risk note).
- **Two independent extraction slices with different risk profiles**:
  - **Reference-pointer slice** (`context.py:1702-1900` roughly —
    `_filter_references_for_action`, `_reference_source_index`, `_resolve_reference_source`,
    `_distribute_references_across_kinds`, `_select_reference_pointers`, plus the module-global
    `_REFERENCE_SOURCE_INDEX_CACHE` at `context.py:1765`) has **zero external consumers** — its
    only call site is `_select_reference_pointers(...)` at `context.py:1350`, inside `context.py`
    itself. This is the **lowest-risk** slice; the cache MUST move with the functions (it's keyed
    by `Path` and populated/read only by these functions — moving the functions without the cache
    silently breaks the memoization, not correctness, but still worth getting right).
  - **Delivery-table slice** (`context.py:728-868` roughly — `_KindDelivery`,
    `_ACTION_BUNDLE_DELIVERY_BY_KIND`, `_kind_delivery`, `action_bundle_bucket`,
    `action_bundle_gate`, `_classify_artifact_urns`) **has three external test importers**:
    `tests/charter/test_action_bundle_delivery.py`, `tests/charter/test_context_display_charter_md.py`,
    and `tests/doctrine/drg/test_unknown_kind_fails_loudly.py` (all confirmed importing these
    symbols from `charter.context` directly — verified in the live tree). You MUST either
    re-export these names from `charter.context` after moving them, or update all three test
    files' import statements in the **same PR** — do not leave a half-moved state where the
    module has moved but nothing still resolves the old import path.
- **Protocol typing scope (WP01/IC-08 boundary, must NOT expand)**: the 12 ignore sites are:
  `context.py:552, 568, 1520, 2526, 2757, 3375, 3515, 3516, 3517, 3518` (10 sites) and
  `progressive_disclosure.py:236, 237` (2 sites — the `repository.get(...)` /
  `repository.get_provenance(...)` calls inside `collect_typed_artifacts`, whose `repository`
  parameter is typed `object` at `progressive_disclosure.py:216`). **The 2
  `progressive_disclosure.py` sites are a documented, deliberate out-of-scope-for-owned_files edit**:
  WP01 owns `progressive_disclosure.py` as a file for the delivery-projection work, so this WP's
  edit there is a narrow, type-only change (swap `object` → `ArtifactRepository` at the parameter
  annotation and drop the two ignore comments) — record this explicitly in your PR description
  and Activity Log as a documented cross-boundary type-only edit, and do **not** list
  `progressive_disclosure.py` in this WP's `owned_files` (it stays WP01's file). Coordinate with
  whoever lands WP01 if there's a conflict.
- **Concrete repos already satisfy the Protocol** (no repo-side changes needed): every concrete
  doctrine repository already implements `get(id) -> T | None` and
  `get_provenance(id) -> str | None` via `BaseDoctrineRepository` (`src/doctrine/base.py:329`).
  This WP only needs to declare the `Protocol` and swap the **parameter/attribute type
  annotations** at the 12 call sites from `object` to the new Protocol — no behavioral change to
  any repository class.
- **Behaviour-preserving is the whole point (NFR-001)**: both the extraction and the retyping must
  produce byte-identical runtime output for every exercised consumer. This is a refactor WP, not a
  feature WP — if a test's expected output needs to change to make this WP pass, that is a signal
  you introduced a regression, not that the test was wrong.

## Branch Strategy

- **Strategy**: Planning artifacts generated on feat/doctrine-delivery-activation; during implement
  this WP may branch from a dependency-specific base but merges back into
  feat/doctrine-delivery-activation unless the human redirects.
- **Planning base branch**: feat/doctrine-delivery-activation
- **Merge target branch**: feat/doctrine-delivery-activation

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.
> Branch from a tip that already includes WP01's merged/landed changes (see Context & Constraints
> above) — this WP is sequenced, not parallel, despite having only one listed dependency.

## Subtasks & Detailed Guidance

### T016 – Extract reference-pointer helpers (+ module cache) to `context_renderers/reference_pointers.py`

- **Purpose**: Move the lowest-risk, zero-external-consumer helper group out of `context.py` into
  its own sibling module, following the existing `context_renderers/` pattern (module docstring
  explaining what section of the resolver's output the module renders, `__all__` declaring the
  public surface, imports scoped to what's needed).
- **Steps**:
  1. Confirm the current line span in your checkout (it may have shifted slightly after WP01
     lands): `_filter_references_for_action`, `_reference_source_index`,
     `_resolve_reference_source`, `_distribute_references_across_kinds`,
     `_select_reference_pointers`, and the module-global `_REFERENCE_SOURCE_INDEX_CACHE`.
  2. Create `src/charter/context_renderers/reference_pointers.py`. Move all five functions and the
     cache dict verbatim (function bodies unchanged — this is a location move, not a rewrite).
     Add a module docstring following the style of `authority_paths.py` (purpose, when it's
     called, any design notes worth preserving from the original `context.py` docstrings/comments).
  3. In `context.py`, replace the moved definitions with an import from the new sibling module
     (`from charter.context_renderers.reference_pointers import _select_reference_pointers` or
     however the single call site at `context.py:1350` needs it — since these are private
     (`_`-prefixed) helpers with a single internal caller, import only what's actually called from
     `context.py`; you do not need to keep the intermediate private helpers importable from
     `context.py` unless something else in the file also calls them — check first).
  4. Confirm no other module imports these private names directly (grep the whole tree, not just
     `tests/`, since they're private and *should* have zero external importers per the ledger —
     verify that claim rather than assuming it).
- **Files**: `src/charter/context.py` (remove ~200 lines), `src/charter/context_renderers/reference_pointers.py` (new).
- **Parallel?**: Sequential with T017 within this WP (both touch `context.py`); can be done before
  or after T017 since the two slices are non-overlapping regions of the file — pick whichever
  order minimizes merge conflicts with your own working copy.
- **Validation**: `uv run pytest tests/charter/ -k "reference" -q` (or the closest existing test
  path covering reference-pointer rendering — identify it during implementation) green;
  `uv run mypy --strict src/charter/context_renderers/reference_pointers.py` clean.
- **Notes**: The cache is the one subtlety here — it MUST move with the functions (not stay behind
  as a `context.py`-level global that the moved functions reach back into). A `context.py` import
  of the new module's cache object for any external reason would be a smell; there shouldn't be one.

### T017 – Extract delivery-table helpers to `context_renderers/delivery_table.py` + re-export shim

- **Purpose**: Move the delivery-table helper group, preserving the three external test import
  paths via either a re-export shim in `charter.context` or same-PR test-import updates (your
  choice — pick whichever keeps the diff smaller and clearer; document which you chose).
- **Steps**:
  1. Confirm the current line span: `_KindDelivery` (NamedTuple), `_ACTION_BUNDLE_DELIVERY_BY_KIND`
     (module-level dict), `_kind_delivery`, `action_bundle_bucket`, `action_bundle_gate`,
     `_classify_artifact_urns`.
  2. Create `src/charter/context_renderers/delivery_table.py`. Move all six symbols verbatim, with
     a module docstring explaining the NodeKind delivery-table concept (the existing docstrings on
     `_KindDelivery` and `_ACTION_BUNDLE_DELIVERY_BY_KIND` already explain the `slot`/`gate`
     semantics — carry that explanation over, don't lose it).
  3. Decide your external-consumer strategy:
     - **Option A (re-export shim)**: in `context.py`, after removing the definitions, add
       `from charter.context_renderers.delivery_table import (action_bundle_bucket,
       action_bundle_gate, _classify_artifact_urns, _KindDelivery, _ACTION_BUNDLE_DELIVERY_BY_KIND,
       _kind_delivery)` (or the subset actually needed at both internal call sites and the external
       test import paths) so `from charter.context import action_bundle_bucket` continues to
       resolve. Simpler for consumers, but keeps `context.py`'s public surface unchanged (arguably
       against the spirit of the extraction).
     - **Option B (update the 3 test files)**: change
       `tests/charter/test_action_bundle_delivery.py`,
       `tests/charter/test_context_display_charter_md.py`, and
       `tests/doctrine/drg/test_unknown_kind_fails_loudly.py` to import from
       `charter.context_renderers.delivery_table` instead of `charter.context`. Cleaner long-term,
       but touches test files outside this WP's `owned_files` list — if you choose this option,
       add those three test files to a note in your PR description explaining the necessary
       cross-file import-path update (small, mechanical, behaviour-preserving).
  4. Whichever option you pick, verify ALL THREE test files still pass without modification to
     their assertions (only import lines may change under Option B).
- **Files**: `src/charter/context.py`, `src/charter/context_renderers/delivery_table.py` (new).
- **Parallel?**: Sequential with T016 within this WP.
- **Validation**:
  `uv run pytest tests/charter/test_action_bundle_delivery.py tests/charter/test_context_display_charter_md.py tests/doctrine/drg/test_unknown_kind_fails_loudly.py -q`
  green under whichever import strategy you chose.
- **Notes**: `bridge_urns` / the requires-closure render cadence (`context.py:145-150, 1090/1129/
  1150, 1202, 1238`) threads through code near this slice — confirm during extraction that you're
  moving the delivery-table helpers only, not accidentally dragging cadence logic that must stay
  in `context.py` (or, symmetrically, leaving a delivery-table helper behind because it looked
  cadence-related). If genuinely ambiguous, prefer leaving borderline logic in `context.py` and
  note the judgment call in the Activity Log for reviewer visibility.

### T018 – Define `ArtifactRepository` Protocol; apply at 12 sites; remove `# type: ignore[attr-defined]`

- **Purpose**: Replace the `object`-typed repository surface with a proper `typing.Protocol` so
  mypy can verify `.get(...)` / `.get_provenance(...)` calls without suppression, net-removing all
  12 existing ignores and adding none.
- **Steps**:
  1. Create `src/charter/repository_protocol.py` with an `ArtifactRepository` Protocol:
     ```python
     from typing import Protocol, TypeVar

     T = TypeVar("T")

     class ArtifactRepository(Protocol[T]):
         def get(self, artifact_id: str) -> T | None: ...
         def get_provenance(self, artifact_id: str) -> str | None: ...
     ```
     (Adjust the generic shape to how the 12 call sites use the return value — some may not need
     genericity if they only call `.get()` for existence checks; check usage before finalizing.
     Keep it minimal — this Protocol exists to remove ignores, not to become a large interface.)
  2. Confirm `BaseDoctrineRepository` (`src/doctrine/base.py:329`) structurally satisfies this
     Protocol already (duck-typing check, no inheritance required for `Protocol` conformance).
  3. At each of the 10 `context.py` sites (`552, 568, 1520, 2526, 2757, 3375, 3515, 3516, 3517,
     3518`) and 2 `progressive_disclosure.py` sites (`236, 237`), change the parameter/attribute
     type from `object` to `ArtifactRepository`, and delete the `# type: ignore[attr-defined]`
     comment.
  4. Re-run `mypy --strict` after each batch (don't wait until all 12 are done) — a structural
     mismatch is real signal: either the Protocol needs a small adjustment or the call site has a
     genuine type discrepancy worth understanding before suppressing it again.
  5. Confirm the final diff removes all 12 `# type: ignore[attr-defined]` occurrences and adds
     none — grep for the string in both files before declaring this subtask done.
- **Files**: `src/charter/repository_protocol.py` (new), `src/charter/context.py` (10 sites),
  `src/charter/progressive_disclosure.py` (2 sites — documented type-only cross-boundary edit,
  not in this WP's `owned_files`).
- **Parallel?**: Do this after T016/T017 land, since the extraction moves code around inside
  `context.py` and you don't want to be retyping call sites that are about to move to a different
  file (some of the 10 `context.py` ignore sites may end up inside `context_renderers/` after
  T016/T017 — verify their final location before applying the Protocol type there).
- **Validation**:
  `uv run mypy --strict src/charter/context.py src/charter/context_renderers/reference_pointers.py src/charter/context_renderers/delivery_table.py src/charter/repository_protocol.py src/charter/progressive_disclosure.py`
  clean, zero `# type: ignore[attr-defined]` remaining across those files.
- **Notes**: If any of the 12 sites turns out, on inspection, to need a materially different
  Protocol shape (e.g. a third method), prefer widening the single `ArtifactRepository` Protocol
  over introducing a second ad-hoc Protocol — the point of this subtask is one clean typed seam,
  not twelve individually-patched call sites.

### T019 – ATDD: context.py consumer tests green (behaviour-preserving) + mypy --strict

- **Purpose**: Prove NFR-001 (0 regressions, byte-identical payloads) and NFR-005 (mypy --strict
  clean, ignores net-removed, none added) hold across the whole WP, not just the individual
  subtasks in isolation.
- **Steps**:
  1. Identify the full set of `context.py` consumer test modules — at minimum the three
     delivery-table importers (`test_action_bundle_delivery.py`, `test_context_display_charter_md.py`,
     `test_unknown_kind_fails_loudly.py`), plus any module exercising `build_charter_context` /
     reference-pointer rendering, plus whatever WP01 added for the profile-channel delivery
     projection (a break here could be a WP01 regression surfacing through this WP's tests —
     investigate before assuming the bug is yours).
  2. Run the full identified set together, not just each file individually, to catch cross-module
     interaction the piecemeal T016-T018 validations might have missed.
  3. If any test's *expected output* needs modification to pass (as opposed to its *import path*,
     which T017 explicitly allows under Option B), treat that as a NFR-001 violation — stop and
     find the actual behavioral drift rather than adjusting the assertion.
  4. Run the full mypy sweep across every file this WP touched (see T018 validation command) one
     final time as the closing check.
- **Files**: no new files — this is a verification subtask over T016-T018's output.
- **Validation**: see Definition of Done below for the exact commands.
- **Notes**: This subtask is where you write the final Activity Log entry summarizing which
  extraction-shim option you chose in T017 and confirming the 12-ignore removal count, since a
  reviewer will look here first for the "is this WP actually done" signal.

## Definition of Done

- [ ] Reference-pointer helpers (`_filter_references_for_action`, `_reference_source_index`,
      `_resolve_reference_source`, `_distribute_references_across_kinds`,
      `_select_reference_pointers`) and their module cache (`_REFERENCE_SOURCE_INDEX_CACHE`) live
      in `src/charter/context_renderers/reference_pointers.py`; `context.py` imports what it needs
      from there.
- [ ] Delivery-table helpers (`_KindDelivery`, `_ACTION_BUNDLE_DELIVERY_BY_KIND`, `_kind_delivery`,
      `action_bundle_bucket`, `action_bundle_gate`, `_classify_artifact_urns`) live in
      `src/charter/context_renderers/delivery_table.py`; the three external test importers
      (`test_action_bundle_delivery.py`, `test_context_display_charter_md.py`,
      `test_unknown_kind_fails_loudly.py`) resolve correctly via a re-export shim or updated
      import paths (documented choice).
- [ ] `src/charter/repository_protocol.py` defines `ArtifactRepository`; all 12
      `# type: ignore[attr-defined]` sites (10 in `context.py`, 2 in `progressive_disclosure.py`)
      are retyped to use it and the ignore comments are removed; zero new ignores added anywhere
      in the touched files.
  - [ ] The `progressive_disclosure.py` edit is explicitly noted in the PR description as a
        documented, type-only, out-of-owned_files cross-boundary edit (WP01 owns that file).
- [ ] `uv run pytest tests/charter/test_action_bundle_delivery.py tests/charter/test_context_display_charter_md.py tests/doctrine/drg/test_unknown_kind_fails_loudly.py -q` — green.
- [ ] `uv run pytest tests/charter/ -k "reference or context_renderers or disclosure" -q` — green
      (adjust the `-k` filter to the actual test modules in your checkout; confirm real coverage).
- [ ] `uv run mypy --strict src/charter/context.py src/charter/context_renderers/reference_pointers.py src/charter/context_renderers/delivery_table.py src/charter/repository_protocol.py src/charter/progressive_disclosure.py` — clean, 0 `# type: ignore[attr-defined]` remaining.
- [ ] `uv run ruff check src/charter/context.py src/charter/context_renderers/ src/charter/repository_protocol.py src/charter/progressive_disclosure.py` — clean.
- [ ] `grep -rn "type: ignore\[attr-defined\]" src/charter/context.py src/charter/progressive_disclosure.py` — zero matches.
- [ ] No test's *expected output/assertions* changed — only import paths, if Option B was chosen
      for the delivery-table shim.
- [ ] **Do NOT run the full `tests/architectural/` or `tests/charter/` suite locally** — targeted
      node-ids above only; CI owns the full sweep.
- [ ] PR description states `Refs #2532` (not `Closes`) and notes this is one half of `#3075`'s
      typing debt — closure of `#3075` depends on WP05's writer-registry half also landing (C-007).

## Risks & Mitigations

- **Sequencing violation**: starting before WP01 lands extracts/retypes code about to change
  underneath you — confirm the worktree base includes WP01's merged changes first.
- **Delivery-table shim breakage**: Option A missing a symbol a test needs, or Option B missing an
  import-line update in one of the three files — mitigate by running all three test files
  explicitly as a named Definition-of-Done step.
- **Cache-left-behind bug**: moving the reference-pointer functions without
  `_REFERENCE_SOURCE_INDEX_CACHE` silently breaks memoization without failing tests that don't
  exercise cache-hit behavior — verify the cache travels with its functions during T016, don't
  trust tests alone to catch it.
- **Protocol scope creep**: widening `ArtifactRepository` beyond what the 12 sites need, or adding
  a second Protocol for an edge case — keep it minimal; prefer widening the one Protocol.
- **Silent boundary violation in `progressive_disclosure.py`**: touching anything beyond the
  narrow `object` → `ArtifactRepository` swap there (e.g. WP01's delivery-projection logic) —
  keep that edit to the smallest possible diff and call it out explicitly.
- **#3075 over-claiming**: describing this WP as closing #3075 alone — state the C-007 dependency
  on WP05 explicitly in the PR description.

## Reviewer Guidance

- Confirm the worktree/branch base actually included WP01's changes before this WP started
  (git log/merge-base), not just that the final diff looks plausible.
- Diff the moved function bodies against their pre-move originals — they should be textually
  identical modulo import adjustments; any logic change inside a "moved" function is a red flag.
- Confirm the delivery-table shim choice (Option A or B) is applied consistently across all three
  test files, not a mix.
- Confirm `_REFERENCE_SOURCE_INDEX_CACHE` is defined in the new sibling module with no stale
  reference left in `context.py`.
- Confirm exactly 12 ignores were removed and 0 added:
  `grep -c "type: ignore\[attr-defined\]"` across `context.py` and `progressive_disclosure.py`
  should read 12 → 0.
- Confirm the `progressive_disclosure.py` edit is a minimal, documented two-line parameter-type
  change plus two ignore-comment removals — nothing else in that file touched.
- Confirm the PR description scopes the ticket claims correctly: `Refs #2532` (not `Closes`), and
  states `#3075` closure depends on WP05 also landing.
- Spot-check `mypy --strict` output yourself rather than trusting the green checkmark alone —
  confirm no new suppression was smuggled in elsewhere in the diff.

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

**Why this matters**: The acceptance system reads the LAST activity log entry as the current
state. If entries are out of order, acceptance will fail even when the work is complete.

**Initial entry**:

- 2026-07-29T22:04:12Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use
`spec-kitty agent tasks move-task WP04 --to <status>` to change WP status.

### Optional Phase Subdirectories

For large features, organize prompts under `tasks/` to keep bundles grouped while maintaining
lexical ordering.
