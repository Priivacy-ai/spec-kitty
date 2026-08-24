# Tracer: Approach

Mission: accept-path-remediation-honesty-01M0TWZP (issues #3730, #3085)

## Why these two issues are one mission

Both defects live on the same seam: `spec-kitty accept`'s path-convention check
(`validate_mission_paths` in `src/specify_cli/validators/paths.py`, and its callers in
`src/specify_cli/acceptance/summary_core.py` and `src/specify_cli/cli/commands/accept.py`).
Fixing them independently would mean two agents editing the same functions in sequence
with no shared context; fixing them together lets the spec state the resolved-path
correctness fix (#3085a) as the substrate the honesty fix (#3730) and the dedup fix
(#3085b) both build on.

## Sequencing (per the readiness report, verified against the code first-hand)

- **WP1** — resolved-path correctness: `validate_mission_paths` stores/reports the
  `full_path` it actually checked, not the bare declared token.
- **WP2** — stop double-reporting: reconcile `contracts/`'s dual declaration
  (`artifacts.optional` + `paths.deliverables` in `software-dev/mission.yaml`) so the
  same missing fact does not appear as both a non-blocking warning and a blocking
  `path_violations` entry.
- **WP3** — honest remediation text + `--lenient` discoverability, depends on WP1+WP2
  (the wording fix should describe the post-dedup, resolved-path world, not the
  pre-fix one).
- **WP4** — red-first tests per behaviour change, one test per WP that fails when that
  WP's change is reverted.

## Scope boundary held explicitly

NOT #3016 (whether the hardcoded `src/`/`tests/`/`contracts/` conventions are right for
non-standard layouts) and NOT #2330. This mission fixes what the check *says* and
reconciles facts already declared — never what it *enforces* or which paths are
declared. Both issues' own "Scope / non-goals" sections state this identically.

## Maintainer requirement (binding)

#3085's 2026-08-02 triage comment requires "a focused repro/acceptance fixture plus
owner/dependency links before implementation." The spec makes this fixture an explicit
deliverable (see FR for the repro fixture), not an implicit side-effect of the WP4 test
tasks.

## 2026-08-25 — plan phase: gate-set correction (diff-coverage does not enforce this diff)

Reading `.github/workflows/ci-quality.yml` directly (not recalled from memory) during
planning found that the `diff-coverage` job's *enforced* (`--fail-under=90`, blocking)
step only checks a hardcoded `critical_paths` allowlist — `src/kernel/*`,
`src/doctrine/*`, `src/charter/*`, `src/specify_cli/status/*`,
`src/specify_cli/lanes/branch_naming.py`, `src/specify_cli/dashboard/handlers/*`,
`src/specify_cli/dashboard/scanner.py`, `src/specify_cli/merge/*`,
`src/runtime/next/*`, `src/mission_runtime/*`. None of `validators/**`,
`acceptance/**`, or `cli/**` (this mission's blast radius) is in that list. The only
other diff-coverage step ("full-diff, advisory") runs `diff-cover ... || true` —
genuinely non-blocking. So `diff-coverage --fail-under=90` does **not** enforce on
this mission's changed lines, contrary to the readiness-report framing that assumed
it would. This does not relax the mission's actual test obligation — NFR-001 and the
charter's "every new branch/helper needs tests in the same PR" bind independently via
the WP4 red-first tests actually running green in `fast-tests-cli`/
`integration-tests-cli` and `fast-tests-core-misc`/`integration-tests-core-misc` — but
the enforcement mechanism is "the tests exist and are green," not "the diff-coverage
tool measured 90% on these lines." Recorded here so sk-implement/sk-review does not
mistakenly treat a diff-coverage percentage as a required, blocking signal for this
PR. Full derivation: `plan.md`'s "Coverage floors" and "Gate set" sections.

## 2026-08-25 — plan phase: markdownlint does not bind on this mission's own kitty-specs artifacts

`.markdownlint-cli2.jsonc`'s `ignores` list explicitly includes `kitty-specs/**`, so
this `plan.md` and any tracer-file appends are exempt from the markdownlint CI gate.
Confirmed by reading the config file directly rather than assuming from the task
framing's "may or may not count, check" prompt.
