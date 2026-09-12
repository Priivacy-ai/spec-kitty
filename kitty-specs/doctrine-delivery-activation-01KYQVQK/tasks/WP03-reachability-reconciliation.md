---
work_package_id: WP03
title: Reachability reconciliation (terminal)
dependencies:
- WP01
- WP02
requirement_refs:
- FR-004
- FR-005
- FR-006
- NFR-002
- NFR-004
planning_base_branch: feat/doctrine-delivery-activation
merge_target_branch: feat/doctrine-delivery-activation
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-delivery-activation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-delivery-activation unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
- T015
phase: Phase 2 - Reachability reconciliation
history:
- at: '2026-07-29T22:04:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/doctrine/drg/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/doctrine/drg/test_reachability.py
- docs/plans/doctrine/delivery-reachability-wiring-table.md
- tests/architectural/test_no_dead_symbols.py
- tests/architectural/_baselines.yaml
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 – Reachability reconciliation (terminal)

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

This WP is the **terminal reconciliation** of the mission: it re-measures the profile-reachable
set via the canonical helper and reconciles ONLY the **reachability** goldens — the pins, the
wiring-table deferred set, and the final forward-API allowlist sweep. It does **not** touch
node/edge cardinality or the relation histogram; those goldens are owned by WP02 (D15) because
WP02 is the WP that authors the DRG-YAML topology that moves them.

- **SC-001/SC-002 (spec.md)**: `_PROFILE_UNREACHABLE`, `_PROFILE_RESCUES`, and
  `_ACTION_UNREACHABLE_D2` in `tests/doctrine/drg/test_reachability.py` are re-measured and
  reconciled to the live topology WP01+WP02 produced.
- **SC-002**: `docs/plans/doctrine/delivery-reachability-wiring-table.md` deferred set drops below
  its baseline of **60** (not 50 — the "50"/"39" figures in the current prose are stale, D19), with
  Family ledger rows for every moved artefact.
- **SC-003**: `_CATEGORY_C_DELIVERY_RAIL_FORWARD_API` (and its `_baselines.yaml` mirror row) shrinks
  by the **2–3 symbols this mission genuinely wired with a cross-file `src/` consumer** — no more,
  no less. `test_no_dead_symbols` stays green.
- A lightweight cross-check test exists that ties each moved reachability member to a ledger
  entry, and the prompt/PR states explicitly that per-member ledger-vs-diff review is the sole,
  non-delegable gate for the pins (D18 — NFR-002 is review-gated, not CI-gated, for this file).

**Definition of "done" for this WP**: every reachability golden that WP01/WP02 caused to move is
reconciled with a ledger row, the deferred set is demonstrably lower than 60, the allowlist sweep
removed only the genuinely-wired ~2–3 symbols, and the targeted test suites listed under Definition
of Done are green.

## Context & Constraints

- **Grounding documents**: `kitty-specs/doctrine-delivery-activation-01KYQVQK/plan.md` §IC-05 (the
  concern this WP implements), `pre-planning-ledger.md` D10–D19 (all load-bearing; D15/D16/D18/D19
  are specific to this WP), `spec.md` FR-004/FR-005/FR-006(final sweep)/NFR-002/NFR-004, and
  `tasks.md` WP03 section.
- **This WP is TERMINAL**: it depends on **WP01 AND WP02**. WP01 is the core delivery vector (the
  `suggests` walk extension); WP02 authors the DRG topology (Family-A `when` backfill, C4
  `template:instantiates` edge, anti-pattern `REJECTS` edges) and owns the cardinality/histogram
  goldens those authorings move. Do not start until both are merged/available in your branch base —
  reconciling against a moving target produces goldens that go stale again on the next merge.
  - **Important nuance (D16, tasks.md)**: the WP01+WP02 dependency is really about the
    **wiring-table Family rows** (which need the completed topology from both). The
    `_PROFILE_UNREACHABLE`/`_PROFILE_RESCUES` **pin delta itself is a pure function of WP01**
    (the `suggests` relation addition) — a reviewer can verify that delta independently of WP02's
    topology-authoring changes. Keep this distinction in mind when explaining your diff to a
    reviewer: the pin numbers and the wiring-table numbers have different — though overlapping —
    grounding.
- **Ownership boundary (D15, hard constraint)**: this WP owns ONLY reachability goldens:
  `_PROFILE_UNREACHABLE`, `_PROFILE_RESCUES`, `_ACTION_UNREACHABLE_D2`
  (`tests/doctrine/drg/test_reachability.py`), the wiring-table deferred set + Family ledgers
  (`docs/plans/doctrine/delivery-reachability-wiring-table.md`), and the forward-API allowlist
  frozenset + baseline mirror (`tests/architectural/test_no_dead_symbols.py`,
  `tests/architectural/_baselines.yaml`). **Do NOT touch**: `_EXPECTED_NODE_COUNT` /
  `_EXPECTED_EDGE_COUNT` (`test_unknown_kind_fails_loudly.py`), `HAND_AUTHORED_EDGES` /
  extractor goldens (`test_extractor_projection.py`), `RELATION_DESCRIPTIONS` histogram claims
  (`doctrine.drg.models` + `docs/architecture/doctrine-relationships.md`), or
  `test_relation_doc_parity.py`. If your re-measurement surfaces a discrepancy in one of those
  files, it is WP02's ownership — flag it in the Activity Log rather than editing it here.
- **Measurement discipline (C-001, hard constraint)**: measure the reachable set **only** via
  `action_channel_reachable` / `profile_channel_reachable`
  (`src/doctrine/drg/reachability.py`) — never hand-roll a walk or re-derive reachability by
  inspecting the DRG-YAML directly. Every number you paste into a golden must trace back to a call
  through these canonical helpers.
- **Review-gating, not CI-gating (D18, critical)**: `_PROFILE_UNREACHABLE` is a hardcoded literal
  frozenset asserted `measured == pin` (`test_reachability.py:363-519`, currently 153 members) —
  the test goes green the instant you paste in the new set, whether or not the set is *correct*.
  This is fundamentally different from the cardinality/histogram goldens WP02 owns, which have a
  real CI-enforced counting mechanism behind them. For this WP, **the reviewer's per-member
  ledger-vs-diff comparison is the sole non-delegable correctness gate** — you must make that
  review tractable (see T013/T015) rather than relying on the test suite alone to prove
  correctness.
- **Baseline correction (D19)**: the wiring table's current prose says "deferred set = 50" in one
  place (line ~271: "directive 4 · paradigm 3 · procedure 4 · styleguide 3 · tactic 28 ·
  toolguide 8") and "Deferred set unchanged at 60" in another (line ~500). The **60** figure is the
  authoritative baseline; the "50" and the Family-A "39→39" claim elsewhere in the doc are stale
  and must be reconciled as part of this WP's start — do this as an explicit first fix, not
  silently folded into the final diff, so a reviewer can see it called out.
- **NFR-002, no silent golden movement**: every reachability/deferred-set number that changes MUST
  carry a matching composition-ledger entry (a row in the wiring table or an equivalent explicit
  note) — zero golden counts move without a paired, human-readable justification.

## Branch Strategy

- **Strategy**: Planning artifacts generated on feat/doctrine-delivery-activation; during implement
  this WP may branch from a dependency-specific base but merges back into
  feat/doctrine-delivery-activation unless the human redirects.
- **Planning base branch**: feat/doctrine-delivery-activation
- **Merge target branch**: feat/doctrine-delivery-activation

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.
> Because this WP is terminal (depends on WP01 + WP02), branch your worktree from the tip that
> already contains both WP01's and WP02's merged/landed changes, not from the mission's original
> base — reconciling against a stale base will immediately go stale again.

## Subtasks & Detailed Guidance

### T012 – Re-measure via the canonical helper and reconcile the reachability pins

- **Purpose**: Establish the new ground truth for `_PROFILE_UNREACHABLE`, `_PROFILE_RESCUES`, and
  `_ACTION_UNREACHABLE_D2` now that WP01 has widened `PROFILE_CHANNEL_RELATIONS` to include
  `SUGGESTS` and WP02 has landed its Family-A/B/C DRG topology.
- **Steps**:
  1. In a scratch script or a REPL session (never hand-edit the golden first), call
     `profile_channel_reachable(graph, agent_profile_seed_urns(graph))` and
     `action_channel_reachable(graph, ..., max_depth=2)` (the exact call shapes already used at
     `test_reachability.py:363-519` / `:303-330` for `_ACTION_UNREACHABLE_D2`) to compute the live
     reachable sets. Do not construct the walk by any other means (C-001).
  2. Compute the new `_PROFILE_UNREACHABLE` = `_activated() - profile_channel_reachable(...)` —
     same derivation as the current frozenset's docstring, just re-run.
  3. Compute the new `_PROFILE_RESCUES` = `_ACTION_UNREACHABLE_D2 - _PROFILE_UNREACHABLE` (per the
     existing docstring at `test_reachability.py:520-524`).
  4. Diff the old frozensets against the new sets member-by-member. For every member that
     **left** `_PROFILE_UNREACHABLE` (now profile-reachable via a `suggests` edge WP01 wired or a
     WP02-authored topology change), confirm you can name the edge/family responsible (Family A/B/C
     from the ledger, or a WP02-specific addition) — this traceability feeds T013's ledger and
     T015's cross-check.
  5. Update the three frozensets in `tests/doctrine/drg/test_reachability.py` in place, preserving
     the existing docstrings' derivation language (update the member counts mentioned in comments,
     e.g. "153 members", to match the new counts).
- **Files**: `tests/doctrine/drg/test_reachability.py` (`_PROFILE_UNREACHABLE` ~L363-519,
  `_PROFILE_RESCUES` ~L525-530, `_ACTION_UNREACHABLE_D2` ~L303-330 region — confirm exact spans in
  your checkout since WP01/WP02 land first).
- **Validation**: `uv run pytest tests/doctrine/drg/test_reachability.py -q` green with the new
  frozensets in place — this is a golden-paste test (D18), so also eyeball the diff against your
  T012.4 traceability notes before moving on.
- **Notes**: If a member you expect to move does NOT move (e.g. it's reachable only via an
  `instantiates` edge, which no channel walks per D13), do not force it — leave it in
  `_PROFILE_UNREACHABLE` and record why in the Activity Log. Do not silently "fix" a member that
  looks wrong without first checking whether the underlying edge is inert by design (D14 — REJECTS
  edges are validation-tier, never delivered).

### T013 – Wiring-table deferred set reconciliation + Family ledgers + stale-prose fix

- **Purpose**: Update the human-readable wiring table so it reflects the live topology, correct the
  stale 50/39 baseline prose (D19), and give the reviewer a durable, per-family record of what
  moved and why — this ledger is what makes T012's review-gated pins tractable to verify (D18).
- **Steps**:
  1. **First**, as a standalone, clearly-labelled fix: correct every place in
     `docs/plans/doctrine/delivery-reachability-wiring-table.md` that states the deferred set is
     "50" (including the Family-A "39→39" breakdown around line ~271) to read **60**, matching the
     already-correct "Deferred set unchanged at 60" language elsewhere in the same document
     (~line 500). Do this before layering in your own reconciliation so the diff is legible as
     "first: fix the pre-existing inconsistency, then: reconcile against the new baseline".
  2. Using T012's member-by-member diff, remove from the deferred set every artefact that became
     reachable this mission (via WP01's `suggests` walk extension or WP02's topology authoring),
     and add one ledger row per Family (A/B/C/E as applicable) recording: which artefacts moved,
     via which edge/relation, and which WP (WP01 vs WP02) is responsible for that edge existing.
  3. Update the "Full deferred set (N), by kind" breakdown line to the new count and per-kind
     tallies.
  4. Confirm the new deferred-set count is strictly **below 60** — if your T012 diff shows zero
     movement, something is wrong (WP01 alone rescues at least the Family A/B/C/E artefacts per the
     ledger); re-check your measurement call in T012 before concluding the count is unchanged.
- **Files**: `docs/plans/doctrine/delivery-reachability-wiring-table.md`.
- **Validation**: Manual review — this file is prose/markdown, not test-gated. Cross-check every
  new ledger row against T012's measured diff so a reviewer can verify 1:1 (this is the
  ledger-vs-diff review D18 requires).
- **Notes**: Do not invent Family rows for artefacts you cannot trace to a specific edge — if T012
  moved a member you can't explain, treat that as a signal to re-verify the measurement, not as
  license to write a vague ledger entry.

### T014 – Final forward-API allowlist sweep

- **Purpose**: Retire from `_CATEGORY_C_DELIVERY_RAIL_FORWARD_API` only the symbols this mission
  genuinely wired with a cross-file `src/` consumer — per D17's pre-classification, that is
  **~2–3 symbols**, most likely `agent_profile_seed_urns` (WP01's T004 explicitly consumes it
  cross-file), and possibly `PROFILE_CHANNEL_RELATIONS` and/or `partition_delivery` if WP01 ended
  up consuming them directly rather than only indirectly. The remaining ~6 symbols
  (`charter_activated_urns`, `normalize_activation_identifier`, `partition_activated_unreachable`,
  `ActivationReachabilityPartition`, `action_channel_reachable`, `action_seed_urns`) are a
  **different concern** (charter-activation / action-channel reachability) that this mission does
  not build a `src/` consumer for — they stay allowlisted-with-note.
- **Steps**:
  1. Read WP01's Activity Log / diff to confirm exactly which of the 9 symbols now have a
     genuine cross-file `src/` importer (not a test-only reference — `_symbol_has_caller` in the
     dead-symbols gate counts only `src/` importers by design, per D17/tasks.md, so a test import
     alone does not qualify a symbol for removal and does NOT accidentally trip the gate either).
  2. For each confirmed-wired symbol, remove its `SymbolKey(...)` entry from
     `_CATEGORY_C_DELIVERY_RAIL_FORWARD_API` in
     `tests/architectural/test_no_dead_symbols.py:1089-1106` and remove/update the matching mirror
     row in `tests/architectural/_baselines.yaml` (`category_c_delivery_rail_forward_api` count —
     currently `19` covering the whole Category C bucket, not just this frozenset; adjust only the
     portion attributable to these symbols leaving the allowlist).
  3. For every symbol that stays allowlisted, confirm its explanatory comment in
     `test_no_dead_symbols.py` still accurately states why (charter-activation / action-channel
     concern, no `src/` consumer built by this mission) — update the comment if the existing text
     no longer matches (e.g. if it referenced "not yet wired" language that should now say
     "different concern, deliberately not wired here").
  4. **Do NOT manufacture a fake cross-file importer** to make a symbol qualify for removal — this
     is explicitly called out in the spec (FR-006, SC-003) and the ledger (IC-02 risk) as the
     anti-pattern the gate exists to catch. If a symbol looks "almost wired" but isn't genuinely
     consumed, leave it allowlisted.
- **Files**: `tests/architectural/test_no_dead_symbols.py` (`_CATEGORY_C_DELIVERY_RAIL_FORWARD_API`
  ~L1089-1106), `tests/architectural/_baselines.yaml` (`category_c_delivery_rail_forward_api`
  mirror row, ~L286-297).
- **Validation**: `uv run pytest tests/architectural/test_no_dead_symbols.py -q` green — both the
  positive case (retired symbols genuinely have a `src/` caller) and the negative case (remaining
  allowlisted symbols still have zero `src/` callers, so the gate doesn't flag them as newly-dead
  without an allowlist entry).
- **Notes**: `profile_channel_reachable` is already wired (the 10th rail symbol, not part of this
  frozenset) — use its existing consumption in `src/doctrine/agent_profiles/repository.py:875` as
  the template for what "genuinely wired" looks like when judging the other candidates.

### T015 – Lightweight member-vs-ledger cross-check test + review-gate note

- **Purpose**: Because NFR-002 is review-gated rather than CI-gated for this file (D18), add a
  narrow, low-maintenance test that catches the most common regression class (a golden edited
  without a matching ledger row) without pretending to fully validate correctness — and record,
  explicitly and in writing, that human ledger-vs-diff review remains the sole non-delegable gate.
- **Steps**:
  1. Write a small test (e.g.
     `tests/doctrine/drg/test_reachability.py::test_profile_rescues_have_ledger_coverage` or a
     sibling test function near the existing pin tests) that parses
     `docs/plans/doctrine/delivery-reachability-wiring-table.md` for the Family ledger rows you
     added in T013 and asserts every member currently in `_PROFILE_RESCUES` (or, more usefully,
     every member that left `_PROFILE_UNREACHABLE` since the mission's starting baseline, if you
     can express that without hardcoding a second copy of the historical baseline) has at least one
     ledger row referencing it. Keep the parsing simple (a regex or line-scan over the Family
     section headers is enough — do not build a markdown AST parser for this).
  2. This test is a **cross-check**, not a correctness proof — it catches "you edited the pin but
     forgot the ledger row", not "the pin value is numerically correct". Say so in the test's
     docstring.
  3. Add a short, explicit note — in this WP's PR description and as a comment near the
     `_PROFILE_UNREACHABLE` frozenset definition — stating: *"NFR-002 for this file is
     review-gated, not CI-gated: `measured == pin` greens on any pasted value. The per-member
     ledger-vs-diff comparison in the reviewer's pass is the sole non-delegable correctness gate for
     these numbers."* This is not optional flavor text — omitting it is a Definition-of-Done gap
     for this WP (see Definition of Done below).
- **Files**: `tests/doctrine/drg/test_reachability.py` (new test function; any new
  create_intent path you introduce for a helper module belongs in this WP's `create_intent` list —
  update the frontmatter if you add one).
- **Validation**: `uv run pytest tests/doctrine/drg/test_reachability.py -q` green, including the
  new cross-check test; the cross-check test itself must be proven red-first against a fixture
  ledger missing a row (a temporary local check during development is sufficient — this doesn't
  need a permanent red-first regression fixture given its narrow scope, but confirm it actually
  fails on a missing-row case before calling it done).
- **Notes**: Keep this test cheap to maintain — a full formal ledger schema is out of scope; the
  goal is "catch the forgot-the-row mistake", not "build a second source of truth".

## Definition of Done

- [ ] `_PROFILE_UNREACHABLE`, `_PROFILE_RESCUES`, and `_ACTION_UNREACHABLE_D2` re-measured via
      `profile_channel_reachable`/`action_channel_reachable` only (C-001) and reconciled to the
      live WP01+WP02 topology.
- [ ] Wiring-table stale "50"/"39" prose corrected to the **60** baseline as an explicit, separately
      identifiable fix (D19), and the deferred set demonstrably drops below 60 with per-Family
      ledger rows for every moved artefact.
- [ ] `_CATEGORY_C_DELIVERY_RAIL_FORWARD_API` shrinks by exactly the symbols with a genuine
      cross-file `src/` consumer (~2–3, per D17) — no manufactured importers, no over-retirement of
      the ~6 charter-activation symbols that stay allowlisted-with-note; `_baselines.yaml` mirror
      updated to match.
- [ ] A lightweight member-vs-ledger cross-check test exists and is proven to catch a missing ledger
      row; an explicit review-gate note (D18) is present both in the PR description and as a code
      comment near `_PROFILE_UNREACHABLE`.
- [ ] `uv run pytest tests/doctrine/drg/test_reachability.py -q` — green.
- [ ] `uv run pytest tests/architectural/test_no_dead_symbols.py -q` — green.
- [ ] `uv run mypy --strict tests/doctrine/drg/test_reachability.py` — clean (no new ignores).
- [ ] `uv run ruff check tests/doctrine/drg/test_reachability.py tests/architectural/test_no_dead_symbols.py` —
      clean.
- [ ] **Do NOT run the full `tests/architectural/` suite locally** — it breaks the session; the
      two targeted node-ids above plus a CI pass are the gate. Do not run the full
      `tests/doctrine/` suite either; scope to the file above.
- [ ] No edits to `_EXPECTED_NODE_COUNT`/`_EXPECTED_EDGE_COUNT`, `HAND_AUTHORED_EDGES`,
      `RELATION_DESCRIPTIONS`, or `test_relation_doc_parity.py` — those are WP02's ownership (D15);
      if your measurement surfaces a discrepancy there, flag it in the Activity Log instead of
      editing it.

## Risks & Mitigations

- **Review-gated golden (D18)**: `_PROFILE_UNREACHABLE`'s test greens on any pasted value —
  mitigate by making the T013 ledger and T015 cross-check the actual verification surface, and by
  writing the review-gate note explicitly so no reviewer mistakes "tests pass" for "numbers are
  correct".
- **Stale baseline confusion (D19)**: the wiring table currently contradicts itself (50 vs 60) —
  mitigate by fixing that as an isolated first step (T013.1) so the reconciliation diff is legible
  against a self-consistent starting point.
- **Ownership creep into WP02's goldens (D15)**: it is tempting to "just fix" a cardinality/
  histogram number you notice is off while you're in these files — resist this; note it in the
  Activity Log for WP02 instead. Mixing ownership makes both WPs' diffs harder to review
  independently.
- **Over-retirement of the allowlist (D17/FR-006)**: retiring more than the genuinely-wired 2–3
  symbols (or manufacturing a fake importer to justify retiring one) directly contradicts SC-003 —
  mitigate by requiring a real, named cross-file `src/` call site for every symbol you remove.
- **Terminal-dependency staleness**: because this WP depends on both WP01 and WP02, branching from
  a base that doesn't yet include both makes every measurement in T012 wrong from the start —
  confirm your worktree base includes both before running T012.

## Reviewer Guidance

- **Verify the measurement provenance**: confirm every changed number in `test_reachability.py` can
  be traced to a real call through `profile_channel_reachable`/`action_channel_reachable` — ask the
  implementer to show the measurement script/session if it isn't obvious from the diff.
- **Do the ledger-vs-diff comparison yourself (D18)**: this is the load-bearing review step for this
  WP. For every member added to or removed from `_PROFILE_UNREACHABLE`/`_PROFILE_RESCUES`, confirm
  there is a corresponding wiring-table Family ledger row naming the edge/WP responsible. A pin
  change with no matching ledger row is a hard reject regardless of whether the tests are green.
- **Confirm the baseline-60 fix is isolated and correct**: check that the 50/39 stale-prose
  correction (D19) reads as a distinct, understandable fix rather than being buried inside the
  reconciliation diff.
- **Confirm ownership boundaries held**: diff `test_unknown_kind_fails_loudly.py`,
  `test_extractor_projection.py`, `doctrine.drg.models` (`RELATION_DESCRIPTIONS`),
  `docs/architecture/doctrine-relationships.md`, and `test_relation_doc_parity.py` — none of these
  should appear in this WP's changeset. If they do, that's WP02's territory leaking in.
- **Confirm the allowlist sweep is exactly the wired set**: cross-check each removed
  `SymbolKey` entry against a real `src/`-file import site in the diff (not a test file). Confirm
  the ~6 stay-allowlisted symbols' explanatory comments still make sense post-mission.
- **Confirm the cross-check test actually catches something**: ask for evidence (or verify
  yourself) that the T015 test fails when a ledger row is missing — a cross-check test that always
  passes regardless of ledger state is vacuous and should be rejected.

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
`spec-kitty agent tasks move-task WP03 --to <status>` to change WP status.

### Optional Phase Subdirectories

For large features, organize prompts under `tasks/` to keep bundles grouped while maintaining
lexical ordering.
