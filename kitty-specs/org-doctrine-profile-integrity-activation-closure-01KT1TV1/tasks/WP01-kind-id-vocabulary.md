---
work_package_id: WP01
title: Canonical kind & ID vocabulary resolver
dependencies: []
requirement_refs:
- FR-027
tracker_refs: []
planning_base_branch: mission/org-doctrine-profile-integrity-activation-closure
merge_target_branch: mission/org-doctrine-profile-integrity-activation-closure
branch_strategy: Planning artifacts for this mission were generated on mission/org-doctrine-profile-integrity-activation-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/org-doctrine-profile-integrity-activation-closure unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-org-doctrine-profile-integrity-activation-closure-01KT1TV1
base_commit: 4ecfe5250856f5ef2180aa091e495dccfa93652e
created_at: '2026-06-01T23:42:10.946447+00:00'
subtasks:
- T001
- T002
- T003
- T004
agent: claude:opus:python-pedro:implementer
shell_pid: '1719915'
history:
- at: '2026-06-01T16:49:18Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/charter/kind_vocabulary.py
execution_mode: code_change
mission_slug: org-doctrine-profile-integrity-activation-closure-01KT1TV1
owned_files:
- src/doctrine/artifact_kinds.py
- src/charter/kind_vocabulary.py
- tests/charter/test_kind_vocabulary.py
role: implementer
tags: []
---

# WP01 — Canonical kind & ID vocabulary resolver

## ⚡ Do This First: Load Agent Profile

Before reading the rest of this WP, load the assigned agent profile via:

```
/ad-hoc-profile-load python-pedro
```

This injects the Python implementation doctrine for this codebase.

## Objective

Create the single canonical mapping for two vocabularies that are currently re-declared across five+ modules with three incompatible spellings (research R-009): (1) operator **kind tokens** (hyphenated, e.g. `agent-profile`) → canonical `ArtifactKind`; (2) artifact **config-stem IDs** ↔ **DRG URN node IDs**. Downstream WPs (WP09 pack-manager, WP16 list, WP17 context) will route through this instead of maintaining their own tables. This WP delivers the resolver and tests only — it does **not** rewire consumers (they own their own files).

## Context

- Spec: [../spec.md](../spec.md) — FR-027; research [../research.md](../research.md) R-009 (the five fragmented tables), R-011-D (the dual config-stem-vs-DRG-`id` system).
- Data model: [../data-model.md](../data-model.md) §1.
- Contract: [../contracts/wave0-foundation.md](../contracts/wave0-foundation.md) C0.1.

### Code map (read first)

- `src/doctrine/artifact_kinds.py` — `ArtifactKind` StrEnum (canonical singular), `_PLURALS`, `_PATTERNS`, `from_plural`. **Extend here.**
- `src/charter/pack_manager.py:104` `_KIND_TO_DOCTRINE_DIR`, `YAML_KEY_MAP` (hyphen keys incl. `mission-type`) — reference only (rewired in WP09).
- `src/charter/activations.py:159` `_SINGULAR_TO_PLURAL_KIND` / `normalize_artifact_kind` (underscore singular→plural; **does NOT handle hyphens** — that gap is why `--include agent-profile` fails).
- `src/charter/catalog.py:215` `_extract_artifact_id` — already reads the `id:` field; reuse for the ID resolver.
- Charter kind universe = the 8 `ArtifactKind` artifact kinds **+ `mission-type`** (which is NOT an `ArtifactKind` member). `template` IS a member but resolves specially.

## Branch Strategy

- Planning/base branch: `mission/org-doctrine-profile-integrity-activation-closure`
- Final merge target: `mission/org-doctrine-profile-integrity-activation-closure`
- Execution worktrees are allocated per computed lane from `lanes.json`; this WP has no dependencies so it can start immediately.

## Subtasks

### T001 — `ArtifactKind.from_operator_token` + mission-type handling

**Purpose**: One total function mapping the documented operator token to a canonical kind.

**Steps**:
1. In `src/doctrine/artifact_kinds.py`, add a classmethod `from_operator_token(cls, token: str) -> ArtifactKind` that:
   - lowercases and normalizes hyphens to underscores (`agent-profile` → `agent_profile`, `mission-step-contract` → `mission_step_contract`).
   - returns the matching member, else raises `ValueError` with a message listing valid operator tokens (no silent fallback — R-009/CL-1).
2. Add a helper `operator_token` property returning the hyphenated form (inverse), for help text and error messages.
3. Mission-type: `mission-type` is not an `ArtifactKind`. Add a module-level sentinel/handling note: expose `CHARTER_KIND_TOKENS: tuple[str, ...]` = the 8 artifact-kind operator tokens + `"mission-type"`. `from_operator_token("mission-type")` must raise a *distinct, documented* error (or a typed sentinel) so callers route mission-type explicitly. Document the choice in the docstring.

**Files**: `src/doctrine/artifact_kinds.py`

**Validation**:
- [ ] `from_operator_token("agent-profile") is ArtifactKind.AGENT_PROFILE`; same for all 8 kinds via hyphen tokens.
- [ ] Unknown token raises `ValueError` listing valid tokens.
- [ ] `mypy` clean; zero-dependency rule preserved (no imports from `charter`/`specify_cli`).

### T002 — Artifact ID resolver (config-stem ↔ DRG URN)

**Purpose**: Resolve a config/file-stem ID (e.g. `001-architectural-integrity-standard`) to a DRG URN node ID (e.g. `directive:DIRECTIVE_001`) and back, using the artifact's `id:` field — the seam that unblocks cascade (WP11) and consistency checks.

**Steps**:
1. Create `src/charter/kind_vocabulary.py` (charter layer — may import `doctrine`, never `specify_cli`).
2. Implement `resolve_artifact_urn(kind: ArtifactKind, config_id: str, *, doctrine_root: Path, org_roots: list[Path] | None = None) -> str` that reads the artifact's `id:` field (reuse the logic behind `charter.catalog._extract_artifact_id`) and returns `f"{kind.value}:{artifact_id}"`.
3. Implement the inverse `resolve_config_id(urn: str, ...) -> str`.
4. Raise a structured error if the ID is unknown for the kind (used by WP10 unknown-ID validation).
5. Keep org/project roots as **parameters passed in as data** (C-008) — do not resolve them here.

**Files**: `src/charter/kind_vocabulary.py`

**Validation**:
- [ ] Round-trip: `resolve_config_id(resolve_artifact_urn(k, id)) == id` for a built-in sample of each kind.
- [ ] Unknown ID raises a structured error naming kind + id.

### T003 — Unit tests

**Steps**: Add `tests/charter/test_kind_vocabulary.py` covering token normalization (all 8 kinds + mission-type behavior + unknown), and ID round-trip for at least directive/tactic/agent_profile using real built-in artifacts.

**Validation**: - [ ] `pytest tests/charter/test_kind_vocabulary.py` green; - [ ] `ruff` + `mypy` clean.

### T004 — Document the canonical charter kind universe

**Steps**: Add a module docstring to `kind_vocabulary.py` (and a short note in `artifact_kinds.py`) stating: charter kinds = `ArtifactKind` artifact kinds + `mission-type`; `template` is addressed specially (no glob); consumers must route kind strings through `from_operator_token` (CC-4). Reference R-009.

**Validation**: - [ ] Docstring present and accurate; reviewer can see the universe without grepping five files.

## Definition of Done

- [ ] All four subtasks complete; `from_operator_token` + ID resolver implemented with tests.
- [ ] `ruff check .`, `mypy src`, and the new tests pass (CC-2).
- [ ] Zero-dependency rule for `doctrine.artifact_kinds` preserved; `charter/kind_vocabulary.py` imports only `doctrine`+`kernel`.
- [ ] No consumer rewiring done here (that is WP09/16/17 scope).
- [ ] **C-007 (binding):** `src/charter/kind_vocabulary.py` declares `__all__`. Its exported symbols gain callers only in later-merging WPs (WP09/16/17); the dead-symbol gate is satisfied at mission-merge when those land. Do not add a permanent allowlist entry to paper over the interim (Burn-down Policy: no net allowlist growth) — coordinate with WP15/#1588 if a lane evaluates the gate in isolation.

## Risks

- **Mission-type asymmetry**: do not force `mission-type` into `ArtifactKind`; that is a separate decision handled in WP04 (FR-032). Keep it an explicit token here.
- **Scope creep**: resist editing `pack_manager.py`/`context.py` — those belong to other WPs and would create ownership overlap.

## Reviewer Guidance (reviewer-renata)

- Confirm no silent fallback on unknown tokens (R-009/CL-1 intent).
- Confirm the ID resolver takes roots as data (C-008) and does not import `specify_cli`.
- Verify the canonical-universe docstring matches the 8+mission-type reality.

## Activity Log

- 2026-06-01T17:28:54Z – claude:opus:python-pedro:implementer – shell_pid=1544264 – Assigned agent via action command
- 2026-06-01T17:34:38Z – claude:opus:python-pedro:implementer – shell_pid=1544264 – Implementation complete & committed (RED+GREEN); ruff/mypy/pytest green (36 tests). Subtasks T001-T004 marked done. BLOCKED on move-task to for_review: WP has no canonical lane status (status.json event_count=0, work_packages={}); event log holds WPCreated/Specify/Plan events but ZERO lane-transition events for any WP. Lane status never bootstrapped (guard: lane states WP01=uninitialized). Fix is mission-wide finalize-tasks/bootstrap, outside WP01 owned-file scope and forbidden by WP-isolation rules. Needs orchestrator/mission-setup action.
- 2026-06-01T19:14:50Z – claude:opus:python-pedro:implementer – shell_pid=1544264 – reset blocked->planned
- 2026-06-01T22:52:13Z – claude:opus:python-pedro:implementer – shell_pid=1685112 – Started implementation via action command
- 2026-06-01T22:52:44Z – claude:opus:python-pedro:implementer – shell_pid=1685112 – WP01 recovered: canonical kind/ID vocabulary resolver; 36 tests green
