---
work_package_id: WP07
title: CommitResult JSON-serialization (#1891, FR-013)
dependencies:
- WP17
requirement_refs:
- FR-013
tracker_refs: []
planning_base_branch: feat/single-authority-topology-cleanup
merge_target_branch: feat/single-authority-topology-cleanup
branch_strategy: Planning artifacts for this mission were generated on feat/single-authority-topology-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-authority-topology-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T018
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "2039700"
history:
- Created by /spec-kitty.tasks 2026-06-23
agent_profile: python-pedro
authoritative_surface: src/specify_cli/git/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/git/commit_helpers.py
- src/specify_cli/cli/commands/agent/tasks.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt its
directives/tactics (or `/ad-hoc-profile-load python-pedro`). State which you applied.

## Objective
**FR-013 (#1891)** — make `CommitResult` JSON-serializable so
`agent tasks map-requirements --json` emits valid JSON instead of
`Object of type CommitResult is not JSON serializable`.

> PLANNING-RESOLVED (probe): `CommitResult = {sha, destination_ref, worktree_root: Path}`
> (`commit_helpers.py:422`) is **disjoint** from the `.kind` removal — the bug is
> the un-serializable `Path` field, not the enum. This WP is standalone; it lives
> in Lane B only because it shares `commit_helpers.py`/`tasks.py` with the enum
> eradication (same-lane sequential ownership). Scope `tasks.py` edits to the
> CommitResult-emit lines only.

## Context
- `CommitResult` is a frozen dataclass with a `Path` field (`worktree_root`).
- The `--json` failure is at the `map-requirements` emit path in `tasks.py`
  (around the `commit_result` usage near `tasks.py:3873-3885`).
- OUT OF SCOPE: the separate "`--json` flag missing from `agent action implement`"
  half of #1891.

## Subtasks
### T018 — Make CommitResult JSON-serializable
Add a serialization path to `CommitResult` (e.g. a `to_dict()` / `__json__` /
asdict-with-str(Path) helper) that renders `worktree_root` as a string. At the
`map-requirements --json` emit site, serialize via that helper so the payload is a
valid JSON document. Add a focused test: `map-requirements --json` output parses
with `json.loads` and contains the expected `sha`/`destination_ref`/`worktree_root`
(as a string). Behavior: broken→working (this is a bug fix, not behavior-neutral).

## Campsite (#1970)
Fix lint/type debt on touched lines; if other dataclasses in `commit_helpers.py`
have the same Path-serialization gap on a `--json` path you touch, note it (do not
broaden scope unless it's the same emit site).

## Test approach (doctrine standard)

> **Test approach (doctrine standard — DIRECTIVE_034/036/041, #2071 CTn).** Assert the **observable contract** — returned value, resolved surface/ref, persisted JSONL/`meta.json`, CLI `--json` payload, or gate verdict — **never** the internal call graph or "collaborator X was invoked" (CT4/D036). Build mission fixtures by delegating to the **production creation seam** (`create_mission_core` / the existing `_stored_topology` helper), not a hand-rolled `meta.json` writer that rots (CT3); use **production-shaped data** — a real 26-char ULID + 8-char mid8, never a short placeholder (testing-principles). Any architectural guard/ratchet anchors keys on `_ratchet_keys.composite_key` (qualname + token-line) or an AST node — **never `file.py:NNN`** — and reuses `audit.py`/`_ratchet_keys.py` (CT1); resolve symbols by AST, never by grepping a string that collides with a surviving flag (NFR-003). Any xfail/skip is a **RED-by-design ATDD pin that names the WP that drains it** and is removed (not re-keyed) when the fix lands — never a defect mask (CT2). Prove behavior-neutrality via the **differential cell over the `(topology × transient)` matrix** PLUS at least one **absolute** assertion (see below) — never a brittle golden count of sites/LOC/refs (CT5); prefer a **tightening ratchet** (count only drops, keyed by symbol-set) over a fixed `== N`. **Pair every "allow / passes / absorbs / ignores-residue" assertion with its negative control** ("still-blocks / still-raises / wrong-topology-differs") — one-sided gate tests let the over-allow mutant survive. When a touched test goes red, classify it (stale→re-point preserving setup / fakeable→delete / valid→fix the product) and establish causation by **code-path coupling, not git-blame** (D041).

### WP07-specific test-DoD
- **T018 drives the CLI `--json` external interface.** The test invokes `agent tasks map-requirements --json`, parses stdout with `json.loads(stdout)`, and asserts `worktree_root` is a **non-empty string containing the mission slug** (kills the `""` / `"None"` serialization mutant) — NOT a unit test of the `to_dict()` helper in isolation.

## Definition of Done
- `map-requirements --json` emits valid JSON; the focused test parses CLI stdout
  with `json.loads` and asserts `worktree_root` is a non-empty slug-bearing string
  (not the helper in isolation). `ruff`/`mypy` clean; full `tests/` green.

## Branch Strategy
`feat/single-authority-topology-cleanup`. Lane B (sequential, after WP17). Worktree from `lanes.json`.

## Reviewer guidance
Confirm the fix is scoped to serialization (no `.kind`/enum coupling). Confirm the
test actually parses the CLI `--json` output, not just the dataclass.

## Activity Log

- 2026-06-23T12:03:16Z – claude:opus:python-pedro:implementer – shell_pid=2026402 – Started implementation via action command
- 2026-06-23T12:10:34Z – claude:opus:python-pedro:implementer – shell_pid=2026402 – Ready: CommitResult JSON-serializable; map-requirements --json parses; test asserts worktree_root is non-empty slug-bearing string via CLI stdout
- 2026-06-23T12:11:22Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=2039700 – Started review via action command
- 2026-06-23T12:18:26Z – user – shell_pid=2039700 – Review passed: CommitResult.to_dict() serializes worktree_root (Path→str); emit site uses commit_result.to_dict() at tasks.py:3888; CLI --json test drives real CommitResult via CliRunner (not a dict stub), parses stdout with json.loads, asserts worktree_root is non-empty slug-bearing string. Red-first confirmed (AttributeError on to_dict → test fails). No .kind/CommitTargetKind coupling in owned files. ruff clean; mypy single pre-existing no-any-return at commit_helpers.py:491 (pre-dates WP07, confirmed via stash). 5 tests green. WP16-coupling note: test imports CommitTargetKind for fixture; WP16 inherits cleanup obligation.
