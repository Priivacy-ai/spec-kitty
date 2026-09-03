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

### Bucket 3 — fixture-construction mechanism rewrite (8 methods named by FR-010, two additional found
during this WP's own re-verification plus the analyze-phase review — 10 total)

All 8 write ONLY `.kittify/charter/charter.yaml`'s `governance:`/`directives:` sections via `save_charter_yaml`
or the local `_write_governance`/`_write_directives` helpers, and never write a `.kittify/config.yaml` at
all — so under WP01's rewrite, every one of them hits the FR-004 absent-config-file path and returns
`False` unconditionally, breaking their `True`-asserting expectations. Each needs its fixture-construction
mechanism rewritten to write `.kittify/config.yaml`'s `activated_paradigms`/`activated_directives`/
`activated_tactics` keys (a `charter:` pointer is optional — direct-on-config.yaml is simplest for these)
AND to null out the specific SPDD-relevant selector in the legacy `governance:`/`directives:` write (see
the Red-first discipline note below — never leave the real id in the legacy write), while preserving the
exact selector under test:

**`tests/charter/test_charter_context_spdd_reasons.py`, class `TestActivation`** (all currently use
`_write_governance`/`_write_directives`, which write only `charter.yaml`):

**Red-first discipline for every item below (binding, re-verified against the live pre-fix
`is_spdd_reasons_active` for this WP): `activation.py`'s OLD body (`_compute_active`/
`_governance_selects_pack`/`_directives_select_pack`, confirmed live) reads ONLY `charter.yaml`'s
`governance:`/`directives:` sections — it never reads `.kittify/config.yaml`. If a rewritten fixture below
leaves the real selector id (the paradigm/tactic/directive under test) anywhere in the legacy
`governance:`/`directives:` write, the OLD body will still return `True` from that legacy content alone,
regardless of what `.kittify/config.yaml` says — the rewritten fixture would then pass on BOTH the OLD and
NEW body, which is not a red-first regression test. Every item below therefore MANDATES nulling out the
specific SPDD-relevant selector from the legacy write (not merely offering it as an option) — leaving
unrelated, non-SPDD content in the same section is fine where a test has other assertions that depend on
it.**

1. `test_paradigm_selected_returns_true` — currently writes `governance:` `selected_paradigms:
   [structured-prompt-driven-development]` via `_write_governance`. Rewrite: change the `_write_governance`
   call to write `selected_paradigms: []` (null out the real id — leaving it there is what would make the
   OLD body pass regardless of the new write) and ALSO write `.kittify/config.yaml` with
   `activated_paradigms: [structured-prompt-driven-development]`. Do NOT leave
   `structured-prompt-driven-development` in the `governance:` write. Assertion
   (`is_spdd_reasons_active(tmp_path) is True`) is UNCHANGED.
2. `test_only_tactic_fill_returns_true` — mirror item 1's pattern exactly: null out `selected_tactics` in
   the `_write_governance` call (write `selected_tactics: []`, not `[reasons-canvas-fill]`) and ALSO write
   `.kittify/config.yaml` with `activated_tactics: [reasons-canvas-fill]`. Do not leave
   `reasons-canvas-fill` in the `governance:` write.
3. `test_only_tactic_review_returns_true` — mirror item 1's pattern exactly: null out `selected_tactics`
   (write `[]`, not `[reasons-canvas-review]`) and ALSO write `.kittify/config.yaml` with
   `activated_tactics: [reasons-canvas-review]`. Do not leave `reasons-canvas-review` in the `governance:`
   write.
4. `test_only_directive_038_returns_true` — mirror item 1's pattern exactly: null out `selected_directives`
   (write `[]`, not `[DIRECTIVE_038]`) and ALSO write `.kittify/config.yaml` with
   `activated_directives: [DIRECTIVE_038]`. Do not leave `DIRECTIVE_038` in the `governance:` write.
5. `test_directive_038_via_directives_yaml` — currently writes DIRECTIVE_038 via `_write_directives`'s
   `directives:` entry-list form (testing the numeric-hint/entry-list matching path against the OLD
   `_directives_select_pack`). Rewrite: change the `_write_directives` call to write an empty
   `directives: []` (or drop the `_write_directives` call entirely) — do not leave the `DIRECTIVE_038`
   entry in `charter.yaml`'s `directives:` section, since `_directives_select_pack` reads exactly that list
   and would return `True` from it alone. ALSO write `.kittify/config.yaml`'s
   `activated_directives: [DIRECTIVE_038]` (or the numeric-hint slug form `038-structured-prompt-boundary`,
   to keep testing the `_is_directive_038` matching-logic variant this test's name implies — your call
   which slug form, but state which in a comment since the test name references `directives_yaml`
   specifically).

**`tests/charter/test_charter_context_spdd_reasons.py`, class `TestParadigmRoundTrip`**:

6. `test_paradigm_in_governance_activates_pack` — currently builds a `GovernanceConfig`/`DoctrineSelectionConfig`
   with `selected_paradigms=["structured-prompt-driven-development"]` and writes it via `save_charter_yaml`
   into `charter.yaml`'s `governance:` section only. Rewrite: change the `DoctrineSelectionConfig` to
   `selected_paradigms=[]` (null out the real id — the OLD body's `_governance_selects_pack` reads exactly
   this field) and ALSO write `.kittify/config.yaml`'s
   `activated_paradigms: [structured-prompt-driven-development]`. Do not leave
   `structured-prompt-driven-development` in the `governance:` write. Consider renaming/re-commenting the
   class docstring's "governance.yaml" framing to reflect the corrected source if you touch it — optional,
   not required for this WP's pass/fail.

**`tests/charter/test_charter_context_spdd_reasons.py`, class `TestSelectedTacticsRoundTrip`**:

7. `test_tactic_only_selection_round_trips_to_governance_and_activates` — this test already builds a full
   `PackContext(... activated_tactics=frozenset({"reasons-canvas-fill"}) ...)` in step 1 and feeds it
   to `compile_charter`. Step 3 (verified live) builds a `governance` object from `compiled.selected_tactics`
   and asserts `"reasons-canvas-fill" in governance.charter.selected_tactics` — KEEP that assertion and the
   earlier `compiled.markdown`/`compiled.selected_tactics` assertions from step 2 exactly as they are; they
   are about the compile round-trip, not about `is_spdd_reasons_active`, and are unaffected by this rewrite.
   Step 4 currently writes that SAME `governance` object (still carrying `reasons-canvas-fill`) into
   `charter.yaml`'s `governance:` section and then asserts `is_spdd_reasons_active(tmp_path) is True`.
   Rewrite step 4 only: write a version of the governance section to `charter.yaml` with `selected_tactics`
   nulled out (`[]`) instead of the real compiled value — leaving `reasons-canvas-fill` in the on-disk
   `governance:` section would make the OLD body's `_governance_selects_pack` return `True` from that
   alone, regardless of `config.yaml`. ALSO write `tmp_path/.kittify/config.yaml`'s
   `activated_tactics: [reasons-canvas-fill]` — mirroring the SAME `pack_context.activated_tactics` value
   already used to compile, so the test stays a genuine end-to-end round-trip (compile → markdown →
   re-extracted governance [step 3's own, untouched assertion] → NOW the real `activated_*` source the
   fixed function actually reads) while staying red-first against the OLD body.

**`tests/charter/test_activate_resolves_no_answers_edit.py`, class `TestSpddActivationDoesNotFlip`**:

8. `test_config_sourced_compile_keeps_spdd_active` — this test uses `PackContext.from_config(REPO_ROOT)`
   (THIS repo's own real dogfood `.kittify/`, not `tmp_path`) to compile a charter, then writes the
   compiled governance selection into `tmp_path/.kittify/charter/charter.yaml` and asserts
   `is_spdd_reasons_active(tmp_path) is True`. The test's own sanity assertion
   (`assert "DIRECTIVE_038" in interview.selected_directives`) checks raw interview data and is UNCHANGED
   by this rewrite. Rewrite the `GovernanceConfig`/`DoctrineSelectionConfig` construction that feeds the
   `charter.yaml` write: null out the four SPDD-relevant selectors specifically —
   `selected_paradigms` with `structured-prompt-driven-development` removed, `selected_tactics` with
   `reasons-canvas-fill`/`reasons-canvas-review` removed, `selected_directives` with `DIRECTIVE_038`
   removed — while leaving any other, unrelated ids from the real dogfood interview/compiled data in
   place unchanged. This repo's own real charter is very likely SPDD-active today (that is the exact bug
   this mission fixes), so leaving those specific ids in the on-disk `governance:` write would let the OLD
   body pass regardless of `config.yaml`'s content. ALSO write `tmp_path/.kittify/config.yaml` mirroring
   `pack_context.activated_paradigms`/`.activated_directives`/`.activated_tactics` (the SAME `pack_context`
   object already loaded from `REPO_ROOT` in this test) — i.e. serialize those three frozensets into
   `tmp_path`'s own `config.yaml` before the final assertion. This keeps the test's real intent (this
   repo's own dogfood shape does not flip to SPDD-inactive under the config-sourced switch) meaningful
   under the new source of truth, while staying genuinely red-first against the OLD body.

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

**A second additional bucket-3 case, found by the analyze-phase review squad (ANALYZE-COVER-001, severity
4) — not among FR-010's named 8, and distinct from item 9 above:**

10. `tests/charter/test_charter_context_spdd_reasons.py`, class `TestCharterContextActive`,
    `test_performance_under_2s_active` — calls `_write_governance(tmp_path, "doctrine:\n  selected_paradigms:\n
    - structured-prompt-driven-development\n  selected_directives: []\n  available_tools: []\n")` (writing
    ONLY `.kittify/charter/charter.yaml`'s `governance:` section — `_write_governance`'s own body, confirmed
    live, never touches `.kittify/config.yaml`), then asserts `is_spdd_reasons_active(tmp_path) is True`
    inside a loop over all 5 `ACTIONS`. Under WP01's FR-004 pin (absent `.kittify/config.yaml` -> `False`),
    this fixture has no `.kittify/config.yaml` at all, so the assertion breaks once WP01's rewrite lands —
    the "Bucket 1 — kept" paragraph below's blanket claim that `TestCharterContextActive` needs "no fixture
    change expected" is false for this one method (re-verified live by reading the class in full: every
    OTHER method in `TestCharterContextActive` genuinely does gate via direct construction and is
    unaffected; this is the sole exception). Mirror items 1-8's exact pattern: rewrite the
    `_write_governance` call to null out `selected_paradigms` (write `selected_paradigms: []`, not
    `[structured-prompt-driven-development]`) and ALSO write `.kittify/config.yaml`'s
    `activated_paradigms: [structured-prompt-driven-development]`. Do not leave
    `structured-prompt-driven-development` in the `governance:`/`doctrine:` write. The assertion
    (`is_spdd_reasons_active(tmp_path) is True`, run once per action in the `ACTIONS` loop) is UNCHANGED.
    Confirm RED-before/GREEN-after per the same blocking-gate discipline as items 1-8.

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
`charter.yaml` fixtures) — **with one confirmed exception**:
`TestCharterContextActive::test_performance_under_2s_active` is bucket-3 item 10 above, not bucket 1 — it
uses a `charter.yaml` fixture (`_write_governance`) rather than direct construction, and its fixture must
be rewritten. Every OTHER method in both classes genuinely gates via direct construction — re-verify they
still pass unmodified once WP01 lands; no fixture change expected for those.
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

## Subtask T014: Rewrite the `TestActivation`/`TestParadigmRoundTrip`/`TestSelectedTacticsRoundTrip`/`TestCharterContextActive` bucket-3 fixtures (items 1-7 and 10 above)

**Purpose**: Commit each rewritten fixture + its (unchanged) assertion as its own red-first change
(C-011): RED against WP01's OLD body, GREEN once WP01's rewrite is available in this workspace.

**Steps**: For each of items 1-7 and 10 in Context above, rewrite the fixture-construction to write
`.kittify/config.yaml`'s `activated_*` key(s) AND null out the specific SPDD-relevant legacy selector as
described (never leave the real id in the legacy `governance:`/`directives:` write), run the test against
WP01's pre-implementation `activation.py` (check out its prior commit temporarily or reason from the git
history diff to confirm), then confirm GREEN against WP01's rewritten body. **This RED-before check is a
blocking gate, not an observational note: if a rewritten fixture is NOT actually RED against WP01's
pre-implementation body, the fixture rewrite is WRONG — a legacy selector was almost certainly left
un-nulled — and must be corrected before this subtask is done.**

**Files**: `tests/charter/test_charter_context_spdd_reasons.py` (~8 method bodies edited)
**Validation**: `pytest tests/charter/test_charter_context_spdd_reasons.py -v` — all green against WP01's
final body.

## Subtask T015: Rewrite `test_config_sourced_compile_keeps_spdd_active` and triage `test_malformed_governance_raises` (items 8-9)

**Purpose**: Complete the bucket-3 rewrite for the file outside `test_charter_context_spdd_reasons.py`, and
resolve the additional case found during this WP's own re-verification.

**Steps**: Apply item 8's fixture rewrite to `test_activate_resolves_no_answers_edit.py`, then confirm RED
against WP01's pre-implementation body before confirming GREEN — the same blocking gate as T014: if item
8's rewritten fixture is not actually RED against the OLD body, a legacy selector was left un-nulled and
the rewrite must be corrected before this subtask is done. Apply item 9's disposition (re-pin or
delete-with-rationale) to `test_malformed_governance_raises`.

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
3. Commit each bucket-3 fixture rewrite as its own red-first commit (or one combined commit covering all 10,
   with the PR description stating each was individually confirmed red-before/green-after) — your call on
   commit granularity, but the red-before/green-after confirmation must be real, not assumed.

**Files**: none new (verification + the item-9 disposition from T015)
**Validation**: Full scoped gate green; diff against baseline shows only this mission's own intentional
flips.

## Definition of Done

- All 10 identified bucket-3 fixtures (8 named by FR-010 + items 9 and 10 found during this WP's own
  re-verification and the analyze-phase review, ANALYZE-COVER-001) write `.kittify/config.yaml`'s
  `activated_*` keys and pass against WP01's rewritten `is_spdd_reasons_active`.
- Each of items 1-8 and 10's rewritten fixtures had its specific SPDD-relevant legacy
  `governance:`/`directives:` selector nulled out (not merely optionally kept), and was confirmed RED
  against WP01's pre-rewrite body before being confirmed GREEN. **This is a blocking gate, not an
  observational note**: a fixture that is GREEN on BOTH the OLD and NEW `is_spdd_reasons_active` body is a
  bug-preserving test, not a red-first regression test, and the fixture rewrite must be corrected (re-null
  the legacy selector) before this WP is considered done — do not mark T014/T015 complete on a fixture only
  confirmed GREEN-after, without a genuine RED-before.
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

- For each of the 10 bucket-3 methods, ask for concrete evidence (a saved RED-run + GREEN-run, or two git
  diffs) that the rewrite was actually red-first, not merely claimed. **Reject the WP if any of items 1-8 or
  10's fixtures was not actually RED against WP01's pre-implementation body** — a fixture that is GREEN on
  both the old and new `is_spdd_reasons_active` body is a bug-preserving test (the OLD-body legacy selector
  was left un-nulled), not a regression test, and must be sent back for correction before this WP can be
  approved.
- For each of items 1-8 and 10, confirm the diff actually shows the legacy `governance:`/`directives:`
  selector nulled out (e.g. `selected_paradigms: []`, not the real id) alongside the new
  `.kittify/config.yaml` write — not merely the `config.yaml` write added on top of an untouched legacy
  write.
- Confirm item 9's disposition (re-pin vs. delete) carries a rationale comment, per the charter's Test
  remediation discipline ("judge the test, not git-blame").
- Confirm no fixture rewrite silently changed the id/paradigm/tactic under test.
- Confirm `tests/charter/test_answers_inert_and_org_union.py`'s three non-`TestThirdLedgerUntouched` classes
  were actually checked for `is_spdd_reasons_active` calls (T016 step 1), not assumed clean.

Implementation command: `spec-kitty agent action implement WP04 --agent claude`
