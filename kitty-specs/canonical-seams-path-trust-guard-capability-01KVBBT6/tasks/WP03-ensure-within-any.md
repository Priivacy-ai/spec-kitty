---
work_package_id: WP03
title: ensure_within_any kernel containment utility
dependencies: []
requirement_refs:
- FR-005
- NFR-001
tracker_refs:
- '#2022'
planning_base_branch: feat/canonical-seams-path-trust-guard-capability
merge_target_branch: feat/canonical-seams-path-trust-guard-capability
branch_strategy: Planning artifacts for this mission were generated on feat/canonical-seams-path-trust-guard-capability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/canonical-seams-path-trust-guard-capability unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3670643"
history:
- 2026-06-17 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/utils.py
create_intent:
- tests/specify_cli/core/test_ensure_within_any.py
execution_mode: code_change
owned_files:
- src/specify_cli/core/utils.py
- tests/specify_cli/core/test_ensure_within_any.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Then read:
1. `kitty-specs/canonical-seams-path-trust-guard-capability-01KVBBT6/spec.md` — **FR-005**, **NFR-001**.
2. `kitty-specs/canonical-seams-path-trust-guard-capability-01KVBBT6/contracts/seam-signatures.md` — the
   `ensure_within_any` contract (roots + optional exact-file allowlist arm).
3. `kitty-specs/canonical-seams-path-trust-guard-capability-01KVBBT6/research.md` — **§(d)/D-3** (the merge helpers
   that will delegate to this in WP04; the XOR helper stays a conditional caller).

## Objective

Add a single parameterized containment utility `ensure_within_any` beside `ensure_within_directory` in
`src/specify_cli/core/utils.py`. It is the kernel seam WP04's two collapsible merge helpers delegate to. This WP
**only adds the util + its tests** — it does not touch merge.py (that's WP04). Independent; can start immediately.

## Subtasks

### T011 — TDD: ensure_within_any tests (RED first)
Create `tests/specify_cli/core/test_ensure_within_any.py`:
- **roots accept:** a path under one of several roots returns `path.resolve(strict=False)`.
- **roots reject:** a path under none of the roots raises `ValueError`.
- **files arm accept:** a path equal to an allowed exact file in `files=` is accepted even if under no root.
- **files arm default empty:** with `files` omitted, only root membership is consulted.
- **files arm is EXACT-equality, not prefix:** a path *under an allowed file's parent* (but not equal to the file)
  and under no root is **REJECTED** — proves `files` is membership, not another root-prefix arm (squad flag).
- **strict=False semantics:** a deeply non-existent nested path (`root/a/b/c/does/not/exist`) under a root is
  **ACCEPTED** (no `FileNotFoundError`) — this fails a strict-resolve implementation, forcing `strict=False`.
- **symlink behavior (executable, not "document"):** create a real symlink — one pointing OUTSIDE all roots is
  rejected, one resolving INSIDE a root is accepted. Pin `ensure_within_any`'s OWN resolve-then-compare behavior;
  do NOT assert parity with `ensure_within_directory` (it uses `resolve()` strict=True — a deliberate divergence).
Run red — paste output into the handoff.

### T012 — Implement `ensure_within_any(path, *, roots, files=())`
In `core/utils.py`, beside `ensure_within_directory` (line ~29):
```python
def ensure_within_any(
    path: Path, *, roots: Sequence[Path], files: Sequence[Path] = ()
) -> Path:
    """Return path.resolve(strict=False) if it is under any of `roots` OR equals
    an allowed exact file in `files`; else raise ValueError. Multi-root sibling of
    ensure_within_directory."""
```
- Resolve `path` and each root with `resolve(strict=False)`; accept if `resolved.is_relative_to(any root)` OR
  `resolved == any resolved file`. Else raise `ValueError` with a message naming the rejected path.
- Add the import `from collections.abc import Sequence` (it is NOT currently imported in `core/utils.py`).
- **Do NOT modify `ensure_within_directory`** (NFR-001) — single-root callers keep it. Note it uses `resolve()`
  (strict=True); `ensure_within_any` intentionally uses `strict=False` (snapshot/rollback paths may not exist).
- Keep complexity ≤ 15; type the `Sequence[Path]` params; no suppressions.

### T013 — Quality gate
- `ruff`+`mypy` clean on `core/utils.py`.
- Confirm `ensure_within_directory` is byte-unchanged and its existing callers/tests stay green.
- New test file green.

## Branch Strategy

Planning/merge base `feat/canonical-seams-path-trust-guard-capability` (PR → main). Worktree per lane from
`lanes.json`. **No dependencies — starts immediately, parallel with WP01/WP05/WP06.**

## Definition of Done

- [ ] `ensure_within_any(path, *, roots, files=())` exists in `core/utils.py`, raises `ValueError`, ≤15, no suppressions.
- [ ] `ensure_within_directory` unchanged.
- [ ] T011 tests cover roots accept/reject, files arm, strict=False, symlink consistency.
- [ ] `ruff`+`mypy` clean; existing utils tests green.

## Risks / reviewer guidance

- **`resolve(strict=False)` is deliberate** (matches the merge helpers WP04 collapses). Reviewer: confirm it is
  NOT `resolve(strict=True)` (would raise on non-existent snapshot paths during rollback).
- This WP is intentionally small (≤3 subtasks) — it is the independent kernel seam; do not pad it with merge.py
  work (that is WP04's, to keep merge.py single-owned).

## Activity Log

- 2026-06-17T20:16:55Z – claude:sonnet:python-pedro:implementer – shell_pid=3633670 – Assigned agent via action command
- 2026-06-17T20:22:44Z – user – shell_pid=3633670 – Moved to claimed
- 2026-06-17T20:22:50Z – user – shell_pid=3633670 – Moved to in_progress
- 2026-06-17T20:23:11Z – user – shell_pid=3633670 – Moved to claimed
- 2026-06-17T20:23:13Z – user – shell_pid=3633670 – Moved to in_progress
- 2026-06-17T20:24:28Z – claude:sonnet:python-pedro:implementer – shell_pid=3633670 – Ready for review: ensure_within_any added to core/utils.py with full squad-hardened test coverage (15 tests). ruff EXIT 0, mypy EXIT 0. ensure_within_directory byte-unchanged. Zero production callers by design — WP04 wires merge.py helpers in separate lane.
- 2026-06-17T20:26:17Z – claude:opus:reviewer-renata:reviewer – shell_pid=3670643 – Started review via action command
- 2026-06-17T20:35:33Z – user – shell_pid=3670643 – Review passed (opus/reviewer-renata): code-clean; matrix verdicts filled
