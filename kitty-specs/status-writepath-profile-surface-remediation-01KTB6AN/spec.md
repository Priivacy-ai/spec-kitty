# MissionStatus Write-Path Completion & Profile-Load Surface Remediation

**Mission ID:** `01KTB6AN8XJWN4ZVMHK4YBAYBY`
**Slug:** `status-writepath-profile-surface-remediation-01KTB6AN`
**Mission type:** software-dev
**Target branch:** `feature/status-writepath-profile-surface-remediation`

## Purpose

Close two distinct but independently-shippable remediation gaps that a prior mission and a doctrine-skill drift left behind:

1. **#1667 residual — `MissionStatus` write path.** *(Scope materially reduced after dialectic review — see `dialectic-review.md`.)* The aggregate's read path shipped in `01KT6HVH` (WP04); its write-method **test coverage and `_read_meta` fail-closed guard then shipped in PR #1682** (`cdc258002`) — which the original spec missed because it relied on the pre-#1682 review report. The **only** genuine residual is: (a) a `mission_slug` validation guard at `load()` (FR-007), and (b) an **open decision** — the live status-write surface (`agent status emit`) still bypasses the aggregate, calling `emit_status_transition_transactional` directly, so #1667's single-domain-ownership intent (FR-019/020) is unmet. Whether to wire it (overlapping #1673) or close #1667 as delivered is the user's call (D-1).

2. **#1636 — profile-load command surfaces.** The `ad-hoc-profile-load` doctrine skill documents four CLI commands (`agent profile show / hierarchy / init / create`) that do not exist; only `agent profile list` does, and it is **activation-blind** (returns every profile on disk regardless of charter activation). This mission delivers an **activation-aware** `profile list` and a new `profile show`, routes them through the existing charter activation chokepoint, and reconciles the skill doc so the documented workflow stops failing.

The two workstreams share no code and may land as independent lanes; they are bundled here because both are small, contained surface-remediations discovered in the same investigation.

## Source Issues

| Issue | Title | Relationship |
|-------|-------|--------------|
| [#1667](https://github.com/Priivacy-ai/spec-kitty/issues/1667) | Introduce `MissionStatus` aggregate (Mission Management domain) | **Residual hardening** — aggregate exists; this closes the untested/unwired write path (RISK-001) |
| [#1636](https://github.com/Priivacy-ai/spec-kitty/issues/1636) | Missing `agent profile show <id>` CLI command — documented by skill, never implemented | **Primary** — implement + activation-aware listing/show; reconcile skill drift |
| [#1672](https://github.com/Priivacy-ai/spec-kitty/issues/1672) | Strangler step 1: e2e parity ratchet (CWD-invariance gate) | **Consumed gate, narrow slice only** — the ratchet exists but covers only the `status` read; this mission extends it over the status **write** path it touches. Full #1672 stays owned by its assignee |
| [#1619](https://github.com/Priivacy-ai/spec-kitty/issues/1619) | Execution-state CWD-derivation root cause (Strangler Fig) | Parent of #1667; out of scope here except as the governing domain model |

Governing ADRs (already on `main`): `architecture/3.x/adr/2026-06-03-1-execution-state-domain-model.md` (Status owned by Mission Management), `…-2-executioncontext-owner-and-committarget.md`. No new ADR is required for either workstream (the domain model is already ratified); one **design note** records the profile-activation gating decision (see Contracts §B).

## User Scenarios & Testing

### Scenario A — Status write path is exercised and verified
A workflow surface applies a lane transition through `MissionStatus.transition(request)` and persists it through `MissionStatus.save(operation=...)`. The transition is validated by the aggregate (domain invariant), `BookkeepingTransaction` is called internally, and a `CommitReceipt` is returned. Both paths have unit coverage for the happy path **and** the rejection path.

### Scenario B — Status write path rejects an illegal transition
`MissionStatus.transition()` is called with an illegal `(from_lane, to_lane)` pair and no `force`. It raises before any event is appended or any commit is made (fail-closed, no partial state).

### Scenario C — `profile list` reflects charter activation
In a project whose charter has explicitly activated a subset of agent profiles, `spec-kitty agent profile list` shows **only** the activated profiles. `--all` shows every available profile across built-in/org/project layers, annotated by source and `activated | available` state. In a project with no explicit activation (the common case), the list is unchanged from today (all built-ins).

### Scenario D — `profile show` is activation-gated
`spec-kitty agent profile show <id>` prints the full resolved profile definition for an **activated** profile. For a non-activated id it fails closed with a structured `profile_not_activated` error listing the activated candidates. `--all` bypasses the gate for inspection.

### Scenario E — Abstract parent profile (lineage gate, Option A)
A profile `child` declares `specializes_from` a parent profile that is **not** itself activated (an "abstract base" holding shared elements). `profile show child` resolves successfully, composing inherited fields from the non-activated parent, and **emits a user-facing warning** that lineage traversed a non-activated parent. `profile show <parent>` (the abstract base, non-activated) fails the activation gate unless `--all` is passed.

### Scenario F — Skill workflow no longer references phantom commands
After reconciliation, the `ad-hoc-profile-load` skill's Step 1 invokes a command that exists; no step references `agent profile show/hierarchy/init/create` as a working command unless that command is actually implemented.

## Functional Requirements

### Workstream A — `MissionStatus` write-path completion (#1667 residual)

| ID | Requirement | Status |
|----|-------------|--------|
> **REVISED after dialectic review (`dialectic-review.md`).** Most of this workstream was already delivered by **PR #1682 (`cdc258002`)**, which landed *after* the `01KT6HVH` review report the original spec was built on. Rows corrected to current `main`. The scope fork **D-1 (X vs Y) is OPEN — user's call** — and gates whether Workstream A exists beyond FR-007.

| ~~FR-001~~ | `transition()` happy-path coverage | **ALREADY DONE** — `tests/unit/status/test_mission_status_aggregate.py:410` (#1682) |
| ~~FR-002~~ | `transition()` rejection-path coverage | **ALREADY DONE** — `…:437` raises `InvalidTransitionError` before append (#1682) |
| ~~FR-003~~ | `save()` → `CommitReceipt` coverage | **ALREADY DONE** — `…:463,528` (#1682) |
| ~~FR-005~~ | invariants inside `transition()` not `BookkeepingTransaction` | **ALREADY TRUE** — `aggregate.py:355` validates; never lived in `BookkeepingTransaction` |
| ~~FR-006~~ | `_read_meta` fail-closed on non-absent I/O errors | **ALREADY DONE** — raises `MissionMetadataUnavailable` at `aggregate.py:244-278` (#1682) |
| FR-007 | `MissionStatus.load()` validates `mission_slug` against `^[A-Za-z0-9_-]+$` (`.isascii()`) at entry, typed error on mismatch, regression coverage incl. an accented-Latin case (DIRECTIVE_010/011). **Genuinely new** — no validation in `load()` today. | Proposed |
| FR-004 (revised) | **OPEN FORK — user decision (D-1).** Unmet half of RISK-001 = "no live caller": `agent status emit` calls `emit_status_transition_transactional` **directly** (`cli/commands/agent/status.py:275`), bypassing the aggregate. **(X)** declare #1667 delivered + **close it** (live-surface wiring → #1673), Workstream A = FR-007 only; **or (Y)** route `agent status emit` through `MissionStatus.transition()/.save()` for true FR-019/020 ownership, accepting #1673 overlap. **Recommendation: (X).** | **Blocked on D-1** |
| FR-008 | *(Fork Y only.)* Extend the #1672 ratchet over the status **write** transition once it routes through the aggregate. Under fork X this FR is **dropped** (ratchet already covers the read; no new aggregate write surface). | Conditional |

### Workstream B — Profile-load command surfaces (#1636)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-010 | A shared factory `build_activation_aware_doctrine_service(repo_root)` constructs the inner `doctrine.service.DoctrineService` and wraps it in `charter.resolver.DoctrineService(inner, pack_context=PackContext.from_config(repo_root))`, so all profile surfaces resolve through one chokepoint | Proposed |
| FR-011 | `spec-kitty agent profile list` defaults to **activated-only**. **Corrected approach (per dialectic review):** today the command builds its descriptor rows from `ProfileRegistry.list_all()` (`profiles_cmd.py:30`), not from `doctrine.service`. To preserve the existing descriptor schema and guarantee NFR-001 byte-identity, **filter the existing `ProfileRegistry` row set by `PackContext.from_config(repo_root).activated_agent_profiles`** (three-state: absent → all; empty → none; set → those) — do **not** swap the data source to the wrapper's `.agent_profiles` dict. The shared factory (FR-010) is used by `show`/`--include`, where no legacy schema is at stake. | Proposed |
| FR-012 | `profile list` gains `--all` and `--show-available` flags (mirroring `charter list`) that drop to the unfiltered repository and annotate each row with source layer and `activated | available` | Proposed |
| FR-013 | A new `spec-kitty agent profile show <id>` (alias `get`) prints a single profile's full resolved definition — `initialization_declaration`, `specialization` (primary/secondary/avoidance), `collaboration` (handoff_to/from, works_with), `canonical_verbs`, `mode_defaults`, directive/tactic references, source layer — with `--json` | Proposed |
| FR-014 | `profile show` is **activation-gated** on the requested (leaf) id: a non-activated id fails closed with a structured `profile_not_activated` error listing activated candidates; `--all` bypasses the gate for inspection | Proposed |
| FR-015 | **Lineage gate = Option A (gate leaf only).** `profile show` resolution MAY traverse `specializes_from` parents that are not themselves activated, to support **abstract base profiles** (non-activated parents storing shared elements). When lineage traverses a non-activated parent, `profile show` emits a clearly-worded user warning naming the non-activated parent(s) | Proposed |
| FR-016 | `charter context --include agent-profile:<id>` resolves through the activation-aware wrapper so the fetch path inherits the activation gate. **Corrected (per dialectic review):** `_build_doctrine_service` is at `charter/context.py:1235`, builds a plain `DoctrineService(**kwargs)` with **no** `PackContext`, and has **6 callers** (lines 333/352/863/1373/2620 + `_maybe_build_doctrine_service@2887`). To avoid changing the return type for all 6 sites, add a **scoped wrapped variant** (e.g. `_build_activation_aware_doctrine_service`) used **only** by the `agent-profile` include branch, constructing `PackContext.from_config(repo_root)` locally (the module already imports `PackContext` and constructs one for a different function near line 244). Do **not** blanket-wrap the shared helper. | Proposed |
| FR-019 | **Glossary (DIRECTIVE_032):** the new load-bearing user-facing terms — *abstract base profile* (and *activated vs available profile*, *activation chokepoint*) — are added to the canonical glossary before the `profile show` warning string ships. Vocabulary ratification precedes code; not deferred as "advisory". | Proposed |
| FR-017 | The `ad-hoc-profile-load` skill source (`src/doctrine/skills/ad-hoc-profile-load/SKILL.md`) is reconciled: adopt/invoke steps point to `spec-kitty ask` / `advise`; profile-detail steps point to the new `profile show`; `hierarchy` / `init` / `create` references are either implemented or removed — no step references a non-existent command | Proposed |
| FR-018 | A doc/CLI-parity guard (test) asserts every `spec-kitty agent profile <subcommand>` referenced in shipped skill docs corresponds to a registered Typer command, preventing future skill drift | Proposed |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Backward compatibility of `profile list`: projects with no explicit `activated_agent_profiles` see identical output to pre-mission behavior | Zero diff on unconfigured projects | Proposed |
| NFR-002 | `BookkeepingTransaction` isolation: the write-path work calls it internally; no change to `coordination/transaction.py` internals | Zero changes to `coordination/transaction.py` | Proposed |
| NFR-003 | No activation regression for runtime: `runtime/next` profile resolution behavior is unchanged (it already uses the wrapper) | Existing runtime tests green | Proposed |
| NFR-004 | `profile show --json` output is machine-stable (sorted keys, documented schema) for scripting | Schema documented in contracts; snapshot-tested | Proposed |

## Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | `coordination/transaction.py` internals must not be modified (NFR-002) | Accepted |
| C-002 | The `MissionStatus` read path and its tests (shipped in `01KT6HVH`) must remain green; this mission is additive to the write path | Accepted |
| C-003 | The activation wrapper `charter.resolver.DoctrineService` must not be duplicated; the shared factory wraps the existing class | Accepted |
| C-004 | `mission_number` must not be used as identity or selector anywhere in new/modified code (ULID/slug only) | Accepted |
| C-005 | Layer rule preserved: the activation-aware wrapper lives in `charter.*` so it may import `PackContext`; profile CLI in `specify_cli.*` constructs it with a real `PackContext` (DIRECTIVE_031 bounded-context boundary) | Accepted |
| C-006 | Template/skill edits target the **source** (`src/doctrine/skills/...`), never the generated agent copies (per CLAUDE.md) | Accepted |
| C-007 | Workstreams A and B are independently shippable; neither may introduce a hard dependency on the other | Accepted |
| C-008 | The e2e parity ratchet (`tests/architectural/test_execution_context_parity.py`, #1672) must remain green throughout; FR-008 extends it but must not weaken its existing assertions | Accepted |

## Key Entities

| Entity | Description |
|--------|-------------|
| `MissionStatus` | Existing aggregate (`src/specify_cli/status/aggregate.py`) — read path shipped; write path (`transition`/`save`) completed + tested here |
| `ActiveWPStatus` | Read projection from `MissionStatus.claim()` — unchanged |
| `BookkeepingTransaction` | Infra coordinator (`coordination/transaction.py`) — called only internally; unchanged |
| `CommitReceipt` | Return type of `save()` (`coordination/types.py`) — unchanged |
| `charter.resolver.DoctrineService` | Activation-aware wrapper (`src/charter/resolver.py:56-129`) — the activation chokepoint; reused, not duplicated |
| `PackContext` | `src/charter/pack_context.py` — three-state `activated_agent_profiles` resolver |
| `build_activation_aware_doctrine_service` | **New** shared factory — single construction seam for all profile surfaces |
| `profile show` | **New** CLI command (`profiles_cmd.py`) — activation-gated single-profile inspector |
| Abstract base profile | A profile referenced via `specializes_from` that is not itself activated; resolvable as lineage but gated for direct `show` |

## Success Criteria

| # | Criterion | Measurable threshold |
|---|-----------|----------------------|
| 1 | `MissionStatus.transition()` and `.save()` have unit coverage (happy + rejection) | New tests in `tests/.../test_mission_status_aggregate.py`; both methods exercised; coverage no longer "MISSING" |
| 2 | RISK-001 closed | A named, tested wired path for the write methods exists (FR-004); review note resolvable |
| 3 | `profile list` is activation-aware with non-breaking default | Unconfigured project: identical output; configured project: filtered; `--all` shows annotated full catalog |
| 4 | `profile show <id>` exists and is activation-gated | Command registered; activated id prints full def; non-activated id → structured error; `--all` inspects |
| 5 | Abstract-parent lineage works with warning | `profile show child` with non-activated parent resolves + warns; `profile show parent` gated |
| 6 | Skill drift closed | `grep "agent profile show/hierarchy/init/create"` in `src/doctrine/skills/ad-hoc-profile-load/SKILL.md` references only implemented commands; parity guard test passes |
| 7 | No regressions | Full existing status + charter + runtime test suites green; zero change to `coordination/transaction.py` |

## Assumptions

- The `MissionStatus` aggregate, `ActiveWPStatus`, `CoordAuthorityUnavailable`, and the `agent/status.py` read-path migration are already shipped (verified on `feature/...` base, originating from `01KT6HVH`); this mission does not rebuild them.
- `charter.resolver.DoctrineService`, `PackContext.from_config`, and the construction pattern in `charter/generate.py:46-74` are the canonical activation seam; the shared factory generalises that pattern.
- `activated_agent_profiles` in `.kittify/config.yaml` is the authoritative activation key for agent profiles (confirmed via `charter list` showing `agent-profile` as a first-class activatable kind).
- The four "phantom" skill commands were never implemented (git history confirms); reconciliation is doc-side plus the one genuinely-needed new command (`show`).

## Open / Unresolved Decisions

Surfaced for `plan` to resolve — not hidden in plan detail (per spec-kitty specify guidance).

| # | Decision | Status | Notes |
|---|----------|--------|-------|
| D-1 | **#1667 disposition (REVISED after dialectic review).** Coverage + fail-closed already shipped (#1682). The only unmet piece is the live write surface bypassing the aggregate (`agent status emit` → `emit_status_transition_transactional` direct, `status.py:275`). **(X)** declare #1667 delivered + close it, route live-surface wiring to #1673, Workstream A = FR-007 only; **(Y)** wire `agent status emit` through `MissionStatus.transition()/.save()` now (overlaps #1673). | **OPEN — user's call** | Recommendation **(X)**. This is the pivotal scope decision; it determines whether Workstream A is essentially "FR-007 + close #1667" or a real write-surface re-wire. |
| D-2 | **Lineage activation gate (FR-015):** leaf-only gate, abstract parents allowed. | **RESOLVED → Option A + warning** | Operator decision 2026-06-05: supports abstract base profiles (non-activated shared-element stores); inheritance must warn, never be silent. |
| D-3 | **#1672 scope:** narrow slice (extend ratchet over write path) vs. full e2e ratchet. | **RESOLVED → narrow slice (FR-008)** | Full #1672 remains owned by its assignee; bundling the P0 gate would muddy ownership. |
| D-4 | **`profile show` not-found schema:** exact JSON shape of `profile_not_activated` (field names, candidate list ordering). | **OPEN (low-risk)** | Align with existing selector-disambiguation error shape; finalize in `plan`/contracts. |

## Terminology & Governance Routing

- **Glossary (route to `spk-doctrine-glossary` during plan):** new/load-bearing terms introduced here — *activated vs available profile*, *abstract base profile*, *activation chokepoint*, *write-path / read-path of `MissionStatus`*. Confirm canonical definitions before code (DIRECTIVE_032 conceptual alignment).
- **Charter (route to `spk-doctrine-charter` if scope shifts):** Workstream B's semantics are governed by the charter activation model (`activated_agent_profiles`). No charter change is required; the mission *consumes* the existing activation contract. Flag if `plan` discovers a needed activation-vocabulary change.

## Out of Scope

- Broader ExecutionContext residue routing (#1673) and `MissionRun → Mission` back-reference (#1663).
- `status/` import-boundary enforcement test (#1664) — sibling follow-up, not bundled.
- The **full** #1672 e2e parity ratchet (the complete `next → implement → move-task → review → status` sequence and its role as the universal CI gate) — only the write-path slice this mission touches is in scope (FR-008); #1672 itself stays owned by its assignee.
- Implementing `profile hierarchy`, `init`, `create` as new commands (skill text is reconciled to not promise them; implementing them is a separate enhancement).
- Any change to `BookkeepingTransaction` internals or the activation wrapper's filtering semantics.

---

## Suggested Contracts & Design (authoring input for `plan`)

> This section is advisory design carried from the pre-spec investigation. The `plan` phase should ratify or revise it. Full current-state evidence lives in `research.md`.

### §A — `MissionStatus` write path

Verified current state (`src/specify_cli/status/aggregate.py`):
- `transition(self, request: TransitionRequest) -> StatusEvent` (~L313-378) — implemented; delegates to `coordination/status_transition.emit_status_transition_transactional`. **Untested.**
- `save(self, *, operation: str) -> CommitReceipt` (~L380-417) — implemented; persists via `BookkeepingTransaction`. **Untested.**
- Domain validation already available: `status/transitions.validate_transition(from_lane, to_lane, ctx) -> (ok, error)`.

Design:
- **Do not** add a new abstraction. Test the existing methods and resolve the wiring question (FR-004): the existing live transactional caller is `emit_status_transition_transactional`; decide whether `agent/status.py` (or a workflow surface) should call `MissionStatus.transition()` directly, or whether the aggregate method is the sanctioned façade *over* that function and the "no live caller" finding is closed by documenting + testing that delegation.
- Fail-closed hardening (FR-006/FR-007) are small guards at `load()`/`_read_meta` entry.

### §B — Profile activation seam (the central design)

The activation model already exists end-to-end; the fix is wiring, not new machinery.

```
.kittify/config.yaml :: activated_agent_profiles (3-state)
   │ PackContext.from_config(repo_root).activated_agent_profiles
   ▼
charter.resolver.DoctrineService(inner, pack_context).agent_profiles   ← activation chokepoint (resolver.py:120-129)
   ▲ reused by: charter list, charter generate, org-layer lint, runtime/next
   │  NEW consumers routed through the shared factory:
   ├── profile list   (default activated-only; --all/--show-available escape)
   ├── profile show    (activation-gated leaf; lineage Option A + warning)
   └── charter context --include agent-profile:<id>
```

Proposed factory (single construction seam, generalising `charter/generate.py:46-74`):

```python
def build_activation_aware_doctrine_service(repo_root: Path) -> "charter.resolver.DoctrineService":
    from charter.resolver import DoctrineService as ActivationDoctrineService
    from charter.pack_context import PackContext
    from doctrine.service import DoctrineService as InnerDoctrineService
    inner = InnerDoctrineService(built_in_root=..., project_root=..., org_roots=...)
    return ActivationDoctrineService(inner, pack_context=PackContext.from_config(repo_root))
```

`profile show` resolution algorithm (lineage Option A):
1. **Visibility gate** — `service.agent_profiles.get(id)`; if absent and not `--all` → `profile_not_activated` error listing activated candidates.
2. **Definition resolution** — render the full profile; compose `specializes_from` lineage via the inner `AgentProfileRepository.resolve_profile(id)` (may traverse non-activated parents = abstract bases).
3. **Warning** — if any traversed ancestor ∉ activated set, emit a user-facing warning naming them ("resolved via non-activated parent profile(s): … — these act as abstract bases and are not directly selectable").

Decision recorded for `plan` to lift into a short design note (not a full ADR): **lineage gate = Option A**, rationale = supports abstract superclass parent profiles (shared-element stores that are intentionally not resolvable/activatable on their own), with an explicit warning so the inheritance is never silent.
