# Quickstart: Skill Trigger-Routing Conformance Suite — Verification Procedure

**Mission**: `skill-trigger-routing-suite-01KYVRB9` | **Date**: 2026-07-31

All commands run from the repository root of the mission's own branch
(`kitty/mission-skill-trigger-routing-suite-01KYVRB9`). This file is the
mandatory, real-execution verification procedure referenced by `plan.md`'s
Verification Strategy — every step must be run for real during
implementation and its actual output recorded in the mission work log, per
this programme's binding rule that a check is not proven until it has been
run against its own rejection case (not merely described).

C-011 (ATDD-first) governs the order within each WP: the failing-first
assertion for a given script/check is committed, as its own commit, against
a placeholder/empty fixture **before** the real fixture content is authored
— the sections below are written in that RED → GREEN order per script.

---

## 0. Prerequisite: cache-warm `@garrison-hq/muster@1.2.1`

```sh
npm install --no-save @garrison-hq/muster@1.2.1
npx --offline @garrison-hq/muster@1.2.1 --version   # confirm the pin resolved, not a floating range
```

## 1. FR-001 — query-set shape gate (lane-a, WP01/WP02)

**RED** (commit first, against an empty placeholder directory):

```sh
mkdir -p conformance/skills/trigger-queries
echo 'id: placeholder
source: "docs/rubric/skills-trigger-taxonomy.md"
threshold: 0.5
shouldTrigger: ["only one query"]
nearMiss: ["only one query"]' > conformance/skills/trigger-queries/placeholder-queries.yaml

node conformance/scripts/check-trigger-queryset-shape.mjs conformance/skills/trigger-queries/*.yaml
echo "RED exit code: $?"   # MUST be 1, naming placeholder-queries.yaml and both axes
```

Commit this RED state (the script + the failing placeholder fixture) as
its own commit. Record the commit SHA in the mission work log — this is
the SHA the reviewer verifies RED against on `planning_base_branch`.

**GREEN** (after the 13 real files are authored, placeholder removed):

```sh
rm conformance/skills/trigger-queries/placeholder-queries.yaml
node conformance/scripts/check-trigger-queryset-shape.mjs conformance/skills/trigger-queries/*.yaml
echo "GREEN exit code: $?"   # MUST be 0
```

**Falsification proof** (construct and run before marking FR-001 done):

```sh
cp conformance/skills/trigger-queries/spk-run-next-duplicate-pair-queries.yaml /tmp/backup.yaml
python3 -c "
import yaml
d = yaml.safe_load(open('conformance/skills/trigger-queries/spk-run-next-duplicate-pair-queries.yaml'))
d['shouldTrigger'] = d['shouldTrigger'][:7]
yaml.safe_dump(d, open('conformance/skills/trigger-queries/spk-run-next-duplicate-pair-queries.yaml','w'))
"
node conformance/scripts/check-trigger-queryset-shape.mjs conformance/skills/trigger-queries/*.yaml
echo "rejection exit code: $?"   # MUST be 1, naming this exact file
cp /tmp/backup.yaml conformance/skills/trigger-queries/spk-run-next-duplicate-pair-queries.yaml
git diff --exit-code conformance/skills/trigger-queries/
```

## 2. FR-002 — twin-phrasing cross-reference (lane-a, WP01/WP02)

**RED**: run `check-twin-phrasing.mjs` against the same placeholder
directory from §1 before any real cross-references are authored — it must
exit `1` for every declared pair/triple (no borrowed phrasing exists yet).

**GREEN**: after all 13 files carry their cross-references:

```sh
node conformance/scripts/check-twin-phrasing.mjs conformance/skills/trigger-queries/
echo "GREEN exit code: $?"   # MUST be 0
```

**Falsification proof**:

```sh
cp conformance/skills/trigger-queries/spk-run-next-run-family-queries.yaml /tmp/backup2.yaml
# Temporarily strip the borrowed phrases from the other two run-family siblings:
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

## 3. FR-003 — manifest skip-guard (lane-b, WP03)

**Unset-endpoint proof** (the graceful-skip path — must never be mistaken
for evidence):

```sh
unset MUSTER_ENDPOINT MUSTER_API_KEY
npx --offline @garrison-hq/muster@1.2.1 skills run conformance/skills/behavioral-manifest.yaml --json \
  | node -e "const r=JSON.parse(require('fs').readFileSync(0)); process.exit(r.results.some(c=>c.type==='behavioral' && c.skipped) ? 1 : 0)"
echo "exit code: $?"   # MUST be 1 -- every behavioral case skipped, proving the guard fires
```

(Corrected during WP04: muster's real `skills run --json` top-level shape is
`{ok, total, passed, failed, skipped, results}` — there is no top-level
`cases` key, per `src/cli/index.ts:1293`/`:1583` at v1.2.1. The original
`r.cases.some(...)` throws at runtime; it happened to still exit non-zero,
satisfying "MUST be 1" for the wrong reason.)

**Configured-endpoint proof** (requires a real or test endpoint):

```sh
export MUSTER_ENDPOINT=<test-endpoint>
export MUSTER_API_KEY=<from CI secret, never a literal here>
npx --offline @garrison-hq/muster@1.2.1 skills run conformance/skills/behavioral-manifest.yaml --json \
  | node -e "const r=JSON.parse(require('fs').readFileSync(0)); process.exit(r.results.some(c=>c.type==='behavioral' && c.skipped) ? 1 : 0)"
echo "exit code: $?"   # MUST be 0 -- no behavioral case skipped
```

## 4. FR-004 — control, both conditions (lane-b, WP03) — the sequencing the mission exists to prove

This is the mission's single most important verification sequence. Run
in this exact order; do not skip the dead-endpoint half even though it
requires deliberately breaking the endpoint:

```sh
# (a) Healthy condition first.
export MUSTER_ENDPOINT=<real, reachable endpoint>
export MUSTER_API_KEY=<real key, from env/secret, never committed>
npx --offline @garrison-hq/muster@1.2.1 skills run conformance/skills/behavioral-manifest.yaml --json > /tmp/report-healthy.json
node conformance/scripts/check-control-discrimination.mjs /tmp/report-healthy.json --mode healthy
echo "healthy-mode exit code: $?"   # MUST be 0: passed:false, derived runsErrored:0

# (b) Rejection proof for the healthy check: run healthy-mode assertions
#     against dead-endpoint data -- must fail, or the script isn't actually
#     distinguishing the two conditions (research.md §2, §7).
export MUSTER_ENDPOINT=http://127.0.0.1:1   # deliberately unreachable
npx --offline @garrison-hq/muster@1.2.1 skills run conformance/skills/behavioral-manifest.yaml --json > /tmp/report-dead.json
node conformance/scripts/check-control-discrimination.mjs /tmp/report-dead.json --mode healthy
echo "healthy-mode against dead data, exit code: $?"   # MUST be 1

# (c) Dead-endpoint condition, correct mode.
node conformance/scripts/check-control-discrimination.mjs /tmp/report-dead.json --mode dead-endpoint
echo "dead-endpoint-mode exit code: $?"   # MUST be 0: passed:false, derived runsErrored>0

# (d) Rejection proof for the dead-endpoint check: run dead-endpoint-mode
#     assertions against healthy data -- must fail (the inverse of (b)).
node conformance/scripts/check-control-discrimination.mjs /tmp/report-healthy.json --mode dead-endpoint
echo "dead-endpoint-mode against healthy data, exit code: $?"   # MUST be 1

# (e) Omitted-mode usage error -- must never silently default.
node conformance/scripts/check-control-discrimination.mjs /tmp/report-healthy.json
echo "no --mode, exit code: $?"   # MUST be 2

# Restore before continuing:
export MUSTER_ENDPOINT=<real, reachable endpoint>
```

Record all five exit codes and the two report files' relevant fields
(`passed`, derived `runsErrored`) in the mission work log — this sequence
*is* SC-002 and User Story 3's proof, not an implementation detail.

## 5. FR-005 — evidence artifact (lane-b, WP03)

**RED** (commit first, against a prose-only placeholder):

```sh
mkdir -p conformance/skills/trigger-evidence
echo '{"summary": "suite passed"}' > conformance/skills/trigger-evidence/placeholder.json
node conformance/scripts/check-evidence-artifact-shape.mjs conformance/skills/trigger-evidence/placeholder.json
echo "RED exit code: $?"   # MUST be 1, naming every missing required field
rm conformance/skills/trigger-evidence/placeholder.json
```

**Credential-leak rejection case**:

```sh
echo '{"timestamp":"2026-07-31T00:00:00Z","model":"gpt-4o-mini","endpointHost":"api.openai.com/v1?api_key=sk-XXXXXXXXXXXXXXXXXXXX","cases":[]}' > /tmp/leaky.json
node conformance/scripts/check-evidence-artifact-shape.mjs /tmp/leaky.json
echo "rejection exit code: $?"   # MUST be 1, naming the credential-leak match, not just "cases empty"
```

**GREEN**: after §4's real healthy run produces `/tmp/report-healthy.json`,
the (tasks-phase-implemented) summarization step writes the real evidence
file per `data-model.md`'s shape, and:

```sh
node conformance/scripts/check-evidence-artifact-shape.mjs conformance/skills/trigger-evidence/<real-file>.json
echo "GREEN exit code: $?"   # MUST be 0
```

Then commit the evidence file for real (FR-005 requires a *committed*
artifact, never one left only in workflow logs).

## 6. NFR-002 — credential grep, both directions

```sh
command grep -rE '(sk-|api[_-]?key\s*[:=]\s*["\047][A-Za-z0-9]{16,})' conformance/skills/behavioral-manifest.yaml .github/workflows/skill-trigger-routing.yml
echo "exit code: $?"   # MUST be 1 (no match) at every commit
```

**Rejection case** (construct once, confirm the grep catches it, then
discard — never commit this state):

```sh
echo 'api_key: "sk-THIS_SHOULD_NEVER_BE_COMMITTED_1234567890"' >> conformance/skills/behavioral-manifest.yaml
command grep -rE '(sk-|api[_-]?key\s*[:=]\s*["\047][A-Za-z0-9]{16,})' conformance/skills/behavioral-manifest.yaml .github/workflows/skill-trigger-routing.yml
echo "rejection exit code: $?"   # MUST be 0 (match found)
git checkout HEAD -- conformance/skills/behavioral-manifest.yaml   # NEVER git checkout . or rm -rf
```

## 7. C-002 — no `pull_request` trigger, parsed not grepped

```sh
python3 -c "
import yaml
d = yaml.safe_load(open('.github/workflows/skill-trigger-routing.yml'))
on = d.get('on', d.get(True, {}))   # PyYAML parses bare 'on:' as boolean True key in YAML 1.1
assert 'pull_request' not in on, 'pull_request trigger present'
print('OK: no pull_request trigger')
"
```

**Rejection case**: temporarily add a `pull_request:` key under `on:` in a
scratch copy of the workflow file (never the committed one) and confirm
the assertion fires — this is the actual risk this programme has
previously gotten backwards (a check that read `on:` but never the parsed
structure, or vice versa a text grep that missed a job-body reference).

## 8. Full local pre-merge check (what an implementing agent runs before requesting review)

```sh
node conformance/scripts/check-trigger-queryset-shape.mjs conformance/skills/trigger-queries/*.yaml \
  && node conformance/scripts/check-twin-phrasing.mjs conformance/skills/trigger-queries/ \
  && node conformance/scripts/check-evidence-artifact-shape.mjs conformance/skills/trigger-evidence/*.json \
  && command grep -rE '(sk-|api[_-]?key\s*[:=]\s*["\047][A-Za-z0-9]{16,})' conformance/skills/behavioral-manifest.yaml .github/workflows/skill-trigger-routing.yml; \
  [ $? -eq 1 ] && echo "conformance: all local checks green"
```

(§4's live both-condition sequence and a real CI `workflow_dispatch` run
are the two steps that cannot be folded into this one-liner — they require
a real endpoint and a real Actions run respectively, and are the closing
verification before the mission is proposed for merge, exactly as
`sk-skills-static-conformance-01KYG7GE`'s own quickstart.md §4 treated its
CI step.)
