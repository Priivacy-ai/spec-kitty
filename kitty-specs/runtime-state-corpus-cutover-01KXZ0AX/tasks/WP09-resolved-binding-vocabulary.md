---
work_package_id: WP09
title: Resolved-binding vocabulary + reducer (tidy-first)
dependencies:
- WP08
requirement_refs:
- FR-013
planning_base_branch: feat/runtime-state-corpus-cutover
merge_target_branch: feat/runtime-state-corpus-cutover
branch_strategy: Planning artifacts for this mission were generated on feat/runtime-state-corpus-cutover. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/runtime-state-corpus-cutover unless the human explicitly redirects the landing branch.
subtasks:
- T033
- T034
- T035
- T036
agent: "claude"
shell_pid: "411008"
shell_pid_created_at: "1784572058.59"
history:
- timestamp: '2026-07-20T08:39:02Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/status/
create_intent:
- tests/specify_cli/status/test_resolved_binding_reducer.py
execution_mode: code_change
model: claude-opus-4-8
owned_files:
- src/specify_cli/status/models.py
- src/specify_cli/status/reducer.py
- tests/specify_cli/status/test_resolved_binding_reducer.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

**Before reading any further**, load the `python-pedro` implementer profile via the
`/ad-hoc-profile-load` skill. Adopt its identity, governance scope, boundaries, and the
initialization declaration it prints. Everything below is authored for that profile: TDD-first,
type-safe Python 3.11+, complexity ≤15, zero suppressions. Do not begin editing until the profile
is loaded and its init declaration is on the record.

## Objective

Add the **resolved-binding event vocabulary** (FR-013): the *actual* `role`, `agent_profile`,
`agent_profile_version`, `model`, and `provider` that take a WP, recorded as delta slots and folded
**latest-wins** into the reduced snapshot. This WP is the **vocabulary + reducer half only** — it
extends `WPInnerStateDelta` (`status/models.py`), `_RUNTIME_SLOTS` and `_apply_annotation_delta`
(`status/reducer.py`), and proves latest-wins reduction. The **dispatch→claim linkage** that *sources*
the resolved values (the `--model`/`--profile`/`--invocation-id` threading, the claim-seam emit, and the
backfill re-seed under the `"resolved_binding"` namespace) is **WP10** — out of scope here.

Because IC-08 adds **five** slots, two functions breach the complexity ceiling / triple-enumeration trap
the moment slots are added. So this WP is **tidy-first (D-14)**: (a) collapse `WPInnerStateDelta`'s
`is_empty`/`to_dict`/`from_dict` triple-enumeration into one source of truth **before** adding fields; and
(b) extract `_apply_annotation_delta`'s flat if-chain (cx ~13) into a data-driven replace-slot table
**before** the slots push it >15. Both tidy-firsts are behaviour-preserving refactors landing in this same
WP, each with its own guard test.

Gated by **WP08's C-009 field-authority ADR landing first** — the per-field authority ruling (resolved
`role`/`agent_profile`/`model` → dynamic/event-log; authored → static/frontmatter) is ADR-worthy per the
#2093 precedent and MUST be ratified before this vocabulary lands (`dependencies: ["WP08"]`).

## Context & grounding

- **Plan IC-08 "Vocabulary" bullet** (`plan.md:384-389`): extend `WPInnerStateDelta`
  (`status/models.py` + `to_dict`/`from_dict`/`is_empty`) — **data-drive the field list** (tidy-first) so
  5 new slots don't triple-enumerate; add `role`/`agent_profile`/`agent_profile_version`/`model`/`provider`
  to `_RUNTIME_SLOTS` + `_apply_annotation_delta` — **first extract the flat if-chain into a data-driven
  replace-slot table** (`_apply_annotation_delta` is cx 13 and these slots push it >15).
- **Plan Complexity Tracking / D-14 census** (`research.md:229-248`): "Two functions breach the complexity
  ceiling as a direct result of this mission's edits → tidy-first extract in the SAME WP":
  `status/reducer.py::_apply_annotation_delta` (cx 13 → >15 when IC-08 adds slots) → **data-driven
  replace-slot table**; and (D-14 "Extra consolidation seams", item 3) `WPInnerStateDelta`'s
  **triple-enumeration** (`is_empty`/`to_dict`/`from_dict`) → **data-drive before IC-08 adds fields**.
  The plan's Charter Check / Complexity Tracking is empty *because* these tidy-firsts hold the ceiling — do
  them or the mandate is broken.
- **Spec FR-013** (`spec.md:242`): the actual resolved `role`/`agent_profile`(+`agent_profile_version`)/
  `model`/`provider` are recorded on the event log at each pick-up and **folded latest-wins into the
  snapshot**, because these actuals **shift across the lifecycle**. This WP owns the *fold-latest-wins*
  vocabulary; the *recording source* (never the frontmatter string — C-007) is WP10.
- **Spec C-009** (`spec.md:270`): the per-field authority ADR (addendum to `2026-07-19-1`) is recorded
  **before** the vocabulary lands. That ADR is WP08 — **this WP is gated on it** (`dependencies: WP08`).
- **Spec C-011** (`spec.md:272`): historical authored recommendations never become resolved actuals —
  this is **WP10's** provenance-correction concern, noted here only to bound scope: WP09 does **not**
  touch the backfill.
- **Research D-10** (`research.md:155-177`): resolved runtime identity is event-sourced, authored intent
  stays frontmatter; these fields are **NOT event-sourced today** — `WPInnerStateDelta` carries no
  `profile`/`model`/`role` (net-new vocabulary). **D-14** (`research.md:229-248`): the two forced
  tidy-firsts + the triple-enumeration collapse.
- **Data-model "New event vocabulary (IC-08)"** (`data-model.md:74-78`): `WPInnerStateDelta` gains `role`,
  `agent_profile`, `agent_profile_version`, `model`, `provider`; reducer `_RUNTIME_SLOTS` +
  `_apply_annotation_delta` gain matching **latest-wins** slots. **"Resolved runtime identity" table**
  (`data-model.md:60-72`): resolved fields are dynamic (event-sourced, latest-wins), never conflated with
  authored (C-008). **INV-8** (`data-model.md:103`): after multiple pick-ups, the reconstructed resolved
  identity equals the most-recent transition's actual (latest-wins).
- **Contract `resolved-binding.md` "Vocabulary" section** (`contracts/resolved-binding.md:7-25`): add
  `resolved: { role, agent_profile, agent_profile_version, model, provider }`; **Reduced**: latest-wins
  into snapshot resolved slots (`_RUNTIME_SLOTS` + `_apply_annotation_delta`); **Absence is valid** (a
  never-reclaimed WP has no resolved slot → the fields stay `None`/absent).
- **Verified current code** (grounding for the tidy-firsts):
  - `status/models.py:366` `class WPInnerStateDelta` — fields at 381-389
    (`shell_pid`, `shell_pid_created_at`, `subtasks`, `note`, `tracker_refs`, `tracker_refs_replace`,
    `agent`, `assignee`, `review`). The field list is **enumerated three times**: `is_empty` (391-403),
    `to_dict` (405-428), `from_dict` (430-455). The plain-scalar fields (`shell_pid` int; `agent`,
    `assignee`, `shell_pid_created_at` str) serialize trivially; `subtasks` (Mapping), `review`
    (ReviewOverride), `tracker_refs`/`tracker_refs_replace` (list), `note` (str→`notes` slot) need custom
    encode/decode. The **five new slots are all plain `str | None`** — the trivially-serialized class.
  - `status/reducer.py:39-48` `_RUNTIME_SLOTS` (8 names) — carried forward across lane transitions by
    `_wp_state_from_event`'s loop (`reducer.py:96-99`). `status/reducer.py:117-161`
    `_apply_annotation_delta` — a flat if-chain (cx ~13); its **simple replace slots** are `shell_pid`,
    `shell_pid_created_at`, `agent`, `assignee` (each `if delta.X is not None: state["X"] = delta.X`);
    `subtasks`/`note`/`tracker_refs*`/`review` are special-cased and MUST stay so.

## Subtasks

### T033 — Tidy-first: data-drive `WPInnerStateDelta`'s field list, THEN add the 5 resolved slots

**Purpose**: Collapse the `is_empty`/`to_dict`/`from_dict` triple-enumeration into **one source of truth**
so the five new resolved slots are declared once, not three times — a behaviour-preserving refactor done
**before** the fields are added.

**Steps**:
1. **Collapse first (no new fields yet).** Rework `WPInnerStateDelta` so the field list is not repeated:
   - `is_empty()` → iterate the dataclass fields directly:
     `all(getattr(self, f.name) is None for f in dataclasses.fields(self))`. This is the strongest
     single-source-of-truth — a new field extends `is_empty` automatically, with **no** list to keep in
     sync.
   - `to_dict()`/`from_dict()` → declare **one** class/module constant of the plain-scalar field names
     (e.g. `_SCALAR_FIELDS: tuple[str, ...] = ("shell_pid", "shell_pid_created_at", "agent", "assignee")`)
     and iterate it in both directions (`to_dict`: `if (v := getattr(self, name)) is not None: d[name] = v`;
     `from_dict`: read each name from `data`). Keep the **special** fields (`subtasks`, `review`,
     `tracker_refs`, `tracker_refs_replace`, `note`) as explicit handlers — they are genuinely not scalar
     round-trips (`shell_pid` needs `int(...)` coercion in `from_dict`; if that complicates the scalar
     loop, keep `shell_pid` explicit and put only the pure `str | None` fields in `_SCALAR_FIELDS`). The
     bar is **genuine collapse** (one authoritative list the readers iterate), not three lists kept in sync.
2. **Prove the collapse is behaviour-preserving** with the round-trip test in T036 (run before adding
   fields, ideally): `from_dict(to_dict(x)) == x` and `is_empty` unchanged for the pre-existing fields.
3. **Then add the five resolved slots** as `role: str | None = None`, `agent_profile: str | None = None`,
   `agent_profile_version: str | None = None`, `model: str | None = None`, `provider: str | None = None`
   (declare them after `review`). Because they are pure `str | None`, adding each is now **one line in the
   dataclass + one name in `_SCALAR_FIELDS`** — `is_empty`/`to_dict`/`from_dict` pick them up with no other
   edit. Update the class docstring to name the resolved-binding group and cite FR-013/C-008 (authored ≠
   resolved).

**Edge cases**: `shell_pid`'s `int(...)` coercion and `subtasks`/`review` decode must not regress — keep
them explicit; absence of a resolved field leaves its slot untouched (the "absent → None" contract).

**Validation**: exactly **one** authoritative field list backs the three methods for the scalar class
(grep confirms no field name is written three times); round-trip and `is_empty` tests green before and
after the field addition; `ruff` + `mypy` clean; `dataclasses` import added if used.

### T034 — Tidy-first: extract `_apply_annotation_delta`'s if-chain into a data-driven replace-slot table

**Purpose**: Lower `reducer._apply_annotation_delta` from a flat if-chain (cx ~13) to a data-driven form
**before** the five slots are added, so it stays ≤15 (the slots would otherwise push it to ~18) — a
behaviour-preserving refactor with its own guard test.

**Steps**:
1. Declare a module constant of the **simple replace slots** — the fields whose fold rule is exactly
   `if delta.<name> is not None: state["<name>"] = delta.<name>`. Today that is `shell_pid`,
   `shell_pid_created_at`, `agent`, `assignee`. Name it e.g.
   `_REPLACE_SLOTS: tuple[str, ...] = ("shell_pid", "shell_pid_created_at", "agent", "assignee")`.
2. Replace those four `if` branches with a single loop:
   `for name in _REPLACE_SLOTS: value = getattr(delta, name); if value is not None: state[name] = value`.
   This removes four decision points and adds two (loop + guard), so cx drops (~13 → ~11) **with no
   behaviour change**.
3. Keep the **special** handlers exactly as-is: `subtasks` (per-subtask merge), `note` (append to the
   `notes` slot — note the field/slot name mismatch: delta `note` → snapshot `notes`, so it is NOT a
   replace slot), `tracker_refs`/`tracker_refs_replace` (union / wholesale-replace with precedence),
   `review` (`state["review"] = delta.review.to_dict()`).
4. **Behaviour-preserving proof**: the T036 refactor-parity test must show identical `state` output for the
   pre-existing slots before and after the extraction (fold a delta touching every current slot; assert the
   reduced dict is byte-equal to the pre-refactor expectation).

**Edge cases**: `note`/`notes` name mismatch (do not fold `note` via the replace table); `tracker_refs`
precedence (replace channel wins when both present) must be untouched; `review.to_dict()` conversion stays.

**Validation**: `_apply_annotation_delta` cyclomatic complexity ≤15 **after** T035's slots are added
(measured, not assumed); the parity test proves the extraction changed no output; `ruff` + `mypy` clean.

### T035 — Add the resolved slots to `_RUNTIME_SLOTS` + `_apply_annotation_delta` (latest-wins fold)

**Purpose**: Wire the five resolved slots through the reducer so an `InnerStateChanged` annotation folds
them **latest-wins** into the snapshot and lane transitions carry them forward.

**Steps**:
1. Extend `_RUNTIME_SLOTS` (`reducer.py:39-48`) with `role`, `agent_profile`, `agent_profile_version`,
   `model`, `provider` so `_wp_state_from_event`'s carry-forward loop (`reducer.py:96-99`) preserves them
   across every lane transition (an implement-claim annotation's binding survives to the review-claim,
   where a new annotation replaces it — latest-wins across the lifecycle, INV-8).
2. Add the same five names to the `_REPLACE_SLOTS` table from T034 — they are pure replace slots, so **no
   new `if` branch** is added to `_apply_annotation_delta` (the whole point of the tidy-first): the loop
   picks them up as data. This is where "5 slots don't push cx >15" is realized.
3. Update the `_apply_annotation_delta` docstring to list the resolved-binding replace slots and cite the
   latest-wins semantics (FR-013 / INV-8).

**Edge cases**: a delta that sets only `model` (a mid-cycle model swap with an unchanged profile) replaces
only that slot, leaving `role`/`agent_profile` intact; an absent resolved field never clobbers a
previously-folded value.

**Validation**: `_RUNTIME_SLOTS` contains all five; a second annotation with new resolved values replaces
the slots (latest-wins), a `None` field leaves the slot untouched; the reduced snapshot exposes the five
resolved slots for a WP that received a resolved-binding annotation; complexity still ≤15.

### T036 — Tests (ATDD): latest-wins fold, delta round-trip, is_empty, tidy-first parity

**Purpose**: Prove the vocabulary + both tidy-firsts with **non-vacuous** tests over real deltas/events.
New file `tests/specify_cli/status/test_resolved_binding_reducer.py` (owned / create-intent).

**Steps**:
1. **Latest-wins reduction** (the headline, FR-013 / INV-8): build an event stream with an
   `InnerStateChanged` annotation carrying resolved `{role: implementer, agent_profile: P1,
   agent_profile_version: v1, model: M1, provider: prov1}`, then a second annotation with
   `{role: reviewer, agent_profile: P2, model: M2}`; reduce and assert the snapshot's resolved slots =
   the **most recent** values (`P2`/`M2`/`reviewer`) while `agent_profile_version`/`provider` retain the
   last non-None value folded (unchanged fields persist). Cover the carry-forward-across-transition path:
   annotation → lane transition → assert the resolved slots survive the transition.
2. **Delta round-trip** (`to_dict`/`from_dict`): a `WPInnerStateDelta` populated with the five resolved
   fields (and a mix of pre-existing fields) satisfies `from_dict(to_dict(x)) == x`; a delta with the
   resolved fields **absent** omits them from `to_dict()` output (absent-leaves-slot-untouched wire
   contract).
3. **`is_empty` correctness with the new fields**: a delta carrying only `model` (or only `role`) is
   **not** empty; the all-`None` delta **is** empty — exercising the dataclass-fields-driven `is_empty`
   so a future added field is covered automatically.
4. **Tidy-first parity (T033 + T034 behaviour-preservation)**: (a) a round-trip / `is_empty` check over
   the **pre-existing** fields proves the T033 collapse changed nothing for them; (b) an
   `_apply_annotation_delta` fold over a delta touching every pre-existing slot
   (`shell_pid`/`subtasks`/`note`/`tracker_refs`/`tracker_refs_replace`/`agent`/`assignee`/`review`)
   asserts the reduced `state` equals the known-good pre-refactor shape — proving T034's extraction is
   behaviour-preserving (including the `note`→`notes` mapping and `tracker_refs_replace` precedence).

**Edge cases**: `tracker_refs_replace` precedence over `tracker_refs` in the parity fold; `note` appended
to `notes` (not a replace slot); a resolved-binding annotation on a WP that never carried one before adds
the slots without disturbing `shell_pid`/`agent`.

**Validation**: the file passes per-file (command below); the latest-wins test **fails** if the fold is
made first-wins or the carry-forward is dropped (non-vacuous); the parity test **fails** if the tidy-first
extraction changes any pre-existing slot's output; no test mocks the reducer — it folds real events.

## Branch Strategy

Planning artifacts were generated on `feat/runtime-state-corpus-cutover`; this WP's completed changes
merge back into `feat/runtime-state-corpus-cutover` (both `planning_base_branch` and
`merge_target_branch`). Execute in the workspace `spec-kitty implement WP09` prepares — the execution
worktree/branch is the computed lane from `lanes.json` (do not reconstruct the path by hand; consume the
resolved workspace). WP09 **depends on WP08** (the C-009 field-authority ADR must land first); do not
begin the vocabulary change until WP08 is approved/done.

## Test strategy

Run the owned test file **individually** with a timeout — never the whole `tests/architectural/`
directory (it hangs). Use `uv run` (bare `python` resolves a sibling checkout → false greens):

```bash
timeout 600 uv run --extra test python -m pytest -p no:cacheprovider tests/specify_cli/status/test_resolved_binding_reducer.py
# regression-check the existing model/reducer suites the tidy-firsts touch:
timeout 600 uv run --extra test python -m pytest -p no:cacheprovider tests/specify_cli/status/
```

Quality gates (must be clean, no suppressions):

```bash
uv run ruff check src/specify_cli/status/models.py src/specify_cli/status/reducer.py
uv run mypy src/specify_cli/status/models.py src/specify_cli/status/reducer.py
```

## Definition of Done

- [ ] `WPInnerStateDelta` carries `role`/`agent_profile`/`agent_profile_version`/`model`/`provider`
  (`str | None`), and the triple-enumeration is **genuinely collapsed** — one authoritative field list
  backs `is_empty`/`to_dict`/`from_dict` for the scalar class (FR-013, D-14, plan IC-08 vocabulary bullet).
- [ ] `_apply_annotation_delta` uses a **data-driven replace-slot table** (not a flat if-chain); its
  cyclomatic complexity is **≤15** with the five slots added (measured); the special handlers
  (`subtasks`/`note`/`tracker_refs*`/`review`) are unchanged (D-14 tidy-first).
- [ ] `_RUNTIME_SLOTS` includes all five resolved slots; they carry forward across lane transitions and
  fold **latest-wins** via `_apply_annotation_delta` (FR-013, INV-8, data-model new-vocabulary).
- [ ] Latest-wins reduction is **proven** by a non-vacuous test (a second annotation replaces the resolved
  slots; carry-forward across a transition holds); delta round-trip (`to_dict`/`from_dict`) and `is_empty`
  are correct with the new fields; both tidy-firsts have behaviour-preserving parity tests.
- [ ] **WP08's C-009 field-authority ADR landed first** (dependency satisfied) — the vocabulary did not
  land ahead of the ADR.
- [ ] Scope respected: **no** backfill re-seed, **no** claim-seam emit, **no** dispatch→claim linkage here
  (that is WP10); this WP is vocabulary + reducer only.
- [ ] `ruff` + `mypy` clean with zero new `# noqa` / `# type: ignore` / per-file ignores; cx ≤15
  everywhere touched (NFR-004).

## Risks & out-of-map edits

- **`models.py` is edited later by WP12 (IC-09 actor widening — `StatusEvent.actor: str → str | dict`).**
  This WP **owns** `models.py` for the `WPInnerStateDelta` vocabulary; WP12 makes a **later out-of-map
  touch** to the same module for the `actor` type-surface. Keep this WP's edits confined to
  `WPInnerStateDelta` (and its scalar-field table) — do **not** pre-empt or widen `StatusEvent.actor`,
  `build_status_event`, or the `InnerStateChanged.actor` `str(...)` coercions (all WP12). Sequencing the two
  WPs on the same file is expected; each owns a disjoint region.
- **Do the tidy-firsts FIRST.** If the five slots are added before the T033 collapse / T034 extraction, the
  triple-enumeration becomes a 3× field-list edit and `_apply_annotation_delta` blows past cx 15 —
  violating the plan's (deliberately empty) Complexity Tracking. Order is load-bearing: collapse → extract
  → add slots.
- **Do NOT touch the backfill, the claim seams, the dispatch/invocation layer, or `emit.py`** — the
  *sourcing* of resolved values (never the frontmatter string, C-007) and the `"resolved_binding"` re-seed
  namespace (C-011) are WP10. Recording a value here would be scope creep and a C-007 hazard.
- **`note` vs `notes` name mismatch** and **`tracker_refs_replace` precedence** are the two behaviour traps
  in the reducer refactor — the parity test (T036.4) exists to catch a regression in either.

## Reviewer guidance (adversarial)

- **Is the triple-enumeration genuinely collapsed — not three lists kept in sync?** Confirm `is_empty`
  iterates the dataclass fields (or the one scalar table), and `to_dict`/`from_dict` iterate **one**
  authoritative `_SCALAR_FIELDS` constant. Grep the five new field names: each must appear as **one**
  dataclass declaration + **one** table entry, never re-listed in each method. A PR that just added the
  five names to three hand-lists is a **reject** — the tidy-first was the point.
- **Is the replace-slot table data-driven, and is `_apply_annotation_delta` ≤15?** Confirm the simple-slot
  folds are a single loop over `_REPLACE_SLOTS` (not restored if-branches), the five resolved slots are
  data in that table (zero new branches), and the measured complexity is ≤15 with the slots present. Confirm
  `subtasks`/`note`/`tracker_refs*`/`review` remained special-cased and unchanged.
- **Is latest-wins actually tested?** The reduction test must fold a *second* annotation and assert the
  resolved slots equal the **most recent** values, and must prove carry-forward across a lane transition.
  Reject a test that folds a single annotation (that proves presence, not latest-wins) or one that mocks the
  reducer instead of folding real `InnerStateChanged` events.
- **Are the tidy-firsts proven behaviour-preserving?** Confirm a parity test shows identical output for the
  pre-existing fields before/after both refactors (including `note`→`notes` and `tracker_refs_replace`
  precedence) — the refactors must be observably no-ops for existing behaviour.
- **Scope + dependency:** confirm this WP touched only `WPInnerStateDelta` + the reducer (no backfill, no
  emit, no claim seam, no `StatusEvent.actor`), and that WP08's C-009 ADR is landed. No new suppressions.

## Activity Log

- 2026-07-20T18:10:28Z – claude – shell_pid=365160 – Assigned agent via action command
- 2026-07-20T18:26:24Z – claude – shell_pid=365160 – Ready for review: resolved-binding vocabulary + reducer slots; two behaviour-preserving tidy-firsts (data-driven delta collapse + _REPLACE_SLOTS table, cx 13->11). 18 new tests + 447 regression tests green; ruff+mypy clean.
- 2026-07-20T18:27:51Z – claude – shell_pid=411008 – Started review via action command
- 2026-07-20T18:29:27Z – user – shell_pid=411008 – Approved: triple-enum collapsed, replace-table cx13->11, 18 latest-wins tests, tidy-firsts pinned
