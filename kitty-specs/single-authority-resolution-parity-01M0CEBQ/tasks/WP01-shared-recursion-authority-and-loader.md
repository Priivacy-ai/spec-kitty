---
work_package_id: WP01
title: Shared recursion authority + loader unification
dependencies: []
requirement_refs:
- C-001
- C-002
- C-006
- FR-001
- NFR-001
- NFR-002
planning_base_branch: spec/charter-resolution-parity
merge_target_branch: spec/charter-resolution-parity
branch_strategy: Planning artifacts for this mission were generated on spec/charter-resolution-parity. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into spec/charter-resolution-parity unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-single-authority-resolution-parity-01M0CEBQ
base_commit: 2fa8069ef2157fe3939537b6befef661e02affcf
created_at: '2026-08-19T14:32:19.182224+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
history:
- Created by /spec-kitty.tasks (M1 charter-resolution program)
agent_profile: python-pedro
authoritative_surface: src/doctrine/
create_intent:
- src/doctrine/discovery_recursion.py
- tests/doctrine/test_discovery_recursion.py
- tests/doctrine/test_overlay_recursion_loader.py
execution_mode: code_change
owned_files:
- src/doctrine/discovery_recursion.py
- src/doctrine/base.py
- src/doctrine/agent_profiles/repository.py
- src/doctrine/styleguides/repository.py
- src/doctrine/assets/repository.py
- tests/doctrine/test_discovery_recursion.py
- tests/doctrine/test_overlay_recursion_loader.py
role: implementer
tags: []
tracker_refs:
- '3490'
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile so your boundaries, directives, and
tactics are active:

```
/ad-hoc-profile-load python-pedro
```

Then run `spec-kitty charter context --action implement --json` and apply the resolved
initialization. State which directives/tactics you applied before writing code.

## Objectives & Success Criteria

Make **loader-side** org/project doctrine discovery **unconditionally recursive** (matching built-in), driven by **one new doctrine-layer authority**, and delete the two redundant subclass overrides plus the third `agent_profiles` divergence site.

- **SC**: a `*.tactic.yaml` and a `*.agent.yaml` authored one directory deep in an org root (and a project overlay) are discovered by `DoctrineService` — parity with built-in (NFR-001; the 71% tactic undercount → 0%).
- **SC**: flat-layout discovery output is **byte-identical** before/after (NFR-002).
- **SC**: `.provenance/*.yaml` sidecars and `.md` files are **never** captured (C-002).
- **SC**: `charter` is not imported here; the authority lives in `doctrine` (C-006).

## Context & Constraints

Read `kitty-specs/single-authority-resolution-parity-01M0CEBQ/{spec.md,plan.md,research.md,data-model.md}` and `contracts/recursion-authority.md`.

Current state (verified against `main`):
- `doctrine/base.py::BaseDoctrineRepository._project_scan` uses a **non-recursive** `project_dir.glob(self._glob)` (line ~159). It backs **both** org and project overlays via `_apply_overlay_layer`.
- `_load_built_in_items` already uses `rglob` (line ~182) — the reference behavior.
- `StyleguideRepository._project_scan` and `AssetRepository._project_scan` override to `rglob` — redundant once the base is recursive.
- `agent_profiles/repository.py::_load` scans built-in `recursive=True` (line ~343) but org (`~353`) and project (`~362`) `recursive=False` — the third, separate divergence.

**Constraints**: unconditional recursion, **not** a per-kind flag (C-001). Kind-specific globs only (C-002). Zero `ruff`/`mypy --strict` suppressions (C-005). `charter` must not be imported (C-006).

## Branch Strategy

Planning base **`spec/charter-resolution-parity`**; final merge target **`spec/charter-resolution-parity`** (single_branch topology). Execution worktrees are allocated per computed lane from `lanes.json`; do not hand-create branches. One PR to `main` lands the whole mission later.

## Subtasks & Detailed Guidance

### Subtask T001 – Red: nested org tactic dropped by the loader
Write `tests/doctrine/test_overlay_recursion_loader.py`. Build a temp org root with a **nested** tactic: `<org>/tactics/testing/acceptance.tactic.yaml` (valid minimal tactic YAML with `id`, `type: tactic`). Load via `DoctrineService`/`TacticRepository` with that org root. **Assert the nested tactic is discovered.** This must **fail** on current `main` (non-recursive `glob` misses the subdir). Keep a sibling flat tactic to prove flat still loads.

### Subtask T002 – Red: nested org agent profile dropped by the loader [P]
In the same test module, build `<org>/agent_profiles/team/reviewer.agent.yaml` (valid profile, `profile-id`) and assert `AgentProfileRepository` discovers it. **Fails** pre-fix (org scan `recursive=False`). Include a nested project-overlay case too (`.kittify/doctrine/...`).

### Subtask T003 – Create the shared recursion authority (doctrine layer)
Create `src/doctrine/discovery_recursion.py`:
```python
"""Single authority for org/project doctrine overlay recursion (C-001, C-006).

Both the loader (doctrine.base, doctrine.agent_profiles.repository) and the
charter-activation resolver (charter.kind_vocabulary) read this so recursion
cannot silently diverge per kind. Recursion is UNCONDITIONAL (C-001) — this is a
parity/derivation surface, not a per-kind toggle. Lives in the doctrine layer;
charter imports DOWN into it (C-006). Kind-specific globs (C-002) are the
caller's concern; this module governs only whether to recurse.
"""
from __future__ import annotations
from doctrine.artifact_kinds import ArtifactKind

def overlay_scan_is_recursive(kind: ArtifactKind) -> bool:  # noqa: ARG001 — uniform policy by design
    """Org/project overlay discovery is recursive for every kind (C-001)."""
    return True

RECURSIVE_OVERLAY_KINDS: frozenset[ArtifactKind] = frozenset(ArtifactKind)
```
Do **not** add a per-kind toggle. Write `tests/doctrine/test_discovery_recursion.py` asserting `overlay_scan_is_recursive(k) is True` for every `ArtifactKind` and `RECURSIVE_OVERLAY_KINDS == frozenset(ArtifactKind)`. (If `# noqa: ARG001` trips the zero-suppression rule, prefer `del kind` or a `_kind` parameter name over the noqa — keep zero suppressions.)

### Subtask T004 – base `_project_scan` → recursive via the authority
In `doctrine/base.py`, change `_project_scan` to scan recursively. Derive the recursion from the authority so the *policy* is shared, e.g.:
```python
from doctrine.discovery_recursion import overlay_scan_is_recursive
...
def _project_scan(self, project_dir: Path) -> list[Path]:
    recursive = overlay_scan_is_recursive(self._artifact_kind)  # or the kind this repo owns
    scan = project_dir.rglob(self._glob) if recursive else project_dir.glob(self._glob)
    return sorted(scan)
```
If `BaseDoctrineRepository` has no direct `ArtifactKind` handle, resolve it from the existing kind machinery (see `_kind`/`_glob`); if a clean kind handle is genuinely unavailable, call `overlay_scan_is_recursive` with the repo's kind via the smallest correct accessor — do **not** hardcode `True`, so the authority remains the single source. Update the docstring to state recursion is authority-driven and unconditional.

### Subtask T005 – Delete redundant styleguide + asset overrides
Remove the `_project_scan` override methods in `styleguides/repository.py` and `assets/repository.py` (they now duplicate the recursive base). Update the surrounding class docstrings/comments that claimed the override was needed. Verify no other code references those methods.

### Subtask T006 – agent_profiles `_load` org/project → recursive via authority
In `agent_profiles/repository.py::_load`, flip the org and project `_scan_directory(..., recursive=False)` calls to derive from `overlay_scan_is_recursive(ArtifactKind.AGENT_PROFILE)` (→ `True`). Leave built-in as-is (already `True`). Keep the `_scan_directory` signature; only the passed flag changes (sourced from the authority).

### Subtask T007 – Green + NFR-002 flat-identical + C-002 negative (loader side)
- Make T001/T002 pass.
- Add an assertion that a **flat** org/project layout yields the identical discovered id-set before/after (rglob over a subdir-free dir == glob). Compare against a golden set built from the flat fixture.
- Add a C-002 negative: drop `<org>/tactics/.provenance/foo.yaml` and `<org>/tactics/notes.md`; assert **neither** is captured by the loader (kind-specific glob `*.tactic.yaml`).
- Record subtasks: `spec-kitty agent tasks mark-status T001 T002 T003 T004 T005 T006 T007 --status done --mission single-authority-resolution-parity-01M0CEBQ`.

## Test Strategy
Red-first (T001/T002 fail on base, pass after). All tests in `tests/doctrine/` with markers `doctrine`, `fast`. Use `tmp_path` org/project fixtures; do **not** touch the real corpus. Run targeted: `PATH=.venv/bin:$PATH SPEC_KITTY_SYNC_DISABLE=1 pytest tests/doctrine/test_overlay_recursion_loader.py tests/doctrine/test_discovery_recursion.py -q`.

## Risks & Mitigations
- **`rglob` capturing unintended files** → kind-specific globs (C-002) + explicit negative test (T007).
- **NFR-002 regression** → flat-identical golden assertion (T007).
- **Base lacks a clean kind handle** → use the existing `_glob`/`_kind` machinery; never hardcode `True` (keep the authority the single source).
- **`ARG001`/unused-arg lint on the uniform policy fn** → use `del kind`/`_kind` naming, not a `# noqa` (C-005 zero suppressions).

## Review Guidance
Verify: authority module has no `charter`/`specify_cli` import; both loader seams derive recursion from the authority (no hardcoded `True`); two overrides deleted with no dangling references; flat output byte-identical; C-002 negative present; zero new suppressions; `mypy --strict` clean on `discovery_recursion.py` + `base.py`.

## Activity Log
- (implementer appends entries here per the template's Activity Log convention)
