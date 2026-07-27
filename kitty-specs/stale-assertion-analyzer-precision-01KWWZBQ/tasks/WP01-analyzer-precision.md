---
work_package_id: WP01
title: Relocation/re-export + generic-literal suppression
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-004
- FR-005
- FR-006
tracker_refs: []
planning_base_branch: fix/stale-assertion-analyzer-precision
merge_target_branch: fix/stale-assertion-analyzer-precision
branch_strategy: Planning artifacts for this mission were generated on fix/stale-assertion-analyzer-precision. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/stale-assertion-analyzer-precision unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
agent: "claude"
shell_pid: "1584876"
history:
- 'Created by planner for #2031/#2343 tasks phase'
agent_profile: python-pedro
authoritative_surface: src/specify_cli/post_merge/
create_intent:
- tests/post_merge/test_stale_assertions_precision.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/post_merge/stale_assertions.py
- tests/post_merge/test_stale_assertions_precision.py
role: implementer
tags: []
task_type: implement
---

# WP01 – Relocation/re-export + generic-literal suppression (closes #2031 + #2343)

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load` → `python-pedro` (implementer, Sonnet-5). Read `spec.md` (FR-001..006, NFR-001, C-001) + `plan.md`. Study `src/specify_cli/post_merge/stale_assertions.py`: `_extract_changed_symbols` (`:139`), `_extract_identifiers` (`:121` — BARE names, no qualname), `_extract_string_literals` (`:130`), the confidence grading (`:392`+/`:532`+), `findings_per_100_loc`/`FP_CEILING` (`:664`).

## Objective
Stop two false-positive engines by **suppressing** (not emitting) the findings:
1. **Relocation/re-export (#2031)** — a removed identifier still importable from its origin file in head.
2. **Generic-literal noise (#2343)** — short/generic removed string literals.
**Suppress (don't emit)**, NOT downgrade-to-`info` — `info` is mislabeled by `merge/executor.py`, dropped by the CLI render, yet still FP-ceiling-counted; not emitting avoids all three (do NOT modify those render files).

## Changes
- **T001 — head-importability suppression (FR-001/002)**: in `_extract_changed_symbols`, before recording a removed identifier from origin file A, check whether **A's HEAD still re-exports/imports that name** — parse A's head AST for `from <mod> import X` (incl. `import X as _X`), `X` in `__all__`, and module/`__init__` re-exports. If still importable-from-A → **suppress** (don't record it removed). ⚠️ **Do NOT** key on "the bare name appears in another changed file" — the analyzer has only bare names, so that collides on common names (`run`/`main`/`setup`) and would **blind genuine deletions** (SC-003). The WP05 extraction storm is caught because the extracted symbols are **re-exported back** from A. Reuse the already-parsed head tree; no full-repo scan (NFR-002).
- **T002 — generic-literal suppression (FR-004)**: add `_is_generic_literal(value: str) -> bool` gating on **GENUINENESS, NOT length**: `True` iff value ∈ a **pinned generic-token set** (common words / format fragments) OR all-punctuation/whitespace/empty. **Do NOT use a `length < N` disjunct** — a genuinely short literal (an error code `"E001"`) can be assert-critical, and since ALL literal findings are by construction literals-in-asserts, length cannot separate noise from signal. Pin the exact token set inline (a module constant, not "e.g."). Suppress matching *removed* literals.
- **T003 — regression fixtures (FR-005/006)** in `tests/post_merge/test_stale_assertions_precision.py`:
  (a) **extraction (PAIRED before/after)** — symbols moved A→B, re-exported back from A: suppression **disabled** → the finding storm; **enabled** → ~0;
  (b) **generic-literal (PAIRED)** — disabled → noisy; enabled → ~0;
  (c) **genuine deletion** (A's head does NOT re-export it) → still flagged high/medium;
  (d) **NAME-COLLISION (the key guard)** — genuine deletion of `X` in file C while an UNRELATED `X` is defined in changed file B, and C's head does NOT re-export `X` → **still flagged** (proves head-importability, not bare-name, is the key);
  (e) **relocate-and-rename** → still flagged;
  (f) a **genuinely SHORT assert-critical literal** (e.g. `"E001"`, NOT in the generic-token set) → **still emitted** (proves genuineness-not-length);
  (g) **FP-ceiling PAIRED on the SAME sized-to-storm extraction fixture** — suppression **disabled** → `findings_per_100_loc > FP_CEILING (5.0)` (reproduces 9.4>5.0); **enabled** → `≤ 5.0`. A 0-finding fixture at `0.0` does NOT satisfy this (FR-006).

## DoD
- Head-importability suppression works; the collision fixture (d) proves a common-name deletion is NOT suppressed.
- Generic-literal suppression per the explicit rule; assert-critical literal still emitted.
- `NFR-001` preserved (never "definitely_stale"); render files (`merge/executor.py`, `cli/.../tests.py`) **untouched** (suppression, not info).
- `PWHEADLESS=1 uv run pytest tests/post_merge/ -q` green (incl. the new fixtures); `ruff` + `mypy --strict` clean on the 2 files; no new suppressions.

## Commit
`git add src/specify_cli/post_merge/stale_assertions.py tests/post_merge/test_stale_assertions_precision.py && git commit -m "fix(post_merge): suppress relocation/re-export + generic-literal false positives in the stale-assertion analyzer — closes #2031 #2343"`

## Report back
The head-importability check (what it parses in A's head); the generic-literal rule (N + token set); the fixtures — especially (d) the collision guard (paste it + show it's flagged); FR-006 ceiling proof; pytest counts; ruff+mypy; lane commit SHA. If head-importability can't be computed from the parsed head tree without a full-repo scan, STOP and report (do NOT fall back to bare-name matching, which blinds deletions).

## Activity Log

- 2026-07-07T01:13:43Z – claude – shell_pid=1584876 – Assigned agent via action command
