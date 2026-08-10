# Phase 0 Research: CI Scoping Gate Reliability

The corpus-reading suite inventory + the exact two-gate trace (with file:line) is in
[research/corpus-suite-inventory.md](./research/corpus-suite-inventory.md), produced by a pre-spec
squad (analytical corpus-mapper + breadth grep sweep). This records the approach decisions.

## Decision: fix the TRIGGER first (Gate 0), then the group/job (Gate 1)

- **Decision**: #3008 is TWO gates. Gate 0 (decisive): `ci-quality.yml` `pull_request.paths` (:14-30)
  AND `push.paths` (:44-66) omit `packs/**`, `kitty-specs/**`, most `.kittify/**`, so a data-only PR
  never triggers the workflow — pre- AND post-merge. Gate 1: even when triggered, no dorny group
  selects the corpus suites. Both must be closed; the trigger is the load-bearing one.
- **Rationale**: adding only a dorny group (Gate 1) without the trigger paths (Gate 0) leaves the
  workflow un-triggered on data-only PRs — the fix would be inert.
- **Alternatives considered**: dorny-group-only — rejected (inert without the trigger).

## Decision: narrow globs — never bare kitty-specs/** (avoid the status-churn trap)

- **Decision**: trigger on `packs/**`, and the DISCRETE globs `kitty-specs/**/spec.md`,
  `kitty-specs/**/plan.md`, `kitty-specs/**/tasks/**`, `kitty-specs/**/contracts/**`,
  `kitty-specs/**/acceptance-matrix.json`, `.kittify/charter/**`, `.kittify/glossaries/**`,
  `.kittify/doctrine/**`, `.kittify/release/downstream-verified.json`. Do NOT glob bare
  `kitty-specs/**` or `status.events.jsonl`/notes/trace.
- **B1 (post-plan squad):** in `on.paths`/`push.paths` these MUST be discrete entries — GitHub's
  top-level path matcher does NOT support `{a,b}` brace expansion (only `* ** ? + ! []`); braces there
  match nothing and the fix ships inert. Brace form is fine ONLY inside a dorny filter. Drop
  `.kittify/skills/**` (no such dir in this repo). See tracer-squad-findings.md.
- **Rationale**: nearly every mission PR appends to `status.events.jsonl`; a bare glob fires the heavy
  corpus suite on almost every PR. The narrow set is exactly what the four kitty-specs-reading tests
  consume. (C-001; the docs-freshness allowlist arch-invariant also forbids `kitty-specs/**` there.)
- **Alternatives considered**: bare `kitty-specs/**` — rejected (false-trigger explosion).

## Decision: one blocking corpus job (not a 9-way fan-out)

- **Decision**: a single `fast-tests-corpus` job modeled on `fast-tests-docs` (:1808-1833), gated on
  `corpus || push`, running the corpus-reading dirs (`tests/doctrine tests/missions
  tests/specify_cli/missions tests/charter tests/architectural tests/contract tests/glossary`), wired
  into `quality-gate` (blocking, NFR-001). `arch-adversarial` needs no edit (its `always()` fires once
  the workflow triggers).
- **Rationale**: OR-ing the corpus group into ~9 heavyweight jobs' `if:` fans out cost on every mission
  PR; one dedicated job bounds it. Do NOT add `docs/**`/`src/doctrine/**` (already covered) — no
  double-run (NFR-004).
- **Alternatives considered**: OR the group into each existing job — rejected (cost fan-out + NFR-004).

## Decision: #3147 diff-scope the blocking check, keep whole-tree non-blocking

- **Decision**: the blocking dead-link check evaluates only the PR's changed files (anchored to the PR
  base ref); the whole-tree scan moves to a scheduled/full-run non-blocking signal (a CI trigger/config
  boolean), never deleted.
- **Rationale**: unrelated pre-existing rot must not fail a docs PR (FR-004), but repo-wide rot must
  still be detectable (FR-005/C-002). Diff-scope narrows WHICH files are checked, not whether the check
  bites — a broken link the PR introduces still fails it.
- **Risk recorded**: a mis-computed base ref is a false-green vector — anchor to the PR base explicitly.

## Decision: co-evolve the arch invariants, add a regression guard

- **Decision**: update `test_ci_quality_path_filters.py`, `test_ci_collection_completeness.py`, and
  `ci_topology_census.json` to claim the new `corpus` group; add a test asserting the group IS selected
  on corpus data and is NOT selected on a `status.events.jsonl`-only diff (NFR-002/SC-002).
- **Rationale**: these invariants exist to prove the path-filter partition is total; a new group must be
  claimed, not silently uncovered. Never `# noqa`/skip to pass (NFR-003).
