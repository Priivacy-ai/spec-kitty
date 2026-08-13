# Contract: this mission's four verification scripts

**Mission**: `skill-trigger-routing-suite-01KYVRB9` | **Date**: 2026-07-31

Four scripts, all `conformance/scripts/*.mjs`, all lane-b (`write_scope`
per `plan.md`'s Work-Package Outline). This file exists so lane-a (query
sets) and lane-b (scripts/workflow/README) can be built independently
without either lane reading the other's source, mirroring
`sk-skills-static-conformance-01KYG7GE`'s own
`completeness-check-cli-contract.md` pattern. Every exit code below must be
proven against its stated rejection case during implementation (this
programme's ten-broken-verification-command history) — this file states
the *contract*, not the proof; the proof is `quickstart.md`.

Amendment to C-001's diff-scope prose (research.md §6): the exhaustive,
correct script filename set for this mission is these four names, not the
`check-trigger-*.mjs` glob spec.md's Constraints table states (that glob
matches only the first script below). `plan.md`'s Work-Package Outline
carries this correction into lane-b's actual `write_scope`.

---

## 1. `check-trigger-queryset-shape.mjs` (FR-001)

```sh
node conformance/scripts/check-trigger-queryset-shape.mjs conformance/skills/trigger-queries/*.yaml
```

- **Arguments**: one or more query-set YAML file paths (shell-globbed by
  the caller; the script itself takes no glob logic).
- **Checks per file**: `id`, `source`, `threshold` present; `shouldTrigger`
  and `nearMiss` are both arrays with `.length >= 8`.
- **Exit `0`**: every file passes every check.
- **Exit `1`**: at least one file fails at least one check; stdout/stderr
  names the specific file and the specific failing field (e.g.
  `spk-run-next-duplicate-pair-queries.yaml: shouldTrigger has 7 entries, need >= 8`).
- **Rejection case to construct and run** (per FR-001's stated
  falsification condition): a fixture with exactly 7 `shouldTrigger`
  entries must exit `1` naming that file and field — not merely "exit
  nonzero," per the ten-broken-verification-command history (`grep -c`'s
  inverted exit code and friends are exactly the class of bug a bare
  "nonzero" check would hide).

## 2. `check-twin-phrasing.mjs` (FR-002)

```sh
node conformance/scripts/check-twin-phrasing.mjs conformance/skills/trigger-queries/
```

- **Arguments**: the trigger-queries directory. Loads the duplicate-pair/
  run-family declaration (data-model.md's Duplicate Pair / Run-Family
  Cluster section) and, for each declared pair/triple, the relevant files
  by the `<skill-id>-<purpose>-queries.yaml` naming convention
  (research.md §8) — never by walking manifest cases.
- **Checks**: for every declared pair `(A, B)`, at least one string in
  `A`'s `nearMiss` is byte-identical to a string in `B`'s `shouldTrigger`,
  and symmetrically; for every declared run-family triple, each member's
  `nearMiss` contains at least one string from each of the other two
  members' `shouldTrigger`.
- **Exit `0`**: every declared relationship satisfied.
- **Exit `1`**: names the specific unsatisfied pair/triple and direction
  (e.g. `spk-run-next -> spec-kitty-runtime-next: no near-miss match found`).
- **Rejection case**: a pair where `A`'s `nearMiss` is populated but shares
  zero strings with `B`'s `shouldTrigger` must exit `1` (FR-002's stated
  falsification condition) — construct this by temporarily emptying one
  file's borrowed phrase before restoring it.

## 3. `check-evidence-artifact-shape.mjs` (FR-005)

```sh
node conformance/scripts/check-evidence-artifact-shape.mjs conformance/skills/trigger-evidence/<file>.json
```

- **Arguments**: one evidence artifact JSON path.
- **Checks**: validates against
  `contracts/evidence-artifact.schema.json` (required fields present,
  types correct, `endpointHost` contains no `@`) **and** additionally scans
  the raw file text for a `MUSTER_API_KEY`-shaped substring
  (NFR-002-equivalent guard scoped to this one file, redundant with but
  independent of the repo-wide NFR-002 grep).
- **Exit `0`**: schema-valid and no credential-shaped substring found.
- **Exit `1`**: names the specific missing/malformed field, or the specific
  credential-leak match.
- **Rejection cases** (both must be constructed and run, per FR-005's
  stated falsification condition):
  1. A prose-only evidence file (`{"summary": "suite passed"}`) must exit
     `1` naming the missing required fields — this is the exact failure
     mode a sibling mission shipped (a control recorded as prose that
     re-measured differently weeks later).
  2. An evidence file whose `endpointHost` is a full URL with an embedded
     `?api_key=...` query parameter must exit `1` naming the credential-leak
     match, not merely the schema violation (a URL is still a valid JSON
     string, so schema-only validation would silently pass this case).

## 4. `check-control-discrimination.mjs` (FR-004 — new, plan-level addition, research.md §7)

```sh
node conformance/scripts/check-control-discrimination.mjs <report.json> --mode healthy
node conformance/scripts/check-control-discrimination.mjs <report.json> --mode dead-endpoint
```

- **Arguments**: the raw `skills run --json` report (not the summarized
  evidence artifact — this script reads muster's own output directly, since
  it runs *before* the evidence-summarization step and must not depend on
  it), plus a required `--mode` flag (no default — an omitted mode must
  itself be a rejection case, see below).
- **Logic**:
  1. Find the case where `isControl === true`. Exit `2` (script-internal
     error, distinct from a discrimination failure) if no such case exists
     or more than one does — this is a manifest-authoring bug, not a
     discrimination-control finding.
  2. Compute `runsErrored(case)` per the derived-sum formula in
     `data-model.md` (Trigger Verdict section).
  3. **Both modes**: exit `1` unless `case.passed === false` **and**
     `case.nearMissAxis.passed === true`. The second half is not
     redundant with the first. muster computes
     `passed = shouldTriggerAxis.passed && nearMissAxis.passed`
     (`src/adapters/skills/trigger.ts:468`, commit `16f0d34c` / `v1.2.1`)
     over two axes with opposite predicates on the same rate (`:242-250`),
     so a model that calls the single offered tool on every query scores
     should-trigger `1.000` (axis passes) and near-miss `1.000` (axis
     fails) and yields `passed: false, runsErrored: 0` — the same shape a
     healthy discriminating run produces. Reading `passed` and
     `runsErrored` alone therefore accepts the exact scenario FR-004's
     control exists to catch (MOES-Media/spec-kitty#25 §8, "a
     permanently-triggering model+prompt combination would look like a
     healthy suite"). Requiring the near-miss axis verdict, combined with
     `passed !== true`, pins both axis facts: it also implies
     `shouldTriggerAxis.passed === false`. A dead endpoint errors every
     run, leaving near-miss at rate `0` and that axis passing, so this
     condition is mode-independent and costs the dead-endpoint proof
     nothing. The real healthy control measured should-trigger `0.083` /
     near-miss `0.000`.
  4. `--mode healthy`: additionally requires `runsErrored(case) === 0`;
     otherwise exit `1` naming which condition failed (e.g.
     `runsErrored=12, expected 0 -- endpoint may be unhealthy`, or
     `passed=true -- the model unexpectedly invoked the rigged tool`, or
     `nearMissAxis.passed=false, expected true (observed near-miss
     triggerRate 1.000 ...)`).
  5. `--mode dead-endpoint`: additionally requires `runsErrored(case) > 0`;
     otherwise exit `1` (e.g.
     `runsErrored=0 -- endpoint did not actually fail, this is not a valid
     dead-endpoint proof run`).
- **Rejection cases** (both directions, this is the FR-004 both-condition
  sequencing itself — see `plan.md`'s Verification Strategy and
  `quickstart.md` §4):
  1. Run `--mode healthy` against a report captured while
     `MUSTER_ENDPOINT` pointed at an unreachable host → must exit `1`
     (this is the actual rejection case: a healthy-mode assertion run
     against dead-endpoint data must fail, proving the script does not
     just check `passed===false` alone, which both conditions satisfy).
  2. Run `--mode dead-endpoint` against a report captured against a live,
     healthy endpoint → must exit `1` (the inverse rejection case).
  3. Omit `--mode` entirely → must exit `2` with a usage message, never
     silently default to either mode (an unflagged default is exactly the
     kind of ambiguity `[ ]`-with-empty-operand and ungated `grep`
     one-liners have produced elsewhere in this programme).
  4. Run either mode against a report whose control case is
     permanently-triggering (both axes at rate `1.000`, hence
     `passed: false, runsErrored: 0`, `nearMissAxis.passed: false`) → must
     exit `1`. This is the rejection case that distinguishes "the grader
     discriminates" from "the model calls everything"; without it the
     control reports success in precisely the situation it was written to
     detect. Pinned by
     `tests/cross_cutting/test_check_control_discrimination.py`, which
     mutates a genuine live raw report
     (`tests/fixtures/skill_trigger_routing/report-healthy-live.json`)
     rather than hand-building a fixture in the shape the check happens to
     look for.

## Exit-code reservation across all four scripts

`0` = passed its specific check. `1` = failed its specific check, naming
the specific failure. `2` = the script itself could not run its check at
all (malformed input it cannot even parse, missing required CLI argument,
zero or multiple control cases where exactly one is required) — reserved
consistently with muster's own CLI convention of never overloading `2` with
a graded-failure meaning (`research.md` §5).

## CI wiring (lane-b's workflow step order)

```yaml
# round-trip: skip: GitHub Actions step-order sketch containing <placeholder> run lines — CI wiring illustration, deliberately not a valid instance, so there is nothing to round-trip
- run: node conformance/scripts/check-trigger-queryset-shape.mjs conformance/skills/trigger-queries/*.yaml
- run: node conformance/scripts/check-twin-phrasing.mjs conformance/skills/trigger-queries/
- run: npx --offline @garrison-hq/muster@1.2.1 skills run conformance/skills/behavioral-manifest.yaml --json > /tmp/report.json
- run: node conformance/scripts/check-control-discrimination.mjs /tmp/report.json --mode healthy
- run: node -e "<FR-003 skip-guard one-liner from spec.md>"   # at least one non-control case not skipped
- run: node scripts to build/commit the evidence artifact (tasks-phase detail)
- run: node conformance/scripts/check-evidence-artifact-shape.mjs conformance/skills/trigger-evidence/<file>.json
```

The `--mode dead-endpoint` invocation is **not** a CI workflow step (CI
only ever runs against a real, intentionally-healthy endpoint) — it is a
one-time, by-hand proof step during implementation, recorded in the work
log exactly the way `sk-skills-static-conformance-01KYG7GE`'s
`quickstart.md` §2 recorded its own flip-and-restore proof. See
`quickstart.md` §4 here for the exact by-hand procedure.
