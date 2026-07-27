# Quality and DevEx Hardening 3.2

**Mission ID**: `01KRJGKH4DJCSF277K9QV3WBE7`
**Mission slug**: `quality-devex-hardening-3-2-01KRJGKH`
**Parent Epic**: [Priivacy-ai/spec-kitty#822](https://github.com/Priivacy-ai/spec-kitty/issues/822) — 3.2.0 stabilization and release readiness
**Target / merge branch**: `fix/quality-check-updates`
**Author profile**: python-pedro (Python implementer specialization — TDD, type safety, behavior-driven testing)
**Pre-mission intake**: [`.kittify/mission-brief.md`](../../.kittify/mission-brief.md), [`.kittify/ticket-context.md`](../../.kittify/ticket-context.md), and the research record under `work/findings/` on the same branch
**Pre-mission doctrine groundwork**: commits `380db5c2e` (regex tactic) and `0878f798d` (rule-pipeline tactic + code-patterns catalog)

## Problem Statement

The 3.2.x line cannot ship as stable while six aggregated tickets under epic #822 remain unresolved. Three failure modes co-exist on the current main (`eaf2df0a6`):

1. **The release-quality apparatus is failing or skipped.** Sonar quality gate is `ERROR` on `main` (new-code coverage 58.8 %, security hotspots 0 % reviewed). Push-time Sonar is gated to schedule/manual runs while the backlog is worked. The strict-mypy gate fails with 60 errors across 45 files.
2. **One reliability test is missing on a known-correct fallback path.** The `m_0_8_0` worktree-symlink migration has the `OSError → shutil.copy2` fallback in code but no regression test covering the fallback arm. The risk is silent regression on Windows runners.
3. **Two daily-use DevEx pain points remain.** `spec-kitty merge` fail-stops on stale lanes even when the conflict shape is additive-only and machine-resolvable — operators spend ~30 min per 10-WP mission rebasing trivial conflicts by hand. The CLI does not tell a user whether they are already on the latest supported version or on a build with no upgrade path; they are left guessing whether the upgrade check ran.

The unifying invariant: **the 3.2.x stable release must be one a user can trust on the daily path, not one that ships green only because the gate it should fail under was skipped.** Coverage is a proxy; stability is the real outcome.

## Motivation

- **Trust as the release bar.** Every ticket in this mission addresses a place where a user could either be silently misled (skipped gate, hidden upgrade state) or made to do trivial machine work (stale-lane rebases) by the current code.
- **Structural debt reduction, not duct-tape.** Refactoring of egregious cognitive-complexity offenders is in scope where the pre-mission audit classifies them as **debt** or **pipeline-shape**. Refactors are paired with characterization tests first — never the other way around. Functions documented as **deliberate linearity** (e.g. `_auth_doctor.render_report` with its 7-section-contract comment) are left alone unless the maintainer signs off.
- **Doctrine-first remediation.** Two doctrine commits landed on this branch before the mission was specified, so the mission can refer to them by name and every WP reaches for the same pattern: `secure-regex-catastrophic-backtracking` for regex hotspots and `chain-of-responsibility-rule-pipeline` for rule-pipeline refactors. The architecture catalog at `architecture/2.x/04_implementation_mapping/code-patterns.md` records the patterns the codebase now formally uses.
- **Epic #822 closure path.** Resolving these six tickets and the parallel mission `review-merge-gate-hardening-3-2-x-01KRC57C` (residual P1) clears the remaining release backlog for 3.2.0 stable.

## Scope

### In Scope

1. **Strict-mypy gate decision and outcome** (#971). The mission either makes the existing target (`src/specify_cli src/charter src/doctrine`) green or narrows the strict target with a documented release contract. The choice is part of this mission's first WP; the recommended default is **make it green** because the failures are concentrated and mechanical (missing stubs + concrete typing issues in `status/reducer.py`, `doctor.py`, `sync/__init__.py`, `agent_retrospect.py`, `auth/recovery`, `next/_internal_runtime`).
2. **Sonar new-code coverage on hot release / auth / sync paths** (#595, workstream A). Behavior-driven test authoring on the top uncovered files: `cli/commands/charter.py`, `cli/commands/doctor.py`, `next/_internal_runtime/engine.py`, `cli/commands/charter_bundle.py`, `cli/commands/agent/config.py`, `release/changelog.py`, `core/file_lock.py`. Tests follow `function-over-form-testing` — observable outcomes only, no constructor / getter / call-count assertions.
3. **Sonar security-hotspot triage** (#595, workstream B). All 6 hotspots resolved with one of: code fix, safe-by-design rationale recorded in Sonar, or false-positive rationale. Known classes: regex backtracking in `release/changelog.py` (apply `secure-regex-catastrophic-backtracking`), loopback `127.0.0.1` in auth/sync (likely safe-by-design — document once), review-lock signal safety.
4. **Structural debt refactor of egregious cognitive-complexity offenders** (#595, workstream C). Each Sonar S3776 hit gets a one-line classification before becoming a WP deliverable. Refactor candidates apply the appropriate doctrine tactic (`refactoring-extract-first-order-concept`, `refactoring-extract-class-by-responsibility-split`, `refactoring-guard-clauses-before-polymorphism`). Pipeline-shape candidates apply the `chain-of-responsibility-rule-pipeline` tactic (Transformer flavor for `migration/mission_state.py::_canonicalize_status_row` and `migration/rebuild_state.py`; Validator flavor for any new detector-shape code).
5. **Push-time SonarCloud restoration** (#825). Once the gate is green on `main`, the `.github/workflows/ci-quality.yml::sonarcloud` conditional flips from `schedule || workflow_dispatch` to `always()`; the temporary deferral comment is removed; CHANGELOG records the restoration.
6. **Targeted Windows symlink-fallback test** (#629). New test file `tests/upgrade/test_m_0_8_0_symlink_windows.py` using `monkeypatch.setattr(os, "symlink", _raise)` so the fallback path runs on every CI pass (POSIX and Windows). Covers both the happy fallback (`OSError → shutil.copy2`) and the dual-failure (`shutil.copy2 → OSError`) arms.
7. **Stale-lane auto-rebase with conflict classification** (#771). A new ADR proposes the conflict-classifier policy (additive-only vs semantic) before implementation. Implementation introduces `lanes/auto_rebase.py` orchestrator and `merge/conflict_classifier.py` rules, attempts `git merge <mission-branch>` inside the lane worktree on stale-detect, auto-resolves additive-only conflicts (pyproject deps, import-block adds, urls.py), regenerates `uv.lock` under a global file lock, and reports auto-resolved vs manual lanes. Semantic conflicts still halt with the current actionable error message.
8. **No-upgrade notification UX** (#740). New modules `core/upgrade_probe.py` (PyPI probe + channel classification) and `core/upgrade_notifier.py` (cache-aware emitter). Distinguishes "already on the latest supported version" from "build/channel with no upgrade path"; never blocks the CLI on network failure; rate-limited to once per 24 h with an `SPEC_KITTY_NO_UPGRADE_CHECK=1` opt-out; reuses `should_check_version()` rather than introducing a parallel gate.
9. **Doctrine and architecture catalog upkeep** (cross-cutting). Every WP cites the doctrine tactics it applies in its prompt. If a new pattern application surfaces in two-or-more places during the mission, the WP that crosses the second-consumer threshold updates `architecture/2.x/04_implementation_mapping/code-patterns.md` per the catalog's extension rules.

### Out of Scope (Non-Goals)

- The residual P1 tranche under mission `review-merge-gate-hardening-3-2-x-01KRC57C` (#987, #986, #985, #983, #984, #644-narrow). That mission owns those WPs; do not duplicate.
- PRs already in flight per epic #822: #1028 (#889 sync rejection), #1027 (#988 `next --json` claimability), #806 (#662 CI duplication).
- Broader encoding-policy audit (#644 broader subset, deferred to post-3.2 per epic).
- Refactor of functions classified as **deliberate linearity** in the audit, primarily `cli/commands/_auth_doctor.py::render_report` (CC 53 — opens with the documented "intentionally linear" comment) and its peer renderers at line 791.
- Renderer / formatter functions whose complexity comes from sequential pretty-printing (`charter_bundle.py::_render_human` family) — extract only if behavior tests demand it.
- New CLI commands; backwards-compatibility shims that are not issue-backed; product expansion of any kind.

## Mission Philosophy (binding for every WP)

1. **Coverage is a proxy; stability is the goal.** Behavior tests only. Apply `function-over-form-testing` — observable outcomes, no structural assertions, no over-mocking, no tests on constructors / getters / call counts. Construction coverage falls out of behavioral coverage naturally.
2. **Characterization tests precede every refactor** on migration / sync / charter / auth code. Per `tdd-red-green-refactor`: capture today's behavior in a fixture-driven test commit *before* the refactor commit. Migration paths run on real user data; behavior preservation is non-negotiable.
3. **Quality > speed.** Land a few WPs well rather than many duct-taped. The release-stability outcome matters more than ticket count.
4. **Test code is production code.** AAA structure visible at a glance, descriptive names of the form `test_<unit>_<behavior>_<context>`, one reason to fail per test, no copy-paste, shared fixtures in `conftest.py` or `tests/_factories/`.
5. **Doctrine tactics are not optional.** Every WP that touches a regex change cites `secure-regex-catastrophic-backtracking`. Every rule-pipeline refactor cites `chain-of-responsibility-rule-pipeline`. Every refactor cites the refactoring tactic it applies. Every test references `function-over-form-testing` if its shape is non-obvious.

## Doctrine and Architecture Contract

Every WP that touches the relevant concern MUST reference these artifacts in its prompt and tests.

### Tactics

| Tactic | Path | Binding scope |
|---|---|---|
| `secure-regex-catastrophic-backtracking` | `src/doctrine/tactics/shipped/secure-regex-catastrophic-backtracking.tactic.yaml` | Every regex change; every `python:S5852` / `python:S6353` Sonar finding. Wall-clock regression test (≤100 ms for 100 000 chars) required per fix. |
| `chain-of-responsibility-rule-pipeline` | `src/doctrine/tactics/shipped/code-patterns/chain-of-responsibility-rule-pipeline.tactic.yaml` | Transformer flavor for `migration/mission_state.py::_canonicalize_status_row` and `migration/rebuild_state.py`. Validator flavor for any new validator-shape code (audit detectors, charter-lint checks). |
| `function-over-form-testing` | `src/doctrine/tactics/shipped/testing/function-over-form-testing.tactic.yaml` | Every new test authored during this mission. |
| `tdd-red-green-refactor` | `src/doctrine/tactics/shipped/testing/tdd-red-green-refactor.tactic.yaml` | Every refactor that touches existing migration / sync / charter / auth code. |
| `refactoring-extract-first-order-concept` | `src/doctrine/tactics/shipped/refactoring/refactoring-extract-first-order-concept.tactic.yaml` | Per-rule extraction (rule pipelines); per-mode runner extraction (`doctor.py::mission_state` CLI multiplexer). |
| `refactoring-extract-class-by-responsibility-split` | `src/doctrine/tactics/shipped/refactoring/refactoring-extract-class-by-responsibility-split.tactic.yaml` | `charter_bundle.py` if a responsibility split surfaces during refactor. |
| `refactoring-guard-clauses-before-polymorphism` | `src/doctrine/tactics/shipped/refactoring/refactoring-guard-clauses-before-polymorphism.tactic.yaml` | Flattening step before rule extraction where conditional pyramids exist. |
| `secure-design-checklist` | `src/doctrine/tactics/shipped/secure-design-checklist.tactic.yaml` | New external surface introduced by #740 (PyPI probe in `upgrade_probe.py`). |

### Architecture documents

- `architecture/2.x/04_implementation_mapping/code-patterns.md` — core code-patterns catalog. Any new pattern that ends up applying in two-or-more places during this mission updates the catalog per its extension rules.
- Mission `review-merge-gate-hardening-3-2-x-01KRC57C` — concurrent in-flight mission. Its WPs are explicitly out of scope here; coordinate at merge time only.
- Epic [#822](https://github.com/Priivacy-ai/spec-kitty/issues/822) — release scope and per-ticket gating notes.

## User Scenarios and Testing

### Primary actors

- **Maintainer / release owner**: drives 3.2.0 stable release readiness; reads Sonar gate, mypy gate, CI workflow status; assesses ticket closure evidence.
- **Daily contributor**: runs `spec-kitty merge` on a 10-WP mission; expects the tool to handle trivial conflicts; expects the CLI to surface upgrade state on use.
- **Continuous-integration system**: runs the strict-mypy gate, the test suite, and (post-WP4 / pre-#825) the Sonar scan on every push to `main`.

### Scenario S-01 — Release owner validates 3.2.0 stable readiness

- **Given** all six tickets are closed (or formally deferred with rationale in the epic).
- **And** the Sonar `Priivacy-ai_spec-kitty` project on `main` reports `Quality gate: OK`.
- **And** `uv run mypy --strict <chosen target>` exits 0 in CI and locally.
- **And** the CI Quality workflow's `sonarcloud` job runs on every push to `main` (no schedule/dispatch restriction).
- **When** the release owner runs the fresh-user smoke (`init → specify → plan → tasks → implement/review → merge → PR`).
- **Then** the smoke passes without manual state repair, prompt repair, or branch reconstruction; the release can be tagged.

### Scenario S-02 — Contributor merges a 10-WP mission with overlapping lanes

- **Given** a mission with parallel lanes that each touched `pyproject.toml` and at least one `__init__.py` import block.
- **And** lanes A and B have already merged into the mission branch.
- **When** the contributor runs `spec-kitty merge` for lane C, which is now stale relative to the updated mission branch.
- **Then** the tool attempts `git merge <mission-branch>` inside the lane C worktree, classifies the resulting `pyproject.toml` + `__init__.py` conflicts as additive-only, resolves them via the union-merge driver, regenerates `uv.lock`, and continues the outer merge pipeline without operator intervention.
- **And** if lane D introduces a semantic conflict in `flags.py`, the tool halts with the current actionable error message, reports auto-resolved lanes vs the failing lane, and does not silently combine incompatible code.

### Scenario S-03 — Contributor invokes the CLI with no upgrade available

- **Given** the contributor has the latest published `spec-kitty-cli` version installed.
- **When** they run a CLI command (and have not opted out via `SPEC_KITTY_NO_UPGRADE_CHECK=1`).
- **Then** the CLI tells them once per 24-hour window that they are on the latest supported version, including the current installed version string.
- **And** if they are on a dev / release-candidate / non-PyPI build, the message instead says "build/channel with no upgrade path".
- **And** if the PyPI probe fails (offline, network error, rate-limited), the CLI proceeds without any message and without delay.
- **And** the existing hard CLI/project mismatch error is unchanged in look and behavior.

### Scenario S-04 — Windows CI verifies the symlink fallback

- **Given** the `m_0_8_0_worktree_agents_symlink` migration runs in an environment where `os.symlink` raises `OSError`.
- **When** the migration applies for a worktree.
- **Then** the migration falls back to `shutil.copy2`, the resulting `AGENTS.md` file exists in the worktree with the expected content, and the migration's `changes` list reports "(symlink failed)".
- **And** if `shutil.copy2` itself raises `OSError`, the migration reports the dual-failure in its `errors` list and the worktree state remains diagnosable.

### Edge cases

- **Sonar `new_coverage` cannot reach 80 % on the chosen surfaces.** The release owner negotiates a tiered threshold or accepts a documented exception in CHANGELOG. The mission cannot unilaterally lower the threshold.
- **`_auth_doctor.render_report` blocks the Sonar gate.** Default is to leave the function (its linearity is deliberate, per the in-code comment); coordinate with the auth maintainer; resolve the Sonar finding via per-file rationale annotation.
- **PyPI rate-limits the upgrade probe.** The probe MUST swallow the failure silently. The 24-hour cache MUST persist even when the most recent probe failed (e.g. cache "unknown" with a shorter retry window).
- **A lane-rebase auto-union produces a valid but semantically wrong merge.** Classifier rules must default to **fail-safe**: when in doubt, return `Manual` and halt. The ADR records every file-pattern rule explicitly.

## Domain Language

Canonical terms introduced or reinforced by this mission. Synonyms in the right column should be avoided in spec, plan, and WP prompts.

| Canonical term | Avoid |
|---|---|
| structural debt | "tech debt" (too broad); "complexity score" (proxy, not the thing) |
| deliberate linearity | "long but readable"; "intentional complexity" |
| pipeline-shape | "rule list"; "decorator chain"; "filter chain" |
| characterization test | "snapshot test" (overloaded); "regression test" (too broad) |
| Sonar quality gate | "Sonar pass/fail"; "Sonar status" |
| catastrophic backtracking | "slow regex"; "ReDoS" (only acceptable as parenthetical) |
| rule pipeline (Validator / Transformer / Scorer flavors) | "engine"; "pipeline" without flavor qualifier |

## Functional Requirements

| ID | Description | Tickets | Status |
|---|---|---|---|
| FR-001 | The CLI command `uv run mypy --strict <chosen target>` exits 0 in CI and locally. The chosen target is documented in `CHANGELOG.md` and is either the existing target (`src/specify_cli src/charter src/doctrine`) or a narrowed target with a documented re-add plan post-3.2. | #971 | Active |
| FR-002 | The Sonar quality gate for `Priivacy-ai_spec-kitty` on `main` reports `status: OK` with `new_coverage` ≥ 80 % on the new-code window and all gate conditions OK. | #595 | Active |
| FR-003 | All 6 outstanding Sonar security hotspots have either a code-fix resolution or a documented rationale (safe-by-design or false-positive) recorded in Sonar, so that `new_security_hotspots_reviewed` reaches 100 %. | #595 | Active |
| FR-004 | The CI Quality workflow `.github/workflows/ci-quality.yml::sonarcloud` runs on `push` events to `main` (no `schedule || workflow_dispatch` restriction) and the temporary deferral comment block is removed. | #825 | Active |
| FR-005 | A behavior test exists for the `m_0_8_0_worktree_agents_symlink` migration that asserts (a) the `OSError → shutil.copy2` fallback runs and produces an `AGENTS.md` file with the expected content, and (b) the dual-failure case produces an `errors` entry. The test runs on every CI pass (POSIX and Windows) using `monkeypatch` rather than being Windows-only. | #629 | Active |
| FR-006 | `spec-kitty merge` attempts `git merge <mission-branch>` inside a stale lane worktree before halting. Additive-only conflicts (pyproject dependencies, import-block additions, urls.py URL lists) are auto-resolved via a union-merge driver; `uv.lock` is regenerated under a global file lock; semantic conflicts halt with the current actionable error. The mission produces an ADR documenting the classifier rules before implementation begins. | #771 | Active |
| FR-007 | The CLI emits a non-blocking notification on use when (a) no upgrade is available because the installed version is the latest supported, or (b) the installed version is on a build/channel with no upgrade path. The notification carries the installed version, distinguishes the two cases, is cached for 24 hours, suppresses identical repeats within the window, never delays the CLI by more than 100 ms on the hot path, and can be disabled via `SPEC_KITTY_NO_UPGRADE_CHECK=1`. | #740 | Active |
| FR-008 | Every regex change in this mission carries a wall-clock regression test asserting linear runtime on an adversarial input characteristic of the rewritten pattern (default budget: ≤100 ms for 100 000 chars). Each test follows `function-over-form-testing`: completion-within-budget is the observable outcome being asserted. | #595 | Active |
| FR-009 | Every refactor of existing migration / sync / charter / auth code is preceded in commit history by a characterization-test commit that captures today's behavior on fixture inputs drawn from real artifacts (`.kittify/migrations/mission-state/`, charter bundles, sync envelopes). The refactor commit MUST leave those tests green. | #595 | Active |
| FR-010 | Each refactor of a high-cognitive-complexity offender cites in its WP prompt the doctrine refactoring tactic it applies (`refactoring-extract-first-order-concept` / `refactoring-extract-class-by-responsibility-split` / `refactoring-guard-clauses-before-polymorphism`) and the rationale for the classification (debt vs pipeline vs deliberate). | #595 | Active |
| FR-011 | Rule-pipeline refactors apply the `chain-of-responsibility-rule-pipeline` tactic. The motivating Transformer-flavor refactor lifts a typed `CanonicalRule` Protocol into `src/specify_cli/migration/canonicalization.py`, refactors `_canonicalize_status_row` and the analogous rules in `rebuild_state.py` onto it, and updates `architecture/2.x/04_implementation_mapping/code-patterns.md` to cite the new canonical implementation. | #595 | Active |
| FR-012 | The mission-review report (produced after merge) explicitly lists every doctrine tactic applied per WP and links the code-patterns catalog where a pattern was applied. Reviewers reject WPs whose prompts do not cite the tactics they should have applied. | (cross-cutting) | Active |
| FR-013 | The canonical-terminology glossary at `.kittify/glossaries/spec_kitty_core.yaml` carries an entry (`surface`, `definition`, `confidence`, `status: active`) for every canonical term introduced or reinforced by this mission — at minimum: `structural debt`, `deliberate linearity`, `pipeline-shape`, `characterization test`, `Sonar quality gate`, `catastrophic backtracking`, `rule pipeline` (with its three flavors), and any further canonical term that surfaces during plan or implement. Entries cross-reference the doctrine tactic or architectural document that codifies the term where one exists. The glossary update lands in the same WP that introduces or reinforces the term; deferring glossary work to a housekeeping pass is rejected at review. | (cross-cutting) | Active |

## Non-Functional Requirements

| ID | Description | Measurable threshold | Status |
|---|---|---|---|
| NFR-001 | Release-stability smoke: a fresh-user `init → specify → plan → tasks → implement/review → merge → PR` cycle on the post-merge `main` MUST succeed without manual state repair, prompt repair, or branch reconstruction. | Cycle completes; no manual repair steps recorded; PR opens cleanly. | Active |
| NFR-002 | Every new test in this mission MUST follow AAA structure visible without scrolling, use a descriptive name of the form `test_<unit>_<behavior>_<context>`, fail for exactly one reason, and avoid copy-paste of fixture setup (use `conftest.py` or `tests/_factories/`). | Reviewer checklist applied to every test file the mission adds. Reviewer rejects the WP otherwise. | Active |
| NFR-003 | No behavior regression on migration / sync / charter / auth code paths. The commit history shows a characterization-test commit immediately before any refactor that touches these paths, and the test suite is green at every commit boundary. | `git log --oneline` shows the characterization commit before each refactor commit; CI green on every commit. | Active |
| NFR-004 | The upgrade-check probe never delays the hot CLI startup path by more than 100 ms in the steady state, including the cache-warm case. The cold-cache path delegates the probe to a background path or accepts a one-time 300 ms budget on first run only. | Measured on the dev machine; recorded in the WP evidence. | Active |
| NFR-005 | The auto-rebase classifier defaults to **fail-safe** on any pattern not explicitly listed in the ADR. The ADR enumerates each file-pattern rule with examples and a "when NOT to apply" clause. | ADR review confirms every rule has an explicit example and counter-example. | Active |
| NFR-006 | The mission's own mission-review (post-merge) cites every doctrine tactic applied per WP and links to the code-patterns catalog where applicable. The mission cannot be marked release-ready otherwise. | Mission-review template extended in this mission's review WP, or the equivalent contract from the parallel mission `review-merge-gate-hardening-3-2-x-01KRC57C` (FR-005…FR-008) applies if it lands first. | Active |

## Constraints

| ID | Description | Status |
|---|---|---|
| C-001 | No work in this mission overlaps with the residual P1 tranche in mission `review-merge-gate-hardening-3-2-x-01KRC57C`. WPs that approach #987, #986, #985, #983, #984, or the #644 narrowed chokepoint MUST stop and coordinate. | Active |
| C-002 | No work in this mission duplicates the in-flight PRs cited in epic #822: #1028 (#889), #1027 (#988), #806 (#662). | Active |
| C-003 | Functions classified as **deliberate linearity** in the pre-mission audit, primarily `cli/commands/_auth_doctor.py::render_report` and its peer renderers, are not refactored without explicit auth-maintainer sign-off recorded in the WP evidence. Default is to leave them. | Active |
| C-004 | New CLI commands and backwards-compatibility shims that are not directly issue-backed are out of scope. | Active |
| C-005 | The Sonar `new_coverage` threshold (80 %) is the configured target. If unachievable on the chosen surfaces, the release owner decides the negotiated outcome (tiered threshold, documented exception, baseline reset). The mission cannot lower the threshold unilaterally. | Active |
| C-006 | The mypy strict scope decision (option A green-the-baseline vs option B narrow-the-target) is decided in this mission's first WP. The chosen option, rationale, and any deferred follow-up are recorded in CHANGELOG and the WP evidence. | Active |
| C-007 | The auto-rebase ADR (FR-006 dependency) MUST land and be linked from the WP before implementation begins on the auto-rebase WP. | Active |
| C-008 | The mission targets `fix/quality-check-updates` as its merge branch (where the pre-mission doctrine commits live). The branch will be merged to `main` as a single PR when the mission completes. | Active |

## Success Criteria

Outcome-level, measurable, technology-agnostic where the mission allows.

1. A 3.2.0 stable release can be cut from the post-merge `main` with no remaining P1 / P2 blockers in epic #822's six-ticket subset.
2. A maintainer running the release smoke (NFR-001) completes the full cycle in one attempt, with no manual repair steps in the cycle log.
3. A daily contributor merging a 10-WP mission with overlapping additive lanes does **not** rebase any lane by hand; the tool handles every additive conflict and reports semantic conflicts only.
4. A user running any CLI command sees either no upgrade notice (cache-warm), or a single, accurate, non-blocking notice within 100 ms on the hot path.
5. A Windows CI run exercises the `m_0_8_0` symlink fallback automatically; the same test runs on POSIX CI via `monkeypatch` so the fallback is covered on every PR.
6. The Sonar dashboard for `Priivacy-ai_spec-kitty` on `main` shows `Quality Gate: OK` for the new-code window, and the GitHub `sonarcloud` check runs on every push.
7. A future agent picking up the codebase finds the rule-pipeline pattern, the regex-secure-coding pattern, and the code-patterns catalog by reading the doctrine and architecture surfaces — without having to reverse-engineer the conventions from existing source files.

## Key Entities and Concepts

Domain entities that recur across requirements; concrete artifact types or contract elements that the mission produces or modifies.

- **`CanonicalRule`** (new typed Protocol). Per-step contract for the Transformer-flavor rule pipeline in `src/specify_cli/migration/canonicalization.py`. Each rule is a pure function `(state, ctx) -> CanonicalStepResult(state', actions, error?)`. Composed by a runner that short-circuits on `error`. Consumed by `_canonicalize_status_row` and the analogous functions in `rebuild_state.py`. Documented in the `chain-of-responsibility-rule-pipeline` tactic notes.
- **`UpgradeProbeResult`** (new value object). Output of the PyPI probe in `src/specify_cli/core/upgrade_probe.py`. Carries: installed version, latest PyPI version, channel classification (`already_current` / `ahead_of_pypi` / `no_upgrade_path` / `unknown`), probe timestamp, error if any. Consumed by `upgrade_notifier.py`.
- **`ConflictClassification`** (new value object). Output of the conflict classifier in `src/specify_cli/merge/conflict_classifier.py`. Carries: file path, hunk text, resolution (`Auto(text)` / `Manual(reason)`). Defined by the auto-rebase ADR; defaults fail-safe to `Manual` when no rule matches.
- **`StatusEvent`** (existing). The status-event row that `_canonicalize_status_row` transforms. Not modified by this mission, but the canonicalization pipeline's invariants on this entity (lane validity, required `to_lane` / `wp_id`, event-id format) are the contract the rule pipeline preserves.
- **`MissionFinding` / `LintFinding`** (existing). Value-object findings shared by audit, charter-lint, and any new validator code in this mission. Pure functions, no inheritance beyond dataclass.

## Open Questions

The following questions are unresolved at spec time and MUST be settled before the affected WP enters plan-phase. The recommended default is in parentheses where Pedro has a position.

1. **#971 mypy strict scope** (A or B). Recommended: A — make the existing target green. Decision lives in the first WP's prompt; record the choice and rationale in CHANGELOG.
2. **#771 conflict-classifier policy.** Which file patterns are auto-resolvable, which are always manual, and which require a deferred extension. Resolution path: ADR before implementation. Default: fail-safe on any unmatched pattern.
3. **`_auth_doctor.render_report` Sonar gate interaction.** If the gate cannot pass without addressing the function's CC 53, coordinate with the auth maintainer. Recommended default: leave the function and resolve the Sonar finding via per-file rationale annotation. Final call by the release owner.

## Acceptance — Release-Gate Level

A reviewer can close this mission as release-ready if and only if all of the following are demonstrably true:

- **Tickets.** All six tickets (#971, #825, #595, #629, #771, #740) are closed with regression evidence, or formally deferred with rationale committed to `work/findings/` and the epic #822 thread updated.
- **Sonar.** Quality gate on `main` is `OK`. Push-time Sonar runs on every push. Hotspot review is 100 %.
- **Mypy.** `uv run mypy --strict <chosen target>` exits 0 in CI and locally. CHANGELOG documents the chosen target.
- **Tests.** Every new test follows `function-over-form-testing`. No constructor / getter / call-count assertions. Reviewer applied the test-code hygiene checklist (NFR-002).
- **Refactors.** Every refactor of migration / sync / charter / auth code is preceded by a characterization-test commit (NFR-003 verified via `git log`).
- **Doctrine citations.** Every WP's prompt cites the doctrine tactics it applied. The mission-review report enumerates them per WP and links the code-patterns catalog where applicable.
- **Glossary.** `.kittify/glossaries/spec_kitty_core.yaml` carries entries for every canonical term in the Domain Language section, plus any further canonical term that surfaced during plan or implement (FR-013).
- **Smoke.** NFR-001 release-stability smoke passes on the post-merge `main`.

## Pre-Mission Research and Intake (binding source documents)

These are not duplicate citations — they are the canonical research input the spec was lifted from. Downstream agents should consult them when a WP prompt needs more detail than this spec carries.

- [`.kittify/mission-brief.md`](../../.kittify/mission-brief.md) — distilled brief, the same input that the specify skill consumed.
- [`.kittify/ticket-context.md`](../../.kittify/ticket-context.md) — per-ticket detail with code paths, validation snapshots, and acceptance criteria.
- `work/findings/00-summary.md` — mission philosophy + WP sequencing seed.
- `work/findings/refactor-audit.md` — three worked offenders classified into debt / deliberate / pipeline.
- `work/findings/rule-pipeline-pattern-survey.md` — codebase survey behind the single-tactic decision.
- `work/findings/971-mypy-strict.md`, `825-sonar-push-restore.md`, `595-sonar-coverage-debt.md`, `629-windows-symlink-test.md`, `771-auto-rebase-stale-lanes.md`, `740-no-upgrade-notification.md` — per-issue detail.
- `work/findings/session-overview.md` — full prep-phase record; candidate input for a future "pre-flight research mission" archetype.
