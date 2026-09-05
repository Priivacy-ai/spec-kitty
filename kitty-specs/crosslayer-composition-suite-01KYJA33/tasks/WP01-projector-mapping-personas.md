---
work_package_id: WP01
title: Profile-to-Soul.md projector, mapping doc, committed personas
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- C-002
planning_base_branch: kitty/mission-crosslayer-composition-suite
merge_target_branch: kitty/mission-crosslayer-composition-suite
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-crosslayer-composition-suite. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-crosslayer-composition-suite unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-crosslayer-composition-suite-01KYJA33
base_commit: 230ae7f0be81083f98bd80d1ffaed8bd577bffe6
created_at: '2026-07-27T20:31:41.914275+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
agent: claude
history:
- timestamp: '2026-07-27T19:45:23Z'
  event: created
  by: /spec-kitty.tasks-outline (planner-priti)
agent_profile: python-pedro
authoritative_surface: conformance/tools/
create_intent:
- conformance/tools/profile2soul.py
- conformance/tools/PROJECTION.md
- conformance/crosslayer/personas/architect-alphonso.Soul.md
- conformance/crosslayer/personas/reviewer-renata.Soul.md
- conformance/scripts/check-persona-drift.sh
- tests/conformance/test_profile2soul.py
- tests/conformance/__init__.py
- tests/cross_cutting/test_crosslayer_wp01_persona_rfc1_conformance.py
execution_mode: code_change
model: ''
owned_files:
- conformance/tools/profile2soul.py
- conformance/tools/PROJECTION.md
- conformance/crosslayer/personas/architect-alphonso.Soul.md
- conformance/crosslayer/personas/reviewer-renata.Soul.md
- conformance/scripts/check-persona-drift.sh
- tests/conformance/test_profile2soul.py
- tests/conformance/__init__.py
- tests/cross_cutting/test_crosslayer_wp01_persona_rfc1_conformance.py
role: implementer
tags: []
tracker_refs: []
---

# WP01 — Profile-to-Soul.md projector, mapping doc, committed personas

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the
frontmatter, and behave according to its guidance before parsing the rest of
this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the
best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Build the deterministic `*.agent.yaml → Soul.md` projector
(`conformance/tools/profile2soul.py`), document its field mapping and
fidelity-loss table (`conformance/tools/PROJECTION.md`), commit the two
personas this mission needs (`architect-alphonso.Soul.md`,
`reviewer-renata.Soul.md`) under `conformance/crosslayer/personas/`, and give
that drift check its own committed, lane-a-owned script
(`conformance/scripts/check-persona-drift.sh`) rather than leaving it as an
inline command only lane-b could fix.

This mission's own artifact — the projector — is, by D1's own words, "the
programme's least-principled artifact": it fabricates RFC-1 fields
(`voice`, `interaction`, `locale`, the object `composition`/
`profile_overrides`/`extensions` blocks, the `profiles` list, and the
`values`/`safety` blocks) that are never graded
(C-003) and never seen by `contradiction-lint.ts` (verified directly against
muster's source, see Context). Do not let that fabrication leak into any
check's stated reason for passing or failing.

## Context (read first)

- Spec: `kitty-specs/crosslayer-composition-suite-01KYJA33/spec.md`
  — FR-001, FR-002, FR-003; Edge Cases ("Fabricated-field grading leakage",
  "Projector regeneration drift"); Dependencies & Assumptions' "Lane
  isolation" bullet (post-plan-review corrected form) and the "Citation
  pinning" bullet.
- Plan: `kitty-specs/crosslayer-composition-suite-01KYJA33/plan.md`
  — IC-01 (this WP's source concern, including the hazard-3 restructuring
  that gives FR-003 its own script instead of an inline-only command);
  IC-00 ("dissolved, not resolved" — read this in full: it is why lane-b
  (WP02) does **not** need this WP's literal projector output to start or
  finish its own work, only the two filenames below).

**Verified independently before this task file was written** (do not take the
plan's claim on faith — it was re-checked against muster's actual source at
the pinned commit `624edd6dddedb86fb89f13084510f02b5a2c7d25`):
`resolvePersonaLayer` (`composition.ts:281-320`) returns only
`personaDoc.body.trim()` into `layerTexts`; `contradiction-lint.ts`'s own
docstring states plainly "C-003: Lint runs on resolved.layerTexts — never raw
fixture files," and `extractClauses`/`analyseLayerPair` operate exclusively
on that map. RFC-1 front-matter (the fabricated fields this WP invents) is
only ever consulted, structurally, by `resolvePersonaLayer`'s own RFC-1
strict-mode presence/shape check — never by the lint. This is why this WP's
correctness is judged on its body-text mapping (FR-001) and its committed
persona files being real and regenerate-clean (FR-003), not on inventing
"the right" fabricated values — there is no such thing; C-003 forbids citing
them as evidence either way.

**The one thing lane-b (WP02) actually depends on from this WP**: the exact
committed filenames — `conformance/crosslayer/personas/architect-alphonso.Soul.md`
and `conformance/crosslayer/personas/reviewer-renata.Soul.md` — must match
byte-for-byte as *paths* (not content) what WP02's `manifest.yaml`/case files
declare as `fixturePath`. WP02 does not read this WP's output to do its own
work (lanes are parallel, no shared pre-step); it only needs the filenames to
agree. Do not rename these two files after committing them without checking
whether WP02 has already merged.

**DIR-012 status, checked, not assumed**: this mission's seed is GitHub issue
`MOES-Media/spec-kitty#26`. `gh issue view 26 --repo MOES-Media/spec-kitty
--json assignees` was checked while authoring this task file and returned
**zero assignees** (unlike M1's seed ticket `MOES-Media/spec-kitty#22`,
cited here as precedent only, which was already assigned when
that mission's WP01 was authored). This is a real, outstanding gate — T001
below is not a formality here.

## Subtasks

### T001 — Satisfy DIR-012 (tracker issue assigned to HiC)

**Purpose**: Charter gate DIR-012 requires the tracker-backed seed issue to be
assigned to the Human-in-Charge before implementation starts on this
mission's first work package. Unlike M1's precedent, this is **not**
already satisfied.

**Steps**:
1. Run `gh issue view 26 --repo MOES-Media/spec-kitty --json assignees` and
   confirm at least one assignee is present. If it still returns zero
   assignees, assign the issue to the Human-in-Charge
   (`gh issue edit 26 --repo MOES-Media/spec-kitty --add-assignee <HiC-login>`)
   before proceeding.
2. Record the confirmation (assignee login, timestamp, and whether it was
   already assigned or assigned by this step) as a one-line work-log entry.
   Do not proceed to T002 until this is recorded.

**Files**: none (verification/administrative only).
**Validation**: the work log contains an explicit DIR-012 confirmation line
naming a real assignee login.

---

### T002 — Author `conformance/tools/profile2soul.py` (FR-001)

**Purpose**: Deterministic, byte-stable projection from a built-in agent
profile YAML to an RFC-1-conformant `Soul.md`.

**Steps**:
1. Map fields per FR-001's table: `profile-id → id`, `name → name`,
   `initialization-declaration` + `purpose` + `description` +
   `specialization.primary-focus` + `specialization.avoidance-boundary` →
   body sections (the profile's own boundary statement is instructional
   content — carry it, do not drop it).
2. Fabricate the required-but-absent RFC-1 keys from a frozen, in-script
   defaults table this task authors: `locale`; an **object** `composition`
   block (`extends`/`mixins`/`merge_policy`); a `profiles` list that must
   include `"default"` (§9); an **object** `profile_overrides`; an
   **object** `values` block (required `priorities`); four `voice` 0–100
   integers plus a required `formatting` enum; four `interaction` enums; a
   `safety` block (three required enums:
   `refusal_style`/`privacy`/`speculation`); and an **object**
   `extensions`. Document the table's values in `PROJECTION.md` (T003) — do
   not invent new values later without updating both files together.
   **Corrected at the accept gate (2026-07-31)**: this step previously read
   "empty `composition`/`profiles`/`profile_overrides`/`extensions`
   **lists**" and omitted `values`/`safety`/`voice.formatting` entirely —
   the same wrong shape spec.md's FR-001 row already corrected against
   muster's real RFC-1 Appendix E/§9 schema (see spec.md's "FR-001 —
   fabricated-defaults shape corrected against muster's real parser"
   subsection). The implementation shipped the correct shape; only this
   instruction text had been left stale.
3. Emit a header comment recording `generated: true` plus a source-profile
   content hash (this is also C-003's textual-audit anchor — the corrected
   exclusion pattern reviewers use, `^#.*generated:\s*true`, depends on this
   exact shape; do not vary it).
4. Use Python stdlib only (no new runtime dependency) per plan.md's Technical
   Context — if `*.agent.yaml` parsing needs a YAML library, reuse whatever
   this fork already vendors for agent-profile parsing rather than adding
   one.
5. No wall-clock timestamps, no unordered dict/set iteration anywhere in the
   output path — this is the determinism property T006 falsifies directly.

**Files**: `conformance/tools/profile2soul.py` (new).
**Validation**: covered by T006 (real execution, both directions).

---

### T003 — Author `conformance/tools/PROJECTION.md` (FR-002)

**Purpose**: Document the field mapping, the fabricated-defaults table, and a
fidelity-loss table naming exactly what the projection cannot carry.

**Steps**:
1. Write the field-mapping section matching T002's actual mapping.
2. Write the fabricated-defaults table (the frozen values T002 uses).
3. Write a `## Fidelity Loss` section naming fields the projection
   structurally cannot carry because no RFC-1 key exists for them:
   `capabilities`, `routing-priority`, `context-sources`,
   `directive-references`, `tactic-references`. **Do not** list
   `purpose`, `initialization-declaration`, `description`, or
   `specialization.*` here — those fields *are* carried (T002's mapping),
   and FR-002's own corrected verification command (T006) specifically
   checks that `initialization-declaration` is absent from this section,
   using the post-spec-corrected assertion form (see T006 — the old
   `grep -qv` form was a vacuous check that this mission's own spec.md
   documents catching).

**Files**: `conformance/tools/PROJECTION.md` (new).
**Validation**: covered by T006.

---

### T004 — Generate and commit the two personas (FR-003)

**Purpose**: Commit `architect-alphonso.Soul.md` and `reviewer-renata.Soul.md`
under `conformance/crosslayer/personas/`, projected from this fork's real
built-in profiles.

**Steps**:
1. `python3 conformance/tools/profile2soul.py src/doctrine/agent_profiles/built-in/architect-alphonso.agent.yaml > conformance/crosslayer/personas/architect-alphonso.Soul.md`
2. `python3 conformance/tools/profile2soul.py src/doctrine/agent_profiles/built-in/reviewer-renata.agent.yaml > conformance/crosslayer/personas/reviewer-renata.Soul.md`
3. Confirm the exact filenames above — WP02 (a different lane) declares these
   two paths as `fixturePath` values in its own case files without reading
   this WP's source; a filename mismatch here breaks WP02's manifest
   silently, only surfacing once both lanes are merged.
4. Commit both files now (do not leave them staged only) — WP02 needs the
   *paths* to exist in this WP's own commit history for the eventual merge,
   though (per IC-00's dissolution) it does not need to read their bytes to
   do its own work in the meantime.

**Files**: `conformance/crosslayer/personas/architect-alphonso.Soul.md`,
`conformance/crosslayer/personas/reviewer-renata.Soul.md` (both new,
committed).
**Validation**: both files exist at the exact paths above; `git log` shows
them committed on this WP's lane branch.

---

### T005 — Author `conformance/scripts/check-persona-drift.sh` (hazard-3 restructuring)

**Purpose**: Give FR-003's drift check its own committed, lane-a-owned
script — the same pattern FR-007 gets (`check-sop-extract-drift.sh`, a
different lane's WP) — so the party who owns the checked artifact (this WP)
is also the party who can fix a broken drift check, instead of that logic
living only inline inside WP04's `crosslayer.yml` (a file this WP never
touches).

**Steps**:
1. Write a script that regenerates both personas from their source profiles
   (the same two commands as T004) into a temp location, then
   `git diff --exit-code` compares them against the committed copies under
   `conformance/crosslayer/personas/`.
2. Exit `0` on a clean (no-drift) result, non-zero if either persona differs
   from its regenerated form.
3. WP04's `crosslayer.yml` will call this script as a one-line call site
   (`bash conformance/scripts/check-persona-drift.sh`) — do not require any
   argument or environment variable beyond what a bare invocation from the
   repo root provides.

**Files**: `conformance/scripts/check-persona-drift.sh` (new).
**Validation**: covered by T006.

---

### T006 — Mandatory real-CLI verification (operator directive)

This mission cannot be called done on inspection alone. Run every command
below for real and record the exact observed exit code (and, where
specified, exact text) in the work log.

**Purpose**: Prove FR-001's determinism, FR-002's corrected fidelity-loss
check, and FR-003/T005's drift gate all behave as specified — using the spec's
own exact commands, not paraphrases.

**Steps**:
1. **FR-001 determinism** (verbatim from spec.md):
   ```sh
   python3 conformance/tools/profile2soul.py src/doctrine/agent_profiles/built-in/architect-alphonso.agent.yaml > /tmp/a.md
   python3 conformance/tools/profile2soul.py src/doctrine/agent_profiles/built-in/architect-alphonso.agent.yaml > /tmp/b.md
   diff /tmp/a.md /tmp/b.md
   ```
   Expect exit **0**. **Falsification** (must be observed, not merely
   asserted possible): make a *local, uncommitted* copy of the projector,
   inject one non-canonicalized/unstable source into it (a
   `time.time_ns()` line, or unordered dict iteration), rerun the identical
   two-step comparison against the modified copy — `diff` must exit **1**.
   Record both exit codes. Discard the modified copy afterward; it must
   never be committed.
2. **FR-002 fidelity-loss check** (verbatim, corrected H1 form):
   ```sh
   grep -A20 "^## Fidelity Loss" conformance/tools/PROJECTION.md | grep -q "capabilities" && \
   grep -A20 "^## Fidelity Loss" conformance/tools/PROJECTION.md | grep -q "routing-priority" && \
   ! grep -A20 "^## Fidelity Loss" conformance/tools/PROJECTION.md | grep -q "initialization-declaration"
   ```
   Expect exit **0**. **Falsification**: temporarily edit a local copy of
   `PROJECTION.md` so its Fidelity Loss section also lists
   `initialization-declaration` alongside `capabilities`/`routing-priority`,
   rerun the identical command against that copy — expect exit **1**. Do not
   use the old `grep -qv "initialization-declaration"` form; the spec
   documents it as a vacuous pass (exits 0 whenever *any* other line in the
   20-line window fails to match, regardless of whether the target string is
   present) — do not reintroduce it.
3. **FR-003 drift gate, both directions**:
   ```sh
   bash conformance/scripts/check-persona-drift.sh
   ```
   Expect exit **0** on a clean tree. **Falsification**: hand-edit one byte
   of one committed persona file, rerun — expect exit **1**; then restore the
   file exactly and confirm `git diff --exit-code
   conformance/crosslayer/personas/` shows a clean tree again. Paste the
   `git diff` output captured immediately after the hand-edit (before
   restoring) into the work log, not just the restored-clean confirmation —
   a restored-clean diff alone does not prove the falsification direction was
   actually exercised.

**Files**: none new — this subtask exercises T002–T005's outputs only.
**Validation**: all exit codes above (six total: 1 pass + 1 fail for each of
three checks) recorded verbatim in the work log; the FR-002 falsification's
edited-section text and the FR-003 falsification's mid-test `git diff` output
both quoted, not just described.

---

### T007 — WP01 verification gate (Definition of Done gate + per-lane C-002)

**Steps** (run in order):
```bash
git diff --stat                                   # ONLY the eight owned_files entries changed
git diff --stat src/doctrine/                     # MUST show no changes — read-only input, never edited
git diff --stat .github/                          # MUST show no changes — not this WP's concern
git diff --name-only <mission-base>...<this-lane-branch> > /tmp/wp01-c002-diff.txt
if grep -qx "conformance/README.md" /tmp/wp01-c002-diff.txt; then echo "C-002 violation"; exit 1; fi
! (grep -vE '^(conformance|kitty-specs|tests)/' /tmp/wp01-c002-diff.txt | grep -q .)
```
The last two lines are this WP's **per-lane C-002 check** (spec.md's C-002
verification command, scoped to `<mission-base>...<this-lane-branch>` instead
of `main...HEAD` — the cross-lane assembled-diff run happens again later, at
mission review, as the backstop; this per-lane run is this WP's own
responsibility and must pass before requesting review). Substitute this WP's
actual base commit and lane branch name once the lane worktree is allocated.

**Allow-list widened to include `tests/` (HIGH-2 remediation, post-review)**:
`pytest.ini` sets `testpaths = tests`, so any collected unit test for this
WP's own artifact must live under `tests/`, not `conformance/`. The original
allow-list (`conformance/`, `kitty-specs/`) trips a false C-002 violation on
exactly that path. This is a task-file defect, not a charter conflict — see
this WP's Activity Log for the full ruling (C-011 is binding; DIR-0xx
directives, including the plan's now-superseded "must ship both" framing,
are all `severity: warn`). The allow-list now excludes `^(conformance|kitty-specs|tests)/`
instead of just the first two.

## Definition of Done

- [ ] DIR-012 satisfied and recorded (T001), including the assignee login,
      before T002 began
- [ ] `profile2soul.py` maps every field FR-001 names, fabricates the six
      RFC-1 key groups from a frozen, documented table, and emits the
      `generated: true` + source-hash header comment in the exact shape
      C-003's audit pattern expects
- [ ] `PROJECTION.md` documents the mapping, the fabricated-defaults table,
      and a Fidelity Loss section that names the five structurally-dropped
      fields and omits every carried field
- [ ] Both personas committed at the exact required paths
- [ ] `check-persona-drift.sh` exists, is lane-a-owned, and is a thin
      one-line call site away from WP04's `crosslayer.yml`
- [ ] `tests/conformance/test_profile2soul.py` covers determinism, the field
      mapping, `_require` raising on a missing field, the fabricated-defaults
      table matching `PROJECTION.md`, and the `generated: true` header shape
      (HIGH-2 remediation; documented one-time C-011 ordering deviation — see
      Activity Log)
- [ ] All of T006's six real exit codes recorded verbatim in the work log,
      including both falsification directions' actual observed output (not
      "should fail" — the real command output)
- [ ] No file outside `owned_files` modified (eight entries; routed, not
      merely located — see Activity Log's round-3 note on why "under `tests/`"
      alone was never sufficient); `src/doctrine/**` and `.github/**` untouched
- [ ] Per-lane C-002 check (T007) passes against this WP's own lane diff

## Risks

- **Filename mismatch with WP02**: this is one of five path-only couplings
  across this mission's task files (M-3 post-tasks-review finding, spec.md
  Dependencies & Assumptions — this pair is no longer the only one named).
  If either persona filename changes after WP02 has already authored its
  case files against the original names, WP02's manifest silently breaks
  only once both lanes are merged. Communicate any filename change
  immediately if WP02 is concurrently in progress.
- **Fabricated-field leakage (C-003)**: it is tempting to describe *why* a
  fabricated `voice`/`interaction` value was chosen in `PROJECTION.md`'s
  prose in a way that reads as grading justification. C-003 forbids citing
  these values as evidence for any pass/fail — keep the defaults table
  purely descriptive (this is what gets fabricated and why the projector
  needs to), never evaluative (this value is why the check passed).
- **DIR-012 was not pre-satisfied for this mission**, unlike M1's precedent —
  T001 is a real gate here, not a formality; do not skip it on the
  assumption it already holds.

## Reviewer guidance

- **Reject if** T001's DIR-012 confirmation names no real assignee.
- **Reject if** any of T006's six exit codes is missing from the work log, or
  if a falsification direction's actual output (not just "expected: 1") is
  absent.
- **Reject if** `PROJECTION.md`'s Fidelity Loss section lists
  `initialization-declaration`, `purpose`, `description`, or
  `specialization.*` — those are carried fields (T002's mapping), and their
  presence here would itself fail T006 step 2's corrected check.
- **Reject if** `check-persona-drift.sh` requires any argument or environment
  variable beyond a bare repo-root invocation — WP04's call site assumes
  none.
- **Reject if** the header comment's `generated: true` shape differs from
  `^#.*generated:\s*true` — C-003's reviewer-facing audit command
  (spec.md) depends on this exact anchor to avoid a false-positive on a
  rubric sentence that happens to contain the word "generated."
- Confirm `git diff --stat` touches exactly the eight `owned_files` entries
  and nothing under `src/doctrine/**` or `.github/**`.

Implementation command: `spec-kitty agent action implement WP01 --agent claude`

## Activity Log

### 2026-07-27 — Remediation of two HIGH review findings (post-implementation)

This entry backfills T001's and T006's required work-log records (HIGH-1),
and records HIGH-2's unit-test remediation, both re-run/re-derived from real
commands against the current lane tree, not from memory.

#### T001 — DIR-012 confirmation

`gh issue view 26 --repo MOES-Media/spec-kitty --json assignees` returned:

```
{"assignees":[{"id":"MDQ6VXNlcjM0Mjg1MjA5","login":"MOES-Media","name":"Jeroen Nouws","databaseId":34285209}],"number":26, ...}
```

**Assignee: `MOES-Media`** (already assigned — not assigned by this step).
This matches M1's `MOES-Media/spec-kitty#22` precedent; DIR-012 is satisfied.

#### T006 — real-CLI verification (all six exit codes, freshly observed)

**1. FR-001 determinism — pass direction**
```
python3 conformance/tools/profile2soul.py .../architect-alphonso.agent.yaml > /tmp/a.md
python3 conformance/tools/profile2soul.py .../architect-alphonso.agent.yaml > /tmp/b.md
diff /tmp/a.md /tmp/b.md
```
`diff` exit **0**.

**2. FR-001 determinism — falsification direction**
A throwaway copy of `profile2soul.py` had `import time` added and
`_content_hash`'s digest line changed to
`hashlib.sha256(source_path.read_bytes() + str(time.time_ns()).encode()).hexdigest()`.
Running the identical two-invocation comparison against this modified copy
(with a 1-second sleep between invocations) produced:
```
1c1
< # generated: true, source-hash: sha256:46d99cda477aca7007541d64acc644b6dc8be2efbfdcf2a670466af89af8b2cf
---
> # generated: true, source-hash: sha256:eea53e7a20c4cf4fdbcdf8b022882d7b17a63184be6d52c21cb000eefa2fae24
```
`diff` exit **1**. The modified copy was discarded (never committed).

**3. FR-002 fidelity-loss check — pass direction**
```
grep -A20 "^## Fidelity Loss" conformance/tools/PROJECTION.md | grep -q "capabilities" && \
grep -A20 "^## Fidelity Loss" conformance/tools/PROJECTION.md | grep -q "routing-priority" && \
! grep -A20 "^## Fidelity Loss" conformance/tools/PROJECTION.md | grep -q "initialization-declaration"
```
Combined exit **0**.

**4. FR-002 fidelity-loss check — falsification direction**
A throwaway copy of `PROJECTION.md` had its Fidelity Loss section edited to
also list `initialization-declaration`:
```
## Fidelity Loss
...
- `capabilities` — RFC-1 has no capability-list concept.
- `initialization-declaration` — injected for falsification test.
- `routing-priority` — RFC-1 has no dispatch/routing concept.
...
```
Running the identical command against this copy: combined exit **1**. The
copy was discarded (never committed).

**5. FR-003 drift gate — pass direction**
```
bash conformance/scripts/check-persona-drift.sh
```
Exit **0** on the clean, committed tree.

**6. FR-003 drift gate — falsification direction**
One byte of the committed `architect-alphonso.Soul.md` was hand-edited
(`initiative: reactive` → `initiative: reactivx`). Re-running the drift
script produced:
```
diff --git a/conformance/crosslayer/personas/architect-alphonso.Soul.md b/tmp/tmp.ndTFjnE3bq/architect-alphonso.Soul.md
index 32aaba1fa..68345ec23 100644
--- a/conformance/crosslayer/personas/architect-alphonso.Soul.md
+++ b/tmp/tmp.ndTFjnE3bq/architect-alphonso.Soul.md
@@ -14,7 +14,7 @@ voice:
   directness: 50
   verbosity: 50
 interaction:
-  initiative: reactivx
+  initiative: reactive
   tone: neutral
   pacing: moderate
   feedback_style: direct
DRIFT DETECTED: conformance/crosslayer/personas/architect-alphonso.Soul.md differs from a fresh profile2soul.py regeneration
```
Script exit **1**. The file was then restored exactly
(`git checkout -- conformance/crosslayer/personas/architect-alphonso.Soul.md`);
`git diff --exit-code conformance/crosslayer/personas/` afterward: exit **0**
(clean tree confirmed), and a clean re-run of the drift script: exit **0**.

Summary of all six exit codes: (1) 0, (2) 1, (3) 0, (4) 1, (5) 0, (6) 1 —
all match spec.md's expected polarity.

#### HIGH-2 — unit tests added, C-011 ruling applied

The DIR-005/C-011 conflict originally disclosed in this WP's implementation
was a **task-file defect**, not a genuine directive collision: `pytest.ini`
sets `testpaths = tests`, so a collected test for this WP's own artifact
must live under `tests/`, but T007's original C-002 allow-list only excluded
`conformance/` and `kitty-specs/`, tripping a false violation on
`tests/conformance/`. C-011 (`.kittify/charter/charter.md:504`, binding)
requires red-green-refactor with a failing-first test; every `DIR-0xx` in
`charter.yaml` is `severity: warn`. A warn-level directive amendment cannot
relieve a binding constraint left unsatisfied — the correct fix is widening
the allow-list, not skipping the tests.

**Fix applied** (three edits, this WP's task file):
1. `tests/conformance/test_profile2soul.py` added to `owned_files` and
   `create_intent` (now six entries, was five).
2. T007's C-002 allow-list widened from
   `grep -v '^conformance/' | grep -v '^kitty-specs/'` to
   `grep -vE '^(conformance|kitty-specs|tests)/'`; the DoD bullet and
   reviewer-guidance line updated from "five" to "six" owned files.
3. `tests/conformance/test_profile2soul.py` written, covering: determinism
   (`project()` called twice, byte-identical, both on a synthetic fixture
   and the real `architect-alphonso.agent.yaml`); the FR-001 field mapping
   (every carried field lands in its documented body section verbatim);
   `_require`/`_require_nested` raising `KeyError`/`TypeError` on a missing
   or wrong-typed field; `main`'s exit codes (0/1/2); the `FABRICATED_*`
   constants cross-checked field-by-field against `PROJECTION.md`'s
   Fabricated Defaults table (parsed from the markdown, not hand-copied) so
   the two hand-synced tables cannot silently drift; and the
   `^#.*generated:\s*true` header-shape anchor, both on synthetic fixtures
   and on the two actually-committed persona files.

**C-011 letter, honestly**: the failing-first commit ordering cannot be
reconstructed retroactively — `profile2soul.py`, `PROJECTION.md`, and the
personas were already committed (`b43b5bf26`) before this test module was
authored. This is a **documented one-time deviation**, not a claim that
red→green happened in the original commit sequence. Remaining WPs in this
mission will be held to true failing-first ordering.

**Red/green demonstrated against a throwaway clone** (since the true
history is gone, this substitutes for it):
- Cloned this lane worktree to `/tmp/wp01-redgreen/clone` (local, disposable,
  outside this repo's own worktree set).
- Checked out this WP's `base_commit` (`230ae7f0be81083f98bd80d1ffaed8bd577bffe6`)
  — confirmed `conformance/tools/profile2soul.py` does not exist at that
  commit (`ls`: "No such file or directory").
- Copied `tests/conformance/` (the new test module) into that checkout and
  ran `python3 -m pytest tests/conformance/test_profile2soul.py -q`:
  **RED** — 18 errors (all fixture-setup `FileNotFoundError`, since the
  module under test does not exist at this commit), exit code **1**.
- Checked out this WP's final commit's `conformance/` tree
  (`b43b5bf26`) into the same clone and re-ran the identical test command:
  **GREEN** — 18 passed, exit code **0**.
- Deleted the throwaway clone.

**Quality gate (this lane worktree, current HEAD)**:
- `pytest tests/conformance/test_profile2soul.py -v`: **18 passed**, exit **0**.
- `ruff check conformance/tools/profile2soul.py tests/conformance/test_profile2soul.py`:
  exit **0** ("All checks passed!").
- `ruff format --check` on both files: exit **0** ("2 files already formatted").
- `mypy --strict conformance/tools/profile2soul.py`: exit **0**
  ("Success: no issues found in 1 source file").
- `mypy --strict tests/conformance/test_profile2soul.py`: exit **0**
  ("Success: no issues found in 1 source file").

**T007 re-verification** (widened allow-list, six owned files):
```
git diff --stat                                   # six owned_files entries only
git diff --stat src/doctrine/                     # no changes
git diff --stat .github/                          # no changes
git diff --name-only 230ae7f0be81083f98bd80d1ffaed8bd577bffe6...kitty/mission-crosslayer-composition-suite-01KYJA33-lane-a > /tmp/wp01-c002-diff.txt
grep -qx "conformance/README.md" /tmp/wp01-c002-diff.txt        # not found, no violation
! (grep -vE '^(conformance|kitty-specs|tests)/' /tmp/wp01-c002-diff.txt | grep -q .)
```
Both C-002 lines: exit **0**.

**Correction (MEDIUM-1, next remediation round):** the sentence originally
here claimed `git diff --stat` "touches exactly the six `owned_files`
entries" with nothing else. That was false as written: the lane branch's
real diff against `230ae7f0be81083f98bd80d1ffaed8bd577bffe6` already
included this task file (`kitty-specs/.../tasks/WP01-projector-mapping-personas.md`,
bookkeeping, expected) *and* `tests/conformance/__init__.py` (empty,
undeclared — added by commit `4e82dc5cb`, the same commit that added
`tests/conformance/test_profile2soul.py`, but never listed in
`owned_files`/`create_intent`). Both C-002 allow-list checks above still
pass (`__init__.py` sits under the widened `tests/` prefix), so no
governance rule was broken — but the "six entries, nothing else" claim was
inaccurate at the time it was written. See the MEDIUM-1 remediation entry
below for the corrected count (seven `owned_files` entries) and the
freshly re-run diff.

Commits: test module committed separately (`test(WP01): add unit coverage
for profile2soul.py (HIGH-2 remediation)`) from this task-file amendment
(`chore(WP01): remediate HIGH-1/HIGH-2 findings — work log + C-002
allow-list widening`), per operator instruction, using plain `git add`/
`git commit` (not `spec-kitty spec-commit`/`finalize-tasks`, per fork
issues #35/#36). `git show --stat` verified after each commit landed the
intended files.

### 2026-07-27 — Remediation round 2: MEDIUM-1 (undeclared file) + LOW-1/LOW-2 (cross-check coverage)

Both HIGH findings from the prior round stand as cleared; this entry closes
the remaining MEDIUM and both LOW findings from the second review pass.

#### MEDIUM-1 — undeclared seventh file

Commit `4e82dc5cb` created `tests/conformance/__init__.py` (empty, matches
~195 sibling `__init__.py` files under `tests/` fork-wide) without adding it
to `owned_files`/`create_intent`, making this task file's "touches exactly
the six `owned_files` entries" claims (frontmatter comment, DoD bullet,
reviewer-guidance bullet, and the round-1 Activity Log's T007 summary
sentence) false as written, even though nothing outside the widened
`tests/` allow-list was actually touched.

**Fix applied**:
1. `tests/conformance/__init__.py` added to `owned_files` and
   `create_intent` (both now **seven** entries).
2. The T007 Steps comment, the DoD bullet, and the reviewer-guidance bullet
   updated from "six" to "seven".
3. The round-1 Activity Log's T007 summary sentence corrected in place
   (see the note directly above this entry) rather than left standing —
   HIGH-1 was precisely about work-log claims matching what commands
   produce, so a false claim inside the remediation entry itself could not
   stand.

**Real lane diff, re-run just now** (not restated from the finding —
observed directly against this WP's actual `base_commit` and the current
lane branch, after the LOW-1/LOW-2 code commit below had already landed):

```
$ git diff --name-only 230ae7f0be81083f98bd80d1ffaed8bd577bffe6...kitty/mission-crosslayer-composition-suite-01KYJA33-lane-a
conformance/crosslayer/personas/architect-alphonso.Soul.md
conformance/crosslayer/personas/reviewer-renata.Soul.md
conformance/scripts/check-persona-drift.sh
conformance/tools/PROJECTION.md
conformance/tools/profile2soul.py
kitty-specs/crosslayer-composition-suite-01KYJA33/status.events.jsonl
kitty-specs/crosslayer-composition-suite-01KYJA33/status.json
kitty-specs/crosslayer-composition-suite-01KYJA33/tasks/WP01-projector-mapping-personas.md
tests/conformance/__init__.py
tests/conformance/test_profile2soul.py
```

Ten paths total: the seven `owned_files` entries (five `conformance/`
artifacts + `tests/conformance/__init__.py` + `tests/conformance/test_profile2soul.py`),
plus three `kitty-specs/` bookkeeping paths (this task file, plus
`status.json`/`status.events.jsonl` — spec-kitty's own mission-state
tracking, written by tooling, not by hand, and outside `owned_files` scope
by design). Both per-lane C-002 checks (T007) still pass: no path outside
`^(conformance|kitty-specs|tests)/` appears, and `conformance/README.md` is
not among them.

#### LOW-1 — `safety` fabricated field now covered

`safety: {}` was rendered from a bare string literal in
`_render_front_matter`, with no `FABRICATED_SAFETY` constant — so neither
the `PROJECTION.md` cross-check nor
`test_fabricated_output_matches_frozen_constants` asserted it; a change to
the rendered `safety` block would have passed all 18 (now 19) tests.

**Fix**: added `FABRICATED_SAFETY: str = "{}"` to `profile2soul.py`,
switched `_render_front_matter` to emit it via the constant, and added an
assertion against it in both `test_fabricated_defaults_table_matches_projection_md`
(cross-check against `PROJECTION.md`'s table) and
`test_fabricated_output_matches_frozen_constants` (rendered-output check).

**Proved by mutation, freshly run**:
- Mutated `_render_front_matter` locally to emit `"safety: null\n"` instead
  of `f"safety: {FABRICATED_SAFETY}\n"`.
- `pytest tests/conformance/test_profile2soul.py -v`: **1 failed, 18
  passed**, exit **1** — `test_fabricated_output_matches_frozen_constants`
  failed with
  `assert 'safety: {}' in '...\nsafety: null\nextensions: []\n...'`
  (the mutated render output, quoted verbatim from the actual failure).
- Restored the constant-based render line exactly.
- `pytest tests/conformance/test_profile2soul.py -v`: **19 passed**, exit
  **0** (green again).
- `bash conformance/scripts/check-persona-drift.sh` after the fix (restored
  state, committed): exit **0** — the constant-based render is byte-identical
  to the prior hardcoded literal, so no persona regeneration was needed and
  none of the four other owned files changed (blob-identity confirmed
  below).

Note (not in scope, flagged for transparency): other fabricated fields are
rendered the same bare-literal way `safety` was and have the same latent
gap in the render-output test (though `PROJECTION.md`'s table values for
them are still checked by the cross-check test). Only `safety` was in scope
for this fix; left as-is. **Corrected at the accept gate (2026-07-31)**:
this note previously named those fields as `values: []` and
`extensions: []`. Neither is a shape `profile2soul.py` emits — checked
against the committed projector and personas, it renders `values:` /
`  priorities: []` (a block, not a list) and `extensions: {}` (an object,
via `FABRICATED_EMPTY_OBJECT_FIELDS`). The bare-literal fields that
actually carry this latent gap are `values`' `priorities: []` line,
`composition`'s `extends: []`/`mixins: []` lines, and the literal `{}`
values of `profile_overrides`/`extensions`. The `[]` spellings were a
survival of the pre-fix empty-list shape spec.md's FR-001 row already
corrected; the code was never wrong, only this note.

#### LOW-2 — cross-check made bidirectional

`test_fabricated_defaults_table_matches_projection_md` only looked up each
known constant *inside* the parsed `PROJECTION.md` table — a new row added
to the table with no matching constant would pass every assertion
silently, unlike a rename/value-change/deletion (all three independently
verified to fail by the prior review round).

**Closed** (judged cheap, not brittle): added
`test_fabricated_defaults_table_key_set_matches_constants`, which builds
the expected key set from the module's own constants
(`FABRICATED_VOICE`, `FABRICATED_INTERACTION`, `FABRICATED_EMPTY_LIST_FIELDS`,
plus `soul_spec`/`locale`/`safety`) unioned with the two bare-literal fields
(`values`, `extensions`) that intentionally have no constant, and asserts
it equals `set(documented.keys())`. This is a straightforward set-equality
check derived entirely from existing constants/fields — no per-field
special-casing beyond what the render code already hand-codes — so it
should not need touching again unless a genuinely new fabricated field is
introduced, at which point the test *should* force a decision (add the
field to this set, or explain why not).

#### Quality gate (this lane worktree, current HEAD)

- `pytest tests/conformance/test_profile2soul.py -v`: **19 passed**, exit
  **0**.
- `ruff check conformance/tools/profile2soul.py tests/conformance/test_profile2soul.py`:
  exit **0** ("All checks passed!").
- `ruff format --check` on both files: exit **0** ("2 files already
  formatted").
- `mypy --strict conformance/tools/profile2soul.py`: exit **0** ("Success:
  no issues found in 1 source file").
- `mypy --strict tests/conformance/test_profile2soul.py`: exit **0**
  ("Success: no issues found in 1 source file").

#### Blob-identity confirmation (four unchanged owned files)

Compared each file's git blob hash at `b43b5bf26` (original implementation
commit) against the current lane `HEAD`:

```
conformance/tools/PROJECTION.md:                                  SAME (e027c743a...)
conformance/crosslayer/personas/architect-alphonso.Soul.md:        SAME (68345ec23...)
conformance/crosslayer/personas/reviewer-renata.Soul.md:            SAME (2543ac443...)
conformance/scripts/check-persona-drift.sh:                        SAME (91f3bf809...)
```

`conformance/tools/profile2soul.py`'s blob differs from `b43b5bf26` (as
expected — LOW-1 changed it), but its *behavior* does not: the drift script
re-run above confirms byte-identical regeneration output.

#### Commits

- `e26ec2b46` — `fix(WP01): close LOW-1/LOW-2 review findings on
  fabricated-defaults coverage` (code: `conformance/tools/profile2soul.py`,
  `tests/conformance/test_profile2soul.py`). Plain `git add`/`git commit`
  used (not `spec-kitty spec-commit`/`finalize-tasks`, per fork issues
  #35/#36); `git show --stat` confirmed both intended files landed and
  nothing else.
- This task-file amendment (MEDIUM-1 fix + this Activity Log entry)
  committed separately, also via plain `git add`/`git commit`; `git show
  --stat` confirmed after landing (see commit immediately following this
  one in `git log`).

### 2026-07-31 — Remediation round 3: CHANGES-REQUIRED close-out (HIGH-1 routing gap, MEDIUM-1 owned_files, mission-record sync, FR-001/C-003 root-cause amendment)

A round-3 review found four defects. The RFC-1 fix itself (the projector,
`PROJECTION.md`, the two personas, `check-persona-drift.sh`) was verified
sound and is **not** reopened by this entry — only routing/bookkeeping/spec
text.

#### HIGH-1 — `tests/conformance/test_persona_rfc1_parser_conformance.py` was selected by zero CI gates

The RFC-1-parser regression test added by the RED/GREEN pair
`79de09db1`/`89d68ba49` (both lane-a) carried `pytestmark = [pytest.mark.
integration, pytest.mark.e2e]` but lived under `tests/conformance/`, a path
no CI workflow references on any lane. `unit-contract-residual`
(`.github/workflows/ci-quality.yml`, the whole-tree marker catch-all)
explicitly negates both `integration` and `e2e`; every scoped, path-routed
gate misses `tests/conformance/**`. The repo's own ratchet caught it:

```
tests/architectural/test_gate_coverage.py::test_no_new_orphan_surfaces
AssertionError: 1 test file(s) are selected by ZERO CI gates and are not
in the recorded baseline: tests/conformance/test_persona_rfc1_parser_conformance.py
```

**Fix (lane-a commit `840a132dd`, "fix(WP01): route RFC-1-parser
conformance test through a CI gate (HIGH-1)")**: `git mv` to
`tests/cross_cutting/test_crosslayer_wp01_persona_rfc1_conformance.py` —
where the sibling `tests/cross_cutting/test_crosslayer_wp05_rule_survival_
cases.py` (lane-e) already lives, and which the `e2e-cross-cutting` job
runs directly by path (`tests/e2e/ tests/cross_cutting/`). Markers and
content unchanged; the two cross-references to the old path
(`conformance/tools/PROJECTION.md`, `tests/conformance/test_profile2soul.py`)
were updated to the new one. Not taken: routing `tests/conformance/**`
into a filter group instead — that file (`ci-quality.yml`'s change-detection
filters) is lane-d's owned file; this would have cost a cross-lane
dependency for no benefit over simply living where CI already looks.

**RED/GREEN, re-pinned at the new path** (both real, fresh runs, this
worktree, `tests/architectural/test_gate_coverage.py`):
- RED (lane-a `89d68ba49`, before this fix — content-correct, still
  ungated): `1 failed, 30 passed` — `test_no_new_orphan_surfaces` fails
  naming exactly the one orphan file above (a second, unrelated failure —
  `test_model_fidelity_spotcheck_sharded_next_tier` — appeared in one
  interleaved local run because the file was mid-`git mv` when that run's
  later subprocess-collection step executed; the clean baseline figure
  the original finding cited, `1 failed / 30 passed`, is the real one and
  is what's recorded here).
- GREEN (lane-a `840a132dd`, after this fix): **`31 passed`** — full clean
  run, no failures, `numFailedTests == 0`.
- The moved test itself, re-run directly against the real, offline-cached
  `@garrison-hq/muster@1.1.0` CLI at its new path: `2 passed` (both
  personas), unchanged from `89d68ba49`.

**On T007's DoD wording**: "any collected unit test for this WP's own
artifact must live under `tests/`" was satisfied throughout (the file was
always under `tests/`) and was never sufficient — the property that
actually matters is that the test is *selected by some CI gate*, not
merely that it is located under `tests/`. Recommend this DoD line be
reworded to say so explicitly for future WPs on this mission; not changed
here since editing that clause is outside this remediation's four items.

#### MEDIUM-1 — undeclared eighth file (second occurrence of this exact defect)

Commit `89d68ba49` added `tests/conformance/test_persona_rfc1_parser_
conformance.py` without adding it to `owned_files`/`create_intent` (its
relocated path is added instead, since the file only ever lands in this
task file's frontmatter after HIGH-1's fix). This is the same defect
round 2 already closed once for `tests/conformance/__init__.py`
(`4e82dc5cb`) — recurring on a file this WP itself authored, not merely on
CI/tooling output.

**Fix applied**: `tests/cross_cutting/test_crosslayer_wp01_persona_rfc1_
conformance.py` added to `owned_files`/`create_intent` (both now **eight**
entries, was seven). The T007 Steps comment, the DoD bullet, and the
reviewer-guidance bullet updated from "seven" to "eight".

**Real lane diff, re-run against this WP's actual `base_commit` and lane-a's
current tip**:

```
$ git diff --name-only 230ae7f0be81083f98bd80d1ffaed8bd577bffe6...840a132dd
conformance/crosslayer/personas/architect-alphonso.Soul.md
conformance/crosslayer/personas/reviewer-renata.Soul.md
conformance/scripts/check-persona-drift.sh
conformance/tools/PROJECTION.md
conformance/tools/profile2soul.py
kitty-specs/crosslayer-composition-suite-01KYJA33/status.events.jsonl
kitty-specs/crosslayer-composition-suite-01KYJA33/status.json
kitty-specs/crosslayer-composition-suite-01KYJA33/tasks/WP01-projector-mapping-personas.md
tests/conformance/__init__.py
tests/conformance/test_profile2soul.py
tests/cross_cutting/test_crosslayer_wp01_persona_rfc1_conformance.py
```

Eleven paths total: the eight `owned_files` entries (five `conformance/`
artifacts + `tests/conformance/__init__.py` +
`tests/conformance/test_profile2soul.py` +
`tests/cross_cutting/test_crosslayer_wp01_persona_rfc1_conformance.py`),
plus three `kitty-specs/` bookkeeping paths (this task file, plus
`status.json`/`status.events.jsonl` — spec-kitty's own mission-state
tracking, written by tooling, not by hand, and outside `owned_files` scope
by design). Per-lane C-002 check (T007, allow-list `^(conformance|
kitty-specs|tests)/`) still passes: every path above matches, and
`conformance/README.md` is not among them.

#### Mission record — this remediation was previously invisible

Before this entry, coord/target both stopped at round 2 (2026-07-27), and
lane-a's own `kitty-specs/` tree is (correctly) byte-identical to its merge
base with coord (`git diff --stat b45ffd3bc HEAD -- kitty-specs/` is empty
on lane-a) — merging cannot clobber coord's Activity Log, so lane-a never
carries this task file's edits itself; per this mission's own established
convention (see round 1/round 2's "chore(WP01): revert kitty-specs/ lane
contamination", commit `9bb0df3be`, lane-a), all `kitty-specs/` bookkeeping
for this WP lands only on coord/target, never on a lane commit. This
means, until this entry, nothing anywhere recorded: the HIGH-1
routing defect, the MEDIUM-1 owned-files gap, or that T006's six recorded
exit codes (round-1 entry above) were captured against the *original*,
since-replaced projector/personas (pre-`89d68ba49`) — stale the moment
the RFC-1 fix landed.

#### T006 — real-CLI verification, re-run against the corrected artifact (all six exit codes, freshly observed, this pass)

Re-run for real in lane-a's current tree (post-`89d68ba49`, post-`840a132dd`),
not restated from the round-1 entry above, which was captured against the
original (broken) projector/personas:

1. **FR-001 determinism — pass direction**: `diff` on two independent
   `profile2soul.py` invocations against `architect-alphonso.agent.yaml`:
   exit **0**.
2. **FR-001 determinism — falsification direction**: a throwaway copy of
   `profile2soul.py` had `import time` added and the header's source-hash
   line changed to hash the source bytes plus `str(time.time_ns()).encode()`;
   two invocations one second apart produced two different
   `# generated: true, source-hash: ...` lines: `diff` exit **1**. Copy
   discarded, never committed.
3. **FR-002 fidelity-loss check — pass direction**: the corrected `!`+`-q`
   command against the current `PROJECTION.md`: combined exit **0**.
4. **FR-002 fidelity-loss check — falsification direction**: a throwaway
   copy of `PROJECTION.md` with `initialization-declaration` injected into
   its Fidelity Loss section: combined exit **1**. Copy discarded.
5. **FR-003 drift gate — pass direction**: `bash conformance/scripts/
   check-persona-drift.sh` on the clean, committed tree: exit **0**.
6. **FR-003 drift gate — falsification direction**: one byte of the
   committed `architect-alphonso.Soul.md` hand-edited (`formality: 50` →
   `formality: 51`); re-running the drift script printed the real diff
   (`- formality: 51` / `+ formality: 50`) and `DRIFT DETECTED: ...`, exit
   **1**. The file was restored exactly
   (`git checkout -- conformance/crosslayer/personas/architect-alphonso.Soul.md`);
   `git diff --exit-code conformance/crosslayer/personas/` afterward: exit
   **0** (clean tree confirmed); a clean re-run of the drift script: exit
   **0**.

Summary of all six exit codes, re-observed against the corrected artifact:
(1) 0, (2) 1, (3) 0, (4) 1, (5) 0, (6) 1 — identical polarity to the
round-1 record, now genuinely against the fixed projector/personas rather
than the originals.

#### spec.md amendment (root cause)

FR-001 and C-003 described the six fabricated key groups as **empty
lists** (`composition: []`, `profiles: []`, `profile_overrides: []`,
`extensions: []`) and never mentioned `values`, `safety`, or
`voice.formatting` at all — the actual root cause of why the original
(broken) shape was ever approved: the DoD only ever cross-checked the
deliverable against this mission's own (wrong) FR text, never against
muster's real RFC-1 parser. Amended in the same commit as this entry (see
`spec.md`'s new "FR-001 — fabricated-defaults shape corrected against
muster's real parser (WP01 remediation)" subsection, and the corrected
FR-001/C-003 rows) — full detail lives there, not duplicated here. C-003's
own textual-audit probe had also silently lost one of its four detectors
(`\bprofile_overrides\s*:\s*\[\]` can never match now that the shape is
`{}`) and its recorded verification of "no false positive" on the
legitimate persona was wrong (real exit is `0`, not `1` — pre-existing,
also true at the RED commit, corrected as such rather than as a
regression); both fixed there too, with the generalizable lesson recorded
for M4/M6/M9.

#### Commits (this entry)

- Lane-a `840a132dd` — `fix(WP01): route RFC-1-parser conformance test
  through a CI gate (HIGH-1)` (code: `git mv` + two cross-reference
  updates; `tests/`, `conformance/tools/PROJECTION.md` only).
- This task-file amendment (MEDIUM-1 fix + this Activity Log entry) and
  the `spec.md` amendment, committed together on coord and mirrored
  identically onto target, both via plain `git add`/`git commit` (not
  `spec-kitty spec-commit`/`finalize-tasks`, per fork issues #35/#36);
  `git show --stat` confirmed after landing on each branch.

No state transition attempted — WP01 remains `for_review`; this
programme's reviews run out-of-band per operator instruction.
