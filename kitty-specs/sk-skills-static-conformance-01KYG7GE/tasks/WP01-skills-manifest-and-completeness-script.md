---
work_package_id: WP01
title: Skills manifest, discrimination control, and completeness script
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-005
- FR-007
- C-001
- NFR-002
planning_base_branch: kitty/mission-sk-skills-static-conformance
merge_target_branch: kitty/mission-sk-skills-static-conformance
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-sk-skills-static-conformance. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-sk-skills-static-conformance unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-sk-skills-static-conformance-01KYG7GE
base_commit: bc435635ea38b404cec059b69f9975d1fec0f70e
created_at: '2026-07-26T23:45:47.431261+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
history:
- timestamp: '2026-07-26T23:20:00Z'
  event: created
  by: /spec-kitty.tasks-outline (planner-priti)
agent_profile: node-norris
authoritative_surface: conformance/skills/
create_intent:
- conformance/skills/manifest.yaml
- conformance/skills/control/name-mismatch/SKILL.md
- conformance/scripts/check-manifest-completeness.mjs
execution_mode: code_change
model: ''
owned_files:
- conformance/skills/manifest.yaml
- conformance/skills/control/name-mismatch/SKILL.md
- conformance/scripts/check-manifest-completeness.mjs
role: implementer
tags: []
tracker_refs: []
---

# WP01 — Skills manifest, discrimination control, and completeness script

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the
frontmatter, and behave according to its guidance before parsing the rest of
this prompt.

- **Profile**: `node-norris`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the
best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Author the 54-case skills conformance manifest (53 real skills + 1 rigged
control), the control fixture that backs the 54th case, and the dependency-
free Node script that keeps the manifest's case count honest against the real
`src/doctrine/skills/*` tree. Prove all three work for real against the actual
muster CLI and the actual skill tree, in both the pass and fail direction,
before this WP is considered done.

This is data + one script under `conformance/**` only. No file under
`src/doctrine/**` or any other spec-kitty runtime path is modified (C-001). No
muster or muster-action source is touched.

## Context (read first)

- Spec: `kitty-specs/sk-skills-static-conformance-01KYG7GE/spec.md`
  — FR-001, FR-002, FR-005, FR-007; Acceptance Scenarios 1, 2, 6, 7, 8, 9;
  Edge Cases ("Manifest/skill-set drift", "Control-case regression")
- Plan: `kitty-specs/sk-skills-static-conformance-01KYG7GE/plan.md`
  — IC-01, IC-02, IC-03; Verification Strategy steps 1–3
- Research: `kitty-specs/sk-skills-static-conformance-01KYG7GE/research.md`
  — §3 (manifest case shape), §4 (control design), §6 (completeness script
  design, directory-scan-by-type, line-based parsing rationale)
- Data model: `kitty-specs/sk-skills-static-conformance-01KYG7GE/data-model.md`
  — `SkillsManifest`, `StaticCase`, `ControlCase`, `CompletenessCheckResult`
- Quickstart (= mandatory verification procedure):
  `kitty-specs/sk-skills-static-conformance-01KYG7GE/quickstart.md` §1, §2, §3
- Contracts:
  `kitty-specs/sk-skills-static-conformance-01KYG7GE/contracts/skills-manifest-case.schema.json`
  (read the `"$comment"` field — it is the normative raw-text authoring
  convention this WP's manifest and script must both honor)
  `kitty-specs/sk-skills-static-conformance-01KYG7GE/contracts/completeness-check-cli-contract.md`
  (the FR-007 script's CLI contract — lane-b's WP03 depends on this contract
  only, not on this WP's source; keep the invocation/exit-code/output shape
  exactly as specified there)

**Hard rules for the whole WP** (from spec + plan):

1. Touch ONLY the three files in `owned_files`. If something outside them
   seems necessary, record it as a blocker in the work log — do not edit it.
   This is the enforcement mechanism for **C-001** (no spec-kitty runtime
   code changes) — T006's `git diff --stat` checks are its verification
   gate.
2. `conformance/skills/manifest.yaml` must be **block-style YAML, one key per
   line, `id:` immediately preceding `skillDir:` inside the same list item, at
   a fixed 4-space indent** — the exact convention in the schema's
   `"$comment"`. This is not stylistic: `check-manifest-completeness.mjs`
   parses the manifest as raw text (no YAML parser), and its correctness
   depends on this literal layout.
3. The manifest ends up with exactly 54 cases: 53 `StaticCase` entries (one
   per `src/doctrine/skills/*` directory, `profile: base`,
   `expectations: {ok: true, violations: []}`, `skillDir` = `../../src/doctrine/skills/<name>`)
   plus 1 `ControlCase` (`id: control-name-mismatch`, `skillDir: control/name-mismatch`,
   `expectations: {ok: false, violations: []}`).
4. `check-manifest-completeness.mjs` MUST scan `src/doctrine/skills/` by
   **entry type**, never by excluding a literal filename:
   `fs.readdirSync(dir, {withFileTypes:true}).filter(e=>e.isDirectory())`.
   `src/doctrine/skills/` also contains a plain `README.md` file (not a skill
   directory) — do not special-case its name; excluding it by type, not by
   name, is what keeps this check correct if a second stray file ever lands
   there.
5. The +1 control-case offset in the completeness script MUST be a named
   constant (e.g. `CONTROL_CASE_COUNT = 1`) declared and documented at its
   point of use — never an inline magic number.
6. Do not invert the control case's polarity. It declares
   `expectations: {ok: false, ...}` deliberately — muster's own rule is
   `passed = ok === expectations.ok` (`src/cli/index.ts:956` at the pinned
   `v1.1.0` tag), so the case **passes** because the harness's actual result
   (`ok: false`, the fixture is genuinely broken) matches the declared
   expectation. If this case were flipped to `ok: true` it would silently
   stop discriminating — this is the fail-safe the spec's Edge Cases section
   describes; do not "fix" it.
7. This mission's seed is GitHub issue `MOES-Media/spec-kitty#22`. Before
   starting Subtask T002 (IC-01), confirm the issue is assigned to the
   Human-in-Charge (DIR-012) — see T001 below. (It already is, per the
   mission's plan.md Charter Check row; this is a confirmation step, not an
   outstanding action.)

## Subtasks

### T001 — Confirm DIR-012 (tracker issue assigned to HiC)

**Purpose**: Charter gate DIR-012 requires the tracker-backed seed issue to be
assigned to the Human-in-Charge before implementation starts on this mission's
first work package.

**Steps**:
1. Run `gh issue view 22 --repo MOES-Media/spec-kitty --json assignees` (or
   equivalent) and confirm at least one assignee is present.
2. Record the confirmation (assignee login, timestamp) as a one-line entry in
   this WP's work log / history. Do not proceed to T002 until this is
   recorded.

**Files**: none (verification only).
**Validation**: the work log contains an explicit DIR-012 confirmation line.

---

### T002 — Author the 53 `StaticCase` entries (IC-01, FR-001)

**Purpose**: Enumerate one conformant manifest case per built-in skill.

**Steps**:
1. List the real skill directories:
   `ls src/doctrine/skills/` (expect 53 directories + the plain `README.md`
   file — do not create a case for `README.md`).
2. Create `conformance/skills/manifest.yaml` with top-level shape:
   ```yaml
   cases:
     - id: <skill-directory-name>
       type: static
       skillDir: ../../src/doctrine/skills/<skill-directory-name>
       profile: base
       expectations:
         ok: true
         violations: []
   ```
   One block per skill, in the exact 4-space-indent, `id:`-immediately-before-
   `skillDir:` layout from the schema's `"$comment"`. `id` mirrors the skill
   directory's basename exactly (case-sensitive).
3. Do not use `../..`-escaping beyond `../../src/doctrine/skills/<name>` — the
   path must resolve inside the repository checkout (spec Acceptance
   Scenario 1's clarification).
4. Commit this 53-case manifest now, before starting T004 (IC-03) — plan.md's
   binding WP01 ordering rule: **IC-01 must be authored and committed before
   IC-03 begins.** IC-02 (T003 below) may happen alongside this commit or
   right after; either is fine.

**Files**: `conformance/skills/manifest.yaml` (new, 53 cases at this point).
**Validation**: `cases` has exactly 53 entries; every `skillDir` resolves to a
real directory under `src/doctrine/skills/`; the file is committed.

---

### T003 — Author the discrimination control fixture + case (IC-02, FR-005)

**Purpose**: Add the one deliberately-broken case that proves the suite can
fail, not just always pass.

**Steps**:
1. Create `conformance/skills/control/name-mismatch/SKILL.md` with YAML
   frontmatter whose `name` field does **not** equal `name-mismatch` (the
   parent directory's basename) — e.g. `name: wrong-name`. This trips the
   name-must-equal-directory-basename static gate, the most legible of
   muster's three hard gates (research.md §4).
2. Append the 54th case to `conformance/skills/manifest.yaml`, same layout
   convention as the other 53:
   ```yaml
     - id: control-name-mismatch
       type: static
       skillDir: control/name-mismatch
       profile: base
       expectations:
         ok: false
         violations: []
   ```
3. Do not touch any of the 53 `StaticCase` entries from T002 while doing this.

**Files**: `conformance/skills/control/name-mismatch/SKILL.md` (new),
`conformance/skills/manifest.yaml` (append one case — now 54 total).
**Validation**: the fixture's frontmatter `name` genuinely differs from
`name-mismatch`; the manifest now has 54 cases.

---

### T004 — Manifest completeness check script (IC-03, FR-007)

**Purpose**: Deliver `conformance/scripts/check-manifest-completeness.mjs`
exactly per `contracts/completeness-check-cli-contract.md`.

**Preconditions**: T002 must be committed (see T002 step 4 — do not begin
this subtask before that commit exists, even if T003 is still open).

**Steps**:
1. Create `conformance/scripts/check-manifest-completeness.mjs` (Node stdlib
   only — `fs`, `path` — no npm dependency, no `package.json` change).
2. Read the actual skill set:
   `fs.readdirSync('src/doctrine/skills', {withFileTypes:true}).filter(e=>e.isDirectory())`
   — filter by entry type, never by excluding the literal name `README.md`
   (hard rule 4 above).
3. Read `conformance/skills/manifest.yaml` as plain text (no YAML parser) and
   extract `(id, skillDir)` pairs per case using the fixed-indent, `id:`-
   before-`skillDir:` convention T002/T003 established.
4. Filter manifest cases whose `skillDir` resolves under
   `src/doctrine/skills/` (this excludes the one control case, whose
   `skillDir` points at `conformance/skills/control/...`), and compare that
   filtered set's basenames against the real directory list from step 2.
5. Declare `const CONTROL_CASE_COUNT = 1;` with a one-line comment explaining
   the offset, and assert
   `manifestStaticCaseCount === actualSkillCount + CONTROL_CASE_COUNT`
   **and** that the two basename sets match exactly.
6. On success: print one confirmation line (e.g.
   `manifest completeness: OK (53 skills + 1 control = 54 cases)`) and
   `process.exit(0)`.
7. On mismatch: print every missing/extra skill by name (never a bare count),
   in the two-line shape from the CLI contract, and `process.exit(1)`. Never
   exit `2` — that code is reserved for muster's own internal-error
   convention, per the contract.

**Files**: `conformance/scripts/check-manifest-completeness.mjs` (new, ~40
lines per research.md §6's estimate).
**Validation**: covered by T005 below (real execution, both directions).

---

### T005 — Mandatory real-CLI verification (operator directive, plan.md Verification Strategy)

This mission cannot be called done on inspection alone. Run every step below
for real and record the real, observed result (exit code and, where relevant,
exact message text) in this WP's work log.

**Purpose**: Prove FR-002, FR-005's discrimination, and FR-007's completeness
check all behave as specified, using the actual built muster CLI and the
actual repository tree — not by asserting from the file contents. Running
step 1 for real (network disabled after the one-time cache-warm) is also this
WP's evidence for **NFR-002** (deterministic given a pinned version, zero
network calls in the run path) — if the offline run failed to reach the
network at all and still produced a correct exit code, that is NFR-002
holding, not incidental.

**Steps** (follows quickstart §1–3 (see that section for the exact diff-check wording)):
1. Cache-warm, then run fully offline (quickstart.md §1):
   ```sh
   npm install --no-save @garrison-hq/muster@1.1.0
   npx --offline @garrison-hq/muster@1.1.0 skills run conformance/skills/manifest.yaml
   ```
   Record the exit code. **MUST be 0** against the real 54-case manifest.
2. Prove discrimination both ways (quickstart.md §2): with the control case
   at its shipped `ok: false`, confirm the baseline run exits `0`; then
   temporarily flip that one case's `ok: false` → `ok: true` (control case
   only — verify by hand which single line changed), re-run, confirm the run
   now exits **non-zero**, then restore the file exactly (`git diff --exit-code
   conformance/skills/manifest.yaml` must show no diff afterward).
   Paste into the work log the exact `git diff conformance/skills/manifest.yaml`
   output captured immediately after the flip (before restoring), showing the
   single `ok: false → ok: true` line change, alongside the post-restore
   clean-diff confirmation. A restored-clean diff alone, with no mid-test diff
   evidence, does not satisfy this gate.
3. Manifest completeness check, both ways (quickstart.md §3): run
   `node conformance/scripts/check-manifest-completeness.mjs` against the true
   tree (expect exit `0`); induce a mismatch by creating a temporary probe
   directory `src/doctrine/skills/__temp-completeness-probe/` with a minimal
   `SKILL.md`, re-run (expect exit non-zero, with the failure message naming
   `__temp-completeness-probe` explicitly, not just a count mismatch), then
   delete the probe directory immediately and re-run once more to confirm the
   script reports `0` again. The probe directory must never be committed.
   Additionally paste the literal terminal transcript (invocation line + full
   stdout/stderr) for both the induced-mismatch run and the restored-clean
   re-run, not just the message text.

**Files**: none new — this subtask only exercises T002–T004's outputs.
**Validation**: all six real exit codes (steps 1, and both directions of 2 and
3) are recorded in the work log with their exact values; the completeness
check's failure message text (naming the specific probe skill) is quoted
verbatim in the work log as proof it names skills, not just a bare count.

---

### T006 — WP01 verification (Definition of Done gate)

**Steps** (run in order):
```bash
git diff --stat                          # ONLY the three owned_files changed (plus new fixture dir)
git diff --stat src/doctrine/            # MUST show no changes (except the T005 probe, already deleted)
git diff --stat .github/                 # MUST show no changes (lane-b's file is not this WP's concern)
grep -c "^  - id:" conformance/skills/manifest.yaml   # sanity count check, expect 54
```
Confirm the DIR-012 confirmation (T001) and all T005 real-run results are
present in the work log before requesting review.

## Definition of Done

- [ ] DIR-012 confirmed and recorded (T001) before T002 began
- [ ] `conformance/skills/manifest.yaml` has exactly 54 cases: 53 `StaticCase`
      (one per real `src/doctrine/skills/*` directory) + 1 `ControlCase`
- [ ] Manifest follows the fixed-indent, `id:`-before-`skillDir:` raw-text
      convention throughout (verified by inspection, not just by the script
      parsing it successfully)
- [ ] `conformance/skills/control/name-mismatch/SKILL.md` exists with a
      frontmatter `name` that genuinely does not equal `name-mismatch`
- [ ] `conformance/scripts/check-manifest-completeness.mjs` scans
      `src/doctrine/skills/` by directory-entry type, never by excluding the
      literal name `README.md`
- [ ] The script's +1 offset is a named, documented constant, not a magic
      number
- [ ] Real muster CLI run against the real 54-case manifest exits `0`
      (recorded in work log)
- [ ] Real control-case flip test: un-flipped exit `0`, flipped exit
      non-zero, file restored with a clean `git diff` (recorded in work log).
      The exact `git diff conformance/skills/manifest.yaml` output captured
      immediately after the flip (before restoring), showing the single
      `ok: false → ok: true` line change, is pasted into the work log
      alongside the post-restore clean-diff confirmation. A restored-clean
      diff alone, with no mid-test diff evidence, does not satisfy this gate.
- [ ] Real completeness-check run: true tree exits `0`, induced mismatch
      exits non-zero and names the specific probe skill, restored tree exits
      `0` again (recorded in work log, failure message quoted verbatim)
- [ ] No file outside `owned_files` is modified; no `src/doctrine/**` file
      left changed; `.github/**` untouched by this WP

## Risks

- **Line-based parsing fragility**: the completeness script depends on the
  manifest's exact layout convention, not a real YAML parser. Mitigated by
  T002/T003 following the convention precisely and T005 exercising the
  script against the real, as-authored manifest (not a hand-crafted test
  fixture) before this WP is marked done.
- **Control-case regression**: if a future edit "fixes" the control fixture's
  name/directory mismatch without updating its declared expectation, the
  suite will fail loudly (`ok:true` actual vs `ok:false` declared) — this is
  the intended fail-safe (spec Edge Cases), not a defect to guard against
  here.
- **DIR-012 timing**: confirming the tracker issue's assignee is a one-time,
  cheap check — the only risk is skipping it; T001 exists specifically so it
  cannot be silently skipped.

## Reviewer guidance

- **Reject if** the manifest is not in block-style, one-key-per-line,
  fixed-4-space-indent YAML, or if any case's `id:`/`skillDir:` pair is not
  adjacent — this breaks FR-007's completeness script silently.
- **Reject if** `check-manifest-completeness.mjs` filters `src/doctrine/skills/`
  entries by excluding the literal string `README.md` instead of filtering by
  `Dirent.isDirectory()`.
- **Reject if** the work log does not contain real, observed exit codes for
  all of quickstart.md §1–§3 (not "should exit 0" — the actual recorded
  value from a real run).
- **Reject if** the control case's `expectations.ok` is anything other than
  `false`, or if its backing fixture's `name` actually equals `name-mismatch`
  (i.e., the fixture is not actually broken).
- Confirm `git diff --stat` shows changes in exactly the three `owned_files`
  entries (plus the new control fixture file itself) and nothing under
  `src/doctrine/**` or `.github/**`.
- Confirm the +1 control-case offset in the script is a named constant with
  an inline comment, not a bare literal `1` used without explanation.

Implementation command: `spec-kitty agent action implement WP01 --agent claude`

## Activity Log

- 2026-07-26T23:49:38Z – claude – shell_pid=364250 – DIR-012 confirmed: gh issue view 22 --repo MOES-Media/spec-kitty shows assignee MOES-Media (Jeroen Nouws), confirmed 2026-07-26T23:44Z before starting T002.
- 2026-07-26T23:49:48Z – claude – shell_pid=364250 – T005 step1 (FR-002/NFR-002): cache-warm 'npm install --no-save @garrison-hq/muster@1.1.0' (added 63 packages, 0 vulnerabilities), then offline 'npx --offline @garrison-hq/muster@1.1.0 skills run conformance/skills/manifest.yaml' -> stdout 'skills: PASS - 54/54 cases passed, 0 failed' with all 54 [PASS] lines incl. [PASS] control-name-mismatch; exit code: 0.
- 2026-07-26T23:49:58Z – claude – shell_pid=364250 – T005 step2 (FR-005 discrimination, both directions): baseline (control ok:false) run exit 0 ("skills: PASS - 54/54 cases passed"). Flipped: sed -i.bak s/ok: false/ok: true/ on manifest.yaml touched exactly 1 line (verified via diff .bak | grep -c ^< = 1). git diff conformance/skills/manifest.yaml captured immediately after flip: "@@ -375,5 +375,5 @@ cases:      skillDir: control/name-mismatch     profile: base     expectations: -      ok: false +      ok: true       violations: []" (single line changed). Re-run with flipped file -> stdout "skills: FAIL - 53/54 cases passed, 1 failed" with "[FAIL] control-name-mismatch"; exit code: 1 (non-zero). Restored: mv manifest.yaml.bak manifest.yaml; git diff --exit-code conformance/skills/manifest.yaml exited 0 (clean, confirmed post-restore). Re-ran baseline again after restore: exit 0, all 54 [PASS] again.
- 2026-07-26T23:50:06Z – claude – shell_pid=364250 – T005 step3 (FR-007 completeness, both directions): baseline "$ node conformance/scripts/check-manifest-completeness.mjs" -> stdout "manifest completeness: OK (53 skills + 1 control = 54 cases)"; exit code 0. Induced mismatch: mkdir -p src/doctrine/skills/__temp-completeness-probe + minimal SKILL.md; re-run -> stdout "manifest completeness: MISMATCH" / "  missing from manifest (present under src/doctrine/skills/, no case found): __temp-completeness-probe" / "  extra in manifest (case present, no matching src/doctrine/skills/<name> directory): (none)"; exit code 1 (non-zero), failure message names __temp-completeness-probe explicitly, not a bare count. Cleanup: rm -rf src/doctrine/skills/__temp-completeness-probe (never committed; git status --short src/doctrine/ showed nothing). Re-ran -> stdout "manifest completeness: OK (53 skills + 1 control = 54 cases)"; exit code 0 again.
- 2026-07-26T23:54:27Z – claude – shell_pid=364250 – T006 verification gate: git diff --stat vs pre-WP01 base (e06862fce..HEAD) shows exactly 3 files changed (conformance/skills/manifest.yaml, conformance/skills/control/name-mismatch/SKILL.md, conformance/scripts/check-manifest-completeness.mjs) = the 3 owned_files, 533 insertions, 0 deletions. git diff --stat src/doctrine/ empty. git diff --stat .github/ empty. grep -c "^  - id:" conformance/skills/manifest.yaml = 54. Working tree clean.
