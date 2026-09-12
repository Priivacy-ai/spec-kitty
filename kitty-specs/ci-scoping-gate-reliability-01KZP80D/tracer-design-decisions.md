# Tracer: Design Decisions — ci-scoping-gate-reliability

Rationale that would otherwise evaporate. Append during implement.

## Planning phase (2026-08-10)

- **#3008 is TWO gates, fix the trigger first.** Gate 0 (`ci-quality.yml`
  `pull_request.paths`/`push.paths` omit `packs/**`/`kitty-specs/**`/`.kittify/**`) is the decisive one:
  a data-only PR never triggers the workflow at all. A dorny-group-only fix (Gate 1) would be inert.
- **Narrow globs, never bare `kitty-specs/**`.** Trigger on the four artifacts the corpus tests read
  (`spec.md`/`plan.md`/`tasks/**`/`contracts/**`/`acceptance-matrix.json`) + `packs/**` +
  `.kittify/{charter,glossaries,doctrine,skills}/**`. Bare `kitty-specs/**` would fire the heavy corpus
  suite on nearly every PR (status.events.jsonl churn). Also required by C-001 + the docs-freshness
  allowlist arch-invariant.
- **One blocking `fast-tests-corpus` job** (modeled on `fast-tests-docs`), not OR-ing the corpus group
  into ~9 heavyweight jobs — bounds per-PR cost. Blocking (feeds quality-gate) per operator decision.
  Do NOT add `docs/**`/`src/doctrine/**` (already covered) → no double-run (NFR-004).
- **#3147: diff-scope the BLOCKING check, retain whole-tree as non-blocking scheduled.** Scoping narrows
  which files are checked, not whether the check bites — a link the PR itself breaks still fails.
- **Co-evolve the arch invariants, never bypass.** New `corpus` group must be claimed in
  `test_ci_quality_path_filters.py` / `test_ci_collection_completeness.py` / `ci_topology_census.json`.
