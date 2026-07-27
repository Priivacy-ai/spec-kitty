# Implementation Plan: Quality and DevEx Hardening 3.2

**Mission ID**: `01KRJGKH4DJCSF277K9QV3WBE7`
**Mission slug**: `quality-devex-hardening-3-2-01KRJGKH`
**Branch**: `fix/quality-check-updates`
**Date**: 2026-05-14
**Spec**: [`spec.md`](spec.md)
**Pre-mission intake**: [`/.kittify/mission-brief.md`](../../.kittify/mission-brief.md), [`/.kittify/ticket-context.md`](../../.kittify/ticket-context.md)
**Author profile**: python-pedro

## Summary

This mission resolves the six tickets aggregated under epic [#822](https://github.com/Priivacy-ai/spec-kitty/issues/822) — mypy strict gate (#971), Sonar coverage debt (#595), Sonar push-time restoration (#825), Windows symlink-fallback test (#629), stale-lane auto-rebase (#771), and no-upgrade UX notification (#740) — for the 3.2.0 stable release. The mission's binding philosophy is structural debt reduction over duct-tape: refactors are paired with characterization tests first, tests assert behavior not structure (per `function-over-form-testing`), and every WP cites the doctrine tactic it applies.

Technical approach (consolidated from `/work/findings/` and the resolved Decision Moment on mypy scope):

- **Mypy strict (#971): option (A) — fix the existing target green.** Recorded in `decisions/DM-01KRJHT7QD7XQMY33Y5TDTQ80V.md`. Approach is concentrated and mechanical: add type stubs (`types-PyYAML`, `types-toml`, `types-jsonschema`, `types-psutil`, `types-requests`) to the dev dependency group, fix concrete typed-code errors in `status/reducer.py`, `doctor.py`, `sync/__init__.py`, `agent_retrospect.py`, `auth/recovery`, `next/_internal_runtime/*`. The `doctor.py:1092` `RepairReport` ↔ `RepoAuditReport` mismatch gets a regression test before the type is narrowed because it likely masks a real branch bug. For `re2`, drop strict (the package has no shipped stubs and is a thin wrapper).
- **Sonar gate (#595, #825): three workstreams in priority order.** (1) Characterization tests on the hot uncovered paths (charter.py, doctor.py, next engine, charter_bundle, agent/config, changelog, file_lock) authored per `function-over-form-testing`. (2) Hotspot triage — the regex hotspots in `release/changelog.py` apply `secure-regex-catastrophic-backtracking` with wall-clock regression tests; the `127.0.0.1` loopback findings get a one-time safe-by-design rationale recorded in Sonar; the review-lock signal-safety hotspot is triaged on its merits. (3) Structural debt refactors of debt-classified or pipeline-shape S3776 offenders — apply `refactoring-extract-first-order-concept` for CLI multiplexers (`doctor.py::mission_state`), `chain-of-responsibility-rule-pipeline` (Transformer flavor) for canonicalization (`_canonicalize_status_row` + `rebuild_state.py`). Push-time Sonar (#825) is the gate-flip at the end: one-line conditional change in `.github/workflows/ci-quality.yml` once gate status is OK on `main`.
- **Symlink test (#629): one new test file** at `tests/upgrade/test_m_0_8_0_symlink_windows.py` using `monkeypatch.setattr(os, "symlink", _raise)` so the fallback runs on every POSIX CI pass — not Windows-only. Parametrizes the dual-failure arm. ~30-min WP.
- **Auto-rebase (#771): ADR-first, then implementation.** An ADR drafted in plan-phase (`architecture/2.x/adr/2026-05-14-1-stale-lane-auto-rebase-classifier-policy.md`) proposes the file-pattern rules (pyproject deps, import-block adds, urls.py URL lists) and the fail-safe default. Implementation introduces `src/specify_cli/lanes/auto_rebase.py` + extends `src/specify_cli/merge/conflict_resolver.py`. Reuses `specify_cli.core.file_lock` for the `uv.lock` regeneration mutex.
- **No-upgrade UX (#740): two new contained modules** at `src/specify_cli/core/upgrade_probe.py` (PyPI probe + channel classification) and `src/specify_cli/core/upgrade_notifier.py` (cache-aware emitter). 24-hour cache, opt-out env `SPEC_KITTY_NO_UPGRADE_CHECK=1`, 100 ms hot-path budget (NFR-004). New external surface — apply `secure-design-checklist` at design time.
- **Cross-cutting (FR-013): glossary entries** for every canonical term in the spec's Domain Language section land in `.kittify/glossaries/spec_kitty_core.yaml` in the same WP that introduces or reinforces the term — not in a housekeeping pass.

## Technical Context

**Language/Version**: Python 3.11+ (project floor; current install is 3.11.15)
**Primary Dependencies**: `typer`, `rich`, `ruamel-yaml`, `pytest`, `pytest-cov`, `mypy` (strict), `ruff`, `httpx` (the Sonar gate runner already invokes these; mission adds `types-PyYAML`, `types-toml`, `types-jsonschema`, `types-psutil`, `types-requests` to the dev group; introduces no new runtime dependency)
**Storage**: Filesystem only (YAML doctrine + JSONL event log + `~/.cache/spec-kitty/upgrade-check.json` for the new probe)
**Testing**: `pytest` with `pytest-cov`, behavior-driven per `function-over-form-testing`; characterization tests precede every refactor on migration / sync / charter / auth code per `tdd-red-green-refactor`; wall-clock regression tests for regex fixes per `secure-regex-catastrophic-backtracking`
**Target Platform**: Cross-platform CLI (Linux, macOS, Windows); Windows symlink fallback is the focus of one WP
**Project Type**: Single project (existing `src/specify_cli/` + `src/doctrine/` + `src/charter/` packages; no new top-level directory)
**Performance Goals**: Upgrade probe ≤ 100 ms on the hot CLI startup path (cache-warm); auto-rebase + union-merge completes in seconds per stale lane; regex remediation asserts ≤ 100 ms wall-clock for 100 000-char adversarial inputs
**Constraints**: No new CLI commands (constraint C-004); no backwards-compatibility shims that are not issue-backed; deliberate-linearity functions stay untouched without maintainer sign-off (C-003); merge target is `fix/quality-check-updates` (C-008)
**Scale/Scope**: Six tickets across six work-package candidates plus cross-cutting glossary upkeep; ~60 mypy errors to fix; ~720 Sonar code-smells on new code (triaged, not all addressed); ~10 high-cognitive-complexity functions to classify (debt / pipeline / deliberate); ~3 new modules; ~1 ADR; ~10–15 new behavior-test files

## Doctrine and Architecture Contract (binding citations)

Every WP cites the tactics it applies in its prompt. Reviewers reject WPs whose prompts do not cite the tactics they should have applied (FR-012, NFR-006).

### Tactics

- `secure-regex-catastrophic-backtracking` (`src/doctrine/tactics/shipped/secure-regex-catastrophic-backtracking.tactic.yaml`) — governs every regex change in this mission; wall-clock regression test required per fix (FR-008).
- `chain-of-responsibility-rule-pipeline` (`src/doctrine/tactics/shipped/code-patterns/chain-of-responsibility-rule-pipeline.tactic.yaml`) — Transformer flavor for the `_canonicalize_status_row` + `rebuild_state.py` refactor (FR-011); Validator flavor for any new detector-shape code introduced incidentally.
- `function-over-form-testing` (`src/doctrine/tactics/shipped/testing/function-over-form-testing.tactic.yaml`) — every new test (FR-008, FR-012, NFR-002).
- `tdd-red-green-refactor` (`src/doctrine/tactics/shipped/testing/tdd-red-green-refactor.tactic.yaml`) — every refactor on migration / sync / charter / auth code (FR-009, NFR-003).
- `refactoring-extract-first-order-concept` (`src/doctrine/tactics/shipped/refactoring/refactoring-extract-first-order-concept.tactic.yaml`) — `doctor.py::mission_state` per-mode-runner extraction; per-rule extraction in canonicalization (FR-010, FR-011).
- `refactoring-guard-clauses-before-polymorphism` (`src/doctrine/tactics/shipped/refactoring/refactoring-guard-clauses-before-polymorphism.tactic.yaml`) — flattening step before rule extraction where conditional pyramids exist.
- `refactoring-extract-class-by-responsibility-split` (`src/doctrine/tactics/shipped/refactoring/refactoring-extract-class-by-responsibility-split.tactic.yaml`) — `charter_bundle.py` if a responsibility split surfaces during refactor.
- `secure-design-checklist` (`src/doctrine/tactics/shipped/secure-design-checklist.tactic.yaml`) — new external surface introduced by #740 PyPI probe.

### Architecture documents

- `architecture/2.x/04_implementation_mapping/code-patterns.md` — core code-patterns catalog. WP that crosses the second-consumer threshold for a pattern updates the catalog per its extension rules (FR-011 + Success Criterion 7).
- New ADR `architecture/2.x/adr/2026-05-14-1-stale-lane-auto-rebase-classifier-policy.md` — proposes the conflict-classifier file-pattern rules for #771 (C-007). Draft template in `/contracts/stale-lane-auto-rebase-classifier-policy.md`.

## Charter Check

Charter context loaded in `compact` mode (1614 chars). Governance:

- **Template set**: `software-dev-default`.
- **Directives in scope**: DIR-001 (Architectural Integrity), DIR-002, DIR-003, DIR-004.
- **Charter glossary obligation** (per the existing charter section): every WP that introduces a new canonical term adds the corresponding entry to `.kittify/glossaries/spec_kitty_core.yaml` with `surface`, `definition`, `confidence`, `status: active`. **Satisfied by FR-013 in spec.md.**
- **Test/typecheck quality gate** (DIRECTIVE_030 referenced by Pedro profile): pytest + mypy + ruff must pass before WP handoff. **Satisfied by NFR-002 + NFR-003 + the mission-review WP that runs the gate.**
- **Locality of change** (DIRECTIVE_024): refactors stay close to the problem. **Satisfied by the audit-classification rubric — each S3776 hit gets a one-line triage; we do not sweep.**
- **Boundary scope**: mission cannot duplicate residual P1 tranche (mission `review-merge-gate-hardening-3-2-x-01KRC57C`) or in-flight PRs (#1028 / #1027 / #806). **Satisfied by C-001 + C-002.**

**Gate status**: PASS. No violations to justify in Complexity Tracking. Re-check after Phase 1 (data-model + contracts) — performed below.

## Project Structure

### Documentation (this feature)

```
kitty-specs/quality-devex-hardening-3-2-01KRJGKH/
├── spec.md                                          # /spec-kitty.specify output (FR/NFR/C tables)
├── plan.md                                          # this file
├── research.md                                      # focused — most pre-research was done pre-mission
├── data-model.md                                    # new value objects: CanonicalRule/StepResult, UpgradeProbeResult, ConflictClassification
├── quickstart.md                                    # contributor verification recipes
├── contracts/
│   ├── stale-lane-auto-rebase-classifier-policy.md  # ADR draft / classifier rules for #771
│   ├── upgrade-probe-and-notifier.md                # external surface for #740 (probe + cache + opt-out env)
│   └── canonicalization-rule-pipeline.md            # Transformer-flavor contract for migration/canonicalization.py
├── checklists/
│   └── requirements.md                              # spec quality checklist (already authored)
├── decisions/
│   └── DM-01KRJHT7QD7XQMY33Y5TDTQ80V.md             # mypy scope decision moment (resolved: A)
├── meta.json                                        # mission identity
├── status.json
├── status.events.jsonl
└── tasks/                                           # populated by /spec-kitty.tasks
    └── README.md
```

### Source Code (repository root)

```
src/
├── specify_cli/
│   ├── cli/commands/
│   │   ├── doctor.py                          # MODIFIED — extract per-mode runners from mission_state
│   │   ├── charter.py                         # MODIFIED — coverage characterization tests; no refactor unless review demands
│   │   ├── charter_bundle.py                  # MODIFIED if responsibility split surfaces
│   │   ├── agent_retrospect.py                # MODIFIED — type annotations
│   │   └── agent/config.py                    # MODIFIED — coverage characterization tests
│   ├── core/
│   │   ├── upgrade_probe.py                   # NEW (FR-007 / #740) — PyPI probe + channel classifier
│   │   ├── upgrade_notifier.py                # NEW (FR-007 / #740) — cache-aware emitter
│   │   ├── version_checker.py                 # MODIFIED — extend should_check_version() hook
│   │   └── file_lock.py                       # used by auto-rebase mutex; no contract change
│   ├── lanes/
│   │   ├── merge.py                           # MODIFIED — delegates to auto_rebase before halting
│   │   └── auto_rebase.py                     # NEW (FR-006 / #771) — orchestrator
│   ├── merge/
│   │   ├── conflict_classifier.py             # NEW (FR-006 / #771) — file-pattern rules
│   │   └── conflict_resolver.py               # MODIFIED — union-merge driver for additive cases
│   ├── migration/
│   │   ├── canonicalization.py                # NEW (FR-011) — CanonicalRule Protocol + runner
│   │   ├── mission_state.py                   # MODIFIED — _canonicalize_status_row lifts onto Protocol
│   │   └── rebuild_state.py                   # MODIFIED — analogous rules lift onto Protocol
│   ├── release/
│   │   └── changelog.py                       # MODIFIED — regex rewrite under secure-regex tactic + wall-clock test
│   ├── status/
│   │   └── reducer.py                         # MODIFIED — type annotation fix
│   ├── sync/
│   │   └── __init__.py                        # MODIFIED — return-type annotation
│   └── upgrade/migrations/
│       └── m_0_8_0_worktree_agents_symlink.py # not modified — only the test is new

tests/
├── unit/
│   └── migration/
│       └── test_canonicalization_rules.py     # NEW — parametrized per-rule tests (FR-011)
├── integration/
│   ├── migration/
│   │   └── test_canonicalization_pipeline.py  # NEW — end-to-end fixture tests from .kittify/migrations/mission-state/
│   ├── lanes/
│   │   └── test_auto_rebase_additive.py       # NEW — two-lane pyproject + import-block merge
│   └── merge/
│       └── test_conflict_classifier.py        # NEW — parametrized file-pattern rules
├── upgrade/
│   └── test_m_0_8_0_symlink_windows.py        # NEW (FR-005 / #629)
├── core/
│   └── test_upgrade_probe_and_notifier.py     # NEW — behavior tests for FR-007
├── regressions/
│   └── test_changelog_regex_redos.py          # NEW — wall-clock regression for FR-008
├── cli/commands/
│   ├── test_doctor_mission_state.py           # NEW — characterization tests for the multiplexer
│   ├── test_charter_coverage.py               # NEW — behavior coverage on hot paths
│   ├── test_charter_bundle_coverage.py        # NEW — behavior coverage
│   ├── test_agent_config_coverage.py          # NEW — behavior coverage
│   └── test_agent_retrospect_coverage.py      # NEW — behavior coverage
└── core/
    └── test_file_lock_behavior.py             # NEW — coverage on uncovered branches

.github/workflows/
└── ci-quality.yml                             # MODIFIED — sonarcloud trigger flipped (FR-004 / #825)

src/doctrine/tactics/shipped/
└── (no new tactics in this mission — the two pre-mission tactics + existing refactoring/testing tactics cover the contract)

.kittify/glossaries/
└── spec_kitty_core.yaml                       # MODIFIED — entries for FR-013 canonical terms

architecture/2.x/
├── 04_implementation_mapping/code-patterns.md # MODIFIED — cite migration/canonicalization.py as canonical Transformer-flavor implementation
└── adr/
    └── 2026-05-14-1-stale-lane-auto-rebase-classifier-policy.md  # NEW — required by C-007 before FR-006 implementation
```

**Structure Decision**: Single-project layout (existing `src/specify_cli/` + `src/doctrine/` + `src/charter/`). The mission introduces three new contained modules (`core/upgrade_probe.py`, `core/upgrade_notifier.py`, `lanes/auto_rebase.py`, `merge/conflict_classifier.py`, `migration/canonicalization.py`) and modifies the rest in place. No new top-level package. The new modules are sized to be reviewable and follow the locality-of-change directive.

## Phasing

### Phase 0 — Research (deliberately small)

Pre-mission research is comprehensive (see `/work/findings/`). Phase 0 produces a focused `research.md` covering only the gaps that surfaced during plan-phase:

1. **`re2` typing strategy.** Whether to drop strict on the `re2` import sites, add a `.pyi` shim, or replace `re2` usage entirely. (Pre-research recommended drop-strict; this phase confirms.)
2. **Sonar new-code-baseline reset decision input.** Pull the current "previous version" baseline value from Sonar; produce the data the release owner needs to decide whether to reset it. (Decision itself belongs to the release owner; we produce evidence.)
3. **Auto-rebase classifier rule corpus.** Enumerate real-world conflict shapes observed in past missions (from `.worktrees/` git history) to validate that the ADR's file-pattern list covers them. This is the input for the ADR; not the ADR itself.
4. **`charter.py` testability triage.** The file has 645 uncovered new lines. Phase 0 produces a one-page note classifying which functions are pure-and-coverable vs which need fixture/typer-runner scaffolding. Drives the per-WP slicing in `/spec-kitty.tasks`.

Phase 0 does **not** re-litigate decisions already made in pre-mission research or in the resolved Decision Moment. Most of the planning ground is on `/work/findings/`.

### Phase 1 — Design and Contracts

1. **`data-model.md`** — value objects introduced by the mission: `CanonicalRule` Protocol + `CanonicalStepResult`, `UpgradeProbeResult`, `ConflictClassification`. Includes invariants (e.g. `CanonicalStepResult.error` short-circuits the pipeline; `UpgradeProbeResult.channel` is one of four documented values; `ConflictClassification` defaults to `Manual` when no rule matches).
2. **`contracts/canonicalization-rule-pipeline.md`** — Transformer-flavor contract for `src/specify_cli/migration/canonicalization.py`. Per-rule Protocol; runner short-circuit semantics; actions accumulation. Cites `chain-of-responsibility-rule-pipeline` tactic notes.
3. **`contracts/upgrade-probe-and-notifier.md`** — external surface for the PyPI probe. Endpoint shape, response handling, cache file layout, opt-out env, channel classification rules, 100 ms hot-path budget contract. Cites `secure-design-checklist` for the new-external-surface treatment.
4. **`contracts/stale-lane-auto-rebase-classifier-policy.md`** — ADR-draft of the file-pattern rules; fail-safe default; per-rule examples and counter-examples. Becomes the canonical ADR text once approved.
5. **`quickstart.md`** — contributor recipes to verify the mission's outcomes: run mypy strict locally, pull Sonar gate status via the REST API helper (`work/snippets/sonarcloud_branch_review.sh`), run the two-lane auto-rebase smoke, trigger the upgrade-probe with cache cold/warm, run the symlink-fallback test.

### Phase 2 — Tasks (DO NOT execute here)

Tasks decomposition is `/spec-kitty.tasks` territory. This plan documents the expected WP shape so the tasks workflow has a clear input:

| Candidate WP | Concern | Doctrine citations | Dependencies |
|---|---|---|---|
| WP01 — mypy strict baseline green | FR-001 (#971) | `function-over-form-testing` (regression test for `doctor.py:1092`); `refactoring-guard-clauses-before-polymorphism` if any flattening surfaces | none |
| WP02 — Windows symlink-fallback test | FR-005 (#629) | `function-over-form-testing` | none |
| WP03 — Canonicalization rule-pipeline extraction | FR-009, FR-010, FR-011 (part of #595 structural debt) | `chain-of-responsibility-rule-pipeline` (Transformer), `refactoring-extract-first-order-concept`, `tdd-red-green-refactor` (characterization first) | WP01 (clean baseline) |
| WP04 — Sonar regex hotspots + wall-clock tests | FR-003 (regex hotspots), FR-008 (#595) | `secure-regex-catastrophic-backtracking`, `function-over-form-testing` | none |
| WP05 — Sonar coverage on hot release/auth paths | FR-002 (#595) | `function-over-form-testing`, characterization-first where refactor surfaces | WP04 (regex shape locked) |
| WP06 — `doctor.py::mission_state` multiplexer refactor | FR-010 (debt classification — part of #595) | `refactoring-extract-first-order-concept`, `function-over-form-testing`, `tdd-red-green-refactor` | WP05 (characterization coverage exists) |
| WP07 — Sonar hotspot triage (non-regex) + Sonar gate flip | FR-003 (#595), FR-004 (#825) | (CI yaml change; coordinated with infra reviewer) | WP04 + WP05 + WP06 + Sonar OK on main |
| WP08 — Auto-rebase ADR + classifier + auto-rebase orchestrator | FR-006 (#771) | (ADR-led design); `function-over-form-testing` integration test | WP01 |
| WP09 — Upgrade-probe + notifier modules | FR-007 (#740) | `secure-design-checklist`, `function-over-form-testing` | WP01 |
| WP10 — Glossary upkeep + code-patterns catalog update + mission-review | FR-012, FR-013, NFR-006 | Closes the cross-cutting requirements | WP01..WP09 |

Lane computation in `/spec-kitty.tasks` will validate or refine this. WP02, WP04, WP08, WP09 are independent of WP01 if `mypy strict` is not a global pre-condition — but Pedro analysis prefers landing WP01 first so subsequent WPs do not chase the moving target.

## Charter Re-Check (post-design)

Re-evaluating after the data-model + contracts pass:

- **DIR-001 (Architectural Integrity)**: PASS — new modules align with existing package boundaries (`core/`, `lanes/`, `merge/`, `migration/`). The auto-rebase ADR is the architectural-integrity artifact for the new merge-semantics surface.
- **DIRECTIVE_024 (Locality)**: PASS — each WP confines its diff to the named files; no sweep refactors.
- **DIRECTIVE_030 (Quality Gate)**: PASS — pytest + ruff + mypy enforced per WP; characterization-test-first contract makes the gate executable.
- **DIRECTIVE_034 (Test-First)**: PASS — FR-009 + NFR-003 codify the characterization-first ordering.
- **Glossary obligation (charter)**: PASS — FR-013 satisfies in-WP glossary entries; constraint added to acceptance.
- **Bounded scope vs concurrent mission `01KRC57C`**: PASS — C-001 and C-002 explicitly carve out the residual P1 tranche and the in-flight PRs.

No new violations. No entries needed in Complexity Tracking.

## Complexity Tracking

No violations to justify. Charter Check passes on both pre- and post-design evaluations.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| (none) | (n/a) | (n/a) |

## Open architectural questions (status)

1. **#971 mypy strict scope** — RESOLVED. Decision Moment `DM-01KRJHT7QD7XQMY33Y5TDTQ80V` recorded option (A) "fix the existing target green". `re2` strict-drop is the only sub-question, handled by Phase 0 research.
2. **#771 conflict-classifier policy** — Drafted in `contracts/stale-lane-auto-rebase-classifier-policy.md`. The ADR becomes canonical in `architecture/2.x/adr/2026-05-14-1-stale-lane-auto-rebase-classifier-policy.md` once approved (PROPOSED → ACCEPTED). Plan-phase deliverable; no HiC pause unless the operator wants to review the draft before WP08 starts.
3. **`_auth_doctor.render_report` deliberate-linearity vs Sonar gate** — DEFERRED. Default per spec is to leave the function and resolve the Sonar finding via per-file rationale. If WP07 (Sonar gate flip) shows the gate cannot pass without addressing the function, escalate to the auth maintainer + release owner before WP07 lands.

## Decisions Log

| Decision | Outcome | Artifact |
|---|---|---|
| Mypy strict scope (option A vs B) | (A) fix existing target green | `decisions/DM-01KRJHT7QD7XQMY33Y5TDTQ80V.md` |

## Branch Strategy Confirmation (2 of 2)

- Current branch at plan completion: `fix/quality-check-updates`.
- Planning / base branch: `fix/quality-check-updates`.
- Final merge target for completed changes: `fix/quality-check-updates`, which will be PR'd to `main` as a single bundle when the mission closes (constraint C-008).
- Branch matches target: **true**.
- Next suggested command: `/spec-kitty.tasks` to decompose this plan into work-package prompts.
