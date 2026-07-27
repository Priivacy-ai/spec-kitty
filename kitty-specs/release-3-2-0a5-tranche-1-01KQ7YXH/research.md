# Research: 3.2.0a5 Tranche 1 — Release Reset & CLI Surface Cleanup

**Mission**: `release-3-2-0a5-tranche-1-01KQ7YXH` (mid8 `01KQ7YXH`)
**Phase**: 0 — Outline & Research
**Branch**: `release/3.2.0a5-tranche-1`

This document resolves every NEEDS CLARIFICATION item from `spec.md` and locks
down the technical decisions feeding Phase 1 design. All findings are
evidence-backed against the current tree on
`/Users/robert/spec-kitty-dev/spec-kitty-20260427-190321-KGr7VE/spec-kitty`.

## R1 — `.python-version` shape (FR-001 / #805)

- **Decision**: Replace the contents of `.python-version` with the single line
  `3.11`. Decision Moment `01KQ7ZSQKT9DVH7B4GGXWS8DTW` resolved by user.
- **Rationale**: `pyproject.toml::[project].requires-python = ">=3.11"`
  already declares the contributor floor. Pinning `.python-version` to a
  higher patch level (currently `3.13`) imposes a stricter implicit floor
  than packaging does, which is what blocked the maintainer's local 3.14
  environment. A floor at `3.11` keeps the per-repo signal that `uv` and
  IDEs use, lets `uv` pick the highest available `>= 3.11` interpreter, and
  matches packaging exactly.
- **Alternatives considered**: (A) remove `.python-version` entirely — loses
  per-repo IDE/`uv` hint; (C) bump pin to `3.14` to match active dev — fixes
  the maintainer's box but reintroduces friction for any contributor on a
  different version.
- **Impact on FR-001**: Restoring `mypy --strict` cleanliness on
  `src/specify_cli/mission_step_contracts/executor.py` is independent of the
  Python version choice. It must be done after `.python-version` is
  loosened so the strict run actually executes against a runtime that can
  interpret current type hints.

## R2 — Schema-version clobber root cause (FR-002 / #705)

- **Decision**: **Confirmed.** Hypothesis from `spec.md` validated against
  source. The fix shape is **swap the call order** at
  `src/specify_cli/upgrade/runner.py:163–164` so `metadata.save(...)` runs
  *before* `_stamp_schema_version(...)`, plus a regression test that asserts
  `spec_kitty.schema_version` survives a no-op `spec-kitty upgrade` run.
- **Rationale**: `ProjectMetadata.save()`
  (`src/specify_cli/upgrade/metadata.py:139–179`) reconstructs the YAML
  payload from a hardcoded three-key dict (`spec_kitty`, `environment`,
  `migrations`). It does **not** read the existing file or preserve unknown
  keys. So when `_stamp_schema_version` writes `spec_kitty.schema_version`
  via raw YAML (`runner.py:163`) and the very next line calls
  `metadata.save(...)` (`runner.py:164`), the freshly stamped key is
  immediately clobbered. After swap, `_stamp_schema_version` does its own
  read-modify-atomic-write *after* save() has overwritten the file, so the
  stamp survives.
- **Alternatives considered**:
  1. Teach `ProjectMetadata.save()` to round-trip unknown keys (medium
     blast radius — changes deserialization contract; pulls dataclass into a
     general-purpose YAML preserver role it wasn't designed for).
  2. Add `schema_version` as a typed field on `ProjectMetadata` (medium
     blast radius — structural change; couples the gate's storage to the
     dataclass; harder to evolve when a future schema bump moves the bound).
  3. Swap call order (low blast radius — two-line move, no contract change,
     `_stamp_schema_version` already implements the safe read-modify-write
     pattern).
- **Impact on tests**: No existing test asserts `schema_version` survives a
  no-op upgrade. The closest neighbor is
  `tests/cross_cutting/versioning/test_upgrade_version_update.py` which
  asserts only the `version` field. We add a sibling test that runs
  `UpgradeRunner.upgrade()` against a fixture project, then re-reads
  `.kittify/metadata.yaml` and asserts `spec_kitty.schema_version == 3` (or
  the current `REQUIRED_SCHEMA_VERSION`). We also add a CLI smoke test that
  runs `spec-kitty upgrade --yes` followed by
  `spec-kitty agent mission branch-context --json` in a tmp project and
  asserts the second command does not gate on `PROJECT_MIGRATION_NEEDED`.

## R3 — `/spec-kitty.checklist` removal (FR-003 / FR-004 / #815 / #635)

- **Decision**: This is a true bulk edit. `change_mode: bulk_edit` is set in
  `meta.json`. The complete occurrence map is materialized at
  `kitty-specs/release-3-2-0a5-tranche-1-01KQ7YXH/occurrence_map.yaml`.
  Twenty-seven REMOVE files; six KEEP references. DIRECTIVE_035 enforcement
  passes when each REMOVE is gone and each KEEP is preserved verbatim.
- **REMOVE categories** (count): source template (1), generated override (1),
  command skills manifest entry (1), skill snapshots for codex+vibe (3),
  twelve-agent regression baselines (10), upgrade legacy fixture
  prompts (2), legacy hash catalog entry (1), historical migration ledger
  notes already in `.kittify/metadata.yaml` (2), public-facing docs and
  README references (6), one CLI user-facing message in
  `src/specify_cli/cli/commands/init.py:723`.
- **KEEP categories**: every reference inside `kitty-specs/<mission>/`
  (mission specs, plans, research notes), the canonical
  `kitty-specs/<mission>/checklists/requirements.md` artifact contract, the
  top-level `RELEASE_CHECKLIST.md` (release-process artifact), and
  in-template prose in `/spec-kitty.specify` that names the requirements
  checklist by purpose rather than by command.
- **Rationale**: `start-here.md` "Important boundary for #815" and C-003 in
  `spec.md` both specify that `kitty-specs/<mission>/checklists/requirements.md`
  must remain. The `RELEASE_CHECKLIST.md` and "review checklist" usages are
  unrelated to the deprecated slash command and refer to release/process
  artifacts. The CLI message at `init.py:723` advertised
  `/spec-kitty.checklist` as part of the post-init quick-start; once the
  command is gone, that line must go too.
- **Alternatives considered**:
  1. Keep a no-op `/spec-kitty.checklist` shim that prints a deprecation
     redirect — rejected. Issue #815 explicitly retires the surface;
     `start-here.md` "Done Criteria" demands "/spec-kitty.checklist is gone
     from generated user-facing command surfaces". A shim contradicts that.
  2. Block #635 separately — rejected. FR-004 closes #635 as superseded by
     FR-003. One PR, one cross-link.
- **Impact on tests**: `tests/specify_cli/skills/test_registry.py`,
  `tests/specify_cli/skills/test_command_renderer.py`,
  `tests/specify_cli/skills/test_installer.py`, and
  `tests/missions/test_command_templates_canonical_path.py` will need
  fixture/snapshot updates to drop the `checklist.md` lines. We also add a
  new aggregate regression test that scans the rendered output of every
  supported agent (per `CLAUDE.md` "Supported AI Agents" table) and asserts
  zero references to `/spec-kitty.checklist` and zero `checklist.md` files
  in the per-agent baseline directories.

## R4 — `spec-kitty init` non-git target (FR-005 / #636)

- **Decision**: Surface a single-line, actionable message when `init` runs
  in a directory that is not inside a git work tree. The exact wording will
  be added during implementation; the contract is captured in
  `contracts/init_non_git_message.contract.md`.
- **Rationale**: Today the `init.py` flow detects whether the **`git`
  binary** is available (`init.py:222–230`,
  `_console.print("[yellow]ℹ git not detected[/yellow] - install git for
  version control")` at `init.py:360`) but **does not** detect whether the
  current directory is a git repository. Mid-2025 design decision (see
  `init.py:595–597`: "T001: No git initialization. init is file-creation-only.")
  intentionally removed any auto-`git init` behavior. That is the right
  call (init must not silently create a git repo for the user), but it left
  the hole #636 names: a non-git target gets a fully-populated `.kittify/`
  with no hint that the user needs to run `git init` themselves before
  `mission create` will work.
- **Alternatives considered**:
  1. Restore auto `git init` — rejected by existing T001 design decision.
  2. Hard-fail (exit non-zero, no scaffold) when target is not a git repo
     — **explicitly rejected** by Decision Moment
     `01KQ84P1AJ8H3FPJN9J5C12CBY` (user resolved option B over option A).
     Rationale: would break the legitimate "scaffold then init later"
     workflow, and #636's verb is "tell users to run `git init`"
     (informational), not "block them".
  3. Print one informational line near the existing `git not detected`
     branch when the target dir is not in a git work tree, plus a single
     trailing line in the success summary that says "next: run `git init`",
     while completing the full scaffold and exiting 0 as today.
     **Selected.** Canonical invariant: non-git init is allowed; silent
     non-git init is not.
- **Impact on tests**: New unit test in
  `tests/specify_cli/cli/commands/test_init_non_git_message.py` (file does
  not exist yet) that drives `init` against a tmp dir without `.git/` and
  asserts the message appears in stdout exactly once. Also extend
  `tests/e2e/test_cli_smoke.py` to verify the message appears in
  `spec-kitty init --help` quick-start text via `rich` markup-stripped
  comparison.

## R5 — `--feature` alias hiding (FR-006 / #790)

- **Decision**: **Already implemented.** All 28 `--feature` parameter
  declarations across 17 command files already carry `hidden=True`. FR-006
  collapses to:
  1. Add a regression test that scans every CLI subcommand's `--help`
     output and asserts zero occurrences of `--feature`.
  2. Update the `start-here.md` "Done Criteria" verification step accordingly.
  3. Close #790 as "already fixed on `main`; regression test added at `<path>`"
     per `start-here.md` Done Criteria.
- **Rationale**: Verified by the FR-003+FR-006 research subagent against the
  full `src/specify_cli/cli/commands/` tree. Documentation in
  `docs/migration/feature-flag-deprecation.md`,
  `docs/reference/cli-commands.md`, etc. already explains the hidden-alias
  behavior and the `SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION` env var.
- **Alternatives considered**: none — re-implementing is wasted work.
- **Impact on tests**: One new test file
  `tests/specify_cli/cli/test_no_visible_feature_alias.py` that walks the
  `typer` app via Click's introspection, calls each subcommand with
  `--help`, and asserts the rendered string contains no `--feature` token.

## R6 — `spec-kitty agent decision` command shape (FR-007 / #774)

- **Decision**: **Already canonical.** The actual subgroup is
  `spec-kitty agent decision { open | resolve | defer | cancel | verify }`,
  matching what `/spec-kitty.specify` and `/spec-kitty.plan` invoke and
  what `docs/reference/missions.md:268` documents
  (`spec-kitty agent decision resolve …`). FR-007 collapses to:
  1. Add a documentation/help/snapshot consistency test that grep-checks
     every doc page, every skill snapshot, and every `--help` output for
     the literal string "decision" + "command" combinations and asserts
     they all use the canonical `spec-kitty agent decision <sub>` shape
     with no surviving variants like `spec-kitty decision …` or
     `spec-kitty agent decisions …`.
  2. Close #774 as superseded by the now-canonical shape; cite the test as
     evidence.
- **Rationale**: A grep across `docs/reference/`, `docs/explanation/`, and
  the skill templates surfaces only one explicit reference, and it is
  already correct. The historical "wrong shape" complaint in #774 likely
  predates the consolidation under `agent decision`. We close it on
  evidence, not by adding a new alias that would multiply surfaces.
- **Alternatives considered**:
  1. Add a top-level `spec-kitty decision` alias for ergonomics —
     rejected. Adds surface area to maintain, contradicts the "agent"
     subgroup convention used by every other agent-driven command, and
     would itself need to be documented across every agent surface.
- **Impact on tests**: New
  `tests/specify_cli/cli/test_decision_command_shape_consistency.py`
  exercising the doc/help/snapshot grep contract.

## R7 — Diagnostic noise: post-success errors and dedup (FR-008 / FR-009 / #735 / #717)

- **Decision (FR-009 / #717)**: Introduce an in-process dedup gate using
  Python `contextvars.ContextVar` so each distinct diagnostic cause prints
  at most once per CLI invocation. Lives in a new module
  `src/specify_cli/diagnostics/dedup.py`. Two callsites in
  `src/specify_cli/sync/background.py:270` and
  `src/specify_cli/sync/background.py:325` are wrapped to consult the
  ContextVar before logging "Not authenticated, skipping sync". The same
  pattern wraps the token-refresh failure logger (path identified during
  implementation).
- **Decision (FR-008 / #735)**: The post-success "shutdown" / "final sync"
  noise comes from `atexit`-registered handlers in
  `src/specify_cli/sync/background.py:456` (BackgroundSyncService.stop) and
  `src/specify_cli/sync/runtime.py:381` (SyncRuntime.stop). These run
  *after* the JSON payload has been written. Suppression rule: when a
  handler runs during interpreter shutdown AND the command's exit status
  is success, downgrade the warning to debug-level (or skip entirely). A
  small process-state flag set by the success path of
  `agent mission create` (and any other JSON-output command we audit)
  drives the decision in the atexit handlers.
- **Rationale**: ContextVar is the smallest-blast-radius dedup primitive
  available — no logging configuration changes, no monkeypatching, no
  thread-local fragility. Async-safe by construction. The success-flag for
  shutdown suppression keeps the atexit handlers' diagnostic value for
  failure paths (where the user *does* want to see the warning) and only
  silences them after a command that has explicitly declared success.
- **Alternatives considered**:
  1. `logging.Filter` that drops duplicate records — rejected. Filters by
     message identity are brittle (formatting variance breaks them) and
     leak across invocations in long-running daemons.
  2. Move the noisy log to source — drop the call entirely once
     `_fetch_access_token_sync()` knows we're unauthenticated — rejected
     because the warning is genuinely useful the *first* time per
     invocation; we want dedup, not silence.
  3. `atexit.unregister` from the success path — rejected; intrusive,
     and the runtime's atexit registration may have already fired in some
     command paths.
- **Impact on tests**: Two new tests:
  1. `tests/sync/test_diagnostic_dedup.py` — drives
     `BackgroundSyncService` directly with a mock unauthenticated session,
     calls the noisy code path twice, asserts the warning fires exactly
     once.
  2. `tests/e2e/test_mission_create_clean_output.py` — runs
     `spec-kitty agent mission create ...` against a tmp project,
     captures stdout+stderr, asserts (a) JSON payload appears, (b) no
     `Not authenticated, skipping sync` repeats, (c) no red-styled error
     lines after the JSON payload.

## R8 — Release metadata coherence (NFR-002)

- **Decision**: This tranche bumps `pyproject.toml::[project].version` to
  `3.2.0a5`, retitles the `CHANGELOG.md` heading from
  `## [Unreleased - 3.2.0]` to `## [3.2.0a5] — 2026-04-XX` (date filled at
  ship time) AND opens a new `## [Unreleased]` section above it with empty
  Added/Changed/Fixed/Removed buckets, and ensures
  `tests/release/test_dogfood_command_set.py` and
  `tests/release/test_release_prep.py` pass against the new state.
- **Rationale**: `pyproject.toml` is currently `3.2.0a4`; the tranche cuts
  `3.2.0a5`. The CHANGELOG is at `[Unreleased - 3.2.0]` with no alpha
  marker, so the heading must split into a versioned `[3.2.0a5]` entry plus
  a fresh `[Unreleased]` placeholder for follow-on tranches. Release prep
  tests are the executable form of NFR-002.
- **Alternatives considered**:
  1. Defer the version bump to merge-time — rejected. Release-prep tests
     must pass on the tranche branch *before* it merges, otherwise we
     repeat #717's "succeeds while broken" pattern in the release flow.
  2. Use a different next-version label like `3.2.0rc1` — out of scope;
     the parent epic (#822) names the next prerelease as 3.2.0a5.
- **Impact on tests**: `tests/release/` should be runnable green at the end
  of this tranche.

## R9 — Status event reader robustness (FR-010, NFR-010)

- **Decision**: **Confirmed during `/spec-kitty.tasks`.** Hypothesis from the
  blocker investigation is correct: `read_events()` in
  `src/specify_cli/status/store.py:209` calls `StatusEvent.from_dict(obj)`
  on every JSON line, and `StatusEvent` is a lane-transition-only dataclass
  (`src/specify_cli/status/models.py:174–252`) that hard-requires `wp_id`.
  Mission-level events written by `spec-kitty agent decision open` (and its
  resolve / defer / cancel / verify siblings) live in the same
  `status.events.jsonl` file with no `wp_id`. So every mission that uses
  the Decision Moment Protocol becomes unable to run any command that
  calls `read_events()` (`finalize-tasks`, `materialize`, `reduce`,
  dashboard scanner, doctor).
- **Fix shape**: Add an `event_type`-presence discriminator at the top of
  `read_events()`'s per-line loop:
  - If the parsed JSON object has a top-level `event_type` field, skip it
    and continue. Lane-transition events have no `event_type`; mission-level
    events (DecisionPoint family, etc.) always do.
  - Document the WHY in a code comment that names the cooperating
    subsystems (status emitter and Decision Moment Protocol).
  - The existing `if event_name.startswith("retrospective."): continue`
    skip stays as-is.
- **Why `event_type`-presence, not absence-of-`wp_id`** (correction after
  external code review): A `if "wp_id" not in obj: continue` duck-type
  guard would also silently swallow corrupted lane-transition events that
  happen to be missing `wp_id`, breaking the existing fail-loud contract for
  malformed lane events. The `event_type`-presence discriminator is just as
  future-proof (no allowlist to maintain) AND preserves the invariant that
  a lane event missing `wp_id` but ALSO missing `event_type` still raises
  `Invalid event structure on line N`.
- **Alternatives considered**:
  1. Change the writer (Decision Moment Protocol) to write to a separate
     file like `decisions.events.jsonl`. Rejected: bigger blast radius
     (every reader of decision events would need updating; the events
     index already lives at `decisions/index.json` for some queries; the
     status events file is the canonical append-only journal).
  2. Add `wp_id: null` to mission-level events. Rejected: requires
     loosening `StatusEvent.wp_id: str` to `str | None`, which then
     cascades into the reducer, transitions, and downstream consumers
     that currently assume non-null `wp_id`. Bigger blast radius for
     marginal type-safety improvement.
  3. Keep raising on missing `wp_id` and require all writers to populate
     it. Rejected: that would force `DecisionPointOpened` events to carry
     a fake `wp_id`, polluting an event-type that is genuinely
     mission-level.
- **Test impact**:
  - New unit test in `tests/status/test_store.py` (or a sibling new file)
    that constructs an event log with a mix of lane-transition and
    DecisionPoint events, calls `read_events()`, and asserts the result
    list contains exactly the lane-transition events (DecisionPoint events
    silently skipped).
  - The existing tranche's own `status.events.jsonl` is the live
    regression: after the fix lands, `finalize-tasks` on this mission
    succeeds without bypass.

## Open clarifications

None. All `[NEEDS CLARIFICATION]` markers from `spec.md` are resolved by the
above (the spec did not contain any). Three items are deliberately left to
implementation-time judgment because they are too localized to need a
research entry: the exact wording of the FR-005 init message, the
canonical CHANGELOG date stamp, and the GitHub issue number to mint for
FR-010 at PR-open time.
