# Implementation Plan: Doctrine Rule Manifests

**Branch**: `kitty/mission-doctrine-rule-manifests` | **Date**: 2026-07-27 | **Spec**: `kitty-specs/doctrine-rule-manifests-01KYH7AM/spec.md`
**Input**: Feature specification from `kitty-specs/doctrine-rule-manifests-01KYH7AM/spec.md`

**Branch contract** (confirmed via `spec-kitty agent mission setup-plan --json`,
run at plan start): current branch, target branch, base branch,
planning-base branch, and merge-target branch are all the **same single
branch**, `kitty/mission-doctrine-rule-manifests` (`branch_matches_target:
true`). There is no separate integration branch — every artifact in this
plan commits directly to that branch, matching M3's predecessor mission
(M1) and the mission's own Dependencies & Assumptions section (this mission
rebases on M1's merged state at `32722b5f1` and does not run parallel with
any other mission editing the shared CI workflow file). **Repeated at the
end of this report per the branch-strategy-confirmation requirement.**

## Summary

Hand-author 13 SOP rule manifests under `conformance/doctrine/` (one per
prioritised directive: 9 trace-decidable — 018, 028, 029, 030, 033, 034,
035, 042, 045 — plus 4 proposed judge directives — 001, 010, 039, 044),
each `sopFile:` pointing at the directive YAML itself so muster's existing
`RULE_DRIFT` static lint (`checkRuleTextPresence`) turns upstream directive
edits into visible staleness. Every one of the 45 rules gets a real,
individually-justified taxonomy-class assignment against
`docs/rubric/sop-rule-taxonomy.md`'s 7 existing classes (**[corrected
post-plan-gate: 24 map cleanly or by documented best-fit; 21 do not fit
any existing class — was 25/20 before two post-plan-gate corrections: 044's
three rules revert from `never-call-tool` to UNMAPPED (binding operator
decision — the classification was judged the weakest fit in the table,
`contracts/rule-classification-and-citation.md`), and 010's two rules move
from UNMAPPED to `output-format` on a reconciliation pass against the
structurally-identical `030-r3` precedent — net +1 UNMAPPED]** and are
shipped as explicit `UNMAPPED` judge-fallback entries — a real taxonomy gap
this plan surfaces rather than glosses over), a commit-pinned upstream citation
verified byte-for-byte against the real `Priivacy-ai/spec-kitty` repository,
and — for the 10 rules whose text wraps across a physical line in the
directive's raw YAML (042×3, 044×3, 045×4) — a single-line fragment whose
uniqueness is mechanically verified (`grep -F -c` = `1`) rather than eyeballed.
One control manifest under `conformance/doctrine/control/` carries a
deliberately drifted `ruleText`, inverted-asserted by CI to **produce**
`RULE_DRIFT` (not to pass cleanly). A new CI job joins M1's existing
`.github/workflows/conformance.yml` (same file, per the mission's own
sequencing constraint), running a `jq`-based drift gate (FR-004/FR-005) plus
one author-added completeness script that closes the one gap muster's own
error paths do not cover: a rule entry silently dropped from a manifest,
which today produces no finding and a clean exit `0` (the mission brief's
"absence lesson," applied here rather than repeated). Zero muster changes;
zero behavioral probes (`probeIds: []` throughout, deferred to M4).

## Technical Context

**Language/Version**: N/A for spec-kitty runtime (no `.py` file is added or
changed — identical posture to M1). `conformance/doctrine/**` is 13
hand-authored YAML manifests + 1 control + one Markdown README, plus one
dependency-free Node ≥22 script (`check-doctrine-manifest-completeness.mjs`,
mirroring M1's `check-manifest-completeness.mjs`) and one Bash+`jq` script
(`check-doctrine-drift-gate.sh`, new to this mission — `jq` is pre-installed
on `ubuntu-latest` and ships as a standard developer-machine tool, so no new
toolchain dependency is introduced).
**Primary Dependencies**: `@garrison-hq/muster@1.1.0` (external, published
npm CLI, same exact pin M1 established — reconfirmed current via `npm view
@garrison-hq/muster version` on 2026-07-27, and confirmed the `sop run`
code path is unchanged between `1.0.0`, `1.1.0`, and muster's current HEAD —
research.md §1). Neither `@garrison-hq/muster` nor `jq` is added to any
spec-kitty dependency manifest.
**Storage**: N/A.
**Testing**: real-CLI verification (binding constraint 6/operator
directive), not a new pytest suite — the actual built `muster` CLI is run
against the actual 13 shipped manifests + 1 control, the discrimination
control is proven both directions, the fragment convention is proven on a
real run for 042/044/045 specifically (spec Acceptance Scenario 3), and
every absence case (missing manifest, missing `sopFile` target, dropped
rule entry, hollowed control) is observed, not assumed. See "Verification
Strategy" below and `quickstart.md`, the executable form of this strategy.
**Target Platform**: GitHub Actions `ubuntu-latest` (the new job joins M1's
existing workflow file) and any POSIX developer machine with Node and `jq`.
**Project Type**: single conformance-data tree; no new spec-kitty package,
module, or top-level source directory — `conformance/doctrine/` sits
alongside M1's `conformance/skills/`, both under the same `conformance/`
root.
**Performance Goals**: not asserted at plan time (measured-not-asserted
policy, same as M1 and this mission's own spec — no NFR-### rows exist in
spec.md by deliberate choice). The new job's real wall-clock minutes are
recorded in `conformance/README.md` alongside M1's existing timing entry
once a real workflow run exists (quickstart.md §8).
**Constraints**: C-001 (diff touches only `conformance/**` and the workflow
file); C-002 (fully offline on PRs, no secrets — reconfirmed stronger than
required: every manifest's `probeIds: []` means the static-lint path never
even attempts to construct a live model client, research.md §2); C-003 (no
probe entries; manifests must load under the pinned muster `1.1.0`).
**Scale/Scope**: 13 shipped manifests (45 rule entries total) + 1 control
manifest (1 entry) = 46 `DoctrineRuleManifestEntry` instances; one drift-gate
script; one completeness script; one README; one new CI job in a shared
workflow file.

## Charter Check

*Gate source: `.kittify/charter/charter.md`. This is spec-kitty's own
Python-runtime charter — as with M1, most Python-specific gates are N/A by
construction (C-001: zero `.py` files touched), marked explicitly below
rather than silently skipped.*

| Charter gate | Status | Note |
|---|---|---|
| DIR-005 — Tests added for new functionality | PASS (alternate form) | No pytest file is added. Substituted by the mandatory real-CLI verification procedure (`quickstart.md`) — every gate this mission adds is exercised for real, in both the pass and fail direction, with results recorded in the mission work log. |
| DIR-006 — Type annotations / mypy --strict | N/A | No `.py` file is added or changed. |
| DIR-007 — Docstrings for public APIs | N/A | No Python public API is added. `check-doctrine-manifest-completeness.mjs` carries an explanatory header comment (M1's own house convention for the `conformance/` tree). |
| DIR-008 — No security issues (credentials, secrets handling) | PASS | Zero secrets anywhere in the new job or scripts — fully static and offline by design, identical posture to M1, and stronger here (no client is ever constructed at all, research.md §2). |
| DIR-009 — Breaking changes documented in CHANGELOG.md | N/A | Purely additive; no existing behavior changes. |
| DIR-010/DIR-011 — ASCII slug sanitization + regression coverage | N/A | No identifier-normalization or slug-sanitization code is touched or added. |
| DIR-012 — Tracker-backed issue assigned to HiC before implementation starts | **ACTION REQUIRED at implement time** | This mission's seed is GitHub issue `MOES-Media/spec-kitty#23`. Whichever agent begins the first WP's implementation **must assign issue #23 to the Human-in-Charge** before or as part of starting, per DIR-012 — flagged here so it is not missed at the tasks/implement handoff (same flag M1 raised for issue #22). |
| DIR-013 — Pre-existing test failures reported before treating as baseline | N/A unless encountered | This mission does not run spec-kitty's own pytest suite; if incidentally observed, DIR-013 still applies. |
| Single canonical authority | PASS | `conformance/doctrine/` is the one home for these manifests; `contracts/rule-classification-and-citation.md` is the one home for the per-rule class/citation table (no duplicate copy lives in the README beyond a rendering of the same facts). |
| Architectural alignment | PASS | `conformance/` stays outside `src/`, consuming muster as an external published CLI — unchanged from M1's established posture. |
| ATDD-first | PASS (adapted) | The spec's Acceptance Scenarios (including AC-4, added post-spec-gate) are the outside-in acceptance surface; `quickstart.md` operationalizes every one as exact commands, both pass and fail directions. |
| Glossary & terminology adherence | PASS | No new domain terminology introduced beyond muster's own existing vocabulary ("rule manifest," "fragment," "UNMAPPED" is this plan's own explicit, defined label, not a silent coinage). |
| Model discipline / dispatch a governed profile | N/A at plan phase | Governs the tasks/implement phase, not this plan's content. |

No charter gate violations requiring justification. No new runtime
dependency is added to spec-kitty itself.

## Project Structure

### Documentation (this mission)

```
kitty-specs/doctrine-rule-manifests-01KYH7AM/
├── spec.md                                          # done (four post-spec-gate corrections already applied)
├── plan.md                                          # this file
├── research.md                                      # Phase 0 output
├── data-model.md                                    # Phase 1 output
├── quickstart.md                                    # Phase 1 output — also the verification procedure
├── contracts/
│   ├── doctrine-rule-manifest-shape.md              # Phase 1 output — manifest shape + loader-guard discharge
│   ├── doctrine-drift-gate-contract.md              # Phase 1 output — FR-004/FR-005 script contract
│   ├── doctrine-manifest-completeness-contract.md   # Phase 1 output — absence-guard script contract
│   └── rule-classification-and-citation.md          # Phase 1 output — the full 45-row FR-002/003/006 table
└── tasks.md                                         # Phase 2 output (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
conformance/
├── README.md                              # UNCHANGED structurally (M1's), gains no new top-level
│                                           # section here — doctrine/README.md is the FR-006 home
├── DECISIONS.md                            # UNCHANGED — D3 already covers this mission's design
├── scripts/
│   ├── check-manifest-completeness.mjs    # UNCHANGED (M1's, skills-only)
│   ├── check-doctrine-drift-gate.sh       # NEW — FR-004/FR-005
│   └── check-doctrine-manifest-completeness.mjs  # NEW — absence guard
├── skills/                                 # UNCHANGED (M1's)
└── doctrine/                               # NEW — this mission's entire surface
    ├── README.md                           # NEW — FR-006 mapping table + coverage roadmap
    ├── 001-architectural-integrity-standard.yaml
    ├── 010-specification-fidelity-requirement.yaml
    ├── 018-doctrine-versioning-requirement.yaml
    ├── 028-search-tool-discipline.yaml
    ├── 029-agent-commit-signing-policy.yaml
    ├── 030-test-and-typecheck-quality-gate.yaml
    ├── 033-targeted-staging-policy.yaml
    ├── 034-test-first-development.yaml
    ├── 035-bulk-edit-occurrence-classification.yaml
    ├── 039-lynn-cole-engineering-culture.yaml
    ├── 042-common-docs.yaml
    ├── 044-canonical-sources-and-unification.yaml
    ├── 045-prs-only-and-read-intent.yaml
    └── control/
        └── 045-drifted.yaml                # NEW — FR-005 discrimination control

.github/workflows/
└── conformance.yml                          # MODIFIED (shared with M1): renamed top-level `name:`,
                                              # added the new `sop-doctrine-conformance` job (3 steps).
                                              # [Corrected post-plan-gate] `permissions: contents: read`
                                              # and SHA-pinned actions are NOT this mission's
                                              # contribution — PR #29 (MOES-Media/spec-kitty, lands
                                              # first per operator decision) adds both. WP03 checks
                                              # for an existing `permissions:` key before inserting
                                              # and does not re-pin/unpin the already-SHA-pinned
                                              # actions.
```

**Structure Decision**: `conformance/doctrine/` sits as a sibling to M1's
`conformance/skills/`, inside the same `conformance/` root — no new
top-level directory beyond what M1 already established. No file under
`src/doctrine/directives/built-in/` is modified; the 13 manifests reference
those files read-only via `sopFile`. `.github/workflows/conformance.yml` is
edited in place (same file as M1's, per the mission's own locked
sequencing constraint — research.md §9), not duplicated into a sibling
workflow.

## Verification Strategy (first-class, per operator directive)

This mission cannot be called done on manifest-inspection or agent
assertion alone. Before any WP is marked complete, the implementing agent
must run, for real, and record the real result of every numbered step in
`quickstart.md`:

1. **All 13 shipped manifests against the real muster CLI** — exit `0`,
   zero disallowed findings (§1).
2. **The one-word-flip demonstration** — proving `RULE_DRIFT` is a
   warning that does *not* flip muster's own exit code, which is FR-004's
   entire reason for existing (§2).
3. **The fragment convention's real-execution proof for 042/044/045**
   specifically — spec Acceptance Scenario 3, added post-spec-gate (§3).
4. **Mechanical fragment/control uniqueness** — `grep -F -c` = `1` for all
   10 fragments, `= 0` for the control's drifted text (§4).
5. **The control manifest's inverted discrimination proof** — must
   *contain* `RULE_DRIFT`, not avoid it (§5).
6. **The absence guard, both ways, across all four failure modes** —
   dropped rule entry, missing manifest file, missing `sopFile` target,
   deleted control manifest (§6) — this is the mission brief's "absence
   lesson" instruction discharged as executable steps, not prose.
7. **The full local pre-PR gate** (§7).
8. **A real GitHub Actions run** of the modified workflow, both jobs green,
   timing recorded (§8) — cannot be simulated locally.

Steps 1–7 are cheap and MUST be run locally by the implementing agent
before requesting review; step 8 requires a real PR and is the closing
verification before the mission is proposed for merge.

## Implementation Concern Map

> Implementation concerns are NOT work packages. `/spec-kitty.tasks`
> translates these into executable WPs.

### IC-01 — The 13 trace-decidable and judge-proposed rule manifests

- **Purpose**: Author all 13 shipped manifests under `conformance/doctrine/`
  per `contracts/doctrine-rule-manifest-shape.md` and
  `contracts/rule-classification-and-citation.md`'s per-rule table (45
  entries total), each with correct `sopFile`, `ruleText`
  (verbatim or fragment), `gradingClass`/`aggregation`/`k`/`passThreshold`,
  and `source.normative`/`source.supporting`.
- **Relevant requirements**: FR-001, FR-002, FR-003.
- **Affected surfaces**: `conformance/doctrine/*.yaml` (13 new files).
- **Sequencing/depends-on**: none — the classification table and citation
  SHAs are already fully resolved by this plan.
- **Risks**: transcription error on the 10 fragment texts and directive
  039's Unicode apostrophes — mitigated by the mandatory `grep -F -c`
  re-verification (quickstart.md §4) before each fragment-bearing or
  039-rule commit, not by care alone.

### IC-02 — Discrimination control (FR-005)

- **Purpose**: Author `conformance/doctrine/control/045-drifted.yaml` per
  `contracts/doctrine-drift-gate-contract.md`'s exact drifted-text
  specification, verified `grep -F -c` = `0` against the real 045 directive
  file before commit.
- **Relevant requirements**: FR-005.
- **Affected surfaces**: `conformance/doctrine/control/045-drifted.yaml` (new).
- **Sequencing/depends-on**: none functionally, but naturally authored
  alongside IC-01's 045 manifest (same source directive, same fragment
  family).
- **Risks**: control regresses to a non-discriminating state if a future
  edit softens the mutation — mitigated by the `grep -F -c` = `0` check
  being a required, re-runnable step (not a one-time authoring fact) and by
  `check-doctrine-manifest-completeness.mjs`'s existence check catching an
  outright deletion.

### IC-03 — Drift-gate script (FR-004/FR-005 CI enforcement)

- **Purpose**: Author `conformance/scripts/check-doctrine-drift-gate.sh`
  per `contracts/doctrine-drift-gate-contract.md` — the main gate over the
  13 shipped manifests plus the inverted control assertion, in one script.
- **Relevant requirements**: FR-004, FR-005.
- **Affected surfaces**: `conformance/scripts/check-doctrine-drift-gate.sh` (new).
- **Sequencing/depends-on**: IC-01 + IC-02 (needs real manifest paths to
  glob and the control's real path).
- **Risks**: none material — the script's logic is fully specified in the
  contract, and its behavior is exercised both ways in `quickstart.md`
  §1–2, §5 before merge.

### IC-04 — Absence-guard completeness script (author-added)

- **Purpose**: Author `conformance/scripts/check-doctrine-manifest-completeness.mjs`
  per `contracts/doctrine-manifest-completeness-contract.md` — closes the
  "rule entry silently dropped" gap identified in research.md §8, mirroring
  M1's own FR-007 addition pattern (a defensive control the original FR
  table didn't name, added once the gap was spotted).
- **Relevant requirements**: none of FR-001–006 directly — an author-added
  control per the mission brief's explicit "absence lesson" instruction,
  flagged here exactly as such rather than silently folded into FR-004.
- **Affected surfaces**: `conformance/scripts/check-doctrine-manifest-completeness.mjs` (new).
- **Sequencing/depends-on**: IC-01 (needs the manifests' final rule counts
  settled) + IC-02 (needs the control manifest's final location settled).
- **Risks**: the directive-side `integrity_rules` bullet-counting algorithm
  must be re-verified against the real files at implementation time (it was
  verified twice during planning — once by hand, once by an independent
  `awk` one-liner — both agreeing on all 13 counts and the 45 total), not
  re-derived from memory.

### IC-05 — `conformance/doctrine/README.md` (FR-006)

- **Purpose**: Author the FR-006 mapping table (directive → taxonomy class,
  including every `UNMAPPED` disposition and its stated reason) and
  coverage roadmap (which of the 26 built-in directives remain, and why
  038/`reconcile-change-scope-tensions` are excluded by construction), plus
  local-invocation instructions for the two new scripts, mirroring M1's
  `conformance/README.md` honesty conventions (known-gaps section,
  structural-vs-observed distinctions). **[Added post-plan-gate]** The
  README must also state explicitly that `docs/rubric/
  sop-rule-taxonomy.md` (the normative source every mapping-table row
  cites) is **cross-repo** — it lives only in the `garrison-hq/muster`
  package, not in this repository — so a reader does not go looking for a
  file that isn't here. The README must also carry
  `contracts/rule-classification-and-citation.md`'s note that
  `source.normative` cites this path with a `#<class-anchor>` suffix, a
  deliberate deviation from the taxonomy's own literal (no-anchor) citation
  format spec, not an oversight.
- **Relevant requirements**: FR-006.
- **Affected surfaces**: `conformance/doctrine/README.md` (new).
- **Sequencing/depends-on**: IC-01 through IC-04 (documents facts those
  concerns establish) and the Verification Strategy's step 8 (the CI timing
  entry cannot be written until a real workflow run exists).
- **Risks**: none material — the source content (the 45-row table) is
  already fully compiled in `contracts/rule-classification-and-citation.md`;
  this concern is largely a faithful rendering of it into the README's own
  format, plus the coverage-roadmap prose.

### IC-06 — CI workflow modification (FR-004 wiring, shared file)

- **Purpose**: Modify `.github/workflows/conformance.yml` in place: rename
  the top-level `name:` (`Skills Static Conformance` → `Static
  Conformance`) and add the new `sop-doctrine-conformance` job (checkout,
  drift gate, completeness check). **[Corrected post-plan-gate]** This
  concern no longer includes adding `permissions: contents: read` as this
  mission's own contribution: PR #29 (`MOES-Media/spec-kitty`, open, in
  final verification) inserts an identical `permissions:\n  contents:
  read` block at the identical anchor (immediately after `- main`,
  immediately before `jobs:`) and additionally SHA-pins both existing
  actions. **Operator decision: PR #29 lands first.** This mission's WP03
  therefore (a) checks for an existing `permissions:` key before
  inserting one, and does not duplicate it if PR #29 has already landed;
  (b) expects both existing actions to already be SHA-pinned and does not
  re-pin or unpin them; (c) pins its own new job's `actions/checkout` step
  to match whatever convention PR #29 leaves in place (a SHA, not a fresh
  `@v6` tag reference).
- **Relevant requirements**: FR-004, FR-005, C-002.
- **Affected surfaces**: `.github/workflows/conformance.yml` (shared with
  both M1's own job and PR #29's hardening changes).
- **Sequencing/depends-on**: IC-03 + IC-04 (needs both scripts' stable
  paths/exit-code contracts — satisfied by their contracts alone; IC-06
  does not need their source, only the contract files, same lane-independence
  pattern M1 used for its own WP03) **plus PR #29 having landed to `main`**
  (new dependency, recorded here rather than rediscovered at implement
  time — research.md §9).
- **Risks**: this mission rebases on M1's merged state and must not run
  concurrently with any other mission editing this same file (spec
  Dependencies & Assumptions) — flagged for the tasks-phase sequencing
  decision, not resolved here since this mission is single-lane (per the
  issue's own WP decomposition, §"Work-Package Outline" below).
  **Additionally**: PR #29 (`MOES-Media/spec-kitty`, open) touches this
  same file at the same anchor point this mission's `permissions:` edit
  would have targeted — confirmed real via `gh pr view 29`. The operator
  has decided PR #29 lands first; this mission's WP03 must rebase on that
  merged state and treat the collision as already resolved (check-before-
  insert), not as a merge conflict to fix reactively.

## Work-Package Outline (preview for `/spec-kitty.tasks` — not tasks.md)

The seed issue's decomposition (§6: WP01 trace-decidable manifests, WP02
judge manifests, WP03 control + CI jq gate + README) is a **single lane**
(house precedent — the issue's own text: "all WPs edit the same manifest
tree + README"), consistent with this plan's Implementation Concern Map:

```json
{
  "lanes": [
    { "lane_id": "lane-a", "wp_ids": ["WP01", "WP02", "WP03"],
      "write_scope": [
        "conformance/doctrine/**",
        "conformance/scripts/check-doctrine-drift-gate.sh",
        "conformance/scripts/check-doctrine-manifest-completeness.mjs",
        ".github/workflows/conformance.yml"
      ],
      "depends_on_lanes": [], "parallel_group": 0 }
  ]
}
```

- **WP01** (IC-01, the 9 trace-decidable directives: 018, 028, 029, 030,
  033, 034, 035, 042, 045 — 26 rule entries): before starting, confirm
  issue `MOES-Media/spec-kitty#23` is assigned to the Human-in-Charge
  (DIR-012).
- **WP02** (IC-01, the 4 proposed judge directives: 001, 010, 039, 044 —
  19 rule entries — including the headline finding, **corrected
  post-plan-gate**, that 001/039/044 are entirely `UNMAPPED` (044 reverted
  from a prior, since-withdrawn `never-call-tool` reclassification —
  binding operator decision) while 010 is better modeled as `output-format`
  than left `UNMAPPED` (reconciliation pass against `030-r3`'s precedent)):
  sequenced after or alongside WP01; no file collision (each directive's
  manifest is its own file).
- **WP03** (IC-02 + IC-03 + IC-04 + IC-05 + IC-06 — control, both scripts,
  README, and the shared workflow file): depends on WP01+WP02's manifests
  existing at their final paths (the drift gate globs them; the README
  documents them), so **WP03 is sequenced after WP01 and WP02**, unlike
  M1's WP03 (which was lane-independent because it depended only on a
  contract file, not on WP01's source). This mission's WP03 genuinely needs
  the real manifest files to exist (the drift-gate script's glob and the
  completeness script's per-directive comparison both read real paths), so
  the contract-only independence pattern does not apply here — flagged
  explicitly so `/spec-kitty.tasks` does not mis-sequence it as parallel-safe.
  **[Added post-plan-gate]** WP03 additionally depends on **PR #29**
  (`MOES-Media/spec-kitty`, open, in final verification — operator decision:
  it lands first) having merged to `main` before WP03 touches
  `.github/workflows/conformance.yml`: PR #29 inserts an identical
  `permissions:\n  contents: read` block at the identical anchor (after
  `- main`, before `jobs:`) and SHA-pins both existing actions. WP03's
  workflow edit must (1) check for an existing `permissions:` key before
  inserting one, never duplicating it; (2) expect both actions to already
  be SHA-pinned and not re-pin or unpin them; (3) pin its own new job's
  `actions/checkout` step to the same convention (a SHA, not a fresh `@v6`
  tag). This is a real dependency, not a hypothetical one — confirmed via
  `gh pr view 29 --repo MOES-Media/spec-kitty`.

**Build order**: WP01 and WP02 may proceed in either order or interleaved
(disjoint files); WP03 must follow both.
