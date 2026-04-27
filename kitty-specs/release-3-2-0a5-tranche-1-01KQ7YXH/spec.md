# Mission Specification: 3.2.0a5 Tranche 1 — Release Reset & CLI Surface Cleanup

**Mission ID**: `01KQ7YXHA5AMZHJT3HQ8XPTZ6B` (mid8 `01KQ7YXH`)
**Mission Slug**: `release-3-2-0a5-tranche-1-01KQ7YXH`
**Mission Type**: software-dev
**Target Branch**: `release/3.2.0a5-tranche-1`
**Created**: 2026-04-27
**Source**: `start-here.md` (workspace root) + GitHub issues listed below.

## Purpose (Stakeholder View)

**TLDR**: Stabilize the 3.2.0a5 release train and trim confusing CLI surfaces; no new product features.

**Context**: This is the first tranche of the 3.2.0 stabilization epic
([Priivacy-ai/spec-kitty#822](https://github.com/Priivacy-ai/spec-kitty/issues/822)).
Local agents and contributors are bumping into nine separate release-hygiene
papercuts that, together, make the next prerelease feel unreliable: a
deprecated command surface (`/spec-kitty.checklist`) keeps appearing in
generated agent files, `spec-kitty upgrade` reports success while leaving the
project in a state that blocks subsequent commands, mission creation prints
red shutdown errors after a successful JSON payload, the same "token refresh
failed" line is repeated three or four times per command, the `--feature`
alias is loud in `--help` even though it is only kept for back-compat, the
`init` command silently fails on a non-git target instead of suggesting
`git init`, and the `spec-kitty agent decision` command shape leads
implementers toward a path that doesn't exist. The tranche fixes these so
operators stop second-guessing the tool.

## Bulk-Edit Notice

Issue #815 removes the same `/spec-kitty.checklist` identifier (and related
`checklist.md` template/snapshot files) across roughly thirty files —
templates, registry, command renderer/installer, shim registry, regression
baselines, snapshot fixtures, and docs. `change_mode: bulk_edit` is set in
`meta.json`; `/spec-kitty.plan` must produce an `occurrence_map.yaml` for the
`/spec-kitty.checklist` removal so DIRECTIVE_035 (cross-file rename gate) can
verify that every occurrence is either removed (intentional surface deletion)
or kept (reserved for canonical contexts such as
`kitty-specs/<mission>/checklists/requirements.md`, "release checklist", and
the requirements-quality wording inside `/spec-kitty.specify`).

## Live Evidence Captured During Specification

These observations were collected while drafting this spec on
`release/3.2.0a5-tranche-1` and are first-hand reproductions of the issues in
scope. Keep them in mind during planning and implementation:

- **Live #705 / #717 evidence** — The CLI binary at `~/.local/bin/spec-kitty`
  reported version `3.2.0a3` in this fresh dev workspace while
  `pyproject.toml` and `.kittify/metadata.yaml` were at `3.2.0a4`. Running
  `spec-kitty upgrade` then `spec-kitty upgrade --yes` printed
  `Upgrade complete! 3.2.0a4 -> 3.2.0a4` even though
  `_stamp_schema_version` (`src/specify_cli/upgrade/runner.py:163`) failed to
  leave `spec_kitty.schema_version` in `.kittify/metadata.yaml`. Strong
  hypothesis: the `metadata.save(...)` call on the line immediately after
  `_stamp_schema_version` clobbers the freshly stamped key because
  `ProjectMetadata.save()` does not preserve unknown fields. The compat
  planner then classifies the project as `LEGACY` and blocks every
  `spec-kitty agent ...` invocation with
  `PROJECT_MIGRATION_NEEDED` — an upgrade that "succeeds" yet leaves the
  project unusable. To unblock spec authoring,
  `spec_kitty.schema_version: 3` was added by hand to
  `.kittify/metadata.yaml`. The implementing agent must reproduce, root-cause,
  and fix this in WP scope (likely co-located with #705 and #717).
- **Live #717 evidence** — A single `spec-kitty agent mission create ...`
  invocation printed `Not authenticated, skipping sync` four times in one
  command session. Token-refresh / sync notices are not deduplicated.
- **Live FR-010 evidence (NEW)** — Running
  `spec-kitty agent mission finalize-tasks --mission <slug> --json` on this
  mission failed with
  `{"error": "Invalid event structure on line 1: 'wp_id'"}` because
  `read_events()` in `src/specify_cli/status/store.py:209` blindly passes
  every event in `status.events.jsonl` to `StatusEvent.from_dict()`, which
  is a lane-transition-only dataclass that requires `wp_id`. The
  Decision Moment Protocol (`spec-kitty agent decision open`) writes
  mission-level `DecisionPointOpened` / `DecisionPointResolved` events into
  the same file with no `wp_id`. The reader has no event-type
  discrimination beyond skipping `retrospective.*`, so every mission that
  uses the Decision Moment Protocol becomes unable to run any command
  that calls `read_events()` (including `finalize-tasks`, `materialize`,
  `reduce`, the dashboard scanner). Two cooperating subsystems write to
  the same file with incompatible schemas.
- **Migration-already-applied warning** — `spec-kitty upgrade --dry-run`
  warned `Migration 3.2.0a4_normalize_mission_lifecycle already applied,
  skipping`, yet `spec-kitty agent mission create` still gated on
  "needs migrations". The user-visible signal disagrees with the reality the
  CLI is enforcing — same family of confusion as #705.

## Scope

### In Scope (this tranche)

- The nine GitHub issues listed under [Functional Requirements](#functional-requirements).
- Regression tests for each fix.
- Documentation/snapshot updates needed to keep the generated agent surfaces
  in sync after `/spec-kitty.checklist` is removed.
- Release metadata reconciliation (`pyproject.toml`, `CHANGELOG.md`, release
  prep tests) so the next prerelease state is internally consistent.
- Live evidence reproductions noted above (especially the schema_version
  clobber in `_stamp_schema_version`).

### Out of Scope

- New product features.
- Changes to hosted SaaS / tracker / sync behavior beyond suppressing the
  noisy success-time output called out in #735 and #717. Any deeper
  hosted-side work is a separate tranche.
- Removal of `kitty-specs/<mission>/checklists/requirements.md` (the
  canonical requirements-quality checklist created by `/spec-kitty.specify`).
  Only the standalone `/spec-kitty.checklist` command surface is being
  retired; the word "checklist" still applies to that file, to release
  checklists, to review checklists, and to tasks.
- Cloning `spec-kitty-saas` or `spec-kitty-tracker` repos unless
  implementation proves it is genuinely required (per `start-here.md`).

## Personas (who feels each fix)

- **Local Spec Kitty agent operator (primary)** — Runs `spec-kitty` CLI in a
  fresh worktree, reads JSON output from `mission create`, and follows the
  `/spec-kitty.specify` → `/spec-kitty.plan` → `/spec-kitty.tasks` →
  `/spec-kitty.implement` workflow. Pain: confusing CLI output causes them
  to second-guess otherwise-successful commands.
- **Spec Kitty contributor** — Edits source templates under
  `src/specify_cli/missions/*/command-templates/` and the registry. Pain:
  deprecated `/spec-kitty.checklist` files keep being regenerated into agent
  copies; release metadata divergence breaks release-prep tests.
- **First-time `spec-kitty init` user** — Runs `spec-kitty init` in a
  directory that is not a git repository. Pain: the command fails without
  telling them they need `git init` first.
- **Implementer reading docs for `spec-kitty agent decision`** — Looks up the
  command shape from `docs/reference/missions.md` or
  `docs/reference/slash-commands.md`. Pain: the documented shape leads to a
  command path that doesn't exist or doesn't behave as advertised.

## Domain Language (canonical terms)

- **Tranche** — A release-scoped batch of stabilization fixes inside the
  3.2.0 epic. This mission is *Tranche 1*.
- **Mission-step contracts** — Code under
  `src/specify_cli/mission_step_contracts/` that defines the typed contract
  surface mission steps must satisfy.
- **Generated user-facing command surface** — Any of the agent-specific
  copies under `.claude/`, `.amazonq/`, `.augment/`, `.codex/`, `.gemini/`,
  `.github/prompts/`, etc. that are produced from sources in
  `src/specify_cli/missions/*/command-templates/`. (See
  `CLAUDE.md` for the canonical source/copy boundary.) When this spec says
  "remove `/spec-kitty.checklist` from the command surface" it means remove
  it from *both* the source templates and the generated copies, and update
  the migrations/registry so future renders never recreate it.
- **Canonical requirements checklist** —
  `kitty-specs/<mission>/checklists/requirements.md`, generated by
  `/spec-kitty.specify`. **Stays.** Distinct from the deprecated
  `/spec-kitty.checklist` slash command.
- **Hidden alias** — A CLI option (e.g. `--feature`) that is still accepted
  for compatibility but is omitted from `--help` output.

## User Scenarios

### Primary scenario — "I cut a clean 3.2.0a5 prerelease"

1. A maintainer is on `release/3.2.0a5-tranche-1`.
2. They run release prep tests (`tests/release/test_dogfood_command_set.py`,
   `tests/release/test_release_prep.py`) plus
   `mypy --strict src/specify_cli/mission_step_contracts/executor.py` and
   `ruff check`.
3. All tests pass: `pyproject.toml`, `CHANGELOG.md`, `.python-version`, and
   release-prep metadata agree on the next prerelease state.
4. The dogfood command-set tests confirm `/spec-kitty.checklist` is **gone**
   from every generated agent surface, while
   `kitty-specs/<mission>/checklists/requirements.md` still gets created by
   `/spec-kitty.specify` against a sample project.
5. They run `spec-kitty --help`, `spec-kitty agent --help`,
   `spec-kitty agent decision --help`, and `spec-kitty init --help`. Help
   output is free of the legacy `--feature` flag, the decision command
   shape is unambiguous, and `init --help` references the "run `git init`"
   guidance.
6. They run a sample mission create flow. JSON payload prints, then no
   trailing red shutdown error, no triplicated token-refresh line.
7. The maintainer tags the release with confidence.

### Exception scenario A — Operator hits the schema_version gate

1. Operator runs any `spec-kitty agent ...` command in a worktree where
   `_stamp_schema_version` failed to persist.
2. Today, they get blocked with `PROJECT_MIGRATION_NEEDED` even though
   `spec-kitty upgrade` reports nothing to do.
3. After this tranche, either (a) `_stamp_schema_version` reliably persists
   `spec_kitty.schema_version` so the gate clears, OR (b) the upgrade
   command surface produces a clear, single-line diagnostic explaining the
   real remediation step. No more silent "complete" messages followed by
   blocked gates.

### Exception scenario B — `spec-kitty init` in a non-git directory

1. New user runs `spec-kitty init` in `~/my-project` which is not a git
   repository.
2. Today, the failure mode is unclear.
3. After this tranche, the command tells them: "This directory is not a git
   repository. Run `git init` and try again." (Wording approved during
   plan.)

### Exception scenario C — Operator looks up `spec-kitty agent decision`

1. Operator opens `docs/reference/missions.md` or
   `docs/reference/slash-commands.md` to find the decision command shape.
2. Today, the documented shape leads to a command path that does not
   resolve as advertised.
3. After this tranche, either an alias is added that matches the documented
   shape, or the docs and `--help` output are updated to point at the
   actual canonical path. Implementers do not chase a phantom command.

## Rules and Invariants

- **R1**: `/spec-kitty.checklist` MUST NOT appear in any generated agent
  command surface after this tranche merges (slash-command agents AND skills
  agents — see `CLAUDE.md` "Supported AI Agents" table).
- **R2**: `/spec-kitty.specify` MUST continue to create
  `kitty-specs/<mission>/checklists/requirements.md` for every new mission.
- **R3**: `--feature` alias MUST remain accepted by every CLI subcommand
  that accepts it today (zero behavioral regression for existing callers).
  Only its `--help` visibility changes.
- **R4**: `spec-kitty upgrade` MUST NOT print a success message in the same
  invocation in which it leaves the project blocked by a downstream gate.
  Either it succeeds and downstream commands work, or it surfaces the
  remediation step before declaring success.
- **R5**: After a successful `mission create` JSON payload, no trailing
  shutdown/sync error lines (red or otherwise) MAY be printed in the same
  command invocation.
- **R6**: A single command invocation MUST print at most one
  "token refresh failed" / "not authenticated, skipping sync" diagnostic
  per failure cause (deduplication scoped to the command session, not the
  process tree).
- **R7**: Release metadata across `pyproject.toml`, `CHANGELOG.md`,
  `.python-version`, and the release-prep test fixtures MUST be internally
  consistent. The dogfood/release tests are the executable form of this
  invariant.
- **R8**: `mission_step_contracts/executor.py` MUST pass `mypy --strict`.

## Functional Requirements

| ID     | Requirement | Linked Issue | Status |
|--------|-------------|--------------|--------|
| FR-001 | Loosen `.python-version` to a constraint compatible with the active local development environment AND restore `mypy --strict` cleanliness for `src/specify_cli/mission_step_contracts/executor.py`. | [#805](https://github.com/Priivacy-ai/spec-kitty/issues/805) | Proposed |
| FR-002 | Fix the dev-worktree `spec-kitty upgrade` version-mismatch behavior so that the CLI binary version, `.kittify/metadata.yaml` `spec_kitty.version`, and `spec_kitty.schema_version` are mutually consistent after a successful `upgrade` run, and so that downstream `spec-kitty agent ...` commands stop being blocked by `PROJECT_MIGRATION_NEEDED` when `upgrade` reported success. | [#705](https://github.com/Priivacy-ai/spec-kitty/issues/705) | Proposed |
| FR-003 | Remove the `/spec-kitty.checklist` slash command from every generated user-facing command surface (slash-command and skills agents), from source templates, from the registry/command renderer/command installer, from the shim registry, from upgrade migrations that recreate it, and from regression baselines and snapshot fixtures. The `kitty-specs/<mission>/checklists/requirements.md` artifact MUST still be created by `/spec-kitty.specify`. | [#815](https://github.com/Priivacy-ai/spec-kitty/issues/815) | Proposed |
| FR-004 | Resolve the older `/spec-kitty.checklist` deprecation ticket as superseded by FR-003 (or close as resolved when FR-003 lands), with an explicit comment linking the two issues. | [#635](https://github.com/Priivacy-ai/spec-kitty/issues/635) | Proposed |
| FR-005 | When `spec-kitty init` is run in a directory that is not a git repository, the command MUST instruct the user to run `git init` (or equivalent) before retrying, with the exact wording approved during plan. The command MUST NOT silently corrupt or partially populate the directory in this case. | [#636](https://github.com/Priivacy-ai/spec-kitty/issues/636) | Proposed |
| FR-006 | Hide legacy `--feature` aliases from `--help` output across all CLI subcommands while preserving their accept-and-route behavior unchanged. | [#790](https://github.com/Priivacy-ai/spec-kitty/issues/790) | Proposed |
| FR-007 | Clarify the `spec-kitty agent decision` command shape so that the path documented in `docs/reference/missions.md`, `docs/reference/slash-commands.md`, the `specify`/`plan` skill snapshots, and `--help` output all match the canonical command path. EITHER add an alias for the documented shape OR update the docs/help to point at the existing canonical path; one consistent answer end-to-end. | [#774](https://github.com/Priivacy-ai/spec-kitty/issues/774) | Proposed |
| FR-008 | Suppress misleading final-sync / shutdown error lines printed after a successful `spec-kitty agent mission create` JSON payload. Successful invocation MUST end with the JSON payload (and any explicitly informational lines), not with red error output. | [#735](https://github.com/Priivacy-ai/spec-kitty/issues/735) | Proposed |
| FR-009 | Deduplicate repeated token-refresh / "not authenticated, skipping sync" failure messages so that each distinct cause prints at most once per command invocation. | [#717](https://github.com/Priivacy-ai/spec-kitty/issues/717) | Proposed |
| FR-010 | `read_events()` in `src/specify_cli/status/store.py` MUST tolerate non-lane-transition events (e.g. `DecisionPointOpened`, `DecisionPointResolved`, and any other top-level `event_type`-discriminated mission-level event) in `status.events.jsonl` instead of raising `KeyError('wp_id')`. Effect: every CLI command that reads the event log (`finalize-tasks`, `materialize`, `reduce`, dashboard, doctor) keeps working on missions that have used the Decision Moment Protocol. Discovered live during `/spec-kitty.tasks` for this mission; new GitHub issue to be filed at PR time. | (new issue, file at PR time) | Proposed |

## Non-Functional Requirements

| ID      | Requirement | Threshold | Status |
|---------|-------------|-----------|--------|
| NFR-001 | Mission-step contract type-safety: `mypy --strict` on `src/specify_cli/mission_step_contracts/executor.py` (and any sibling contract modules touched by the tranche) returns zero errors. | 0 mypy errors | Proposed |
| NFR-002 | Release metadata coherence: `pyproject.toml::[project].version`, `CHANGELOG.md` next-version heading, `.python-version`, and the release-prep test fixtures (`tests/release/test_dogfood_command_set.py`, `tests/release/test_release_prep.py`) all agree on the next prerelease state. | 100% test pass under `tests/release/` | Proposed |
| NFR-003 | CLI surface diff after FR-003: zero references to `/spec-kitty.checklist` in any agent-rendered command surface (slash-command + skills agents), verified by a regression test that scans the rendered output of every supported agent. | 0 occurrences across all 15 supported agents (CLAUDE.md "Supported AI Agents" table) | Proposed |
| NFR-004 | `mission create` final output cleanliness: the last line of stdout for a successful JSON-mode invocation is the closing `}` of the JSON payload (or an explicit single informational line). No red error output after success. | 0 trailing error lines on success | Proposed |
| NFR-005 | Token-refresh / sync diagnostic deduplication: each distinct failure cause prints at most once per CLI invocation. | ≤1 occurrence per cause per invocation | Proposed |
| NFR-006 | `spec-kitty upgrade` success/state coherence: after `spec-kitty upgrade` reports `Upgrade complete!`, immediately running `spec-kitty agent mission branch-context --json` MUST succeed (no `PROJECT_MIGRATION_NEEDED` block). | 0 false-success cases in regression suite | Proposed |
| NFR-007 | Help-output footprint for legacy aliases: `--feature` does not appear in any `--help` output across the CLI; existing call sites that pass `--feature` continue to work without warning. | 0 `--help` mentions; 100% acceptance retention | Proposed |
| NFR-008 | Documentation/help/skill-snapshot consistency for `spec-kitty agent decision`: every operator-facing path resolves to the same canonical command shape. | 0 contradictions between docs, help, and skill snapshots | Proposed |
| NFR-009 | Bulk-edit gate compliance for FR-003: `/spec-kitty.plan` produces an `occurrence_map.yaml` covering every file that mentions `/spec-kitty.checklist` (or the deprecated `checklist.md` template), classifying each occurrence as remove vs keep. DIRECTIVE_035 enforcement passes. | 100% classified, 0 unclassified occurrences | Proposed |
| NFR-010 | Status event reader robustness: `read_events()` returns successfully for every `status.events.jsonl` that contains zero or more lane-transition events plus zero or more mission-level events (DecisionPoint family, retrospective, future event types). | 0 KeyError on any well-formed event log; per-event-type unit coverage | Proposed |

## Constraints

| ID    | Constraint | Source | Status |
|-------|------------|--------|--------|
| C-001 | Stabilization-only tranche: no new product features may be introduced. | `start-here.md` "Local Rules" / Mission scope | Proposed |
| C-002 | All changes land on `release/3.2.0a5-tranche-1` and merge into the same branch (final integration into `main` is handled outside this mission). | `start-here.md` "Branch" + Branch contract from `mission branch-context` | Proposed |
| C-003 | The canonical `kitty-specs/<mission>/checklists/requirements.md` artifact created by `/spec-kitty.specify` MUST NOT be removed or renamed. Only the standalone `/spec-kitty.checklist` slash command surface is retired. | `start-here.md` "Important boundary for #815" | Proposed |
| C-004 | Existing call sites that pass `--feature` MUST continue to work after FR-006. No deprecation warning may be printed unless explicitly approved during plan. | `start-here.md` "Feature alias hiding" | Proposed |
| C-005 | Only edit sources under `src/specify_cli/missions/*/command-templates/` and related source modules; never edit generated agent copies under `.claude/`, `.amazonq/`, `.codex/`, etc. (per `CLAUDE.md` "Template Source Location"). | `CLAUDE.md` (project guideline) | Proposed |
| C-006 | If implementation proves SaaS/tracker integration is required, clone the missing repos into the workspace per `start-here.md`; do not reuse existing local checkouts under `~/ClaudeCowork/Spec-Kitty-Cowork`. | `start-here.md` "Local Rules" | Proposed |
| C-007 | Hosted-auth / tracker / SaaS / sync / websocket commands run during this tranche must be invoked with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. | `start-here.md` "Local Rules" | Proposed |
| C-008 | DIRECTIVE_035 (cross-file rename gate) must hold for the FR-003 bulk edit; an `occurrence_map.yaml` is required during plan. | Charter doctrine + `meta.json::change_mode = bulk_edit` | Proposed |

## Key Entities

- **Project metadata** (`.kittify/metadata.yaml`) — `spec_kitty.version`,
  `spec_kitty.schema_version`, `spec_kitty.last_upgraded_at`, migration
  ledger. Authoritative source for the `compat/planner.py` gate.
- **Release metadata** — `pyproject.toml::[project].version`, `CHANGELOG.md`,
  `.python-version`, fixtures referenced from `tests/release/`.
- **Slash-command source templates** —
  `src/specify_cli/missions/<mission_type>/command-templates/*.md`. Edited
  here, copied out to per-agent surfaces.
- **Skills source templates** — Source files that the command renderer
  installs into `.agents/skills/spec-kitty.<command>/SKILL.md` for Codex /
  Vibe.
- **Agent command-surface registry** —
  `src/specify_cli/skills/registry.py`,
  `src/specify_cli/skills/command_renderer.py`,
  `src/specify_cli/skills/command_installer.py`,
  `src/specify_cli/shims/registry.py`. Determines what gets rendered for
  every supported agent.
- **Upgrade migrations** —
  `src/specify_cli/upgrade/migrations/`. Drives schema-version stamping and
  template propagation; FR-002 root-cause likely lives in
  `runner.py::_stamp_schema_version` + `metadata.save`.
- **Sync / auth diagnostics** — `src/specify_cli/auth/`, `src/specify_cli/sync/`.
  Source of FR-008 / FR-009 noise.

## Assumptions

- `release/3.2.0a5-tranche-1` is the correct landing branch and is intended
  to be a long-lived release branch for this tranche only (confirmed by
  `mission branch-context`: `branch_matches_target = true`).
- The active maintainer's local environment uses Python 3.14.0 and `uv`;
  FR-001's `.python-version` loosening targets a constraint that includes
  3.14 without dropping the contributor floor (decided during plan).
- "Hidden alias" semantics for `--feature` follow Typer's standard `hidden=True`
  pattern (decided during plan).
- The decision-command "clarify or alias" choice in FR-007 is a planning-time
  decision; either branch satisfies the requirement so long as docs, help, and
  skill snapshots all agree afterwards.
- The `/spec-kitty.checklist` removal is purely additive-to-deprecate: once
  removed, no compatibility shim is needed. Any user invoking
  `/spec-kitty.checklist` will get a "command not found" from their agent,
  which is the desired terminal state.

## Success Criteria

- **SC-001** — A maintainer can run the dogfood command-set test and the
  release-prep test and have them both pass on
  `release/3.2.0a5-tranche-1` in under 60 seconds, with `/spec-kitty.checklist`
  gone from every rendered agent surface and `requirements.md` still produced.
- **SC-002** — `spec-kitty --help`, `spec-kitty agent --help`,
  `spec-kitty agent decision --help`, and `spec-kitty init --help` produce
  output that contains zero references to the legacy `--feature` alias and
  zero contradictions about the decision command shape, verified by a single
  regression test.
- **SC-003** — Running `spec-kitty agent mission create ...` once produces
  exactly one valid JSON payload on stdout and zero red error/diagnostic
  lines after it. Verified by a CLI smoke test.
- **SC-004** — Running `spec-kitty upgrade` followed immediately by any
  `spec-kitty agent ...` command succeeds with no `PROJECT_MIGRATION_NEEDED`
  block, in 100% of regression-suite invocations.
- **SC-005** — A new user attempting `spec-kitty init` in a non-git
  directory sees an actionable "run `git init`" message within one CLI
  invocation, with no partially-populated `.kittify/` left behind.
- **SC-006** — Each issue in the tranche (#805, #705, #815, #635, #636,
  #790, #774, #735, #717) is closed with a link either to (a) a regression
  test added in this tranche, or (b) explicit "already fixed on `main` —
  regression test added at `<path>`" evidence per `start-here.md` "Done
  Criteria".
- **SC-007** — A first-time operator who follows
  `start-here.md` end-to-end on a fresh clone of
  `release/3.2.0a5-tranche-1` reaches a green `mission create` and a clean
  `--help` surface without manually editing `.kittify/metadata.yaml` or
  consulting any out-of-tree workaround.
- **SC-008** — A mission that has used the Decision Moment Protocol
  (`spec-kitty agent decision open`) successfully runs every downstream
  command that calls `read_events()` (`finalize-tasks`, `materialize`,
  `reduce`, dashboard, doctor) without `KeyError('wp_id')`.

## Dependencies

- Charter doctrine (`DIRECTIVE_003`, `DIRECTIVE_010`, and `DIRECTIVE_035`
  for the bulk edit) — already loaded during specify bootstrap.
- `requirements-validation-workflow` and `premortem-risk-identification`
  tactics from charter context — to be applied during `/spec-kitty.plan`.
- The `spec-kitty-bulk-edit-classification` skill — to be loaded by the
  agent driving `/spec-kitty.plan` so the occurrence map is produced
  correctly for FR-003.
- No external SaaS / tracker integration is assumed; if needed, repos must
  be cloned per C-006.

## Open Items (deferred to plan)

None requiring `[NEEDS CLARIFICATION]` markers. Two planning-time decisions
are explicitly noted above:

1. FR-001 / `.python-version` loosening shape (e.g. minimum Python version,
   range, or unpinning entirely) — decided during plan based on the
   maintainer's environment.
2. FR-007 alias-vs-doc-fix decision for `spec-kitty agent decision` — decided
   during plan based on the canonical command path that exists today.

Both are normal planning decisions; they do not block specification readiness.
