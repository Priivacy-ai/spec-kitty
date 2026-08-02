---
work_package_id: WP03
title: SOP policy extract and its own drift gate (lane-b part 2)
dependencies: []
requirement_refs:
- FR-007
- C-002
planning_base_branch: kitty/mission-crosslayer-composition-suite
merge_target_branch: kitty/mission-crosslayer-composition-suite
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-crosslayer-composition-suite. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-crosslayer-composition-suite unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-crosslayer-composition-suite-01KYJA33
base_commit: 9bbed911bb4cc9fa93cef305891895511d6c10c8
created_at: '2026-07-27T20:39:34.660573+00:00'
subtasks:
- T014
- T015
- T016
- T017
- T018
agent: claude
history:
- timestamp: '2026-07-27T19:45:23Z'
  event: created
  by: /spec-kitty.tasks-outline (planner-priti)
agent_profile: implementer-ivan
authoritative_surface: conformance/crosslayer/
create_intent:
- conformance/crosslayer/sop-extract.md
- conformance/scripts/check-sop-extract-drift.sh
- tests/cross_cutting/test_check_sop_extract_drift.py
execution_mode: code_change
model: ''
owned_files:
- conformance/crosslayer/sop-extract.md
- conformance/scripts/check-sop-extract-drift.sh
- tests/cross_cutting/test_check_sop_extract_drift.py
role: implementer
tags: []
tracker_refs: []
---

# WP03 — SOP policy extract and its own drift gate

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the
frontmatter, and behave according to its guidance before parsing the rest of
this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the
best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Author a bounded, committed `AGENTS.md` operating-policy extract
(`conformance/crosslayer/sop-extract.md`, OQ-6 option (b), committed as
**final**, not provisional) with its own drift-check script
(`conformance/scripts/check-sop-extract-drift.sh`), mirroring FR-003's
persona-drift pattern exactly. This WP has no dependency on WP01 or WP02 —
it reads only `AGENTS.md`, a shared, read-only repo-root file neither lane
owns.

## Context (read first)

- Spec: `kitty-specs/crosslayer-composition-suite-01KYJA33/spec.md`
  — FR-007; Edge Cases ("AGENTS.md as SOP slot may swamp small-model context
  (OQ-6)" — `AGENTS.md` is 35,933 bytes, verified via `ls -la AGENTS.md` at
  this mission's base commit); Dependencies & Assumptions' OQ-6 decision
  bullet (option (b), committed as **final** — this WP's extract is not
  gated on the later baseline-degradation spike; author it unconditionally).
- Plan: `kitty-specs/crosslayer-composition-suite-01KYJA33/plan.md`
  — IC-03 (this WP's source concern).

**OQ-6 is settled, not open, for this WP's purposes**: the choice of
*whether* to extract (vs. shipping the whole file, or per-rule minimal SOPs)
is permanently decided in favor of a policy extract. The only thing left open
(a later spike measuring whether extract byte-length correlates with
baseline degradation) informs future tuning only and does not gate this WP —
build the extract and its drift gate now, unconditionally.

## Subtasks

### T014 — Author `conformance/crosslayer/sop-extract.md`

**Purpose**: A bounded subset of `AGENTS.md`'s operating-policy sections,
small enough to sit alongside a persona and skill in a composed context
window without the small-model risk the full 35,933-byte file would pose.

**Steps**:
1. Read `AGENTS.md` at the repo root and identify the operating-policy
   sections relevant to composed cross-layer checking (the sections this
   mission's own rule-survival cases will eventually cite, e.g. sections
   touching direct-push and signing policy — see `rule-survival-045`/`029`'s
   eventual dependency in WP05, blocked on M3).
2. Extract those sections verbatim into `conformance/crosslayer/sop-extract.md`
   — no paraphrasing, since T015's drift script re-extracts by matching
   against the same source sections.
3. Keep the extract's section boundaries stable and documented (e.g. a
   comment naming which `AGENTS.md` headings were extracted) so T015's script
   has an unambiguous, mechanically-repeatable extraction rule, not a
   judgment call re-made by hand each time.

**Files**: `conformance/crosslayer/sop-extract.md` (new).
**Validation**: covered by T016.

---

### T015 — Author `conformance/scripts/check-sop-extract-drift.sh`

**Purpose**: Mirror FR-003's persona-drift pattern exactly for the SOP-extract
side of the composition — without it, OQ-6's choice of a committed extract
(rather than the whole file) would have no equivalent drift protection,
an asymmetry FR-007 exists specifically to close.

**Steps**:
1. Write a script that re-extracts the same source sections from `AGENTS.md`
   (the same mechanical rule T014 documents) and
   `git diff --exit-code`s the result against the committed
   `sop-extract.md`.
2. Exit `0` on a clean tree, non-zero if the extract has drifted from what a
   fresh re-extraction of `AGENTS.md` would produce.
3. WP04's `crosslayer.yml` calls this script as a one-line call site — do not
   require any argument beyond a bare repo-root invocation.

**Files**: `conformance/scripts/check-sop-extract-drift.sh` (new).
**Validation**: covered by T016.

---

### T016 — Mandatory real-CLI verification (operator directive)

**Steps**:
```sh
bash conformance/scripts/check-sop-extract-drift.sh
```
Expect exit **0** on a clean tree. **Falsification**: hand-edit one committed
line of `conformance/crosslayer/sop-extract.md` (never `AGENTS.md` itself —
that file is shared, read-only input), rerun — expect exit **1**; restore the
line exactly and confirm `git diff --exit-code conformance/crosslayer/sop-extract.md`
shows a clean tree again. Paste the mid-test `git diff` output (captured
immediately after the hand-edit, before restoring) into the work log, not
just the restored-clean confirmation.

**Files**: none new.
**Validation**: both exit codes (clean, falsified) recorded verbatim; the
mid-test diff quoted.

---

### T017 — WP03 verification gate (Definition of Done + per-lane C-002)

**Steps** (run in order):
```bash
git diff --stat                                   # ONLY the three owned_files entries changed
git diff --stat AGENTS.md                          # MUST show no changes — shared, read-only input
git diff --name-only <mission-base>...<this-lane-branch> > /tmp/wp03-c002-diff.txt
if grep -qx "conformance/README.md" /tmp/wp03-c002-diff.txt; then echo "C-002 violation"; exit 1; fi
! (grep -vE '^(conformance|kitty-specs|tests)/' /tmp/wp03-c002-diff.txt | grep -v '^\.github/workflows/crosslayer\.yml$' | grep -q .)
```
The allow-list was widened (remediation, C-011 follow-up) from
`conformance/` + `kitty-specs/` to also admit `tests/` — `owned_files`
gained a test path (T018) and this scope gate must not reject it. The last
two lines are this WP's **per-lane C-002 check**, this WP's own
responsibility before requesting review; the cross-lane assembled-diff run
happens again at mission review as the backstop.

---

### T018 — C-011 test: pin the drift gate's observable behavior (remediation)

**Purpose**: The operator ruled C-011 (ATDD-First Discipline, `charter.md:504`)
binding over `charter.yaml`'s `tdd_required: false`. WP03 originally shipped
with no test of its own; this subtask closes that gap.

**Documented one-time deviation from C-011's letter**: the failing-first
commit ordering cannot be reconstructed retroactively — `sop-extract.md` and
`check-sop-extract-drift.sh` were already authored and merged (T014/T015)
before this test was written. The test is landed now, its red/green
demonstrated against a throwaway clone of the pre-implementation commit (see
the Activity Log), rather than fabricating a red-then-green commit history
that did not happen.

**Steps**:
1. Write `tests/cross_cutting/test_check_sop_extract_drift.py`, pinning: a
   clean sandbox exits 0 (twice); a mutated `sop-extract.md` exits 1 *and*
   the mutation survives on disk; a mutated `AGENTS.md` exits 1; the default
   (no-argument) invocation never writes `sop-extract.md` even when
   reporting drift; `--write` regenerates the extract and leaves a
   subsequent default call clean; an unrecognized argument is rejected.
   Runs against a sandboxed copy of the script + its two inputs (never the
   live checkout).
2. Placed under `tests/cross_cutting/` (not a new `tests/conformance/`
   directory) so it is actually collected by a live CI gate
   (`e2e-cross-cutting`'s whole-directory scan) without requiring any edit
   to `.github/workflows/ci-quality.yml`, which this WP does not own.
   Carries `pytest.mark.integration` + `pytest.mark.git_repo` (not `fast` —
   it shells out via `subprocess`, which the repo's own marker-correctness
   architectural guard forbids pairing with `fast`).
3. Commit separately from the Fix 1/Fix 2 remediation commit.

**Files**: `tests/cross_cutting/test_check_sop_extract_drift.py` (new).
**Validation**: `uv run python -m pytest tests/cross_cutting/test_check_sop_extract_drift.py -v`
— all cases pass; count and exit code recorded in the Activity Log.

## Definition of Done

- [ ] `sop-extract.md` committed, containing a bounded, documented subset of
      `AGENTS.md`'s operating-policy sections
- [ ] `check-sop-extract-drift.sh` committed, mirrors FR-003's pattern, exits
      `0` clean / non-zero on drift, both observed for real (T016)
- [ ] `AGENTS.md` itself is untouched by this WP
- [ ] Per-lane C-002 check (T017) passes against this WP's own lane diff
- [ ] No file outside `owned_files` modified
- [ ] C-011 test (T018) committed separately, passes, with a documented
      red/green demonstration or an honest statement of why one wasn't
      cleanly possible

## Risks

- **Paraphrasing instead of verbatim extraction**: if T014's extract does not
  match the source sections character-for-character, T015's script will
  either always report drift (false positive) or never detect real drift
  (false negative) depending on how loosely it re-extracts. Keep extraction
  mechanical and documented.
- **OQ-6 spike confusion**: do not block this WP on the separate,
  later baseline-degradation spike — that spike informs future tuning only,
  per the spec's explicit decision; this extract ships now, unconditionally.

## Reviewer guidance

- **Reject if** `AGENTS.md` itself was edited by this WP.
- **Reject if** T016's falsification direction (mid-test diff) is not quoted
  in the work log.
- **Reject if** the extraction rule is not documented well enough for a
  reviewer to independently confirm the drift script's re-extraction logic
  matches what was actually committed.
- Confirm the per-lane C-002 check (T017) was actually run.
- **Reject if** the default (no-argument) invocation of
  `check-sop-extract-drift.sh` writes to `sop-extract.md` under any
  condition — `--write` must only ever be reachable via the explicit flag.
- **Reject if** the C-011 test (T018) is missing, does not actually run in
  CI (confirm it carries a marker + path a live gate selects), or is not
  committed separately from the Fix 1/Fix 2 remediation commit.

Implementation command: `spec-kitty agent action implement WP03 --agent claude`

## Activity Log

**Remediation pass (2026-07-27, post-review, lane-c).** Three review findings
fixed against `HEAD` (commit `22efcade8`, Fix 2 landed): empty Activity Log
(HIGH), no `--write` remedy for the documented regenerate command (MEDIUM),
and a missing C-011 test (NEW, operator ruling). All commands below were
re-run for real just now, not reconstructed from memory or the commit
message.

### T016 — mandatory real-CLI falsification (re-run, values observed now)

Baseline, clean tree, run twice:
```
$ bash conformance/scripts/check-sop-extract-drift.sh; echo $?
0
$ bash conformance/scripts/check-sop-extract-drift.sh; echo $?
0
```

Falsification (hand-edited line 1 of the committed `sop-extract.md`
in place, from `<!--` to `<!-- DRIFT-TEST-MUTATION-T016`; `AGENTS.md` was
never touched):
```
$ bash conformance/scripts/check-sop-extract-drift.sh; echo $?
diff --git a/.../conformance/crosslayer/sop-extract.md b/tmp/sop-extract-fresh.NUKSuT
index 00585e33a..965db6b0a 100644
--- a/.../conformance/crosslayer/sop-extract.md
+++ b/tmp/sop-extract-fresh.NUKSuT
@@ -1,4 +1,4 @@
-<!-- DRIFT-TEST-MUTATION-T016
+<!--
 SOP policy extract (FR-007, OQ-6 option (b)).
1
```

**Mid-test diff (`git diff -- conformance/crosslayer/sop-extract.md`,
captured immediately after the hand-edit, before restoring):**
```diff
diff --git a/conformance/crosslayer/sop-extract.md b/conformance/crosslayer/sop-extract.md
index 965db6b0a..00585e33a 100644
--- a/conformance/crosslayer/sop-extract.md
+++ b/conformance/crosslayer/sop-extract.md
@@ -1,4 +1,4 @@
-<!--
+<!-- DRIFT-TEST-MUTATION-T016
 SOP policy extract (FR-007, OQ-6 option (b)).
 
 This file is a bounded, verbatim subset of the repo-root AGENTS.md's
```

Restore + hash verification:
```
mutated hash  : 676338c9a68fad680dc1f21387b1085cf0735d2de6a77ac5a23fbeb547f67af8
$ git checkout -- conformance/crosslayer/sop-extract.md
restored hash : 28db7b207b9c1e1a8bda09ef66fdcfa097d21c39072960ea53f9bad54d77aedc  (matches pre-mutation)
$ git diff --exit-code conformance/crosslayer/sop-extract.md; echo $?
0
```

### Additional mutation-position sweep (verify-before-handing-back)

Same clean baseline hash `28db7b207b9c1e1a8bda09ef66fdcfa097d21c39072960ea53f9bad54d77aedc`
each time before mutating.

| Mutation position | Run exit | Mutation present on disk (hash differs)? | Restored hash matches baseline? | Post-restore `git diff --exit-code` |
|---|---|---|---|---|
| First line (header marker) — same edit as T016 above | 1 | yes (`676338c9...`) | yes | 0 |
| Last content line (line 47, "Recovery if origin/main…") | 1 | yes (`d1793369...`) | yes | 0 |
| Single byte, mid-file (byte offset 800, `r`→`R` inside the extraction-rule prose) | 1 | yes (`5412fd06...`) | yes | 0 |

### Fix 2 — `--write` mode, fresh exit codes

```
$ sed -i '1s/.*/<!-- WRITE-MODE-DRIFT-CHECK/' conformance/crosslayer/sop-extract.md
$ bash conformance/scripts/check-sop-extract-drift.sh; echo $?      # default, drifted
1
$ bash conformance/scripts/check-sop-extract-drift.sh --write; echo $?
check-sop-extract-drift: regenerated .../conformance/crosslayer/sop-extract.md from AGENTS.md
0
$ bash conformance/scripts/check-sop-extract-drift.sh; echo $?      # default, post-write
0
$ git diff --exit-code conformance/crosslayer/sop-extract.md; echo $?   # regenerated content == committed content
0
```
Confirms: the default (no-argument) invocation stays read-only and still
detects drift (exit 1) without writing; `--write` regenerates the extract
byte-identical to what the default check would have compared against, and
leaves the gate clean afterward. `--write` is reachable only via the
literal flag — WP04's CI call site (bare invocation) can never trigger it.

### T017 — per-lane C-002 gate (re-run against final commit state)

```
$ git diff --stat                                   # only owned_files entries changed
 conformance/crosslayer/sop-extract.md          |  2 +-
 conformance/scripts/check-sop-extract-drift.sh | 43 ++++++++++++++++++++++++--
 kitty-specs/.../tasks/WP03-sop-extract-drift-gate.md | (Activity Log + T017/T018 doc)
 tests/cross_cutting/test_check_sop_extract_drift.py | (new)
$ git diff --stat AGENTS.md; echo $?
(no output — AGENTS.md untouched)
$ git diff --name-only kitty/mission-crosslayer-composition-suite-01KYJA33...kitty/mission-crosslayer-composition-suite-01KYJA33-lane-c > /tmp/wp03-c002-diff.txt
$ cat /tmp/wp03-c002-diff.txt
conformance/crosslayer/sop-extract.md
conformance/scripts/check-sop-extract-drift.sh
kitty-specs/crosslayer-composition-suite-01KYJA33/tasks/WP03-sop-extract-drift-gate.md
tests/cross_cutting/test_check_sop_extract_drift.py
$ grep -qx "conformance/README.md" /tmp/wp03-c002-diff.txt && echo "C-002 violation"
(no match — no C-002 violation)
$ ! (grep -vE '^(conformance|kitty-specs|tests)/' /tmp/wp03-c002-diff.txt | grep -v '^\.github/workflows/crosslayer\.yml$' | grep -q .); echo $?
0   # PASS — every changed path is under conformance/, kitty-specs/, or tests/
```

### T018 — C-011 test

`tests/cross_cutting/test_check_sop_extract_drift.py`, 6 test functions,
run against a sandboxed copy of the script + `AGENTS.md` + `sop-extract.md`
(never the live checkout):

```
$ uv run python -m pytest tests/cross_cutting/test_check_sop_extract_drift.py -v
tests/cross_cutting/test_check_sop_extract_drift.py::test_clean_sandbox_exits_zero_twice PASSED
tests/cross_cutting/test_check_sop_extract_drift.py::test_mutated_extract_exits_one_and_mutation_survives PASSED
tests/cross_cutting/test_check_sop_extract_drift.py::test_mutated_agents_md_exits_one PASSED
tests/cross_cutting/test_check_sop_extract_drift.py::test_default_invocation_never_writes_extract_even_with_drift PASSED
tests/cross_cutting/test_check_sop_extract_drift.py::test_write_flag_regenerates_and_default_is_then_clean PASSED
tests/cross_cutting/test_check_sop_extract_drift.py::test_unknown_argument_is_rejected PASSED
6 passed in 71.53s
```

Placed under `tests/cross_cutting/` (not a new `tests/conformance/`
directory) and marked `pytest.mark.integration` + `pytest.mark.git_repo` so
it is actually selected by the live `e2e-cross-cutting` CI job without any
edit to `.github/workflows/ci-quality.yml` (out of this WP's `owned_files`
and forbidden by the widened T017 scope gate above). Verified this claim
for real rather than asserting it: ran this repo's own architectural
gate-coverage ratchet
(`tests/architectural/test_gate_coverage.py::test_no_new_orphan_surfaces`)
plus its marker-convention/marker-correctness guards
(`tests/architectural/test_pytest_marker_convention.py`,
`tests/architectural/test_pytest_marker_correctness.py`) against the new
file — all 5 passed (199.31s), confirming the new test is neither a
newly-orphaned (never-runs-in-CI) file nor mismarked (`fast` + `subprocess`,
or a `git`-invoking file missing `git_repo`).

**C-011 letter — documented one-time deviation.** `sop-extract.md` and
`check-sop-extract-drift.sh` (T014/T015) were already authored and merged
before this test was written, so a genuine failing-first commit ordering
cannot be reconstructed retroactively for those two subtasks. Red/green was
still demonstrated where practical, against the actual pre-implementation
state:

```
$ git worktree add --detach /tmp/wp03-pre-impl 9bbed911bb4cc9fa93cef305891895511d6c10c8
Preparing worktree (detached HEAD 9bbed911b)
$ mkdir -p /tmp/wp03-pre-impl/tests/cross_cutting
$ cp tests/cross_cutting/test_check_sop_extract_drift.py /tmp/wp03-pre-impl/tests/cross_cutting/
$ ls /tmp/wp03-pre-impl/conformance/crosslayer   # WP03's deliverables genuinely absent here
ls: cannot access '.../conformance/crosslayer': No such file or directory
$ cd /tmp/wp03-pre-impl && <lane-c-venv>/bin/python -m pytest tests/cross_cutting/test_check_sop_extract_drift.py -v --tb=short
FAILED tests/cross_cutting/test_check_sop_extract_drift.py::test_clean_sandbox_exits_zero_twice
FAILED tests/cross_cutting/test_check_sop_extract_drift.py::test_mutated_extract_exits_one_and_mutation_survives
FAILED tests/cross_cutting/test_check_sop_extract_drift.py::test_mutated_agents_md_exits_one
FAILED tests/cross_cutting/test_check_sop_extract_drift.py::test_default_invocation_never_writes_extract_even_with_drift
FAILED tests/cross_cutting/test_check_sop_extract_drift.py::test_write_flag_regenerates_and_default_is_then_clean
FAILED tests/cross_cutting/test_check_sop_extract_drift.py::test_unknown_argument_is_rejected
6 failed in 75.95s (0:01:15)
  # every failure: FileNotFoundError on conformance/scripts/check-sop-extract-drift.sh
  # (and, transitively, conformance/crosslayer/sop-extract.md) — RED, for the
  # expected reason: the WP03 deliverables do not exist yet at this commit.
$ cd - && git worktree remove --force /tmp/wp03-pre-impl
$ uv run python -m pytest tests/cross_cutting/test_check_sop_extract_drift.py -v   # back at this lane's HEAD
6 passed in 71.53s   # GREEN
```
Genuinely red (all 6 fail, `FileNotFoundError` on the not-yet-existing
script/extract) at the pre-implementation commit, genuinely green at this
lane's final state — the closest honest substitute for a red-then-green
*commit* history that cannot be rewritten after the fact.

### Verification summary

- Gate clean: exit 0, twice, byte-identical (T016 baseline above).
- First-line / last-line / single-byte mutations: exit 1 each, mutation
  hash-verified present, restore hash-verified back to baseline.
- Test suite: `uv run python -m pytest tests/cross_cutting/test_check_sop_extract_drift.py -v`
  → 6 passed, exit 0.
- `git status --porcelain` clean in this lane after the final commit (see
  the WP03 commits on `kitty/mission-crosslayer-composition-suite-01KYJA33-lane-c`).
- Primary checkout (`/home/jeroennouws/dev/spec-kitty-conformance`, branch
  `kitty/mission-crosslayer-composition-suite`) was not switched or
  committed against; its pre-existing uncommitted bookkeeping
  (`meta.json`, `WP01`/`WP03` frontmatter reformatting) was left untouched.

### Post-review remediation — MEDIUM-1 (`--write` silently deletes a
### section on a heading rename) + LOW-1/LOW-2/LOW-4

**Bug, reproduced against the live lane checkout before any fix (AGENTS.md
hash `ba065f47...` restored after):** renamed
`## Branch Protection and CI` → `## Branch Protection and CI Policy` in
`AGENTS.md`.

```
default check (before rename)          exit=0
default check (after rename)           exit=1   drift correctly reported
--write (buggy, pre-fix)               exit=0
  extract: 3141 -> 2241 bytes, 48 -> 38 lines (10 lines deleted, the
  "Branch Protection and CI" section silently gone)
default check (re-run, post-write)     exit=0   GATE NOW REPORTED CLEAN
```

Root cause: `extract_section()`'s `awk` only sets `inside=1` when
`$0 == heading` fires; if it never fires (heading renamed), the function
prints nothing and returns 0. `regenerate()` had no way to distinguish
"heading matched, section legitimately short" from "heading never
matched" and `--write` wrote the truncated result straight over the
committed extract.

**Fix** (`conformance/scripts/check-sop-extract-drift.sh`):
`extract_section()` now tracks a `found` flag inside the `awk` program and
`exit`s 1 in its `END` block when the heading never matched, wrapped in
`if ! awk ...; then echo ... "heading not found" ...; return 1; fi` so the
failure is caught (not tripped by `set -e` mid-condition) and then
propagates loudly with `return 1`. Also hardened `--write` itself: it now
builds `regenerate()`'s output into a `mktemp` scratch file first and only
`mv`s it over `EXTRACT_FILE` on success (previously `regenerate >
"${EXTRACT_FILE}"` truncated the committed file the instant the
redirection opened, before a single byte was produced — so a mid-`
regenerate` failure would have left the committed extract half-overwritten
instead of merely erroring). This mirrors the read-only branch's existing
mktemp+trap pattern.

**Bug reproduced again post-fix, same rename:**

```
default check (after rename)           exit=1   "heading not found in
                                                  .../AGENTS.md: ## Branch
                                                  Protection and CI"
--write (fixed)                        exit=1   same message; extract
                                                  file byte-for-byte
                                                  untouched (size 3141,
                                                  sha256 28db7b20...,
                                                  unchanged before/after)
default check (re-run, post-write attempt) exit=1  same message — never
                                                     reports clean
```

Both the default check and `--write` now fail closed on the same renamed
heading, and a failed `--write` leaves the committed extract completely
untouched rather than half-overwritten.

**Four `--write` states re-verified** on the live checkout after the fix
(unrelated to the rename bug — ordinary drift/repair cycle):
clean/no-args `0`; drifted (`sed`-mutated first line)/no-args `1` with the
mutation still present on disk; drifted/`--write` `0`; post-write/no-args
`0`; `git diff --exit-code` on the regenerated file against the git-tracked
committed content `0` (byte-identical).

**Mutation sweep re-run** (first line, last line, single byte at offset
800) against the real committed `sop-extract.md`, each time from baseline
hash `28db7b207b9c1e1a8bda09ef66fdcfa097d21c39072960ea53f9bad54d77aedc`:
all three exit `1`, mutation present on disk (hash differs — first-line
`676338c9...` matches the T016 record exactly; single-byte `5412fd06...`
matches the WP03 sweep record exactly; last-line uses a different literal
edit than the original sweep so its hash differs from the recorded
`d1793369...` but the mutated-then-restored-then-clean-diff sequence is
identical), restored hash `28db7b20...` (matches baseline) every time,
`git diff --exit-code` clean after each restore.

**LOW-2** — added two tests to
`tests/cross_cutting/test_check_sop_extract_drift.py`:
`test_write_never_modifies_agents_md` (hashes `AGENTS.md` before/after a
`--write` run against a drifted sandbox extract, asserts equality — pins
the property the script's header comment asserts twice) and
`test_write_on_renamed_heading_fails_and_extract_is_untouched` (renames a
pinned heading in the sandbox `AGENTS.md` copy, runs `--write`, asserts
nonzero exit + "heading not found" on stderr + the extract file
byte-for-byte untouched, and that the default no-arg check on the same
renamed heading also fails). Confirmed the heading-rename test fails
(`assert 0 != 0`) against the pre-fix script and passes against the fixed
script; the AGENTS.md-hash test passes against both (it pins an
already-sound neighbouring property, not the defect itself — expected).

**LOW-1** — `test_unknown_argument_is_rejected` now also asserts
`"unknown argument" in result.stderr`, not just `returncode == 1`.

**LOW-4** — left `--help` exiting 1 (fail-closed, prints usage to
stderr) rather than adding a 0-exit help path. One-line reason recorded
inline in the script next to the argument parser: this is a one-flag
internal remediation script, not a general CLI, and `--help` failing
closed is one of the twelve accidental-invocation guards this WP's review
already verified and accepted — making it a documented success path would
be a new, untested behavior change with no required benefit.

**Test suite:** `pytest tests/cross_cutting/test_check_sop_extract_drift.py -v`
→ 8 passed (was 6), exit 0.

**Clean-tree confirmation:** `git status --porcelain` in this lane shows
only the two intentionally-changed files
(`conformance/scripts/check-sop-extract-drift.sh`,
`tests/cross_cutting/test_check_sop_extract_drift.py`); `AGENTS.md` and
`conformance/crosslayer/sop-extract.md` hash-verified restored to their
pre-remediation values throughout. Primary checkout
(`/home/jeroennouws/dev/spec-kitty-conformance`, branch
`kitty/mission-crosslayer-composition-suite`) was not touched.

No state transition performed — WP03 is already `for_review` and this
review round runs out-of-band; recorded here per instruction instead of
attempting `--to for_review` (which would error `Illegal transition`).

- **MEDIUM-1 remediation (`--write`'s `mv` was cross-device, so neither
  atomic nor mode-preserving)**: the `mktemp` scratch file `--write` builds
  its replacement in was created under `${TMPDIR:-/tmp}` (tmpfs, st_dev 44
  in this environment) while `EXTRACT_FILE` lives on the repo's filesystem
  (btrfs, st_dev 43) — a different device, so the closing `mv` always took
  coreutils' cross-device copy-then-unlink fallback instead of a real
  `rename(2)`. Two consequences, both confirmed for real before fixing:
  - **(a) Mode regression on every successful `--write`.** Verified this
    lane's on-disk `conformance/crosslayer/sop-extract.md` was already at
    mode `600` (`git ls-files -s` reports `100644`; `stat` reported `600`;
    `git status` reported clean throughout — git tracks only the
    executable bit, never the full mode, so the regression was invisible
    to git). Restored it to `644` in the fix commit.
  - **(b) Non-atomicity.** Reproduced the exact class of failure the
    reviewer described: ran a bigfile-instrumented copy of the pre-fix
    script's `--write` in the background, polled the destination path at
    high frequency, and `SIGKILL`ed it the instant the destination's size
    changed — left a 3141-byte extract as a ~227MB truncated partial file,
    mode `600`. Confirmed the fixed script cannot reproduce this: the same
    kill-on-first-size-change technique against the fixed script only ever
    observes the destination at its pristine original size or the full
    regenerated size, never partial, across three attempts.
  - **Fix**: `mktemp "${EXTRACT_FILE}.XXXXXX"` (scratch file beside the
    destination, guaranteeing same filesystem, so `mv` is always a true
    same-device `rename(2)` — atomic regardless of file size) plus
    `chmod --reference="${EXTRACT_FILE}" "${WRITE_TMP_FILE}"` before the
    move (needed regardless of filesystem, since even a same-device
    `rename(2)` hands the moved inode's `mktemp`-assigned `0600` straight
    to the destination path). Corrected the adjacent comment, which
    claimed "a failure here leaves EXTRACT_FILE completely untouched" in a
    way that was true for a `regenerate()`/`extract_section` failure but
    previously false for a kill during the `mv` itself; the comment now
    explains the `mv`'s atomicity explicitly rather than leaving it an
    unproven, implicit claim.
  - **Test**: extended `test_write_flag_regenerates_and_default_is_then_clean`
    (`tests/cross_cutting/test_check_sop_extract_drift.py`) to pin the
    extract's mode across a successful `--write`. Watched it fail against
    the pre-fix script first (`AssertionError ... got 0o600`), then pass
    after the fix. Full suite: 8 passed (count unchanged — an existing
    test was extended, not a new one added).
  - Re-ran the T016-style mutation sweep (first-line, last-line,
    single-byte mutations) against the fixed script in a fresh sandbox:
    exit 1 each time, mutation surviving on disk, hash-verified restore
    after each.
  - Ran 20 parallel default-invocation + 20 parallel `--write` invocations
    against a shared sandbox: no stray `sop-extract.md.XXXXXX` scratch
    files survive. Confirmed the `trap ... EXIT` cleanup also fires
    correctly on a normal (non-`SIGKILL`) failure path (a renamed pinned
    heading causing `extract_section` to fail): extract untouched, no
    stray scratch file left. Separately confirmed `SIGKILL` itself bypasses
    the `EXIT` trap (universal bash/OS behavior, not a regression from
    this fix, and consistent with how the truncation bug above was
    demonstrated) — a `kill -9` landing mid-`regenerate()` (before `mv` is
    even reached) can leave one stray scratch file on disk; this is an
    inherent limitation of `SIGKILL` semantics, not something this fix (or
    any trap-based cleanup) can address.
- **LOW-1 (fixed)**: swapped the `AGENTS_FILE` existence guard from `-f` to
  `-r` (`conformance/scripts/check-sop-extract-drift.sh` line ~87), so an
  unreadable-but-present source file (`chmod 000 AGENTS.md`, reproduced and
  confirmed) is now reported as "source file not found or not readable"
  instead of silently falling through to `awk`'s raw permission-denied
  error plus `extract_section`'s misleading "heading not found" fallback
  message. Trade-off accepted: `-r` no longer distinguishes "missing" from
  "present but a directory/unreadable", but the prior `-f` guard didn't
  either for the permission case, and this script's own real-awk-error
  printed immediately above the misdiagnosis already made the defect
  cosmetic — the fix is a clean-message improvement, not a new safety
  property.
- **LOW-2 (recorded, not changed)**: a duplicate `## Branch Protection and
  CI` heading further down `AGENTS.md` is silently ignored by
  `extract_section`'s "first match through the next `---`" rule — policy
  text placed under a second copy of a pinned heading would be invisible
  to both the extract and its drift check. This is an accepted property of
  the settled, mechanical extraction rule (first-occurrence, not
  last-occurrence or all-occurrences), not a defect this WP's scope covers;
  the rule itself is intentionally unchanged.
