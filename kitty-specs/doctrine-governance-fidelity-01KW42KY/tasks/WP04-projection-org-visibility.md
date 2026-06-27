---
work_package_id: WP04
title: Agent-profile projection org visibility (#2166)
dependencies:
- WP02
requirement_refs:
- FR-006
tracker_refs: []
planning_base_branch: mission/doctrine-governance-fidelity
merge_target_branch: mission/doctrine-governance-fidelity
branch_strategy: Planning artifacts for this mission were generated on mission/doctrine-governance-fidelity. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/doctrine-governance-fidelity unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
phase: Lane B — org-pack profile consolidation
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1007657"
history:
- at: '2026-06-27T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/tool_surface/profiles/
create_intent:
- tests/specify_cli/tool_surface/test_projection_org_visibility.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/tool_surface/profiles/projection.py
- tests/specify_cli/tool_surface/test_projection_org_visibility.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Agent-profile projection org visibility (#2166)

## ⚡ Do This First: Load Agent Profile

Load `python-pedro` via the `/ad-hoc-profile-load` skill (read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml`) and adopt its directives before implementing.

- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent**: `claude`

---

## Objectives & Success Criteria

- Agent-profile projection emits the **charter-activation-admitted** org agents to the host surface (`.claude/agents/`) and records them in the projection manifest with a **non-builtin `source_layer`** (FR-006) — merged onto the existing `.kittify/agent_profiles` project layer, NOT via a raw `org_dirs` splice (C-008).
- **Two-regime live proof (NFR-002)**: an admitted org profile appears in the projection manifest (`source_layer != builtin`) and on the host surface; a **de-activated** org profile is **absent** from both.
- **No regression (NFR-001)**: a built-in-only project (no org packs) projects byte-identically to today; the existing project layer is preserved unchanged (FR-007, C-002).
- Closes **#2166** (the projection leg of the #2156 `org_dirs` omission).

**Done when**: the two-regime projection test passes red-first and asserts the manifest `source_layer`; the no-org-packs regression test proves byte-identical projection; org overlay is the WP02 activation-filtered subset (no raw `org_dirs`); ruff + mypy clean, complexity ≤ 15.

## Context & Constraints

- **Depends on WP02.** Consume `resolve_activated_org_profiles(repo_root)` from `src/specify_cli/invocation/org_profiles.py`; never re-derive org roots or re-construct the gate (C-006/C-008).
- **Root cause (research.md census).** `src/specify_cli/tool_surface/profiles/projection.py:69-78` `default_profile_repository()` constructs `AgentProfileRepository(project_dir=.kittify/agent_profiles)` with **no** `org_dirs` — so org-pack agents are never projected (#2166, same root cause as the dispatch leg). Note the project subdir here is `.kittify/agent_profiles` (`_PROJECT_PROFILE_SUBDIR`, `projection.py:40`) — **distinct** from dispatch's `.kittify/profiles`; preserve this project layer (C-002, two-distinct-project-layers invariant).
- **Provenance / `source_layer`.** The org layer is provenance-tagged `"org"` by the repository (`src/doctrine/agent_profiles/repository.py:353-357`, exposed via `get_provenance`, `:566`). The projection manifest must record the admitted org agents with a non-builtin `source_layer` so the host surface and operator can see they came from the org pack. Use the WP02 helper's provenance-preserving output to set this.
- **C-008 / charter is the entry point.** Project only the **activation-admitted** subset; a de-activated org profile must NOT project (would create the opposite split-brain — gated dispatch hides what ungated projection would write).
- **`None` default.** No activation list → all org profiles admitted (#2156 install→visible). Explicit list excluding an id → absent.
- **C-005 red-first** through the pre-existing projection surface (`default_profile_repository` / `ProfileProjector.project`), not WP02's internal API. **C-007** realistic org-pack fixtures (`orgzilla-org-analyst`, `<pack>/agent_profiles/<id>.agent.yaml`). **NFR-003** ruff/mypy clean.

## Subtasks & Detailed Guidance

### Subtask T011 — RED two-regime projection test (manifest `source_layer`)

- **Purpose**: Witness the missing org agent in projection (positive) AND prove de-activation is honoured (negative) before fixing.
- **Steps**: In `tests/specify_cli/tool_surface/test_projection_org_visibility.py`, build a real-format org-pack scratch repo (WP02 fixture shape). Drive the projection surface (`default_profile_repository(project_root)` → `ProfileProjector.project(tool_key, project_root)`, or the public projection entry it backs). Assert:
  - **admitted** (activation absent OR explicit list including) → `orgzilla-org-analyst` is projected AND appears in the manifest with `source_layer != "builtin"` (RED today — currently absent).
  - **de-activated** (explicit list excluding it) → `orgzilla-org-analyst` is NOT projected and NOT in the manifest.
  - a seeded `.kittify/agent_profiles` project profile is STILL projected in both regimes (project layer preserved).
- **Files**: `tests/specify_cli/tool_surface/test_projection_org_visibility.py`.
- **Notes**: Assert the actual manifest `source_layer` value, not just presence — manifest provenance correctness is the #2166 acceptance hinge.

### Subtask T012 — Wire `default_profile_repository` to merge the org subset

- **Purpose**: Make projection org-aware via the activation seam.
- **Steps**: In `src/specify_cli/tool_surface/profiles/projection.py`, keep the `project_dir=.kittify/agent_profiles` construction; additionally merge `resolve_activated_org_profiles(repo_root)` onto the projected set, carrying provenance so the manifest records a non-builtin `source_layer`. Thread `repo_root` through to `default_profile_repository` if it is not already available (the signature currently takes `project_root` — confirm callers and pass the repo root or derive it). Ensure `ProfileProjector.project` and manifest emission observe the merged set. Keep complexity ≤ 15 — extract a small merge/provenance helper if needed.
- **Files**: `src/specify_cli/tool_surface/profiles/projection.py`.
- **Notes**: Do NOT add an `org_dirs=` argument to the `AgentProfileRepository(...)` here — that is the forbidden raw splice (WP05 gate will fail it). Merge the WP02-returned provenance-tagged profiles instead.

### Subtask T013 — No-org-packs regression test (NFR-001)

- **Purpose**: Prove byte-identical projection when no org packs are declared.
- **Steps**: Add a regression test asserting that with **no** `doctrine.org.packs` declared, projection output (host files + manifest entries/ordering/`source_layer`) is identical to pre-mission (built-in + `.kittify/agent_profiles` project layer only).
- **Files**: `tests/specify_cli/tool_surface/test_projection_org_visibility.py`.

## Test Strategy

- Run: `PWHEADLESS=1 pytest tests/specify_cli/tool_surface/test_projection_org_visibility.py -q`.
- Prove T011 RED (positive admitted-but-absent) against pre-fix code; GREEN after T012. The negative (de-activated absent) and T013 (no-packs identical) must hold both before and after.
- `ruff check` + `mypy` on `src/specify_cli/tool_surface/profiles/projection.py`.

## Risks & Mitigations

- **Manifest provenance wrong** → T011 asserts `source_layer != builtin` directly.
- **Raw `org_dirs` splice** → forbidden (C-008); merge the WP02 provenance-tagged list. WP05 gate enforces this.
- **C-002 violation** (wrong project layer, or collapsing onto the dispatch `.kittify/profiles` layer) → preserve `.kittify/agent_profiles`; T011's "project profile still projected" assertion guards this.
- **De-activated profile leaks to host surface** → the negative regime in T011 fails such a regression.

## Review Guidance

- Verify BOTH regimes are asserted live (admitted projected with non-builtin `source_layer` / de-activated absent) — NFR-002.
- Verify no `org_dirs=` argument was added to `AgentProfileRepository(...)` (raw-splice ban).
- Verify the `.kittify/agent_profiles` project layer is preserved and the no-org-packs projection is byte-identical (T013).
- Verify `#2166` acceptance: org agent present in BOTH the host surface and the manifest with correct provenance.

## Post-Tasks Squad Remediations (BINDING)

- **Consume WP02's `ResolvedOrgProfile` record; assert `source_layer == "org"` AND `source_path is not None`** in the manifest entry. A bare `list[AgentProfile]` cannot satisfy #2166 (projector reads provenance from the repo via `get_provenance`/`get_source_path`, falling back to `builtin`).
- If the WP02 record is unavailable, the only alternative is to project from the activation-aware INNER repository (which tags org provenance) — and WP05's allowlist must explicitly bless that seam. Prefer the WP02 record.
- De-activated org profile must be ABSENT from the manifest (NFR-002 negative regime).

---

## Activity Log

- 2026-06-27T00:00:00Z – system – Prompt created.
- 2026-06-27T10:09:05Z – claude:opus:python-pedro:implementer – shell_pid=978673 – Assigned agent via action command
- 2026-06-27T10:17:02Z – claude:opus:python-pedro:implementer – shell_pid=978673 – org agents projected source_layer=org; de-activated absent; ruff/mypy exit 0
- 2026-06-27T10:18:22Z – claude:opus:reviewer-renata:reviewer – shell_pid=1007657 – Started review via action command
- 2026-06-27T10:23:40Z – user – shell_pid=1007657 – reviewer-renata APPROVE: org source_layer/source_path correct; private-map merge sound; two-regime green (follow-up: public register_profile API)
