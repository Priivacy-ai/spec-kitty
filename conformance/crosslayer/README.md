# `conformance/crosslayer/` — Crosslayer Composition Suite (mission M7)

This directory is mission M7's own documentation
(`crosslayer-composition-suite-01KYJA33`, seed `MOES-Media/spec-kitty#26`).
It is **entirely separate from the shared top-level
[`../README.md`](../README.md)**, which documents wave-1's Skills Static
Conformance suite and is never edited by this mission (M3's PR #30 also
touches that shared file; M7 avoids the collision by documenting itself
here instead — see `kitty-specs/crosslayer-composition-suite-01KYJA33/spec.md`,
Dependencies & Assumptions).

M7 composes a real deployed spec-kitty stack — a projected persona +
`AGENTS.md` policy extract (SOP) + one skill — and runs
[`@garrison-hq/muster`](https://github.com/garrison-hq/muster)'s
`crosslayer` adapter over it: static contradiction/precedence lint on every
PR that touches `conformance/**` or `packs/built-in/agent_profiles/**`
(see "CI wiring" below — a PR touching neither path never sees this job),
behavioral rule-survival on cadence against a live model.

## Manifest layout

Per `kitty-specs/crosslayer-composition-suite-01KYJA33/plan.md`'s Project
Structure section (the authoritative layout for this mission; each path
below is owned by the WP named, not this one):

```
conformance/crosslayer/
├── README.md            # this file — WP04 (this WP)
├── personas/
│   ├── architect-alphonso.Soul.md   # committed, WP01 — projected from
│   │                                # packs/built-in/agent_profiles/
│   │                                # architect-alphonso.agent.yaml
│   └── reviewer-renata.Soul.md      # committed, WP01
├── sop-extract.md        # WP03 — bounded AGENTS.md policy extract (OQ-6)
├── manifest.yaml          # WP02 — CompositionManifestCase[], $ref-included
├── control.yaml           # WP02 — FR-006 discrimination control
│                          # (one committed case, control-verbosity-flip;
│                          #  the "flip" direction. The "neutralize"
│                          #  direction is a reproduction procedure run from
│                          #  an uncommitted scratch copy, not a shipped
│                          #  case — see control.yaml's own header comment)
├── fixtures/
│   ├── control-persona.Soul.md               # WP02 — control.yaml fixture
│   ├── control-skill.SKILL.md                # WP02 — control.yaml fixture
│   ├── control-sop.md                        # WP02 — control.yaml fixture
│   ├── invalid-persona-missing-key.Soul.md   # WP02 — C-001 fixture
│   └── spk-run-next.SKILL.md                 # WP02 — FR-004 case fixture,
│                                              # a symlink into
│                                              # src/doctrine/skills/
└── cases/
    ├── architect-run-skill.yaml     # WP02 — FR-004 case 1
    ├── reviewer-run-skill.yaml      # WP02 — FR-004 case 2
    ├── rule-survival-045.yaml       # WP05, blocked on M3
    ├── rule-survival-029.yaml       # WP05, blocked on M3
    └── erosion-control-045.yaml     # WP05, blocked on M3
```

Some of these paths are not yet present in every lane's own worktree at
implementation time — this mission's lanes are isolated worktrees, and this
WP (WP04) owns only `.github/workflows/crosslayer.yml` and this README. The
paths above are fixed in advance by `plan.md`'s Project Structure section,
which is what lets WP04's CI wiring (below) reference WP01's and WP03's
scripts, and WP02's manifest, by path only, without needing their bytes at
authoring time (see spec.md's Dependencies & Assumptions, "The full
path-only coupling surface").

## The two check classes

1. **Static contradiction/precedence lint** (`contradiction-lint.ts`, every
   PR): `muster crosslayer run conformance/crosslayer/manifest.yaml --static-only`.
   Assembly order is SOP→persona→skill
   (`composition.ts`'s `buildComposedText`, RFC-1 §7.5/Appendix G
   resolution). Offline, zero-network, no repository secrets required —
   safe to run on a fork PR.
2. **Behavioral rule-survival** (`rule-survival.ts`, cadence, live model):
   `muster crosslayer run conformance/crosslayer/manifest.yaml` (no
   `--static-only`) against a live OpenAI or NVIDIA NIM endpoint, measuring
   whether a safety-relevant SOP rule's pass rate degrades once composed.
   Requires `MUSTER_ENDPOINT`/`MUSTER_API_KEY` (or `OPENAI_API_KEY`
   fallback); **until WP05/lane-c lands, this manifest carries zero
   rule-survival cases** — see the inline comment in
   `.github/workflows/crosslayer.yml`'s cadence job before treating a green
   cadence run as evidence this check class is exercised.

## CI wiring (`.github/workflows/crosslayer.yml`)

A workflow file **isolated from the shared
[`.github/workflows/conformance.yml`](../../.github/workflows/conformance.yml)**
by design (never edited by this mission — see spec.md's collision-avoidance
note above). Two jobs:

- **`static-gate`** — every `pull_request`, path-filtered to both
  `conformance/**` and `packs/built-in/agent_profiles/**` (a
  profile-only PR must still see and be able to fix the persona-drift
  check its own diff affects). Runs, in order: checkout, the static
  contradiction lint via `garrison-hq/muster-action` (pinned to the same
  commit `conformance.yml` already trusts), then two bare one-line drift
  checks — `bash conformance/scripts/check-persona-drift.sh` (WP01) and
  `bash conformance/scripts/check-sop-extract-drift.sh` (WP03). No
  `secrets:` reference anywhere in this job.
- **`cadence-rule-survival`** — `schedule:` (weekly) plus
  `workflow_dispatch:` for on-demand manual runs. Sources
  `MUSTER_ENDPOINT`/`MUSTER_API_KEY` from GitHub Actions **repository
  secrets only** (never a manifest value, never CLI args, never a log
  line). Zero real cases until WP05/lane-c lands — explicitly commented
  inline in the workflow file itself.

## Running the static check locally

Cache-warm the pinned package once per environment (network enabled), then
run offline (mirrors the shared suite's own two-step convention documented
in `../README.md`):

```bash
npm install --no-save @garrison-hq/muster@1.2.1   # one-time, network enabled
npx --offline @garrison-hq/muster@1.2.1 crosslayer run \
  conformance/crosslayer/manifest.yaml --static-only --json
```

Expect exit `0` with the JSON summary's `failed` field at `0` against the
shipped benign manifest. Also run the two drift-check scripts directly,
bare, from the repo root:

```bash
bash conformance/scripts/check-persona-drift.sh
bash conformance/scripts/check-sop-extract-drift.sh
```

Both exit `0` on a clean tree and non-zero the moment their respective
committed artifact drifts from what regenerating it right now would
produce.

## Fabricated-field discipline (C-003)

The projector (`conformance/tools/profile2soul.py`, WP01) fabricates RFC-1
fields (`voice`, `interaction`, `locale`, and empty
`composition`/`profiles`/`profile_overrides`/`extensions` lists) that no
agent profile carries, to satisfy `resolveCompositionDetailed`'s structural
precondition. **No check, README prose, or `expected` block in this suite
may ever cite one of those fabricated fields as the reason a case passed or
failed** — grading rests on body text and composed behavior only. See
`kitty-specs/crosslayer-composition-suite-01KYJA33/spec.md`'s C-003 row for
the full constraint and its review-time audit command.
