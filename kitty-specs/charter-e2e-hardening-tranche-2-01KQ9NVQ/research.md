# Research: Charter E2E Hardening Tranche 2

**Mission**: `charter-e2e-hardening-tranche-2-01KQ9NVQ`
**Date**: 2026-04-28
**Status**: WP01 complete — every R-section now carries concrete file:line references and confirmed Decision/Rationale/Alternatives entries. The plan-time direction holds for R1, R3, R4, R6, R7. R2 surfaces a wider-than-expected scope (fixture corpus gap rather than write-pipeline bug) that R5/R6/etc. do not depend on; the operator-escalation note at the bottom of R2 flags it for the affected fix WP (WP03) without blocking the rest of the tranche.

This document follows the format from the plan command: each topic has a Decision (or hypothesis), Rationale, and Alternatives considered.

---

## R1 — `charter generate` output and tracking expectations (drives #841)

**Question**: Where does `spec-kitty charter generate` write the charter today, what does `charter bundle validate` expect to find, and why does the E2E need undocumented `git add` choreography between the two?

**Confirmed**: `charter generate` writes the charter markdown to `.kittify/charter/charter.md` and emits a JSON envelope whose `charter_path` is the relative form of that path. `bundle validate` then asserts that path is **git-tracked**, not merely present on disk:

- Generate path: `src/specify_cli/cli/commands/charter.py:1233` calls `write_compiled_charter(charter_dir, compiled, force=force)` where `charter_dir = repo_root / ".kittify" / "charter"` (`charter.py:1200`). The charter path is then `charter_dir / "charter.md"` (`charter.py:1240`).
- The low-level writer is `src/charter/generator.py:53-58` (`write_charter`) — it just calls `path.write_text(...)`; no git activity.
- JSON envelope shape is built at `src/specify_cli/cli/commands/charter.py:1257-1276`. Today's keys: `result`, `success`, `charter_path`, `interview_source`, `mission`, `template_set`, `selected_paradigms`, `selected_directives`, `available_tools`, `references_count`, `library_files`, `files_written`, `diagnostics`. There is **no** `next_step` field and no `git_add` instruction.
- Validate path: `src/specify_cli/cli/commands/charter_bundle.py:225-300` (`validate`) calls `_classify_paths(canonical_root, list(manifest.tracked_files), require_tracked=True)` at line 246. The "tracked" check is `_is_git_tracked` (`charter_bundle.py:113-132`) which shells out to `git ls-files --error-unmatch -- <rel>` — a path that exists on disk but was never `git add`ed returns `False` and is surfaced as **missing** (lines 157-159).
- The canonical manifest pins `tracked_files = [CHARTER_MD]` where `CHARTER_MD = Path(".kittify/charter/charter.md")` (`src/charter/bundle.py:33, 91-93`). Derived files (governance.yaml / directives.yaml / metadata.yaml) are required to *exist* on disk but not to be tracked — only `charter.md` is tracked-required.
- Doctrine resolution candidates are in `src/charter/_doctrine_paths.py:29-58` and confirm `.kittify/doctrine/` is preferred when present, with shipped-layer fallbacks; this is independent of the charter-tracking invariant but documents the same `.kittify/charter/` directory contract.

**Decision (preferred direction holds)**: Have `charter generate --json` add a `next_step` field to the existing envelope in `charter.py:1257-1276`. When `_is_git_tracked(repo_root, "charter.md")` returns False after the write, the field is `{"action": "git_add", "paths": ["<charter_path>"]}`. When the file is already tracked (re-generation case) the field is `{"action": "none"}`. The E2E then reads `next_step.action` and runs the documented `git add` only when instructed. `bundle validate` is unchanged.

**Rationale**: The tracked-charter invariant in `bundle validate` is load-bearing — it is the same invariant SaaS-sync and CI consumers depend on (manifest pins `tracked_files`). Loosening it would change semantics for every consumer. Locating the fix at the `charter generate` JSON output keeps the change inside one file (`charter.py`), is self-describing, and is exactly the option the brief authorizes. No change is needed in `charter_bundle.py` or `bundle.py`.

**Alternatives considered**:
- **Make `charter generate` auto-stage the file**: Couples a "generate" command to git mutation; surprising and likely violates the auto-commit hygiene principle issue #846 raises. Rejected.
- **Make `bundle validate` accept untracked working-tree files**: Loosens an invariant for everyone to fix one test path; risks changing semantics for SaaS sync and CI consumers. Rejected.
- **Status quo plus document the manual `git add`**: Documents broken behavior as a feature; rejected by FR-002 as written.

---

## R2 — `charter synthesize` adapter contract and write pipeline (drives #839)

**Question**: What does `synthesize --adapter fixture --dry-run --json` emit today, what does `--json` write to disk, and why does the E2E fall back to `--dry-run-evidence` plus hand-seeding `.kittify/doctrine/`?

**Confirmed**: The synthesis pipeline and write pipeline are **functionally complete**, including disk persistence to `.kittify/doctrine/` and the synthesis manifest. The blocker is a **fixture-corpus coverage gap**, not a missing write pipeline.

- CLI entry: `src/specify_cli/cli/commands/charter.py:1787-1934` (`charter_synthesize`). The `--json` non-dry-run path imports `synthesize` and calls it at line 1900. JSON envelope shape: `result/target_kind/target_slug/inputs_hash/adapter_id/adapter_version` (`charter.py:1902-1911`).
- Orchestrator: `src/charter/synthesizer/orchestrator.py:83-213` (`synthesize`). Lines 167-173 stage and promote via `write_pipeline.promote(...)`; promote (`src/charter/synthesizer/write_pipeline.py:236-436`) writes content to `.kittify/doctrine/<kind-subdir>/...` (lines 360-368), provenance sidecars to `.kittify/charter/provenance/...`, and the manifest last to `.kittify/charter/synthesis-manifest.yaml` (lines 416-426). The pipeline is atomic per KD-2.
- `run_all` synthesis is in `src/charter/synthesizer/synthesize_pipeline.py:446-547`. It calls the adapter and computes provenance entries; no filesystem writes happen here — they all funnel through `write_pipeline`.
- FixtureAdapter: `src/charter/synthesizer/fixture_adapter.py:59-122`. `_fixture_path` (lines 83-89) computes the fixture path as `<fixture_root>/<kind>/<slug>/<short_hash>.<kind>.yaml` where `short_hash` is the first 12 hex chars of `compute_inputs_hash(request, "fixture", FIXTURE_VERSION)`. `generate()` (lines 91-115) **raises `FixtureAdapterMissingError` if the file does not exist** (line 96-102).
- Fixture corpus today: `tests/charter/fixtures/synthesizer/{directive,tactic,styleguide}/` — only a hand-curated set of (kind, slug, hash) tuples, e.g. `tests/charter/fixtures/synthesizer/directive/mission-type-scope-directive/7eb312cccccf.directive.yaml`. The hash is content-derived from `(interview_snapshot, doctrine_snapshot, drg_snapshot, run_id, adapter_hints, evidence)` — see `compute_inputs_hash` in `src/charter/synthesizer/request.py`.
- E2E F1 finding: `tests/e2e/test_charter_epic_golden_path.py:495-636` documents the same finding inline: a fresh project's interview snapshot produces a different hash than any pre-recorded fixture, so `--adapter fixture` deterministically raises `FixtureAdapterMissingError` and the E2E falls through to `--dry-run-evidence` plus hand-seeded `.kittify/doctrine/PROVENANCE.md`.
- `--dry-run-evidence` is just an evidence-bundle summary printer that exits before any synthesis runs (`charter.py:1858-1877`). It does NOT write `.kittify/doctrine/`. The E2E's hand-seed step at `test_charter_epic_golden_path.py:617-631` creates the directory itself with a stub `PROVENANCE.md`.

**Decision (revised — see operator escalation below)**: The minimal-viable fix is **not** in the write pipeline. It has two layers; WP03 must pick:

1. **Fixture-corpus expansion (smaller-blast-radius)**: Pre-record fixtures for the canonical fresh-project interview snapshot used by the E2E. Add a small set of (directive/tactic/styleguide, slug) fixtures whose `inputs_hash` matches what `_build_synthesis_request` produces for the E2E's fresh project. This makes `--adapter fixture --json` succeed end-to-end on a fresh project and lets the E2E drop both the `--dry-run-evidence` fallback and the hand-seed.
2. **Fixture-resolver relaxation (broader)**: Change `FixtureAdapter._fixture_path` so it falls back from the exact-hash filename to the (kind, slug) directory's "any" fixture when no hash match is found. This is the more invasive option — it changes the determinism story spelled out in `synthesize_pipeline.py:23-32`.

**Rationale**: FR-004 requires the public command to create artifacts on disk; the test must not seed them. The blocking pipe is the fixture lookup, not the write pipeline. Option 1 is the smallest local change that closes the test gap and preserves byte-identical determinism for everyone else. Option 2 widens fixture resolution semantics for all callers; it is rejected unless option 1 is judged not to scale.

**Alternatives considered**:
- **Promote `--dry-run-evidence` to first-class and have the E2E call it**: Codifies a debug affordance as a public path; rejected (it does no synthesis at all).
- **Skip fixture synthesis in the E2E and only test dry-run**: Loses coverage of the write pipeline; rejected.
- **Use `--adapter generated` in the E2E**: Requires LLM-authored YAML under `.kittify/charter/generated/`; not available in a fresh project. Rejected.

> **Operator note for WP03**: The plan-time direction said "make the real `--adapter fixture --json` path write doctrine artifacts". WP01 finds the write path is already correct end-to-end; the actual gap is the fixture corpus. WP03 should pick option 1 above (record canonical fresh-project fixtures) unless the corpus footprint becomes prohibitive. This is a scoping nuance, not a tranche-blocking deviation — the rest of the WPs are unaffected.

---

## R3 — `--json` stdout discipline (drives #842)

**Question**: Which CLI commands currently leak SaaS sync / auth diagnostic warnings into `--json` stdout, and is the leak in shared output plumbing or per-command?

**Confirmed**: Diagnostics are all routed through Python `logging` (logger names per module: `src/specify_cli/sync/runtime.py:45`, `src/specify_cli/sync/background.py:38`, `src/specify_cli/sync/events.py:29`, etc.) and rich `Console` instances. The leak vector is **atexit-time shutdown warnings** from the background sync service that fire AFTER a command's JSON payload has been printed. The defense pattern is the per-command `mark_invocation_succeeded()` flag, but only one command opts in today.

- The flag implementation: `src/specify_cli/diagnostics/dedup.py:64-77`. `mark_invocation_succeeded()` flips a process-state flag; `invocation_succeeded()` is read by atexit handlers to downgrade their warnings.
- Atexit consumers:
  - `src/specify_cli/sync/runtime.py:307-353` (`SyncRuntime.stop`) consults the flag at line 322 and downgrades WS / background-sync teardown warnings.
  - `src/specify_cli/sync/background.py:150-208` (`BackgroundSyncService.stop`) consults the flag at line 172 and downgrades final-sync timeout / lock-failure warnings (lines 177-207).
- Only opt-in caller today: `src/specify_cli/cli/commands/agent/mission.py:727` calls `mark_invocation_succeeded()`. **None of the four `--json` paths in scope opt in:**
  - `charter generate --json` (`charter.py:1257-1277`) — no call.
  - `charter bundle validate --json` (`charter_bundle.py:293-296`) — no call.
  - `charter synthesize --json` (`charter.py:1902-1911`) — no call.
  - `next --json` (`src/specify_cli/cli/commands/next_cmd.py`) — no call.
- Per-command stderr discipline is mixed: `charter synthesize` constructs `err_console = Console(stderr=True)` (`charter.py:1844`) and routes `SynthesisError` panels there (line 1925-1928). `charter bundle validate` constructs `err_console = Console(stderr=True)` (`charter_bundle.py:234`) and routes resolver failures there (line 240-241). `charter generate` does **not** construct an err_console; its error path prints `[red]Error:[/red]` via `console` (stdout) at lines 1292, 1295.
- Shared `console` instance: `console = Console()` at `charter.py:40` (stdout). Auth warnings flow through normal logging — `src/specify_cli/auth/transport.py` does not print to stdout itself; one Rich-style `console.print` call exists at `src/specify_cli/auth/flows/device_code.py:63` (interactive device-code flow only).
- SaaS-sync diagnostic guards: per-command stdout-only paths in `src/specify_cli/cli/commands/sync.py` (`saas_sync_disabled_message` calls at lines 248, 295, 363, 422, 437, 483, 493, 966) — all are user-facing `console.print(...)` for the `sync` command itself, not shared plumbing. The leak risk for the four `--json` commands is the **atexit path**, not these.

**Decision direction (refined)**: Two-layer fix targeted at the four `--json` paths:

1. **Add `mark_invocation_succeeded()` calls** at the end of the success branch in each of the four envelope writers — `charter.py:1276` (after the `print(json.dumps(...))` for generate), `charter.py:1911` (after the synthesize success print), `charter_bundle.py:296` (after `sys.stdout.write`), and the corresponding `next_cmd.py` JSON write. This activates the existing atexit-downgrade path and stops shutdown warnings from leaking onto stdout/stderr after the JSON payload.
2. **Route in-command error/diagnostic prints to stderr explicitly**. The `charter generate` error block at `charter.py:1291-1296` should construct an `err_console = Console(stderr=True)` and use it (matches the pattern already established in `charter_bundle.py:234` and `charter.py:1844`).

Add per-command tests asserting `json.loads(stdout)` parses cleanly and `stderr` is either empty or contains only documented diagnostic lines.

**Rationale**: FR-005 requires exactly one JSON document on stdout. The lowest-blast-radius fix is to enable the existing `mark_invocation_succeeded()` mechanism for the four commands; the secondary fix (per-command error→stderr) prevents red `Error:` lines printed via `console` from interleaving with JSON.

**Alternatives considered**:
- **Wrap each `--json` invocation in the test with a "tolerate trailing junk" parser**: Defeats FR-005; rejected.
- **Suppress all SaaS diagnostics under `--json`**: Hides legitimate failure signals; rejected. The atexit-downgrade path keeps them at debug-level.
- **Move the success-flag flip into a shared decorator**: Possible but increases blast radius; the per-command call site is small (one line), and the flag's docstring explicitly recommends per-command opt-in (`dedup.py:20-22`).

---

## R4 — Prompt resolution in `next` (drives #844 / #336)

**Question**: How does `next --json` decide a step's `prompt_file`? Why did `#336` produce `prompt_file: null` for discovery? PR `#803` claims fixed; what does the fix look like and is it covered by tests?

**Confirmed**: The runtime bridge resolves prompts via `_build_prompt_safe` in three call sites and **swallows every exception** by returning `None`. There is no structured-blocked decision when prompt building fails — the caller emits a `kind=step` Decision with `prompt_file: null`. The runtime-next SKILL still ships the workaround text.

- Helper: `src/specify_cli/next/decision.py:455-481` (`_build_prompt_safe`). Wraps `build_prompt(...)` in `try/except Exception` and returns `None` on any failure (line 479-480). It also redirects stdout/stderr inside the call (lines 468-469) to keep diagnostic output out of `--json` payloads.
- Step-kind matrix in `decision.py:358-452` (`_state_to_action`):
  - `discovery` is mapped via the `_ALIASES` table at line 425 (`"discovery": "research"`).
  - `research`, `documentation`, and other generic states resolve via `resolve_command(f"{state}.md", repo_root, mission=mission_name)` (line 418); on `FileNotFoundError`, fall through (lines 420-421).
  - Composed actions (`specify`, `plan`, `tasks`, `implement`, `review`) are dispatched via `_should_dispatch_via_composition` (`runtime_bridge.py:429-461`) backed by `_COMPOSED_ACTIONS_BY_MISSION` (`runtime_bridge.py:402-406`).
- Three call sites in `runtime_bridge.py` where `prompt_file` can be `None`:
  - `runtime_bridge.py:1571-1583` (CLI-guard failure path) — `prompt_file = _build_prompt_safe(action or current_step_id, ...) if action else None`. If `_state_to_action` returned `(None, None, None)`, `action` is `None` and `prompt_file` is `None`.
  - `runtime_bridge.py:1662-1674` (composition-dispatch failure path) — same shape.
  - `runtime_bridge.py:2118-2138` (legacy non-composition step path) — calls `_build_prompt_safe` unconditionally; if it returns `None`, the Decision still ships with `kind=step, prompt_file=None`.
  - `runtime_bridge.py:2147-2315` (`_map_runtime_decision`): blocked → `prompt_file` not set; decision_required → builds `prompt_file` via `build_decision_prompt` and silently keeps it `None` on exception (lines 2193-2207); step → `prompt_file = _build_prompt_safe(...)` with no fallback on `None`.
- Existing workaround text in the SOURCE skill at `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md`:
  - Step kind row at line 369: "Check `prompt_file` is not null, then read and execute".
  - Explicit warning at lines 377-380: "If it is `null`, the runtime could not generate a prompt for this step (known issue #336). Treat a null `prompt_file` as a blocked state — do not attempt to execute without a prompt."
  - Bash example at lines 451-456: explicit `if [ "$PROMPT" = "null" ] || [ -z "$PROMPT" ]; then break  # Cannot execute without a prompt`.
  - Known-issues entry at lines 504-507: "#336 — `prompt_file` can be `null` on `step` decisions… **Workaround:** Check `prompt_file` for null before acting; treat null as blocked."

**Decision direction (preferred holds)**: Tighten the three call sites so that a `None` from `_build_prompt_safe` becomes a `Decision` with `kind=DecisionKind.blocked` and a structured `reason` (e.g. `"prompt resolution failed for step '<id>' / action '<action>'"`) rather than a `kind=step` decision with `prompt_file=None`. Concretely:

1. After `prompt_file = _build_prompt_safe(...)` at lines 1571-1583, 1662-1674, 2118, 2252, and 2286 in `runtime_bridge.py`, check for `None` and return a blocked Decision instead of a step Decision when both `prompt_file is None` and the action requires a prompt.
2. Add per-step-kind tests (discovery, research, documentation, implement, review, composed actions) asserting the issued Decision either carries a non-empty resolvable `prompt_file` or is `kind=blocked` with a populated `reason`.
3. Remove the workaround text from `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` (lines 369, 377-380, 451-456, 504-507) and refresh agent copies via the established skill-update path (see R7).

**Rationale**: FR-006 + FR-013. `prompt_file: null` on `kind=step` is currently undefined behavior (the SKILL even tells callers to treat it as blocked) — making the runtime emit a structured `blocked` decision in that case formalizes what callers already do.

**Alternatives considered**:
- **Allow `prompt_file: null` for "informational" steps and adapt the E2E**: Conflates step kinds; rejected — there is no documented public step kind that legitimately carries no prompt.
- **Resolve a generic placeholder prompt on the fly**: Hides missing prompt-template definitions; rejected.
- **Surface the underlying exception text in `reason`**: Good idea, partial — the catch block in `_build_prompt_safe:479-480` swallows the exception. WP06 should capture the exception message and pass it back to the caller for inclusion in `reason`.

---

## R5 — Profile-invocation lifecycle write path (drives #843)

**Question**: Where in the runtime is `.kittify/events/profile-invocations/` populated? For which step kinds is the path skipped today, and why?

**Confirmed**: The lifecycle write path is `StepContractExecutor.execute → ProfileInvocationExecutor.invoke → InvocationWriter.write_started/write_completed`. The directory is `.kittify/events/profile-invocations/`, the records are JSONL, and the canonical outcome enum is `done | failed | abandoned` (NOT `skipped|blocked` as the brief suggested — the actual schema is narrower). Composed software-dev/research/documentation actions get records; legacy DAG step kinds (e.g. `discovery`) do not.

- Storage path constant: `src/specify_cli/invocation/writer.py:16` — `EVENTS_DIR = ".kittify/events/profile-invocations"`. Each invocation produces one JSONL file at `<EVENTS_DIR>/<invocation_id>.jsonl` (`writer.py:61-67`).
- Write entrypoints:
  - `InvocationWriter.write_started` (`writer.py:96-121`) — exclusive-create mode; ULID-collision detection.
  - `InvocationWriter.write_completed` (`writer.py:123-167`) — append mode; idempotent guard against double-completion.
- Schema: `src/specify_cli/invocation/record.py:19-42` (`InvocationRecord`). Critical for WP07: the `outcome` field type at `record.py:34` is `Literal["done", "failed", "abandoned"] | None`. This is the canonical enum — the brief's expected `skipped|blocked` are NOT valid values today.
- Tier policy: `record.py:77-117` (`MINIMAL_VIABLE_TRAIL_POLICY`). Tier 1 is mandatory and writes one InvocationRecord at `EVENTS_DIR/{invocation_id}.jsonl` before the executor returns (line 79-86).
- Composer: `src/specify_cli/mission_step_contracts/executor.py:136-222` (`StepContractExecutor.execute`):
  - Per-step started write: line 178 (`self._invocation_executor.invoke(...)`).
  - Per-step completed write: line 213 (`self._invocation_executor.complete_invocation(payload.invocation_id, outcome="done")`); failure path line 206-208 with `outcome="failed"`.
- ProfileInvocationExecutor: `src/specify_cli/invocation/executor.py`. The `invoke` path at `executor.py:140-237` builds `InvocationRecord(event="started", ...)` (lines 213-225) and calls `self._writer.write_started(record)` (line 225). `complete_invocation` at `executor.py:252-305` calls `self._writer.write_completed(...)` (line 277-282).
- Composition gate: `src/specify_cli/next/runtime_bridge.py:402-461` (`_should_dispatch_via_composition`). Composed actions for built-in missions are pinned at lines 402-406:
  ```
  software-dev:    {specify, plan, tasks, implement, review}
  research:        {scoping, methodology, gathering, synthesis, output}
  documentation:   {discover, audit, design, generate, validate, publish}
  ```
  Custom missions widen via `_resolve_step_binding` (lines 464-484) when the frozen template's step has `agent_profile` or `contract_ref` set.
- Skipped step kinds today: any `software-dev` step NOT in the set above (e.g. `discovery`) flows through the legacy DAG planner path (`runtime_bridge.py:2118-2144`) and **does not call `ProfileInvocationExecutor`**, so no started/completed pair is written for those steps.
- Tests covering the runtime walk pattern: `tests/integration/test_documentation_runtime_walk.py`, `tests/integration/test_research_runtime_walk.py` (referenced as the established pattern).

**Decision direction (preferred holds, with enum correction)**: Extend the lifecycle writer to cover every step kind issued by `next`, including discovery and other legacy DAG steps that bypass composition today. WP07 should:

1. Wire `ProfileInvocationExecutor.invoke` / `complete_invocation` into the legacy DAG path in `runtime_bridge.py:2118-2144` (and the parallel sites at 1571-1583, 1662-1674, 2147-2315) so paired `started` / `completed` records are emitted for every issued action.
2. Use the canonical outcome vocabulary as defined: **`done | failed | abandoned`** (`record.py:34`). The brief's expected `skipped|blocked` mapping is not in scope of WP07; if those outcomes are desired, that is a separate schema change requiring a Pydantic-frozen model bump in `record.py:42`.
3. Action identity: `action` field on `InvocationRecord` (line 25) is the canonical token; pass the resolved `action` from `_state_to_action` (or the composed-action token from `_normalize_action_for_composition`).
4. Add an integration test that walks one composed action end-to-end and asserts the started/completed pair exists at `.kittify/events/profile-invocations/<invocation_id>.jsonl`.

**Rationale**: FR-007 + NFR-006. The composition path already writes paired records; widening the writer to the legacy DAG is small and local. The outcome enum correction is critical — using `skipped` or `blocked` would fail Pydantic validation at `InvocationRecord` construction time.

**Alternatives considered**:
- **Move the lifecycle-write call into a `next`-side wrapper**: Spreads responsibility; rejected because the executor is the canonical write site (see C-001 invariant note at `runtime_bridge.py:393-395`).
- **Make the directory optional and document its WP-only scope**: Defeats FR-010; rejected.
- **Expand the outcome enum to include `skipped|blocked`**: Possible but out of scope for WP07. The current `abandoned` value is sufficient for "agent walked away" cases.

---

## R6 — Init metadata stamping (drives #840)

**Question**: Where does `spec-kitty init` write `.kittify/metadata.yaml` and which schema fields are stamped today? What is the canonical set of `schema_capabilities`?

**Confirmed**: Init writes metadata via `ProjectMetadata.save(...)` and **does not stamp** `spec_kitty.schema_version` or `spec_kitty.schema_capabilities`. The canonical constants live in the migration runner module.

- Init writer: `src/specify_cli/cli/commands/init.py:817-834`. Constructs a `ProjectMetadata(...)` instance with `version`, `initialized_at`, `python_version`, `platform`, `platform_version` only (lines 824-830) and saves via `metadata.save(project_path / ".kittify")` at line 831. There is no `schema_version` or `schema_capabilities` argument.
- Metadata writer body: `src/specify_cli/upgrade/metadata.py:139-179` (`ProjectMetadata.save`). The YAML structure assembled at lines 147-169 contains only:
  - `spec_kitty: {version, initialized_at, last_upgraded_at}` (lines 148-152)
  - `environment: {python_version, platform, platform_version}` (lines 153-157)
  - `migrations: {applied: [...]}` (lines 158-168)
  No `schema_version` or `schema_capabilities` keys are emitted.
- Canonical schema constants: `src/specify_cli/migration/runner.py:33-39`:
  ```
  _TARGET_SCHEMA_VERSION = 3
  _TARGET_SCHEMA_CAPABILITIES = [
      "canonical_context",
      "event_log_authority",
      "ownership_manifest",
      "thin_shims",
  ]
  ```
- Where the constants are USED today: `src/specify_cli/migration/runner.py:192-218` (`_update_schema_version`) — only on **upgrade**, not on fresh init. It loads `.kittify/metadata.yaml`, sets `spec_kitty["schema_version"] = _TARGET_SCHEMA_VERSION` and `spec_kitty["schema_capabilities"] = _TARGET_SCHEMA_CAPABILITIES` (lines 211-212), and writes back. This is invoked from the migration runner pipeline at line 544.
- Reader confirms presence is required for downstream commands: `src/specify_cli/migration/schema_version.py:60-87` (`get_project_schema_version`) reads `data["spec_kitty"]["schema_version"]`. If absent, the project is classified as `UNMIGRATED` (`schema_version.py:39`) and the migration gate (`src/specify_cli/migration/gate.py:89`) blocks normal commands.
- Existing fresh-init tests:
  - `tests/init/test_init_minimal_integration.py`
  - `tests/init/test_init_flow_integration.py`
  - `tests/init/test_init_idempotent.py`
  - `tests/init/test_init_in_existing_repo.py`
  - `tests/init/test_init_next_steps.py`
  - `tests/init/test_init_help.py`
  - `tests/agent/test_init_command.py`
  - `tests/agent/cli/commands/test_init_non_interactive.py`
  - `tests/specify_cli/cli/commands/test_init_manifest_coexistence.py`
  - `tests/specify_cli/cli/commands/test_init_hybrid.py`
  None of these assert `schema_version` or `schema_capabilities` are present after init (verified via grep — those tokens do not appear in any `tests/init/` or `tests/specify_cli/cli/commands/test_init*.py` file).

**Decision direction (preferred holds)**: Make `spec-kitty init` stamp both fields at create time using the canonical migration constants (do NOT duplicate the literals). WP02 should:

1. Add `schema_version: int | None = None` and `schema_capabilities: list[str] | None = None` to `ProjectMetadata` at `src/specify_cli/upgrade/metadata.py:33-43` (with a frozen default of None for backward-compat with existing `load()` paths).
2. In `ProjectMetadata.save` at `metadata.py:147-169`, write `spec_kitty.schema_version` and `spec_kitty.schema_capabilities` when set (preserving omission for legacy projects).
3. Update the init call site at `cli/commands/init.py:824-830` to import `_TARGET_SCHEMA_VERSION` and `_TARGET_SCHEMA_CAPABILITIES` from `src/specify_cli/migration/runner.py` (or extract to a small `migration/schema_constants.py` module if the leading-underscore name causes import friction) and pass them into the `ProjectMetadata(...)` constructor.
4. Cover with a fresh-init integration test (new test in `tests/init/`) that asserts `.kittify/metadata.yaml` contains `spec_kitty.schema_version == 3` and `spec_kitty.schema_capabilities == [...4-item canonical list...]`. Keep existing upgrade-version tests passing.

**Rationale**: FR-001. Reuse the existing migration source-of-truth so fresh and upgraded projects converge on the same constants. The leading-underscore name on `_TARGET_SCHEMA_VERSION` is a minor refactor concern: either widen the symbol's public-API status or introduce a single-module-name re-export.

**Alternatives considered**:
- **Backfill via a doctor command**: Pushes setup burden onto every operator; rejected. Init is the right place.
- **Lazy-stamp on first use**: Spreads the contract; rejected.
- **Duplicate the constants in init.py**: Drift-prone; rejected. Reuse via import.

---

## R7 — Skill copy refresh path (drives #336 / #844 cleanup)

**Question**: Which migration refreshes generated copies of `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` into agent directories (`.claude/`, `.amazonq/`, etc.)? How is it triggered in the repo workflow?

**Confirmed**: The dedicated migration is `m_2_1_2_fix_runtime_next_skill.py`, which uses the reusable `find_skill_files` helper (NOT `get_agent_dirs_for_project`). Skill files are deployed across the SKILL_ROOTS list rather than the slash-command AGENT_DIRS list. The repo workflow is `spec-kitty upgrade`.

- Skill-specific migration: `src/specify_cli/upgrade/migrations/m_2_1_2_fix_runtime_next_skill.py` (entire file, 103 lines).
  - `_SKILL_NAME = "spec-kitty-runtime-next"` at line 21.
  - `apply` (lines 55-102) reads the canonical SKILL.md from `doctrine/skills/spec-kitty-runtime-next/SKILL.md` (lines 60-65 via `importlib.resources.files("doctrine")`, fallback to repo path at lines 67-75).
  - Walk: `find_skill_files(project_path, _SKILL_NAME, ["SKILL.md"])` at line 82 — iterates every installed copy across all known agent skill roots and replaces it.
  - Detection gate: `_OLD_MARKERS` (lines 25-27) — only replaces a copy if it still contains the pre-2.1.2 marker. Once WP06 modifies the canonical SKILL.md, a new migration with new markers is required.
- Reusable helper module: `src/specify_cli/upgrade/skill_update.py`.
  - `SKILL_ROOTS` (lines 37-51) lists the 13 possible skill roots: `.claude/skills`, `.agents/skills`, `.qwen/skills`, `.kilocode/skills`, `.github/skills`, `.gemini/skills`, `.cursor/skills`, `.opencode/skills`, `.windsurf/skills`, `.augment/skills`, `.roo/skills`, `.agent/skills`, `.codex/skills`.
  - Functions: `find_skill_files(project_path, skill_name, file_patterns=None)` (skill_update.py:71-...), `apply_text_replacements(...)`, `file_contains_any(...)`.
- Slash-command (NOT skill) helper for completeness: `src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py`. The helper `get_agent_dirs_for_project` is re-exported at line 570 (imported at line 22 from a sibling utilities module). This helper is for **slash-command** AGENT_DIRS (e.g. `.claude/commands`, `.amazonq/prompts`, etc.) — a different list from `SKILL_ROOTS`.
- Manifest: `.kittify/command-skills-manifest.json` only tracks the **command-skills** packages (e.g. `spec-kitty.advise`, `spec-kitty.charter`, `spec-kitty.implement`) installed under `.agents/skills/spec-kitty.<command>/SKILL.md`. It does NOT enumerate copies of governance skills like `spec-kitty-runtime-next`. The `command-skills-manifest.json` plays no role in refreshing `spec-kitty-runtime-next/SKILL.md` copies — that job belongs solely to the migrations under `src/specify_cli/upgrade/migrations/`.
- Established workflow command: `spec-kitty upgrade` runs registered migrations (via the `MigrationRegistry` decorator at `m_2_1_2_fix_runtime_next_skill.py:30`).

**Decision direction (preferred holds)**: WP06 must:

1. Edit the SOURCE skill at `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` to remove the `prompt_file == null` workaround text (specifically lines 369, 377-380, 451-456, and 504-507 per R4).
2. Author a new migration `m_X_Y_Z_remove_runtime_next_null_prompt_workaround.py` (version aligned with the WP shipping it) that mirrors the structure of `m_2_1_2_fix_runtime_next_skill.py`. Its `_OLD_MARKERS` should match the workaround text being removed (not the new markers — those go into the canonical file).
3. After editing the source skill, run `spec-kitty upgrade` locally so agent copies under `.claude/skills/spec-kitty-runtime-next/SKILL.md`, `.agents/skills/spec-kitty-runtime-next/SKILL.md`, etc. are regenerated and land in the same diff. Confirm via `find_skill_files(repo_root, "spec-kitty-runtime-next", ["SKILL.md"])`.

**Rationale**: CLAUDE.md is explicit that source files are edited and copies are generated. The migration module is the canonical mechanism for refreshing copies; the helper to use is `find_skill_files` (skill scope), not `get_agent_dirs_for_project` (slash-command scope). The two `AGENT_DIRS`/`SKILL_ROOTS` lists differ by design — using the wrong helper would skip half the agents.

**Alternatives considered**:
- **Edit copies in place to avoid running the migration**: Direct violation of CLAUDE.md; rejected.
- **Skip refreshing copies and rely on next user upgrade**: Means the workaround text ships in this PR's generated artifacts; rejected.
- **Use `get_agent_dirs_for_project` instead of `find_skill_files`**: Wrong list — slash commands vs skills are different surfaces. Rejected.

---

## Summary table

| ID | Topic | Decision direction | Verification owner |
|---|---|---|---|
| R1 | charter generate ↔ bundle validate | `charter generate --json` adds `next_step.action == "git_add"` when charter.md is untracked; bundle validate unchanged | WP01 → WP04 |
| R2 | charter synthesize fixture write pipeline | Write pipeline already correct; pre-record canonical fresh-project fixtures (operator note above) | WP01 → WP03 |
| R3 | `--json` stdout discipline | Add `mark_invocation_succeeded()` to the four `--json` paths; route in-command errors to stderr explicitly | WP01 → WP05 |
| R4 | Prompt resolution in next | None-from-`_build_prompt_safe` becomes structured blocked Decision; remove SKILL workaround text | WP01 → WP06 |
| R5 | Profile-invocation lifecycle | Wire executor into legacy DAG path; canonical outcome enum is `done\|failed\|abandoned` (record.py:34) | WP01 → WP07 |
| R6 | Init metadata stamping | Stamp `schema_version=3` and 4-item `schema_capabilities` from `migration/runner.py` constants at init time | WP01 → WP02 |
| R7 | Skill copy refresh | Edit SOURCE then add a new migration mirroring `m_2_1_2_fix_runtime_next_skill.py`; refresh via `spec-kitty upgrade` | WP01 → WP06 |

WP01 has replaced every "To verify" block with concrete file:line references and either confirmed the decision direction or noted an in-scope refinement. The R2 nuance (corpus gap, not write-pipeline bug) is documented in-place and does not block any other WP.

---

## Open follow-ups (informational)

- R2's corpus-pre-recording approach (option 1) is the recommended starting point for WP03. If the fresh-project interview snapshot turns out to be unstable across spec-kitty versions (i.e. fixture hash drifts), WP03 may need to escalate to option 2 (fixture-resolver relaxation) or to a per-test fixture-generation hook.
- R5 includes a corrected outcome vocabulary (`done|failed|abandoned`) that diverges from the brief's expected (`done|failed|skipped|blocked`). WP07 should confirm whether the existing 3-value enum is sufficient for the lifecycle records the E2E asserts on; if not, that becomes a separate Pydantic schema change.
- R6 mentions the leading-underscore on `_TARGET_SCHEMA_VERSION` / `_TARGET_SCHEMA_CAPABILITIES`. If WP02 prefers a clean import surface, extracting them to `src/specify_cli/migration/schema_constants.py` (or similar) and re-exporting from `runner.py` is the smallest local refactor.
