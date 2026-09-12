# Phase 0 Research: Modular per-package CI + automated asset/prompt regeneration

**Mission**: `modular-per-package-ci-01M025GV`
**Tracker**: [Priivacy-ai/spec-kitty#3447](https://github.com/Priivacy-ai/spec-kitty/issues/3447)
**Date**: 2026-08-15
**Status**: Complete — both load-bearing decisions settled; scope corrections applied; user forks confirmed.

This document settles the two load-bearing decisions the issue required research to decide, records the
codebase evidence that grounds them, and captures three scope corrections the investigation surfaced plus
the four downstream forks the operator confirmed.

---

## Decisions settled

### D1 — "Separate workflow as a precursor" mechanism → **(a) reusable workflows (`workflow_call`)**

Each module (kernel, doctrine, packs) becomes a self-contained `on: workflow_call` workflow file, invoked as
an ordered job **inside** `ci-quality.yml` via `uses:`. Coverage still aggregates in ONE run; Sonar stays a
single scan. Rejected: **(b)** top-level workflows chained by `workflow_run` (cross-run artifact fetch by
run-id, fragments Sonar's single-run context).

**Why (a) wins — evidence:**

1. **Coverage aggregation is already glob/pattern-based and per-run scoped**, so same-run reusable-workflow
   artifacts drop in with zero aggregator changes provided artifact + coverage filenames are preserved:
   - `diff-coverage` (PR-time gate): `download-artifact` with `pattern: '*-reports'` then `find … -name 'coverage-*.xml'` — `.github/workflows/ci-quality.yml:3467-3473`, `:3517-3519`.
   - `sonarcloud` (nightly/dispatch): same glob discovery → comma-joined `report_paths` → single scan — `ci-quality.yml:3721-3728`, `:3815-3870`, `:4022-4032`.
2. **Reusable-workflow jobs run inside the caller's run**, so their `upload-artifact` outputs are downloadable
   by later caller jobs in that same run (artifacts are per-run scoped). Standard GitHub Actions semantics.
3. **`quality-gate` absorbs required-check-name churn** — it consumes `toJSON(needs)` wholesale
   (`ci-quality.yml:4361`, `:4438`), so a `uses:` job surfacing inner checks as `caller / inner` does not
   break the single required check as long as branch protection pins `quality-gate`.
4. **Option (b)'s cross-run tax already exists once in-repo and is documented as a gap**: the `ui-e2e`
   coverage is fetched cross-workflow by head-SHA (`ci-quality.yml:3768-3813`, FR-013/#2623). Living proof
   that (b) is the costlier, error-prone path.
5. **`kernel-tests` is the clean first slice**: `needs: [changes]` only, single non-sharded job, own inline
   90% coverage floor, one `coverage-kernel.xml` / `kernel-test-reports` artifact already consumed by
   diff-coverage + sonarcloud + quality-gate — `ci-quality.yml:1077-1133`.

**Precedent for the standalone-module *step content*** (not the reusable mechanism): `doctrine-charter-tests.yml`
is an existing standalone top-level workflow, `paths:`-filtered, that runs `tests/doctrine|charter` independently
and documents the skip-with-green required-check pattern (`doctrine-charter-tests.yml:97-131`, `:204-225`). It
emits **no** coverage — so it models the module *test invocation* to lift, not the `workflow_call` mechanism
(no `workflow_call`/`workflow_run` exists anywhere in `.github/workflows/` today — this mission introduces the first).

**Gotchas carried into the plan:**
- **Architectural CI-model guards parse the job graph** and may assume every job has inline `steps:` rather
  than `uses:`. Must be read + updated: `tests/architectural/test_ci_collection_completeness.py`,
  `test_ci_quality_path_filters.py`, `_gate_coverage.py` critical-path parser (`ci-quality.yml:3491-3514`),
  `test_coverage_root_collisions.py`, `test_release_ci_ownership.py`. **Highest-effort integration point.**
- **Required-check pinning** in branch-protection is repo-admin config (not in-tree). The `uses:` refactor is a
  non-event iff `quality-gate` is the pinned check; verify before landing.

### D2 — Fork-PR regeneration UX → **check-only on fork PRs; auto-commit on same-repo/dispatch; maintainer PAT escape hatch**

- **Fork PRs run check-only** (`spec-kitty regen --check`, fail with exact command + diff). Technically forced:
  a fork PR's base-repo `GITHUB_TOKEN` is read-only and cannot push to the contributor's fork.
- **Same-repo push / `workflow_dispatch` auto-commit** the regenerated fixtures. Near-exact template:
  `all-contributors-normalize.yml` — `pull_request_target` + same-repo guard
  `github.event.pull_request.head.repo.full_name == github.repository` (`:18`) + bot identity + `git push
  origin HEAD:${{ head.ref }}` (`:63-74`), `permissions: contents: write` (`:12-14`).
- **Maintainer `regen` label → privileged run that pushes regen commits into the fork branch via a maintainer
  PAT** (operator's confirmed choice). This is the higher-UX, higher-risk option: it introduces a privileged
  secret and **requires a security review**. Must follow the `pull_request_target`-with-trusted-tooling pattern
  (never execute PR-supplied code; run base-repo tooling over PR data only). See Constraints below.

**Fork-detection idioms already in-repo** (reuse, don't invent): equality guard
`head.repo.full_name == github.repository` (`all-contributors-normalize.yml:18`, `ci-quality.yml:990`);
inequality env flag `IS_FORK_PR` (`ci-quality.yml:4247`, consumed to degrade-to-skip `:4292`); canonical-repo
pin `IS_CANONICAL_REPO` (`ci-quality.yml:4254`).

**Standalone regen entrypoint** — model on the existing dual-mode `spec-kitty doctrine regenerate-graph
[--check] [--json]` (`src/specify_cli/cli/commands/doctrine.py:211-294`): write-mode mutates fixtures,
`--check` renders into a tempdir + per-file byte comparison + exit 1 on stale + structured JSON. Proposed
surface: **`spec-kitty regen [--check] [--json]`**, registered alongside `materialize`
(`cli/commands/__init__.py:271`). It reuses existing render code with **no new render logic**:
- 12-agent command fixtures: `render_command_template()` (`src/specify_cli/template/asset_generator.py:117`)
  over `AGENT_COMMAND_CONFIG.keys()` (12) × `PROMPT_BACKED_COMMANDS` (12).
- Skill snapshots: `command_renderer.render(template_path, agent_key, version).to_skill_md()`
  (`src/specify_cli/skills/command_renderer.py:384`, `:124`) over `("codex","vibe")` × `PROMPT_BACKED_COMMANDS`.
- Check-mode failure prints offending `<agent>/<command>` + `difflib` unified diff + literal `Run: spec-kitty
  regen`, mirroring the gate's own message (`test_twelve_agent_parity.py:154-157`).

---

## Scope corrections (issue was imprecise; these reshape the spec)

1. **The drifting assets are committed *test fixtures*, NOT the untracked `.claude/commands/…`.**
   `git ls-files .claude/commands/` and `.agents/skills/` both return 0 — those are deployed to *consumer/global*
   roots, never committed here. The committed, CI-gated, drifting assets are:
   - `tests/specify_cli/regression/_twelve_agent_baseline/<agent>/<command>.<ext>` — 12 agents × 12
     prompt-backed commands = **144 files**.
   - `tests/specify_cli/skills/__snapshots__/<agent>/<command>.SKILL.md` — codex + vibe × 12 = **24 files**.
   #3379's "12 parity + 2 snapshot failures" maps exactly to one edited `specify` prompt. **Regen's real target
   is these 168 fixtures**, produced from source `packs/built-in/missions/mission-steps/<type>/<step>/prompt.md`.

2. **Per-package `pyproject.toml`s are DORMANT groundwork** — headers say "not yet built, published, or consumed
   by CI or any runtime import path" (`src/kernel/pyproject.toml:1-5`, `src/doctrine/pyproject.toml:1-5`). Root
   `pyproject.toml:147` still ships all seven packages as one distribution; CI installs the monorepo via `uv
   sync --frozen --all-extras`. **So this mission is a test-partition + workflow-structure split, not per-wheel
   builds.** The wheel cutover (kernel→doctrine→charter as ONE no-partial follow-on) is governed separately by
   ADR `docs/adr/3.x/2026-08-02-1-charter-wheel-assessment.md` (Accepted). Honors the Shared Package Boundary
   (ADR 2026-04-25-1): no new build gates requiring wheel publication.

3. **Sonar does NOT decorate PRs today.** The `sonarcloud` job is `if: always() && (schedule ||
   workflow_dispatch)` (`ci-quality.yml:3648`) — nightly/manual only, one scan, sets `sonar.branch.name` but no
   `sonar.pullrequest.*`. The PR-time coverage enforcement is the separate `diff-coverage` job
   (`ci-quality.yml:3429`, `--fail-under=90`, critical-path list already includes `src/kernel/*`,
   `src/doctrine/*`, `src/charter/*` at `:3491-3514`). The issue's "keep Sonar single-run PR decoration intact"
   is therefore read as **"don't fragment coverage across runs"**, not "preserve an existing PR-decoration
   feature."

---

## Baselines to re-home for the module-owned partition

| Baseline | Path | Pins |
|---|---|---|
| Twelve-agent command fixtures | `tests/specify_cli/regression/_twelve_agent_baseline/<agent>/<command>.<ext>` (144) | Byte-identical rendered command per (agent, command) |
| Skill snapshots | `tests/specify_cli/skills/__snapshots__/<agent>/<command>.SKILL.md` (24) | Byte-identical `SKILL.md` for codex + vibe |
| Golden count (skills) | `tests/specify_cli/skills/test_command_installer.py:707` — `len(CANONICAL_COMMANDS) == 15` | Total canonical command count |
| Golden count (agents) | `test_twelve_agent_parity.py:188` (`== 12`), `:234-244` (per-agent file count) | Agent count + per-agent fixture cardinality |
| CI path filters routing these | `ci-quality.yml:497` (`src/specify_cli/skills/**`), `:834` (`tests/specify_cli/regression/**`), focused step `:838-846` | Which fast-tests job runs the gate on which source path |
| Marker/route completeness oracles | `tests/architectural/test_marker_job_completeness.py`, `test_arch_shard_marker_completeness.py`, `test_ci_collection_completeness.py` | Every marker + every collected test's marker-set reaches a CI gate |
| Shard registry seam | `tests/_shard_registry.py`, `tests/_arch_shard_map.py`, `tests/_next_shard_map.py` | Path→shard assignment (arch/next groups) |

**Trap to avoid** (operator memory `double-marker-ci-home-trap`): relocating these tests must keep every
relocated test resolving to exactly one CI home, or `test_marker_job_completeness.py` reds.

---

## Version-pin asymmetry (resolved)

The two fixture suites hard-code DIFFERENT render versions: twelve-agent = `_BASELINE_VERSION = "3.1.2a3"`
(`test_twelve_agent_parity.py:80`, patched over `_get_cli_version`); skills = `_TEST_VERSION = "3.0.0"`
(`test_command_renderer.py:72`). A standalone regen must reproduce both exactly or fixtures won't match the
gates. **Decision (operator): hoist both pins to shared constants imported by BOTH the tests and `regen`** so
there is a single source of truth and the tool + gate can never diverge.

---

## Confirmed operator decisions (four downstream forks)

1. **Gate surface** → *Also narrow the gate AND add regen.* Do the regen automation **and** narrow the
   144+24 byte-grid to structural invariants + one canonical snapshot per the maintainer TODOs already in
   `test_twelve_agent_parity.py:26-37` and `test_command_renderer.py:19-30`. Permanently ends the churn.
2. **Version pins** → *Hoist to shared constants* (see above).
3. **Fork-PR escape hatch** → *`regen` label → maintainer PAT pushes regen commits into the fork branch.*
   Security-review-gated; privileged secret; `pull_request_target` trusted-tooling pattern mandatory.
4. **Sonar scope** → *Preserve current behavior* — single-run coverage aggregation + `diff-coverage` PR gate;
   **no** new Sonar PR decoration.

---

## Module inventory (what each precursor workflow owns)

- **kernel** (POC / first slice): `src/kernel` (zero-dep root package), tests `tests/kernel/`, `--cov=src/kernel`
  → `coverage-kernel.xml`. Lift `ci-quality.yml:1077-1133` verbatim into `.github/workflows/module-kernel.yml`.
- **doctrine**: `src/doctrine` (+ `src/charter`), tests `tests/doctrine/`, `tests/charter/`,
  `--cov=doctrine --cov=charter` → `coverage-fast-doctrine.xml` + `coverage-integration-doctrine.xml`. Two legs
  (fast + integration) — preserve `${{ matrix.shard }}` naming if ever sharded.
- **packs**: `packs/built-in` has no build and no dedicated test suite — its tests ride the `corpus` group
  (`fast-tests-corpus`, `--cov=src/doctrine`, `ci-quality.yml:1894`). "packs module" = lift `fast-tests-corpus`
  into a reusable file. **`spec-internal` is NOT in the tree** — deferred, not scaffolded this mission.

---

## Open items handed to spec/plan

- Read the five architectural CI-model guards (D1 gotcha) before committing to the slice count; they are the
  highest-effort integration risk.
- Confirm which check names branch protection pins (repo-admin) so the `uses:` refactor stays a non-event.
- Security review for the PAT-push labeled workflow (D2 decision 3) is a required, tracked precondition before
  that workflow lands enabled.
- Sequence: kernel POC (prove coverage-into-aggregation end-to-end) → doctrine + packs → regen tool → regen CI
  automation → gate narrowing → baseline re-homing.
