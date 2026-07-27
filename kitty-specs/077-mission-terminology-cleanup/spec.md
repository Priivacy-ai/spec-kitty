# Mission Specification: Mission Terminology Cleanup and Machine-Facing Alignment

| Field | Value |
|---|---|
| Mission Slug | `077-mission-terminology-cleanup` |
| Mission Type | `software-dev` |
| Friendly Name | Mission terminology cleanup and machine-facing alignment |
| Target Branch | `main` |
| Created | 2026-04-08 |
| Validated Baseline (`spec-kitty`) | `54269f7c131a5efc40b729d412de26f6b05c65fb` |
| Validated Baseline (`spec-kitty-events`) | `5b8e6dc39da0fc0ad37de41fd576111ea542cf36` |
| Authoritative ADR | `architecture/2.x/adr/2026-04-04-2-mission-type-mission-and-mission-run-terminology-boundary.md` |
| Authoritative Initiative | `architecture/2.x/initiatives/2026-04-mission-nomenclature-reconciliation/README.md` |
| Tracks Issues | `Priivacy-ai/spec-kitty#241` (immediate), `Priivacy-ai/spec-kitty#543` (gated follow-on) |

---

## 1. Problem Statement

Spec Kitty's terminology layer is settled at the architecture level but has not landed at the surface level. The accepted ADR `2026-04-04-2-mission-type-mission-and-mission-run-terminology-boundary.md` and the published `spec-kitty-events 3.0.0` contract both lock in a single canonical model:

- **Mission Type** — reusable workflow blueprint (`software-dev`, `research`, `documentation`).
- **Mission** — concrete tracked item under `kitty-specs/<mission-slug>/`. Identified by `mission_slug`.
- **Mission Run** — runtime/session execution instance only. Identified by `mission_run_id`.
- **Feature** — software-dev compatibility alias only, scheduled for deprecation.

Despite that decision, the `spec-kitty` CLI, doctrine skills, public docs, and several test surfaces still teach and accept the wrong nouns for tracked-mission selection. Specifically:

- Tracked-mission CLI selectors are still implemented as a multi-alias parameter (`"--mission", "--mission-run", "--feature"` on the same option), which breaks the canonical boundary in three different directions at once.
- Help text still labels tracked-mission selectors as "Mission run slug", actively teaching users the wrong layer.
- Doctrine skills and explanation docs still instruct agents to pass `--mission-run` to select tracked missions.
- The dual-flag conflict case (`--mission X --feature Y` with different values) is silently resolved by "last value wins" because typer's alias semantics never raise. Users get a different mission than they asked for, with no warning.
- The orchestrator-api contract tests already reject `--feature` and the orchestrator-api code is already canonical `--mission`-only with a fixed 7-key envelope. The main CLI still accepts `--feature` as a co-equal alias with no deprecation behavior. The repo currently ships split behavior between two of its own surfaces; the reconciliation direction is to bring the main CLI toward the orchestrator-api's strictness, not the other way around.
- Machine-facing legacy `feature_*` field names persist in some places even though the upstream `spec-kitty-events 3.0.0` contract is already canonical on `mission_slug`, `mission_number`, `mission_type`, `MissionCreated`, and `MissionClosed`.

The cost of leaving this unresolved is concrete:

1. Agents and operators learn the wrong selector vocabulary from official docs and skills, then have to be re-taught every time the CLI or orchestrator-api drifts.
2. Resolution behavior under dual-flag conflict is non-deterministic from the user's perspective, which makes scripts and automation silently dangerous.
3. The contradiction between main CLI and orchestrator-api creates ongoing support friction and prevents any single canonical example from being correct in both places.
4. Machine-facing surfaces that still emit `feature_*` fields force every downstream consumer (orchestrator, SaaS, hub, tracker, runtime, events projections, dashboards) to maintain dual-shape parsing forever instead of converging on the published `spec-kitty-events 3.0.0` contract.

This mission resolves the operator-facing terminology drift first (`#241`), then performs the gated machine-facing alignment cleanup (`#543`) once `#241` has landed. It does **not** rename `Mission` to `MissionRun`, does **not** introduce `mission_run_slug`, does **not** rename `MissionCreated` / `MissionClosed`, and does **not** rename `kitty-specs/*/` directories. Those directions are explicitly out of scope and would require a new ADR and a new cross-repo contract decision.

## 2. Sequencing

This mission has two distinct, ordered scopes. They are deliberately not merged into a single rename program.

### Scope A — Issue `#241`: Operator-Facing Selector Cleanup (Immediate)

`#241` is the immediate implementation scope. It addresses the surfaces an operator or agent touches directly: CLI flags, CLI help text, doctrine skills, agent-facing docs, runtime-loop documentation, and the test surface that pins selector behavior. Scope A must be complete and accepted before Scope B begins.

### Scope B — Issue `#543`: Machine-Facing Contract Alignment (Gated Follow-On)

`#543` is a gated follow-on. It addresses machine-facing surfaces that still emit or accept legacy `feature_*` payload fields, internal command names that still describe the tracked mission as a "feature", and any first-party contract that has not yet aligned with `spec-kitty-events 3.0.0`. Scope B may not begin until Scope A's acceptance gates have passed, because Scope A is what gives operators a stable canonical vocabulary to reason about Scope B against.

### Sequencing Rule

Work packages for Scope B may be planned in parallel with Scope A, but they must not be merged or accepted until Scope A's acceptance gates are green. The intent is to remove all ambiguity at the operator surface first, then reduce machine-facing churn against a stable vocabulary.

## 3. Canonical Model (Locked — Do Not Renegotiate)

The implementing team must treat the following as fixed inputs and may not rediscover them during planning or implementation. Any deviation requires a new ADR.

### 3.1 Domain Vocabulary

| Canonical term | Layer | Identifier field |
|---|---|---|
| `Mission Type` | Reusable blueprint | `mission_type` |
| `Mission` | Concrete tracked item under `kitty-specs/<mission-slug>/` | `mission_slug`, `mission_number` |
| `Mission Run` | Runtime/session execution instance | `mission_run_id` |
| `Work Package` | Planning/review slice inside a mission | `wp_id` |
| `Feature` | Software-dev compatibility alias for `Mission` | (deprecated) |

### 3.2 Canonical Selector Rules

| Selector | Canonical meaning | Status |
|---|---|---|
| `--mission` | Tracked mission slug | Canonical |
| `--mission-type` | Reusable blueprint / template | Canonical |
| `--mission-run` | Runtime/session selector only | Canonical (runtime-only) |
| `--feature` | Compatibility alias for `--mission` on legacy software-dev surfaces | Deprecated, removable after migration window |

### 3.3 Non-Goals (Locked)

The implementing team **must not** propose, plan, or land any of the following. These are explicit non-goals and are listed here so they cannot be reintroduced under the guise of "consistency".

- ❌ Make `--mission-run` the canonical selector for tracked-mission selection.
- ❌ Rename `mission_slug` → `mission_run_slug`.
- ❌ Rename `MissionCreated` → `MissionRunCreated`.
- ❌ Rename `MissionClosed` → `MissionRunClosed`.
- ❌ Change `aggregate_type="Mission"` → `aggregate_type="MissionRun"`.
- ❌ Rename any `kitty-specs/*/` directory or restructure the on-disk mission layout.
- ❌ Introduce a new `mission_run_slug` field anywhere in any first-party contract.

If any contributor or reviewer requests a change in any of the above directions, the correct response is "that requires a new ADR and a new cross-repo contract decision". This mission must not perform that work, even partially, and must not leave behind any code path that makes those changes easier to ship later.

## 4. User Scenarios and Testing

### 4.1 Scenario A — Operator Selects a Tracked Mission Correctly

**Actor:** Spec Kitty operator.

**Given** a repository with multiple missions under `kitty-specs/`,
**When** the operator runs any tracked-mission command with `--mission <slug>`,
**Then** the command resolves the requested mission, executes against it, and prints help text and examples that only use `--mission` for tracked-mission selection.

### 4.2 Scenario B — Agent Reads a Doctrine Skill and Picks the Right Selector

**Actor:** AI coding agent following a doctrine skill.

**Given** an agent loads a Spec Kitty doctrine skill that explains how to pick a tracked mission,
**When** the agent reads the skill,
**Then** every example, every command snippet, and every prose reference uses `--mission` for tracked-mission selection. No skill instructs the agent to use `--mission-run` for tracked-mission selection.

### 4.3 Scenario C — Operator Uses the Deprecated `--feature` Alias

**Actor:** Spec Kitty operator running a legacy automation script.

**Given** a script that still passes `--feature <slug>` to a tracked-mission command,
**When** the script runs during the migration window,
**Then** the command still executes correctly, but stderr emits exactly one explicit deprecation warning per invocation that names the canonical replacement (`--mission`) and points to the migration policy. The exit code is unchanged from the canonical equivalent.

### 4.4 Scenario D — Operator Passes Conflicting `--mission` and `--feature` Values

**Actor:** Spec Kitty operator (or buggy automation).

**Given** an operator runs a tracked-mission command with `--mission A --feature B` where `A != B`,
**When** the command parses arguments,
**Then** the command fails fast with a deterministic non-zero exit, prints a clear conflict error that names both flags and both values, and does **not** silently resolve to either value. This behavior is consistent across every tracked-mission command surface in the main CLI.

### 4.5 Scenario E — Runtime/Session Selector Stays Runtime-Only

**Actor:** Operator inspecting a runtime/session.

**Given** an operator runs a runtime/session command with `--mission-run <run-id>`,
**When** the command parses arguments,
**Then** the command resolves a runtime/session instance, never a tracked mission slug, and the help text says so explicitly. Any tracked-mission command that today still accepts `--mission-run` as an alias for tracked-mission selection rejects it (or, during the migration window, emits a deprecation warning that points to `--mission`).

### 4.6 Scenario F — Main CLI and Orchestrator-API Reconcile in the Tightening Direction

**Actor:** Integrator wiring CI to either the main CLI or the orchestrator-api.

**Given** the integrator writes a script that targets a tracked mission,
**When** they run the same logical command via the main CLI and via the orchestrator-api,
**Then** both surfaces accept `--mission` as canonical. The orchestrator-api rejects `--feature` outright (unchanged from today). The main CLI accepts `--feature` as a deprecated alias during the migration window with a single stderr deprecation warning per invocation. The reconciliation direction is to bring the main CLI toward the orchestrator-api's strictness, **never** the other way around: the orchestrator-api's 7-key envelope is not widened, and no `--feature` alias or deprecation field is reintroduced to it.

### 4.7 Scenario G — Machine-Facing Consumer Reads Mission Identity (Scope B)

**Actor:** First-party machine-facing consumer (runtime, events projections, orchestrator, SaaS, hub, tracker, dashboard).

**Given** a consumer reads tracked-mission identity from any first-party Spec Kitty payload after Scope B lands,
**When** the consumer parses the payload,
**Then** `mission_slug`, `mission_number`, and `mission_type` are present and canonical, and any `feature_*` field that remains is either gone, dual-written behind an explicit compatibility alias gate, or marked deprecated with a documented removal date. No new `mission_run_slug` field is introduced.

### 4.8 Edge Cases

- An operator passes `--mission` with no value → existing typer required-value error, unchanged.
- An operator passes `--mission A --mission B` (same flag twice) → typer's standard "last value wins" is acceptable (this is a single-flag duplication, not a cross-alias conflict). Acceptance does not regress this case.
- An operator passes `--feature` against a command that has *never* accepted it → command rejects with a clear "unknown option" error, unchanged from current behavior.
- An operator passes `--mission-run X` to a runtime command on a slug that does not match any runtime/session → existing not-found behavior, unchanged.
- An operator passes `--mission` to a command that genuinely is a mission-type selector (e.g., creating a new mission of a given type) → command must reject `--mission` with a clear "did you mean `--mission-type`?" error. This is the inverse of the bug in Scope A and must not be reintroduced.

## 5. Functional Requirements

| ID | Requirement | Status |
|---|---|---|
| FR-001 | Every tracked-mission command surface in the main CLI accepts `--mission <slug>` as the canonical selector. | Required |
| FR-002 | No tracked-mission command surface in the main CLI lists `--mission-run` as an alias for tracked-mission selection. | Required |
| FR-003 | `--mission-run` is reserved exclusively for runtime/session selectors and is documented as such in every help string where it appears. | Required |
| FR-004 | `--mission-type` is the canonical selector wherever the argument is the reusable blueprint or template, and no surface uses bare `--mission` to mean blueprint selection. The verified inverse-drift sites in §8.1 are converted to `--mission-type` (with `--mission` accepted only as a hidden deprecated alias on those sites during the migration window, mirroring the §11 policy applied in the inverse direction). | Required |
| FR-005 | `--feature` is accepted only as a hidden deprecated compatibility alias on tracked-mission commands during the migration window, and emits exactly one explicit deprecation warning per invocation. | Required |
| FR-006 | Passing `--mission X` and `--feature Y` with different values to the same tracked-mission command fails deterministically with a non-zero exit and a conflict error that names both flags and both values. | Required |
| FR-007 | Passing `--mission X` and `--feature X` with the same value succeeds, but still emits the deprecation warning for `--feature`. | Required |
| FR-008 | All tracked-mission help strings that previously read "Mission run slug" now read "Mission slug" (or an equivalent canonical phrasing) and reference `--mission` first. | Required |
| FR-009 | All Spec Kitty doctrine skills that instruct agents how to select a tracked mission use `--mission` as the canonical selector and contain no instruction to use `--mission-run` for tracked-mission selection. | Required |
| FR-010 | All Spec Kitty agent-facing explanation docs (including the runtime-loop doc) teach `--mission` as the canonical tracked-mission selector and remove any teaching of `--mission-run` for tracked-mission selection. | Required |
| FR-011 | The behavior of `mission current` is identical across all selector forms: it accepts `--mission`, accepts `--feature` with a deprecation warning, rejects the dual-flag conflict from FR-006, and never resolves a "last alias wins" outcome. | Required |
| FR-012 | The split between main CLI and orchestrator-api selector behavior is closed by bringing the main CLI toward the orchestrator-api's strict canonical-only state, not by relaxing the orchestrator-api. Both surfaces accept `--mission` as canonical. The orchestrator-api continues to reject `--feature` outright; the main CLI accepts `--feature` only as a deprecated alias during the migration window (per §11). The orchestrator-api's existing 7-key envelope (`src/specify_cli/orchestrator_api/envelope.py`) is not widened, no structured `deprecation` field is added to it, and no `--feature` alias is reintroduced to its commands. | Required |
| FR-013 | A migration/deprecation note for `--feature` is published in user-facing docs and references the canonical replacement, the deprecation window, and the planned removal criteria. | Required |
| FR-014 | (Scope B) `mission_slug`, `mission_number`, and `mission_type` are present and canonical in every first-party machine-facing payload that identifies a tracked mission. | Required |
| FR-015 | (Scope B) Any remaining `feature_slug` or `feature_*` field in a first-party machine-facing surface is either removed, dual-written behind an explicit compatibility alias gate, or explicitly marked deprecated with a documented removal date. | Required |
| FR-016 | (Scope B) First-party machine-facing contracts align with the published `spec-kitty-events 3.0.0` field naming and event names. | Required |
| FR-017 | (Scope B) `MissionCreated` and `MissionClosed` remain the canonical catalog event names; no rename to `MissionRunCreated` / `MissionRunClosed` is performed. | Required |
| FR-018 | (Scope B) Runtime/session identifiers (`mission_run_id`) remain runtime-only and never appear as canonical tracked-mission identity in any first-party contract. | Required |
| FR-019 | (Scope B) No new `mission_run_slug` field is introduced anywhere in any first-party contract. | Required |
| FR-020 | (Scope B) `kitty-specs/*/` directory layout is unchanged. | Required |
| FR-021 | Every site in §8.1.2 (Inverse Drift Sites) where `--mission` currently means "blueprint/template selector" is converted so the canonical form is `--mission-type`. The literal flag `--mission` is retained on those sites only as a deprecated alias for `--mission-type` during the migration window, with the same single-warning behavior as §11. | Required |
| FR-022 | The CI grep guards introduced for FR-009 / FR-010 apply only to live first-party surfaces (`src/doctrine/skills/**`, `docs/**`, top-level `README.md`, `CONTRIBUTING.md`, and `CHANGELOG.md`). They explicitly exclude `kitty-specs/**` (historical mission artifacts), `architecture/**` (historical ADRs and initiative records), `CHANGELOG`-style historical entries, and the `.kittify/` runtime state. Historical mission specs may freely retain legacy selector vocabulary; rewriting them is not in scope. | Required |

## 6. Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|---|---|---|---|
| NFR-001 | Selector resolution overhead introduced by deterministic conflict detection adds no measurable latency to command startup. | < 5ms p95 added to `mission current` cold start vs validated baseline. | Required |
| NFR-002 | The deprecation warning for `--feature` is emitted at most once per invocation per tracked-mission command. | Exactly 1 warning per invocation when `--feature` is used. | Required |
| NFR-003 | The deprecation warning is suppressible by an explicit opt-in environment variable for legacy CI consumers, but is not silently disabled by default. | `SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION=1` documented and honored. | Required |
| NFR-004 | Documentation and skill updates do not introduce broken internal links. | 0 broken internal links in updated docs and skills (validated by existing link checker). | Required |
| NFR-005 | Test coverage for canonical selectors, alias deprecation, and dual-flag conflict is at least 90% on the touched modules. | ≥ 90% line coverage on modified `cli/commands/*.py` and `agent/tasks.py` tracked-mission selector paths. | Required |
| NFR-006 | (Scope B) Machine-facing contract changes do not silently break any existing first-party consumer that follows the published `spec-kitty-events 3.0.0` contract. | 0 breakages observed in cross-repo first-party consumer test fixtures. | Required |

## 7. Constraints

| ID | Constraint | Status |
|---|---|---|
| C-001 | The implementation must not perform any action listed in §3.3 (Non-Goals). | Locked |
| C-002 | The implementation must not rename or restructure any directory under `kitty-specs/`. | Locked |
| C-003 | The implementation must not change the published `spec-kitty-events 3.0.0` event names or aggregate types. | Locked |
| C-004 | Scope B work packages must not merge until all Scope A acceptance gates have passed. | Locked |
| C-005 | The migration window for `--feature` must be defined explicitly in user-facing docs, with named conditions for removal. The removal itself is out of scope for this mission. | Locked |
| C-006 | The implementation must not introduce a new `mission_run_slug` field, even in compatibility shims. | Locked |
| C-007 | All tests added by this mission must use only canonical selectors (`--mission`, `--mission-type`, `--mission-run` for runtime). Compatibility-alias tests must explicitly assert deprecation behavior, not normal operation. | Locked |
| C-008 | No code path may be added that makes a future `Mission → MissionRun` rename "easier" (e.g., abstract base classes, parallel field shadows, or aggregate-type indirection). | Locked |
| C-009 | The mission must not introduce a backward-compatibility shim for `mission_run_slug` because no such field has ever existed. | Locked |
| C-010 | The orchestrator-api's fixed 7-key envelope in `src/specify_cli/orchestrator_api/envelope.py` must not be widened by this mission. No new top-level keys, no structured deprecation field, no alias-warning channel. The orchestrator-api stays canonical-only. | Locked |
| C-011 | No work in this mission may rewrite, edit, or "modernize" historical mission artifacts under `kitty-specs/**` (other than this mission's own `077-mission-terminology-cleanup/` directory) or under `architecture/**`. Historical artifacts are append-only history and are excluded from grep gates by FR-022. | Locked |

## 8. Verified Drift and Bugs (Inputs to Planning)

The following drift and bug list is the validated baseline for planning. The implementing team should treat each item as a known-bad starting state, not as something to rediscover.

### 8.1 Drift Sites

#### 8.1.1 Tracked-Mission Selector Drift (`--mission-run` and `--feature` used for tracked-mission selection)

- `src/specify_cli/cli/commands/next_cmd.py:33` — tracked-mission selector is declared as `typer.Option("--mission", "--mission-run", "--feature", help="Mission slug")`. The canonical violation here is that `--mission-run` appears as an alias for tracked-mission selection, and `--feature` is a co-equal alias with no deprecation behavior.
- `src/specify_cli/cli/commands/next_cmd.py:48` — example help text reads `spec-kitty next --agent codex --mission-run 034-my-feature`, actively teaching the wrong selector.
- `src/specify_cli/cli/commands/agent/tasks.py` (lines 842, 1389, 1572, 1655, 1726, 1945, 2205, 2295, 2659) — every tracked-mission selector in this file declares `typer.Option("--mission", "--mission-run", help="Mission run slug")`. Both the alias list and the help string are wrong.
- `src/specify_cli/cli/commands/mission.py:172-194` — `mission current` declares `typer.Option(None, "--mission", "--feature", "-f", help="Mission slug")`. Because typer collapses multi-alias options to a single parameter with last-value-wins semantics, passing `--mission A --feature B` silently resolves to `B`. This is the verified dual-flag bug for FR-006.
- `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` — instructs agents to use `--mission-run` for tracked-mission selection.
- `docs/explanation/runtime-loop.md` — teaches legacy selectors for tracked-mission selection.

#### 8.1.2 Inverse Drift Sites (`--mission` used to mean blueprint/template)

These sites are the *inverse* of the tracked-mission drift: the literal flag `--mission` is wired to a parameter that semantically means "mission type / blueprint / template". By the canonical model in §3, that parameter must be `--mission-type`. WPA2b owns this fix.

- `src/specify_cli/cli/commands/agent/mission.py:488` — `agent mission create` declares `mission: Annotated[str | None, typer.Option("--mission", help="Mission type (e.g., 'documentation', 'software-dev')")]`. The literal flag should be `--mission-type`; `--mission` should be retained only as a deprecated alias.
- `src/specify_cli/cli/commands/charter.py:67` — `charter interview` declares `mission: str = typer.Option("software-dev", "--mission", help="Mission key for charter defaults")`. The literal flag should be `--mission-type`; `--mission` should be retained only as a deprecated alias.
- `src/specify_cli/cli/commands/lifecycle.py:27` — `lifecycle.specify` declares `mission: Optional[str] = typer.Option(None, "--mission", help="Mission type (e.g., software-dev, research)")`. The literal flag should be `--mission-type`; `--mission` should be retained only as a deprecated alias.

#### 8.1.3 Cross-Surface Split

- The orchestrator-api code at `src/specify_cli/orchestrator_api/commands.py:437` already uses `--mission` exclusively (no aliases) and is contract-tested to reject `--feature` at `tests/contract/test_orchestrator_api.py:164`. The orchestrator-api's response envelope is fixed to 7 keys at `src/specify_cli/orchestrator_api/envelope.py:49`. The split between main CLI and orchestrator-api is real, but the **direction of reconciliation is to bring the main CLI toward the orchestrator-api's strictness**, not the other way around. The orchestrator-api is the canonical reference state for tracked-mission selectors and must not be relaxed or widened by this mission (C-010).

### 8.2 Verified Behavior Bug

- `mission current --mission A --feature B` (different values) does not produce a conflict error. Resolution is "last alias wins" because all aliases share one parameter. The user gets a different mission than they asked for, with no warning. This must be encoded as a regression test asserting the new deterministic conflict behavior from FR-006.

### 8.3 Verified Blast Radius (Inputs to Planning)

| Area | Surface | Mention count |
|---|---|---|
| `src/specify_cli/**` | files mentioning `--feature` | 16 |
| `src/specify_cli/**` | files mentioning `mission-run` | 7 |
| `tests/**` | test files mentioning either | 24 |
| Repo-wide Markdown | files mentioning `feature_slug`, `--feature`, or `--mission-run` | 299 |

### 8.4 Verified Upstream Contract Facts (`spec-kitty-events`)

These facts constrain the plan and must not be re-litigated:

- `mission_slug`, `mission_number`, and `mission_type` are canonical fields in `spec-kitty-events 3.0.0`.
- `MissionCreated` and `MissionClosed` are canonical catalog event names.
- Runtime-only `MissionRun*` event names exist and are intentionally separate; they must stay runtime-only.
- Scan results at validation time: `mission_slug` appears in 110 files in `spec-kitty-events`; `mission_run_slug` appears in 0; `MissionCreated` appears in 15; `MissionRunCreated` appears in 0.

## 9. Blast Radius by Area

### 9.1 Scope A — `#241`

| Area | Representative surfaces | Expected change kind |
|---|---|---|
| Main CLI — tracked-mission selectors | `src/specify_cli/cli/commands/next_cmd.py`, `src/specify_cli/cli/commands/mission.py`, `src/specify_cli/cli/commands/agent/tasks.py`, other tracked-mission command modules in `src/specify_cli/cli/commands/**` | Replace multi-alias declarations with canonical `--mission` + explicit `--feature` deprecation alias. Add deterministic dual-flag conflict detection. |
| Main CLI — help text | All `Option(..., help=...)` strings on tracked-mission selectors | Replace "Mission run slug" with canonical phrasing. |
| Doctrine skills | `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md`, other doctrine skills under `src/doctrine/skills/**` that teach selector usage | Replace `--mission-run` instruction with `--mission` for tracked-mission selection. |
| Agent-facing docs | `docs/explanation/runtime-loop.md`, other explanation docs that teach selectors | Replace legacy selector teaching with canonical selectors. |
| Reference docs | `docs/reference/cli-commands.md`, `docs/reference/agent-subcommands.md` if present | Update help-text snippets and examples. |
| Tests — contract | `tests/contract/test_orchestrator_api.py` (no behavior change — assertions remain that `--feature` is rejected) and **new** parallel main-CLI contract tests | Confirm orchestrator-api stays canonical-only and unchanged. Add main-CLI canonical/alias/conflict assertions on the human-facing side. Tighten the main CLI toward the orchestrator-api, do not relax the orchestrator-api. |
| Tests — unit and integration | Tests in `tests/specify_cli/cli/commands/**` and `tests/contract/**` that touch tracked-mission selectors and inverse-drift selectors | Add coverage for FR-001..FR-013 and FR-021, including the dual-flag conflict regression for both directions. |
| Migration policy doc | New short doc page or addition to existing migration notes | Document `--feature` deprecation window and removal criteria. |

### 9.2 Scope B — `#543`

| Area | Representative surfaces | Expected change kind |
|---|---|---|
| Internal command names | Anywhere a first-party command or method still says `feature` for the tracked-mission concept | Rename to `mission` (or compatibility-gate explicitly), without touching aggregate types or directory layout. |
| Machine-facing payloads | Output payloads from `src/specify_cli/agent/**`, `src/specify_cli/orchestrator_api/**`, status emitters, and any first-party JSON producer | Ensure `mission_slug` / `mission_number` / `mission_type` are canonical. Compatibility-gate or remove residual `feature_*` fields. |
| Status events | `status.events.jsonl` schema and `status/*` modules | No change to `aggregate_type="Mission"`. Confirm field naming is canonical. |
| Catalog event names | Anywhere `MissionCreated` / `MissionClosed` appear | No rename. |
| Cross-repo contract docs | `docs/reference/event-envelope.md`, `docs/reference/orchestrator-api.md`, `COMPATIBILITY.md` if present | Align with `spec-kitty-events 3.0.0` and document the alias window. |

## 10. Acceptance Criteria

### 10.1 Scope A — `#241`

Scope A is accepted when **all** of the following are true:

1. `rg --type py "(--mission-run|mission-run)" src/specify_cli/cli/commands` returns no result for tracked-mission selector definitions. Any remaining matches must be in genuine runtime/session contexts and must be explicitly validated by the reviewer.
2. `rg --type py "Mission run slug" src/specify_cli/cli/commands` returns zero matches.
3. `mission current --mission A --feature B` exits non-zero with a deterministic conflict error that names both flags and both values. Asserted by a regression test.
4. `mission current --feature X` succeeds, resolves the same mission as `mission current --mission X`, and emits exactly one deprecation warning to stderr that names `--mission` as the canonical replacement.
5. `mission current --feature X` exits with the same exit code as `mission current --mission X` when both succeed.
6. `mission current --mission X --feature X` succeeds and still emits the deprecation warning exactly once.
7. Every tracked-mission command surface in the main CLI passes the same canonical/alias/conflict assertions.
8. Every Spec Kitty doctrine skill under `src/doctrine/skills/**` that mentions tracked-mission selection uses `--mission` and contains no instruction to use `--mission-run` for tracked-mission selection. Verified by an automated grep in CI scoped to `src/doctrine/skills/**` only. Historical mission artifacts under `kitty-specs/**` and `architecture/**` are explicitly out of scope for this gate (per FR-022, C-011).
9. `docs/explanation/runtime-loop.md` and other agent-facing explanation docs under `docs/**` teach `--mission` as the canonical tracked-mission selector and contain no `--mission-run` instruction for tracked-mission selection. Verified by an automated grep in CI scoped to `docs/**` only.
10. The orchestrator-api remains canonical-only: `src/specify_cli/orchestrator_api/commands.py` continues to declare `--mission` without aliases, `tests/contract/test_orchestrator_api.py` continues to assert `--feature` is rejected, and `src/specify_cli/orchestrator_api/envelope.py` is unchanged (still 7 keys, no new structured deprecation field). The main CLI is brought into alignment with this state by adopting `--mission` as canonical and `--feature` as a deprecated alias. The split is closed by tightening the main CLI, not by relaxing the orchestrator-api.
11. A migration/deprecation policy for `--feature` is published in user-facing docs and is referenced from main-CLI deprecation warnings.
12. CI is green on all touched modules with ≥ 90% coverage on modified selector paths (NFR-005).
13. None of the §3.3 non-goals appear in the diff. Verified by reviewer checklist.
14. Each site in §8.1.2 (Inverse Drift Sites) — `agent/mission.py:488`, `charter.py:67`, `lifecycle.py:27` — has been converted so the canonical literal flag is `--mission-type`, with `--mission` retained only as a deprecated alias on those sites. Asserted by tests covering: (a) `--mission-type X` succeeds; (b) `--mission X` succeeds and emits exactly one deprecation warning naming `--mission-type`; (c) `--mission-type A --mission B` (different values) fails deterministically.
15. No file under `kitty-specs/**` (other than `077-mission-terminology-cleanup/`) or under `architecture/**` is modified by this mission's diff. Verified by reviewer checklist and by C-011.

### 10.2 Scope B — `#543`

Scope B is accepted when **all** of the following are true (and only after Scope A is accepted):

1. Every first-party machine-facing payload identifying a tracked mission carries `mission_slug`, `mission_number`, and `mission_type` as canonical fields.
2. Any remaining `feature_*` field is either removed, gated behind an explicit compatibility alias declaration, or marked deprecated with a documented removal date in the contract docs.
3. No first-party machine-facing surface introduces or accepts `mission_run_slug`.
4. `MissionCreated` and `MissionClosed` remain the canonical catalog event names. No rename anywhere.
5. `aggregate_type="Mission"` remains unchanged.
6. The first-party machine-facing surfaces match the field naming and event names published in `spec-kitty-events 3.0.0`.
7. The compatibility alias window for any remaining `feature_*` fields is documented in one place and referenced from the contract docs.
8. CI is green and cross-repo first-party consumer fixtures show 0 breakages (NFR-006).
9. None of the §3.3 non-goals appear in the diff.

## 11. Migration and Deprecation Policy for `--feature`

This policy is part of the spec because it is a user-facing contract, not an implementation detail.

### 11.1 During the Migration Window

The migration policy is **deliberately asymmetric** between the human-facing main CLI and the machine-facing orchestrator-api. The main CLI gets a transitional deprecation window because real human users have real legacy scripts. The orchestrator-api stays strict because it is a machine-facing contract with a fixed envelope and no legitimate need for transitional warnings — its consumers either match the canonical contract or they fail loudly.

**Main CLI (`src/specify_cli/cli/commands/**`)**:

- `--feature` is accepted as a hidden compatibility alias on every tracked-mission command surface (that is: declared with `typer.Option(..., hidden=True)` and not advertised in `--help`, examples, tutorials, or docs).
- Every invocation that uses `--feature` emits exactly one deprecation warning to stderr. The warning names `--mission` as the canonical replacement and links to the migration policy doc.
- Passing `--mission` and `--feature` with different values is a deterministic error (FR-006). Passing them with the same value succeeds with the warning still emitted (FR-007).
- The deprecation warning is suppressible via an opt-in environment variable (`SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION=1`) for legacy CI consumers that cannot tolerate stderr noise during the cutover. The default behavior is to emit the warning.
- The same single-warning, deterministic-conflict, opt-in-suppression policy applies in the inverse direction (FR-021) for the inverse-drift sites in §8.1.2: `--mission` is accepted only as a hidden deprecated alias for `--mission-type`, with the warning suppressible by `SPEC_KITTY_SUPPRESS_MISSION_TYPE_DEPRECATION=1`.

**Orchestrator-api (`src/specify_cli/orchestrator_api/**`)**:

- `--feature` remains rejected outright. No deprecation alias, no warning, no structured deprecation field.
- The 7-key envelope is unchanged. C-010 forbids widening it.
- The orchestrator-api is the canonical reference state and the rest of the codebase is brought toward it, not the other way around.
- Rationale: machine-facing contracts must be strict by default. A deprecation window on the orchestrator-api would introduce a new top-level envelope key (or stderr noise that JSON consumers can't see), and would create exactly the kind of long-lived compatibility shim this mission exists to remove.

### 11.2 Removal Criteria (Out of Scope for This Mission)

This mission does not remove `--feature`. It defines the conditions under which removal becomes appropriate:

- All first-party doctrine skills, agent-facing docs, examples, tutorials, and reference docs use `--mission`.
- All first-party machine-facing surfaces have completed Scope B.
- A documented telemetry or audit window has elapsed during which legacy `--feature` usage in first-party CI fixtures is zero.

The decision to actually remove `--feature` is a separate change that must reference this policy and the conditions above. This mission must not perform that removal.

## 12. Test Strategy

### 12.1 Selector Behavior Tests (Scope A)

For every tracked-mission command surface touched by Scope A, add tests that assert:

1. **Canonical**: `<command> --mission <slug>` resolves the expected mission and exits 0.
2. **Alias deprecation**: `<command> --feature <slug>` resolves the same mission, exits 0, and emits exactly one deprecation warning to stderr.
3. **Same-value compatibility**: `<command> --mission <slug> --feature <slug>` exits 0 and still emits the deprecation warning.
4. **Conflict (regression for the verified bug)**: `<command> --mission A --feature B` exits non-zero with a conflict error that names both flags and both values.
5. **Runtime selector reject**: `<command> --mission-run <something>` is rejected (or, during the migration window, emits a deprecation warning that points to `--mission`). The exact behavior depends on whether the command historically accepted `--mission-run` as a tracked-mission alias.
6. **Inverse reject**: For commands whose canonical selector is `--mission-type`, passing `--mission` is rejected with a "did you mean `--mission-type`?" error.
7. **Suppression env var**: With `SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION=1` set, `<command> --feature <slug>` succeeds and emits no deprecation warning.

### 12.2 Documentation and Skill Tests (Scope A)

The grep guards in this section are scoped to **live first-party surfaces only**. They explicitly exclude `kitty-specs/**` (historical mission artifacts), `architecture/**` (historical ADRs and initiative records), and `.kittify/` runtime state. See FR-022 and C-011.

- Add a CI grep check that fails the build if any file under `src/doctrine/skills/**` or `docs/**` instructs use of `--mission-run` for tracked-mission selection. The check must not scan `kitty-specs/**` or `architecture/**`.
- Add a CI grep check that fails the build if any tracked-mission CLI help string in `src/specify_cli/cli/commands/**` contains the phrase "Mission run slug".
- Add a CI grep check that fails the build if any file under `src/doctrine/skills/**` or `docs/**` instructs use of `--mission` (without `-type`) where the surrounding context is mission-type / blueprint / template selection. This guards FR-021.
- The grep guards must be implementable as small `rg --type-add` invocations or as a single dedicated test in `tests/contract/`. They are not allowed to require manual enumeration of historical files.

### 12.3 Cross-Surface Reconciliation Tests (Scope A)

The orchestrator-api and the main CLI do **not** behave identically during the migration window. The orchestrator-api is strict; the main CLI has a transitional deprecation window. Tests must reflect this asymmetry.

- The existing assertions in `tests/contract/test_orchestrator_api.py` that `--mission` is canonical and `--feature` is rejected stay as they are. No regression and no relaxation.
- Add a new contract test that asserts `src/specify_cli/orchestrator_api/envelope.py` still produces a 7-key envelope with the documented key set, to fail loudly if any future work attempts to widen it (C-010).
- Add new main-CLI contract tests that assert the canonical/alias/deprecation-warning/conflict behavior for every tracked-mission command surface in the main CLI. These tests are net-new and live alongside the existing orchestrator-api contract tests; they do not share fixtures with them.
- Document in test docstrings that the asymmetry is intentional and references §11.1.

### 12.4 Machine-Facing Contract Tests (Scope B)

- Add contract tests against representative first-party machine-facing payloads that assert `mission_slug`, `mission_number`, and `mission_type` are present and canonical.
- Add a contract test that fails if any first-party payload introduces `mission_run_slug`.
- Add a contract test that fails if any first-party catalog event is renamed away from `MissionCreated` / `MissionClosed`.
- Add cross-repo first-party consumer fixtures (or extend existing ones) to validate NFR-006.

### 12.5 No-Regression Tests for Non-Goals

Add reviewer-checklist items and, where automatable, CI grep checks to ensure none of the §3.3 non-goals appear in the diff:

- Reject `mission_run_slug` anywhere in source.
- Reject renames of `MissionCreated` / `MissionClosed` / `aggregate_type="Mission"`.
- Reject any change to the `kitty-specs/*/` directory layout.

## 13. Work Package Outline

These work packages are an outline for `/spec-kitty.plan` and `/spec-kitty.tasks` to refine. Sequencing constraints from §2 apply.

### 13.1 Scope A Work Packages (`#241` — Immediate)

- **WPA1 — Selector Audit and Canonical Map.** Inventory every tracked-mission selector site and every blueprint/template selector site in `src/specify_cli/cli/commands/**`. Produce a canonical map: which file, which command, which current alias list, what the parameter actually means semantically (tracked mission slug vs mission type), which target alias list. Use the §8.1.1 and §8.1.2 inventories as the verified starting state. Output is the input to WPA2a and WPA2b.
- **WPA2a — Tracked-Mission Selector Refactor.** Replace every tracked-mission selector declaration with `--mission` as canonical and `--feature` as deprecated alias. Remove `--mission-run` from tracked-mission selector alias lists. Update help strings to canonical phrasing. Covers all sites in §8.1.1.
- **WPA2b — Inverse Drift Refactor (`--mission` → `--mission-type`).** For each site in §8.1.2 (`agent/mission.py:488`, `charter.py:67`, `lifecycle.py:27`, plus any additional sites discovered in WPA1), convert the literal flag to `--mission-type` as canonical and retain `--mission` only as a deprecated alias. Wire each through the same selector-resolution helper introduced in WPA3, parameterized for the inverse direction. Apply FR-021 acceptance tests to each site.
- **WPA3 — Deterministic Dual-Flag Conflict Handling.** Introduce a small selector-resolution helper that rejects `--mission X --feature Y` (and, in the inverse direction, `--mission-type A --mission B`) with a deterministic conflict error and accepts the same-value case with a deprecation warning. Wire every tracked-mission and mission-type command surface through this helper.
- **WPA4 — Deprecation Warning Plumbing.** Implement the single-warning-per-invocation deprecation emit, including the `SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION=1` opt-in suppression for the `--feature` direction and `SPEC_KITTY_SUPPRESS_MISSION_TYPE_DEPRECATION=1` for the inverse direction. Route all relevant commands through it.
- **WPA5 — `mission current` Behavior Fix.** Resolve the verified bug in `mission current` (last-alias-wins). Add the regression test from §12.1 case 4.
- **WPA6 — Doctrine Skills Cleanup.** Update `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` and any other doctrine skill that teaches tracked-mission selection to use `--mission`. Add the CI grep check from §12.2 scoped to `src/doctrine/skills/**` only — historical mission artifacts under `kitty-specs/**` are out of scope (FR-022, C-011).
- **WPA7 — Agent-Facing Docs Cleanup.** Update `docs/explanation/runtime-loop.md` and any other explanation doc under `docs/**` that teaches tracked-mission selectors. Add the CI grep check from §12.2 scoped to `docs/**` only — historical mission artifacts and `architecture/**` are out of scope (FR-022, C-011).
- **WPA8 — Cross-Surface Alignment (Tightening Direction Only).** Bring the main CLI selector behavior into alignment with the orchestrator-api's existing canonical state. Do not relax the orchestrator-api. Do not widen the orchestrator-api envelope (C-010). Confirm `tests/contract/test_orchestrator_api.py` continues to assert `--feature` is rejected and that `src/specify_cli/orchestrator_api/envelope.py` is unchanged. Add parallel main-CLI contract tests that assert the canonical/alias/conflict behavior on the human-facing side.
- **WPA9 — Migration Policy Documentation.** Publish the §11 migration/deprecation policy (asymmetric: main CLI has window, orchestrator-api stays strict) in user-facing docs and reference it from the main-CLI deprecation warning text.
- **WPA10 — Scope A Acceptance Gate.** Run the full §10.1 acceptance criteria, capture evidence, and gate Scope B on its completion.

### 13.2 Scope B Work Packages (`#543` — Gated Follow-On)

- **WPB1 — Machine-Facing Inventory.** Inventory every first-party machine-facing surface that emits or accepts tracked-mission identity. Identify residual `feature_*` fields. Output is the input to WPB2.
- **WPB2 — Canonical Field Rollout.** Ensure `mission_slug`, `mission_number`, and `mission_type` are present and canonical on every first-party machine-facing payload identifying a tracked mission.
- **WPB3 — Compatibility Gate or Removal for `feature_*` Fields.** For each residual `feature_*` field, decide remove / dual-write / deprecate, and execute. Document the decision in the contract docs. Do not introduce `mission_run_slug`.
- **WPB4 — Contract Docs Alignment.** Update `docs/reference/event-envelope.md`, `docs/reference/orchestrator-api.md`, and any compatibility doc to match `spec-kitty-events 3.0.0` and the alias window.
- **WPB5 — Cross-Repo Consumer Validation.** Run cross-repo first-party consumer fixtures (or extend existing ones) and verify NFR-006.
- **WPB6 — Scope B Acceptance Gate.** Run the full §10.2 acceptance criteria and capture evidence.

## 14. Assumptions

- The published `spec-kitty-events 3.0.0` contract is stable for the duration of this mission and will not introduce a competing field rename. (Validated at commit `5b8e6dc39da0fc0ad37de41fd576111ea542cf36`.)
- Typer's option declaration semantics are unchanged: declaring multiple alias strings on a single `Option(...)` collapses them to one parameter with last-value-wins resolution. This is the verified mechanism behind the dual-flag bug, and the fix must move conflict detection out of the declaration and into a small post-parse resolution helper.
- The orchestrator-api surface is already canonical and is treated as the reference state. The selector-resolution helper introduced in WPA3 lives in the main CLI surface. The orchestrator-api does not consume the helper because it does not need a deprecation window (per §11.1, C-010).
- The `--feature` deprecation warning's text and link target are user-visible product copy and may be subject to a writing pass during implementation. The behavioral acceptance criteria do not depend on the exact wording.
- Existing tests that today pass `--mission-run` to tracked-mission commands are themselves drift artifacts and will be updated as part of WPA2 / WPA8, not preserved as compatibility tests.

## 15. Open Questions

The user's brief explicitly asked for open questions only when they are real and still unresolved after reading the ADR and issue bodies. The following are the only such questions identified:

1. **Q1 — Migration window length signaling.** This mission's policy says removal of `--feature` is out of scope and conditional on telemetry. Should the deprecation warning include an explicit "no earlier than" date, or only the named conditions? **Recommended default:** named conditions only, because dates have a way of becoming load-bearing when they were meant to be aspirational. Confirm during planning.
2. **Q2 — Suppression env var naming.** NFR-003 names `SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION=1` and §11.1 names `SPEC_KITTY_SUPPRESS_MISSION_TYPE_DEPRECATION=1`. If either conflicts with an existing Spec Kitty env var convention discovered during planning, the implementing team may rename them, but the behavior (single env var per direction, opt-in, default off) is fixed. Confirm during planning.
3. **Q3 — Inverse-drift suppression scope.** FR-021 + §11.1 introduce a parallel deprecation window for `--mission` → `--mission-type` on the three sites in §8.1.2. Is the second env var (`SPEC_KITTY_SUPPRESS_MISSION_TYPE_DEPRECATION=1`) genuinely needed, or is one combined env var (`SPEC_KITTY_SUPPRESS_TERMINOLOGY_DEPRECATIONS=1`) acceptable? **Recommended default:** two distinct env vars, because the two deprecations have different removal timelines and combining them would couple their lifecycle. Confirm during planning.

The previously open question about orchestrator-api deprecation channel is now closed: §11.1 makes the asymmetry explicit. The orchestrator-api stays strict and rejects `--feature` outright; the main CLI gets the transitional warning. C-010 forbids widening the orchestrator-api envelope.

If any of these become contentious during planning, escalate to the ADR author rather than re-litigating the canonical model.

## 16. Key Entities

| Entity | Description | Canonical identifier |
|---|---|---|
| Mission | The concrete tracked item under `kitty-specs/<mission-slug>/`. | `mission_slug`, `mission_number` |
| Mission Type | The reusable workflow blueprint. | `mission_type` |
| Mission Run | A runtime/session execution instance of a mission. | `mission_run_id` |
| Work Package | A planning/review slice inside a mission. | `wp_id` |
| Tracked-Mission Command Surface | Any CLI command in `src/specify_cli/cli/commands/**` whose primary argument is a tracked mission slug. | (set of files) |
| Runtime/Session Command Surface | Any CLI command whose primary argument is a runtime/session instance. | (set of files) |
| Doctrine Skill | A skill file under `src/doctrine/skills/**` that teaches agents how to operate Spec Kitty. | (set of files) |

## 17. References

- ADR: `architecture/2.x/adr/2026-04-04-2-mission-type-mission-and-mission-run-terminology-boundary.md`
- Initiative: `architecture/2.x/initiatives/2026-04-mission-nomenclature-reconciliation/README.md`
- Issue (immediate): `Priivacy-ai/spec-kitty#241`
- Issue (gated follow-on): `Priivacy-ai/spec-kitty#543`
- Upstream contract: `Priivacy-ai/spec-kitty-events` README, COMPATIBILITY, `src/spec_kitty_events/__init__.py`, `kitty-specs/014-mission-contract-cutover/spec.md`
- Validated baseline (`spec-kitty`): commit `54269f7c131a5efc40b729d412de26f6b05c65fb`
- Validated baseline (`spec-kitty-events`): commit `5b8e6dc39da0fc0ad37de41fd576111ea542cf36`
