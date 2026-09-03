---
work_package_id: WP04
title: Triage the three pinning test files against WP01's rewrite
dependencies:
- WP01
requirement_refs:
- FR-010
planning_base_branch: fix/spdd-reasons-activation-split-brain-3838
merge_target_branch: fix/spdd-reasons-activation-split-brain-3838
branch_strategy: Planning artifacts for this mission were generated on fix/spdd-reasons-activation-split-brain-3838. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/spdd-reasons-activation-split-brain-3838 unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
history: []
agent_profile: implementer-ivan
authoritative_surface: tests/charter/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/charter/test_charter_context_spdd_reasons.py
- tests/charter/test_activate_resolves_no_answers_edit.py
- tests/charter/test_answers_inert_and_org_union.py
role: implementer
tags: []
tracker_refs: []
---

# WP04 — Triage the three pre-existing pinning test files against WP01's rewrite

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Triage every assertion in `tests/charter/test_charter_context_spdd_reasons.py`,
`tests/charter/test_activate_resolves_no_answers_edit.py`, and `tests/charter/test_answers_inert_and_org_union.py`
against WP01's rewritten `is_spdd_reasons_active`: keep assertions whose intent survives, flip assertions
that encode the bug itself, and rewrite the fixture-construction mechanism (not merely the assertion) for
the bucket-3 methods FR-010 names — writing `.kittify/config.yaml`'s `activated_*` keys instead of
`charter.yaml`'s `governance:`/`directives:` sections, while preserving each test's original selector
under test.

## Context

**This WP DEPENDS ON WP01** — it cannot go green until WP01's rewritten `is_spdd_reasons_active` has
landed. Per C-011/plan.md section (i), this WP's own red-first commits are sequenced BEFORE WP01's
implementation commit conceptually (the fixture rewrites are "red against the OLD function"), but as a
practical matter you should implement this WP AFTER WP01's implementation commit is available in your
workspace, then verify: (a) the rewritten fixture, run against WP01's OLD body (checkout WP01's pre-implementation
commit, or reason about it directly from the old source you can still read in git history) is RED, and (b)
the same fixture, run against WP01's NEW body, is GREEN. Record both observations — do not merely assert
GREEN-after and assume RED-before.

**FR-010's own three-bucket triage (verified against the live test files for this WP, not copied from the
mission brief without re-checking):**

### Bucket 3 — fixture-construction mechanism rewrite (8 methods named by FR-010, one additional found
during this WP's own re-verification — 9 total)

All 8 write ONLY `.kittify/charter/charter.yaml`'s `governance:`/`directives:` sections via `save_charter_yaml`
or the local `_write_governance`/`_write_directives` helpers, and never write a `.kittify/config.yaml` at
all — so under WP01's rewrite, every one of them hits the FR-004 absent-config-file path and returns
`False` unconditionally, breaking their `True`-asserting expectations. Each needs its fixture-construction
mechanism rewritten to ALSO (or instead) write `.kittify/config.yaml`'s `activated_paradigms`/
`activated_directives`/`activated_tactics` keys (a `charter:` pointer is optional — direct-on-config.yaml
is simplest for these), while preserving the exact selector under test:

**`tests/charter/test_charter_context_spdd_reasons.py`, class `TestActivation`** (all currently use
`_write_governance`/`_write_directives`, which write only `charter.yaml`):

1. `test_paradigm_selected_returns_true` — currently writes `governance:` `selected_paradigms:
   [structured-prompt-driven-development]`. Rewrite: ALSO write `.kittify/config.yaml` with
   `activated_paradigms: [structured-prompt-driven-development]`. Keep the `governance:` write too (or
   drop it) — your call; the load-bearing addition is the `config.yaml` write, since that is what the new
   function actually reads. Assertion (`is_spdd_reasons_active(tmp_path) is True`) is UNCHANGED.
2. `test_only_tactic_fill_returns_true` — mirror with `activated_tactics: [reasons-canvas-fill]`.
3. `test_only_tactic_review_returns_true` — mirror with `activated_tactics: [reasons-canvas-review]`.
4. `test_only_directive_038_returns_true` — mirror with `activated_directives: [DIRECTIVE_038]`.
5. `test_directive_038_via_directives_yaml` — currently writes DIRECTIVE_038 via `_write_directives`'s
   `directives:` entry-list form (testing the numeric-hint/entry-list matching path). Rewrite: write
   `.kittify/config.yaml`'s `activated_directives: [DIRECTIVE_038]` (or the numeric-hint slug form
   `038-structured-prompt-boundary`, to keep testing the `_is_directive_038` matching-logic variant this
   test's name implies — your call which slug form, but state which in a comment since the test name
   references `directives_yaml` specifically).

**`tests/charter/test_charter_context_spdd_reasons.py`, class `TestParadigmRoundTrip`**:

6. `test_paradigm_in_governance_activates_pack` — currently builds a `GovernanceConfig`/`DoctrineSelectionConfig`
   with `selected_paradigms=["structured-prompt-driven-development"]` and writes it via `save_charter_yaml`
   into `charter.yaml`'s `governance:` section only. Rewrite: ALSO write `.kittify/config.yaml`'s
   `activated_paradigms: [structured-prompt-driven-development]`. Consider renaming/re-commenting the class
   docstring's "governance.yaml" framing to reflect the corrected source if you touch it — optional, not
   required for this WP's pass/fail.

**`tests/charter/test_charter_context_spdd_reasons.py`, class `TestSelectedTacticsRoundTrip`**:

7. `test_tactic_only_selection_round_trips_to_governance_and_activates` — this test already builds a full
   `PackContext(... activated_tactics=frozenset({"reasons-canvas-fill"}) ...)` in step 1 and feeds it
   to `compile_charter`. Its FINAL step writes only `charter.yaml`'s `governance:` section (via
   `save_charter_yaml`) and then asserts `is_spdd_reasons_active(tmp_path) is True`. Rewrite: after writing
   `charter.yaml`, ALSO write `tmp_path/.kittify/config.yaml`'s `activated_tactics: [reasons-canvas-fill]`
   — mirroring the SAME `pack_context.activated_tactics` value already used to compile, so the test stays
   a genuine end-to-end round-trip (compile → markdown → re-extracted governance → NOW ALSO the real
   `activated_*` source the fixed function reads) rather than losing coverage of the compile step. Keep the
   existing `compiled.markdown`/`governance.charter.selected_tactics` assertions unchanged — only the final
   `is_spdd_reasons_active` precondition changes.

**`tests/charter/test_activate_resolves_no_answers_edit.py`, class `TestSpddActivationDoesNotFlip`**:

8. `test_config_sourced_compile_keeps_spdd_active` — this test uses `PackContext.from_config(REPO_ROOT)`
   (THIS repo's own real dogfood `.kittify/`, not `tmp_path`) to compile a charter, then writes the
   compiled governance selection into `tmp_path/.kittify/charter/charter.yaml` and asserts
   `is_spdd_reasons_active(tmp_path) is True`. Rewrite: after writing `charter.yaml`, ALSO write
   `tmp_path/.kittify/config.yaml` mirroring `pack_context.activated_paradigms`/`.activated_directives`/
   `.activated_tactics` (the SAME `pack_context` object already loaded from `REPO_ROOT` in this test) —
   i.e. serialize those three frozensets into `tmp_path`'s own `config.yaml` before the final assertion.
   This keeps the test's real intent (this repo's own dogfood shape does not flip to SPDD-inactive under
   the config-sourced switch) meaningful under the new source of truth.

**Additional bucket-3-shaped case found during THIS WP's own re-verification, beyond FR-010's named 8 —
flag this explicitly in the PR description, do not silently fold it into the count without noting the
discrepancy:**

9. `tests/charter/test_charter_context_spdd_reasons.py`, `TestActivation::test_malformed_governance_raises`
   — writes malformed YAML directly into `.kittify/charter/charter.yaml` and asserts
   `is_spdd_reasons_active(tmp_path)` raises `YAMLError`. Under WP01's rewrite, `is_spdd_reasons_active` no
   longer reads `.kittify/charter/charter.yaml` for this decision at all — it reads `.kittify/config.yaml`
   (or, if a pointer is present, the pointed file). Since this fixture never writes `.kittify/config.yaml`,
   the new function hits the FR-004 absent-config-file path and returns `False` — it does NOT raise. This
   test's *intent* ("malformed activation-source data raises, never silently False/True", FR-005's own
   requirement) is real and survives — but its fixture must be re-pointed to write the malformed YAML into
   `.kittify/config.yaml` (or a `charter:` pointer target) instead of `.kittify/charter/charter.yaml`.
   **Before rewriting it, check whether WP01's own T002 (`test_spdd_reasons_activation_parity.py`) already
   commits an equivalent malformed-config FR-005 regression test** — if it does, this old test becomes
   genuinely redundant (the charter's Test remediation discipline: "stub → delete", but only after judging
   it, not blithely) and you may either (a) re-pin it (rewrite the fixture, keep it) for belt-and-suspenders
   coverage of this specific SPDD-file-family test suite, or (b) delete it with a one-line rationale citing
   WP01's equivalent coverage. Either is acceptable; do NOT silently leave it red or silently delete it
   without a rationale comment in the diff.

### Bucket 2 — assertions that encode the bug itself, flipped

Re-verify against the live files for this WP whether any assertion beyond the bucket-3 methods above
literally asserts "`governance.charter.selected_*`-only IS the activation source" as its point (rather than
merely constructing a fixture that happens to use that section). From this WP's own reading, none of the
non-bucket-3 assertions in these three files make that claim directly — `test_no_charter_returns_false` and
`test_unrelated_directives_returns_false` (both in `TestActivation`) assert `False` for cases that stay
`False` under the new source too (no `.kittify/config.yaml` is written in either fixture, so both hit the
FR-004 pin either way) — these are Bucket 1 (kept), not Bucket 2. If your own re-reading finds a genuine
Bucket-2 case, flip only that specific assertion and state the flip explicitly in the diff/PR description
(the diff itself is the record, per FR-010's own instruction) — do not silently normalize other passing
assertions.

### Bucket 1 — kept, mechanics unchanged

`TestCharterContextInactive`/`TestCharterContextActive` (both in `test_charter_context_spdd_reasons.py`)
gate on `is_spdd_reasons_active` returning `False`/`True` respectively via direct construction (not
`charter.yaml` fixtures) — re-verify they still pass unmodified once WP01 lands; no fixture change expected.
`TestActivateResolvesNoAnswersEdit`/`TestDeactivateDropsNoAnswersEdit` (in
`test_activate_resolves_no_answers_edit.py`) do not call `is_spdd_reasons_active` at all (confirmed by
reading the file) — unaffected, no change. `tests/charter/test_answers_inert_and_org_union.py`'s
`TestThirdLedgerUntouched::test_apply_org_charter_does_not_touch_governance_yaml` (confirmed by reading it
for this WP) asserts `apply_org_charter_to_interview` never writes a separate `.kittify/charter/governance.yaml`
file — it does not call `is_spdd_reasons_active` at all and is entirely orthogonal to WP01's change; its
intent ("answers are inert, only `.kittify/config.yaml` is written") survives untouched, per FR-010's own
explicit example. Every other class in `test_answers_inert_and_org_union.py`
(`TestOrgRequiredPromotedIntoConfig`, `TestOrgRequiredIdFormNormalizedBeforePromotion`,
`TestAnswersInertForActivation`) tests `apply_org_charter_to_interview`/config-promotion machinery, not
`is_spdd_reasons_active` — re-verify by grepping the file for `is_spdd_reasons_active`; if any of these
classes DOES call it (a case this WP's own reading did not find), triage it the same way as the bucket-3
methods above and note the correction to this prompt in the PR description.

### Marker discipline

No marker changes for any of the three files (plan.md section (j), re-confirmed live): `test_charter_context_spdd_reasons.py`
keeps `pytestmark = [pytest.mark.unit]` (collected by `unit-contract-residual`, NOT `fast-tests-charter` —
it lacks the `fast` marker); `test_activate_resolves_no_answers_edit.py` keeps `[pytest.mark.fast,
pytest.mark.doctrine]`; `test_answers_inert_and_org_union.py` keeps `[pytest.mark.unit, pytest.mark.fast,
pytest.mark.doctrine]`. This WP only edits fixture-construction bodies and specific assertions inside
existing test methods — it does not add new test files or change any file's `pytestmark`.

## Subtask T014: Rewrite the 5 `TestActivation`/`TestParadigmRoundTrip`/`TestSelectedTacticsRoundTrip` bucket-3 fixtures (items 1-7 above)

**Purpose**: Commit each rewritten fixture + its (unchanged) assertion as its own red-first change
(C-011): RED against WP01's OLD body, GREEN once WP01's rewrite is available in this workspace.

**Steps**: For each of items 1-7 in Context above, rewrite the fixture-construction to write
`.kittify/config.yaml`'s `activated_*` key(s) as described, run the test against WP01's pre-implementation
`activation.py` (confirm RED — if WP01 has already merged in your workspace, check out its prior commit
temporarily or reason from the git history diff to confirm), then confirm GREEN against WP01's rewritten
body.

**Files**: `tests/charter/test_charter_context_spdd_reasons.py` (~7 method bodies edited)
**Validation**: `pytest tests/charter/test_charter_context_spdd_reasons.py -v` — all green against WP01's
final body.

## Subtask T015: Rewrite `test_config_sourced_compile_keeps_spdd_active` and triage `test_malformed_governance_raises` (items 8-9)

**Purpose**: Complete the bucket-3 rewrite for the file outside `test_charter_context_spdd_reasons.py`, and
resolve the additional case found during this WP's own re-verification.

**Steps**: Apply item 8's fixture rewrite to `test_activate_resolves_no_answers_edit.py`. Apply item 9's
disposition (re-pin or delete-with-rationale) to `test_malformed_governance_raises`.

**Files**: `tests/charter/test_activate_resolves_no_answers_edit.py` (~1 method body edited),
`tests/charter/test_charter_context_spdd_reasons.py` (item 9, 1 method)
**Validation**: `pytest tests/charter/test_activate_resolves_no_answers_edit.py -v`,
`pytest tests/charter/test_charter_context_spdd_reasons.py -k malformed -v`.

## Subtask T016: Confirm Bucket 1/Bucket 2 disposition and re-run the full scoped gate

**Purpose**: Confirm every non-bucket-3 assertion in all three files either stays green unmodified (Bucket
1) or was deliberately flipped with a stated rationale (Bucket 2), and re-run the mission's scoped gate set.

**Steps**:
1. Re-read `test_answers_inert_and_org_union.py`'s four classes to confirm none besides
   `TestThirdLedgerUntouched` calls `is_spdd_reasons_active` — grep for the symbol; if found anywhere else,
   triage it per the bucket-3 pattern and note the correction.
2. Run `pytest tests/charter/ tests/architectural/test_charter_offering_does_not_import_activation.py
   tests/architectural/test_no_dead_symbols.py -q` — diff against the mission's own baseline (captured
   independently by WP01/WP02/WP03 in their workspaces; if this WP runs in a workspace that already has
   WP01 merged, capture your own fresh baseline against WP01's landed state before this WP's own changes,
   so you have a clean before/after for THIS WP's diff specifically).
3. Commit each bucket-3 fixture rewrite as its own red-first commit (or one combined commit covering all 9,
   with the PR description stating each was individually confirmed red-before/green-after) — your call on
   commit granularity, but the red-before/green-after confirmation must be real, not assumed.

**Files**: none new (verification + the item-9 disposition from T015)
**Validation**: Full scoped gate green; diff against baseline shows only this mission's own intentional
flips.

## Definition of Done

- All 9 identified bucket-3 fixtures (8 named by FR-010 + item 9 found during this WP's own
  re-verification) write `.kittify/config.yaml`'s `activated_*` keys and pass against WP01's rewritten
  `is_spdd_reasons_active`.
- Each rewritten fixture was confirmed RED against WP01's pre-rewrite body before being confirmed GREEN.
- No Bucket-1 (kept) test's behavior changed.
- Any genuine Bucket-2 flip found is stated explicitly in the diff/PR description.
- The scoped gate set (`tests/charter/` + the two named architectural files) passes.

## Risks

- **Sequencing risk**: implementing this WP before WP01's implementation commit is available means you
  cannot verify GREEN-after in your own workspace yet — coordinate timing; do not merge/finalize this WP's
  implementation commit until WP01's is actually available to run against.
- **Silent over-fix**: rewriting a fixture's construction mechanism must not also silently change what
  selector is under test (e.g. accidentally testing `DIRECTIVE_010` instead of `DIRECTIVE_038` in item 4) —
  diff each rewritten method against its original to confirm only the write-target changed, not the
  asserted id/paradigm/tactic.
- **Item 9's disposition ambiguity**: deleting `test_malformed_governance_raises` without actually
  confirming WP01's parity test covers the equivalent case would leave a real regression path untested —
  verify, don't assume, before choosing delete over re-pin.

## Reviewer Guidance

- For each of the 9 bucket-3 methods, ask for concrete evidence (a saved RED-run + GREEN-run, or two git
  diffs) that the rewrite was actually red-first, not merely claimed.
- Confirm item 9's disposition (re-pin vs. delete) carries a rationale comment, per the charter's Test
  remediation discipline ("judge the test, not git-blame").
- Confirm no fixture rewrite silently changed the id/paradigm/tactic under test.
- Confirm `tests/charter/test_answers_inert_and_org_union.py`'s three non-`TestThirdLedgerUntouched` classes
  were actually checked for `is_spdd_reasons_active` calls (T016 step 1), not assumed clean.

Implementation command: `spec-kitty agent action implement WP04 --agent claude`
