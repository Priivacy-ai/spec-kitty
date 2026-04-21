# Implementation Plan: Profile Invocation Runtime and Audit Trail

**Branch**: `main` (planning and eventual merge target) | **Date**: 2026-04-21 | **Spec**: [`spec.md`](./spec.md)
**Release target**: `3.2.0` (builds on `3.2.0a3` baseline; Phase 4 of Charter/Doctrine EPIC #461)
**Input**: [spec.md](./spec.md) · 19 FR, 8 NFR, 10 C · 9 user scenarios · 7 edge cases

---

## Summary

Deliver the `3.2.0` runtime execution surface for the Charter/Doctrine EPIC (#461, Phase 4). The central deliverable is `ProfileInvocationExecutor` — a new `src/specify_cli/invocation/` package that routes every profile-governed CLI invocation through a unified `(profile_id, action, governance_context)` triple, writes a Tier 1 `InvocationRecord` to a local JSONL audit log before returning to the caller, and optionally propagates that record to SaaS in the background.

Four CLI surfaces are built on top of the executor: `spec-kitty advise` (returns routing decision + governance context, opens an invocation record), `spec-kitty ask <profile> <request>` (named-profile shorthand), `spec-kitty do <request>` (anonymous dispatch through the deterministic action router), and `spec-kitty profiles list` (enumerates available profiles). A fifth surface, `spec-kitty profile-invocation complete`, closes open records. A sixth, `spec-kitty invocations list`, queries the local log.

The action router (ADR-3) is a pure deterministic function over canonical role verbs and profile domain keywords — no LLM call in the routing path. ADR-3 is a record-and-freeze document produced during WP4.1 as an entry gate before any router code is merged. The spec's three-tier minimal viable trail policy is materialized as a formal code constant in WP4.6 (`MinimalViableTrailPolicy`).

SaaS propagation is additive: records are written locally first, then propagated in a background thread when a SaaS token is configured. Propagation failure is logged to `.kittify/events/propagation-errors.jsonl` and never blocks the CLI.

Scope is bounded: `intake` does not route through the executor; workflow composition hooks are documented stubs only; Phase 5 glossary rollout and Phase 6 retrospective are explicitly deferred.

---

## Technical Context

**Release**: `3.2.0` (current prerelease line: `3.2.0a3`)
**Language/Version**: Python 3.11+ (existing spec-kitty baseline)
**Primary Dependencies (existing, reused)**: `typer` (CLI), `rich` (console), `ruamel.yaml` (YAML), `pydantic` v2 (models + schema validation), `pytest` (tests), `mypy` strict (type-check)
**New Dependencies**: **None**. ULID generation reuses `python-ulid` or `ulid2` already present for mission identity (mission 083); confirm in plan gate. SHA-256 is `hashlib` stdlib.
**Storage**: Filesystem only. New paths:
- `.kittify/events/profile-invocations/<profile_id>-<invocation_id>.jsonl` — per-invocation JSONL record
- `.kittify/events/propagation-errors.jsonl` — SaaS propagation error log
No database, no queue, no new network dependency beyond existing SaaS client.
**Testing**: `pytest`, `mypy --strict`. 100% of tests run offline (no live LLM, no live SaaS). SaaS integration tests are tagged `@pytest.mark.saas_integration` and excluded from CI default run.
**Target Platform**: Local developer machines + CI (Linux + macOS + Windows; `Path.open("a")` for JSONL append is cross-platform).
**Performance Goals**:
- `spec-kitty advise` end-to-end (governance context load + event write): < 500 ms (NFR-001)
- `invocations list` for 100 most recent at 10,000-entry log: < 200 ms (NFR-008)
**Constraints**:
- No LLM call in the routing path (C-001 / ADR-3 decision)
- `InvocationRecord` is append-only; no in-place mutation after initial write (NFR-006)
- `intake` does not route through `ProfileInvocationExecutor` (C-005 / FR-018)
- Zero SaaS calls block the CLI (FR-015)
- `mypy --strict` clean (NFR-005) and ≥ 90% line coverage on invocation package code (NFR-004)
**Scale/Scope**: Small. Dozens of profiles at most; hundreds of invocation records per project per week. This is a correctness and interface-shape problem, not a throughput problem.

---

## Charter Check

Charter present at `/Users/robert/spec-kitty-dev/charter5/spec-kitty/.kittify/charter/charter.md`.

| Directive / Tactic | Applicability | Status |
|---|---|---|
| **DIRECTIVE_003 — Decision Documentation** | ADR-3 (router algorithm) is a load-bearing decision; the executor interface shape and MinimalViableTrailPolicy tier definitions are also material. | **PASS (with action)**: ADR-3 is produced as a required WP4.1 entry gate artifact before any router code is merged. KD-1 through KD-6 below capture all other material decisions with rationale and rejected alternatives. |
| **DIRECTIVE_010 — Specification Fidelity** | Plan must not contradict spec's 19 FRs, 8 NFRs, 10 Cs. | **PASS**: Plan only resolves HOW; all WHATs are preserved from spec. No scope additions. |
| **adr-drafting-workflow** | ADR-3 qualifies. | **PASS**: ADR-3 drafted in Phase 1 (see `adr-3-deterministic-action-router.md`), required as WP4.1 entry gate. |
| **problem-decomposition** | Already applied in spec §9; plan refines WP granularity. | **PASS**: 8 WPs with explicit dependency graph below. |
| **premortem-risk-identification** | R-1…R-6 from spec §11 plus plan-specific risks below. | **PASS**: Premortem table in §"Risks & Premortem" below. |
| **eisenhower-prioritisation** | WP order reflects unblocking value: WP4.1 (foundation) → WP4.2+WP4.6 (parallel) → WP4.3+WP4.4+WP4.5 (CLI surfaces) → WP4.7+WP4.8 (propagation + query). | **PASS**. |
| **requirements-validation-workflow** | Every FR traces to at least one user scenario and one test target in §"Review & Validation". | **PASS**. |
| **review-intent-and-risk-first** | Downstream review order captured in §"Review & Validation Strategy". | **PASS**. |
| **stakeholder-alignment** | Host LLM/agent harness, operator, SaaS dashboard user, profile registry owner. Interaction surfaces are explicit in US-1…US-9. | **PASS**. |
| **Policy — 90% coverage** | Applies to all new code under `src/specify_cli/invocation/`. | **PASS** (NFR-004). |
| **Policy — mypy --strict** | Applies to all new modules. | **PASS** (NFR-005). |
| **Policy — integration tests for CLI commands** | `advise`, `ask`, `do`, `profiles list`, `profile-invocation complete`, `invocations list` are all CLI commands. | **PASS**: integration tests specified in §"Review & Validation Strategy". |

**No violations. No Complexity Tracking entries required.**

---

## Key Decisions

### KD-1 · Package location — new `src/specify_cli/invocation/` package

All executor, router, record, writer, registry, and propagator code lives under `src/specify_cli/invocation/`. This package depends on `src/doctrine/agent_profiles/` (profiles) and `src/charter/context.py` (governance context), following the existing dependency direction (`specify_cli` → `doctrine` → `charter`).

No changes are made to `src/specify_cli/next/` (the mission-advancement loop). The executor is an orthogonal surface — it handles profile invocations, not mission step orchestration.

**Rejected alternatives**:
- Extending `src/specify_cli/next/` — conflates step orchestration with profile invocation; wrong semantic boundary.
- New top-level package `src/invocation/` — breaks existing import conventions; all spec-kitty CLI code is under `src/specify_cli/`.

### KD-2 · ADR-3: Deterministic action router (Option A — record-and-freeze)

**Decision**: The v1 action router is a pure deterministic function with no LLM call. Routing precedence:

1. **Explicit `profile_hint`**: if the caller supplies a profile ID or name, resolve it via `AgentProfileRepository.get()`. Derive action from the normalized request tokens using the profile's role `canonical_verbs`. Return `RouterDecision(confidence="exact")`.

2. **Canonical verb matching**: normalize request tokens (lowercase, split on whitespace and punctuation, drop stop-words). For each role, check whether any `DEFAULT_ROLE_CAPABILITIES.canonical_verbs` entry appears in the normalized token set. Collect `(role, matched_verb)` pairs.

3. **Domain keyword matching**: for each profile in the repository, check whether any `AgentProfile.domain_keywords` entry appears in the normalized token set. Score candidates using `routing_priority` as a tiebreaker.

4. **Resolution**: if exactly one `(profile_id, action)` pair has the highest score with no ties → `RouterDecision(confidence="canonical_verb"` or `"domain_keyword")`. If zero matches or multiple tied candidates → `RouterAmbiguityError(candidates=[...])`.

**Stated action field**: the resolved action string is normalized to a canonical token (e.g., `"implement"`, `"review"`, `"plan"`, `"specify"`, `"advise"`) using a mapping table. Unknown verbs pass through as-is.

**Reason**: preserves the "Spec Kitty must not spawn a parallel LLM call" invariant (issue #466 / #519); stays fully offline-testable; keeps the smallest releaseable chunk small. Hybrid fallback is explicitly open for a future release after real invocation data is available.

**ADR-3 document**: produced as `kitty-specs/profile-invocation-runtime-audit-trail-01KPQRX2/adr-3-deterministic-action-router.md` before WP4.2 implementation is approved.

### KD-3 · Governance context assembly — `build_charter_context()` direct call

The executor calls `build_charter_context(repo_root, profile=profile_id, action=action, mark_loaded=False)` from `src/charter/context.py` to assemble the governance context block. `mark_loaded=False` prevents invocations from poisoning the first-load tracking used by `specify`/`plan`/`implement`/`review` flows.

The governance context hash stored in `InvocationRecord.governance_context_hash` is the first 16 hex characters of `sha256(result.text.encode()).hexdigest()`. This is sufficient for provenance; it is not a security hash.

**Degraded-mode handling**: if `build_charter_context()` returns `mode="missing"` (no charter synthesized), the executor emits a structured warning and returns a minimal context block indicating that governance context is unavailable. An `InvocationRecord` is still written so the invocation is auditable. The CLI exits with code 0 but the JSON payload contains `governance_context_available: false`.

### KD-4 · Profile resolution — shipped-first, project-local-override

`AgentProfileRepository` already supports a `project_dir` override path for project-local profiles. The executor constructs the repository with `AgentProfileRepository(shipped_dir=..., project_dir=repo_root / ".kittify" / "profiles")` so that shipped profiles are always available and project-local profiles (once Phase 3 writes them) shadow them.

If `.kittify/profiles/` does not exist (the common case for projects that have not run Phase 3 synthesis), the repository gracefully falls back to shipped profiles only, with no error.

### KD-5 · InvocationRecord write — append-to-per-invocation JSONL file

Each invocation writes its record to a dedicated JSONL file at `.kittify/events/profile-invocations/<profile_id>-<invocation_id>.jsonl`. The file starts with the `started` event and gains a `completed` event when `profile-invocation complete` is called.

**Rationale**: per-invocation files simplify concurrent writes (no cross-file locking needed — ULID ensures uniqueness), make individual record lookup O(1) (filename contains the invocation ID), and make the directory scannable for `invocations list` queries.

**Rejected alternatives**:
- Single append-only log per profile (`<profile_id>.jsonl`) — concurrent writes need advisory locking; read-all scan for specific ID is O(n).
- Single global log — same concurrency concern plus noisier scans.

### KD-6 · SaaS propagation — background thread, post-write, non-blocking

After a successful local JSONL write, the propagator submits the record to a `ThreadPoolExecutor` (size 1 per CLI invocation lifecycle). The propagation thread calls the existing SaaS sync client. On failure it appends to `.kittify/events/propagation-errors.jsonl`. On success it is silent. The main CLI thread never joins the propagation thread before returning.

**Process lifecycle**: for short-lived CLI processes (`advise`, `ask`, `do`), the `ThreadPoolExecutor` is given a 5-second `shutdown(wait=True)` timeout via `atexit` registration. Propagation that exceeds 5 seconds at process exit is abandoned and logged as a timeout error.

---

## Project Structure

### Documentation (this feature)

```
kitty-specs/profile-invocation-runtime-audit-trail-01KPQRX2/
├── spec.md                               # Specification (already committed)
├── plan.md                               # This file
├── research.md                           # Phase 0 findings
├── data-model.md                         # Entity model and field definitions
├── quickstart.md                         # Operator quickstart
├── adr-3-deterministic-action-router.md  # ADR-3 record-and-freeze (Phase 1 output)
├── contracts/
│   ├── invocation-payload.yaml           # InvocationPayload JSON schema
│   ├── invocation-record.yaml            # InvocationRecord JSONL schema
│   └── router-decision.yaml             # RouterDecision / RouterAmbiguityError schema
├── checklists/
│   └── requirements.md                  # Spec quality checklist (already committed)
└── tasks/                               # Populated by /spec-kitty.tasks
```

### Source Code (repository root)

```
src/specify_cli/invocation/              # NEW — main package
├── __init__.py                          # Public API: ProfileInvocationExecutor, InvocationRecord, ...
├── executor.py                          # ProfileInvocationExecutor class
├── router.py                            # ActionRouter (deterministic, Option A)
├── record.py                            # InvocationRecord Pydantic model + MinimalViableTrailPolicy
├── writer.py                            # JSONL event writer (append-only)
├── propagator.py                        # SaaS background propagator
├── registry.py                          # ProfileRegistry (thin wrapper: AgentProfileRepository)
└── errors.py                            # RouterAmbiguityError, ProfileNotFoundError, ContextUnavailableError

src/specify_cli/cli/commands/
├── advise.py                            # NEW: `advise` + `profile_invocation complete`
├── profiles_cmd.py                      # NEW: `profiles list`
└── invocations_cmd.py                   # NEW: `invocations list`

src/specify_cli/cli/
└── main.py                              # MODIFY: register new command groups

tests/specify_cli/invocation/           # NEW — test package
├── __init__.py
├── test_executor.py
├── test_router.py
├── test_record.py
├── test_writer.py
├── test_propagator.py
├── test_registry.py
└── cli/
    ├── test_advise.py
    ├── test_profiles.py
    └── test_invocations.py

tests/specify_cli/invocation/fixtures/  # NEW — test fixtures
├── profiles/                            # Minimal fixture profiles for tests
│   ├── implementer.agent.yaml
│   └── reviewer.agent.yaml
└── invocation_records/                  # Golden JSONL fixtures
    └── sample_record.jsonl
```

**Storage Layout (new runtime paths):**

```
.kittify/
└── events/
    ├── profile-invocations/
    │   └── <profile_id>-<invocation_id>.jsonl     # One file per invocation
    └── propagation-errors.jsonl                    # SaaS propagation error log
```

**Structure Decision**: Single project, extending existing `src/specify_cli/` package tree. New `invocation/` subpackage follows existing conventions (e.g., `status/`, `merge/`, `next/`). CLI command files follow existing split pattern (`*_cmd.py` to avoid collision with stdlib `profiles` etc.).

---

## Phase 0: Research Findings

*(Full findings in `research.md`. Summary here.)*

**R-0-1 — ULID dependency confirmed**: `python-ulid` is already present (confirmed via `src/specify_cli/status/models.py` ULID import). No new dependency needed.

**R-0-2 — `build_charter_context` API confirmed callable**: `src/charter/context.py::build_charter_context(repo_root, *, profile, action, mark_loaded, depth)` → `CharterContextResult`. The `profile` parameter accepts `str | None` and is passed to DRG filtering. Confirmed the function does not produce side effects that interfere with first-load state when `mark_loaded=False`.

**R-0-3 — `AgentProfileRepository` constructor confirmed**: `AgentProfileRepository(shipped_dir=Path, project_dir=Path | None, active_languages=...)` — project-local override path is already supported. Repository loads project profiles from `<project_dir>/<profile_id>.agent.yaml` and merges them with shipped profiles by matching `profile-id`. Fallback to shipped-only is graceful when `project_dir` does not exist.

**R-0-4 — `DEFAULT_ROLE_CAPABILITIES` canonical verbs confirmed**: 8 roles × 3 verbs each. IMPLEMENTER → `["generate", "refine", "implement"]`; REVIEWER → `["audit", "assess", "review"]`; ARCHITECT → `["audit", "synthesize", "plan"]`; PLANNER → `["plan", "decompose", "prioritize"]`; RESEARCHER → `["analyze", "investigate", "summarize"]`; CURATOR → `["classify", "curate", "validate"]`; DESIGNER → `["synthesize", "draft", "design"]`; MANAGER → `["coordinate", "delegate", "monitor"]`.

**R-0-5 — CLI-SaaS contract schema gap**: The `spec-kitty-saas` contract YAML could not be fetched (private repo). Issue #495 confirms `ProfileInvocationStarted` and `ProfileInvocationCompleted` event types exist as of April 13, 2026. WP4.7 entry gate: verify contract field coverage against `InvocationRecord` v1 fields before implementing propagator. If gap exists, treat as a blocking WP4.7 issue, not a silent adaptation.

**R-0-6 — `main.py` CLI registration confirmed**: `src/specify_cli/cli/main.py` registers command groups. New commands require `app.add_typer()` calls. Follows existing pattern (checked `charter.py`, `next_cmd.py`, `merge.py` registration).

**R-0-7 — No ULID collision under concurrent writes**: Each invocation generates its ULID using `ulid2.generate()` or equivalent at executor entry — before any filesystem write. File path includes both `profile_id` and `invocation_id`, ensuring no collision even if two agents call `advise` for the same profile at the same millisecond.

**R-0-8 — `intake.py` isolation confirmed**: `src/specify_cli/cli/commands/intake.py` is a standalone command that does not share entry points with `advise`/`ask`/`do`. No refactoring needed to keep it outside the executor path.

---

## Phase 1: Design

### Data Model

*(Full entity definitions in `data-model.md`. Summary here.)*

#### InvocationRecord (v1)
```
invocation_id        : str          # ULID, primary key
profile_id           : str          # profile identifier
action               : str          # normalized action token
request_text         : str          # original request string
governance_context_hash : str       # SHA-256 hex prefix (16 chars) of context text
actor                : str          # "claude" | "operator" | inferred from env
started_at           : str          # ISO-8601 UTC
completed_at         : str | None   # null until profile-invocation complete
outcome              : str | None   # null | "done" | "failed" | "abandoned"
evidence_ref         : str | None   # null | relative path to EvidenceArtifact
governance_context_available : bool # false when DRG/charter is missing
```

#### RouterDecision
```
profile_id   : str
action       : str
confidence   : "exact" | "canonical_verb" | "domain_keyword"
match_reason : str          # human-readable description of which signal matched
```

#### RouterAmbiguityError
```
request_text : str
candidates   : list[RouterCandidate]

RouterCandidate:
  profile_id   : str
  action       : str
  match_reason : str
```

#### InvocationPayload (CLI response)
```
invocation_id                : str
profile_id                   : str
profile_friendly_name        : str
action                       : str
governance_context_text      : str          # CharterContextResult.text
governance_context_hash      : str
governance_context_available : bool
router_confidence            : str | None   # null when profile_hint was explicit
```

#### ProfileDescriptor (for `profiles list`)
```
profile_id     : str
friendly_name  : str
role           : str
action_domains : list[str]   # canonical_verbs + domain_keywords merged
```

#### MinimalViableTrailPolicy (code constant, not a data structure)
```python
# Materialized as a module-level constant in record.py
MINIMAL_VIABLE_TRAIL_POLICY = MinimalViableTrailPolicy(
    tier_1=TierPolicy(
        name="every_invocation",
        mandatory=True,
        description="One InvocationRecord written locally before executor returns.",
        storage_path=".kittify/events/profile-invocations/<profile_id>-<invocation_id>.jsonl",
    ),
    tier_2=TierPolicy(
        name="evidence_artifact",
        mandatory=False,
        description="Optional EvidenceArtifact for invocations producing checkable output.",
        storage_path=".kittify/evidence/<invocation_id>/",
        promotion_trigger="caller sets evidence_ref on profile-invocation complete",
    ),
    tier_3=TierPolicy(
        name="durable_project_state",
        mandatory=False,
        description="Promotion to kitty-specs/ or doctrine only when invocation changes project-domain state.",
        promotion_trigger="spec, plan, tasks, merge, accept commands only",
    ),
)
```

### API Contracts

*(Full schemas in `contracts/`. Summary here.)*

**`spec-kitty advise <request> [--profile <name>] [--json]`**
- Exit 0: prints `InvocationPayload` as JSON (or rich text)
- Exit 1: structured error JSON `{error: str, error_code: str, candidates?: [...]}` for ambiguity, missing profile, context unavailable
- Side effect: writes `.kittify/events/profile-invocations/<profile_id>-<invocation_id>.jsonl` (open record)
- Never spawns an LLM call

**`spec-kitty profile-invocation complete --invocation-id <id> [--outcome <status>] [--evidence <path>]`**
- Exit 0: prints closed `InvocationRecord` summary
- Exit 1: structured error for unknown ID or already-closed record
- Side effect: appends `completed` event to the invocation's JSONL file; triggers SaaS propagation if configured

**`spec-kitty ask <profile> <request> [--json]`**
- Identical contract to `advise --profile <profile> <request> [--json]`

**`spec-kitty do <request> [--json]`**
- Identical to `advise` but no `--profile` flag; always routes through `ActionRouter`

**`spec-kitty profiles list [--json]`**
- Exit 0: list of `ProfileDescriptor` as JSON array or rich table
- Exit 1: no profiles available (no shipped profiles or project profiles)

**`spec-kitty invocations list [--profile <name>] [--limit N] [--json]`**
- Exit 0: list of `InvocationRecord` (summary view) sorted by `started_at` descending
- Defaults: `--limit 20`

### ADR-3: Deterministic Action Router (record-and-freeze)

*(Full ADR in `adr-3-deterministic-action-router.md`. Summary here.)*

**Decision**: Option A — deterministic verb-mapping table, no LLM call in routing path.

**Routing precedence** (pure function, testable offline):
1. Explicit `profile_hint` → `AgentProfileRepository.get(hint)` → derive action from `DEFAULT_ROLE_CAPABILITIES[role].canonical_verbs`
2. Canonical verb match → `canonical_verbs` of all roles vs normalized request tokens
3. Domain keyword match → `AgentProfile.domain_keywords` vs normalized request tokens, scored by `routing_priority`
4. Ambiguity / no-match → `RouterAmbiguityError`

**Action normalization**: canonical token set is `{"implement", "review", "plan", "specify", "advise", "analyze", "design", "curate", "coordinate"}`. Verb aliases map to canonical tokens (e.g., `"generate"` → `"implement"`, `"audit"` → `"review"`, `"synthesize"` → `"plan"`).

**Future extension point**: the `ActionRouter` accepts an optional `router_plugin: ActionRouterPlugin | None = None` slot (a no-op `Protocol` in v1) reserved for a future hybrid fallback. This slot is documented but never called in v1.

### Quickstart

*(Full guide in `quickstart.md`. Summary here.)*

For a host-LLM agent (e.g., Claude Code) integrating `advise`:
```bash
# 1. Discover available profiles
spec-kitty profiles list --json

# 2. Get governance context for an action (opens invocation record)
RESULT=$(spec-kitty advise "implement WP03" --json)
INVOCATION_ID=$(echo $RESULT | python3 -c "import sys,json; print(json.load(sys.stdin)['invocation_id'])")
CONTEXT=$(echo $RESULT | python3 -c "import sys,json; print(json.load(sys.stdin)['governance_context_text'])")

# 3. ... host LLM executes work using $CONTEXT ...

# 4. Close the record
spec-kitty profile-invocation complete --invocation-id "$INVOCATION_ID" --outcome done

# 5. Review recent invocations
spec-kitty invocations list --limit 5 --json
```

---

## Work Packages

### WP Dependency Graph

```
WP4.1 (executor core + profiles list + v1 record + writer)
    │
    ├──→ WP4.2 (ADR-3 record + action router)
    │        │
    │        └──→ WP4.5 (do command)
    │
    ├──→ WP4.6 (MinimalViableTrailPolicy formal artifact + tier promotion API)
    │
    ├──→ WP4.3 (advise + ask + profile-invocation complete)
    │        └── depends on WP4.2 (for router wiring)
    │
    └──→ WP4.8 (invocations list)
              └──→ WP4.7 (SaaS propagation)

Parallelism after WP4.1:
  WP4.2 || WP4.6 (fully independent)
  WP4.3 (after WP4.2) || WP4.8 || WP4.6 (after WP4.1)
  WP4.4 merged into WP4.3 (thin shim, < 50 LOC; not a separate WP)
  WP4.5 after WP4.2
  WP4.7 after WP4.8
```

*WP4.4 (`ask` command) is absorbed into WP4.3 — it is a one-line delegation to `advise --profile` and does not justify a separate work package.*

### WP4.1 — Executor Core + Profiles List + v1 Record + Writer

**Entry gate**: ADR-3 document at `kitty-specs/profile-invocation-runtime-audit-trail-01KPQRX2/adr-3-deterministic-action-router.md` must be committed before this WP opens for review.

**Scope**:
- New package `src/specify_cli/invocation/__init__.py` with public API exports
- `executor.py`: `ProfileInvocationExecutor` class
  - `__init__(self, repo_root: Path)`
  - `invoke(request: str, profile_hint: str | None = None) -> InvocationPayload`
  - Calls `ProfileRegistry.get()` / `list_all()`
  - Calls `build_charter_context(repo_root, profile=profile_id, action=action, mark_loaded=False)`
  - Calls `InvocationWriter.write_started(record)`
  - Returns `InvocationPayload`
  - Documents (but does not call) the `router_plugin` workflow composition hook
- `record.py`: `InvocationRecord` Pydantic v2 model with all v1 fields + `MinimalViableTrailPolicy` constant (stub tiers for WP4.6 to fill)
- `writer.py`: `InvocationWriter` class
  - `write_started(record: InvocationRecord) -> Path` — creates JSONL file, appends started event
  - `write_completed(invocation_id: str, repo_root: Path, outcome: str | None, evidence_ref: str | None)` — appends completed event
  - Raises `InvocationWriteError` on filesystem failure (non-zero exit in executor)
- `registry.py`: `ProfileRegistry` thin wrapper
  - `get(profile_id: str) -> AgentProfile | None`
  - `list_all() -> list[AgentProfile]`
  - `resolve(profile_id: str) -> AgentProfile` (raises `ProfileNotFoundError` on miss)
- `errors.py`: `RouterAmbiguityError`, `ProfileNotFoundError`, `ContextUnavailableError`, `InvocationWriteError`
- `src/specify_cli/cli/commands/profiles_cmd.py`: `spec-kitty profiles list [--json]`
- Register `profiles` group in `main.py`
- Tests: executor happy path, degraded mode (no charter), registry fallback to shipped-only, JSONL writer append-only invariant, profiles list JSON output

**Files created**:
```
src/specify_cli/invocation/__init__.py
src/specify_cli/invocation/executor.py
src/specify_cli/invocation/record.py
src/specify_cli/invocation/writer.py
src/specify_cli/invocation/registry.py
src/specify_cli/invocation/errors.py
src/specify_cli/cli/commands/profiles_cmd.py
tests/specify_cli/invocation/__init__.py
tests/specify_cli/invocation/test_executor.py
tests/specify_cli/invocation/test_record.py
tests/specify_cli/invocation/test_writer.py
tests/specify_cli/invocation/test_registry.py
tests/specify_cli/invocation/cli/test_profiles.py
tests/specify_cli/invocation/fixtures/profiles/implementer.agent.yaml
tests/specify_cli/invocation/fixtures/profiles/reviewer.agent.yaml
kitty-specs/profile-invocation-runtime-audit-trail-01KPQRX2/adr-3-deterministic-action-router.md
```

**Files modified**:
```
src/specify_cli/cli/main.py  (add profiles group registration)
```

### WP4.2 — ADR-3 Action Router Implementation

**Entry gate**: ADR-3 document accepted (signed off in WP4.1).

**Scope**:
- `router.py`: `ActionRouter` class (pure function — no I/O, no LLM)
  - `route(request_text: str, profile_hint: str | None = None) -> RouterDecision | RouterAmbiguityError`
  - Uses `DEFAULT_ROLE_CAPABILITIES` from `src/doctrine/agent_profiles/capabilities.py`
  - Uses `AgentProfile.specialization.domain_keywords` (via registry)
  - Token normalization: lowercase, split on `r'[\s\W]+'`, drop stop-words from a fixed 30-word list
  - Precedence: exact hint → canonical_verb match → domain_keyword match → ambiguity
  - `CANONICAL_VERB_MAP: dict[str, str]` mapping aliases to canonical action tokens
  - `ActionRouterPlugin` Protocol stub (no-op, documents future extension point)
- `executor.py` updated: integrate `ActionRouter` into `invoke()` for the no-hint path

**Test coverage** (table-driven):
- Exact hint: supplied profile ID resolves correctly
- Canonical verb: `"implement the feature"` → IMPLEMENTER profile
- Domain keyword: project-specific keyword matches profile
- Ambiguity: `"help me"` → `RouterAmbiguityError` with candidates
- No match: request with no recognizable verbs or keywords → `RouterAmbiguityError` with empty candidates
- Hint with missing profile: `RouterAmbiguityError` with `ProfileNotFoundError` message
- Stop-word stripping: `"please do an implement"` still routes to IMPLEMENTER

**Files created**:
```
src/specify_cli/invocation/router.py
tests/specify_cli/invocation/test_router.py
```

**Files modified**:
```
src/specify_cli/invocation/executor.py  (wire router for no-hint path)
```

### WP4.3 — `advise` + `ask` + `profile-invocation complete` CLI Surfaces

**Entry gate**: WP4.2 approved.

**Scope**:
- `advise.py` CLI commands:
  - `spec-kitty advise <request> [--profile <name>] [--json]` → calls `ProfileInvocationExecutor.invoke()`
  - `spec-kitty ask <profile> <request> [--json]` → thin shim: `advise(request, profile_hint=profile)`
  - `spec-kitty profile-invocation complete --invocation-id <id> [--outcome <status>] [--evidence <path>]` → calls `InvocationWriter.write_completed()`
- Rich console output (non-JSON path): profile name, action, governance context text (scrollable), invocation ID in muted footer
- JSON output (`--json`): full `InvocationPayload` serialized
- Error output: structured JSON to stderr for all error paths; non-zero exit code
- Register `advise` and `ask` groups, `profile-invocation` group in `main.py`
- Integration tests: `CliRunner` tests covering all three commands, happy path + error paths

**Files created**:
```
src/specify_cli/cli/commands/advise.py
tests/specify_cli/invocation/cli/test_advise.py
```

**Files modified**:
```
src/specify_cli/cli/main.py  (register advise, ask, profile-invocation groups)
```

### WP4.5 — `do` Command

**Entry gate**: WP4.2 approved.

**Scope**:
- `do_cmd.py` (or added to `advise.py`) — `spec-kitty do <request> [--json]`
- Delegates to `ProfileInvocationExecutor.invoke(request, profile_hint=None)` — router always invoked
- Same output contract as `advise`
- Register `do` command in `main.py`
- Integration tests: router-path invocation, ambiguity error surfaces correctly

**Files created**:
```
src/specify_cli/cli/commands/do_cmd.py
tests/specify_cli/invocation/cli/test_do.py
```

**Files modified**:
```
src/specify_cli/cli/main.py  (register do command)
```

### WP4.6 — `MinimalViableTrailPolicy` Formal Artifact + Tier Promotion API

**Entry gate**: WP4.1 approved (MinimalViableTrailPolicy stub exists).

**Scope**:
- Finalize `MinimalViableTrailPolicy` in `record.py` with all three tiers fully specified as frozen dataclasses
- Add `tier_eligible(record: InvocationRecord) -> TierEligibility` function: determines which tiers an invocation qualifies for based on `outcome`, `evidence_ref`, and `action`
- Add `promote_to_evidence(record: InvocationRecord, evidence_dir: Path, content: str) -> EvidenceArtifact` — creates Tier 2 artifact at `.kittify/evidence/<invocation_id>/`
- Policy is importable by all surfaces: `from specify_cli.invocation.record import MINIMAL_VIABLE_TRAIL_POLICY`
- Tests: tier eligibility decisions, evidence artifact creation, policy constant immutability

**Files modified**:
```
src/specify_cli/invocation/record.py  (finalize MinimalViableTrailPolicy, add tier functions)
tests/specify_cli/invocation/test_record.py  (extend with tier tests)
```

### WP4.8 — `invocations list` + Skill Pack Updates

**Entry gate**: WP4.1 approved.

**Scope**:
- `invocations_cmd.py`: `spec-kitty invocations list [--profile <name>] [--limit N] [--json]`
  - Scans `.kittify/events/profile-invocations/` using `Path.glob("<profile_id>-*.jsonl")` (filtered by `--profile`) or `Path.glob("*.jsonl")` (all)
  - Reads last line of each JSONL file for current record state
  - Sorts by `started_at` descending, truncates to `--limit` (default 20)
  - Output: JSON array or rich table with profile, action, status, started_at columns
- Performance: O(n) file reads where n = min(total_files, limit * 2). For 10,000 JSONL files: directory scan + read last line of 10,000 files. If ≥ 200ms on CI, optimize to an index file (`.kittify/events/invocation-index.jsonl`) maintained by the writer. Benchmark in WP4.8.
- Skill pack updates: update `.agents/skills/spec-kitty.advise/SKILL.md` (new), add `advise`/`ask`/`do` documentation to harness skill packs
- Register `invocations` group in `main.py`
- Integration tests: query with profile filter, empty log, limit truncation

**Files created**:
```
src/specify_cli/cli/commands/invocations_cmd.py
tests/specify_cli/invocation/cli/test_invocations.py
.agents/skills/spec-kitty.advise/SKILL.md  (new skill pack doc)
```

**Files modified**:
```
src/specify_cli/cli/main.py  (register invocations group)
```

### WP4.7 — SaaS Propagation

**Entry gate**: WP4.8 approved. WP4.7 entry gate also requires CLI-SaaS contract field coverage verification (R-0-5).

**Scope**:
- `propagator.py`: `InvocationSaaSPropagator`
  - `propagate(record: InvocationRecord, repo_root: Path) -> None`
  - Submits to `ThreadPoolExecutor(max_workers=1)`; registers `atexit` shutdown (5-second timeout)
  - On SaaS client error: appends to `.kittify/events/propagation-errors.jsonl`
  - Uses `invocation_id` as SaaS idempotency key
  - Reads SaaS token from existing auth store (same path as charter sync uses)
  - If no SaaS token configured: no-op, no warning
- `executor.py` updated: inject propagator after `write_completed()`
- SaaS contract adapter: maps `InvocationRecord` fields to `ProfileInvocationStarted` / `ProfileInvocationCompleted` envelope types from existing CLI-SaaS contract
- Tests (offline): mock SaaS client, verify non-blocking behavior, verify error logging, verify idempotency key is set, verify no-op when token absent

**Files created**:
```
src/specify_cli/invocation/propagator.py
tests/specify_cli/invocation/test_propagator.py
```

**Files modified**:
```
src/specify_cli/invocation/executor.py  (inject propagator after write_completed)
```

---

## Review & Validation Strategy

### FR → Test Matrix

| FR | Test Location | Test Type | Key Assertion |
|----|---------------|-----------|---------------|
| FR-001 (executor is single primitive) | test_executor.py | Unit | `advise`/`ask`/`do` all call `ProfileInvocationExecutor.invoke()` |
| FR-002 (profiles list) | cli/test_profiles.py | Integration | JSON array with required fields |
| FR-003 (advise contract) | cli/test_advise.py | Integration | Returns invocation_id, profile_id, governance_context_text |
| FR-004 (ask = advise --profile) | cli/test_advise.py | Integration | Same payload as advise with explicit profile |
| FR-005 (do routes via router) | cli/test_do.py | Integration | Router path invoked, payload matches expected profile |
| FR-006 (JSONL written before return) | test_writer.py | Unit | File exists before executor returns |
| FR-007 (invocations list) | cli/test_invocations.py | Integration | Returns sorted records, filter works |
| FR-008 (open record on every invoke) | test_executor.py | Unit | JSONL file created even when complete not called |
| FR-009 (write failure → exit 1) | test_writer.py | Unit | `InvocationWriteError` → non-zero exit |
| FR-010 (router interface + ADR) | test_router.py + ADR-3 doc | Unit + artifact | ADR doc exists before WP4.2 merges |
| FR-011 (ambiguity → structured error) | test_router.py | Unit | `RouterAmbiguityError` with candidates list |
| FR-012 (governance context from DRG) | test_executor.py | Unit | `build_charter_context` called with profile+action |
| FR-013 (event storage path) | test_writer.py | Unit | Path matches `<profile_id>-<invocation_id>.jsonl` |
| FR-014 (v1 schema fields) | test_record.py | Unit | All 9 required fields present and typed |
| FR-015 (SaaS non-blocking) | test_propagator.py | Unit | Mock SaaS 5xx: main thread returns in < 500ms |
| FR-016 (SaaS idempotency) | test_propagator.py | Unit | Idempotency key = invocation_id |
| FR-017 (trail tier policy) | test_record.py | Unit | `MINIMAL_VIABLE_TRAIL_POLICY` constant is frozen |
| FR-018 (intake not wired) | test_executor.py + cli/test_intake.py | Unit | intake command leaves 0 JSONL records |
| FR-019 (workflow hooks are stubs) | test_executor.py | Unit | `router_plugin=None` path produces no error, no additional behavior |

### Performance Assertions

| NFR | Test | Threshold |
|-----|------|-----------|
| NFR-001 (advise < 500ms) | `test_executor.py::test_invoke_latency` with fixture profiles + no-charter degraded mode | < 500ms |
| NFR-008 (invocations list < 200ms at 10K) | `test_invocations.py::test_list_large_log` with 10K synthetic JSONL files | < 200ms |

### Gate Sequence (per WP)

1. **WP4.1**: ADR-3 doc committed → mypy --strict passes → 90%+ coverage → `profiles list` CLI integration test passes
2. **WP4.2**: ADR-3 doc signed off → router unit tests pass (all 7 table-driven cases) → mypy passes
3. **WP4.3**: advise/ask/complete integration tests pass → FR-003, FR-004, FR-006, FR-008 verified
4. **WP4.5**: do integration test passes → FR-005 verified
5. **WP4.6**: tier policy frozen → FR-017 verified → Pydantic model final
6. **WP4.8**: invocations list integration test passes → performance gate (< 200ms at 10K)
7. **WP4.7**: SaaS contract field coverage verified → propagator unit tests pass → FR-015, FR-016 verified

---

## Risks & Premortem

| Risk | Trigger | Mitigation |
|------|---------|------------|
| R-1: Router ambiguity is too frequent in practice | Real requests rarely match canonical verbs cleanly | WP4.2 must include a human-reviewed sample of 20 typical requests against the router before the WP is approved. If > 30% produce RouterAmbiguityError, expand the alias table before shipping WP4.5. |
| R-2: CLI-SaaS contract schema gap (R-0-5) | `ProfileInvocationStarted` missing fields for v1 `InvocationRecord` | WP4.7 entry gate: reviewer must verify contract against schema. If gap found, treat as a blocking issue. Do NOT adapt silently — raise with spec-kitty-saas team. |
| R-3: `invocations list` latency at large log | 10,000+ JSONL files → directory scan is slow | WP4.8 benchmarks this. If > 200ms, add an append-only index at `.kittify/events/invocation-index.jsonl` maintained by `write_started`. NFR-008 is a hard gate. |
| R-4: SaaS propagation thread leaks on long-running processes | Host-LLM runs as a long-lived process; invocation propagation threads accumulate | `atexit` shutdown with `wait=True, cancel_futures=True` and 5-second timeout. Each `invoke()` call creates at most one thread submission; the executor does not hold an open thread pool between calls. |
| R-5: `intake` scope creep | Future contributor accidentally routes intake through executor | FR-018 and C-005 are explicit. `test_executor.py` includes a negative test: calling `intake` must leave 0 JSONL records. This test is a regression guard. |
| R-6: Profile source confusion | Operator has shipped profiles but expects project-local profiles to override | `ProfileRegistry` logs which source each profile was loaded from (shipped vs project-local) at debug level. `profiles list --json` includes a `source` field per descriptor. |
| R-7: `mark_loaded=False` breaks first-load tracking | If `build_charter_context` is called with `mark_loaded=True` by mistake, `specify`/`plan` flows see incorrect first-load state | Verified in test_executor.py: assert that `context-state.json` is not modified after `invoke()`. Explicit in executor docstring. |

---

## Report

**Branch contract (final confirmation)**:
- Current branch at plan start: `main`
- Planning/base branch: `main`
- Final merge target for completed changes: `main`
- `branch_matches_target: true`

**Artifacts produced by this plan**:
| Artifact | Path | Status |
|----------|------|--------|
| plan.md | `kitty-specs/profile-invocation-runtime-audit-trail-01KPQRX2/plan.md` | This file |
| research.md | `kitty-specs/profile-invocation-runtime-audit-trail-01KPQRX2/research.md` | Phase 0 complete |
| data-model.md | `kitty-specs/profile-invocation-runtime-audit-trail-01KPQRX2/data-model.md` | Phase 1 complete |
| contracts/ | `kitty-specs/profile-invocation-runtime-audit-trail-01KPQRX2/contracts/` | Phase 1 complete |
| quickstart.md | `kitty-specs/profile-invocation-runtime-audit-trail-01KPQRX2/quickstart.md` | Phase 1 complete |
| ADR-3 | `kitty-specs/profile-invocation-runtime-audit-trail-01KPQRX2/adr-3-deterministic-action-router.md` | Phase 1 complete |

**Next step**: `/spec-kitty.tasks` to generate work packages.
