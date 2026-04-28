# Charter E2E Hardening Tranche 2 — Specification

**Mission ID**: `01KQ9NVQT8QS2QPX78YSXDQ6WN`
**Mission slug**: `charter-e2e-hardening-tranche-2-01KQ9NVQ`
**Mission type**: software-dev
**Target / merge branch**: `fix/charter-e2e-827-tranche-2`
**Created**: 2026-04-28

---

## Purpose

**TLDR**: Convert the merged Charter golden-path E2E into a strict regression gate by fixing six product gaps and removing every test bypass.

**Context**: PR #838 landed the first product-repo E2E for issue `#827` but tolerated softened checks because the public CLI still had gaps in fresh-init metadata, `charter generate`/`bundle validate` interaction, fixture synthesis, JSON stdout cleanliness, prompt-file resolution, and profile-invocation lifecycle records. Tranche 2 fixes those product gaps so the operator path works end-to-end through public commands, then strips the test's bypass helpers so a future regression in any of those areas fails the golden-path gate from a fresh project using only public CLI commands.

---

## Problem Statement

After PR #838, `tests/e2e/test_charter_epic_golden_path.py` exists in the product repo but is not yet a strict gate. It tolerates softened behavior in six places:

1. JSON parsing accepts trailing non-whitespace after the first JSON object.
2. The test hand-stamps `.kittify/metadata.yaml` with schema fields a fresh `spec-kitty init` should already provide.
3. `charter generate` and `charter bundle validate` disagree about where the generated charter must live, requiring undocumented manual `git add` choreography in the test.
4. The synthesize block falls back to `--dry-run-evidence` and hand-seeds `.kittify/doctrine/` instead of failing when fixture synthesis is broken.
5. The prompt-file assertion only validates the field if it is present, allowing `prompt_file: null` regressions to pass silently.
6. The profile-invocation assertion early-returns when `.kittify/events/profile-invocations/` is absent, so missing lifecycle records don't fail the test.

Because each bypass tolerates a real product bug (issues `#839`–`#844`), the test is not actually a regression gate yet. Operators cannot trust that "charter golden-path E2E green" means the public CLI works from a fresh project, and the next user who tries to drive Charter from an init project will hit the same gaps PR #838 papered over.

---

## Primary Scenario

**Actor**: A spec-kitty operator (human or autonomous agent) running the public CLI from a fresh project on their workstation.

**Trigger**: They want to drive a complete Charter golden path from initialization through synthesis and into the runtime mission loop using only documented public commands.

**Happy path**: They run `git init`, `spec-kitty init`, the charter interview/generate path, `charter bundle validate --json`, `charter synthesize --adapter fixture --dry-run --json`, `charter synthesize --adapter fixture --json`, the charter status/lint commands, `spec-kitty next --json` (query), `spec-kitty next --result success --json` (advance), and the retrospect summary. Every command prints exactly one well-formed JSON document on stdout when invoked with `--json`. Generated artifacts (`.kittify/metadata.yaml` schema fields, `.kittify/doctrine/`, `.kittify/events/profile-invocations/`) are created by the public commands themselves. No hidden helpers, no hand-seeded files, no out-of-band `git add` are required.

**Exception path**: If any product step regresses — for example a synthesize bug returns no manifest, `next` issues a step with `prompt_file: null`, or a `--json` command leaks SaaS sync warnings to stdout — the golden-path E2E fails loudly at that step, surfacing the offending regression instead of silently working around it.

**Rule that must always hold**: The deterministic golden-path E2E exercises every step of the operator sequence through subprocess CLI calls only, parses every `--json` stdout strictly, and asserts every artifact the public commands are supposed to produce.

---

## Domain Language

| Canonical term | Meaning in this mission | Avoid |
|---|---|---|
| Golden-path E2E | `tests/e2e/test_charter_epic_golden_path.py` — the single deterministic Charter test | "the charter test" (ambiguous), "the smoke test" |
| Operator path | Sequence of public CLI commands a user actually runs | "happy path" (generic) |
| Fresh project | A temp dir created by the existing fresh-project fixture, with `git init` and no pre-seeded `.kittify` files beyond what `spec-kitty init` produces | "clean repo" |
| Strict JSON parsing | `json.loads(stdout)` over the full stream, failing if any non-whitespace remains | "parse JSON" |
| Bypass | A test helper or conditional that tolerates a known product gap | "workaround" |
| Profile-invocation lifecycle | Paired `started`/`completed` records in `.kittify/events/profile-invocations/` for an issued action | "invocation log" |
| Issued step | A step `spec-kitty next --json` returns to the agent for execution | "next step" (overloaded) |

---

## Functional Requirements

| ID | Requirement | Status |
|---|---|---|
| FR-001 | A fresh `spec-kitty init` writes `.kittify/metadata.yaml` containing `spec_kitty.schema_version` and `spec_kitty.schema_capabilities` without any external bootstrap step. | Required |
| FR-002 | `spec-kitty charter generate --json` followed by `spec-kitty charter bundle validate --json` succeeds in a fresh git project without undocumented manual `git add` choreography; if a `git add` is required, `charter generate` emits an explicit instruction the E2E follows verbatim. | Required |
| FR-003 | `spec-kitty charter synthesize --adapter fixture --dry-run --json` returns a strict JSON envelope describing the planned synthesis, exactly one document on stdout. | Required |
| FR-004 | `spec-kitty charter synthesize --adapter fixture --json` creates `.kittify/doctrine/` and the expected synthesis manifest/provenance artifacts on disk; the operator path does not require `--dry-run-evidence` to make those artifacts appear. | Required |
| FR-005 | Every command invoked with `--json` emits exactly one JSON document on stdout; SaaS sync, auth, and background diagnostics are routed to stderr or are represented inside the JSON envelope, never appended to stdout. | Required |
| FR-006 | `spec-kitty next --json` never returns an issued step whose prompt-file field is missing, `null`, empty, or pointing at a path that does not exist; when no prompt can be resolved the bridge returns a structured blocked decision instead. | Required |
| FR-007 | When `spec-kitty next` issues or advances a composed action, `.kittify/events/profile-invocations/` exists and contains paired `started` and `completed` records whose action identity matches the issued step and whose `outcome` is in the accepted vocabulary (e.g. `done`, `failed`). | Required |
| FR-008 | The golden-path E2E exercises the full operator sequence — fresh git init, `spec-kitty init`, charter interview/generate, `charter bundle validate --json`, `charter synthesize --adapter fixture --dry-run --json`, `charter synthesize --adapter fixture --json`, charter status/lint validation, `spec-kitty next --json` query, `spec-kitty next --result success --json` advancement, and the retrospect summary — entirely through subprocess CLI calls. | Required |
| FR-009 | The golden-path E2E parses every `--json` stdout with strict full-stream `json.loads`; any first-object-only helper such as `_parse_first_json_object` is removed. | Required |
| FR-010 | The golden-path E2E asserts paired `started`/`completed` profile-invocation lifecycle records exist for every issued action in the run; absence of the directory or any required record fails the test instead of returning early. | Required |
| FR-011 | The golden-path E2E asserts every issued step's prompt-file field is present, non-empty, and resolvable on disk; conditional acceptance is removed so a `null`, empty, or dangling value fails the test. | Required |
| FR-012 | The golden-path E2E starts from the existing fresh-project fixture with `git init`, retains the source-checkout pollution guard, and fails if the run mutates any file in the source checkout. | Required |
| FR-013 | The runtime-next skill (`src/doctrine/skills/spec-kitty-runtime-next/SKILL.md`) — and any generated agent copies the project workflow expects — no longer documents a `prompt_file == null` workaround, since `#336` is verified fixed by PR `#803`. | Required |
| FR-014 | The PR opened from `fix/charter-e2e-827-tranche-2` against `Priivacy-ai/spec-kitty:main` declares which of `#839`, `#840`, `#841`, `#842`, `#843`, `#844` it closes or partially closes, mentions `#336` as a verified fixed antecedent, and includes a before/after statement on E2E strictness, the verification commands run, and any remaining `#827` follow-up scope. | Required |

---

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|---|---|---|---|
| NFR-001 | The narrow gate completes successfully on a developer workstation. | `uv run pytest tests/e2e/test_charter_epic_golden_path.py -q -s` exits 0 in ≤ 5 minutes from a clean checkout. | Required |
| NFR-002 | The targeted product gates pass. | `uv run pytest tests/e2e tests/next tests/integration/test_documentation_runtime_walk.py tests/integration/test_research_runtime_walk.py -q` exits 0; `uv run pytest tests/charter tests/specify_cli/mission_step_contracts tests/doctrine_synthesizer -q` exits 0; `uv run ruff check src tests` exits 0. | Required |
| NFR-003 | Strict typing passes on touched typed surfaces. | `uv run mypy --strict src/specify_cli src/charter src/doctrine tests/e2e/test_charter_epic_golden_path.py` exits 0. | Required |
| NFR-004 | One full golden-path run mutates zero files inside the source checkout. | The existing source-checkout pollution guard reports zero changes after a green run. | Required |
| NFR-005 | The golden-path E2E is deterministic. | 5 consecutive `uv run pytest tests/e2e/test_charter_epic_golden_path.py -q` runs all pass with no flakes on the same workstation. | Required |
| NFR-006 | New product-level regression coverage exists for each fixed gap so a regression is caught even outside the E2E. | Each of FR-001, FR-003/FR-004, FR-005, FR-006, and FR-007 has at least one targeted unit/integration test that fails when that product fix is reverted. | Required |

---

## Constraints

| ID | Constraint | Status |
|---|---|---|
| C-001 | The golden-path E2E uses public CLI commands only — no internal helpers, no hand-seeded `.kittify/` files, no manual metadata mutation. | Required |
| C-002 | The deterministic golden-path E2E does not introduce a SaaS dependency. SaaS-touching commands run only when `SPEC_KITTY_ENABLE_SAAS_SYNC=1` is explicitly set; this tranche prefers local/offline paths. | Required |
| C-003 | Issues `#845` (dossier snapshot side effects), `#846` (specify/plan auto-commit content), `#847` (decision events corrupting status reducer), and `#848` (uv.lock vs installed events pin drift) are deferred unless they block the strict gate. External `spec-kitty-end-to-end-testing` repo coverage, plain-English suite expansion, SaaS canaries, dossier ergonomics beyond the pollution guard, specify/plan auto-commit changes, and status-event reducer cleanup are out of scope. | Required |
| C-004 | The PR targets `Priivacy-ai/spec-kitty:main` from branch `fix/charter-e2e-827-tranche-2` (base `daaee895 release: 3.2.0a5 tranche 1`). | Required |
| C-005 | After PR creation, `#827` receives a comment with the PR URL and the remaining tranche recommendation; partially fixed issues receive precise remaining-scope comments; the runtime-next skill cleanup for `#336` lands in the same PR if not already complete. | Required |
| C-006 | The fresh-project fixture and source-checkout pollution guard from PR #838 are preserved and not regressed. | Required |

---

## Success Criteria

The mission is successful when all of the following are observably true:

1. The golden-path E2E fails for every PR-#838 bypass that this tranche removes — the test would catch a re-introduced regression in fresh-init schema metadata, generate↔validate disagreement, fixture synthesis, JSON stdout cleanliness, prompt-file resolution, or profile-invocation lifecycle records.
2. The golden-path E2E passes from a fresh project using only the public CLI commands listed in FR-008, with strict JSON parsing throughout and no helper-based bypasses in the test source.
3. One full golden-path run leaves the source checkout file-tree unchanged (pollution guard reports zero diffs).
4. The narrow gate, targeted product gates, ruff, and mypy strict commands listed in NFR-001 / NFR-002 / NFR-003 all exit 0 locally on the implementer's workstation.
5. The PR against `Priivacy-ai/spec-kitty:main` declares closes/partial-closes for `#839`–`#844`, mentions verified `#336`, and `#827` has been updated with the PR URL and remaining-tranche note.
6. The runtime-next skill no longer references a `prompt_file == null` workaround.

---

## Out of Scope

- External `spec-kitty-end-to-end-testing` repo coverage for the Charter epic.
- Plain-English test suite expansion.
- SaaS / tracker / sync canary tests.
- Dossier snapshot ergonomics beyond preserving the source-pollution guard (defers `#845`).
- Auto-commit behavior changes for specify/plan beyond what the golden path requires (defers `#846`).
- Status event reducer schema cleanup unless it breaks the golden path (defers `#847`).
- `uv.lock` vs installed `spec-kitty-events` pin drift in review gates (defers `#848`).

These may resurface in a later `#827` tranche.

---

## Key Entities

- **Golden-path E2E**: `/Users/robert/spec-kitty-dev/spec-kitty-20260428-103627-oSca5Q/spec-kitty/tests/e2e/test_charter_epic_golden_path.py`. The single deterministic Charter test; the gate this mission hardens.
- **Fresh project fixture**: Existing pytest fixture used by the golden-path E2E that creates a temp directory and runs `git init` before the operator-path commands.
- **`.kittify/metadata.yaml`**: Project metadata file written by `spec-kitty init`; must contain `spec_kitty.schema_version` and `spec_kitty.schema_capabilities` after init.
- **`.kittify/doctrine/`**: Directory created by `charter synthesize --adapter fixture --json`, holding the synthesis manifest and provenance artifacts.
- **`.kittify/events/profile-invocations/`**: Directory holding paired `started`/`completed` records for each issued composed action.
- **Issued step**: The structure returned by `spec-kitty next --json` describing the next runtime action, including a prompt-file field that must be present, non-empty, and resolvable.
- **Charter CLI**: `spec-kitty charter generate|bundle validate|synthesize|status|lint`, the public commands the golden path drives.
- **`spec-kitty next` CLI**: Public mission advancement loop that issues steps and writes invocation lifecycle records.
- **Runtime-next skill**: `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` and any generated agent copies; previously documented a `prompt_file == null` workaround that this mission removes.

---

## Implementation Surface (informational, not prescriptive)

The brief calls out likely product-fix areas. They are recorded here so the planning phase can scope work, but specific module choices belong in the plan, not in this spec:

- Synthesis: `src/charter/synthesizer/fixture_adapter.py`, `src/charter/synthesizer/orchestrator.py`, `src/charter/synthesizer/write_pipeline.py`, `src/charter/_doctrine_paths.py`, charter CLI command modules under `src/specify_cli` or `src/charter`.
- Prompt resolution: `src/specify_cli/next/decision.py`, `src/specify_cli/next/runtime_bridge.py`, `src/specify_cli/next/prompt_builder.py`, mission runtime YAML prompt-template handling.
- Profile-invocation lifecycle: `src/specify_cli/mission_step_contracts/executor.py`, `src/specify_cli/invocation/`, `src/specify_cli/next/runtime_bridge.py`, plus existing integration coverage around documentation/research runtime walks and composition trail records.
- JSON output discipline: shared JSON-output plumbing for charter and `next` commands.
- Init metadata: `spec-kitty init` and adjacent metadata-stamping code; existing upgrade-version tests must keep passing.
- Skill cleanup: `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` and any generated agent copies the upgrade workflow refreshes.

---

## Assumptions

- The fresh-project fixture and source-checkout pollution guard from PR #838 are still intact on `fix/charter-e2e-827-tranche-2` (verified by branch context: branch matches base PR #838 work).
- Issue `#336` remains closed as fixed by PR `#803`; any reopening would change the scope of FR-006 / FR-013.
- The implementer can run the full local verification suite (`uv run pytest -q`) on this workstation; gates listed in NFR-001/002/003 are the contract.
- "Strict JSON envelope" in FR-003 means well-formed JSON with the shape `charter synthesize --dry-run --json` already documents in product code; no new envelope schema is being introduced by this tranche beyond what existing CLI tests imply.
- The accepted profile-invocation `outcome` vocabulary (`done`, `failed`, …) is the one already used by `src/specify_cli/invocation/`; this mission does not redefine it.
- "Public CLI" means anything documented in `spec-kitty --help` and the command-template surface, excluding internal Python helpers in `src/`.

---

## Dependencies

- Tranche 1 / PR #838 has merged the initial golden-path E2E; this mission edits that file rather than creating a parallel test.
- Issue `#827` epic remains open and is the parent issue for tracking remaining tranches.
- Issues `#839`, `#840`, `#841`, `#842`, `#843`, `#844` exist and are addressable in this PR; `#336` exists and is closed.
- `Priivacy-ai/spec-kitty` GitHub repo is accessible for PR creation and issue commenting.

---

## Verification Plan (informational)

The plan phase will turn these into work-package acceptance:

1. Narrow gate: `uv run pytest tests/e2e/test_charter_epic_golden_path.py -q -s` (NFR-001).
2. Targeted gates: `uv run pytest tests/e2e tests/next tests/integration/test_documentation_runtime_walk.py tests/integration/test_research_runtime_walk.py -q`; `uv run pytest tests/charter tests/specify_cli/mission_step_contracts tests/doctrine_synthesizer -q`; `uv run ruff check src tests` (NFR-002).
3. Type strictness: `uv run mypy --strict src/specify_cli src/charter src/doctrine tests/e2e/test_charter_epic_golden_path.py` (NFR-003).
4. Pollution guard: a single golden-path run leaves the source checkout file-tree unchanged (NFR-004).
5. Determinism: 5 consecutive narrow-gate runs all pass (NFR-005).
6. Per-fix regression coverage: targeted unit/integration tests for FR-001, FR-003/FR-004, FR-005, FR-006, FR-007 (NFR-006).
7. Optional pre-PR full suite: `uv run pytest -q` (informational only).

---

## Notes

- The existing fresh-project fixture and source-checkout pollution guard are explicit "keep" items per the brief; planning should not propose alternatives that drop them.
- This is not a bulk-edit mission. No identifier or path is being renamed across many files — fixes are scoped to product code paths and a single E2E test, plus a skill doc cleanup.
- No `[NEEDS CLARIFICATION]` markers remain; all critical decisions are resolved by the brief or by stable defaults documented in Assumptions.
