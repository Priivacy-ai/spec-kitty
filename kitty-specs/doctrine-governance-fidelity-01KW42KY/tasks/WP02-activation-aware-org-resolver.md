---
work_package_id: WP02
title: Charter-activation-aware org-profile resolver
dependencies: []
requirement_refs:
- FR-003
- FR-007
tracker_refs: []
planning_base_branch: mission/doctrine-governance-fidelity
merge_target_branch: mission/doctrine-governance-fidelity
branch_strategy: Planning artifacts for this mission were generated on mission/doctrine-governance-fidelity. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/doctrine-governance-fidelity unless the human explicitly redirects the landing branch.
subtasks:
- T004
- T005
- T006
phase: Lane B — org-pack profile consolidation
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "964928"
history:
- at: '2026-06-27T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/invocation/
create_intent:
- src/specify_cli/invocation/org_profiles.py
- tests/specify_cli/invocation/test_org_profiles.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/invocation/org_profiles.py
- tests/specify_cli/invocation/test_org_profiles.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Charter-activation-aware org-profile resolver

## ⚡ Do This First: Load Agent Profile

Load `python-pedro` via the `/ad-hoc-profile-load` skill (read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml`) and adopt its directives before implementing.

- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent**: `claude`

---

## Objectives & Success Criteria

- A single new helper, `resolve_activated_org_profiles(repo_root) -> list[AgentProfile]`, returns the **charter-activated org-provenance subset** of profiles — composed from `resolve_org_roots` + `PackContext.activated_agent_profiles` via the existing `build_activation_aware_doctrine_service` (FR-003). It is the one seam every org-honouring consumer (WP03 dispatch/context, WP04 projection) calls — they NEVER splice raw `org_dirs` (C-008).
- The helper is **pure** and **fail-closed**: a malformed allowlist / DRG must not flip a de-activated profile to admitted (NFR-004). It returns only org-provenance profiles, provenance-tagged so WP04 can set a non-builtin `source_layer` (FR-007, C-002).
- Three-regime activation contract honoured: `activated_agent_profiles` absent (`None`) → **all** org profiles admitted (backward-compat / #2156 install→visible); explicit list **including** an id → present; explicit list **excluding** an id → absent (C-008).

**Done when**: the 3-regime + fail-closed tests pass red-first against a real-format org-pack fixture; the helper reuses the activation wrapper (no re-implemented gate, no raw `org_dirs` returned); ruff + mypy clean, complexity ≤ 15.

## Context & Constraints

- **Charter is the org-resolution entry point (C-008).** The activation gate lives at `src/charter/resolver.py:121-130` — `DoctrineService.agent_profiles` filters the merged profile set by `PackContext.activated_agent_profiles` (three-state). It sits **two layers above** `resolve_org_roots`, so a thin wrapper over `resolve_org_roots` alone would surface declared-but-**de-activated** org profiles (research.md "Architectural-alignment squad", row 3 of debbie's 4×4 matrix = the bypass). REUSE `build_activation_aware_doctrine_service` at `src/specify_cli/doctrine_service_factory.py:38` — it already builds the inner `DoctrineService(org_roots=resolve_org_roots(...))` and wraps it with the activation-aware `charter.resolver.DoctrineService` + `PackContext.from_config(repo_root)`. **Never re-implement the gate (C-006).**
- **Org-provenance subset only (C-002, FR-007).** `build_activation_aware_doctrine_service(...).agent_profiles` returns the full merged dict (built-in ⊕ org ⊕ project). This helper must return ONLY the org-provenance members — do not leak built-in/project profiles, and do not collapse the project layer into this overlay. Provenance is exposed by the repository via `get_provenance(profile_id)` which tags the org layer as `"org"` (`src/doctrine/agent_profiles/repository.py:353-357, :566`). Confirm how to recover provenance through the activation wrapper during T005 (the wrapper delegates unknown attributes to the inner service via `__getattr__` at `resolver.py:136-139`, so the inner repository's `get_provenance` is reachable).
- **Layer rule (import-cycle avoidance).** The new file lives in `specify_cli.*` — the allowed dependency direction is `specify_cli → charter → doctrine` (see `doctrine_service_factory.py` module docstring, lines 17-24). The factory itself already lives in `specify_cli`, so importing it from `specify_cli/invocation/org_profiles.py` is cycle-safe. Do **not** place this helper inside `charter.*` or `doctrine.*`.
- **`None` default semantics.** When `PackContext.activated_agent_profiles is None`, the wrapper applies no filter, so all org profiles are admitted. This is the common-case backward-compat path (#2156 install→visible) and must be preserved.
- **Canonical seam (C-006).** `resolve_org_roots(repo_root)` is `src/doctrine/drg/org_pack_config.py:263`. Do not hand-roll org-root resolution.
- **C-005 red-first** through the helper's observable behaviour over a real org-pack fixture. **C-007** realistic fixtures: real-format pack id, `<pack>/agent_profiles/<id>.agent.yaml`, profile id like `orgzilla-org-analyst`. **NFR-003** ruff/mypy clean, focused test per branch.

## Subtasks & Detailed Guidance

### Subtask T004 — RED 3-regime activation-filter test

- **Purpose**: Witness the contract before the helper exists (and pin all three regimes so a later raw-`org_dirs` regression is caught).
- **Steps**: In `tests/specify_cli/invocation/test_org_profiles.py`, build a real-format org-pack fixture on disk: a scratch `repo_root` with `.kittify/config.yaml` declaring `doctrine.org.packs[].local_path` pointing at a pack dir, and the profile at `<pack>/agent_profiles/orgzilla-org-analyst.agent.yaml` (valid `.agent.yaml` shape: `profile-id`, `name`, `roles`, `schema-version`). Parametrise the three regimes via `.kittify/config.yaml` activation state:
  - **absent** (no `activated_agent_profiles` key) → `resolve_activated_org_profiles(repo_root)` contains `orgzilla-org-analyst`.
  - **explicit list INCLUDING** `orgzilla-org-analyst` → present.
  - **explicit list EXCLUDING** it (e.g. `["python-pedro"]`) → **absent**.
  - Assert the returned profiles are org-provenance only (no built-in id leaks). Confirm RED today (module/function does not exist → ImportError/AttributeError is acceptable red — but prefer asserting behaviour so the green delta is meaningful).
- **Files**: `tests/specify_cli/invocation/test_org_profiles.py`.
- **Notes**: Reuse existing org-pack fixture helpers if `tests/specify_cli/invocation/fixtures/` or `tests/charter/fixtures/` already provide a real-format pack scaffold; otherwise add a small local builder. Do not invent `foo`/`bar` ids (C-007).

### Subtask T005 — Implement `resolve_activated_org_profiles`

- **Purpose**: Provide the one canonical org overlay seam for WP03/WP04.
- **Steps**: Create `src/specify_cli/invocation/org_profiles.py` exposing `resolve_activated_org_profiles(repo_root: Path) -> list[AgentProfile]` (with `__all__`). Implementation:
  1. Build the activation-aware service: `service = build_activation_aware_doctrine_service(repo_root)` (import from `specify_cli.doctrine_service_factory`).
  2. Read the **activation-filtered** merged profiles (`service.agent_profiles` — already gated by `PackContext`).
  3. Reduce to the **org-provenance** subset using the inner repository's provenance (`layer == "org"`); discard built-in/project members.
  4. Return a deterministically ordered `list[AgentProfile]` (sort by `profile_id`).
  - Keep it pure (no global state, no mutation of inputs) and small (≤ 15 complexity). Type-annotate the public signature.
- **Files**: `src/specify_cli/invocation/org_profiles.py`.
- **Notes**: Resolve open-question #1 from research.md (module placement) in favour of `specify_cli/invocation/org_profiles.py` (this owned file) — adjacent to `registry.py` (WP03's consumer) and cycle-safe. If recovering provenance through the wrapper proves awkward, prefer threading provenance from the inner `service._inner.agent_profiles` repository over re-deriving org roots — but never bypass the activation filter to do so.

### Subtask T006 — Fail-closed regression test (NFR-004)

- **Purpose**: A malformed allowlist/DRG must not flip a de-activated profile to admitted.
- **Steps**: Add a test that, with an explicit `activated_agent_profiles` list **excluding** `orgzilla-org-analyst` AND a malformed/garbage activation or DRG input (e.g. an unparesable extra entry, or a corrupt pack-config field that the gate tolerates), asserts the de-activated profile is STILL absent — the helper fails closed, never open. If the gate raises on malformed input, assert the helper surfaces a structured error rather than silently returning the full set.
- **Files**: `tests/specify_cli/invocation/test_org_profiles.py`.
- **Notes**: Exercise the negative direction specifically — a single "activated-only" positive assertion is fakeable (NFR-002 philosophy applied at unit scope).

## Test Strategy

- Run: `PWHEADLESS=1 pytest tests/specify_cli/invocation/test_org_profiles.py -q`.
- Prove T004 RED against pre-implementation code, then GREEN after T005. T006 stays GREEN through the activation filter (never relaxes to admit a de-activated id).
- `ruff check src/specify_cli/invocation/org_profiles.py tests/specify_cli/invocation/test_org_profiles.py && mypy src/specify_cli/invocation/org_profiles.py`.

## Risks & Mitigations

- **Re-implementing the gate** → forbidden; reuse `build_activation_aware_doctrine_service` only (C-006/C-008). Covered structurally by the WP05 arch gate later.
- **Import cycle** (`charter` ↔ `specify_cli`) → place the helper in `specify_cli/invocation/`, import the factory (already in `specify_cli`), never import `specify_cli` from `charter`/`doctrine`.
- **Provenance leak** → assert org-only membership in T004; do not return built-in/project profiles (C-002).
- **`None`-default regression** → the absent-key regime in T004 pins "all org admitted".

## Review Guidance

- Verify the helper composes `build_activation_aware_doctrine_service` and does NOT construct a raw `AgentProfileRepository(org_dirs=...)`.
- Verify all three regimes are asserted (absent / includes / excludes) and the exclude regime is genuinely RED-capable (would fail on a bypassing impl).
- Verify org-provenance filtering (no built-in/project leak) and deterministic ordering.
- Verify fail-closed behaviour (T006) and ruff/mypy cleanliness.

## Post-Tasks Squad Remediations (BINDING)

- **Return contract MUST carry provenance — `list[AgentProfile]` is INSUFFICIENT.** `AgentProfile` has no `source_layer`/`source_path`; provenance lives on the repository (`get_provenance`/`get_source_path`). A bare list makes WP04's #2166 `source_layer="org"` assertion UNSATISFIABLE (repo fallback → "builtin").
- **T005 returns `list[ResolvedOrgProfile]`** — a small record `{profile: AgentProfile, source_layer: str, source_path: Path | None}`. Recover provenance + source_path from the activation-aware service's INNER repository: `svc = build_activation_aware_doctrine_service(repo_root)`; for each activated id, `svc._inner.agent_profiles.get_provenance(id)` / `.get_source_path(id)`, keep only `source_layer == "org"`. This is the activated-ids ∩ org-provenance composition.
- WP03 (routing) needs only presence (the contract gap doesn't bite it); WP04 needs the full record.

---

## Activity Log

- 2026-06-27T00:00:00Z – system – Prompt created.
- 2026-06-27T09:51:04Z – claude:opus:python-pedro:implementer – shell_pid=918445 – Assigned agent via action command
- 2026-06-27T10:01:37Z – claude:opus:python-pedro:implementer – shell_pid=918445 – ResolvedOrgProfile resolver (activated ∩ org-provenance via build_activation_aware_doctrine_service); 3-regime + fail-closed green (6 passed); red proven (ImportError + naive-raw leak); ruff/mypy exit 0
- 2026-06-27T10:05:33Z – claude:opus:reviewer-renata:reviewer – shell_pid=964928 – Started review via action command
- 2026-06-27T10:08:39Z – user – shell_pid=964928 – reviewer-renata APPROVE: ResolvedOrgProfile via reused activation gate; no raw org_dirs; 3-regime+fail-closed green
