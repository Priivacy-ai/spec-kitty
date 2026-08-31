---
work_package_id: WP05
title: Activation-bypass architectural gate
dependencies:
- WP03
- WP04
requirement_refs:
- FR-008
tracker_refs: []
planning_base_branch: mission/doctrine-governance-fidelity
merge_target_branch: mission/doctrine-governance-fidelity
branch_strategy: Planning artifacts for this mission were generated on mission/doctrine-governance-fidelity. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/doctrine-governance-fidelity unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
phase: Lane B — org-pack profile consolidation
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1058764"
history:
- at: '2026-06-27T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_org_activation_seam.py
create_intent:
- tests/architectural/test_org_activation_seam.py
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_org_activation_seam.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – Activation-bypass architectural gate

## ⚡ Do This First: Load Agent Profile

Load `python-pedro` via the `/ad-hoc-profile-load` skill (read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml`) and adopt its directives before implementing.

- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent**: `claude`

---

## Objectives & Success Criteria

- A new architectural gate, `tests/architectural/test_org_activation_seam.py`, fails if a routing/projection surface constructs a profile repository that **bypasses the charter activation filter** — i.e. splices raw `org_dirs`/`resolve_org_roots` directly into an `AgentProfileRepository` instead of routing through the WP02 activation-aware seam (FR-008, C-008).
- The gate asserts the **CONTRACT** (org-honouring sites route through the activation seam), NOT a fakeable `org_dirs`-presence proxy — a gate that merely asserts "site passes `org_dirs`" would CERTIFY the bypass (research.md: the originally-planned FR-008 gate was inverted; revised per C-008).
- A **self-mutation teeth test** proves the gate bites: inject a raw `AgentProfileRepository(org_dirs=resolve_org_roots(...))` into a routing surface → gate fails; revert → passes. A **concrete integer floor** prevents a vacuous (zero-site) pass.
- Confirmed **built-in-only sites are excluded** with recorded rationale (C-003) — `cli/commands/agent/tasks.py` (language resolution) and the `charter/context` module-cache language path are intentional, not swept.

**Done when**: the gate enumerates the org-honouring construction sites and asserts each routes through the activation seam; the self-mutation test passes (bites on injection, green on revert); the floor is non-vacuous; the allowlist of excluded built-in-only sites carries rationale; ruff + mypy clean.

## Context & Constraints

- **Depends on WP03 + WP04** — the gate codifies the invariant those WPs establish (registry + context + projection route through the WP02 seam). Author it after they land so the "correct" sites exist to assert against.
- **C-008 (the contract being gated).** Org-pack agent profiles reach dispatch routing, governance context, and projection ONLY through the charter activation filter (`PackContext.activated_agent_profiles`, three-state). No invocation/projection-layer consumer may splice raw `org_dirs`/`resolve_org_roots` that bypass the filter. The canonical seam is `resolve_activated_org_profiles` (WP02) / `build_activation_aware_doctrine_service` (`src/specify_cli/doctrine_service_factory.py:38`).
- **Why a presence proxy is wrong (research.md, architectural-alignment squad).** debbie's 4×4 matrix row 3 shows raw `repo+org_dirs` surfaces a profile the charter EXPLICITLY de-activated. Asserting "`org_dirs` is passed" would mark that bypass as compliant. The gate must instead assert that org-honouring sites obtain their org overlay from the activation-aware seam (e.g. via `resolve_activated_org_profiles` / the activation wrapper) and do NOT pass `org_dirs=` into a bare `AgentProfileRepository(...)` at routing/projection surfaces.
- **Scope (C-003).** The ratchet covers the **org-honouring** surfaces only: `src/specify_cli/invocation/registry.py`, `src/charter/context.py` (governance-context path), `src/specify_cli/tool_surface/profiles/projection.py`. **Exclude** confirmed built-in-only sites with rationale: `src/specify_cli/cli/commands/agent/tasks.py` (built-in-only language resolution — research.md census), and the `charter/context` language/module cache built-in-only path. The `DoctrineService.agent_profiles` canonical seam (`doctrine/service.py`) and the activation wrapper itself are the reference, not violations.
- **Gate-discipline (memory: gate-unmask + anti-vacuity).** Assert the contract, carry a concrete integer floor (number of org-honouring sites verified), and add a self-mutation teeth test so a future inversion is caught. Pin against a stable signal (AST/import inspection over the named modules), not a line number that benign edits will move (DIRECTIVE_041).
- **C-005 / NFR-003.** Red-first the teeth test; ruff/mypy clean; complexity ≤ 15.

## Subtasks & Detailed Guidance

### Subtask T014 — Implement the activation-seam gate

- **Purpose**: Forbid activation-bypassing profile-repo construction at org-honouring surfaces.
- **Steps**: Create `tests/architectural/test_org_activation_seam.py`. Enumerate the org-honouring construction sites (registry, charter governance-context, projection) — prefer AST inspection of the named source modules over brittle text scans. For each, assert:
  1. it obtains its org overlay through the activation seam (references `resolve_activated_org_profiles` / `build_activation_aware_doctrine_service` / the activation-aware `charter.resolver.DoctrineService`), AND
  2. it does NOT construct an `AgentProfileRepository(...)` with an `org_dirs=` keyword (the raw splice).
  Maintain a small explicit allowlist of confirmed built-in-only sites (`agent/tasks.py`, the `charter/context` language/module cache) with an inline rationale comment per entry (C-003). Add a concrete integer floor: assert the count of verified org-honouring sites is `>= N` (set N to the actual number, currently 3) so the gate cannot pass vacuously if sites disappear or are renamed.
- **Files**: `tests/architectural/test_org_activation_seam.py`.
- **Notes**: Hoist any repeated literals (module paths, the `org_dirs` token, the seam symbol names) to module constants (Sonar S1192). Keep the AST/inspection helpers small and testable.

### Subtask T015 — Self-mutation teeth test + floor verification

- **Purpose**: Prove the gate bites (it is not vacuous or inverted).
- **Steps**: Add a teeth test that programmatically simulates a violation — e.g. feed the gate's site-checker a synthetic/temp module source containing `AgentProfileRepository(org_dirs=resolve_org_roots(repo_root))` at a routing-like surface and assert the checker flags it; then assert a compliant snippet (routing through `resolve_activated_org_profiles`) passes. Also assert the integer floor is met by the real codebase (the three WP03/WP04 sites are present and compliant). The teeth test must be RED if the gate logic is inverted (asserting `org_dirs` presence) — verify by reasoning/local mutation.
- **Files**: `tests/architectural/test_org_activation_seam.py`.
- **Notes**: Drive the teeth test through the gate's own predicate/helper (not by editing real source on disk), so it is hermetic and CI-safe. This is the anti-`#2188`-style guard: the gate must witness an injected offender, not just pass on clean code.

## Test Strategy

- Run: `PWHEADLESS=1 pytest tests/architectural/test_org_activation_seam.py -q`.
- The teeth test (T015) is the red-first proof: the gate flags a synthetic raw-`org_dirs` splice and passes a compliant seam reference.
- `ruff check tests/architectural/test_org_activation_seam.py && mypy tests/architectural/test_org_activation_seam.py` (or the repo's architectural-test type scope).
- Run the full `tests/architectural/` suite to confirm no cross-gate interaction.

## Risks & Mitigations

- **Vacuous/inverted gate** (the originally-planned failure mode) → assert the activation seam (contract), self-mutation teeth test required (T015), concrete integer floor (T014).
- **Over-scope** → exclude `agent/tasks.py` + the `charter/context` language/module cache with inline rationale (C-003); the gate must not flag intentional built-in-only sites.
- **Brittle assertion** (line-number/text drift) → inspect via AST/imports over named modules, pin the contract not a location (DIRECTIVE_041).
- **Floor erosion** → the `>= N` floor fails if an org-honouring site is silently dropped, surfacing the regression.

## Review Guidance

- Verify the gate asserts the activation seam (NOT `org_dirs` presence) — confirm it would FAIL on debbie's row-3 raw-splice bypass.
- Verify the self-mutation teeth test bites on an injected violation and is green on revert.
- Verify the integer floor is concrete and non-vacuous, and the excluded built-in-only sites each carry a rationale.
- Verify the three WP03/WP04 sites are covered and pass; no over-scoping onto intentional built-in-only sites.

## Post-Tasks Squad Remediations (BINDING)

- **The BINDING assertion is the ABSENCE of raw `org_dirs=` / `resolve_org_roots(` at the named org-honouring surfaces** (registry / projection / context dispatch path). "References the activation seam" is ADVISORY only — satisfiable by an unused import or comment, so it has no teeth on its own.
- **The self-mutation fixture (T015) MUST be a site that IMPORTS the seam YET still splices `org_dirs`** — proving the reference-only half would pass while the real (absence) assertion fails. Concrete integer floor (N=3 in-scope surfaces); exclude `agent/tasks.py` + `charter/context` language cache with recorded rationale.

---

## Activity Log

- 2026-06-27T00:00:00Z – system – Prompt created.
- 2026-06-27T10:25:44Z – claude:opus:python-pedro:implementer – shell_pid=1025281 – Assigned agent via action command
- 2026-06-27T10:39:46Z – claude:opus:python-pedro:implementer – shell_pid=1025281 – activation-bypass gate: absence-of-raw-org_dirs assertion + self-mutation teeth + integer floor; passes on fixed tree
- 2026-06-27T10:40:25Z – claude:opus:reviewer-renata:reviewer – shell_pid=1058764 – Started review via action command
- 2026-06-27T10:59:30Z – user – shell_pid=1058764 – reviewer-renata APPROVE: non-vacuous activation-bypass gate; live-mutation RED/revert-GREEN; floor=3; allowlist+discovery-call correct; 12 passed
