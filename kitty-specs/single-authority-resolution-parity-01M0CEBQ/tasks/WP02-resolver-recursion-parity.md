---
work_package_id: WP02
title: Resolver recursion parity (kind_vocabulary)
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-003
planning_base_branch: spec/charter-resolution-parity
merge_target_branch: spec/charter-resolution-parity
branch_strategy: Planning artifacts for this mission were generated on spec/charter-resolution-parity. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into spec/charter-resolution-parity unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
- T011
- T012
- T013
history:
- Created by /spec-kitty.tasks (M1 charter-resolution program)
agent_profile: python-pedro
authoritative_surface: src/charter/kind_vocabulary.py
create_intent:
- tests/charter/test_kind_vocabulary_recursion_parity.py
execution_mode: code_change
owned_files:
- src/charter/kind_vocabulary.py
- tests/charter/test_kind_vocabulary_scan_roots.py
- tests/charter/test_kind_vocabulary_recursion_parity.py
role: implementer
tags: []
tracker_refs:
- '3426'
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

Make the **charter-activation resolver** derive recursion from the **same** authority WP01 introduced, so a nested org styleguide (or any kind) that loads at runtime also **resolves for activation** — closing the #3426 list-vs-activate asymmetry.

- **SC (FR-003)**: a nested org `*.styleguide.yaml` resolves via `charter activate` (was silently dropped).
- **SC (FR-002)**: for the exercised kinds, the resolver's discovery set **equals** the loader's discovery set.
- **No reordering regression**: the flat-before-legacy grouping and multi-root precedence (flat wins) are preserved — only the recursive flag changes.

## Context & Constraints

Read `contracts/recursion-authority.md` and `contracts/parity-gate.md`. Key seams in `src/charter/kind_vocabulary.py`:
- `_org_scan_dirs` emits the flat org dir as `(flat, False)` (line ~282) and the legacy `built-in` subdir as `(legacy, True)`. The docstring documents the **#3426 residual** you are fixing.
- `_layer_scan_dirs` emits `(candidate, False)` (line ~304).
- `_built_in_scan_dir` already emits `(dir, True)`.
- `_iter_artifact_paths` applies `scan_dir.rglob(pattern) if recursive else scan_dir.glob(pattern)` (line ~325).

Cross-check (do not change): `charter/pack_manager.py::list_available_detailed` already uses `rglob` — the availability catalog is recursive; this WP brings the **activation** resolver up to it.

**Constraints**: import the authority from `doctrine.discovery_recursion` (charter → doctrine is legal; C-006). Unconditional recursion (C-001). Zero suppressions (C-005).

## Branch Strategy
Planning base **`spec/charter-resolution-parity`**; merge target **`spec/charter-resolution-parity`**. Worktrees per computed lane from `lanes.json`. Depends on WP01 (the authority module).

## Subtasks & Detailed Guidance

### Subtask T008 – Red: nested org styleguide not activatable (#3426)
Write `tests/charter/test_kind_vocabulary_recursion_parity.py`. Build a temp org root with a nested styleguide `<org>/styleguides/writing/caveman.styleguide.yaml`. Call `resolve_artifact_urn(ArtifactKind.STYLEGUIDE, "caveman", doctrine_root=..., org_roots=[org])` (or `layer_roots={"org": org}` per the resolver's contract). **Assert it resolves** to the URN. This **fails** on `main` (flat org dir emitted `recursive=False` → nested file missed).

### Subtask T009 – Red: nested org tactic not resolved by the resolver [P]
Same module: nested `<org>/tactics/testing/x.tactic.yaml`; assert `resolve_artifact_urn(ArtifactKind.TACTIC, "x", ...)` resolves. **Fails** pre-fix. Add a `layer_roots={"project": proj}` nested case too.

### Subtask T010 – `_org_scan_dirs`: flat org dir recursive from authority
Change the flat entry from `(flat, False)` to derive its recursion from `overlay_scan_is_recursive(kind)` (→ `True`). Preserve the flat-before-legacy grouping and the legacy `built-in` entry unchanged. Example:
```python
from doctrine.discovery_recursion import overlay_scan_is_recursive
...
recursive = overlay_scan_is_recursive(kind)
if flat.is_dir():
    flat_dirs.append((flat, recursive))
```

### Subtask T011 – `_layer_scan_dirs`: recursive from authority
Change `dirs.append((candidate, False))` to `(candidate, overlay_scan_is_recursive(kind))`.

### Subtask T012 – Retire the #3426 residual docstring
Update the `_org_scan_dirs` / `_scan_roots` docstrings: remove the "Known residual (tracked #3426)" paragraph and the now-false claim that only styleguide/asset repos scan org recursively. State that overlay recursion is now unconditional and sourced from `doctrine.discovery_recursion`, and note `pack_manager.list_available_detailed` is already-recursive (so list and activate now agree). Keep the flat-before-legacy precedence rationale.

### Subtask T013 – Green + update existing scan-roots regression + parity
- Make T008/T009 pass.
- Update `tests/charter/test_kind_vocabulary_scan_roots.py`: any assertion pinning the flat org dir as `(dir, False)` must now expect `True`. **Keep** `test_multi_root_precedence_flat_wins_regardless_of_root_order` semantics — flat still wins; only the recursive flag flips. Do not reorder returned entries.
- Add an explicit parity assertion: for the exercised kinds, the set of paths the resolver iterates for a nested fixture equals what `DoctrineService` discovers.
- Record: `spec-kitty agent tasks mark-status T008 T009 T010 T011 T012 T013 --status done --mission single-authority-resolution-parity-01M0CEBQ`.

## Test Strategy
Red-first (T008/T009). Markers `charter`/`unit` per the file's existing convention. `tmp_path` fixtures only. Run: `PATH=.venv/bin:$PATH SPEC_KITTY_SYNC_DISABLE=1 pytest tests/charter/test_kind_vocabulary_recursion_parity.py tests/charter/test_kind_vocabulary_scan_roots.py -q`.

## Risks & Mitigations
- **Breaking the multi-root precedence regression** → only flip the boolean; keep grouping/order. Re-run the existing precedence test in both root orderings.
- **`layer_roots` vs `org_roots` API confusion** → mirror how existing scan-roots tests construct roots; assert via `resolve_artifact_urn`/`_iter_artifact_paths`.
- **Docstring drift** → T012 removes the now-false residual claim so the code and its doc agree (fail-loud honesty).

## Review Guidance
Verify: recursion sourced from `doctrine.discovery_recursion` (not a hardcoded `True`); flat-before-legacy precedence intact; #3426 residual docstring removed and replaced with the honest statement; existing scan-roots regression updated (not deleted); nested org styleguide + tactic both resolve; zero suppressions; `mypy --strict` clean.

## Activity Log
- (implementer appends entries here)
