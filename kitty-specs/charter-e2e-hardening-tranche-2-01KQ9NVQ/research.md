# Research: Charter E2E Hardening Tranche 2

**Mission**: `charter-e2e-hardening-tranche-2-01KQ9NVQ`
**Date**: 2026-04-28
**Status**: Open — answers below are **plan-time hypotheses** based on the brief and CLAUDE.md context. Each unknown will be re-confirmed against the current code by the WP01 research work package before the corresponding fix WP locks a direction. Where the brief gives a definitive answer, that is recorded as **Confirmed**; where the answer needs codebase reading, it is marked **To verify**.

This document follows the format from the plan command: each topic has a Decision (or hypothesis), Rationale, and Alternatives considered.

---

## R1 — `charter generate` output and tracking expectations (drives #841)

**Question**: Where does `spec-kitty charter generate` write the charter today, what does `charter bundle validate` expect to find, and why does the E2E need undocumented `git add` choreography between the two?

**Hypothesis (To verify)**: `charter generate` writes `charter.md` to a path inside the project tree that `bundle validate` looks for via the git index rather than the working tree, so a freshly generated (and unstaged) charter is invisible to validation. The test in PR #838 worked around this by adding the file manually.

**Decision direction (preferred)**: Have `charter generate --json` print an explicit, machine-readable instruction (e.g., `"next_step": {"git_add": ["charter.md"]}` field in the JSON envelope) when the generated file is not yet tracked, *and* update the E2E to follow that instruction verbatim. This preserves whatever invariant `bundle validate` relies on (likely "validate what is committable, not what happens to be in the working tree") while making the operator path documented and self-describing.

**Rationale**: The brief explicitly allows this option ("emit a clear instruction that the E2E follows explicitly"). It avoids loosening `bundle validate`'s tracked-charter invariant, which may be load-bearing for downstream consumers. It also gives non-test operators clear guidance.

**Alternatives considered**:
- **Make `charter generate` auto-stage the file**: Couples a "generate" command to git mutation, which is surprising and likely violates the same auto-commit hygiene principle that issue #846 raises.
- **Make `bundle validate` accept untracked working-tree files**: Loosens invariant for everyone to fix one test path; risks changing semantics for SaaS sync and CI consumers.
- **Status quo plus document the manual `git add`**: Documents broken behavior as a feature; rejected by FR-002 as written.

**Files to read in WP01**: `src/charter/cli/generate.py` (or equivalent), `src/charter/cli/bundle_validate.py`, `src/charter/_doctrine_paths.py`, `tests/charter/`. **To verify**: actual file paths.

---

## R2 — `charter synthesize` adapter contract and write pipeline (drives #839)

**Question**: What does `synthesize --adapter fixture --dry-run --json` emit today, what does `--json` write to disk, and why does the E2E fall back to `--dry-run-evidence` plus hand-seeding `.kittify/doctrine/`?

**Hypothesis (To verify)**: The fixture adapter's `--dry-run` JSON envelope is correct but the non-dry-run `--json` path does not actually write the doctrine artifacts the E2E expects (or it errors before writing). `--dry-run-evidence` may be a different code path that produces the artifacts but bypasses the orchestrator's write pipeline, so the test uses it to seed enough state to keep going.

**Decision direction**: Make the real `synthesize --adapter fixture --json` path write `.kittify/doctrine/` and the synthesis manifest/provenance artifacts. Drop the `--dry-run-evidence` fallback from the E2E entirely. If the existing fixture adapter does not yet produce an end-to-end synthesis, complete the write pipeline so a fixture run produces the same artifact tree a real adapter would.

**Rationale**: FR-004 requires the public command to create the artifacts on disk; the test must not seed them. The `--dry-run-evidence` path appears to be either a debug affordance or a vestigial half-implementation; it is not the operator path.

**Alternatives considered**:
- **Promote `--dry-run-evidence` to first-class and have the E2E call it**: Codifies a "fake" path as the public path; rejected.
- **Skip fixture synthesis in the E2E and only test dry-run**: Loses coverage of the write pipeline, which is what users actually exercise; rejected.

**Files to read in WP01**: `src/charter/synthesizer/fixture_adapter.py`, `src/charter/synthesizer/orchestrator.py`, `src/charter/synthesizer/write_pipeline.py`, `src/charter/_doctrine_paths.py`, `tests/doctrine_synthesizer/`. Confirm actual symbol names.

---

## R3 — `--json` stdout discipline (drives #842)

**Question**: Which CLI commands currently leak SaaS sync / auth diagnostic warnings into `--json` stdout, and is the leak in shared output plumbing or per-command?

**Hypothesis (To verify)**: A shared "before-emit" hook (likely in a CLI base or a `--json` decorator) prints SaaS sync errors to stdout because the underlying SaaS client logs to the same stream the JSON serializer uses. Per-command leaks may also exist where commands print warnings before flipping into JSON-emit mode.

**Decision direction**: Audit the four `--json` paths the E2E touches (`charter generate`, `charter bundle validate`, `charter synthesize`, `next`). Route SaaS sync / auth / background-tracker diagnostics to stderr or to a structured `warnings` field inside the JSON envelope. Add per-command tests asserting that strict full-stream `json.loads(stdout)` succeeds and that `stderr` is either empty or contains only expected non-JSON diagnostics.

**Rationale**: FR-005 requires exactly one JSON document on stdout; the cleanest fix is at the source (the diagnostic emission path), not at parse time in the test. Targeting all four touched commands ensures the strict E2E will not flap on a fifth command discovered later.

**Alternatives considered**:
- **Wrap each `--json` invocation in the test with a "tolerate trailing junk" parser**: Defeats the purpose of FR-005; rejected.
- **Suppress all SaaS diagnostics under `--json`**: Hides legitimate failure signals; rejected. Routing to stderr or envelope preserves them.

**Files to read in WP01**: shared JSON-output helpers under `src/specify_cli/`; SaaS sync emission sites (likely in tracker / events client modules). **To verify**.

---

## R4 — Prompt resolution in `next` (drives #844 / #336)

**Question**: How does `next --json` decide a step's `prompt_file`? Why did `#336` produce `prompt_file: null` for discovery? PR `#803` claims fixed; what does the fix look like and is it covered by tests?

**Hypothesis (To verify)**: `runtime_bridge.py` resolves the prompt by looking up `prompt_template` in a runtime YAML or step definition, then passes the resolved path through `prompt_builder.py`. The `#336` bug returned null when the discovery step's runtime YAML had no `prompt_template` key; PR `#803` likely added a fallback that resolves a default per step kind or returns a structured blocked decision.

**Decision direction**: Confirm that issued steps from `next --json` always carry a non-empty, on-disk-resolvable `prompt_file`. Where no prompt is resolvable, return a structured blocked decision (status `blocked`, reason text) rather than a partial issued step with `prompt_file: null` or empty. Lock this with per-step-kind tests (discovery, research, documentation, composed actions). Remove the workaround text from the runtime-next SOURCE skill (`src/doctrine/skills/spec-kitty-runtime-next/SKILL.md`) and refresh agent copies via the established upgrade migration path.

**Rationale**: FR-006 + FR-013. The brief explicitly says `#336` is fixed and asks the E2E to lock the behavior — which means the test must be willing to fail if a regression returns `null`.

**Alternatives considered**:
- **Allow `prompt_file: null` for "informational" steps and adapt the E2E**: Conflates step kinds; rejected because there is no documented public step kind that legitimately carries no prompt.
- **Resolve a generic placeholder prompt on the fly**: Hides missing prompt-template definitions; rejected.

**Files to read in WP01**: `src/specify_cli/next/decision.py`, `src/specify_cli/next/runtime_bridge.py`, `src/specify_cli/next/prompt_builder.py`, mission runtime YAML prompt-template definitions, PR `#803` diff for context, `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` for current workaround text.

---

## R5 — Profile-invocation lifecycle write path (drives #843)

**Question**: Where in the runtime is `.kittify/events/profile-invocations/` populated? For which step kinds is the path skipped today, and why?

**Hypothesis (To verify)**: `mission_step_contracts/executor.py` (or `specify_cli/invocation/`) writes `started` and `completed` records around the agent invocation for some step kinds (e.g., implement/review work-package actions) but is bypassed for composed actions issued by `next` outside the implement-review loop. The early-return in PR #838's E2E exists precisely because the directory is empty for the discovery/charter steps the test exercises.

**Decision direction**: Extend the lifecycle writer to cover composed actions issued by `next`. The pair (`started`, `completed`) is written even when the action is a charter-flow step or a discovery step, with action identity matching the issued step's `action`/`step_id` and `outcome` in the canonical vocabulary (`done`, `failed`, …). Add an integration test that walks one composed action and asserts the paired records exist.

**Rationale**: FR-007 + NFR-006 require the directory to exist and contain paired records for issued actions. This makes the runtime observable for any step kind, not just WP-bound ones.

**Alternatives considered**:
- **Move the lifecycle-write call into a `next`-side wrapper**: Spreads the responsibility; rejected because executor is the canonical write site.
- **Make the directory optional and document its WP-only scope**: Defeats FR-010; rejected.

**Files to read in WP01**: `src/specify_cli/mission_step_contracts/executor.py`, `src/specify_cli/invocation/` package, `src/specify_cli/next/runtime_bridge.py`, existing `tests/integration/test_documentation_runtime_walk.py` and `tests/integration/test_research_runtime_walk.py` for the pattern of asserting trail records.

---

## R6 — Init metadata stamping (drives #840)

**Question**: Where does `spec-kitty init` write `.kittify/metadata.yaml` and which schema fields are stamped today? What is the canonical set of `schema_capabilities`?

**Hypothesis (To verify)**: Init writes a metadata file with project identity but does not yet stamp `spec_kitty.schema_version` or `spec_kitty.schema_capabilities`. Upgrade migrations (e.g., `m_0_9_1_complete_lane_migration`) stamp those fields when migrating an older project, which is why E2E tests of *upgraded* projects worked but a fresh init did not have them.

**Decision direction**: Make `spec-kitty init` stamp both fields at create time using the same canonical values that the upgrade-version logic uses. Reuse the existing schema-version and schema-capabilities source of truth (constants, not duplicated literals). Cover with an integration test that creates a fresh project and asserts the fields appear in `.kittify/metadata.yaml`. Keep existing upgrade-version tests passing.

**Rationale**: FR-001. The fix should not duplicate the schema constants; reuse the existing migration source.

**Alternatives considered**:
- **Backfill via a doctor command**: Pushes a setup burden onto every operator; rejected. Init is the right place.
- **Lazy-stamp on first use**: Spreads the contract; rejected.

**Files to read in WP01**: `src/specify_cli/init/` (or wherever init logic lives), upgrade migrations under `src/specify_cli/upgrade/migrations/` for the canonical schema constants, existing fresh-init tests.

---

## R7 — Skill copy refresh path (drives #336 / #844 cleanup)

**Question**: Which migration refreshes generated copies of `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` into agent directories (`.claude/`, `.amazonq/`, etc.)? How is it triggered in the repo workflow?

**Hypothesis (To verify)**: Per CLAUDE.md, source skills under `src/doctrine/skills/` are deployed to agent directories by an upgrade migration via the `get_agent_dirs_for_project()` helper. The skill copies under `.claude/commands/` etc. are regenerated when `spec-kitty upgrade` runs. The CI / repo workflow may run a "skills regenerate" check.

**Decision direction**: Edit only the SOURCE skill file. After editing, run `spec-kitty upgrade` (or the equivalent `agent skills sync`) locally as part of WP06 so the regenerated agent copies land in the diff. Confirm the established repo-workflow check (if any) doesn't fail because copies are out of sync.

**Rationale**: CLAUDE.md is explicit that source files are edited and copies are generated. Hand-editing copies would create drift.

**Alternatives considered**:
- **Edit copies in place to avoid running the migration**: Direct violation of CLAUDE.md; rejected.
- **Skip refreshing copies and rely on next user upgrade**: Means the workaround text ships in this PR's generated artifacts; rejected.

**Files to read in WP01**: `src/specify_cli/upgrade/migrations/` for the skills-sync migration; `.kittify/command-skills-manifest.json` to understand which agents reference the skill; CLAUDE.md "Template Source Location" section.

---

## Summary table

| ID | Topic | Decision direction | Verification owner |
|---|---|---|---|
| R1 | charter generate ↔ bundle validate | Generate emits explicit `git add` instruction in JSON; E2E follows it | WP01 → WP04 |
| R2 | charter synthesize fixture write pipeline | Make `--json` actually write doctrine artifacts; drop `--dry-run-evidence` fallback | WP01 → WP03 |
| R3 | `--json` stdout discipline | Route SaaS diagnostics to stderr or envelope; per-command tests | WP01 → WP05 |
| R4 | Prompt resolution in next | Always non-empty resolvable `prompt_file` or structured blocked decision | WP01 → WP06 |
| R5 | Profile-invocation lifecycle | Extend writer to cover composed actions; paired `started`/`completed` | WP01 → WP07 |
| R6 | Init metadata stamping | Stamp schema_version + schema_capabilities at init using canonical constants | WP01 → WP02 |
| R7 | Skill copy refresh | Edit SOURCE only; run upgrade/skills sync to refresh copies | WP01 → WP06 |

WP01 will replace each "To verify" block with concrete file/line references and either confirm the decision direction or escalate a deviation for the user before the affected fix WP starts.

---

## Open follow-ups (informational)

- If R1 verification finds that *both* `charter generate` and `bundle validate` need changes (not one or the other), WP04 should be split into 04a and 04b before lanes are locked.
- If R2 verification finds the fix requires a non-trivial doctrine-paths refactor, WP03 escalates as a follow-up tranche per the plan's risk register.
