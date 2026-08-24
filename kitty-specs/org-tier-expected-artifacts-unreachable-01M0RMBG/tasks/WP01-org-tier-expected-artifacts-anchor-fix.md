---
work_package_id: WP01
title: Org-tier expected-artifacts.yaml anchor fix (RED-first, implementation, maintenance, gate verification)
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- NFR-001
- NFR-002
- NFR-003
- C-001
- C-002
- C-003
- C-004
- C-005
- C-006
- C-007
planning_base_branch: fix/org-tier-expected-artifacts-3703
merge_target_branch: fix/org-tier-expected-artifacts-3703
branch_strategy: Planning artifacts for this mission were generated on fix/org-tier-expected-artifacts-3703. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/org-tier-expected-artifacts-3703 unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
history: []
agent_profile: python-pedro
authoritative_surface: src/charter/org_expected_artifacts.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/charter/org_expected_artifacts.py
- tests/charter/test_org_expected_artifacts.py
- tests/charter/test_mission_type_profiles.py
- tests/dossier/test_manifest.py
- tests/dossier/test_rebaseline.py
- tests/dossier/test_indexer.py
role: implementer
tags: []
tracker_refs: []
---

# WP01 — Org-Tier `expected-artifacts.yaml` Anchor Fix

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Fix `resolve_org_expected_artifacts` (`src/charter/org_expected_artifacts.py:82`) so it
anchors an org pack's `expected-artifacts.yaml` override at
`<org_root>/missions/<mission_type>/expected-artifacts.yaml` — matching every sibling
org-tier resolver in `src/specify_cli/runtime/resolver.py` and the built-in layout it
mirrors — instead of the current, wrong `<org_root>/<mission_type>/expected-artifacts.yaml`.
Correct the module/function docstrings to match, and correct the five test files whose
fixture helpers duplicate the old (wrong) path join so the anchor move does not regress
currently-GREEN coverage to RED.

## Context

**Why this WP exists**: An org-pack author who lays out their pack's mission assets the
only way the codebase demonstrates — mirroring `packs/built-in/missions/<type>/` as
`<org_root>/missions/<type>/mission.yaml`, `templates/`, and `expected-artifacts.yaml` — gets
a silently-ignored manifest override today. This is a one-line path-join defect with a
docstring correction and five dependent test-fixture corrections. See `spec.md` (FR-001
through FR-005, NFR-001–003, C-001–C-007, SC-001–005) and `plan.md` (Phasing / Work
Packages, ATDD-First Discipline, Baseline Discipline, Campsite-Clean Scope) for the full
binding detail this WP implements; both files live in this mission's `feature_dir`.

**This is the ONLY work package for this mission.** `plan.md`'s Phasing section describes
five logical steps (campsite-clean: none; RED-first tests; FR-001/002 implementation;
FR-003/004/005 maintenance; gate verification). Those five steps are carried here as six
ordered subtasks (T001–T006) inside **one** WP rather than split across multiple WPs,
because `tests/charter/test_org_expected_artifacts.py` is touched by both the RED-first
step (T001) and the maintenance step (T003) — two narrow WPs both claiming that file would
fail spec-kitty's ownership validator (file-level overlap, not line-level; `codebase-wide`
is the only exemption and does not apply to a narrow six-file fix like this one). One WP
with an internally ordered commit sequence is the correct shape. All six subtasks land as
part of the mission's single PR (per `plan.md`'s "PR Shape" section) — do not open more
than one PR and do not create additional WPs.

**Commit ordering is load-bearing (charter C-011, spec.md NFR-001).** T001's RED-first test
commit MUST be its own commit, landing BEFORE T002's implementation commit. The reviewer
will `git log` this WP's commits and verify RED at the WP's first commit / planning base
(`c76ce3473`) and GREEN at the WP's final commit. Do not squash T001 and T002 together.

**Baseline capture (plan.md "Baseline Discipline") — do this BEFORE T001's edit lands:**
Before touching any file, run the mission's full five-file target test surface once,
unmodified, and record the pass/fail set by test node ID:

```bash
pytest tests/charter/test_org_expected_artifacts.py tests/charter/test_mission_type_profiles.py tests/dossier/test_manifest.py tests/dossier/test_rebaseline.py tests/dossier/test_indexer.py -v
```

This is expected to be entirely GREEN for these five files (main/`c76ce3473` carries ~23
known-red tests + 2 errors elsewhere, tracked as issue #3284 — cite it, do not open a
duplicate; do not assume this narrow five-file surface intersects that baseline without
checking). After each commit in T001–T005, re-run this same command and diff the result
against this step-1 baseline by node ID — a test RED after your commit that was GREEN (or
absent) in the baseline is yours to fix; a test that was already RED in the baseline and
stays RED is pre-existing #3284 territory, left alone.

**Shared test-venv lock (#3283) — capacity signal.** Run every `pytest` invocation for this
WP sequentially against the shared `.venv`; never launch a second concurrent `pytest` run
against it. If an invocation appears to hang, wait for the prior one to finish rather than
firing a second run as a workaround.

**No sibling-fallback (C-002, operator-decided).** The fixed path join checks exactly one
location. Do not add "check new path, fall back to old path" logic — the old location has
zero possible existing consumers (unreachable since #3516 shipped it) and every sibling
org-tier resolver checks exactly one location.

**No validator gate (C-003, operator-decided).** Do not add a `pack_validator` reachability
gate for org-pack `expected-artifacts.yaml` — explicitly out of scope for this mission.

### Subtask T001: RED-first test commit — FR-001/FR-002 pinning + FR-003's new regression case

**Purpose**: Add two test cases to `tests/charter/test_org_expected_artifacts.py` that pin
the *current* (pre-fix) RED behavior as a failing-first commit, per NFR-001:

1. A fixture written at the **corrected** anchor
   (`<org_root>/missions/<mission_type>/expected-artifacts.yaml`) must be found by
   `resolve_org_expected_artifacts` — asserts the return value is the parsed mapping, not
   `None`. This is RED today because the resolver still joins the old path.
2. A fixture written **only** at the **old**, pre-fix anchor
   (`<org_root>/<mission_type>/expected-artifacts.yaml`, no `missions/` segment) must
   resolve to `None`. This is RED today because the old path IS currently found (returns
   the parsed mapping, not `None`) — this is the regression coverage SC-004 measures, and
   no existing test in this file provides it. Per spec.md FR-003, add this case in (or
   immediately adjacent to) `TestResolveOrgExpectedArtifactsEmptyCases`.

**Steps**:
1. Capture the step-1 baseline per the Context section above, before any edit.
2. Add both test methods to `tests/charter/test_org_expected_artifacts.py`. **Do not route
   these two new tests through `_write_org_expected_artifacts`** — that helper still writes
   to the old, pre-fix path at this point in the sequence (T003 fixes it later) and using it
   here would make the two new tests' pass/fail state depend on a helper change that hasn't
   landed yet, breaking the RED-first ordering. Instead:
   - For case 1 (corrected anchor), construct the fixture path directly:
     `org_root / "missions" / mission_type / "expected-artifacts.yaml"`, write valid YAML
     content, then call `resolve_org_expected_artifacts([org_root], mission_type)` and
     assert the result equals the parsed content (not `None`).
   - For case 2 (old anchor only), the existing (still-unmodified) `_write_org_expected_artifacts`
     helper already writes to exactly this old path today — using it here is fine and
     idiomatic; assert `resolve_org_expected_artifacts([org_root], mission_type)` is `None`.
3. Commit this test-only change as its own commit, e.g.:
   `test(charter): pin org-tier expected-artifacts anchor RED states (FR-001/FR-003)`.
4. Confirm mechanical RED: run
   `pytest tests/charter/test_org_expected_artifacts.py -k "<new_test_name_1> or <new_test_name_2>" -v`
   and confirm **both fail** against the still-unmodified `org_expected_artifacts.py`. This
   is the RED half of the RED→GREEN pair the reviewer will independently verify.

**Files**: `tests/charter/test_org_expected_artifacts.py` (+~20–35 lines: two new test
methods; no other file touched in this subtask)

**Validation**: `pytest tests/charter/test_org_expected_artifacts.py -k <new_test_names> -v`
shows exactly 2 failures, both attributable to the still-unfixed resolver (not a typo or
fixture-setup bug — read the failure output to confirm it is the expected
`None`-vs-mapping mismatch, not an error).

### Subtask T002: FR-001 + FR-002 implementation commit

**Purpose**: Land the one-line path-join fix and the paired docstring corrections that turn
T001's two pinned RED tests GREEN.

**Steps**:
1. In `src/charter/org_expected_artifacts.py`, line 82, change:
   `path = org_root / mission_type / _EXPECTED_ARTIFACTS_FILENAME`
   to:
   `path = org_root / "missions" / mission_type / _EXPECTED_ARTIFACTS_FILENAME`
2. Correct `resolve_org_expected_artifacts`'s docstring (currently lines ~51–79) wherever it
   states `<org_root>/<mission_type>/expected-artifacts.yaml` to instead state
   `<org_root>/missions/<mission_type>/expected-artifacts.yaml`.
3. Correct the module docstring (currently lines 1–29) the same way, **and** add one caveat
   sentence to its Contract C-4 citation per `plan.md`'s Contracts section, since that frozen
   historical doc
   (`kitty-specs/up-org-doctrine-consumers-01M05YAB/contracts/org-tier-resolution-contract.md`,
   C-007 — do NOT touch that file) still shows the pre-fix path in its own code sample:
   > Contract C-4's own code sample cites the pre-fix path
   > (`<org_root>/<mission_type>/expected-artifacts.yaml`) — that frozen historical document
   > is not kept in sync with this bugfix; see this module's
   > `resolve_org_expected_artifacts` docstring for the current, correct on-disk path.
4. Do **not** touch `_read_yaml_mapping` — its parsing/warning logic is already correct;
   only the caller's path construction moves.
5. Do **not** add a fallback to the old path (C-002 — see Context section).
6. Commit as its own commit, e.g.:
   `fix(charter): anchor org-tier expected-artifacts.yaml at missions/<type>/ (FR-001, FR-002)`.
7. Re-run T001's two pinned tests — both must now be GREEN:
   `pytest tests/charter/test_org_expected_artifacts.py -k "<new_test_name_1> or <new_test_name_2>" -v`
8. Run the full file: `pytest tests/charter/test_org_expected_artifacts.py -v`. Expect
   several **pre-existing** tests to now fail (their fixtures still target the old path via
   the not-yet-fixed helper/hand-built paths) — this is expected fallout from the anchor
   move and is exactly what T003 fixes next; do not attempt to fix it here.

**Files**: `src/charter/org_expected_artifacts.py` (~4–8 line diff: one path-join line +
docstring corrections; no logic change to `_read_yaml_mapping`)

**Validation**: T001's two new tests both pass; the diff to this file is minimal and touches
only the path join and docstring prose (no signature change to either function).

### Subtask T003: FR-003 maintenance — `tests/charter/test_org_expected_artifacts.py` fixture helper + 5 hand-built paths + docstring

**Purpose**: Update `_write_org_expected_artifacts` (currently lines ~31–43) to write to the
corrected anchor, hand-correct the five malformed-file tests that construct their target
path directly instead of via the helper, and correct the helper's own docstring — restoring
full-file GREEN now that T002's anchor move landed. No RED-first commit required for this
subtask (NFR-001's explicit maintenance-only exclusion) — must be GREEN at this commit.

**Steps**:
1. Update `_write_org_expected_artifacts`'s path construction to insert `"missions"`
   (`org_root / mission_type / "expected-artifacts.yaml"` →
   `org_root / "missions" / mission_type / "expected-artifacts.yaml"`).
2. Correct the helper's docstring (line ~32) to state the corrected path.
3. Hand-correct these five methods in `TestResolveOrgExpectedArtifactsMalformedFile`, each of
   which constructs its target directory directly instead of calling the helper — insert the
   missing `missions/` segment in each:
   - `test_malformed_yaml_file_treated_as_no_match` (line ~160,
     `target_dir = org_root / "software-dev"` → `org_root / "missions" / "software-dev"`)
   - `test_non_mapping_yaml_content_treated_as_no_match` (line ~170, same construction)
   - `test_malformed_yaml_file_logs_a_warning_naming_the_file` (line ~188, same construction)
   - `test_non_mapping_yaml_content_logs_a_warning_naming_the_file` (line ~206, same
     construction)
   - `test_later_malformed_root_does_not_clobber_earlier_good_match` (line ~259,
     `malformed_dir = second_root / "software-dev"` →
     `second_root / "missions" / "software-dev"`)
   Leaving any of these five uncorrected either fails the test outright (first two) or makes
   it pass vacuously — the file is never found rather than found-and-rejected-as-malformed
   (last three) — undermining NFR-001's GREEN-at-final-commit promise for this class.
4. Correct the four pre-fix-path docstrings named in spec.md's "Note (fix round,
   2026-08-24)" that belong to this file: `_write_org_expected_artifacts`'s docstring
   (line ~32) — already done in step 2 above.
5. Optionally (not required): refactor T001's two new tests to route through the now-fixed
   `_write_org_expected_artifacts` helper for the corrected-anchor case, if it reduces
   duplication — do not delete or weaken either assertion.
6. Commit as its own commit, e.g.:
   `test(charter): correct org-tier fixture anchor in test_org_expected_artifacts.py (FR-003)`.

**Files**: `tests/charter/test_org_expected_artifacts.py` (the same file as T001 — this is
why T001 and T003 are subtasks inside one WP rather than two separate WPs; see Context
section)

**Validation**: `pytest tests/charter/test_org_expected_artifacts.py -v` fully GREEN — every
test in the file passes, including T001's two new tests and the full pre-existing matrix
(empty-cases, single-root, declared-order precedence, malformed-file with/without warning,
custom-mission-type-no-builtin-baseline).

### Subtask T004: FR-004 maintenance — `tests/charter/test_mission_type_profiles.py`

**Purpose**: Update the duplicated `_write_org_expected_artifacts` helper (currently lines
~996–1010, consumed by `TestOrgTierExpectedArtifactsThreading` at line ~1014) to the
corrected anchor, with its docstring corrected in step. No RED-first commit required
(maintenance-only per NFR-001) — must be GREEN at this commit.

**Steps**:
1. Locate the locally-duplicated `_write_org_expected_artifacts` helper in this file and
   insert the same `"missions"` segment into its path join as in T003.
2. Correct this helper's docstring (line ~997, named in spec.md's "Note (fix round,
   2026-08-24)") to state the corrected path.
3. Confirm the existing before/after threading-through-`resolve_mission_type_context`
   coverage stays intact: the `required_always` count delta assertion and the
   whole-file-replacement-not-field-merge assertion must both still pass unmodified in
   substance (only the fixture's on-disk location changes).
4. Commit as its own commit, e.g.:
   `test(charter): correct org-tier fixture anchor in test_mission_type_profiles.py (FR-004)`.

**Files**: `tests/charter/test_mission_type_profiles.py` (~2–4 line diff inside the
duplicated helper + its docstring; no other part of this large file is touched)

**Validation**: `pytest tests/charter/test_mission_type_profiles.py -v` fully GREEN,
specifically `TestOrgTierExpectedArtifactsThreading`'s test methods.

### Subtask T005: FR-005 maintenance — three `tests/dossier/` fixture helpers

**Purpose**: Update the three independently-duplicated `_write_org_manifest`-style helpers
in `tests/dossier/` to the corrected anchor, so these end-to-end, unmocked exercises of the
resolver (via `ManifestRegistry.load_manifest`, `rebaseline_snapshot_file`, and
`Indexer.index_feature` respectively) keep passing at GREEN instead of regressing to RED.
No RED-first commit required (maintenance-only per NFR-001) — must be GREEN at this commit.

**Steps**:
1. `tests/dossier/test_manifest.py` (`_write_org_manifest`, currently lines ~516–524,
   consumed by `TestManifestRegistryOrgTier` including
   `test_org_override_delta_through_load_manifest`): insert the `"missions"` segment into
   the path join; correct this helper's docstring (line ~517, named in spec.md's "Note (fix
   round, 2026-08-24)") to state the corrected path.
2. `tests/dossier/test_rebaseline.py` (`_write_org_manifest`, currently lines ~494–500,
   consumed by `TestRebaselineOrgAwareness`'s `test_org_pack_required_artifact_reaches_rebaselined_snapshot`
   and `test_two_pack_chain_second_pack_reaches_rebaseline`): same path-join correction;
   correct this helper's docstring (line ~495, named in the same spec.md note).
3. `tests/dossier/test_indexer.py` (a locally-duplicated `_write_org_manifest` method,
   currently lines ~714–721, consumed by `test_org_override_changes_required_artifact_set`):
   same path-join correction. This helper has **no docstring** (spec.md explicitly notes
   this) — do not add one; only the path join changes.
4. Commit as one commit covering all three files (or three small commits, implementer's
   choice — all land as maintenance, no RED-first requirement), e.g.:
   `test(dossier): correct org-tier fixture anchor across manifest/rebaseline/indexer tests (FR-005)`.

**Files**: `tests/dossier/test_manifest.py`, `tests/dossier/test_rebaseline.py`,
`tests/dossier/test_indexer.py` (~2–4 line diff each, inside the named helper only)

**Validation**: `pytest tests/dossier/test_manifest.py tests/dossier/test_rebaseline.py tests/dossier/test_indexer.py -v`
fully GREEN, specifically confirming `test_org_override_delta_through_load_manifest`,
`test_org_pack_required_artifact_reaches_rebaselined_snapshot`,
`test_two_pack_chain_second_pack_reaches_rebaseline`, and
`test_org_override_changes_required_artifact_set` all pass.

### Subtask T006: Gate verification

**Purpose**: Confirm the whole mission's target test surface is GREEN modulo the #3284
pre-existing baseline, and confirm the locally-checkable CI gates named in `plan.md`'s "The
Gate Set For This Mission" section before treating this WP as CI-ready.

**Steps**:
1. Run the full five-file target surface and diff by node ID against the step-1 baseline
   captured in the Context section:
   ```bash
   pytest tests/charter/test_org_expected_artifacts.py tests/charter/test_mission_type_profiles.py tests/dossier/test_manifest.py tests/dossier/test_rebaseline.py tests/dossier/test_indexer.py -v
   ```
   Confirm: no test is RED that was GREEN (or absent) in the step-1 baseline. Any
   pre-existing #3284 red stays red, untouched, not attributed to this mission.
2. Confirm TID251 banned-API lint is clean on the six touched files:
   `ruff check src tests --select TID251` (path-independent, always runs in CI; expected
   pass-through — the six files use no banned API).
3. Confirm the Contextive glossary freshness check passes (it DOES execute against this
   diff, since `src/charter/**` is in its change-detection path list — not a skip):
   `uv run python scripts/generate_contextive_glossaries.py check`
4. Check diff-coverage locally on the one production file, since `src/charter/*` is in the
   `diff-coverage` job's enforced `critical_paths` list (`--fail-under=90`) — the changed
   lines in `src/charter/org_expected_artifacts.py` (the path join + docstring) must be
   covered at ≥90% by the test suite. The existing and T001-added tests already exercise
   the changed line directly, so this is expected to pass; confirm rather than assume.
5. Optional, not a CI-ready precondition (advisory-only gate): `mypy --strict src/charter`
   for typing hygiene.
6. Confirm the six-file set (C-001) is exactly what changed — `git diff --stat` against the
   WP's base commit should show exactly these six files, nothing more.

**Files**: none new — this subtask is verification-only, no further edits expected unless a
gate surfaces a genuine regression (in which case, fix it inside the six-file set only).

**Validation**: All items above pass or are confirmed pass-through; `git diff --stat`
confirms exactly six files changed.

## Definition of Done

- [ ] T001's two RED-pinning tests exist as their own commit in `tests/charter/test_org_expected_artifacts.py`, and the reviewer can independently reproduce RED at that commit (or at the planning base `c76ce3473`) and GREEN at the WP's final commit.
- [ ] T002's FR-001+FR-002 implementation commit lands as its own commit, strictly after T001's commit and before T003–T005's maintenance commits.
- [ ] T003/T004/T005's maintenance commits land GREEN throughout — no test deleted, weakened, or skipped (SC-003) — and require no RED-first pinning of their own (NFR-001's exclusion).
- [ ] All four docstrings named in spec.md's "Note (fix round, 2026-08-24)" are corrected: `tests/charter/test_org_expected_artifacts.py`'s `_write_org_expected_artifacts`, `tests/charter/test_mission_type_profiles.py`'s `_write_org_expected_artifacts`, `tests/dossier/test_manifest.py`'s `_write_org_manifest`, `tests/dossier/test_rebaseline.py`'s `_write_org_manifest`. `test_indexer.py`'s helper is correctly left without a docstring.
- [ ] The five hand-built malformed-file test paths in `TestResolveOrgExpectedArtifactsMalformedFile` are all corrected (T003's list of five method names).
- [ ] `resolve_org_expected_artifacts`'s and the module's docstrings state the corrected `<org_root>/missions/<mission_type>/expected-artifacts.yaml` path; the module docstring also carries the one-sentence Contract C-4 staleness caveat.
- [ ] No sibling-fallback to the old path exists anywhere in the diff (C-002).
- [ ] No `pack_validator` reachability gate is added (C-003 — out of scope).
- [ ] Full five-file target test surface (`pytest tests/charter/test_org_expected_artifacts.py tests/charter/test_mission_type_profiles.py tests/dossier/test_manifest.py tests/dossier/test_rebaseline.py tests/dossier/test_indexer.py`) is GREEN, modulo #3284's pre-existing baseline red (not attributable to this mission — C-006).
- [ ] TID251 lint clean; Contextive glossary freshness check passes; `src/charter/*` diff-coverage locally confirmed ≥90% on changed lines.
- [ ] Exactly six files changed in the whole WP diff (C-001) — no scope creep into `resolver.py`, `manifest.py`, `mission_type_profiles.py` (the two untouched callers), or the frozen contract doc under `kitty-specs/up-org-doctrine-consumers-01M05YAB/`.
- [ ] Per-subtask completion is recorded via `spec-kitty agent tasks mark-status <Txxx> --status done` for T001–T006 (event-sourced; not a hand-ticked checkbox).

## Risks

- **Coupling T001's RED-first tests to the not-yet-fixed helper.** If T001's two new tests
  are written to call `_write_org_expected_artifacts` for the corrected-anchor case, they
  cannot be RED today (the helper still writes to the old path, so the corrected-anchor
  fixture would never even be written) — this breaks the RED-first proof. Mitigation: T001
  must construct the corrected-anchor fixture path directly/inline, not via the shared
  helper (see T001 Steps, item 2).
- **Missing one of the five hand-built malformed-file path corrections (T003).** Two of the
  five fail outright post-fix if missed; the other three pass vacuously (file never found,
  not found-and-rejected). Mitigation: use spec.md FR-003's exact method/line list as a
  checklist, not memory.
- **Accidentally adding a sibling-fallback** ("check new path, then fall back to old path")
  out of an instinct to be conservative. This violates C-002 (operator-decided) and would
  introduce new, unmatched asymmetry versus every sibling org-tier resolver. Mitigation: the
  path join must have exactly one location checked; no try/except-based dual-path logic.
- **Running pytest concurrently against the shared `.venv`.** Contends with the shared
  test-venv lock (#3283, a capacity signal, not a bug to fix). Mitigation: run all `pytest`
  invocations for this WP sequentially; if one appears to hang, wait for it rather than
  firing a second concurrent run.
- **Misattributing #3284's pre-existing red to this change.** Mitigation: follow the
  Baseline Discipline mechanism in the Context section exactly — capture the step-1 baseline
  before any edit, diff by test node ID after every commit, never treat "some red exists"
  as "my change is broken" without checking against the baseline set first.
- **Widening scope past the six-file set (C-001).** The two production callers
  (`mission_type_profiles.py`, `manifest.py`) and the frozen contract doc each carry their
  own stale-path docstring/prose, per `plan.md`'s Campsite-Clean Scope section — this is a
  known, deliberately deferred gap (a fast-follow issue/mission), not something to fold into
  this WP. Do not touch those files.

## Reviewer Guidance

- **Verify RED→GREEN mechanically, not by reading code.** Check out (or `git stash`) the WP
  at T001's commit and confirm both new tests fail via
  `pytest tests/charter/test_org_expected_artifacts.py -k "<new_test_names>" -v`; then check
  the WP's final commit and confirm both pass. This mirrors the charter's C-011 discipline
  and `plan.md`'s ATDD-First Discipline section verbatim.
- **Confirm commit ordering**: `git log` for this WP's branch should show the RED-first test
  commit (T001) strictly before the FR-001/FR-002 implementation commit (T002), which
  precedes the maintenance commits (T003–T005).
- **Confirm the six-file set is exact** (C-001): `git diff --stat` against the WP's base
  should list exactly `src/charter/org_expected_artifacts.py`,
  `tests/charter/test_org_expected_artifacts.py`,
  `tests/charter/test_mission_type_profiles.py`, `tests/dossier/test_manifest.py`,
  `tests/dossier/test_rebaseline.py`, `tests/dossier/test_indexer.py` — nothing more.
- **Confirm no sibling-fallback (C-002)** was added to the path join in
  `src/charter/org_expected_artifacts.py` — exactly one location should be checked.
- **Confirm no validator gate (C-003)** was added anywhere in the diff.
- **Confirm SC-004's regression case exists as its own, clearly-named test** (fixture only
  at the old anchor → `None` post-fix), not silently folded into an unrelated existing test.
- **Confirm all four docstring corrections** named in spec.md's "Note (fix round,
  2026-08-24)" landed, and that `test_indexer.py`'s helper correctly has no docstring added.
- **Run the full five-file target surface** yourself and confirm GREEN modulo #3284 — do not
  accept "we ran the tests" as a bare claim; the invocation is named in T006 and in
  `plan.md`'s SC-003.
- **Terminology canon (C-004)**: confirm no `feature*` naming was introduced anywhere in the
  diff — expected to have no practical effect here, but worth a quick grep.

Implementation command: `spec-kitty agent action implement WP01 --agent claude`
