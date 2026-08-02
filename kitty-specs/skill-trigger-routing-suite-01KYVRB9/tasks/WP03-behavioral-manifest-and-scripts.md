---
work_package_id: WP03
title: Behavioral manifest and verification scripts
dependencies:
- WP01
- WP02
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- NFR-002
- NFR-003
planning_base_branch: kitty/mission-skill-trigger-routing-suite-01KYVRB9
merge_target_branch: kitty/mission-skill-trigger-routing-suite-01KYVRB9
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-skill-trigger-routing-suite-01KYVRB9. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-skill-trigger-routing-suite-01KYVRB9 unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
- T019
- T020
history:
- timestamp: '2026-07-31T13:37:19Z'
  agent: planner-priti
  action: WP prompt generated via staged tasks-outline/tasks-packages
agent_profile: node-norris
authoritative_surface: conformance/
create_intent:
- conformance/skills/behavioral-manifest.yaml
- conformance/scripts/check-trigger-queryset-shape.mjs
- conformance/scripts/check-twin-phrasing.mjs
- conformance/scripts/check-control-discrimination.mjs
- conformance/scripts/check-evidence-artifact-shape.mjs
execution_mode: code_change
model: ''
owned_files:
- conformance/skills/behavioral-manifest.yaml
- conformance/scripts/check-trigger-queryset-shape.mjs
- conformance/scripts/check-twin-phrasing.mjs
- conformance/scripts/check-control-discrimination.mjs
- conformance/scripts/check-evidence-artifact-shape.mjs
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP03 – Behavioral Manifest and Verification Scripts

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `node-norris`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Author `conformance/skills/behavioral-manifest.yaml` (14 cases: 13 real +
1 control, referencing WP01/WP02's now-merged query-set files by name) and
four dependency-free Node ≥22 scripts:
`check-trigger-queryset-shape.mjs` (FR-001), `check-twin-phrasing.mjs`
(FR-002), `check-control-discrimination.mjs` (FR-004, this plan's own
addition — spec.md's FR-004 verification command was prose, not a script),
and `check-evidence-artifact-shape.mjs` (FR-005).

## Context

This is lane-b's first WP, depends on lane-a (WP01+WP02) completing first —
not merely non-colliding with it (`plan.md`'s own Findings item 4). Every
`querySetPath` in the manifest you write must match a real, already-merged
file from WP01 or WP02 exactly.

**C-001 diff-scope correction** (plan.md Findings item 3, research.md §6):
spec.md's C-001 states the allowed script glob as `check-trigger-*.mjs` —
that glob matches only `check-trigger-queryset-shape.mjs`. Your other three
scripts (`check-twin-phrasing.mjs`, `check-control-discrimination.mjs`,
`check-evidence-artifact-shape.mjs`) do not match it. This is a known,
flagged imprecision in spec.md's own constraint prose, not a blocker —
`contracts/verification-scripts-cli-contract.md` states the corrected,
exhaustive four-script list explicitly, and this WP's own `owned_files`
(above) is the authority for what you may write. Do not restrict yourself to
the glob's literal match.

**Amendment status**: this imprecision is being **carried forward via task
files, not amended into spec.md** — it is a verification-design correction
(the constraint's own prose was imprecise relative to the mission's already-
committed deliverables), not a change to what C-001 actually requires
(scope stays: no `SKILL.md` edits, diff confined to the named surfaces).

### `runsErrored` — read this before writing `check-control-discrimination.mjs`

`runsErrored` is **not** a case-level JSON field in muster's `skills run
--json` output (research.md §2, data-model.md). `SkillsCaseResult` has only
`errored?: boolean` (case-level, structural failures only — bad
`skillDir`/`querySetPath`, never a network failure). The actual per-run error
counts live two levels deep:

```
runsErrored(case) =
  sum(case.shouldTriggerAxis.queryBreakdown[].runsErrored) +
  sum(case.nearMissAxis.queryBreakdown[].runsErrored)
```

This derived sum — not `passed`, not `triggerRate` — is the **only** field
that distinguishes "the control discriminated because the model is good"
from "the control discriminated because the endpoint is dead and every call
errored." `passed: false` is true in **both** conditions by construction (a
fully dead endpoint makes every `runSingleQuery` call throw, so
`runsTriggered = 0` for both axes, and `near-miss` passes — `0 < threshold` —
while `should-trigger` fails — `0 < threshold` — giving the same
`passed: false` shape as a healthy, well-discriminating run). Any
implementation of `check-control-discrimination.mjs` that reads `passed`
alone without computing the derived sum will pass both of the cross-wired
rejection cases in T018 below, which is exactly the bug this script exists
to prevent.

## Subtask T015: Author `behavioral-manifest.yaml`

**Purpose**: 14 cases — one per WP01/WP02 query-set file, plus the control.

**Steps**:
1. Confirm all 13 non-control query-set files and the 1 control file exist
   at their expected paths under `conformance/skills/trigger-queries/`
   (10 from WP01, 4 from WP02) before writing a single manifest line.
2. Write the `defaults` block:
   ```yaml
   defaults:
     model: gpt-4o-mini        # D-2, matches muster's own unset-MUSTER_MODEL fallback
     runsPerQuery: 3
     threshold: 0.5
   ```
3. Write 13 non-control cases, one per query-set file. Each case:
   ```yaml
   - id: <skill-id>                       # or "<skill-id>-run-family" for the
                                           # run-family-purpose case over a
                                           # shared skillDir
     type: behavioral
     skillDir: "../../src/doctrine/skills/<skill-id>"
     profile: base
     querySetPath: "trigger-queries/<skill-id>-<purpose>-queries.yaml"
     runsPerQuery: 3
     threshold: 0.5
     isControl: false
   ```
   Two `id`s per shared run-family skill (e.g. `spk-run-next` and
   `spk-run-next-run-family`), same `skillDir`, different `querySetPath`
   (research.md §8).
4. Write the control case:
   ```yaml
   - id: rigged-impossible-control
     type: behavioral
     skillDir: "../../src/doctrine/skills/ad-hoc-profile-load"  # placeholder dir,
                                           # irrelevant once isControl substitutes
                                           # name+description (research.md §4)
     profile: base
     querySetPath: "trigger-queries/rigged-impossible-control-queries.yaml"
     runsPerQuery: 3
     threshold: 0.5
     isControl: true                       # sole `true` in the manifest
   ```
5. Validate the manifest is well-formed YAML and every `querySetPath`
   resolves to a real file: `python3 -c "import yaml; yaml.safe_load(open('conformance/skills/behavioral-manifest.yaml'))"`
   plus a loop checking each referenced path with `os.path.exists`.

**Files**: `conformance/skills/behavioral-manifest.yaml` (new, ~120-150 lines).
**Validation**: 14 cases total, exactly one `isControl: true`; every
`querySetPath` exists on disk.

## Subtask T016: `check-trigger-queryset-shape.mjs` (FR-001)

**Purpose**: Exit `0` when every given file has ≥8 entries per axis and all
required fields; exit `1` naming the specific file/field otherwise.

**Steps**:
1. Implement per `contracts/verification-scripts-cli-contract.md` §1: args =
   one or more YAML file paths; checks `id`, `source`, `threshold` present;
   `shouldTrigger`/`nearMiss` both arrays with `.length >= 8`.
2. **RED** (prove the script itself can fail, against a fresh placeholder —
   the real files already exist from WP01/WP02, so use a scratch copy, not
   the committed ones):
   ```sh
   cp conformance/skills/trigger-queries/spk-run-next-duplicate-pair-queries.yaml /tmp/backup1.yaml
   python3 -c "
   import yaml
   d = yaml.safe_load(open('conformance/skills/trigger-queries/spk-run-next-duplicate-pair-queries.yaml'))
   d['shouldTrigger'] = d['shouldTrigger'][:7]
   yaml.safe_dump(d, open('conformance/skills/trigger-queries/spk-run-next-duplicate-pair-queries.yaml','w'))
   "
   node conformance/scripts/check-trigger-queryset-shape.mjs conformance/skills/trigger-queries/*.yaml
   echo "rejection exit code: $?"   # MUST be 1, naming this exact file and the shouldTrigger axis
   cp /tmp/backup1.yaml conformance/skills/trigger-queries/spk-run-next-duplicate-pair-queries.yaml
   git diff --exit-code conformance/skills/trigger-queries/   # confirm no residual change
   ```
3. **GREEN**:
   ```sh
   node conformance/scripts/check-trigger-queryset-shape.mjs conformance/skills/trigger-queries/*.yaml
   echo "GREEN exit code: $?"   # MUST be 0
   ```
4. Commit the script only after both proofs are recorded (RED proof does not
   require its own commit here, since it mutates and restores WP01/WP02's
   already-merged files rather than adding new content — record the exit
   codes in the mission work log instead).

**Files**: `conformance/scripts/check-trigger-queryset-shape.mjs` (new, Node stdlib only).
**Validation**: exit 1 on the 7-entry rejection case (naming the file), exit
0 on the real 14 files, `git diff --exit-code` confirms the temporary
mutation left no residue.

## Subtask T017: `check-twin-phrasing.mjs` (FR-002)

**Purpose**: Exit `0` when every declared pair/triple relationship is
satisfied; exit `1` naming the unsatisfied relationship otherwise.

**Steps**:
1. Implement per `contracts/verification-scripts-cli-contract.md` §2: args =
   the trigger-queries directory. Load the duplicate-pair/run-family
   declaration (`data-model.md` "Duplicate Pair / Run-Family Cluster") as a
   small in-script constant (or `conformance/skills/clusters.yaml` if you
   prefer separating data from logic — your call, not fixed by the plan).
   For each declared pair/triple, load files by the
   `<skill-id>-<purpose>-queries.yaml` naming convention — **never** by
   walking the manifest's case list (so the check stays meaningful even if a
   manifest case is temporarily commented out).
2. Checks: for pair `(A, B)`, ≥1 string in `A.nearMiss` byte-identical to a
   string in `B.shouldTrigger`, and symmetrically; for the run-family triple,
   each member's `nearMiss` contains ≥1 string from each of the other two
   members' `shouldTrigger`.
3. **RED** (rejection case, temporary mutation + restore):
   ```sh
   cp conformance/skills/trigger-queries/spk-run-next-run-family-queries.yaml /tmp/backup2.yaml
   python3 -c "
   import yaml
   d = yaml.safe_load(open('conformance/skills/trigger-queries/spk-run-next-run-family-queries.yaml'))
   d['nearMiss'] = ['unrelated filler query ' + str(i) for i in range(8)]
   yaml.safe_dump(d, open('conformance/skills/trigger-queries/spk-run-next-run-family-queries.yaml','w'))
   "
   node conformance/scripts/check-twin-phrasing.mjs conformance/skills/trigger-queries/
   echo "rejection exit code: $?"   # MUST be 1, naming the spk-run-next run-family relationship
   cp /tmp/backup2.yaml conformance/skills/trigger-queries/spk-run-next-run-family-queries.yaml
   git diff --exit-code conformance/skills/trigger-queries/
   ```
4. **GREEN**:
   ```sh
   node conformance/scripts/check-twin-phrasing.mjs conformance/skills/trigger-queries/
   echo "GREEN exit code: $?"   # MUST be 0
   ```

**Files**: `conformance/scripts/check-twin-phrasing.mjs` (new).
**Validation**: exit 1 on the stripped-near-miss rejection case (naming the
relationship), exit 0 on the real files, no residual mutation.

## Subtask T018: `check-control-discrimination.mjs` (FR-004)

**Purpose**: `<report.json> --mode healthy|dead-endpoint` — compute the
derived `runsErrored(case)` sum (see Context above) for the `isControl: true`
case and assert the mode-appropriate expectation.

**Steps**:
1. Implement per `contracts/verification-scripts-cli-contract.md` §4:
   - Find the case where `isControl === true`. Exit `2` if zero or more than
     one such case exists (a manifest-authoring bug, not a discrimination
     finding).
   - Compute `runsErrored(case)` per the derived-sum formula above.
   - `--mode healthy`: exit `0` iff `passed === false && runsErrored === 0`;
     else exit `1` naming which condition failed.
   - `--mode dead-endpoint`: exit `0` iff `passed === false && runsErrored >
     0`; else exit `1`.
   - Omitted `--mode`: exit `2` with a usage message — **never** a silent
     default to either mode.
2. Because this WP does not yet have a live endpoint (that is WP04's job),
   prove the script's **logic** here against two small, hand-written synthetic
   `report.json` fixtures (not committed — scratch files under `/tmp`,
   modeled on the JSON shapes in `data-model.md`'s "Trigger Verdict"
   section):
   - A synthetic "healthy" report: the control case has
     `shouldTriggerAxis.queryBreakdown` and `nearMissAxis.queryBreakdown`
     entries all with `runsErrored: 0`, and `passed: false`.
   - A synthetic "dead-endpoint" report: same case, but every
     `queryBreakdown[].runsErrored` equals `runsPerQuery` (e.g. `3`), and
     `passed: false`.
3. Run the four proofs against these synthetic fixtures:
   ```sh
   node conformance/scripts/check-control-discrimination.mjs /tmp/synthetic-healthy.json --mode healthy
   echo "exit: $?"   # MUST be 0
   node conformance/scripts/check-control-discrimination.mjs /tmp/synthetic-dead.json --mode dead-endpoint
   echo "exit: $?"   # MUST be 0
   node conformance/scripts/check-control-discrimination.mjs /tmp/synthetic-dead.json --mode healthy
   echo "exit: $?"   # MUST be 1 -- proves the script isn't just checking passed===false
   node conformance/scripts/check-control-discrimination.mjs /tmp/synthetic-healthy.json --mode dead-endpoint
   echo "exit: $?"   # MUST be 1 -- inverse
   node conformance/scripts/check-control-discrimination.mjs /tmp/synthetic-healthy.json
   echo "exit: $?"   # MUST be 2 -- no --mode, never a silent default
   ```
4. Record all five exit codes in the mission work log. **This synthetic
   proof is necessary but not sufficient** — WP04 must re-run this exact
   five-proof sequence against **real** `report-healthy.json`/
   `report-dead.json` captured from a live `MUSTER_ENDPOINT` (quickstart.md
   §4) before FR-004/SC-002 can be marked done. Do not let this WP's
   synthetic-fixture proof be mistaken for that live proof — flag this
   explicitly to the WP04 implementer in your handoff notes.

**Files**: `conformance/scripts/check-control-discrimination.mjs` (new).
**Validation**: all five synthetic-fixture exit codes match the contract
(0, 0, 1, 1, 2) — this is the FR-004 both-condition sequencing at the
unit-test level; WP04 repeats it at the live-endpoint level.

## Subtask T019: `check-evidence-artifact-shape.mjs` (FR-005)

**Purpose**: Validate a committed evidence artifact against
`contracts/evidence-artifact.schema.json`, plus an independent
credential-leak text scan.

**Steps**:
1. Implement per `contracts/verification-scripts-cli-contract.md` §3: args =
   one evidence-artifact JSON path. Validates against the schema (required
   fields, types, `endpointHost` contains no `@`) **and** separately scans
   the raw file text for a `MUSTER_API_KEY`-shaped substring.
2. **RED** (prose-only placeholder):
   ```sh
   mkdir -p conformance/skills/trigger-evidence
   echo '{"summary": "suite passed"}' > conformance/skills/trigger-evidence/placeholder.json
   node conformance/scripts/check-evidence-artifact-shape.mjs conformance/skills/trigger-evidence/placeholder.json
   echo "RED exit code: $?"   # MUST be 1, naming every missing required field
   rm conformance/skills/trigger-evidence/placeholder.json
   ```
3. **Credential-leak rejection case**:
   ```sh
   echo '{"timestamp":"2026-07-31T00:00:00Z","model":"gpt-4o-mini","endpointHost":"api.openai.com/v1?api_key=sk-XXXXXXXXXXXXXXXXXXXX","cases":[]}' > /tmp/leaky.json
   node conformance/scripts/check-evidence-artifact-shape.mjs /tmp/leaky.json
   echo "rejection exit code: $?"   # MUST be 1, naming the credential-leak match specifically, not just schema violation
   ```
4. **GREEN**: construct one small, hand-written valid fixture matching the
   schema exactly (`data-model.md`'s Evidence Artifact example) and confirm
   exit `0`. Do not commit this fixture — WP04 produces the real, first
   committed evidence artifact from an actual live run.

**Files**: `conformance/scripts/check-evidence-artifact-shape.mjs` (new).
**Validation**: RED (prose-only) exits 1 naming missing fields; credential-
leak case exits 1 naming the leak; a schema-valid synthetic fixture exits 0.

## Subtask T020: FR-003 skip-guard verification + validate-only preflight

**Purpose**: Confirm the manifest's skip-guard behavior (unset endpoint →
every behavioral case `skipped: true`) using the real, now-complete
manifest, and run the mission's `finalize-tasks --validate-only` preflight
before this WP's final commit.

**Steps**:
1. Cache-warm the pinned CLI if not already done:
   ```sh
   npm install --no-save @garrison-hq/muster@1.2.1
   npx --offline @garrison-hq/muster@1.2.1 --version
   ```
2. Unset-endpoint proof (the graceful-skip path):
   ```sh
   unset MUSTER_ENDPOINT MUSTER_API_KEY
   npx --offline @garrison-hq/muster@1.2.1 skills run conformance/skills/behavioral-manifest.yaml --json \
     | node -e "const r=JSON.parse(require('fs').readFileSync(0)); process.exit(r.results.some(c=>c.type==='behavioral' && c.skipped) ? 1 : 0)"
   echo "exit code: $?"   # MUST be 1 -- every behavioral case skipped, proving the guard fires
   ```

   (Corrected during WP04: muster's real `skills run --json` top-level shape
   is `{ok, total, passed, failed, skipped, results}` — no top-level `cases`
   key. The `r.cases.some(...)` form throws at runtime and coincidentally
   still exits non-zero, passing this step's gate for the wrong reason.)
   This also incidentally proves the manifest itself parses and every
   `querySetPath`/`skillDir` resolves — a structural smoke test of T015's
   work, independent of any live endpoint.
3. Confirm the offline static suite is unaffected (NFR-001 partial check —
   full before/after diff is WP04's job once the whole mission's changes are
   in, but a spot check here catches an early regression):
   ```sh
   npx --offline @garrison-hq/muster@1.2.1 skills run conformance/skills/manifest.yaml --json > /tmp/static-after-wp03.json
   ```
   (Save this output; WP04 will diff it against a pre-mission baseline.)
4. NFR-002 credential grep on this WP's own files:
   ```sh
   command grep -rE '(sk-|api[_-]?key\s*[:=]\s*["\047][A-Za-z0-9]{16,})' conformance/skills/behavioral-manifest.yaml
   echo "exit code: $?"   # MUST be 1 (no match)
   ```
5. Run the mission-level preflight (this is required before finalize-tasks'
   mutating command runs at the tasks-finalization step, and is good
   practice again here since this WP changes WP frontmatter-adjacent
   surfaces):
   ```sh
   spec-kitty agent mission finalize-tasks --validate-only --mission skill-trigger-routing-suite-01KYVRB9 --json
   ```
   Report any `missing_requirement_refs_wps`, `unknown_requirement_refs`, or
   `unmapped_functional_requirements` rather than proceeding past them.
6. Commit the manifest and four scripts as this WP's final commit set (the
   individual RED/GREEN proofs in T016-T019 do not each require their own
   commit if they only mutate/restore scratch or already-merged files; the
   scripts and manifest themselves are new files and must be committed).
   Run `spec-kitty agent tasks mark-status T015 T016 T017 T018 T019 T020
   --status done`.

**Files**: none new (verification only); commits the manifest + 4 scripts
authored in T015-T019.
**Validation**: unset-endpoint proof exits 1 (all skipped); credential grep
exits 1 (no match); `finalize-tasks --validate-only` reports no blocking
issues.

## Definition of Done

- `behavioral-manifest.yaml` exists with exactly 14 cases (13 non-control +
  1 control), every `querySetPath` resolving to a real WP01/WP02 file.
- Four scripts exist under `conformance/scripts/`, each proven against its
  RED/rejection case and its GREEN case (T016-T019), with exit codes
  recorded in the mission work log.
- `check-control-discrimination.mjs`'s five synthetic-fixture exit codes
  (0, 0, 1, 1, 2) are recorded — understood as necessary-but-not-sufficient
  pending WP04's live-endpoint repeat of the same five-proof sequence.
- FR-003's unset-endpoint skip-guard proof exits 1 (every case skipped).
- NFR-002 credential grep exits 1 (no match) on this WP's own files.
- `finalize-tasks --validate-only` reports no blocking requirement-mapping
  or dependency issues.
- `spec-kitty agent tasks mark-status` run for T015-T020.

## Risks

- **`runsErrored` misimplemented as a top-level field read** — the single
  highest-value correctness risk in this mission (per `plan.md`'s own IC-05
  risk note): a bug here silently launders a dead-endpoint run as a valid
  discrimination proof. Mitigated by T018's four cross-wired/no-mode
  synthetic proofs being mandatory, not optional.
- **Manifest references a file WP01/WP02 renamed after merge** — mitigated
  by T015's explicit existence check before any manifest content is written.
- **Mistaking T018's synthetic proof for the live proof** — explicitly
  flagged in T018 step 4; WP04 must not skip its own live re-proof on the
  assumption this WP already "proved FR-004."

## Reviewer Guidance

- Confirm each script's RED/rejection proof was actually run (exit codes
  recorded), not merely asserted in prose.
- Independently verify the `runsErrored(case)` derivation in
  `check-control-discrimination.mjs`'s source against the formula in this
  prompt's Context section and in `data-model.md` — this is the mission's
  central correctness risk.
- Confirm `check-twin-phrasing.mjs` loads pair/triple declarations by
  filename convention, not by walking the manifest's case list.
- Confirm no file touches `src/doctrine/skills/**` or `kitty-specs/`.

## Implementation Command

```sh
spec-kitty agent action implement WP03 --agent claude
```

## Activity Log

- 2026-08-01T22:46:55Z – unknown – T015: behavioral-manifest.yaml committed at a5115ff72 (14 cases: 13 real + 1 control). Pre-commit validated via python3 yaml.safe_load: 14 cases, exactly one isControl:true, every querySetPath/skillDir resolves on disk, no duplicate ids, NFR-002 grep exits 1 (no match).
- 2026-08-01T22:47:08Z – unknown – T016: check-trigger-queryset-shape.mjs committed at 9c6980327 (FR-001). Canonicalizes WP01/WP02's inline shape-gate check, fixing two findings from WP01's review: exit 1 on zero input files (was silently exit 0 in the inline predecessor -- empty glob, empty loop body, unchanged ok=True accumulator), and per-axis distinctness/non-blank checks (muster's gradeAxis sums every entry without deduplicating, trigger.ts:242-244). RED proofs: zero-arg invocation exit 1; empty-glob passthrough exit 1; 7-entry axis (constructed via the mission's own yaml.safe_dump mutation procedure) exit 1 naming the file+axis; synthetic blank+duplicate fixture exit 1 naming both. GREEN: all 14 real WP01/WP02 files exit 0 (reproduces WP01's 10-file and WP02's 4-file inline results exactly). Byte-identical stdout across two runs. Discovered mid-implementation: PyYAML's safe_dump reformats list items to zero-indent/unquoted, which the first parser draft could not read (would have reported '0 entries' instead of '7 entries' -- fixed before commit, not a shipped defect).
- 2026-08-01T22:47:17Z – unknown – T017: check-twin-phrasing.mjs committed at 0706a2eed (FR-002). Loads clusters by filename convention (never by walking behavioral-manifest.yaml's case list). Run-family triple comparison matches WP02's own verified T014 self-check exactly: near-miss read from each member's run-family file, should-trigger for the other two members read from their duplicate-pair file (not their run-family file) -- discovered during implementation that a naive run-family-to-run-family comparison, while producing the same result today, does not match what WP02 actually verified. RED: no-arg usage exit 1; empty directory (13 missing files) exit 2, naming each; stripped spk-run-next-run-family nearMiss (mission's own mutation procedure) exit 1 naming both now-unsatisfied directions. GREEN: 5 pairs + 1 triple, 16 ordered directions, exit 0 -- reproduces WP01's 10-direction and WP02's 6-direction inline results exactly. Byte-identical stdout across two runs.
- 2026-08-01T22:47:27Z – unknown – T018: check-control-discrimination.mjs committed at b26c734b5 (FR-004, new script -- spec.md's own verification command was prose). Computes derived runsErrored(case) = sum(shouldTriggerAxis.queryBreakdown[].runsErrored) + sum(nearMissAxis.queryBreakdown[].runsErrored) from the RAW muster --json report's .results array (never reads a nonexistent top-level runsErrored field). --mode required, no default: omission is itself a rejection case. Proven against two hand-written synthetic fixtures modeled on data-model.md's Trigger Verdict shape (no live endpoint available to this WP -- that is WP04's job; this synthetic proof is necessary but not sufficient, flagged explicitly for WP04). Five-proof sequence observed exit codes: --mode healthy vs healthy fixture = 0; --mode dead-endpoint vs dead fixture = 0; --mode healthy vs dead fixture (cross-wired) = 1; --mode dead-endpoint vs healthy fixture (cross-wired inverse) = 1; omitted --mode = 2. All five match the contract exactly (0,0,1,1,2). Additional proofs: zero/two isControl cases both exit 2; skipped control case (no axis data) exit 2; malformed JSON exit 2; missing report-path exit 2; invalid --mode value exit 2; control passed:true exit 1. Byte-identical stdout across two runs.
- 2026-08-01T22:47:35Z – unknown – T019: check-evidence-artifact-shape.mjs committed at 2d760e434 (FR-005). Hand-rolled validator against contracts/evidence-artifact.schema.json plus an independent credential-leak text scan over raw file bytes (schema alone cannot catch a full-URL endpointHost with an embedded api_key query param, since it contains no '@'). RED (prose-only {"summary":"suite passed"}): exit 1, naming all 4 missing top-level fields plus the unexpected 'summary' field. Credential-leak case (endpointHost as full URL with ?api_key=sk-XXXX...): exit 1, naming the credential-leak match specifically and distinctly from the also-reported schema violation. GREEN (data-model.md's own worked Evidence Artifact example): exit 0. Additional falsification: endpointHost containing '@' exit 1; out-of-range triggerRate exit 1; missing/unreadable file exit 2. Byte-identical stdout across two runs.
- 2026-08-01T22:47:49Z – unknown – T020: cache-warmed @garrison-hq/muster@1.2.1 (npx --offline --version confirms exact pin, not a range). Unset-endpoint skip-guard proof: found and worked around a real bug in the mission's own prescribed one-liner (spec.md FR-003 verification command, quickstart.md section 3, and this task file's own T020 step 2 all read r.cases.some(...), but muster's actual --json top-level shape is {ok,total,passed,failed,skipped,results} per src/cli/index.ts:1293/1583 at v1.2.1 -- there is no top-level 'cases' key). Run as literally written, the one-liner throws (Cannot read properties of undefined) and coincidentally still exits 1, passing the T020 gate for the wrong reason -- exactly this programme's vacuous-check pattern. Ran the corrected r.results.some(...) version instead: exit 1, all 14 behavioral cases skipped (confirmed via r.results.filter(c=>c.type==='behavioral').every(c=>c.skipped===true)). Anti-vacuity: constructed a synthetic report with skipped:false on every behavioral case and confirmed the corrected one-liner exits 0. This run also smoke-tested the manifest structurally (all 14 querySetPath/skillDir resolved, muster read and ran it without error). Flagging this .cases/.results discrepancy for WP04, which reuses the same one-liner pattern in the workflow file and README. NFR-001 spot check: conformance/skills/manifest.yaml (static suite) still reports total:54, ok:true, skipped:0 -- unaffected by this WP's additions. NFR-002 grep on behavioral-manifest.yaml: exit 1 (no match) -- the only file this NFR's stated command names for this WP. finalize-tasks --validate-only --mission skill-trigger-routing-suite-01KYVRB9 --json: result=validation_passed, no missing_requirement_refs_wps/unknown_requirement_refs/unmapped_functional_requirements; one informational (non-blocking) ownership_warning that WP04's trigger-evidence/** glob matches zero files yet, expected since WP04 has not run.
