# Implementation Plan: MissionStatus Write-Path Completion & Profile-Load Surface Remediation

**Branch**: `feature/status-writepath-profile-surface-remediation` | **Date**: 2026-06-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/status-writepath-profile-surface-remediation-01KTB6AN/spec.md`
**Research**: [research.md](./research.md)

## Summary

Two independent, contained remediations delivered as parallel lanes:

- **Workstream A (#1667 residual):** the `MissionStatus` aggregate read path is shipped and tested; its write methods (`transition()`, `save()`) are implemented but **untested and unwired** (RISK-001). Add unit coverage (happy + rejection + receipt), resolve the write-path wiring question (D-1), add fail-closed guards (`_read_meta`, slug allowlist), and extend the #1672 CWD-parity ratchet over the status write surface. **No new abstractions; no change to `BookkeepingTransaction`.**
- **Workstream B (#1636):** make `profile list` activation-aware and add an activation-gated `profile show`, both routed through the existing charter activation chokepoint (`charter.resolver.DoctrineService`) via one shared factory; route `charter context --include agent-profile:<id>` through the same seam; reconcile the `ad-hoc-profile-load` skill's four phantom commands; add a doc/CLI parity guard. Lineage gate = **Option A** (abstract base profiles allowed, with a warning).

Technical approach is **wire-through-existing-seams**, not greenfield. Both the status aggregate and the activation wrapper already exist; the work is test coverage, one factory, CLI surface, and doc reconciliation.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase)
**Primary Dependencies**: typer (CLI), rich (console), ruamel.yaml (config/frontmatter), pytest (tests); internal: `specify_cli.status`, `specify_cli.coordination`, `charter.resolver`, `charter.pack_context`, `doctrine.service`, `doctrine.agent_profiles`
**Storage**: Filesystem only — `.kittify/config.yaml` (`activated_agent_profiles`), `kitty-specs/<mission>/status.events.jsonl`; no database
**Testing**: pytest; unit (`tests/status/`, `tests/specify_cli/cli/commands/`), architectural (`tests/architectural/`); headless `PWHEADLESS=1` where applicable; `mypy --strict` + `ruff`
**Target Platform**: Cross-platform CLI (Linux/macOS/Windows), Python 3.11+
**Project Type**: single (CLI library)
**Performance Goals**: No new hot paths; profile listing/show are interactive-latency commands; parity ratchet ≤ existing wall-clock budget
**Constraints**: Zero change to `coordination/transaction.py` (NFR-002); `profile list` non-breaking for unconfigured projects (NFR-001); layer rule `doctrine ← charter` preserved (C-005); source-template edits only, never generated agent copies (C-006)
**Scale/Scope**: ~6-8 touched source files + tests across two lanes; no migration of on-disk data

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate (charter `--action plan`) | Assessment |
|---|---|
| DIR-005 Tests for new functionality | ✅ FR-001..003, FR-008, FR-018 are test-first deliverables |
| DIR-006 Type annotations (`mypy --strict`) | ✅ all new code typed; factory + `profile show` fully annotated |
| DIR-007 Docstrings for public APIs | ✅ new factory + command + aggregate write methods get docstrings |
| DIR-010/011 Identifier safety (ASCII allowlist) | ✅ FR-007 slug allowlist `[A-Za-z0-9_-]` with regression coverage |
| DIR-031 Bounded-context boundary | ✅ wrapper stays in `charter.*`; CLI in `specify_cli.*` (C-005) |
| DIR-032 Conceptual alignment / vocabulary | ⚠️ route new terms to glossary (abstract base profile, activation chokepoint) before/within plan; no code-before-vocab violation since no new domain model |
| DIR-003 Decision documentation | ✅ D-2 (lineage) recorded; D-1 resolved here in plan; short design note for activation gating |

**Verdict:** PASS. No charter violation requires Complexity Tracking. One advisory: confirm glossary terms during implementation (non-blocking).

## Resolved Decisions (from spec Open/Unresolved)

- **D-1 (write-path wiring) — RESOLVED → 1b (façade-over-existing).** The aggregate's `transition()` already delegates to `coordination/status_transition.emit_status_transition_transactional` (the live transactional caller). We will **not** invent a new production call site in this mission. Instead: (a) add the missing unit coverage proving the delegation works; (b) add one **integration test** that drives a real lane transition through `MissionStatus.transition()`+`.save()` end-to-end so the methods have a genuine exercised caller (the test is the live caller, plus the parity ratchet extension exercises the same path); (c) document `MissionStatus.{transition,save}` in the module as the sanctioned aggregate API over the transactional plumbing. This closes RISK-001's "no live caller / no coverage" without premature re-wiring of `agent/status.py` (which is a read surface). Re-wiring write callers belongs to #1673 residue routing, kept out of scope (C-007).
- **D-2 (lineage gate) — Option A + warning** (operator decision; abstract base profiles).
- **D-3 (#1672 scope) — narrow slice** (FR-008).
- **D-4 (`profile_not_activated` schema)** — finalized in contracts below.

## Project Structure

### Documentation (this feature)

```
kitty-specs/status-writepath-profile-surface-remediation-01KTB6AN/
├── plan.md            # this file
├── spec.md            # complete spec (FR-001..018)
├── research.md        # verified seam maps + current state
├── data-model.md      # Phase 1 — entities + contracts (this plan authors it)
└── tasks.md           # Phase 2 — /spec-kitty.tasks (NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/
├── status/
│   └── aggregate.py                 # A: docstring write methods; FR-006 _read_meta guard; FR-007 slug allowlist
├── cli/commands/
│   ├── profiles_cmd.py              # B: activation-aware list + new `show`/`get` command (FR-011..014)
│   └── charter/context_*.py         # (only if needed) ensure --include path uses wrapper
└── <new> doctrine_service_factory   # B: build_activation_aware_doctrine_service() (FR-010)
                                     #    placement: a shared module importable by profiles_cmd
                                     #    + charter.context (candidate: specify_cli/charter_runtime/ or
                                     #    a thin specify_cli/doctrine/ helper — decided in data-model)

src/charter/
└── context.py                       # B: _build_doctrine_service() returns the wrapped service (FR-016)

src/doctrine/skills/ad-hoc-profile-load/
└── SKILL.md                         # B: reconcile 4 phantom commands (FR-017) — SOURCE template, not copies

tests/
├── status/
│   └── test_mission_status_aggregate.py     # A: + transition()/save() unit coverage (FR-001..003)
├── architectural/
│   ├── test_execution_context_parity.py     # A: extend over write transition (FR-008)
│   └── test_docs_cli_reference_parity.py     # B: extend / add profile-command parity guard (FR-018)
└── specify_cli/cli/commands/
    └── test_profiles_cmd.py                  # B: list activation filtering + show gating + lineage warning
```

**Structure Decision**: Single-project CLI library. Workstream A is confined to `status/aggregate.py` + its test file + the architectural ratchet. Workstream B is confined to `profiles_cmd.py` + one new factory module + `charter/context.py` + the SKILL source + tests. The two lanes share **no** files → they can be implemented and reviewed fully in parallel.

## Architecture & Data Flow

### Workstream A — write-path completion

```
caller (test / future surface)
   │  TransitionRequest
   ▼
MissionStatus.transition(request)
   │  1. validate_transition(from, to, GuardContext)   ← domain invariant (status/transitions.py)
   │  2. emit_status_transition_transactional(request) ← existing live transactional path
   ▼
BookkeepingTransaction.acquire → append_event → materialize → commit   (UNCHANGED infra)
   │
   ▼  CommitReceipt  ◄── MissionStatus.save(operation=...)
```

- `transition()` validates **before** any append (FR-002 fail-closed).
- `save()` returns the `CommitReceipt` from the transaction (FR-003).
- `_read_meta` (FR-006): distinguish "file absent" (legacy → `(None, False)` OK) from "present-but-unreadable" (→ typed error, fail closed).
- `load()` (FR-007): slug allowlist guard at entry.

### Workstream B — activation chokepoint wiring

```
.kittify/config.yaml :: activated_agent_profiles (3-state)
   │ PackContext.from_config(repo_root)
   ▼
build_activation_aware_doctrine_service(repo_root)   ← NEW single factory (FR-010)
   = charter.resolver.DoctrineService(inner, pack_context)
   │ .agent_profiles → activation-filtered dict
   ├── profile list   (default filtered; --all/--show-available → inner.list_all annotated)
   ├── profile show    (gate leaf via .get(id); resolve lineage via inner repo; warn on non-activated parent)
   └── charter context --include agent-profile:<id>   (_build_doctrine_service returns wrapped)
```

## Interfaces & Contracts (Phase 1 — detailed in data-model.md)

- `build_activation_aware_doctrine_service(repo_root: Path) -> charter.resolver.DoctrineService`
- `profile list [--all] [--show-available] [--json]` — default = activated-only
- `profile show <id> [--all] [--json]` — activated-gated; `--json` emits stable sorted-key schema
- `profile_not_activated` error (D-4): `{ "error": "profile_not_activated", "profile_id": <id>, "activated_candidates": [<sorted ids>] }`
- Lineage warning (FR-015): non-fatal stderr/`warnings[]` field naming non-activated ancestors

## Migration / Rollout

- **No data migration.** `activated_agent_profiles` semantics unchanged; absent key → all built-ins (NFR-001).
- Rollout is additive: new `show` command + a flag on `list`; existing `list` default narrows only for projects that explicitly restricted profiles.
- Skill reconciliation ships as a doctrine source-template edit; propagates to agent copies on `spec-kitty upgrade` (do **not** hand-edit generated copies, C-006).

## Test Strategy

| FR | Test | Type |
|----|------|------|
| FR-001/002 | `transition()` happy + illegal-pair rejection | unit |
| FR-003 | `save()` returns `CommitReceipt` w/ event_ids | unit/integration |
| FR-004 | integration: real lane transition through aggregate write API | integration |
| FR-006/007 | `_read_meta` typed error; slug allowlist (incl. accented + `.isascii()` per DIR-011) | unit |
| FR-008 | parity ratchet extended over write transition, both CWDs | architectural |
| FR-011/012 | `list` activation filtering (3-state) + `--all`/`--show-available` annotation | unit |
| FR-013/014 | `show` full def + activation gate + structured not-found | unit |
| FR-015 | lineage Option A: abstract-parent resolves + warning; `show <parent>` gated | unit |
| FR-016 | `--include agent-profile` inherits gate | unit |
| FR-017/018 | SKILL.md references only real commands; doc/CLI parity guard | architectural |

## Risks

| Risk | Mitigation |
|------|-----------|
| Write-path integration test needs real coord topology (git worktree) | reuse the parity-ratchet fixture pattern (`test_execution_context_parity.py` already builds a real worktree) |
| Factory placement could violate layer rule | factory lives in `specify_cli.*`, imports `charter.resolver`/`pack_context` (allowed direction); confirmed in data-model |
| `profile list` default change surprises a configured project | documented as intended (NFR-001); `--all` escape hatch; release note |
| Skill copies drift again | FR-018 parity guard test is the structural backstop |

## Complexity Tracking

*No Charter Check violations. No entries required.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
