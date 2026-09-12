# Implementation Plan: Doctrine Behavioral Suite

**Branch**: `kitty/mission-doctrine-behavioral-suite` | **Date**: 2026-08-01 | **Spec**: `kitty-specs/doctrine-behavioral-suite-01KYW5XK/spec.md`
**Input**: Feature specification from `kitty-specs/doctrine-behavioral-suite-01KYW5XK/spec.md`

**Branch contract** (confirmed via `spec-kitty agent mission setup-plan --mission
doctrine-behavioral-suite-01KYW5XK --json`, 2026-08-01): current, target, base,
planning-base, and merge-target branch are all the same single branch,
`kitty/mission-doctrine-behavioral-suite` (`branch_matches_target: true`).
Single-branch topology, no dedicated integration branch. `spec-kitty agent
mission branch-context --json`'s informational `primary_branch` field reports
`mission-crosslayer-composition-suite` (M7's mission, a different clone
entirely) via the known machine-global-journal quirk; every actionable field
(`current_branch`, `target_branch`, `base_branch`, `planning_base_branch`,
`merge_target_branch`, `branch_matches_target: true`, `recommended_strategy:
"stay"`) is correctly scoped to this mission. Matches the briefed behavior
exactly — no action required.

## Summary

Author five profile-axis behavioral manifests
(`conformance/behavioral/profiles/<id>.yaml`) grading `architect-alphonso`,
`reviewer-renata`, `implementer-ivan`, `planner-priti`, and `debugger-debbie`'s
*deployed* system prompts against four judge axes (avoidance-boundary,
domain-scope/capability containment, handoff discipline, canonical-verb
usage) defined verbatim in muster's own `docs/rubric/spec-kitty-behavioral-axes.md`;
a deterministic, input-sensitive generator
(`conformance/behavioral/tools/render_profile.py`) that produces the exact
`.claude/agents/<id>.md` body `ClaudeCodeProfileRenderer.render()` would emit,
committed under `conformance/behavioral/projected/`; a discrimination
control manifest proving every grader class can fail for two distinguishable
reasons (genuine non-compliance vs. dead endpoint); at least one behavioral
scenario appended to each of three of M3's already-shipped
`conformance/doctrine/*.yaml` directive manifests; and a
`workflow_dispatch`-only cadence workflow that runs `muster sop run` against
all of the above and commits a structured evidence artifact. No new runtime:
`muster sop run` (`@garrison-hq/muster@1.2.2`, exact pin — corrected from an
earlier `@1.2.1` pin; see "muster pin correction" in Technical Context below)
is the entire grading engine, consumed as an external, published CLI.

This plan corrects three points where the spec's design does not survive
direct contact with muster's actual rubric document and runtime, beyond what
the prior adversarial-squad remediation already fixed (see Findings, below):
FR-004's "capability containment" axis is muster's **domain-scope**
containment axis, which explicitly disclaims grading tool-authorization;
FR-006's pass^k requirement must extend to that same axis, and pass^k
manifests must set `passThreshold` **equal to `k`**, not the general
`ceil(k/2)` value, to get the runtime behavior FR-006 promises; and every
`JudgeAssertion` this mission builds must embed a verbatim excerpt of the
graded profile's own field at the YAML path the axis grades, per the rubric
document's own binding Integration Contract — a requirement no FR-001..004
verification cell in spec.md currently checks.

## Technical Context

**Language/Version**: Python 3.11+ for the one new script
(`render_profile.py`, mirroring M7's `profile2soul.py`); Bash for the
`runsErrored` helper; YAML for all manifests; Markdown for the README and
projected profile bodies. No `.py` file under `src/` is touched — this
mission's only Python is a standalone `conformance/` script that *imports*
`specify_cli`/`doctrine`/`charter` (this repository's own installed
packages) rather than modifying them.
**Primary Dependencies**: `@garrison-hq/muster@1.2.2` (external, published
npm CLI, exact pin — **muster pin correction**: an earlier draft of this
plan and of spec.md pinned `@1.2.1`, which is stale and actively harmful:
`db80a4295` ("fix(openclaw-sop): stop applying the k-run passThreshold to a
single run's judge vote", `garrison-hq/muster#89`, closing
`garrison-hq/muster#88`) is not an ancestor of `v1.2.1` but is an ancestor of
`v1.2.2` (confirmed via `git merge-base --is-ancestor db80a4295 v1.2.2`);
`1.2.1` reintroduces the exact defect this plan's own Findings/Dependencies
text documents — every judge-graded rule with a resolved threshold `≥ 2` was
permanently unpassable. Always specify `@1.2.2` in every command this
mission's manifests, README, or workflow reference; confirmed against
muster's own source tree at `main@8ce12906`, read-only). This repository's own `spec-kitty-cli` package
(editable-installed, confirmed via `pip show` → `spec-kitty-cli 3.2.5`),
specifically `charter.profiles.AgentProfile` and
`specify_cli.tool_surface.profiles.renderers.ClaudeCodeProfileRenderer` —
consumed read-only, never modified.
**Storage**: Filesystem only — committed YAML/Markdown/JSON under
`conformance/behavioral/`, plus edits to three existing files under
`conformance/doctrine/`.
**Testing**: Real-CLI verification (`muster sop run`, offline-mock
`ChatClient` fixtures for falsification, and one live credentialed run
before acceptance), not a new pytest suite — matching the established
`sk-skills-static-conformance`/`skill-trigger-routing-suite` precedent for
this `conformance/` tree. Every check is run for real, in both its pass and
rejection direction, per `quickstart.md`.
**Target Platform**: GitHub Actions `ubuntu-latest` (cadence workflow, real
`MUSTER_ENDPOINT`/`MUSTER_MODEL`/`MUSTER_API_KEY` secrets) and any POSIX
developer machine with Python 3.11+ and `npx` (local static/offline checks;
live checks need real credentials).
**Project Type**: Single conformance-data tree, extending the existing
`conformance/` directory M1–M3 scaffolded (`conformance/doctrine/` already
has 13 manifests; `conformance/behavioral/` does not exist yet — confirmed
directly against this checkout).
**Performance Goals**: Not applicable — no throughput/latency requirement;
FR-006's `k ≥ 5` run count is a statistical-confidence floor, not a
performance target.
**Constraints**: C-001 (env-only credentials, muster's own two NI-001
regexes reused, confirmed at `tests/unit/invariants.test.ts:81-82`), C-002
(cadence-only, must actually invoke every manifest), C-003 (deployed-truth
`systemPrompt`, generator output only), C-004 (no fabricated field cited as
grading evidence).
**Scale/Scope**: 5 profile manifests (4 rules each, 20 judge rules total), 1
control manifest (2 rules), 3 edited doctrine manifests, 1 generator script,
5 committed projected bodies, 1 `runsErrored` helper, 1 workflow file (2
jobs), 1 README, 1..N committed evidence artifacts (grows per cadence run).

## Charter Check

*Gate source: `.kittify/charter/charter.md`. DIR-001..013 are `severity:
warn` per `charter.yaml`; the binding `C-0xx` charter directives exist only
as `charter.md` prose — spec.md's own hand-enumerated table (labeled
`CHTR-003/004/007/011` in this mission's documents specifically to avoid
colliding with this mission's own `C-001..004`, per spec.md's Charter
Compliance section) is carried forward here unchanged.*

| Charter gate | Status | Note |
|---|---|---|
| DIR-005 — Tests added for new functionality | PASS (alternate form) | No pytest file added (this mission's surface is entirely `conformance/`, outside `src/`). Substituted by the mandatory real-CLI verification procedure (`quickstart.md`), run in both pass and rejection directions for every FR. |
| DIR-006 — mypy --strict | N/A for the generator | `render_profile.py` is a standalone script outside the `src/` mypy surface; still typed with standard-library type hints for readability, not gated by CI. |
| DIR-007 — Docstrings for public APIs | N/A (alt.) | No `src/` public API added. `render_profile.py` and the `runsErrored` helper each carry an explanatory module header, mirroring M7's `profile2soul.py` convention. |
| DIR-008 — No security issues | PASS, actively verified | C-001's grep gate runs at CI time reusing muster's own two regexes verbatim; the evidence artifact's `endpointHost` field is hostname-only by construction (never the full URL, path, or key); credentials only ever enter via `MUSTER_API_KEY`/`MUSTER_ENDPOINT`/`MUSTER_MODEL` env vars, never a file or argv. |
| DIR-009 — Breaking changes in CHANGELOG.md | N/A | Purely additive; FR-005's edits to M3's doctrine manifests only *append* scenarios, never remove or rename an existing `ruleId`. |
| DIR-010/011 — identifier/slug sanitization | N/A | No identifier-normalization code touched. |
| DIR-012 — Tracker issue assigned to HiC before implementation | ACTION REQUIRED at implement time | Seed issue `https://github.com/MOES-Media/spec-kitty/issues/24` must be confirmed assigned to the Human-in-Charge before WP01 implementation starts (spec.md records this as already applied during authoring; re-confirm at implement time). |
| DIR-013 — Pre-existing failures reported before baselining | N/A unless encountered | This mission never runs spec-kitty's own pytest suite as an acceptance gate; applies only if an implementing agent incidentally observes a pre-existing failure elsewhere in this checkout. |
| **C-011 — ATDD-first (binding)** | PASS, sequenced explicitly | See Verification Strategy and Implementation Concern Map: each WP's first commit is a failing check against a placeholder/empty fixture (e.g., `render_profile.py` run against a deliberately incomplete profile YAML, expecting the loud `KeyError` failure mode; a profile manifest with `k: 1` before the real `k: 5` value lands), committed before the real fixture. The reviewer verifies RED on this branch's own base commit (`2b52bca4d`, single-branch topology) and GREEN on each WP's final commit. Commit SHAs are recorded live during implementation, not fixed here. |
| CHTR-003 (dual-read) | N/A | No dual-homed identifier introduced. |
| CHTR-004 (burn-down) | N/A | No deprecation-list burn-down; this mission adds new manifests. |
| CHTR-007 (`__all__`) | N/A | This mission ships YAML/Markdown/one Python script under `conformance/`, not a new `src/` public-API module. |
| **CHTR-011 (ATDD-first, outranks every DIR-0xx)** | PASS | Identical binding as C-011 above — spec.md itself was authored outside-in (verification commands and falsification conditions before any implementation), and this plan carries that discipline into the WP-level commit sequence. |
| Single canonical authority | PASS | `conformance/behavioral/README.md` is the one home for this suite's endpoint matrix, env-var table, cost table, and the model+context-not-harness caveat; the evidence-artifact shape is documented in exactly one place (`data-model.md`). |
| Architectural alignment | PASS | `conformance/` stays outside `src/`; muster consumed only as an external, pinned, published CLI — no source coupling in either direction; the generator imports this repository's own `charter`/`specify_cli` packages read-only (see Finding 5 below for the one implementation hazard this creates). |
| Glossary & terminology | PASS | No new domain terminology invented; "avoidance-boundary adherence," "domain-scope containment," "handoff discipline," "canonical-verb usage," "pass^k," "k-of-n" are all muster's own rubric-document vocabulary, carried verbatim. |

No charter gate violations requiring justification (Complexity Tracking
below is empty for the same reason).

## Project Structure

### Documentation (this mission)

```
kitty-specs/doctrine-behavioral-suite-01KYW5XK/
├── spec.md                                     # done
├── plan.md                                     # this file
├── research.md                                 # Phase 0 output (if produced)
├── data-model.md                               # Phase 1 output — evidence-artifact + manifest shapes
├── quickstart.md                               # Phase 1 output — executable verification procedure
├── contracts/
│   └── evidence-artifact.schema.json           # Phase 1 output — FR-005/Evidence Artifact section
├── checklists/requirements.md                  # done
└── tasks/                                      # Phase 2 output (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
conformance/behavioral/                          # NEW top-level suite directory
├── tools/
│   └── render_profile.py                        # NEW — lane-a (FR-009)
├── projected/                                    # NEW, committed — lane-a (FR-009)
│   ├── architect-alphonso.md
│   ├── reviewer-renata.md
│   ├── implementer-ivan.md
│   ├── planner-priti.md
│   └── debugger-debbie.md
├── profiles/                                     # NEW — lane-a (FR-001..004, FR-006)
│   ├── architect-alphonso.yaml                   # 4 rules: AVOIDANCE-BOUNDARY-, CAPABILITY-CONTAINMENT-,
│   │                                              #          HANDOFF-DISCIPLINE-, CANONICAL-VERBS-<id>
│   ├── reviewer-renata.yaml
│   ├── implementer-ivan.yaml
│   ├── planner-priti.yaml
│   └── debugger-debbie.yaml
├── README.md                                     # NEW — lane-a (FR-008)
├── control-manifest.yaml                         # NEW — lane-b (FR-007)
├── scripts/
│   └── check-runs-errored.sh                     # NEW — lane-b (FR-007; relocated off lane-a's
│                                                  #        tools/** — see Finding 4)
└── evidence/                                      # NEW, grows one file per cadence run — lane-b (FR-007)
    └── <ISO-date>-<mid8>.json

conformance/doctrine/                             # EXISTING (M3, 13 files) — 3 edited in place, lane-b (FR-005)
├── 010-specification-fidelity-requirement.yaml   # EDITED — +1 behavioral scenario
├── 039-lynn-cole-engineering-culture.yaml        # EDITED — +1 behavioral scenario
└── 044-canonical-sources-and-unification.yaml    # EDITED — +1 behavioral scenario

.github/workflows/
└── behavioral.yml                                # NEW — lane-b (C-002 cadence workflow, 2 jobs)
```

**Structure Decision**: extends the existing `conformance/` tree; no new
top-level directory outside it. `conformance/doctrine/*.yaml`'s 10
*untouched* files (of 13) are never opened by this mission's diff. Nothing
under `kitty-specs/` is written by either lane branch (spec.md's own
constraint, re-affirmed here).

## Component & Data Flow

```
src/doctrine/agent_profiles/built-in/<id>.agent.yaml   (READ-ONLY, this repo's own)
        │  render_profile.py: sys.path-guarded import of THIS repo's
        │  charter.profiles.AgentProfile + specify_cli's ClaudeCodeProfileRenderer
        │  (see Finding 5 — never the globally pip-editable-installed checkout)
        ▼
conformance/behavioral/projected/<id>.md   (committed, FR-009)
        │  systemPrompt: <path> + content-hash citation (C-003)
        ▼
conformance/behavioral/profiles/<id>.yaml   (FR-001..004/006 — 4 rules per profile,
        │  promptTemplate embeds the verbatim profile-field excerpt the
        │  rubric's Integration Contract requires — see Finding 3)
        │  MUSTER_ENDPOINT=... MUSTER_MODEL=... MUSTER_API_KEY=... \
        │      npx @garrison-hq/muster@1.2.2 sop run <manifest> --json
        ▼
doSopRun → buildSopClient()|SOP_NOOP_CLIENT → runSopManifestSuite
        │  runComplianceProbeEntry × k runs per rule, each try/caught
        │  individually (FR-012 error containment — a dead endpoint
        │  increments that run's error, never aborts the case)
        ▼
gradeJudgeCompliance (order-swap, rubric-anchored) → SOPRunVerdict[]
        │  aggregateKofN / pass^k aggregation per rule
        ▼
SOPSuiteReport { verdicts[].runs[].error, passed, ... }  (--json)
        │  conformance/behavioral/scripts/check-runs-errored.sh computes
        │  the derived runsErrored count (no top-level field exists —
        │  SOPSuiteReport/SOPCaseVerdict confirmed at manifest.ts:156-192)
        ▼
evidence-summarization (workflow step, shape fixed by data-model.md)
        ▼
conformance/behavioral/evidence/<ISO-date>-<mid8>.json   (committed, FR-007)
```

Cadence workflow (`behavioral.yml`, `workflow_dispatch` only, C-002) is the
only CI caller of this pipeline, with two jobs — `main-suite` (all 5 profile
manifests + the 3 edited doctrine manifests) and `control-suite`
(`control-manifest.yaml`) — each independently computing
`check-runs-errored.sh`'s output and writing it into the evidence artifact's
per-case `runsErrored` field; `quickstart.md`'s commands exercise the
identical pipeline by hand during implementation and at the pre-acceptance
live-run gate.

## Verification Strategy (first-class; see `quickstart.md` for the executable form)

Every command below states credentials explicitly wherever it exercises a
live model — the specific class of defect (muster#76's endpoint-omission
shape) this spec's own remediation pass found and fixed five times.

| FR/C | Verification approach | Command (abridged — see `quickstart.md` for the full form) | Expected | Falsification |
|---|---|---|---|---|
| FR-001 | Avoidance-boundary judge rule, live + offline-mock | `MUSTER_ENDPOINT=<ep> MUSTER_MODEL=<m> MUSTER_API_KEY=<k> muster sop run conformance/behavioral/profiles/architect-alphonso.yaml --json` | exit `0`, `passed: true` (competent model) | Mock-`ChatClient` fixture whose reply writes implementation code directly → `AVOIDANCE-BOUNDARY-architect-alphonso` verdict `passed: false` |
| FR-002 | Handoff-discipline judge rule | Same command, filtered to the `HANDOFF-DISCIPLINE-*` `ruleId` via `--json \| jq` | `passed: true` for a reply that names a handoff-to role and stops | Mock fixture: reply both hands off *and* performs the next phase → `passed: false` |
| FR-003 | Canonical-verb judge rule (k-of-n) | Same, filtered to `CANONICAL-VERBS-*` | `passed: true`, `passCount ≥ 3` of 5 | Mock fixture: every reply uses generic verbs, zero canonical-verb overlap → `passed: false` |
| FR-004 | Domain-scope/capability-containment judge rule — **rubricText and scenario design corrected, see Finding 1** | Same, filtered to `CAPABILITY-CONTAINMENT-*` | `passed: true` for a reply that declines/redirects and whose declined action's *subject matter* stays outside the profile's declared `capabilities` domains | Mock fixture: reply narrates performing the disallowed action → `passed: false` |
| FR-005 | Directive manifests carry ≥1 judge verdict | `muster sop run conformance/doctrine/010-specification-fidelity-requirement.yaml --json` | exit `0`/`1` (model-conditional) with ≥1 `assertionKind: "judge"` verdict | `jq -e '[.verdicts[].runs[].grades[] \| select(.assertionKind == "judge")] \| length > 0'` against a static-only fixture report → exit `1` (spec.md's own corrected predicate, re-verified here) |
| FR-006 | `k ≥ 5`; pass^k rows (`AVOIDANCE-BOUNDARY-*`, **and `CAPABILITY-CONTAINMENT-*` — Finding 2a**) set `aggregation: pass-k` **and `passThreshold` equal to `k`** (Finding 2b); k-of-n rows set `passThreshold: ceil(k/2)` | `yq -e '[.rules[] \| select(.ruleId \| test("^(AVOIDANCE-BOUNDARY\|CAPABILITY-CONTAINMENT)")) \| has("passThreshold") and (.passThreshold == .k)] \| all' conformance/behavioral/profiles/architect-alphonso.yaml` (deliberately `has(...)`-gated, not `(.passThreshold // .k) == .k` — that defaulted form is a vacuous tautology that reads `true` even when `passThreshold` is missing entirely, verified empirically against a fixture with `CAPABILITY-CONTAINMENT-*`'s `passThreshold` omitted: the naive form returned `true`/exit `0`, a false pass on exactly the omission this check exists to catch, before being replaced) | `true`, exit `0` | Fixture with `aggregation: pass-k, k: 5, passThreshold: 3` → manifest load throws (`manifest.ts:299-306`'s own validator); implementers must still write `passThreshold: <k>` explicitly in every committed manifest for manifest hygiene and validator self-consistency — `runner.ts:566`'s *runtime* default is `ceil(k/2)`, computed regardless of `aggregation`, but only actually consumed by the k-of-n branch (`aggregateKofN`); the pass-k branch's `aggregatePassK` takes no threshold argument at `@garrison-hq/muster@1.2.2`, so omission is not runtime-load-bearing on these pass-k rows specifically (it is on the k-of-n rows below). This `yq` check only audits the committed YAML, not the runtime path, either way. Verified for real: the `has(...)`-gated command returns `false`/exit `1` against both the explicit-wrong-value fixture and the omitted-field fixture, and `true`/exit `0` against a fully-compliant fixture. |
| FR-007 | Both grader classes fail under two distinguishable conditions | Healthy: `MUSTER_ENDPOINT=<ep> MUSTER_MODEL=<m> MUSTER_API_KEY=<k> muster sop run conformance/behavioral/control-manifest.yaml --json > /tmp/h.json; echo $?` then `conformance/behavioral/scripts/check-runs-errored.sh /tmp/h.json` | exit `1` (both controls fail), `runsErrored == 0` | Dead endpoint (`MUSTER_ENDPOINT=http://127.0.0.1:9/v1`, same manifest) → exit `1` again (same!), but `runsErrored > 0`; cross-wiring the two reports through the wrong expectation must itself be shown failing during implementation validation |
| FR-008 | README carries endpoint matrix, env-var table, trivial-refusal semantics, model+context caveat | `test -f conformance/behavioral/README.md && command grep -Eq "MUSTER_ENDPOINT" ... && command grep -Eq "trivial.refusal\|TRIVIAL_REFUSAL" ... && command grep -Eqi "model.*not.*harness\|model\+context" ...` (portable `grep -E`, per spec.md's own corrected form) | exit `0` | Pre-mission tree (file absent) → exit `1`; unescaped `model+context` literal against a fixture containing only that phrase → exit `1` (proves the escape is load-bearing) |
| FR-009 | Determinism + **input-sensitivity** (Finding 5 governs *how*, not *whether*, this passes) | `render_profile.py <architect.yaml> > a.md; render_profile.py <architect.yaml> > b.md; diff a.md b.md` (exit `0`) **and** `render_profile.py <architect.yaml> > a.md; render_profile.py <reviewer.yaml> > c.md; ! diff -q a.md c.md` (exit `0`) | Both exit `0` | Hand-edited committed projected file, re-diff → exit `1`; a no-op stand-in generator (ignores argv, echoes a constant) passes the determinism check but fails the input-sensitivity check (`diff -q` on its two outputs is empty, so `!` inverts to exit `1`) |
| **New — Integration Contract excerpt (Finding 3, spec.md's C-005)** | Every `JudgeAssertion`'s `promptTemplate` embeds the verbatim profile-field excerpt its axis grades | `yq '.rules[] \| select(.ruleId \| test("^AVOIDANCE-BOUNDARY")) \| .promptTemplate' <manifest> \| command grep -qF "$(yq -r '.specialization["avoidance-boundary"]' <source.agent.yaml>)"` (axis-specific field per the Integration Contract table; note two corrections needed for the real, hyphenated schema field — `.specialization."avoidance-boundary"` errors as `jq: error: boundary/0 is not defined` since a bare hyphen after a key is parsed as subtraction unless bracket-quoted, and `yq -r` (raw output) is required or the extracted value stays JSON-quoted and never matches the unquoted excerpt text) | match found, exit `0` — verified for real against a fixture `promptTemplate` embedding the literal excerpt | `promptTemplate` that only says "consult the profile's avoidance-boundary field" without the literal text → no match, exit `1` — verified for real |
| C-001 | No secrets in manifests/argv | `command grep -rE '(nvapi-[A-Za-z0-9]{8}\|\bsk-[A-Za-z0-9_-]{20})' conformance/behavioral/*.yaml conformance/behavioral/profiles/*.yaml .github/workflows/behavioral.yml` | exit `1` (no match) | Planted fake key → exit `0` (match found), confirming the grep fires — then discard, never commit |
| C-002 | Cadence-only; workflow actually invokes every manifest | YAML parse of `on:` (no `pull_request`), **plus a post-merge procedural check** (see Finding 6 — this half cannot run inside either lane's isolated worktree) | assertion passes; `ls conformance/behavioral/profiles/*.yaml conformance/behavioral/control-manifest.yaml` matches the workflow's referenced globs | Scratch copy with `pull_request:` added → assertion fires; workflow referencing a manifest glob absent from disk (or vice versa) → post-merge check fails |
| C-003 | `systemPrompt` never hand-paraphrased | Manual review: every manifest's `systemPrompt`/`sopFile` cites `conformance/behavioral/projected/<id>.md` plus a `sha256:` content hash matching `render_profile.py`'s own hash of the source `.agent.yaml` | hashes match | Hand-edited `systemPrompt` text not traceable to the projected file → review fails |
| C-004 | No fabricated field cited as evidence | Review every `rubricText`/`promptTemplate` against the fields the projected body actually carries (`routing-priority`, `max-concurrent-tasks`, `context-sources` never cited) | no citation of an unrendered field | A rubric referencing `routing-priority` (not in the rendered Claude-agent body) → review fails |

### FR-007's both-condition sequencing (explicit)

1. Run `control-manifest.yaml` against the real, healthy endpoint (all three
   `MUSTER_*` vars set). Capture `/tmp/ctrl-healthy.json`. Assert exit `1`,
   `runsErrored == 0` via `check-runs-errored.sh`.
2. Point `MUSTER_ENDPOINT` at an unreachable port. Re-run. Capture
   `/tmp/ctrl-dead.json`. Assert exit `1` (same!), `runsErrored > 0`.
3. As a **third**, one-time falsification proof (per spec.md's own
   remediation), re-run the healthy command with its env vars stripped back
   out — reproduces the pre-fix muster#76 shape for the record: exit `1`,
   `runsErrored > 0`, byte-for-byte indistinguishable at the top level from
   step 2's genuinely dead endpoint.
4. Restore `MUSTER_ENDPOINT`/`MUSTER_MODEL`/`MUSTER_API_KEY` before
   continuing any other work.

## Acceptance Gate Sequencing (SC-006, "One Live Credentialed Run")

Per the lane-isolation hazard (an acceptance command that must open a
sibling lane's file cannot pass from that lane), this gate is **not** part
of either WP's own acceptance criteria. It runs in three ordered phases:

1. **Lane-scoped acceptance** (during implementation, inside each lane's own
   worktree): WP01 (lane-a) may run a live `muster sop run` against its own
   `conformance/behavioral/profiles/<id>.yaml` files — they are its own
   output. WP02 (lane-b) may run a live `muster sop run` against its own
   `control-manifest.yaml` and against `conformance/doctrine/*.yaml`
   (pre-existing, M3-merged, so visible in *any* lane's worktree branched
   from this mission's base). Neither WP can run the cross-file `ls`
   comparison C-002 requires, because the sibling lane's files do not exist
   in its own worktree yet.
2. **Post-merge, pre-accept** (both lanes merged onto
   `kitty/mission-doctrine-behavioral-suite`): re-run `muster sop run`
   against **all five** profile manifests plus the control manifest with
   real credentials, in one sitting. Verify, per SC-006's own text: the
   evidence artifact exists and is non-placeholder (`totalRuns` matches
   FR-006's `k ≥ 5`, `runsErrored` is a real recorded value); the raw
   `--json` report's `runs[].transcript` strings are non-empty and not
   byte-identical across a case's own runs (rules out a cached/no-op
   client); the control manifest's run shows `runsErrored == 0` for both
   controls alongside `passed: false`. Also run C-002's full `ls`
   cross-check here — this is the first point at which both lanes'
   manifests coexist on disk.
3. **Recorded at `/spec-kitty.accept`**, not as a per-PR CI gate (C-002).
   One passing gate run certifies FR-001..004's design against a real model
   at least once; it does not certify every future cadence run (spec.md's
   own "floor, not the cadence job" framing, unchanged here).

## Implementation Concern Map

> Implementation concerns are NOT work packages. `/spec-kitty.tasks`
> translates these into executable WPs.

### IC-01 — Deterministic profile→Claude-agent-body generator

- **Purpose**: Author `render_profile.py`: load one `*.agent.yaml` source
  file directly into a `charter.profiles.AgentProfile` (Pydantic
  `model_validate`, bypassing `AgentProfileRepository`'s directory-scanning
  default entirely — none of the 5 target profiles declare
  `specializes_from`, confirmed), call
  `ClaudeCodeProfileRenderer().render(profile)`, write the result plus a
  `sha256:` content hash of the source file to stdout/`projected/<id>.md`.
  **Must** prepend this checkout's own `src/` to `sys.path` before any
  `specify_cli`/`charter`/`doctrine` import (see Finding 5) — never rely on
  whatever is currently `pip`-editable-installed.
- **Relevant requirements**: FR-009.
- **Affected surfaces**: `conformance/behavioral/tools/render_profile.py`
  (new); `conformance/behavioral/projected/*.md` (new, 5 files, committed).
- **Sequencing/depends-on**: none.
- **Risks**: Finding 5's import-shadowing hazard is the single highest-value
  correctness risk in this concern — silently rendering against a different
  checkout's renderer/profile-directory state would produce a
  `systemPrompt` that is not this repository's own deployed truth,
  violating C-003 without any visible symptom (the two checkouts' relevant
  files are identical *today*, confirmed, but are already on different
  commits, so this is a live, not hypothetical, risk).

### IC-02 — Five profile-axis behavioral manifests (FR-001..004, FR-006)

- **Purpose**: Author `conformance/behavioral/profiles/<id>.yaml` for all 5
  target profiles, each with 4 rules (`AVOIDANCE-BOUNDARY-<id>`,
  `CAPABILITY-CONTAINMENT-<id>`, `HANDOFF-DISCIPLINE-<id>`,
  `CANONICAL-VERBS-<id>`), `sopFile:`/`systemPrompt` citing IC-01's output
  path + hash. Pass^k rows (`AVOIDANCE-BOUNDARY-*`,
  `CAPABILITY-CONTAINMENT-*` — Finding 2a) set `aggregation: pass-k` and
  `passThreshold: <k>` explicitly (Finding 2b); k-of-n rows
  (`HANDOFF-DISCIPLINE-*`, `CANONICAL-VERBS-*`) set
  `passThreshold: ceil(k/2)`. Every rule's `rubricText` quotes the matching
  `docs/rubric/spec-kitty-behavioral-axes.md` §-block verbatim (§1→FR-001,
  §2→FR-004 — corrected mapping, Finding 1 — §3→FR-002, §4→FR-003); every
  `promptTemplate` embeds the graded profile's own field excerpt per the
  rubric's Integration Contract table (Finding 3).
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-004, FR-006.
- **Affected surfaces**: `conformance/behavioral/profiles/*.yaml` (new, 5
  files).
- **Sequencing/depends-on**: IC-01 (references its committed output paths
  and hashes by name).
- **Risks**: Finding 1 (FR-004's rubric/scenario mismatch) is the concern's
  central correctness risk — a `CAPABILITY-CONTAINMENT-<id>` scenario whose
  disallowed action's *subject matter* happens to fall inside a declared
  capability domain would cite §2's rubricText while grading nothing that
  text actually asks about, producing an unfalsifiable or arbitrary judge
  verdict. Mitigated by designing every containment turn so the disallowed
  action's topic (not merely its tool-grant status) is demonstrably outside
  the profile's `capabilities` list, reviewed against §2.3's discrimination
  control example before commit.

### IC-03 — Behavioral scenario additions to M3's directive manifests

- **Purpose**: Append ≥1 behavioral scenario (with a `judge`-graded
  assertion) to each of `010-specification-fidelity-requirement.yaml`,
  `039-lynn-cole-engineering-culture.yaml`, and
  `044-canonical-sources-and-unification.yaml`, preserving every existing
  `ruleId` and the manifests' own `sopFile:` — additive edits only, per
  FR-005.
- **Relevant requirements**: FR-005.
- **Affected surfaces**: 3 of `conformance/doctrine/*.yaml`'s 13 existing
  files (edited, not replaced).
- **Sequencing/depends-on**: none within lane-b; independent of IC-01/IC-02
  (different lane, no shared files, per this plan's lane design below).
- **Risks**: an accidental rename or reordering of an existing `ruleId`
  would silently break the other 10 untouched manifests' cross-references
  if any exist — mitigated by reviewing each edit as a pure append (new
  `rules[]` entries only) before commit.

### IC-04 — README (endpoint matrix, env vars, trivial-refusal, caveat)

- **Purpose**: Author `conformance/behavioral/README.md`: endpoint matrix
  (Ollama/DGX, NIM, hosted), `MUSTER_ENDPOINT`/`MUSTER_MODEL`/`MUSTER_API_KEY`
  table, cost table, the model+context-not-harness caveat, and the
  trivial-refusal guard semantics — portable `grep -E` forms only (spec.md's
  own corrected FR-008 form, re-affirmed here).
- **Relevant requirements**: FR-008.
- **Affected surfaces**: `conformance/behavioral/README.md` (new).
- **Sequencing/depends-on**: IC-01, IC-02 (documents facts those establish;
  its own falsification proof needs the file layout IC-01/IC-02 create).
- **Risks**: none material beyond the portability regression FR-008's own
  corrected form already guards against.

### IC-05 — Control manifest and `runsErrored` helper

- **Purpose**: Author `control-manifest.yaml` (judge control: rubric demands
  an impossible property; behavioral control: system prompt orders the
  forbidden action) and `conformance/behavioral/scripts/check-runs-errored.sh`
  (the `jq '[.verdicts[].runs[] | select(.error != null)] | length'`
  computation, packaged as a reusable script rather than inlined into the
  workflow, so local falsification runs and the CI workflow share one
  implementation — never duplicated logic that could drift). **Path
  corrected off `conformance/behavioral/tools/`** (lane-a's exclusive
  write_scope) **onto a new lane-b-owned `conformance/behavioral/scripts/`**
  directory — see Finding 4.
- **Relevant requirements**: FR-007.
- **Affected surfaces**: `conformance/behavioral/control-manifest.yaml`
  (new); `conformance/behavioral/scripts/check-runs-errored.sh` (new).
- **Sequencing/depends-on**: none.
- **Risks**: the derived-sum computation is this concern's highest-value
  correctness risk — a bug here silently launders a dead-endpoint run as a
  valid discrimination proof. Mitigated by the mandatory three-run sequence
  in "FR-007's both-condition sequencing" above being run for real, not
  merely described, before FR-007 is marked done.

### IC-06 — Cadence workflow

- **Purpose**: Author `.github/workflows/behavioral.yml`:
  `workflow_dispatch` only (C-002); two jobs (`main-suite` — every
  `conformance/behavioral/profiles/*.yaml` plus the 3 IC-03-edited
  `conformance/doctrine/*.yaml` files, glob-driven, never a literal
  five-name list, per the parallelism note below; `control-suite` —
  `control-manifest.yaml`); `MUSTER_ENDPOINT`/`MUSTER_MODEL`/`MUSTER_API_KEY`
  as repository secrets; both jobs invoke `check-runs-errored.sh` per case
  and write the result into the evidence artifact's `runsErrored` field
  (FR-007 elaboration's extended scope — main-suite too, not only
  control-suite); `control-suite`'s own step asserts nonzero exit and
  `runsErrored == 0`, never treating that job's exit `1` as a build
  failure; muster invoked pinned exactly `@1.2.2` (corrected from an earlier
  `@1.2.1` pin — see Technical Context's "muster pin correction").
- **Relevant requirements**: FR-007, C-001, C-002.
- **Affected surfaces**: `.github/workflows/behavioral.yml` (new).
- **Sequencing/depends-on**: IC-05 (needs `check-runs-errored.sh` to exist
  and `control-manifest.yaml`'s path). **Does not depend on IC-01/IC-02**
  (lane-a): the workflow drives `muster sop run` via `conformance/behavioral/
  profiles/*.yaml` runtime globs, never an authored-time literal file list —
  the 5 profile IDs and the `ruleId` naming convention are already fully
  fixed in spec.md, so lane-b's workflow authoring needs no knowledge of
  lane-a's actual committed content (contrast with the M6 sibling mission's
  lane-b, which genuinely needed lane-a's literal file names and was
  sequenced accordingly — this mission's two lanes are genuinely
  parallel, not merely non-colliding).
- **Risks**: schedule/cron wiring is explicitly out of scope (M8,
  `garrison-hq/muster-action#2`) — this workflow must not gain a
  `schedule:` trigger through copy-paste from a different workflow file.

## Work-Package Outline (preview for `/spec-kitty.tasks` — not tasks.md)

**Predicted lane count: 2**, both `parallel_group: 0`, `depends_on_lanes: []`.

`compute_lanes` (`src/specify_cli/lanes/compute.py`, read directly before
writing this section) unions **code** WPs only when their declared
`owned_files` globs overlap (`_globs_overlap`: exact-match, or one pattern's
wildcard-stripped prefix is a path-prefix of the other) or — only when
ownership is *not already provably disjoint* — when they share an
inferred surface keyword. Dependency edges never collapse lanes by
themselves; they only become lane-level `depends_on_lanes` edges after
grouping.

This mission's real file layout makes fine-grained IC-per-WP splitting
actively dangerous here: IC-01 (`tools/**`+`projected/**`), IC-02
(`profiles/**`), and IC-04 (`README.md`) are three **genuinely disjoint**
subtrees under `conformance/behavioral/` — declared as three separate WPs,
`compute_lanes` would place them in **three separate lanes** (the "framed 2
lanes, got 4" failure mode), even though IC-02 depends on IC-01. Worse,
because two more lane-b subtrees (`control-manifest.yaml`, `evidence/**`)
also live directly under `conformance/behavioral/`, any WP that claimed a
broad `conformance/behavioral/**` glob to force IC-01/IC-02/IC-04 together
would also swallow lane-b's files into the same union (the "all four WPs
collapsed into one lane" failure mode) — confirmed directly: prefix-stripping
`conformance/behavioral/**` yields `conformance/behavioral`, which is a
path-prefix of `conformance/behavioral/control-manifest.yaml` too.

The resolution adopted here is the one the `skill-trigger-routing-suite`
(M6) and `crosslayer-composition-suite` (M7) sibling missions both already
established as sound: **choose WP granularity deliberately, per lane, and
let a WP's `owned_files` genuinely span everything that lane's single
reviewable unit of work touches** — never split by IC when the ICs share no
directory but do share a lane, and never broaden a glob past what a WP
actually needs. Both this mission's lanes are small enough (5 manifests +
1 script + 1 doc; 1 manifest + 1 script + 1 workflow + 3 file edits) that one
WP per lane is the correct granularity, not an evasion of the algorithm:

```json
{
  "lanes": [
    { "lane_id": "lane-a", "wp_ids": ["WP01"],
      "write_scope": [
        "conformance/behavioral/tools/**",
        "conformance/behavioral/projected/**",
        "conformance/behavioral/profiles/**",
        "conformance/behavioral/README.md"
      ],
      "depends_on_lanes": [], "parallel_group": 0 },
    { "lane_id": "lane-b", "wp_ids": ["WP02"],
      "write_scope": [
        "conformance/doctrine/010-specification-fidelity-requirement.yaml",
        "conformance/doctrine/039-lynn-cole-engineering-culture.yaml",
        "conformance/doctrine/044-canonical-sources-and-unification.yaml",
        "conformance/behavioral/control-manifest.yaml",
        "conformance/behavioral/scripts/**",
        "conformance/behavioral/evidence/**",
        ".github/workflows/behavioral.yml"
      ],
      "depends_on_lanes": [], "parallel_group": 0 }
  ]
}
```

- **WP01** (lane-a): IC-01 → IC-02 → IC-04, in that order (IC-02 cites
  IC-01's committed output; IC-04 documents both). Internal sequencing is
  expressed as an ordered subtask/commit sequence within the one WP, per
  C-011/CHTR-011's ATDD-first discipline — not as separate WPs, since
  `conformance/behavioral/tools/**`, `profiles/**`, and `README.md` are
  mutually disjoint globs that `compute_lanes` would otherwise fragment.
  Before starting, confirm `github.com/MOES-Media/spec-kitty/issues/24` is
  assigned to the Human-in-Charge (DIR-012).
- **WP02** (lane-b): IC-03 + IC-05 + IC-06, in any internal order (IC-03's
  doctrine edits are independent of IC-05/IC-06; IC-06 depends on IC-05
  within this same WP). **Zero cross-lane dependency on WP01** — verified
  above (IC-06's workflow globs, not literal paths).

**Build order**: WP01 and WP02 run **in true parallel** (`parallel_group: 0`
for both) — this is the genuine two-stream concurrency spec.md's Lanes
section intends, not merely non-colliding write scopes with a hidden
sequential dependency (contrast the M6 sibling's own corrected finding,
where its lane-b needed lane-a's literal output first). The only
sequencing this mission has is *within* each lane's own single WP, and the
mission-level, post-merge Acceptance Gate (above), which necessarily runs
after both lanes land.

## Complexity Tracking

*No entries — no charter gate violations require justification.*

No new runtime dependency: `@garrison-hq/muster` is consumed via `npx`,
never added to any dependency manifest. `render_profile.py` imports only
this repository's own already-installed `charter`/`specify_cli` packages
(read-only) plus `ruamel.yaml`/standard library, matching M7's
`profile2soul.py` precedent exactly.

## Findings Requiring Spec Attention

*Per this skill's guardrail, these were originally flagged rather than
silently patched into spec.md's FR/C text. **All seven have since been
addressed directly in spec.md** during a dedicated post-plan remediation
pass (see `checklists/requirements.md`'s "Post-plan remediation pass" note
for the resolution summary and commit history for the per-finding diffs).
None changes an FR's stated user-observable behavior — all are
verification-design, path, or integration-fidelity corrections. This
section is kept as the historical record of what the plan phase found and
why; if a future reviewer judges any resolution insufficient, route it back
through `spk-mission-specify` before `/spec-kitty.tasks` runs.*

1. **FR-004's axis is muster's "Domain-Scope Containment" (§2), not a
   tool-authorization check — and §2 explicitly disclaims grading tool
   authorization at all.** Read directly from
   `docs/rubric/spec-kitty-behavioral-axes.md` §2.1 (muster `main@8ce12906`):
   *"This axis therefore does not grade tool authorization at all... A
   rubric that asks a judge whether a tool invocation was 'explicitly
   granted by the profile' has no schema-defined mapping... and is not
   decidable by any judge, however capable."* FR-004's own text ("a
   scenario's system prompt lists a tool palette exceeding the profile's
   declared capabilities... the rubric asks whether the reply declines...
   rather than fabricating the disallowed action") reads exactly like the
   tool-authorization framing §2.1 disclaims. Telling corroboration: the
   Dependencies & Assumptions section scopes M2's "quotes rubric verbatim"
   dependency to "FR-001..003" only — FR-004 is silently excluded, without
   explanation. This plan resolves it as: FR-004's `rubricText` is §2's
   actual text (subject-matter/domain framing); scenario turns must be
   designed so the disallowed action's *subject matter* (not merely its
   absence from a granted-tool list) falls outside the profile's declared
   `capabilities` domains — the FR-004 elaboration's own example
   (architect-alphonso "runs the test suite") happens to satisfy this by
   coincidence (testing is outside `system-design`/`architecture-review`/
   etc.), but that is not guaranteed by FR-004's stated design principle and
   must be designed for explicitly across all 5 profiles' scenarios.

2. **FR-006's pass^k requirement is incomplete, and its `passThreshold`
   guidance is inconsistent with the manifest schema's own validation
   rule.**
   (a) Muster's rubric doc's own Aggregation Summary table classifies
   **both** §1 (avoidance-boundary) and §2 (domain-scope/capability
   containment) as `pass^k`/Safety-critical — §3/§4 (handoff, canonical-verb)
   are `k-of-n`/Stylistic. FR-006 only names avoidance-boundary as pass-k;
   `CAPABILITY-CONTAINMENT-<profile>` is left unstated. This plan extends
   the pass-k requirement to both safety-critical `ruleId` prefixes.
   (b) `manifest.ts:299-306`'s own validator throws when a `pass-k` rule
   declares `passThreshold !== k`. `runner.ts:566`'s `dispatchProbeVerdicts`
   computes `entry.passThreshold ?? Math.ceil(entry.k / 2)` **on every row,
   regardless of `aggregation`**, but only the `k-of-n` branch (`aggregateKofN`)
   actually *consumes* that computed value — the `pass-k` branch calls
   `aggregatePassK(runVerdicts)`, which takes no threshold argument at all and
   never has (verified against `graders.ts` both before and after
   `garrison-hq/muster#89`/`db80a4295`, the passThreshold-defect fix described
   in spec.md's Dependencies section — that fix touched a different call site,
   `runComplianceProbeEntry`'s *inner* single-run judge vote, not this outer
   aggregation). **Correction (was: "silently weakens 'all runs must pass' to
   a majority vote at runtime" for an omitted pass-k `passThreshold`) — that
   claim is stale/was never accurate**: omitting `passThreshold` on a
   `pass-k` row has no runtime effect on the outer aggregation, because
   `aggregatePassK` ignores the field either way; the row still requires
   every one of the `k` runs to pass. The downgrade-to-majority-vote risk is
   real, and runtime-load-bearing, only on **k-of-n** rows. Spec.md's
   Live-Model Plan states "`passThreshold: ceil(k / 2)`... explicit in every
   manifest" as a blanket rule; applied literally to a pass-k row this
   either throws at load time (if also declared pass-k with `passThreshold:
   3, k: 5`) or, if `passThreshold` is omitted to dodge that error, is
   merely inconsistent with `manifest.ts`'s own self-documentation intent —
   not a runtime weakening. This plan corrects the guidance: pass-k rows set
   `passThreshold` **equal to `k`**, explicitly (manifest hygiene /
   validator self-consistency); k-of-n rows set `ceil(k/2)`, explicitly
   (runtime-load-bearing).

3. **No FR-001..004 verification cell checks the rubric document's own
   binding Integration Contract requirement.** `docs/rubric/
   spec-kitty-behavioral-axes.md`'s "Integration Contract" section (lines
   59-101) states, as a normative requirement: every `JudgeAssertion` this
   mission builds must have its `promptTemplate` embed the verbatim excerpt
   of the graded profile's own field at the YAML path that axis grades
   (`specialization.avoidance-boundary` for §1; `capabilities` for §2;
   `roles`/`role` + `collaboration.handoff-to` for §3;
   `collaboration.canonical-verbs` for §4) — *"an M4 JudgeAssertion whose
   promptTemplate omits the named excerpt for its axis is not a faithful
   embedding of this rubric."* Without it, the judge is asked to consult a
   field it was never shown, which the rubric doc itself calls
   "indistinguishable... from asking it to guess." No FR-001..004
   verification cell in spec.md tests for this omission. This plan adds it
   as a cross-cutting acceptance criterion (Verification Strategy table,
   new row) and an IC-02 design requirement.

4. **FR-007's suggested script path collides with lane-a's exclusive
   write_scope.** FR-007's elaboration names its `runsErrored`-computation
   script as living at `conformance/behavioral/tools/check_runs_errored.sh
   or equivalent` — but `conformance/behavioral/tools/**` is lane-a's
   write_scope per spec.md's own Lanes section, and FR-007 is assigned to
   lane-b. Left as written, WP02 would need to open a path inside WP01's
   lane, violating the mission's own "no WP in either lane opens a file
   under the other lane's write_scope" rule. This plan relocates the script
   to a new, lane-b-owned `conformance/behavioral/scripts/` directory.

5. **FR-009's generator has an import-shadowing risk that threatens SC-003,
   demonstrated (not hypothetical) against this checkout.** This
   repository's `charter`/`specify_cli` packages are `pip`-editable-installed
   pointing at `/home/jeroennouws/dev/spec-kitty` specifically (`pip show`
   confirms `spec-kitty-cli 3.2.5` at that path) — a *different* checkout
   from this mission's own (`-m4`, currently at `2b52bca4d` vs. the
   canonical checkout's `0a3a76db3`; the two checkouts' relevant files are
   byte-identical today by coincidence, confirmed directly, not by
   guarantee). A script that does a bare `from specify_cli...import
   ClaudeCodeProfileRenderer` resolves against whichever checkout happens to
   be the current editable-install target, not necessarily the checkout the
   script is running inside — silently reintroducing exactly the
   "dependency on another repository's tree state" SC-003 exists to rule
   out. This plan's IC-01 requires the script to prepend its own checkout's
   `src/` to `sys.path` before any such import, and to construct
   `AgentProfile` directly from the one parsed source file rather than via
   `AgentProfileRepository`'s directory-scanning default (which carries the
   identical risk for the profile-data side, not just the renderer-code
   side).

6. **C-002's full procedural cross-check and the SC-006 live-run gate
   cannot be either lane's own WP acceptance criterion.** Per the lane
   isolation hazard, lane-b's isolated worktree never contains lane-a's
   `conformance/behavioral/profiles/*.yaml` files until both lanes merge.
   Spec.md states the live-run gate is "checked at `/spec-kitty.accept`,"
   which is consistent with this, but does not explicitly say the same
   about C-002's `ls`-based file-set cross-check — this plan makes that
   explicit (Acceptance Gate Sequencing, phase 2) so a future WP-level
   acceptance reviewer does not attempt (and fail) that check inside a
   single lane's worktree.

7. **`buildSopClient`'s actual gating variable is `MUSTER_ENDPOINT` alone —
   worth stating precisely, not as a correction but as an implementation
   note.** `MUSTER_MODEL` defaults to `gpt-4o-mini` and the API-key env name
   falls back to `OPENAI_API_KEY` when `MUSTER_API_KEY` is unset
   (`src/cli/index.ts:1608-1622`) — only `MUSTER_ENDPOINT`'s absence
   triggers the `SOP_NOOP_CLIENT` fallback the muster#76 defect class is
   about. Setting all three explicitly (as this plan and spec.md both
   require) remains the correct practice regardless — it prevents a
   contributor's personal `OPENAI_API_KEY` from silently authenticating a
   request aimed at a different endpoint, and pins the intended model rather
   than the CLI's own default — but implementers should not misdiagnose a
   future incident by assuming all three vars are equally load-bearing for
   the no-op-fallback behavior specifically.

None of the seven items above changes an FR's stated user-observable
behavior; all are verification-design, path-layout, or
integration-fidelity clarifications this plan supplies. Items 1-3 are the
highest-value: without them, FR-004's grading is testing something other
than what its own text describes, FR-006's **k-of-n** (stylistic) rows can
silently degrade below their intended `ceil(k/2)` majority threshold if
`passThreshold` is left implicit and the default drifts from what this
plan's guidance intends (the pass-k/safety-critical rows do not carry this
particular risk — `aggregatePassK` never consumes `passThreshold`, see
Finding 2b's correction above), and every judge rule in the suite risks
asking the model to comply with a field it was never shown.
