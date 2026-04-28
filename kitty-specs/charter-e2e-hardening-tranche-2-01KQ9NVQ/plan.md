# Implementation Plan: Charter E2E Hardening Tranche 2

**Branch**: `fix/charter-e2e-827-tranche-2`
**Date**: 2026-04-28
**Mission**: `charter-e2e-hardening-tranche-2-01KQ9NVQ` (mission_id `01KQ9NVQT8QS2QPX78YSXDQ6WN`)
**Spec**: `/Users/robert/spec-kitty-dev/spec-kitty-20260428-103627-oSca5Q/spec-kitty/kitty-specs/charter-e2e-hardening-tranche-2-01KQ9NVQ/spec.md`
**Branch contract**: Current = `fix/charter-e2e-827-tranche-2`; Planning base = `fix/charter-e2e-827-tranche-2`; Merge target = `fix/charter-e2e-827-tranche-2`. `branch_matches_target = true`. The eventual upstream PR target (`Priivacy-ai/spec-kitty:main` from base `daaee895`) is downstream of this mission and out of the runtime merge contract.

---

## Summary

Convert the merged Charter golden-path E2E (`tests/e2e/test_charter_epic_golden_path.py`, landed in PR #838) from a diagnostic spine into a strict regression gate. Six product gaps (#839 fresh-init schema metadata, #840 generate↔validate disagreement, #841 same — confirm split with #840, #842 SaaS noise on `--json` stdout, #843 missing profile-invocation lifecycle, #844 nullable `prompt_file`) are fixed in the public CLI with targeted regression tests for each fix, then the E2E's six bypass helpers and conditionals are stripped in a final test-hardening WP. The runtime-next skill's `prompt_file == null` workaround is removed in the same PR (verifies #336 fix from PR #803).

**Approach** (single-line per fix):

- **#840 fresh init schema** → stamp `spec_kitty.schema_version` and `spec_kitty.schema_capabilities` in `spec-kitty init`'s metadata writer; cover with a fresh-init integration test.
- **#841 generate↔validate** → research first; then either make `charter generate` print an explicit `git add` instruction (and follow it from the E2E) or relax `charter bundle validate` to accept the generated path. Pick the option research surfaces as least-disruptive to merged invariants.
- **#839 fixture synthesis** → make `charter synthesize --adapter fixture --dry-run --json` and `--json` succeed end-to-end so `.kittify/doctrine/` and synthesis manifest/provenance artifacts land on disk without `--dry-run-evidence`.
- **#842 strict JSON** → audit `--json` paths used by the E2E (`charter generate`, `charter bundle validate`, `charter synthesize`, `next`) and route SaaS sync/auth diagnostics to stderr or into the JSON envelope; add per-command tests asserting strict full-stream parsing.
- **#844 / #336 prompt_file** → ensure `next --json` issued steps always carry a non-empty, resolvable `prompt_file`; when no prompt is resolvable, return a structured blocked decision. Remove the workaround text from `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` and refresh generated agent copies via the established upgrade migration path.
- **#843 profile-invocation lifecycle** → ensure issuing/advancing a composed action via `next` writes paired `started` and `completed` records in `.kittify/events/profile-invocations/` with action identity matching the issued step and `outcome` in the accepted vocabulary.
- **Test hardening (final)** → delete `_parse_first_json_object`, `_bootstrap_schema_version`, the synthesize fallback to `--dry-run-evidence`, the doctrine hand-seeding, the prompt-file conditional, and the profile-invocation early-return; require strict full-stream `json.loads` and resolvable prompt files everywhere; assert paired lifecycle records.

---

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty CLI codebase)
**Primary Dependencies**: typer (CLI), rich (console), ruamel.yaml (YAML/frontmatter), pytest (testing). No new dependencies introduced.
**Storage**: Filesystem only — `.kittify/metadata.yaml`, `.kittify/doctrine/`, `.kittify/events/profile-invocations/`, `kitty-specs/<mission>/...`. No new data stores.
**Testing**: pytest with 90%+ coverage on new code. Integration tests for CLI commands invoke them as subprocesses. The narrow gate is `tests/e2e/test_charter_epic_golden_path.py`; targeted gates listed in NFR-002.
**Target Platform**: Developer workstation; spec-kitty CLI as installed package or `uv run`. Python 3.11+. macOS / Linux.
**Project Type**: single (single-package Python CLI repo).
**Performance Goals**: Narrow gate completes in ≤ 5 minutes (NFR-001). Full E2E run mutates 0 source-checkout files (NFR-004). 5-run determinism (NFR-005). No new performance constraints introduced.
**Constraints**: `mypy --strict` must pass on `src/specify_cli`, `src/charter`, `src/doctrine`, `tests/e2e/test_charter_epic_golden_path.py`. `ruff check src tests` must pass. No SaaS dependency in deterministic E2E; SaaS-touching commands gated behind `SPEC_KITTY_ENABLE_SAAS_SYNC=1`.
**Scale/Scope**: One E2E file hardened. Six product fixes across the modules below. One skill doc cleanup. Per-fix regression tests added (≈ 6 new test files / blocks).

### Module surface (informational)

- `src/specify_cli/` — init metadata, next decision/runtime_bridge/prompt_builder, invocation, mission_step_contracts/executor, JSON output plumbing.
- `src/charter/` — synthesizer (fixture_adapter, orchestrator, write_pipeline), `_doctrine_paths.py`, charter CLI command modules, generate/bundle-validate plumbing.
- `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` — source skill (workaround removal). Generated agent copies refreshed via the established migration path (per CLAUDE.md "Template Source Location" rules — edit SOURCE only).
- `tests/e2e/test_charter_epic_golden_path.py` — single E2E file hardened.
- `tests/charter/`, `tests/specify_cli/`, `tests/specify_cli/next/`, `tests/specify_cli/invocation/`, `tests/specify_cli/mission_step_contracts/`, `tests/doctrine_synthesizer/`, `tests/integration/` — per-fix regression test homes (existing convention).

---

## Charter Check

**GATE**: Must pass before Phase 0 research. Re-check after Phase 1 design.

Charter exists at `.kittify/charter/charter.md`. The action-doctrine policy summary (loaded via `charter context --action plan`) mandates:

| Charter rule | Status in this plan |
|---|---|
| Python 3.11+, typer, rich, ruamel.yaml, pytest, mypy --strict | ✓ — no deviation; all fixes use existing tooling |
| 90%+ test coverage on new code | ✓ — NFR-006 makes per-fix targeted tests mandatory |
| `mypy --strict` must pass | ✓ — NFR-003 enforces this on touched typed surfaces |
| Integration tests for CLI commands | ✓ — narrow gate + targeted gates exercise CLI via subprocess |
| DIRECTIVE_003 (Decision Documentation) | ✓ — research.md captures the #841 fix-direction decision |
| DIRECTIVE_010 (Specification Fidelity) | ✓ — implementation will trace to FR-IDs in the spec; tasks-finalize will require WP→FR linkage |

No charter conflicts. **GATE: PASS** (will re-check after Phase 1).

---

## Project Structure

### Documentation (this feature)

```
kitty-specs/charter-e2e-hardening-tranche-2-01KQ9NVQ/
├── plan.md                      # This file
├── research.md                  # Phase 0 output (this command)
├── data-model.md                # Phase 1 output (this command) — minimal: no new entities
├── quickstart.md                # Phase 1 output (this command) — operator-path walk
├── contracts/                   # Phase 1 output (this command) — JSON envelope shapes
│   ├── charter-synthesize-dry-run.json
│   ├── charter-synthesize.json
│   ├── charter-bundle-validate.json
│   ├── next-issue.json
│   └── next-advance.json
├── spec.md                      # /spec-kitty.specify output (already written)
├── meta.json                    # mission identity (already written)
├── checklists/
│   └── requirements.md          # spec quality checklist (already written)
├── status.events.jsonl          # status event log (managed by runtime)
└── tasks/                       # /spec-kitty.tasks output (next phase)
```

### Source structure (no change)

This mission edits within the existing single-package layout:

```
src/specify_cli/
src/charter/
src/doctrine/skills/spec-kitty-runtime-next/SKILL.md
tests/e2e/test_charter_epic_golden_path.py
tests/{charter,specify_cli,specify_cli/next,specify_cli/invocation,
       specify_cli/mission_step_contracts,doctrine_synthesizer,integration}/
```

No new directories, no module moves, no public-API additions beyond existing CLI surfaces.

---

## Phase 0: Outline & Research

The unknowns in this plan are not language/framework choices — those are fixed by the charter. They are product-specific behavioral questions whose current state must be confirmed before fixes are committed to a direction. Research consolidates findings in `research.md` (this file's sibling). Topics:

1. **Current `charter generate` output and tracking expectations** — does it emit instructions today? where does it write the charter? what does `bundle validate` look for? (drives #841 fix direction)
2. **Current `charter synthesize` adapter contract and write pipeline** — what does `--dry-run --json` currently emit? what does `--json` write to disk? what is the `--dry-run-evidence` fallback the E2E uses today and why does it diverge from `--json`? (drives #839 fix scope)
3. **`--json` stdout discipline today** — which commands currently leak SaaS sync warnings to stdout, and is the leak in shared plumbing or per-command? (drives #842 single-vs-many fix)
4. **Prompt resolution in `next`** — how does `runtime_bridge.py` decide a step's `prompt_file`? what step shapes today return null or missing? what does `prompt_builder.py` do for composed actions? (drives #844 / #336 surface)
5. **Profile-invocation lifecycle write path** — where does `mission_step_contracts/executor.py` and `specify_cli/invocation/` decide whether to write `started`/`completed` records? for which step kinds is the path skipped today? (drives #843 fix)
6. **Init metadata stamping** — where does `spec-kitty init` write `.kittify/metadata.yaml`? where does upgrade-version logic stamp schema fields? what set of schema_capabilities is canonical today? (drives #840 fix)
7. **Skill copy refresh path** — confirm which migration refreshes `.claude/`/`.amazonq/`/etc. copies of `spec-kitty-runtime-next/SKILL.md` and how to trigger it (drives #336 cleanup completeness)

These are the seven research questions in `research.md`. Each must be answered with concrete file/line references and a Decision/Rationale/Alternatives block before Phase 1 contracts are locked.

**Output**: `research.md` (created alongside this plan; will be filled with current-behavior findings during the research WP unless answers are evident at task-generation time).

---

## Phase 1: Design & Contracts

**Prerequisites**: research.md complete (or research delegated to a research WP that runs before product-fix WPs).

### Data model

Negligible. This mission introduces no new entities. The Key Entities listed in `spec.md` (golden-path E2E test, fresh-project fixture, `.kittify/metadata.yaml`, `.kittify/doctrine/`, `.kittify/events/profile-invocations/`, issued step, charter CLI, runtime-next skill) all exist and are not redefined here. `data-model.md` records this explicitly so reviewers can confirm there is no schema work hidden in this tranche.

### Contracts (JSON envelopes locked by this tranche)

Each contract file describes the strict shape the public CLI must honor after this mission. The E2E and per-fix regression tests parse against these shapes. The contracts are not new APIs — they document and lock current public-CLI behavior so future regressions are catchable. Files:

- `contracts/charter-synthesize-dry-run.json` — the strict envelope `charter synthesize --adapter fixture --dry-run --json` must emit (FR-003).
- `contracts/charter-synthesize.json` — the strict envelope `charter synthesize --adapter fixture --json` must emit, plus listed on-disk artifacts under `.kittify/doctrine/` (FR-004).
- `contracts/charter-bundle-validate.json` — the strict envelope `charter bundle validate --json` must emit; if a tracking-instruction is required by `charter generate`, that instruction's shape is captured here too (FR-002).
- `contracts/next-issue.json` — the strict envelope `spec-kitty next --json` must emit when issuing a step, including the `prompt_file` field and acceptable `blocked` shape (FR-006).
- `contracts/next-advance.json` — the strict envelope `spec-kitty next --result success --json` must emit and the lifecycle records that must appear under `.kittify/events/profile-invocations/` after the call (FR-007).

### Quickstart

`quickstart.md` walks the deterministic operator path the E2E exercises (FR-008). It is also what the PR description references and what `#827` will get linked to. The quickstart steps mirror the `Verification Plan` in spec.md.

### Charter Check (post-design)

Re-evaluating after Phase 1: contracts and data-model.md introduce no new dependencies, no new test framework, no implementation-detail leakage into spec/data-model.md, and respect mypy strict (Python type stubs in tests use existing patterns). **GATE: PASS** (post-design).

---

## Sequencing Strategy

The brief is decisive: "fix the product gaps and **then** remove the test bypasses." This translates into the following WP ordering, which `/spec-kitty.tasks` will materialize:

1. **WP01 Research** (single research WP) — answer the seven Phase 0 research questions; output `research.md` populated with file/line references and Decision/Rationale/Alternatives blocks. Required before any product-fix WP commits to a direction.
2. **WP02–WP07 Product fixes (parallelizable in lanes)**:
   - WP02 — `#840` fresh init schema metadata + integration test
   - WP03 — `#839` real fixture synthesis (dry-run JSON + write pipeline) + tests
   - WP04 — `#841` generate↔validate agreement (direction picked from research) + tests
   - WP05 — `#842` strict `--json` stdout discipline + per-command tests
   - WP06 — `#844` / `#336` prompt-file resolution in `next` + tests + skill source cleanup
   - WP07 — `#843` paired profile-invocation lifecycle records + integration test
3. **WP08 Test hardening (final)** — strip all six bypasses from `tests/e2e/test_charter_epic_golden_path.py`; add strict full-stream parsing helper; assert paired lifecycle records, resolvable prompts, real synthesize artifacts; remove `_parse_first_json_object`, `_bootstrap_schema_version`, doctrine hand-seeding, fallback `--dry-run-evidence`, prompt-file conditional, profile-invocation early-return.
4. **WP09 PR / issue hygiene** — open PR against `Priivacy-ai/spec-kitty:main`; declare closes/partial-closes for `#839`–`#844`; verify-mention `#336`; comment on `#827` with PR URL and remaining-tranche note; ensure generated agent copies of the runtime-next skill are refreshed by upgrade migration if the repo workflow demands it.

The `/spec-kitty.tasks` step will compute lanes; based on shared file footprints, WP02 (init), WP05 (JSON plumbing), and WP06 (next/prompts) likely share a lane via touched modules in `src/specify_cli/`, while WP03/WP04 (charter) share another lane, and WP07 (invocation) probably shares with WP06. WP01 and WP08 are sequential bookends.

---

## Risks and Premortem

Following the `premortem-risk-identification` tactic from charter doctrine:

| Risk | How it would manifest | Mitigation |
|---|---|---|
| #841 research surfaces that *both* generate and validate need changes, not one or the other | A single direction picked in WP04 leaves the strict E2E flapping between merged states | Research WP must produce a binary directional decision; if both sides need changes, split WP04 into 04a/04b before lanes are locked |
| Fixture synthesis fix (#839) requires a non-trivial doctrine paths refactor | WP03 balloons in scope, blocking WP08 | Time-box WP03 research; if scope > "small change in fixture_adapter + write_pipeline", escalate as a follow-up tranche and keep the test bypass for that one path only with an explicit issue link |
| `--json` stdout discipline fix (#842) breaks SaaS-touching CLI tests that *expect* warnings on stdout | Targeted gates regress | Audit `tests/specify_cli/saas/` (or equivalent) before fix; route to stderr explicitly; update assertions only where they were tolerating broken behavior |
| Removing the runtime-next skill workaround drifts from generated agent copies that haven't been migrated | New projects ship the workaround until they upgrade | Run the established upgrade migration locally as part of WP06; verify regenerated copies under `.claude/`, `.amazonq/`, etc. land in the diff |
| Profile-invocation lifecycle fix changes event-log semantics expected by status reducer | `tests/specify_cli/mission_step_contracts/`, `tests/integration/test_documentation_runtime_walk.py`, `tests/integration/test_research_runtime_walk.py` regress | Targeted gates list explicitly includes those files; WP07 must run them before signaling done |
| Strict E2E becomes flaky on slow workstations (NFR-001 ≤ 5 min) | Determinism gate (NFR-005) flaps | Profile narrow-gate runtime in WP08; if it exceeds budget, identify the slowest CLI subprocess and either parallelize fixture setup or document expected runtime |
| Source-checkout pollution guard regresses while editing the E2E | NFR-004 fails | WP08 must keep the existing pollution-guard assertion as an explicit "do not delete" item; the WP review checklist requires confirming guard presence |

---

## Out of Scope (recap)

Already enumerated in `spec.md` Out of Scope section. Issues #845–#848 are deferred. External `spec-kitty-end-to-end-testing` repo coverage, plain-English suite expansion, SaaS canaries, dossier ergonomics beyond the pollution guard, specify/plan auto-commit changes, and status-event reducer cleanup are out of scope unless they break the golden path.

---

## Verification (mirrors NFR-001..006)

- Narrow gate: `uv run pytest tests/e2e/test_charter_epic_golden_path.py -q -s`
- Targeted gates: `uv run pytest tests/e2e tests/next tests/integration/test_documentation_runtime_walk.py tests/integration/test_research_runtime_walk.py -q`; `uv run pytest tests/charter tests/specify_cli/mission_step_contracts tests/doctrine_synthesizer -q`; `uv run ruff check src tests`
- Type strictness: `uv run mypy --strict src/specify_cli src/charter src/doctrine tests/e2e/test_charter_epic_golden_path.py`
- Pollution guard: zero source-checkout diffs after one full run
- Determinism: 5 consecutive narrow-gate runs all green
- Optional pre-PR: `uv run pytest -q`

---

## Final Branch Contract Restatement

- **Current branch**: `fix/charter-e2e-827-tranche-2`
- **Mission planning/base branch**: `fix/charter-e2e-827-tranche-2`
- **Mission merge target**: `fix/charter-e2e-827-tranche-2` (matches current — this branch is both the work surface and the mission merge sink)
- **Eventual upstream PR**: from `fix/charter-e2e-827-tranche-2` against `Priivacy-ai/spec-kitty:main` (base `daaee895 release: 3.2.0a5 tranche 1`); that PR is created in WP09 after the mission merges.

---

## Next command

`/spec-kitty.tasks` — break this plan into work packages WP01..WP09 per the sequencing above. Do **not** start implementation until tasks are finalized and lanes are computed.
