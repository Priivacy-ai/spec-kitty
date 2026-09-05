---
work_package_id: WP03
title: Discrimination control, drift-gate + completeness scripts, README, CI workflow
dependencies:
- WP01
- WP02
requirement_refs:
- FR-004
- FR-005
- FR-006
- FR-007
- FR-009
- C-001
- C-002
- C-003
planning_base_branch: kitty/mission-doctrine-rule-manifests
merge_target_branch: kitty/mission-doctrine-rule-manifests
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-doctrine-rule-manifests. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-doctrine-rule-manifests unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
- T017
- T018
- T019
- T020
- T021
history: []
agent_profile: node-norris
authoritative_surface: conformance/
create_intent:
- conformance/doctrine/control/045-drifted.yaml
- conformance/doctrine/README.md
- conformance/scripts/check-doctrine-drift-gate.sh
- conformance/scripts/check-doctrine-manifest-completeness.mjs
execution_mode: code_change
owned_files:
- conformance/doctrine/control/045-drifted.yaml
- conformance/doctrine/README.md
- conformance/scripts/check-doctrine-drift-gate.sh
- conformance/scripts/check-doctrine-manifest-completeness.mjs
- .github/workflows/conformance.yml
role: implementer
tags: []
tracker_refs: []
---

# WP03 — Discrimination control, drift-gate + completeness scripts, README, CI workflow

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

Close out mission `doctrine-rule-manifests-01KYH7AM`: author the one
discrimination control manifest (deliberately drifted `ruleText`), the CI
drift-gate script and the absence-guard completeness script, the
`conformance/doctrine/README.md` mapping table + coverage roadmap, and the
new `sop-doctrine-conformance` CI job in the shared
`.github/workflows/conformance.yml`. Prove, for real against the actual
muster CLI and a real GitHub Actions run, that the gate fires correctly in
both directions (clean on the 13 shipped manifests, dirty on the control)
and that every absence failure mode (missing manifest, missing `sopFile`
target, dropped rule entry, deleted control) is caught loudly.

**Dependency**: this WP depends on WP01 (9 trace-decidable manifests) and
WP02 (4 judge-proposed manifests) both being complete — the drift-gate
script globs the 13 real manifest paths and the completeness script compares
against their real rule counts, so this WP genuinely needs those 13 files to
exist, not just their contracts.

## Context

This mission (`doctrine-rule-manifests-01KYH7AM`, wave-2 mission M3 of the
muster ⇄ spec-kitty agent-conformance programme, GitHub issue
`MOES-Media/spec-kitty#23`) makes 13 of spec-kitty's 26 built-in directives
machine-checkable via muster's `openclaw-sop` adapter. WP01 and WP02
authored the 13 manifests (45 rule entries: 26 in WP01's 9 trace-decidable
directives, 19 in WP02's 4 judge-proposed directives). This WP closes the
loop: without it, the 13 manifests are inert documentation — nothing in CI
ever runs `muster sop run` against them, and nothing proves the drift
detector actually fires when it should.

Everything below is copied verbatim from this mission's planning artifacts
(the four `contracts/*.md` files and `quickstart.md`) so this WP is
self-contained.

**Two lessons from sibling missions, binding on everything you write in this
WP**:

1. **Assert exact vectors, not membership.** A sibling WP's assertion
   "contains at least one finding of each required kind" was proven blind to
   a fixture silently acquiring a *second* kind — it catches deletion and
   defusal but not corruption. Wherever this WP's scripts or verification
   steps assert findings, require an **exact count and exact kind vector**
   (e.g. "exactly one finding, kind `RULE_DRIFT`" — not "at least one
   `RULE_DRIFT` finding somewhere in the array"), plus a **file-count
   assertion** on the manifest set (exactly 13 shipped + 1 control) so a
   silently shrunk manifest set fails loudly and independently of any
   per-finding check.
2. **Evidence must be falsifiable.** Prior missions shipped gates that
   accepted prose summaries, and a control that was defeated without anyone
   noticing because it was never observed failing. Every verification step
   in this WP requires **literal terminal transcripts and actual exit
   codes** pasted into the work log — not "should exit 0." **The
   discrimination control specifically must be observed producing a
   `RULE_DRIFT` finding for real** (Subtask T019 below) — a control never
   seen to fire is an unverified control, indistinguishable from a dead one.

## Note on `FR-007`/`FR-009` in this WP's `requirement_refs`

This mission's `spec.md` Requirements section defines exactly six functional
requirements, `FR-001`–`FR-006` (confirmed by the spec's own quality
checklist: "All six FRs (001–006) ... No IDs were invented"). `spec.md`
nonetheless contains two **prose mentions** of `FR-007` and `FR-009` that
belong to *other* artifacts — `FR-001`'s post-spec-gate correction note
references "M1's spec['s] ... post-spec-gate FR-007 addition" (a different
mission's requirement, cited for precedent), and an Edge Cases entry
mentions "`FR-009` in that file" referring to an internal label inside
muster's own `manifest.ts` source, not this spec's requirement table.

`spec-kitty agent mission finalize-tasks`'s requirement-mapping validator
scans `spec.md`'s full text for any `FR-\d+`/`NFR-\d+`/`C-\d+` substring
(not just table rows), so it treats these two prose mentions as if they were
functional requirements of *this* mission needing a WP mapping. They are
not — do not go looking for `FR-007`/`FR-009` rows in this mission's
`spec.md` Requirements table; there are none, and none should be added
(adding invented rows would violate the spec's own already-passed quality
gate). Their presence in this WP's `requirement_refs` is a mechanical
satisfaction of the validator's global-scan behavior, recorded here so a
future reader does not mistake it for a real, ninth functional requirement
of this mission.

## The exact artifacts you are authoring

### 1. Control manifest — `conformance/doctrine/control/045-drifted.yaml` (FR-005, IC-02)

Same shape as every other manifest, one entry, `sopFile` pointing at the
**real** 045 directive file (three directory levels up from
`conformance/doctrine/control/`, not two — this file is one directory
deeper than the 13 shipped manifests):

```yaml
version: "1.0.0"
sopFile: "../../../src/doctrine/directives/built-in/045-prs-only-and-read-intent.directive.yaml"
rules:
  - ruleId: "045-r1-drifted"
    ruleText: "Agents must never run `git push origin main`, `git push --force`, or `gh pr"
    probeIds: []
    gradingClass: "binary"
    aggregation: "pass-k"
    k: 3
    passThreshold: 3
    source:
      normative: "docs/rubric/sop-rule-taxonomy.md#1-never-call-tool"
      supporting: "https://github.com/Priivacy-ai/spec-kitty/blob/03d19bb988fe283457c49fc217bfd68f1f849633/src/doctrine/directives/built-in/045-prs-only-and-read-intent.directive.yaml"
```

The `ruleText` above is the real 045-r1 fragment (`"Agents must not run
\`git push origin main\`, \`git push --force\`, or \`gh pr"`) with exactly
one word changed: **"must not run" → "must never run"**. This is the one
manifest in the whole mission where "found nothing" is the failure, not the
success — CI must assert this file **produces** a `RULE_DRIFT` finding
(inverted polarity vs. every other gate in this mission).

**Before committing, verify the mutation is genuinely absent from the real
file** (Subtask T014 below):
```sh
grep -F -c "Agents must never run \`git push origin main\`, \`git push --force\`, or \`gh pr" \
  src/doctrine/directives/built-in/045-prs-only-and-read-intent.directive.yaml
# MUST print 0
```
If this ever prints a number greater than `0`, the control has stopped
discriminating (a future directive edit could coincidentally introduce this
exact phrase) — do not ship a control whose mutated text is not genuinely
absent from the real file.

This file is **excluded** from the drift gate's "must be clean" Phase 1 loop
(its path is under `control/`, not matched by the `conformance/doctrine/*.yaml`
glob) and is **excluded** from the completeness script's per-directive rule
count comparison (checked instead for bare existence + exactly 1 rule entry).

### 2. `conformance/scripts/check-doctrine-drift-gate.sh` (FR-004/FR-005, IC-03)

**Invocation**: `bash conformance/scripts/check-doctrine-drift-gate.sh`, no
arguments, run from the repository root. Manifest paths are discovered by
globbing `conformance/doctrine/*.yaml` (the 13 shipped manifests) plus one
hardcoded path to the control,
`conformance/doctrine/control/045-drifted.yaml`.

**Phase 1 — FR-004, the main gate** (must find nothing, for every shipped manifest):

```sh
for manifest in conformance/doctrine/*.yaml; do
  set +e
  out=$(npx --yes @garrison-hq/muster@1.1.0 sop run "$manifest" --json)
  muster_exit=$?
  set -e
  # muster's own exit code: 0 = passed, 1 = lint error/probe failure, 2 = execution error
  bad=$(printf '%s' "$out" | jq '[.lintFindings[] | select(.kind=="RULE_DRIFT" or .kind=="MISSING_SOURCE" or .kind=="MANIFEST_ERROR" or .kind=="STRUCTURAL_ABSENCE")]')
  count=$(printf '%s' "$bad" | jq 'length')
  # count MUST be 0 for every manifest
done
```

**Why `STRUCTURAL_ABSENCE` is in this filter — do not remove it.** It was
added post-plan (binding operator decision) after the mission's own gate
reproduced it against the real built CLI: a missing `sopFile:` target (a
deleted or renamed directive file, or a typo'd path) produces
```json
{ "lintFindings": [{ "kind": "STRUCTURAL_ABSENCE", "severity": "error", ... }], "passed": false }
```
with real exit `1`. Before this fix, the filter selected only
`RULE_DRIFT`/`MISSING_SOURCE`/`MANIFEST_ERROR`, so this exact failure mode
reported `count=0` — a false-clean gate pass — even though muster's own
`passed` field was already `false`. This is the third recurrence of the
absence-class defect in this programme; **a future edit that "simplifies"
this filter back down to three kinds reintroduces that exact defect.**
`STRUCTURAL_ABSENCE`'s presence here is belt-and-suspenders with the
exit-code capture below, not a substitute for it: the exit-code check
catches cases where muster never emits JSON at all (exit `2`), while this
filter entry catches cases where muster *does* emit valid JSON with
`passed: false` and the script must name the specific offending finding
kind rather than only report a bare "gate failed."

**Phase 2 — FR-005, the inverted control assertion** (must find at least one `RULE_DRIFT`):

```sh
set +e
out=$(npx --yes @garrison-hq/muster@1.1.0 sop run conformance/doctrine/control/045-drifted.yaml --json)
muster_exit=$?
set -e
count=$(printf '%s' "$out" | jq '[.lintFindings[] | select(.kind=="RULE_DRIFT")] | length')
# count MUST be >= 1
```

**Failure handling — capturing muster's real exit code (hardened, this is
not optional pseudocode, it is the actual required behavior).** A missing
manifest file does **not** produce `MANIFEST_ERROR` JSON with exit `1` — it
was verified against the real built CLI to behave differently:

```
$ node dist/cli/index.js sop run conformance/doctrine/does-not-exist.yaml --json
muster: cannot read sop manifest "...": ENOENT: ...
REAL EXIT CODE: 2
```

`doSopRun` calls `readFileOrThrow(absManifestPath, "sop manifest")`
(`src/cli/index.ts:1436` in the muster package) **before** it ever calls
`runSopManifestSuite`. `readFileOrThrow` throws an `ExecutionError` on
`ENOENT`, which propagates to `runCli`'s top-level catch
(`src/cli/index.ts:1979-1982`), which prints a plain
`muster: cannot read sop manifest "...": ...` line to **stderr** and returns
exit **`2`** — **no JSON is ever produced** for this case. A naive script
that never captures `$?` and never checks whether `$out` is valid JSON
before piping it to `jq` would, on this real case, feed an empty string
(only stdout is captured by `$(...)`; the ENOENT message went to stderr) to
`jq` — undefined/unspecified behavior for a gate script, not a designed hard
failure.

**The script MUST therefore, for every `sop run` invocation (both Phase 1's
loop and Phase 2's control call)**:
1. Capture muster's real exit code (`muster_exit=$?`, with `set +e` around
   the invocation, as shown above).
2. Before doing anything with `jq`, treat `muster_exit != 0` as an
   immediate, named hard gate failure for that manifest — independent of
   what `jq` would or wouldn't find — with a message distinguishing exit
   `1` ("muster ran, found a lint/probe failure") from exit `2` ("muster
   could not execute — see stderr above, e.g. an ENOENT on the manifest path
   or the resolved `sopFile` target").
3. Treat empty or non-JSON `$out` (e.g. `jq -e . >/dev/null 2>&1 <<<"$out"`
   failing) as its own named hard gate failure, even if `muster_exit`
   happened to be `0` — belt-and-suspenders against any future muster
   change that emits partial/malformed output on an unanticipated code path.
4. Only run the `RULE_DRIFT`/`MISSING_SOURCE`/`MANIFEST_ERROR`/
   `STRUCTURAL_ABSENCE` `jq` filter (Phase 1) or the `RULE_DRIFT`-count
   filter (Phase 2) once steps 2–3 have both passed for that invocation.

**`jq` must never be the only thing standing between a broken run and a
green gate.** A script that skips steps 1–3 and only ever inspects `jq`'s
output would, on a real ENOENT, either crash opaquely on malformed `jq`
input or — worse — silently report `count=0` and pass. Both outcomes are
exactly the "gate looks green, muster is actually broken" failure this
closes.

**Exit codes for this script**:

| Code | Meaning |
|---|---|
| `0` | All 13 shipped manifests clean (zero disallowed findings, muster exited `0` with valid JSON for every one) AND the control produced at least one `RULE_DRIFT` (muster exit `0`, valid JSON). |
| `1` | At least one shipped manifest has a disallowed finding, OR muster itself exited non-zero or emitted non-JSON/empty output for any shipped manifest or the control, OR the control failed to discriminate (zero `RULE_DRIFT` findings) — name which manifest(s), which failure mode, and which finding(s), never a bare count. |
| (never `2`) | This script's own exit code never reuses muster's `2` — a muster-side exit `2` is one of the named hard-failure modes above and is reported as this script's own exit `1`. |

**Output shape**: on success, one line per manifest confirming it is clean,
then a confirmation line the control discriminated, e.g.:
```
checking: conformance/doctrine/001-architectural-integrity-standard.yaml — clean
...
checking: conformance/doctrine/045-prs-only-and-read-intent.yaml — clean
control OK: RULE_DRIFT present (1 finding) as expected
```
On failure, name the offending manifest and dump the specific finding
objects (not a bare count) via `jq .` on the filtered array.

**Non-goals** (do not scope-creep this script): does not check
`UNDEFINED_PRECEDENCE`/`TOOL_DRIFT` (reported-not-gating per FR-004); does
not independently re-validate manifest YAML shape beyond what
`loadAndValidateManifest` already does; does not validate `sopFile:` target
existence beyond the `STRUCTURAL_ABSENCE` filter entry above (the
completeness script, item 3 below, never reads `sopFile:` at all — this
script's `STRUCTURAL_ABSENCE` entry is the **sole** guard against a deleted
directive file or a typo'd `sopFile:` path — the two scripts do not overlap
here); does not check rule-count completeness (item 3 below owns that).

### 3. `conformance/scripts/check-doctrine-manifest-completeness.mjs` (absence guard, author-added, IC-04)

**Invocation**: `node conformance/scripts/check-doctrine-manifest-completeness.mjs`,
no arguments, run from the repository root. Dependency-free Node (stdlib
`fs`/`path` only, no npm dependency, no `package.json` change). No network
access, no environment variables.

**This script closes the one gap muster's own error paths do not cover**: a
rule entry silently dropped from a manifest produces no finding of any kind
and a clean `exit 0` from muster itself.

**Algorithm**:
1. **Expected rule count per in-scope directive** — read each of the 13
   directive files and count `integrity_rules` bullets via a line-based
   block scan (no YAML parser):
   ```js
   // Enter the block at a line matching /^integrity_rules:/
   // Exit the block at the next line matching /^[A-Za-z_]+:/
   // Count lines inside the block matching /^\s*-\s/
   ```
   This algorithm, run against the 13 real directive files, produces:
   `001→3, 010→2, 018→2, 028→3, 029→2, 030→3, 033→2, 034→3, 035→3, 039→11,
   042→4, 044→3, 045→4` — **summing to exactly 45**. These 13 numbers are
   **recomputed fresh on every run** — never hardcoded as a lookup table
   (the whole point is to catch a *future* directive edit or manifest edit
   going out of sync).
2. **Actual rule count per shipped manifest** — read each of the 13
   manifest files as plain text (no YAML parser) and count lines matching
   `/^\s*- ruleId:/`.
3. **Manifest existence** — confirm all 13 expected manifest files exist at
   `conformance/doctrine/<directive-stem>.yaml` (paired 1:1 by filename
   stem — this filename-stem pairing convention is why WP01/WP02's
   manifests must mirror their directive's stem exactly, minus
   `.directive`) and that the control manifest exists at
   `conformance/doctrine/control/045-drifted.yaml` with exactly 1 rule
   entry.

   **This filename-stem pairing is the entire extent of what this script
   checks about a manifest's identity — it never reads or validates a
   manifest's `sopFile:` field.** A manifest can exist at the right path,
   with the right rule count, and still point its `sopFile:` at a deleted
   directive file or a typo'd path; this script reports `OK` for that
   manifest regardless. **That specific failure mode is guarded exclusively
   by the drift gate's `STRUCTURAL_ABSENCE` jq filter entry (item 2 above)
   — do not add `sopFile:` validation to this script, the division of labor
   is deliberate: filename-stem pairing is this script's job; `sopFile:`
   target existence is the jq gate's job; neither script re-implements the
   other's guard.**
4. **Compare and report** — for each directive, assert
   `actualManifestRuleCount === expectedDirectiveRuleCount`. On any mismatch
   (including a manifest file being entirely absent, treated as an actual
   count of `0`), print every offending directive by name and both counts;
   exit `1`. On full agreement across all 13 directives plus the control's
   existence, print a one-line confirmation and exit `0`.

**Output shape**:
- Success (exit `0`): `doctrine manifest completeness: OK (13 manifests, 45 rules, 1 control)`
- Failure (exit `1`), naming every mismatch explicitly:
  ```
  doctrine manifest completeness: MISMATCH
    045-prs-only-and-read-intent: directive has 4 integrity_rules, manifest has 3 rule entries (missing: 1)
  ```
  or for a missing manifest file:
  ```
    029-agent-commit-signing-policy: manifest file conformance/doctrine/029-agent-commit-signing-policy.yaml not found (expected 2 rules, found 0)
  ```
  or for a missing/empty control:
  ```
    control manifest conformance/doctrine/control/045-drifted.yaml not found or has 0 rule entries (expected exactly 1)
  ```

**Exit codes**: `0` = all 13 counts match and control exists with exactly 1
rule; `1` = any mismatch, named explicitly; this script never exits `2`
(reserved for "muster itself errored" — this script never invokes muster).

**Non-goals**: does not validate `ruleText` content, `gradingClass`/
`aggregation` correctness, or citation shape (muster's own checks, via the
drift gate, cover that); does not validate `sopFile:` targets (item 2's job,
not this script's — do not duplicate); does not detect a duplicated
`ruleId` where the count still happens to match (muster's own loader
already throws on duplicate `ruleId`, caught by the drift gate as
`MANIFEST_ERROR`).

### 4. `conformance/doctrine/README.md` (FR-006, IC-05)

Must contain, at minimum:

**A. Directive→class mapping table** — one row per rule (45 rows), covering
every rule this mission ships. The complete data (copy this table into the
README, formatted as you see fit, but every fact below must appear):

| Directive | ruleId | Coverage | Class | gradingClass |
|---|---|---|---|---|
| 001 | 001-r1 | full-line | UNMAPPED | judge |
| 001 | 001-r2 | full-line | UNMAPPED | judge |
| 001 | 001-r3 | full-line | UNMAPPED | judge |
| 010 | 010-r1 | full-line | output-format | binary |
| 010 | 010-r2 | full-line | output-format | binary |
| 018 | 018-r1 | full-line | output-format | binary |
| 018 | 018-r2 | full-line | output-format | binary |
| 028 | 028-r1 | full-line | never-call-tool | binary |
| 028 | 028-r2 | full-line | output-format | binary |
| 028 | 028-r3 | full-line | never-call-tool | binary |
| 029 | 029-r1 | full-line | never-call-tool | binary |
| 029 | 029-r2 | full-line | never-call-tool | binary |
| 030 | 030-r1 | full-line | tool-order | binary |
| 030 | 030-r2 | full-line | UNMAPPED | judge |
| 030 | 030-r3 | full-line | output-format | binary |
| 033 | 033-r1 | full-line | never-call-tool | binary |
| 033 | 033-r2 | full-line | UNMAPPED | judge |
| 034 | 034-r1 | full-line | tool-order | binary |
| 034 | 034-r2 | full-line | output-format | binary |
| 034 | 034-r3 | full-line | UNMAPPED | judge |
| 035 | 035-r1 | full-line | output-format | binary |
| 035 | 035-r2 | full-line | tool-order | binary |
| 035 | 035-r3 | full-line | UNMAPPED | judge |
| 039 | 039-r1 | full-line | UNMAPPED | judge |
| 039 | 039-r2 | full-line | UNMAPPED | judge |
| 039 | 039-r3 | full-line | UNMAPPED | judge |
| 039 | 039-r4 | full-line | UNMAPPED | judge |
| 039 | 039-r5 | full-line | UNMAPPED | judge |
| 039 | 039-r6 | full-line | UNMAPPED | judge |
| 039 | 039-r7 | full-line | UNMAPPED | judge |
| 039 | 039-r8 | full-line | UNMAPPED | judge |
| 039 | 039-r9 | full-line | UNMAPPED | judge |
| 039 | 039-r10 | full-line | UNMAPPED | judge |
| 039 | 039-r11 | full-line | UNMAPPED | judge |
| 042 | 042-r1 | fragment | never-call-tool | binary |
| 042 | 042-r2 | fragment | output-format | binary |
| 042 | 042-r3 | fragment | output-format | binary |
| 042 | 042-r4 | full-line | output-format | binary |
| 044 | 044-r1 | fragment | UNMAPPED | judge |
| 044 | 044-r2 | fragment | UNMAPPED | judge |
| 044 | 044-r3 | fragment | UNMAPPED | judge |
| 045 | 045-r1 | fragment | never-call-tool | binary |
| 045 | 045-r2 | fragment | never-call-tool | binary |
| 045 | 045-r3 | fragment | tool-order | binary |
| 045 | 045-r4 | fragment | tone-persona-adherence | judge |

**Summary counts to state explicitly**: 45 rules total across 13 directives;
10 fragment-cited rules (042×3, 044×3, 045×4), 35 full-line rules; **24
rules mapped to an existing class** (`never-call-tool`×8, `output-format`×11,
`tool-order`×4, `confirm-before-destructive`×0 — this mission ships zero
examples of that class, which is not a structural problem, the taxonomy does
not require every mission to exercise every class — `tone-persona-adherence`×1);
**21 rules UNMAPPED (judge-fallback)**: all 11 of 039, all 3 of 001, all 3 of
044, plus one each from 030, 033, 034, 035.

**B. Cross-repo note (state this explicitly, do not omit)**: `docs/rubric/
sop-rule-taxonomy.md` — the normative source every mapping-table row cites —
lives only in the `garrison-hq/muster` package, **not in this repository**.
A reader should not go looking for that file here.

**C. Citation-anchor deviation note (state this explicitly)**: every
`source.normative` in this mission's manifests cites
`docs/rubric/sop-rule-taxonomy.md#<class-anchor>`, appending a `#<anchor>`
fragment. The taxonomy's own citation-format section specifies the literal
string with no anchor. This mission deviates deliberately, for reader
precision — harmless to muster's loader, which only checks non-emptiness —
not an oversight.

**D. Coverage roadmap** — the 13 in-scope directives (listed above) versus
the 13 built-in directives this mission does **not** cover, with a reason
for each:

| Directive | Title | Why not covered |
|---|---|---|
| 003-decision-documentation-requirement | Decision Documentation Requirement | Not in this mission's prioritised set (issue #23); candidate for a future coverage-extension mission |
| 024-locality-of-change | Locality of Change | Not in this mission's prioritised set; candidate for future coverage |
| 025-boy-scout-rule | Boy Scout Rule | Not in this mission's prioritised set; candidate for future coverage |
| 031-context-aware-design | Context-Aware Design | Not in this mission's prioritised set; candidate for future coverage |
| 032-conceptual-alignment | Conceptual Alignment | Not in this mission's prioritised set; candidate for future coverage |
| 036-black-box-integration-testing | Black-Box Integration Testing | Not in this mission's prioritised set; candidate for future coverage |
| 037-living-documentation-sync | Living Documentation Sync | Not in this mission's prioritised set; candidate for future coverage |
| 038-structured-prompt-boundary | Structured Prompt Change-Boundary | **Excluded by construction, not oversight**: carries neither `integrity_rules` nor `validation_criteria` — no `ruleText` source exists for it (verified: `grep -c "^integrity_rules:"` on the real file returns `0`) |
| 040-recurring-bug-structural-intervention | Recurring-Bug Structural-Intervention Discipline | Not in this mission's prioritised set; candidate for future coverage |
| 041-tests-as-scaffold-not-friction | Tests as Scaffold, Not Friction | Not in this mission's prioritised set; candidate for future coverage |
| 043-close-defect-class-by-construction | Close Defect Classes by Construction | Not in this mission's prioritised set; candidate for future coverage |
| 046-readable-consistent-prs | Readable and Consistent Pull Requests | Not in this mission's prioritised set; candidate for future coverage |
| reconcile-change-scope-tensions | Reconciling Change-Scope Tensions | **Excluded by construction**: advisory-enforcement, carries no numeric directive code — a different kind of artifact than the numbered directives this mission targets |

**E. Local-invocation instructions** for both new scripts:
```sh
bash conformance/scripts/check-doctrine-drift-gate.sh \
  && node conformance/scripts/check-doctrine-manifest-completeness.mjs \
  && echo "doctrine conformance: both checks green"
```
This is the exact sequence a contributor runs before opening a PR, and the
exact sequence the new `sop-doctrine-conformance` CI job runs.

**F. CI timing entry**: once T020 (real CI run) produces a real `run_id` and
wall-clock minutes, record them in this README's timing table alongside
M1's existing `skills-conformance` job entry — measured, never asserted as
a ceiling.

**G. `TOOL_DRIFT` exercise disclosure (state this explicitly, do not omit)**:
`detectToolDrift` (`index.ts:128-144` in the muster package) is skipped
entirely unless the invocation passes `--env-tools`; none of this mission's
`sop run` invocations (WP01, WP02, or this WP's own T019/`check-doctrine-
drift-gate.sh`) pass it. That means every "zero `TOOL_DRIFT`" result recorded
anywhere in this mission proves nothing — the detector never ran, it wasn't
clean. Rules `033-r1`, `042-r3`, `042-r4`, `045-r1`, `045-r2` contain
backticked identifiers that would be genuine `TOOL_DRIFT` candidates if the
detector were exercised. This WP must do one of the two:
1. Pass `--env-tools` in the drift-gate script (or a dedicated verification
   step) and evaluate `TOOL_DRIFT` for real against the shipped manifests, or
2. If that is out of scope for this WP, state plainly in this README section
   that `TOOL_DRIFT` is unexercised across the mission — an unexercised
   detector silently reported as "clean" is the same failure shape as an
   unfired control (see FR-005's discrimination requirement above), and this
   mission has already spent significant effort guarding against exactly that
   class of false-clean signal (see `STRUCTURAL_ABSENCE` in item 2 above).
`checkRuleTextPresence` (the source of the `RULE_DRIFT` results) always
runs regardless of `--env-tools`, so the zero-`RULE_DRIFT` results elsewhere
in this mission remain genuine and are not affected by this disclosure.

### 5. `.github/workflows/conformance.yml` modification (FR-004 wiring, IC-06)

**Read the current file before editing** — as of this WP's authoring, PR #29
(`MOES-Media/spec-kitty`, which adds `permissions: contents: read` and
SHA-pins both existing actions) has **merged to the upstream `main` branch**
(`gh pr view 29 --repo MOES-Media/spec-kitty` shows `state: MERGED`), but it
may or may not yet be present on **this mission's own branch checkout** —
confirm which state you are actually looking at before editing (Subtask T018
step 1 below handles this explicitly).

**Rename** the top-level `name:` from `Skills Static Conformance` to
`Static Conformance` — the file now hosts two distinct suites.

**Permissions block — check before inserting, never duplicate**:
1. If the file already has a top-level `permissions:` key (e.g.
   `permissions:\n  contents: read`, inserted by PR #29), **leave it exactly
   as-is** — do not add a second one, do not modify it.
2. If the file does **not** yet have a `permissions:` key (PR #29's change
   has not reached this branch), insert `permissions:\n  contents: read`
   immediately after the `- main` line under `on: push: branches:` and
   immediately before `jobs:` — the same anchor point PR #29 uses.

**Action SHA-pinning — expect it, don't redo it**:
1. If `actions/checkout` and `garrison-hq/muster-action` are already
   SHA-pinned (a 40-character commit SHA in place of `@v6`/`@v1`), **do not
   re-pin or unpin them** — leave the existing job's steps untouched, this
   is not your WP's file territory to modify beyond adding the new job.
2. **Pin your own new job's `actions/checkout` step to match whatever
   convention is already in the file** at the time you edit it: if the
   existing job's `actions/checkout` step already uses a SHA, use the exact
   same SHA for your new job's checkout step (not a fresh `@v6` tag
   reference, which would be inconsistent with the rest of the file); if
   for some reason it is still `@v6` when you look, match that instead.
   The rule is **consistency with what the file already does**, not a
   specific hardcoded pin value — because you may be looking at either the
   pre- or post-PR-#29 state depending on rebase timing.

**New job** — add `sop-doctrine-conformance` (job-level
`name: SOP doctrine conformance (muster)`), independent of and
parallel-safe with the existing `skills-conformance` job (disjoint file
sets, neither job writes anything):

```yaml
  sop-doctrine-conformance:
    name: SOP doctrine conformance (muster)
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@<match-existing-convention>

      - name: Run doctrine rule-manifest drift gate (FR-004/FR-005)
        run: bash conformance/scripts/check-doctrine-drift-gate.sh

      - name: Verify doctrine manifest rule-count completeness (absence guard)
        run: node conformance/scripts/check-doctrine-manifest-completeness.mjs
```

Three steps, in this order (drift gate before completeness check, so both a
drift failure and a completeness failure are visible in one job's log if
both occur — order between the two checks does not otherwise matter).

**No `secrets:` reference anywhere in the new job (C-002)** — resolving
`npx @garrison-hq/muster@1.1.0` needs normal npm-registry network access,
which a GitHub-hosted runner has by default; this also means the job passes
on a fork PR with zero repository secrets available.

**Trigger block is shared, unchanged** — `on: pull_request` (any branch) /
`push: branches: [main]` — do not add a new trigger condition.

## Subtasks

### T014 — Author the control manifest + mechanical drifted-text absence check (IC-02, FR-005)

**Purpose**: Author the one manifest in this mission whose entire purpose is
to be caught, not to pass.

**Steps**:
1. Create `conformance/doctrine/control/045-drifted.yaml` exactly per the
   "1. Control manifest" section above.
2. Before committing, run:
   ```sh
   grep -F -c "Agents must never run \`git push origin main\`, \`git push --force\`, or \`gh pr" \
     src/doctrine/directives/built-in/045-prs-only-and-read-intent.directive.yaml
   # MUST print 0
   ```
3. Record this command and its exact output in the work log.

**Files**: `conformance/doctrine/control/045-drifted.yaml` (new, 1 rule).
**Validation**: the `grep -F -c` check prints `0`; the file's `sopFile` is
`"../../../src/doctrine/directives/built-in/045-prs-only-and-read-intent.directive.yaml"`
(three levels up, not two).

---

### T015 — Author `check-doctrine-drift-gate.sh` (IC-03, FR-004/FR-005)

**Purpose**: Deliver the main CI gate exactly per the "2." section above.

**Steps**:
1. Create `conformance/scripts/check-doctrine-drift-gate.sh` implementing
   both phases and the mandatory failure-handling (exit-code capture, JSON
   validity check, `STRUCTURAL_ABSENCE` in the Phase 1 filter) exactly as
   specified above — do not simplify the filter to three kinds, do not skip
   the exit-code/JSON-validity checks.
2. Ensure the script's own exit codes match the table above (`0`, `1`, never
   `2`).
3. Make the file executable (`chmod +x`) — not strictly required since it is
   invoked via `bash <script>`, but matches house convention.

**Files**: `conformance/scripts/check-doctrine-drift-gate.sh` (new).
**Validation**: covered by T019 below (real execution, both directions).

---

### T016 — Author `check-doctrine-manifest-completeness.mjs` (IC-04, absence guard)

**Purpose**: Deliver the absence-guard script exactly per the "3." section
above.

**Steps**:
1. Create `conformance/scripts/check-doctrine-manifest-completeness.mjs`
   (Node stdlib only — `fs`, `path` — no npm dependency).
2. Implement the block-scan `integrity_rules` counter and the
   `- ruleId:` line counter exactly as specified.
3. **Do not add any `sopFile:` reading or validation to this script** — that
   is deliberately the drift gate's job (`STRUCTURAL_ABSENCE`), not this
   one's; re-implementing it here would violate the stated division of
   labor and could mask a bug in one script behind the other appearing to
   also catch it.
4. Match the exact output-shape strings from the "3." section above (or
   functionally equivalent phrasing that still names every offender
   explicitly, never a bare count).

**Files**: `conformance/scripts/check-doctrine-manifest-completeness.mjs` (new, ~60 lines).
**Validation**: covered by T019 below (real execution, all four absence
failure modes).

---

### T017 — Author `conformance/doctrine/README.md` (IC-05, FR-006)

**Purpose**: Render the complete directive→class mapping table, summary
counts, cross-repo note, citation-anchor deviation note, coverage roadmap,
local-invocation instructions, and the `TOOL_DRIFT` exercise disclosure —
all specified verbatim in the "4." section above.

**Steps**:
1. Create `conformance/doctrine/README.md` containing, at minimum, sections
   A through G from the "4." section above (you may reformat/reorganize,
   but every fact listed must appear somewhere in the file).
2. Leave a placeholder for section F's CI timing entry (`run_id`, wall-clock
   minutes) — fill it in during T020, once a real run exists. Do not
   fabricate a number here.
3. Section G (`TOOL_DRIFT` disclosure): decide and state which of the two
   options in section G above this WP takes — do not leave it ambiguous or
   silently omit it.

**Files**: `conformance/doctrine/README.md` (new).
**Validation**: manual read-through confirms sections A–G are all present;
the mapping table's 45-row content and the 24-mapped/21-UNMAPPED summary
counts match the numbers given in the "4." section above exactly; section G
explicitly states whether `TOOL_DRIFT` was exercised in this mission.

---

### T018 — Modify `.github/workflows/conformance.yml` (IC-06, FR-004/FR-005 wiring)

**Purpose**: Wire the new job into the shared CI workflow, respecting the
PR #29 landing dependency.

**Steps**:
1. **First, confirm the actual current state of this file on your working
   branch** (do not assume either pre- or post-PR-#29 state):
   ```sh
   grep -n "^permissions:" .github/workflows/conformance.yml || echo "NO permissions key yet"
   grep -nE "uses: actions/checkout@[0-9a-f]{40}" .github/workflows/conformance.yml || echo "checkout NOT SHA-pinned yet"
   ```
   Record both results in the work log. If PR #29's changes are not yet
   present (this is expected if your branch has not been rebased onto the
   latest upstream state since PR #29 merged — confirmed merged via
   `gh pr view 29 --repo MOES-Media/spec-kitty --json state,mergedAt`),
   rebase or merge the latest upstream `main` into your working branch
   before proceeding, so you are editing the post-PR-#29 state rather than
   independently re-adding what PR #29 already added.
2. Rename the top-level `name:` to `Static Conformance`.
3. Insert `permissions: contents: read` **only if** step 1 found no
   existing `permissions:` key — otherwise leave the existing block
   untouched (see "Permissions block" above).
4. Add the new `sop-doctrine-conformance` job exactly per the YAML template
   in the "5." section above, pinning your new job's `actions/checkout` to
   match whatever convention step 1 found already in use for the existing
   job's `actions/checkout` step.
5. Confirm no `secrets:` reference exists anywhere in the file.
6. Confirm the trigger block (`on: pull_request` / `push: branches: [main]`)
   is unchanged.

**Files**: `.github/workflows/conformance.yml` (modified).
**Validation**: `grep -n "secrets:" .github/workflows/conformance.yml`
returns nothing; the new job has exactly 3 steps in the specified order; no
duplicate `permissions:` key; the new job's checkout pin matches the
existing job's checkout pin convention.

---

### T019 — Mandatory real-CLI verification (operator directive, all failure modes both ways)

This mission cannot be called done on inspection alone. Run every step below
for real and record the real, observed result (exit code, exact message
text, exact `--json`/`jq` output) in this WP's work log — a prose summary is
explicitly insufficient.

**Purpose**: Prove FR-004, FR-005's inverted discrimination, and the
absence-guard's four failure modes all behave as specified, using the actual
built muster CLI and the actual repository tree.

**Steps**:
1. **All 13 shipped manifests, clean tree, zero disallowed findings**
   (AC-1/AC-2) — same command as WP01/WP02's per-manifest checks, but now
   run across all 13 at once and also via the drift-gate script itself:
   ```sh
   for manifest in conformance/doctrine/*.yaml; do
     echo "=== $manifest ==="
     npx --yes @garrison-hq/muster@1.1.0 sop run "$manifest" --json | tee /tmp/out.json
     echo "exit code: ${PIPESTATUS[0]}"
     jq '[.lintFindings[] | select(.kind=="RULE_DRIFT" or .kind=="MISSING_SOURCE" or .kind=="MANIFEST_ERROR" or .kind=="STRUCTURAL_ABSENCE")]' /tmp/out.json
   done
   ```
   **Do not write `echo "exit code: $?"` immediately after a `| tee` pipe** —
   `$?` there is `tee`'s exit status, not muster's, so the line prints `0`
   unconditionally regardless of what muster did (this exact defect was
   found and fixed in WP01's equivalent snippet during WP02 review; it never
   shipped here only because the values happened to come out right). Use
   `${PIPESTATUS[0]}` (as corrected above) or avoid the pipe entirely (e.g.
   `out=$(... --json)`, as the actual `check-doctrine-drift-gate.sh` script
   pseudocode above already does correctly) — never trust `$?` after any
   pipeline. This applies with equal force to `check-doctrine-drift-gate.sh`
   itself (item 2 above): the script's Phase 1/2 `set +e; out=$(...);
   muster_exit=$?; set -e` pattern is correct because it is a command
   substitution, not a pipe — do not "simplify" it into a `| tee` +
   `echo $?` form, which would silently make the exit-code half of the gate
   always read `0`.
   Record all 13 pairs (exit code, filter result) verbatim — an exact count
   of 13 clean results, not "all passed."
2. **The control's inverted discrimination proof (AC-3)** — must be
   *observed producing* the finding, per the falsifiable-evidence lesson
   above:
   ```sh
   npx --yes @garrison-hq/muster@1.1.0 sop run conformance/doctrine/control/045-drifted.yaml --json \
     | jq '[.lintFindings[] | select(.kind=="RULE_DRIFT")] | length'
   # MUST print a number >= 1 — record the EXACT number and the exact
   # finding object(s), not just "it produced RULE_DRIFT"
   ```
3. **All four absence failure modes, both ways**:
   ```sh
   # (a) A rule entry silently dropped from a real manifest:
   cp conformance/doctrine/045-prs-only-and-read-intent.yaml /tmp/045.bak
   # ... remove the 045-r4 entry's lines by hand ...
   node conformance/scripts/check-doctrine-manifest-completeness.mjs
   # MUST print non-zero (1), naming "045-prs-only-and-read-intent" with "expected 4, found 3"
   cp /tmp/045.bak conformance/doctrine/045-prs-only-and-read-intent.yaml
   node conformance/scripts/check-doctrine-manifest-completeness.mjs
   # MUST print 0 again

   # (b) Manifest file entirely missing:
   mv conformance/doctrine/029-agent-commit-signing-policy.yaml /tmp/
   npx --yes @garrison-hq/muster@1.1.0 sop run conformance/doctrine/029-agent-commit-signing-policy.yaml --json
   # MUST print exit code 2, with a plain "muster: cannot read sop manifest ..." line on
   # stderr and NO JSON on stdout (this is the real, verified-during-planning behavior —
   # not the "MANIFEST_ERROR, exit 1" behavior an earlier draft of this mission wrongly assumed)
   mv /tmp/029-agent-commit-signing-policy.yaml conformance/doctrine/

   # (c) sopFile target missing (directive file deleted, or sopFile: typo'd):
   manifest=conformance/doctrine/045-prs-only-and-read-intent.yaml
   cp "$manifest" "$manifest.bak"
   sed -i 's#sopFile: .*#sopFile: "../../src/doctrine/directives/built-in/does-not-exist.directive.yaml"#' "$manifest"
   npx --yes @garrison-hq/muster@1.1.0 sop run "$manifest" --json | tee /tmp/out-absent.json
   # MUST print exit code 1
   jq '[.lintFindings[] | select(.kind=="STRUCTURAL_ABSENCE")]' /tmp/out-absent.json
   # MUST print a non-empty array
   mv "$manifest.bak" "$manifest"
   git diff --exit-code "$manifest"

   # (d) Control manifest deleted:
   mv conformance/doctrine/control/045-drifted.yaml /tmp/
   node conformance/scripts/check-doctrine-manifest-completeness.mjs
   # MUST print non-zero (1), naming the missing control manifest
   mv /tmp/045-drifted.yaml conformance/doctrine/control/
   ```
   Record every command, its real exit code, and the relevant message/JSON
   excerpt verbatim, for all four sub-cases in both directions (broken +
   restored).
4. **The full local pre-PR gate**:
   ```sh
   bash conformance/scripts/check-doctrine-drift-gate.sh \
     && node conformance/scripts/check-doctrine-manifest-completeness.mjs \
     && echo "doctrine conformance: both checks green"
   ```
   Record the exact output and confirm both scripts exit `0` on the true,
   restored tree.

**Files**: none new — this subtask only exercises T001–T018's outputs
(temporary test edits must always be restored, confirmed via
`git diff --exit-code`).
**Validation**: work log contains all recorded exit codes and message
excerpts described above, verbatim.

---

### T020 — Real GitHub Actions CI run (quickstart §8, mandatory)

This step cannot be simulated locally.

**Purpose**: Prove the modified workflow actually runs, both jobs green, in
a real GitHub Actions execution.

**Steps**:
1. Once this mission's full change set (WP01's 9 manifests, WP02's 4
   manifests, and this WP's control/scripts/README/workflow) is on a PR
   against `MOES-Media/spec-kitty` on branch
   `kitty/mission-doctrine-rule-manifests`, confirm the renamed workflow
   (`Static Conformance`) triggers.
2. Confirm **both** jobs run green: the pre-existing
   `Skills static conformance (muster)` job (unaffected by this mission)
   and the new `SOP doctrine conformance (muster)` job (all three of its
   steps green).
3. Record that run's `run_id` and wall-clock minutes in
   `conformance/doctrine/README.md`'s timing table (T017's placeholder),
   alongside M1's existing entry.
4. Independently verify the cited run:
   `gh run view <run_id> --repo MOES-Media/spec-kitty --json conclusion,headBranch,createdAt,updatedAt`
   — confirm `conclusion=success`, `headBranch` matches this mission's PR
   branch, and timestamps are consistent with the claimed wall-clock
   minutes.
5. If the PR is opened from a fork, confirm the new job still completes
   green with no secret-related failure (C-002).

**Files**: `conformance/doctrine/README.md` (fills in T017's placeholder).
**Validation**: work log records the real `run_id`, real wall-clock minutes,
both jobs' `conclusion=success`, independently re-confirmed via `gh run
view`, not merely asserted.

---

### T021 — WP03 Definition-of-Done verification gate

**Steps** (run in order):
```bash
git diff --stat                              # ONLY the owned_files changed (issue-matrix.md only if its #11 row actually needs an edit — it did not)
git diff --stat conformance/doctrine/018-doctrine-versioning-requirement.yaml  # empty — WP01/WP02's files untouched by this WP
git diff --stat src/doctrine/                # MUST show no changes
grep -n "secrets:" .github/workflows/conformance.yml   # MUST return nothing
grep -c "^permissions:" .github/workflows/conformance.yml   # MUST be exactly 1, never 2
```
Confirm T014's control-text absence check, T019's full real-execution
transcript set, and T020's real CI run are all present in the work log
before requesting review.

## Definition of Done

- [ ] Control manifest exists, `sopFile` three levels up, `ruleText` exactly
      the specified one-word mutation, `grep -F -c` = `0` check recorded
- [ ] `check-doctrine-drift-gate.sh` implements both phases plus the
      mandatory exit-code/JSON-validity failure handling; the
      `STRUCTURAL_ABSENCE` filter entry is present and not simplified away
- [ ] `check-doctrine-manifest-completeness.mjs` never reads or validates
      `sopFile:` — filename-stem pairing only
- [ ] `conformance/doctrine/README.md` contains the full 45-row mapping
      table, the 24-mapped/21-UNMAPPED summary counts, the cross-repo
      taxonomy note, the citation-anchor deviation note, the 13-directive
      coverage roadmap (with 038 and `reconcile-change-scope-tensions`
      flagged as excluded-by-construction, not merely "not covered"),
      local-invocation instructions, and an explicit `TOOL_DRIFT`
      exercise disclosure (section G — either `--env-tools` was run and
      evaluated for real, or the README states plainly that the detector
      is unexercised)
- [ ] `.github/workflows/conformance.yml` has exactly one `permissions:` key
      (not duplicated), both pre-existing actions left exactly as found
      (not re-pinned or unpinned), the new job's `actions/checkout` matches
      the existing convention, and the new job has exactly 3 steps in the
      drift-gate-then-completeness order
- [ ] No `secrets:` reference anywhere in the workflow file
- [ ] T019's real-execution transcripts recorded for: all 13 shipped
      manifests (exact count, exact clean result each), the control's
      inverted discrimination (exact finding count, not just "some"), and
      all four absence failure modes in both directions
- [ ] T020's real GitHub Actions run recorded: `run_id`, wall-clock minutes,
      both jobs `conclusion=success`, independently re-confirmed via `gh run
      view`
- [ ] No file outside `owned_files` is modified; no `src/doctrine/**` file
      or any of WP01/WP02's 13 manifest files is touched by this WP

## Risks

- **Control regression**: if a future edit "fixes" the control's mutation
  toward something that no longer discriminates, the suite fails silently.
  Mitigated by the `grep -F -c = 0` check being a required, re-runnable
  step (T014), and the exact-count assertion in T019 step 2 (not just
  "produced some RULE_DRIFT").
- **Filter simplification temptation**: `STRUCTURAL_ABSENCE` in the Phase 1
  filter looks removable to someone who has not seen the real ENOENT/
  typo'd-`sopFile` behavior. Do not remove it — see the "do not remove it"
  rationale in the "2." section above.
- **PR #29 timing**: if your branch is edited before a rebase picks up PR
  #29's already-merged changes, you risk re-adding a `permissions:` key
  that will collide once the branches converge. T018 step 1's check-first
  discipline exists specifically to avoid this.
- **Membership-only assertions**: do not write or accept any verification
  step phrased as "contains at least one finding of the required kind" for
  anything gated on an exact count — this is the specific defect the
  sibling-mission lesson above describes. Every drift-gate/completeness
  assertion in this WP is an exact count or exact vector, not membership.

## Reviewer guidance

- **Reject if** the drift-gate script's Phase 1 filter has fewer than the 4
  required finding kinds (`RULE_DRIFT`, `MISSING_SOURCE`, `MANIFEST_ERROR`,
  `STRUCTURAL_ABSENCE`).
- **Reject if** the drift-gate script does not capture and check muster's
  real exit code and JSON validity before invoking `jq`, for both phases.
- **Reject if** the completeness script reads or validates `sopFile:` in any
  way (violates the deliberate division of labor with the drift gate).
- **Reject if** the workflow file has a duplicated `permissions:` key, or if
  the existing job's actions were re-pinned/unpinned by this WP.
- **Reject if** any verification step in the work log is phrased as
  membership ("contains a RULE_DRIFT finding") rather than an exact count or
  vector, for anything this WP is responsible for gating.
- **Reject if** the work log's control-discrimination evidence (T019 step 2)
  does not show the control actually producing a `RULE_DRIFT` finding with
  an exact count — a control that has never been observed to fire is
  unverified, not merely under-documented.
- **Reject if** T020's `run_id` cannot be independently confirmed via
  `gh run view` to have `conclusion=success` on the correct branch.
- Confirm `git diff --stat` shows changes in exactly the 5 `owned_files`
  entries and none of WP01/WP02's 13 manifest files.

Implementation command: `spec-kitty agent action implement WP03 --agent claude`
