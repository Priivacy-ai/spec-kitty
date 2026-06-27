---
work_package_id: WP03
title: Dispatch routing + governance-context org visibility
dependencies:
- WP02
requirement_refs:
- FR-004
- FR-005
tracker_refs: []
planning_base_branch: mission/doctrine-governance-fidelity
merge_target_branch: mission/doctrine-governance-fidelity
branch_strategy: Planning artifacts for this mission were generated on mission/doctrine-governance-fidelity. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/doctrine-governance-fidelity unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
phase: Lane B — org-pack profile consolidation
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1017277"
history:
- at: '2026-06-27T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/invocation/
create_intent:
- tests/specify_cli/invocation/test_registry_org_visibility.py
- tests/charter/test_context_org_governance.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/invocation/registry.py
- src/charter/context.py
- tests/specify_cli/invocation/test_registry_org_visibility.py
- tests/charter/test_context_org_governance.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Dispatch routing + governance-context org visibility

## ⚡ Do This First: Load Agent Profile

Load `python-pedro` via the `/ad-hoc-profile-load` skill (read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml`) and adopt its directives before implementing.

- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent**: `claude`

---

## Objectives & Success Criteria

- `ProfileRegistry` (the dispatch routing catalog) includes the **charter-activation-admitted** org subset — merged onto its existing `.kittify/profiles` **project** layer — so `spec-kitty dispatch` routes to activated org agents (FR-004). It MUST NOT splice raw `org_dirs` (C-008).
- A `--profile`-hinted **activated** org agent loads **non-empty governance context** through `charter/context.py` (FR-005) — not a routed-but-context-empty half-fix.
- **Two-regime live proof (NFR-002)**: an admitted org profile is present in `ProfileRegistry.list_all()` AND carries non-empty governance context; a **de-activated** org profile (explicit `activated_agent_profiles` excluding it) is **absent** from both. A single activated-only assertion is forbidden.
- **No regression (NFR-001)**: a project with no org packs is byte-identical to today; the existing `.kittify/profiles` project layer stays honoured unchanged (FR-007, C-002).
- Advances #2156 (dispatch routing + governance-context legs).

**Done when**: the two-regime registry/context tests pass red-first; the no-org-packs regression test proves byte-identical behaviour; org overlay is the WP02 activation-filtered subset (no raw `org_dirs`); ruff + mypy clean, complexity ≤ 15.

## Context & Constraints

- **Depends on WP02.** Consume `resolve_activated_org_profiles(repo_root)` from `src/specify_cli/invocation/org_profiles.py` — never re-derive org roots or re-construct the gate (C-006/C-008).
- **Routing leg root cause (research.md census).** `src/specify_cli/invocation/registry.py:22-26` constructs `AgentProfileRepository(project_dir=.kittify/profiles)` with **no** `org_dirs` — so org-pack profiles are invisible to dispatch routing (live divergence: charter/specify catalog 19, dispatch catalog 18). Merge the WP02 org subset **onto** this existing project repo; do NOT reroute `ProfileRegistry` through `DoctrineService` (that would change which project profiles dispatch sees — C-002, the two-distinct-project-layers invariant).
- **Governance-context leg root cause.** `src/charter/context.py:1602` `_default_agent_profile_repository()` caches a built-in-only `AgentProfileRepository()` (no org/project layer) used by `_load_agent_profile` on the prompt-build path — so a dispatched org profile resolves empty context. **Precedent to reuse**: the same module already has `_build_activation_aware_doctrine_service` at `:1300-1333` gating `charter context --include agent-profile:<id>` (FR-016/#1636), with the exact `None`-default short-circuit (`if pack_context.activated_agent_profiles is None: return inner`). Mirror that activation-aware shape for the `--profile`-hinted governance-context path; do NOT splice raw `org_dirs`.
- **C-002 reconciliation.** C-002 governs the **project** overlay; the **org** overlay's sole notion of "active" is charter activation. Correct design = keep each consumer's project repo, **merge** the activation-admitted org-provenance subset onto it (C-008).
- **`None` default.** No activation list → all org profiles admitted (#2156 install→visible). Explicit list excluding an id → absent everywhere.
- **C-005 red-first** through the pre-existing public surfaces (`ProfileRegistry.list_all()` / `dispatch --profile` governance-context path), not WP02's internal API. **C-007** realistic org-pack fixtures (`orgzilla-org-analyst`, `<pack>/agent_profiles/<id>.agent.yaml`). **NFR-003** ruff/mypy clean.

## Subtasks & Detailed Guidance

### Subtask T007 — RED two-regime routing-catalog test

- **Purpose**: Witness dispatch's missing org profile (positive) AND prove de-activation is honoured (negative) before fixing.
- **Steps**: In `tests/specify_cli/invocation/test_registry_org_visibility.py`, build a real-format org-pack scratch repo (reuse the WP02 fixture shape: `.kittify/config.yaml` declaring the pack, profile at `<pack>/agent_profiles/orgzilla-org-analyst.agent.yaml`). Assert:
  - **admitted** (activation absent OR explicit list including) → `orgzilla-org-analyst` ∈ `ProfileRegistry(repo_root).list_all()` (RED today — currently absent).
  - **de-activated** (explicit list excluding it) → `orgzilla-org-analyst` ∉ `list_all()`.
  - the existing `.kittify/profiles` project profile (seed one) is STILL present in both regimes (project layer preserved — C-002/FR-007).
- **Files**: `tests/specify_cli/invocation/test_registry_org_visibility.py`.

### Subtask T008 — Wire `registry.py` to merge the WP02 org subset

- **Purpose**: Make the routing catalog org-aware via the activation seam.
- **Steps**: In `src/specify_cli/invocation/registry.py`, keep the `project_dir=.kittify/profiles` construction; additionally merge `resolve_activated_org_profiles(repo_root)` onto the catalog. Prefer overlaying the activated org subset onto the repo's loaded list (project profiles take precedence per the existing layer order — confirm against `AgentProfileRepository` provenance/override semantics) without rerouting the project layer through `DoctrineService`. Ensure `list_all()`, `get()`, `resolve()`, and `has_profiles()` all observe the merged set consistently. Keep complexity ≤ 15 — extract a small private merge helper if needed.
- **Files**: `src/specify_cli/invocation/registry.py`.
- **Notes**: Do NOT add an `org_dirs=` argument to the `AgentProfileRepository(...)` here — that is the forbidden raw splice (WP05 gate will fail it). Merge the WP02-returned `list[AgentProfile]` instead.

### Subtask T009 — Wire `charter/context.py` governance-context path

- **Purpose**: A dispatched activated org agent loads non-empty governance context.
- **Steps**: In `src/charter/context.py`, make the `--profile`-hinted governance-context resolution (the `_default_agent_profile_repository()` / `_load_agent_profile` path around `:1590-1618`) activation-aware for org profiles, mirroring the existing `_build_activation_aware_doctrine_service` precedent at `:1300-1333` (including its `None`-default short-circuit). The dispatched org profile must resolve through the charter activation filter and carry non-empty context. Respect the existing process-wide cache contract and the `_reset_agent_profile_cache()` test hook (`:1606`). Keep the built-in-only fast path unchanged when no org packs are declared.
- **Files**: `src/charter/context.py`.
- **Notes**: `charter` may NOT import `specify_cli` (layer rule). If the org overlay must enter here, thread it as **data** (resolved roots/profiles handed in by the caller), reusing the in-module `_build_activation_aware_doctrine_service` rather than importing the WP02 `specify_cli` helper. Confirm the actual call path during implementation and keep the wiring inside the allowed dependency direction. Add the governance-context assertion to `tests/charter/test_context_org_governance.py`.

### Subtask T010 — No-org-packs regression test (NFR-001)

- **Purpose**: Prove byte-identical behaviour when no org packs are declared.
- **Steps**: Add a regression test (split across the two test files as appropriate) asserting that with **no** `doctrine.org.packs` declared, `ProfileRegistry.list_all()` and the governance-context path produce output identical to pre-mission (built-in + `.kittify/profiles` project layer only, unchanged ordering/content).
- **Files**: `tests/specify_cli/invocation/test_registry_org_visibility.py`, `tests/charter/test_context_org_governance.py`.

## Test Strategy

- Run: `PWHEADLESS=1 pytest tests/specify_cli/invocation/test_registry_org_visibility.py tests/charter/test_context_org_governance.py -q`.
- Prove T007 RED (positive admitted-but-absent) against pre-fix code; GREEN after T008. The negative (de-activated absent) and T010 (no-packs identical) must hold both before and after the org-overlay wiring.
- `ruff check` + `mypy` on `src/specify_cli/invocation/registry.py` and `src/charter/context.py`.

## Risks & Mitigations

- **Routed-but-context-empty half-fix** → T009 covers the governance-context leg explicitly (FR-005); do not ship T008 alone.
- **Raw `org_dirs` splice** → forbidden (C-008); merge the WP02 `list[AgentProfile]`. WP05 gate enforces this structurally.
- **C-002 violation** (rerouting the project layer through `DoctrineService`) → keep `.kittify/profiles` as the project layer; only ADD the org overlay. T007's "project profile still present" assertion guards this.
- **Layer-rule import cycle** in `charter/context.py` → thread org data in, reuse the in-module activation-aware builder; never import `specify_cli` from `charter`.

## Review Guidance

- Verify BOTH legs (routing + governance context) are wired and BOTH regimes (admitted visible / de-activated hidden) are asserted live — NFR-002.
- Verify no `org_dirs=` argument was added to any `AgentProfileRepository(...)` construction here (raw-splice ban).
- Verify the `.kittify/profiles` project layer is preserved (project profile still present) and the no-org-packs path is byte-identical (T010).
- Verify the `charter/context.py` wiring stays within the `specify_cli → charter → doctrine` dependency direction.

## Post-Tasks Squad Remediations (BINDING)

- **T009 must assert an ORG-DOCTRINE SENTINEL, not `context != ""`.** A built-in/generic fallback context passes a non-emptiness check (fakeable routed-but-context-empty). Assert the governance context contains a distinctive string that exists ONLY in `orgzilla-org-analyst`'s pack doctrine.
- **Drive the dispatch `--profile` surface, NOT `charter context --include`.** The `--include` path (`context.py:~363`) is ALREADY gated; the dispatch prompt-build path is `_load_agent_profile` → `_default_agent_profile_repository()` (`context.py:1593`, a cached zero-arg BUILT-IN-ONLY repo). Fixing the already-gated path would false-green T009.
- Making `--profile` activation-aware means threading `repo_root` into `_default_agent_profile_repository` and reworking its process-wide cache key + `_reset_agent_profile_cache` — all within owned `context.py` (charter has no module-level `specify_cli` import, so the layer rule holds; the in-module `_build_activation_aware_doctrine_service` at `:1300` is the seam).

---

## Activity Log

- 2026-06-27T00:00:00Z – system – Prompt created.
- 2026-06-27T10:09:01Z – claude:opus:python-pedro:implementer – shell_pid=978673 – Assigned agent via action command
- 2026-06-27T10:21:27Z – claude:opus:python-pedro:implementer – shell_pid=978673 – registry+context org-gated; two-regime green (sentinel-based); ruff/mypy exit 0
- 2026-06-27T10:22:02Z – claude:opus:reviewer-renata:reviewer – shell_pid=1017277 – Started review via action command
- 2026-06-27T10:25:38Z – user – shell_pid=1017277 – reviewer-renata APPROVE: registry merge (project-wins) + dispatch context activation-aware (FR-016 precedent, layer rule intact); sentinel two-regime green
