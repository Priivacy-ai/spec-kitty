# Tasks: Charter E2E Hardening Tranche 2

**Mission**: `charter-e2e-hardening-tranche-2-01KQ9NVQ`
**Branch**: `fix/charter-e2e-827-tranche-2`
**Spec**: `kitty-specs/charter-e2e-hardening-tranche-2-01KQ9NVQ/spec.md`
**Plan**: `kitty-specs/charter-e2e-hardening-tranche-2-01KQ9NVQ/plan.md`

---

## Strategy

The brief is decisive: **fix the product gaps first, then strip the test bypasses**. WP01 confirms current behavior with concrete file references; WP02–WP07 land six product fixes (each with its own targeted regression test per NFR-006); WP08 strips every E2E bypass and locks the strict gate; WP09 opens the upstream PR and updates issue hygiene.

Phases:

1. **Phase 0 — Research** (WP01): answer the 7 open behavioral questions in `research.md`.
2. **Phase 1 — Product fixes** (WP02–WP07): six independent fixes, lane-parallelizable.
3. **Phase 2 — Test hardening** (WP08): strip bypasses; lock strict E2E.
4. **Phase 3 — Hygiene** (WP09): PR + issue updates.

WP01 is a hard prerequisite for WP02–WP07. WP08 depends on WP02–WP07 all being merged. WP09 depends on WP08.

---

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Investigate #840 init metadata stamping → R6 in research.md | WP01 |  | [D] |
| T002 | Investigate #841 charter generate ↔ bundle validate → R1 | WP01 | [D] |
| T003 | Investigate #839 charter synthesize fixture pipeline → R2 | WP01 | [D] |
| T004 | Investigate #842 `--json` stdout discipline → R3 | WP01 | [D] |
| T005 | Investigate #844/#336 prompt resolution in `next` → R4 | WP01 | [D] |
| T006 | Investigate #843 profile-invocation lifecycle write path → R5 | WP01 | [D] |
| T007 | Finalize research.md with file/line refs and skill-refresh path → R7 | WP01 |  | [D] |
| T008 | Stamp `spec_kitty.schema_version` and `spec_kitty.schema_capabilities` in `spec-kitty init` metadata writer (reuse existing constants) | WP02 |  | [D] |
| T009 | Add fresh-init integration test asserting fields present in `.kittify/metadata.yaml` | WP02 |  | [D] |
| T010 | Verify upgrade-version tests still pass | WP02 |  | [D] |
| T011 | Make `charter synthesize --adapter fixture --dry-run --json` emit strict envelope per `contracts/charter-synthesize-dry-run.json` | WP03 |  | [D] |
| T012 | Make `charter synthesize --adapter fixture --json` write `.kittify/doctrine/` artifacts via real write pipeline (no `--dry-run-evidence` fallback) | WP03 |  | [D] |
| T013 | Add unit/integration tests for dry-run JSON envelope shape | WP03 | [D] |
| T014 | Add integration test asserting on-disk artifacts after `--json` run | WP03 | [D] |
| T015 | Verify `tests/doctrine_synthesizer/` and `tests/charter/` still pass | WP03 |  | [D] |
| T016 | Implement #841 fix per research direction (default: `charter generate --json` emits `next_step.git_add` instruction; otherwise `bundle validate` accepts generated path) | WP04 |  | [D] |
| T017 | Add or update tests covering generate→bundle-validate operator path in a fresh git project | WP04 |  | [D] |
| T018 | Verify `tests/charter/` regression-free | WP04 |  | [D] |
| T019 | Cross-check the operator path against `kitty-specs/<mission>/quickstart.md` Step 2; update if direction differed from default | WP04 |  | [D] |
| T020 | Audit SaaS sync / auth / background diagnostic emission sites that leak into `--json` stdout | WP05 |  | [D] |
| T021 | Route diagnostics to stderr or into structured `warnings` envelope inside the JSON document | WP05 |  | [D] |
| T022 | Add per-command test asserting strict full-stream `json.loads(stdout)` for `charter generate`, `charter bundle validate`, `charter synthesize`, `next` (new file: `tests/specify_cli/test_json_output_discipline.py`) | WP05 |  | [D] |
| T023 | Verify SaaS-touching tests still pass; update assertions only where they tolerated broken behavior | WP05 |  | [D] |
| T024 | Verify `tests/charter/`, `tests/next/`, `tests/specify_cli/` regression-free | WP05 |  | [D] |
| T025 | Ensure `next --json` issued steps always carry non-empty resolvable `prompt_file` per `contracts/next-issue.json`; structured blocked decision when no prompt resolvable | WP06 |  |
| T026 | Add per-step-kind tests (discovery, research, doc, composed actions) asserting prompt-file presence/resolvability | WP06 |  |
| T027 | Edit SOURCE skill `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` to remove the `prompt_file == null` workaround text | WP06 |  |
| T028 | Run skills sync / upgrade migration locally; confirm regenerated copies under `.claude/`, `.amazonq/`, `.gemini/`, `.cursor/`, `.qwen/`, `.opencode/`, `.windsurf/`, `.kilocode/`, `.augment/`, `.roo/`, `.kiro/`, `.agent/`, `.agents/skills/` land in the diff | WP06 |  |
| T029 | Verify `tests/next/` regression-free | WP06 |  |
| T030 | Extend lifecycle writer (executor + invocation pipeline) to cover composed actions issued by `next`; emit paired `started`/`completed` records with action identity match | WP07 |  |
| T031 | Ensure `outcome` field on `completed` is in canonical vocabulary (`done`, `failed`, `skipped`, `blocked`) per `contracts/next-advance.json` | WP07 |  |
| T032 | Add integration test walking one composed action and asserting paired records exist under `.kittify/events/profile-invocations/` with matching action identity | WP07 |  |
| T033 | Verify `tests/integration/test_documentation_runtime_walk.py`, `tests/integration/test_research_runtime_walk.py`, `tests/specify_cli/mission_step_contracts/`, `tests/specify_cli/invocation/` regression-free | WP07 |  |
| T034 | Delete `_parse_first_json_object()` from `tests/e2e/test_charter_epic_golden_path.py`; switch to strict full-stream `json.loads(stdout)` for every `--json` call | WP08 |  |
| T035 | Delete `_bootstrap_schema_version()` and any direct `.kittify/metadata.yaml` mutation in the test (rely on FR-001) | WP08 |  |
| T036 | Delete synthesize fallback to `--dry-run-evidence` and hand-seeding of `.kittify/doctrine/`; require real `synthesize --json` to produce artifacts (rely on FR-003/FR-004) | WP08 |  |
| T037 | Delete conditional prompt-file acceptance; require non-empty resolvable `prompt_file` for every issued step (rely on FR-006) | WP08 |  |
| T038 | Delete profile-invocation absent-directory early return; require paired `started`/`completed` lifecycle records for every issued action (rely on FR-007) | WP08 |  |
| T039 | Keep source-checkout pollution guard, fresh-project fixture, and "every step exercised through subprocess CLI" assertions; add any new strict assertions per spec FR-008..FR-012 | WP08 |  |
| T040 | Run narrow gate, targeted gates, ruff, mypy strict, and 5-run determinism check; all must exit 0 | WP08 |  |
| T041 | Open PR from `fix/charter-e2e-827-tranche-2` against `Priivacy-ai/spec-kitty:main` declaring closes for `#839`, `#840`, `#841`, `#842`, `#843`, `#844`; verified-mention `#336` antecedent | WP09 |  |
| T042 | Comment on `#827` with PR URL and remaining-tranche recommendation | WP09 | [P] |
| T043 | Comment precisely on any partially fixed issue stating what remains | WP09 | [P] |
| T044 | Cross-check that generated agent skill copies refreshed by upgrade migration appear in PR diff (coordinate with WP06 T028 outcome) | WP09 |  |

(`[P]` indicates parallel-safe within its WP. WP-level parallelism is governed by `dependencies` and lane assignment computed by `finalize-tasks`.)

---

## Work Packages

### WP01 — Research Current Behavior

**Goal**: Answer the seven open research questions in `research.md` with concrete file/line references so each product-fix WP starts from confirmed ground truth, not hypothesis.

**Priority**: P0 — blocks WP02..WP07.

**Independent test**: Reviewer reads `research.md`; every "To verify" block is replaced with file/line refs and a confirmed Decision/Rationale/Alternatives entry.

**Included subtasks**:

- [x] T001 Investigate #840 init metadata stamping (WP01)
- [x] T002 Investigate #841 charter generate ↔ bundle validate (WP01)
- [x] T003 Investigate #839 charter synthesize fixture pipeline (WP01)
- [x] T004 Investigate #842 `--json` stdout discipline (WP01)
- [x] T005 Investigate #844/#336 prompt resolution in `next` (WP01)
- [x] T006 Investigate #843 profile-invocation lifecycle write path (WP01)
- [x] T007 Finalize research.md with file/line refs and skill-refresh path (WP01)

**Implementation sketch**: Read source files referenced in `plan.md` Phase 0 and `research.md` topics R1..R7. For each, capture concrete paths, current behavior, and decision direction with file:line citations. Escalate any deviation from the default decision direction (e.g., R1 needs *both* sides changed) before product-fix WPs commit.

**Parallel opportunities**: T002–T006 are independent investigations and can be done in any order or in parallel. T001 and T007 bookend.

**Dependencies**: none.

**Risks**: Research surfaces a deviation requiring scope split (e.g., #841 needs both generate and bundle validate changed). Mitigation: WP01 is empowered to re-split WP04 before any code lands.

**Estimated prompt size**: ~280 lines.

---

### WP02 — Fresh Init Schema Metadata (#840)

**Goal**: Make `spec-kitty init` stamp `spec_kitty.schema_version` and `spec_kitty.schema_capabilities` into `.kittify/metadata.yaml` so the E2E never needs to bootstrap them by hand.

**Priority**: P1 — required for E2E hardening (FR-001).

**Independent test**: After `spec-kitty init` in a fresh directory, both fields are present in `.kittify/metadata.yaml` with canonical values; existing upgrade-version tests still pass.

**Included subtasks**:

- [x] T008 Stamp schema_version + schema_capabilities in init metadata writer (WP02)
- [x] T009 Add fresh-init integration test asserting fields present (WP02)
- [x] T010 Verify upgrade-version tests still pass (WP02)

**Implementation sketch**: Locate canonical schema constants (per WP01 R6 — likely under `src/specify_cli/upgrade/migrations/`). Reuse them in `src/specify_cli/init/` so init writes the same values upgrade migrations would write. Do not duplicate literals.

**Dependencies**: WP01.

**Risks**: Schema constants may live in a place that creates a circular import; mitigation: extract them to a shared module if needed.

**Estimated prompt size**: ~220 lines.

---

### WP03 — Real Fixture Synthesis (#839)

**Goal**: Make `charter synthesize --adapter fixture --json` write the doctrine artifacts the operator path expects, so the E2E does not need `--dry-run-evidence` or hand-seeding.

**Priority**: P1 (FR-003, FR-004).

**Independent test**: Fresh project + `charter synthesize --adapter fixture --dry-run --json` returns strict envelope; `charter synthesize --adapter fixture --json` writes `.kittify/doctrine/manifest.yaml` and provenance artifacts on disk; no `--dry-run-evidence` is invoked.

**Included subtasks**:

- [x] T011 Make synthesize --dry-run --json emit strict envelope (WP03)
- [x] T012 Make synthesize --json write doctrine artifacts via real write pipeline (WP03)
- [x] T013 Add unit/integration tests for dry-run envelope shape (WP03)
- [x] T014 Add integration test for on-disk artifacts after --json run (WP03)
- [x] T015 Verify tests/doctrine_synthesizer/ and tests/charter/ pass (WP03)

**Implementation sketch**: Per WP01 R2, fix the gap in `src/charter/synthesizer/fixture_adapter.py` and/or `synthesize_pipeline.py` / `write_pipeline.py` so the public `--json` path produces the same artifacts the `--dry-run-evidence` debug path produces today. Cover via `tests/doctrine_synthesizer/` and a charter-CLI integration test under `tests/charter/`.

**Dependencies**: WP01.

**Risks**: Fix may require non-trivial doctrine-paths refactor (per plan risk register). If scope > "small change in fixture_adapter + write_pipeline", escalate to a follow-up tranche and keep the bypass flagged in WP08.

**Estimated prompt size**: ~360 lines.

---

### WP04 — Generate ↔ Bundle Validate Agreement (#841)

**Goal**: Make `charter generate --json` and `charter bundle validate --json` agree about where the generated charter must live and how it must be tracked, with no undocumented `git add` choreography.

**Priority**: P1 (FR-002).

**Independent test**: Fresh git project + `charter generate --json` + (optional `git add` per emitted instruction) + `charter bundle validate --json` succeeds; the test follows whatever instruction `charter generate --json` emitted, not out-of-band knowledge.

**Included subtasks**:

- [x] T016 Implement #841 fix per research direction (WP04)
- [x] T017 Add/update tests covering generate→bundle-validate operator path (WP04)
- [x] T018 Verify tests/charter/ regression-free (WP04)
- [x] T019 Cross-check operator path against quickstart.md Step 2 (WP04)

**Implementation sketch**: Default direction (per `research.md` R1): make `charter generate --json` include a `next_step.action == "git_add"` field per `contracts/charter-bundle-validate.json` when generated charter is not yet tracked. The E2E (in WP08) reads and follows this verbatim. If WP01 surfaces that `bundle validate` should accept the generated path instead, implement that direction and update the contract.

**Dependencies**: WP01.

**Risks**: If both sides need changes, split into WP04a and WP04b before lanes lock.

**Estimated prompt size**: ~300 lines.

---

### WP05 — Strict `--json` Stdout Discipline (#842)

**Goal**: Every `--json` command emits exactly one JSON document on stdout. SaaS sync / auth / background diagnostics route to stderr or into a structured `warnings` field inside the JSON envelope.

**Priority**: P1 (FR-005).

**Independent test**: New `tests/specify_cli/test_json_output_discipline.py` parses `charter generate --json`, `charter bundle validate --json`, `charter synthesize --adapter fixture --dry-run --json`, and `next --json` with strict full-stream `json.loads(stdout)` and asserts `stderr` contains only expected non-JSON diagnostics.

**Included subtasks**:

- [x] T020 Audit diagnostic emission sites that leak into --json stdout (WP05)
- [x] T021 Route diagnostics to stderr or structured warnings envelope (WP05)
- [x] T022 Add per-command strict-parse test (new file) (WP05)
- [x] T023 Verify SaaS-touching tests still pass (WP05)
- [x] T024 Verify charter/next/specify_cli test trees regression-free (WP05)

**Implementation sketch**: Per WP01 R3, identify the SaaS sync / auth emission sites (likely `src/specify_cli/saas/` or `src/specify_cli/sync/` if present, plus per-command diagnostic logging). Route via stderr or fold into envelope. Owner of shared plumbing: this WP. Per-command JSON cleanup that requires the per-command file is owned by that command's WP — coordinate via PR review.

**Dependencies**: WP01.

**Risks**: Shared plumbing change might affect SaaS-touching tests; targeted-gate coverage from NFR-002 catches this.

**Estimated prompt size**: ~340 lines.

---

### WP06 — Prompt-File Resolution in `next` + Skill Cleanup (#844 / #336)

**Goal**: `next --json` issued steps always carry a non-empty, resolvable `prompt_file`; when no prompt is resolvable, the call returns a structured blocked decision. Source skill `spec-kitty-runtime-next/SKILL.md` no longer documents a `prompt_file == null` workaround.

**Priority**: P1 (FR-006, FR-013).

**Independent test**: Per-step-kind tests (discovery, research, doc, composed) assert `prompt_file` is present, non-empty, and resolves on disk OR the response is `status: "blocked"` with a `reason`. Source skill no longer mentions the workaround. Generated agent copies are refreshed.

**Included subtasks**:

- [ ] T025 Ensure next --json issued steps carry non-empty resolvable prompt_file (WP06)
- [ ] T026 Add per-step-kind tests for prompt-file presence/resolvability (WP06)
- [ ] T027 Edit SOURCE skill to remove prompt_file == null workaround (WP06)
- [ ] T028 Run skills sync / upgrade migration; confirm regenerated copies in diff (WP06)
- [ ] T029 Verify tests/next/ regression-free (WP06)

**Implementation sketch**: Per WP01 R4, in `src/specify_cli/next/runtime_bridge.py` / `decision.py` / `prompt_builder.py`, ensure prompt resolution always returns a resolvable path or a structured blocked decision. Per CLAUDE.md "Template Source Location" rule, edit only `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md`; refresh agent copies via the established upgrade migration.

**Dependencies**: WP01.

**Risks**: If a step kind legitimately has no prompt template today, the fix changes its behavior. Mitigation: confirm via WP01 R4 whether any step kind needs a new prompt template added.

**Estimated prompt size**: ~360 lines.

---

### WP07 — Profile-Invocation Lifecycle (#843)

**Goal**: When `next` issues or advances a composed action, paired `started` and `completed` lifecycle records are written under `.kittify/events/profile-invocations/` with action identity matching the issued step and `outcome` in the canonical vocabulary.

**Priority**: P1 (FR-007).

**Independent test**: Integration test walks one composed action via `next --json` + `next --result success --json` and asserts paired records exist with matching action identity and `outcome == "done"`.

**Included subtasks**:

- [ ] T030 Extend lifecycle writer to cover composed actions (WP07)
- [ ] T031 Ensure outcome field uses canonical vocabulary (WP07)
- [ ] T032 Add integration test asserting paired records (WP07)
- [ ] T033 Verify documentation/research runtime walks regression-free (WP07)

**Implementation sketch**: Per WP01 R5, extend `src/specify_cli/mission_step_contracts/executor.py` and/or `src/specify_cli/invocation/writer.py` so composed actions issued by `next` go through the same lifecycle-write path that WP-bound actions use today. Match the existing record schema in `src/specify_cli/invocation/record.py`; do not redefine.

**Dependencies**: WP01.

**Risks**: Changing the lifecycle write path could affect status-event reducer input (issue #847 deferred). Targeted gates around `tests/specify_cli/mission_step_contracts/` catch reducer regressions.

**Estimated prompt size**: ~320 lines.

---

### WP08 — E2E Test Hardening (Strip All Bypasses)

**Goal**: Strip every PR-#838 bypass from `tests/e2e/test_charter_epic_golden_path.py`. The strict gate fails for every regression in WP02–WP07.

**Priority**: P0 — the mission's core deliverable (FR-008 through FR-012).

**Independent test**: All WP02–WP07 product fixes are merged. The strict E2E (1) parses every `--json` stdout with `json.loads(stdout)`; (2) does not stamp metadata; (3) does not seed doctrine; (4) does not fall back to `--dry-run-evidence`; (5) requires non-empty resolvable `prompt_file`; (6) requires paired lifecycle records. NFR-001..006 all pass.

**Included subtasks**:

- [ ] T034 Delete _parse_first_json_object; use full-stream json.loads (WP08)
- [ ] T035 Delete _bootstrap_schema_version and metadata mutation (WP08)
- [ ] T036 Delete --dry-run-evidence fallback and hand-seeding of doctrine (WP08)
- [ ] T037 Delete conditional prompt-file acceptance; require resolvable prompt_file (WP08)
- [ ] T038 Delete profile-invocation early return; require paired lifecycle records (WP08)
- [ ] T039 Keep pollution guard, fresh-project fixture, subprocess CLI assertions; add new strict assertions per FR-008..012 (WP08)
- [ ] T040 Run narrow gate, targeted gates, ruff, mypy strict, 5-run determinism (WP08)

**Implementation sketch**: Edit `tests/e2e/test_charter_epic_golden_path.py` only (single-file footprint). Remove the six bypass blocks listed in the spec's "Current Test Seams To Tighten" section. Use the operator sequence from `quickstart.md` as the source of truth. Keep all "Keep" items (pollution guard, fresh-project fixture, subprocess CLI) and add the strict assertions enumerated in FR-008..012.

**Dependencies**: WP02, WP03, WP04, WP05, WP06, WP07.

**Risks**: Strict E2E may exceed the 5-minute budget; if it does, profile and parallelize fixture setup or document the runtime increase.

**Estimated prompt size**: ~480 lines.

---

### WP09 — PR Creation & Issue Hygiene

**Goal**: Open the upstream PR with proper closes/partial-closes; update `#827` epic; comment on partially fixed issues with what remains; ensure regenerated skill copies appear in the PR diff.

**Priority**: P1 — required for the mission's GitHub-side deliverable (FR-014, C-005).

**Independent test**: PR exists at `Priivacy-ai/spec-kitty` from `fix/charter-e2e-827-tranche-2` to `main` with title, summary, before/after E2E strictness statement, declared closes for `#839`–`#844`, mention of `#336`, verification commands and results, and remaining `#827` follow-up scope. `#827` has a comment with the PR URL.

**Included subtasks**:

- [ ] T041 Open PR with proper closes/partial-closes and verification log (WP09)
- [ ] T042 Comment on #827 with PR URL and remaining-tranche recommendation (WP09)
- [ ] T043 Comment precisely on any partially fixed issue (WP09)
- [ ] T044 Cross-check skill copy refresh appears in PR diff (WP09)

**Implementation sketch**: Use `gh pr create` with HEREDOC body following the spec's "PR Expectations" section. Use `gh issue comment` for `#827` and any partial-close issues. Confirm WP06 T028 already landed the regenerated agent-copy diff.

**Dependencies**: WP08.

**Risks**: GitHub auth scopes — if `gh` fails with limited token scopes per CLAUDE.md, unset `GITHUB_TOKEN` and use keyring auth.

**Estimated prompt size**: ~250 lines.

---

## Dependency Graph

```
WP01 (Research)
  ├── WP02 (#840 init schema)         ─┐
  ├── WP03 (#839 synthesize)           │
  ├── WP04 (#841 generate↔validate)    ├── WP08 (E2E hardening) ── WP09 (PR/hygiene)
  ├── WP05 (#842 strict JSON)          │
  ├── WP06 (#844 prompt-file + skill)  │
  └── WP07 (#843 lifecycle)           ─┘
```

WP02–WP07 may run in parallel lanes once WP01 is approved. Lane assignment is computed by `finalize-tasks` from the `owned_files` declarations.

---

## Parallelization Highlights

- **WP02–WP07** are six independent product fixes that can land in parallel lanes once WP01 ships. The plan's owned-files declarations ensure no two WPs touch the same file.
- **WP08** is a single-file edit (the E2E test) that depends on all six product fixes — naturally serialized at the end.
- **WP09** is a GitHub-only WP that depends on WP08 — final step.

## MVP Recommendation

**WP01 + WP08** is not a viable MVP — without WP02–WP07, the strict E2E would fail on bypassed product gaps. The minimum viable shippable scope is **WP01 → WP02..WP07 (all six) → WP08 → WP09**. Cutting any product-fix WP forces keeping its corresponding bypass in the test, which violates the success criterion.

If scope must be cut, the only safe move is to defer one product fix (e.g., WP05 strict JSON discipline if SaaS audit balloons) plus *its* bypass, document the deferral in the PR description, and file a follow-up tranche issue. This requires explicit operator approval before WP08 starts.

---

## Verification (mirrors NFR-001..006)

- Narrow gate: `uv run pytest tests/e2e/test_charter_epic_golden_path.py -q -s`
- Targeted gates: `uv run pytest tests/e2e tests/next tests/integration/test_documentation_runtime_walk.py tests/integration/test_research_runtime_walk.py -q`; `uv run pytest tests/charter tests/specify_cli/mission_step_contracts tests/doctrine_synthesizer -q`; `uv run ruff check src tests`
- Strict typing: `uv run mypy --strict src/specify_cli src/charter src/doctrine tests/e2e/test_charter_epic_golden_path.py`
- Pollution guard: zero source-checkout diffs after one full run
- Determinism: 5 consecutive narrow-gate runs all green
