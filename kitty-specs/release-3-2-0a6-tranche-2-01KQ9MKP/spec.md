# Mission Spec: 3.2.0a6 Tranche 2 Bug Cleanup

**Mission ID**: `01KQ9MKPYMT1528C6VH6B8BT67`
**Mission Slug**: `release-3-2-0a6-tranche-2-01KQ9MKP`
**Mission Type**: software-dev
**Target Branch**: `release/3.2.0a6-tranche-2`
**Created**: 2026-04-28

## Purpose

**TLDR**: Fix seven blocker bugs in 3.2.0a6 covering fresh-project setup, `--json` output integrity, agent identity parsing, review-cycle counters, invocation lifecycle, and charter generate/validate parity.

**Context**: PR #837 closed Tranche 1 of the 3.2.0a6 release. This bug-only mission addresses Tranche 2: seven defects across init metadata stamping, `--json` command output, WP agent string parsing, review-cycle accounting, profile-invocation lifecycle records on `next`, and charter `generate`/`synthesize`/`validate` parity. Together they restore the documented golden path (`init` → charter `setup`/`generate`/`synthesize` → `next`) so it works on a fresh project without manual metadata or doctrine seeding, ensure strict `json.loads(stdout)` on covered `--json` commands even when SaaS sync fails or is unauthorized, preserve tool/model/profile/role across WP resolution and prompt generation, and stop spurious review-cycle inflation on reclaim/regenerate flows.

## Stakeholders & Actors

- **Operator (primary)**: a developer running Spec Kitty CLI commands against a fresh or existing project. Wants the documented golden path to work without hand-edits.
- **External tooling**: scripts and CI pipelines that consume `--json` stdout via `json.loads`. Cannot tolerate non-JSON noise on stdout.
- **Coding agent**: a Claude / Codex / etc. process driven by `spec-kitty implement` and `spec-kitty review`. Needs accurate `tool:model:profile:role` identity carried through prompts.
- **Reviewer (human or LLM)**: drives review verdicts; only their **rejections** should advance review-cycle counters.

## Domain Language

Canonical terms used in this spec; do not substitute synonyms.

| Canonical term | Definition | Avoid |
|---|---|---|
| **Fresh project** | A project initialized via `spec-kitty init` with no manual edits to `.kittify/` afterwards. | "new project", "blank repo" (when precision matters) |
| **Strict JSON** | The exact contract that `json.loads(stdout)` succeeds on the unmodified stdout stream of a `--json` command. | "valid JSON", "parseable output" |
| **JSON envelope** | The single top-level JSON object emitted by a `--json` command. Diagnostics may live inside this object but never outside it. | "JSON wrapper", "result object" |
| **Resolved agent identity** | The 4-tuple (`tool`, `model`, `profile_id`, `role`) carried by a work package after `WPMetadata.resolved_agent()` runs. | "agent string", "agent name" |
| **Review cycle** | An integer counter that advances exactly once per genuine review **rejection** of a work package. | "review pass", "review iteration" (those refer to the artifact, not the counter) |
| **Profile-invocation lifecycle record** | A paired (started, completed) local record written by `spec-kitty next` when it issues or advances a public action. | "invocation log", "next event" |
| **Charter bundle parity** | The invariant that a charter produced by `charter generate` is accepted by `charter bundle validate` without manual git staging. | "charter sync", "charter coherence" |

## User Scenarios & Testing

Each scenario is anchored to one of the seven defects. The "primary path" walks the operator from a clean state through the fix; the "exception path" covers the most common branch.

### Scenario 1 — Fresh init stamps schema metadata (Issue #840)

- **Primary actor**: Operator on a fresh project.
- **Trigger**: `spec-kitty init` completes; operator immediately runs the next CLI command without touching `.kittify/metadata.yaml`.
- **Success outcome**: `.kittify/metadata.yaml` contains a non-empty `schema_version` and a `schema_capabilities` block compatible with the runtime; downstream commands (`charter setup`, `next`) start without raising "missing schema" errors.
- **Exception path**: If `init` runs against a directory that already has a `metadata.yaml`, the existing schema fields are preserved (no overwrite of operator-authored values).

### Scenario 2 — `--json` stdout stays strict under SaaS sync failure (Issue #842)

- **Primary actor**: Script or CI consumer.
- **Trigger**: Consumer pipes `spec-kitty agent mission create --json` (or any `--json` command) into `json.loads`; SaaS sync is unavailable, unauthorized, or disabled.
- **Success outcome**: `json.loads(stdout)` succeeds. Sync/auth diagnostics appear on stderr or are nested inside the JSON envelope under a `diagnostics` (or equivalent) key — never as bare lines on stdout.
- **Exception path**: When `SPEC_KITTY_ENABLE_SAAS_SYNC=1` is set and SaaS is reachable, behavior is unchanged from the success path; sync diagnostics still do not appear on stdout outside the envelope.

### Scenario 3 — Colon-format `--agent` preserves model/profile/role (Issue #833)

- **Primary actor**: Operator launching an implement step.
- **Trigger**: Operator runs `spec-kitty agent action implement WP01 --agent claude:opus-4-7:reviewer-default:reviewer`.
- **Success outcome**: `WPMetadata.resolved_agent()` returns a 4-tuple where `tool="claude"`, `model="opus-4-7"`, `profile_id="reviewer-default"`, `role="reviewer"`; the implement and review prompts reflect all four fields.
- **Exception path**: A partial string (`claude:opus-4-7`) preserves `tool` and `model` and falls back to default `profile_id` and `role`, with no silent discard. Bare strings (`claude`) preserve current single-token fallback.

### Scenario 4 — Review-cycle counter advances only on real rejections (Issue #676)

- **Primary actor**: Operator (or orchestrator) re-running implement on a reclaimed WP.
- **Trigger**: After a WP enters `for_review`, the operator runs `spec-kitty agent action implement WPNN` again to regenerate the implement prompt without the reviewer having issued a rejection.
- **Success outcome**: The review-cycle counter for that WP is unchanged; no new `review-cycle-N.md` artifact is written.
- **Exception path**: When the reviewer issues an actual rejection, the counter advances by exactly one and exactly one new `review-cycle-N.md` is created.

### Scenario 5 — `next` writes lifecycle records (Issue #843)

- **Primary actor**: Coding agent running the canonical `spec-kitty next --agent <name>` loop.
- **Trigger**: `next` issues an action (e.g., `step=implement`) and later advances past it.
- **Success outcome**: A pair of local records exists for that issuance — one `started` and one `completed` — keyed to the same canonical action identifier; the `action` field on each record matches the mission step/action that `next` actually issued.
- **Exception path**: If the agent stops between `started` and `completed`, the next invocation does not silently overwrite the orphan; the orphan is observable to `doctor`-style tooling.

### Scenario 6 — Charter generate/validate parity on a fresh project (Issue #841)

- **Primary actor**: Operator running the documented governance setup flow on a fresh project.
- **Trigger**: `spec-kitty charter generate` succeeds.
- **Success outcome**: The very next `spec-kitty charter bundle validate` call also succeeds — without the operator needing to `git add charter.md` between the two commands. The product behavior is **`generate` auto-tracks the produced `charter.md`** (Assumption A1).
- **Exception path**: If `generate` cannot auto-track (e.g., not a git repo), it fails with a clear, actionable error that names the specific remediation (initialize git, or run a documented offline path), instead of silently producing a state that `validate` will reject.

### Scenario 7 — Charter synthesize works on a fresh project (Issue #839)

- **Primary actor**: Operator running the golden-path `init → charter setup/generate/synthesize → next` flow.
- **Trigger**: On a fresh project where `.kittify/doctrine/` has **not** been hand-seeded, the operator runs `spec-kitty charter synthesize`.
- **Success outcome**: The public CLI path completes successfully and writes whatever doctrine artifacts the runtime needs; subsequent commands do not require additional manual seeding (Assumption A2).
- **Exception path**: The E2E test at `tests/e2e/test_charter_epic_golden_path.py` exercises this flow without hand-seeding `.kittify/doctrine/` and passes; any required offline/test adapter is documented.

### Always-true rules (rule probing)

- A `--json` command never emits stdout that fails strict JSON parsing under any SaaS state.
- An identity transformation (parse → resolve → re-emit) of an agent string never silently drops fields.
- The review-cycle counter for a WP is monotonic and changes exactly once per real rejection event.
- A `next` issuance and its completion share the same canonical action identifier.

## Functional Requirements

| ID | Requirement | Status |
|---|---|---|
| FR-001 | `spec-kitty init` MUST stamp `schema_version` and a `schema_capabilities` block in `.kittify/metadata.yaml` so a fresh project does not require hand edits to that file before subsequent CLI commands. | Active |
| FR-002 | If `metadata.yaml` already exists at `init` time, existing schema fields MUST be preserved unmodified; the stamp MUST be additive, not destructive. | Active |
| FR-003 | All covered `--json` commands MUST produce stdout that is strict-JSON-parseable (`json.loads(stdout)` succeeds) regardless of SaaS sync state (disabled, unauthorized, network failure, or success). | Active |
| FR-004 | Sync, auth, and tracker diagnostics MUST be routed to stderr OR nested inside the JSON envelope under a documented key; they MUST NOT appear as bare text lines on stdout outside the envelope. | Active |
| FR-005 | `WPMetadata.resolved_agent()` MUST parse colon-delimited agent strings of the form `tool:model:profile_id:role` into a 4-tuple preserving every supplied field. | Active |
| FR-006 | Partial colon strings (e.g., `tool:model`, `tool`) MUST fall back deterministically to documented defaults for missing fields, with no silent discard of supplied fields. | Active |
| FR-007 | The implement and review prompt-generation flows MUST consume the 4-tuple from `resolved_agent()` end-to-end, so `model`, `profile_id`, and `role` are visible in the rendered prompt context. | Active |
| FR-008 | Re-running `spec-kitty agent action implement WPNN` (reclaim / regenerate) MUST be idempotent with respect to review state: it MUST NOT advance the review-cycle counter and MUST NOT create a new `review-cycle-N.md`. | Active |
| FR-009 | The review-cycle counter for a WP MUST advance exactly once when, and only when, a reviewer issues a real rejection event for that WP. | Active |
| FR-010 | A real rejection MUST create exactly one new `review-cycle-N.md` artifact whose `N` matches the post-increment counter value. | Active |
| FR-011 | `spec-kitty next` MUST write a `started` profile-invocation lifecycle record at the moment it issues a public action, and a paired `completed` record when that action advances. | Active |
| FR-012 | The `action` field on each lifecycle record MUST equal the canonical mission step/action identifier that `next` issued; mismatched pairs MUST be rejected by validation rather than silently accepted. | Active |
| FR-013 | `spec-kitty charter generate` MUST produce an artifact set that `spec-kitty charter bundle validate` accepts on the same fresh project, with no manual `git add` between the two commands. | Active |
| FR-014 | `charter generate` MUST auto-track its produced `charter.md` (Assumption A1). If auto-tracking is not possible (e.g., not a git repo), `generate` MUST fail with an actionable error that names the remediation. | Active |
| FR-015 | `spec-kitty charter synthesize` MUST run successfully on a fresh project (no hand-seeded `.kittify/doctrine/`) via a public CLI path. | Active |
| FR-016 | The golden-path E2E `tests/e2e/test_charter_epic_golden_path.py` MUST exercise the `init → charter setup → charter generate → charter synthesize → next` flow without hand-seeding `.kittify/doctrine/` and without manually editing `.kittify/metadata.yaml`. | Active |
| FR-017 | Documentation describing the governance setup flow MUST match the CLI invariant chosen for FR-013/FR-014; any documented step that becomes redundant (e.g., a manual `git add`) MUST be removed. | Active |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|---|---|---|---|
| NFR-001 | Strict JSON contract: `json.loads(stdout)` succeeds for every covered `--json` command across the full SaaS state matrix (disabled, unauthorized, network-failed, authorized-success). | Pass rate: 100% across all four states for every covered command. | Active |
| NFR-002 | Test coverage for new or modified code paths in this mission. | ≥ 90% line coverage on changed modules per the project's pytest+coverage gate (matches charter policy). | Active |
| NFR-003 | Type checking on changed code. | `mypy --strict` passes with zero new errors on touched modules. | Active |
| NFR-004 | Regression coverage for agent identity parsing. | ≥ 1 unit test per supported colon arity (1, 2, 3, 4 segments) plus an end-to-end test that asserts `model`, `profile_id`, and `role` appear in a rendered prompt. | Active |
| NFR-005 | Review-cycle idempotency proof. | A test re-runs `implement` ≥ 3 times against a `for_review` WP and asserts the counter and `review-cycle-N.md` filesystem are unchanged across all runs. | Active |
| NFR-006 | Lifecycle-pairing proof. | A test asserts that for any `started` record, exactly one `completed` (or explicit failure) record exists with the same canonical action identifier across ≥ 5 issued actions. | Active |
| NFR-007 | Golden-path E2E runtime budget. | The fresh-project golden-path E2E completes in under 120 seconds on CI (no hand seeding, no manual `git add`). | Active |
| NFR-008 | Backward compatibility for pre-existing projects. | Running `init` against a project that already had a hand-edited `metadata.yaml` produces no field-value diff on existing keys (excluding the additive stamp). | Active |

## Constraints

| ID | Constraint | Status |
|---|---|---|
| C-001 | Scope is bug-only. New charter product features, new auth flows, new tracker intake features, and dashboard/frontend work are out of scope unless strictly required to fix one of the listed issues. | Active |
| C-002 | All work merges into `release/3.2.0a6-tranche-2`; no direct landing on `main`. | Active |
| C-003 | Any local CLI invocation that touches SaaS, tracker, hosted auth, or sync flows on this developer machine MUST set `SPEC_KITTY_ENABLE_SAAS_SYNC=1` per the machine-level AGENTS.md. | Active |
| C-004 | Identity fields in `meta.json` (`mission_id`, `slug`, `mission_slug`, `created_at`, `target_branch`) MUST NOT be modified by any work in this mission. `mission_number` is display-only and MUST remain `null` pre-merge. | Active |
| C-005 | The mission must not introduce a separate "test-only" code path for fresh-project charter synthesize; the public CLI is the canonical path (Assumption A2). | Active |
| C-006 | Stack policy from charter doctrine applies: typer (CLI), rich (console), ruamel.yaml (frontmatter), pytest (test), mypy strict (type check). No new top-level runtime dependencies. | Active |
| C-007 | The shared package boundary (events, tracker as external PyPI; runtime CLI-internal) MUST NOT be re-violated. Use `spec_kitty_events.*` and `spec_kitty_tracker.*` public imports only. | Active |
| C-008 | Out of scope for this tranche: #771 stale-lane auto-rebase, #726/#728/#729 intake papercuts, #303/#662/#595 CI/Sonar/release-readiness, #260/#253/#631/#630/#629/#644/#323/#317 rc compatibility cleanup. | Active |

## Key Entities

- **Project metadata file** (`.kittify/metadata.yaml`): YAML document carrying `schema_version` and `schema_capabilities`; consumed by runtime/migration code; written by `init`.
- **Resolved agent identity**: 4-tuple (`tool`, `model`, `profile_id`, `role`) attached to a work package; produced by `WPMetadata.resolved_agent()`; consumed by implement/review prompt rendering.
- **Review-cycle counter**: integer per WP; backed by review-cycle artifacts (`review-cycle-N.md`); advances only on rejection events.
- **Profile-invocation lifecycle record**: local JSON/YAML record per (issuance, completion); keyed by a canonical action identifier shared across the pair.
- **Charter bundle**: artifact set produced by `charter generate` and validated by `charter bundle validate`; lives under `.kittify/charter/` and must be in a state that the validator accepts.
- **Charter doctrine**: artifacts under `.kittify/doctrine/` (procedures, tactics, directives, guidelines) consumed by action-scoped charter context.

## Success Criteria

Measurable, technology-agnostic outcomes. Each is independently verifiable.

- **SC-001 (Fresh-path completion)**: An operator completes the entire fresh-project golden path (`init → charter setup → charter generate → charter synthesize → next`) on a previously empty directory **without** editing any file under `.kittify/` by hand and **without** running any `git add` against charter outputs.
- **SC-002 (JSON parsability)**: For every covered `--json` command, an external script that calls `json.loads(stdout)` succeeds in 100% of trials across the four SaaS states (disabled, unauthorized, network-failed, authorized-success). No retries, no stripping, no preprocessing.
- **SC-003 (Identity preservation rate)**: For agent strings supplied with all four colon segments, the implement and review prompts reflect the supplied `model`, `profile_id`, and `role` values in 100% of cases (no silent discards).
- **SC-004 (Review-cycle precision)**: Across ≥ 10 simulated reclaim/regenerate runs in a controlled test, the review-cycle counter changes 0 times when there is no real rejection, and exactly 1 time per real rejection.
- **SC-005 (Lifecycle observability)**: For ≥ 95% of issued public `next` actions, both `started` and `completed` lifecycle records exist with matching canonical action identifiers; orphan `started` records are observable rather than silently overwritten.
- **SC-006 (Charter parity rate)**: On a fresh project, `charter generate` followed immediately by `charter bundle validate` succeeds in 100% of runs without intervening manual git operations.
- **SC-007 (Documentation/CLI agreement)**: A human reading the documented governance setup flow can complete it verbatim on a fresh project with zero deviation from the documented commands.
- **SC-008 (Bug-only discipline)**: The diff for this mission introduces zero new public CLI subcommands and zero new top-level runtime dependencies.

## Assumptions

- **A1 (Charter generate auto-tracks)**: For Issue #841, the chosen product behavior is that `charter generate` auto-tracks its produced `charter.md` so that `charter bundle validate` succeeds without a manual `git add`. This aligns with the tranche-level acceptance criterion that fresh paths must not require manual metadata or doctrine seeding. The alternate behavior (fail with a clear actionable state) is reserved for explicitly non-git environments.
- **A2 (Public CLI synthesize on fresh project)**: For Issue #839, the chosen product behavior is that the **public CLI** `spec-kitty charter synthesize` works on a fresh project. We do not introduce a parallel "offline/test adapter" code path; the golden-path E2E exercises the same public surface real users hit.
- **A3 (Covered `--json` commands)**: The set of `--json` commands explicitly exercised by tests (mission CRUD, status, charter context, decision moment, action commands, etc.) is the contract surface for FR-003/FR-004. Any `--json` flag added to a command outside this set is brought under the strict-JSON contract by adding a regression test, not by relaxing the rule.
- **A4 (Local SaaS toggle)**: All local SaaS-touching test invocations in this tranche are run with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` per machine-level AGENTS.md.
- **A5 (Mission identity model)**: This mission relies on the post-083 ULID-based identity model (`mission_id` + `mid8`); `mission_number` remains display-only. No code in this tranche reads `mission_number` as identity.
- **A6 (No new dependencies)**: Fixes are achievable within the existing dependency set declared in `pyproject.toml`. If a fix appears to require a new dependency, that is a signal to revisit the design before adding it.

## Out of Scope

- Issue #771 (stale-lane auto-rebase) — only addressed if it directly blocks this tranche's merge.
- Intake papercuts: #726, #728, #729.
- CI / Sonar / release-readiness cost cleanup: #303, #662, #595.
- RC compatibility cleanup: #260, #253, #631, #630, #629, #644, #323, #317.
- New product features in any of the touched areas (charter, JSON commands, agent identity, review pipeline, invocation lifecycle).
- Frontend / dashboard work.
- New auth flows or tracker intake features.

## References

- GitHub release epic: https://github.com/Priivacy-ai/spec-kitty/issues/822
- Tranche 1 PR: https://github.com/Priivacy-ai/spec-kitty/pull/837
- Prior stabilization PR: https://github.com/Priivacy-ai/spec-kitty/pull/803
- Issues in scope: #840, #842, #833, #676, #843, #841, #839
- Likely implementation files (informational, not normative):
  - `src/specify_cli/status/wp_metadata.py` (#833)
  - `src/specify_cli/cli/commands/init.py`, `src/specify_cli/migration/runner.py` (#840)
  - `src/specify_cli/sync/`, `src/specify_cli/auth/transport.py`, JSON command wrappers (#842)
  - `src/specify_cli/cli/commands/agent/`, review-cycle handling paths (#676)
  - `src/specify_cli/invocation/`, `src/specify_cli/cli/commands/advise.py`, runtime/next plumbing (#843)
  - `tests/e2e/test_charter_epic_golden_path.py` (#839/#840/#841/#842/#843)
