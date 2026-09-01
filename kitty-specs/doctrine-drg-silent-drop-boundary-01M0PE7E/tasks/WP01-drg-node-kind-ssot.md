---
work_package_id: WP01
title: DRG node-kind SSOT (#3608)
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
planning_base_branch: fix/doctrine-drg-silent-drop-boundary
merge_target_branch: fix/doctrine-drg-silent-drop-boundary
branch_strategy: Planning artifacts for this mission were generated on fix/doctrine-drg-silent-drop-boundary. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/doctrine-drg-silent-drop-boundary unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-doctrine-drg-silent-drop-boundary-01M0PE7E
base_commit: 91f1729f55c5b70a4c5ebd86ad5d829e2a64f2a7
created_at: '2026-08-23T06:46:00.845111+00:00'
subtasks:
- T001
- T002
- T003
history:
- at: '2026-08-23T00:00:00Z'
  actor: tasks
  note: WP created
agent_profile: python-pedro
authoritative_surface: src/charter/synthesizer/
create_intent:
- tests/charter/test_topic_resolver_node_kinds.py
execution_mode: code_change
owned_files:
- src/charter/synthesizer/topic_resolver.py
- tests/charter/test_topic_resolver_node_kinds.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:
`/ad-hoc-profile-load python-pedro` (or `spec-kitty agent profile show python-pedro`
+ `spec-kitty charter context --action implement --json`). Apply its
initialization, boundaries, directives, and tactics; state which you applied.
Use the shadow venv: `export PATH="$PWD/.venv/bin:$PATH"`.

## Objective

Kill the hand-maintained copy of the DRG node-kind set and derive it from the
canonical `NodeKind` enum, so no kind is ever silently unrecognized at the URN
resolution gate — and pin the boundary with a behaviour test that catches a
future revert-to-copy. This is #3608 and the archetype of the whole mission.

## Context

- `src/charter/synthesizer/topic_resolver.py:37` is a hand-literal
  `_DRG_NODE_KINDS: frozenset[str]` (currently 10 kinds). It has drifted **6**
  behind `NodeKind` (`src/doctrine/drg/models.py`, 16 members): `anti_pattern`,
  `asset`, `glossary`, `glossary_pack`, `mission_step_contract`, `template`.
- The membership gate at `topic_resolver.py:236`
  (`if lhs not in _DRG_NODE_KINDS: return None`) silently drops legitimate
  DRG-URN selectors (e.g. `glossary_pack:<id>`).
- **There is already an SSOT twin to reuse**: `src/doctrine/drg/merge.py:504`
  defines `_NODE_KIND_PREFIXES = frozenset(kind.value for kind in NodeKind)`.
- Value == URN-prefix is structurally guaranteed by `DRGNode._validate_urn`
  (`models.py`), so keying membership on `.value` is provably correct.

## Subtasks

### T001 — Derive `_DRG_NODE_KINDS` from `NodeKind`
- Replace the literal frozenset at `topic_resolver.py:37` with a derivation:
  `frozenset(k.value for k in NodeKind)`. Prefer **importing/reusing** the existing
  twin `merge.py:504` `_NODE_KIND_PREFIXES` if that does not create an import
  cycle; otherwise derive locally with the identical expression and a comment
  cross-referencing the twin (single-source intent, G2).
- This adds a `charter → doctrine.drg.models` import (a permitted downward
  dependency). Confirm no cycle (`tests/architectural/test_layer_rules.py`).
- Keep the module comment honest (drop the stale "superset, from …NodeKind" text).

### T002 — Behaviour-pinned drift-guard test  [P]
- New test `tests/charter/test_topic_resolver_node_kinds.py`.
- **Do NOT** rely on `_DRG_NODE_KINDS == {k.value for k in NodeKind}` — that is a
  tautology once T001 lands (squad F7, post-tasks G7). **Pin the behaviour**:
  `monkeypatch`/extend `NodeKind` (or patch the resolver's view of it) with a
  synthetic member and assert the resolver recognizes a URN with the new value at
  the gate **without any edit** to `topic_resolver.py`.
- Acceptance for this WP is carried by this behaviour pin **plus T003** (each
  previously-dropped kind resolves) — NOT by a set-equality assertion. Do not add a
  tautological equality fallback that a lazy implementation could ship green.

### T003 — Previously-dropped kinds resolve at the gate  [P]
- In the same test file, assert that a URN for **each** of the 6 previously-missing
  kinds (`anti_pattern`, `asset`, `glossary`, `glossary_pack`,
  `mission_step_contract`, `template`) is recognized at the `topic_resolver.py:236`
  gate (i.e. the LHS passes membership). Parametrize over all `NodeKind` values so
  new members are covered automatically.
- Red-first: confirm at least the `glossary_pack` case FAILS against the current
  hand-copy before T001, then passes after.

## Branch Strategy

Planning base and final merge target: `fix/doctrine-drg-silent-drop-boundary`.
Execution worktrees are allocated per computed lane from `lanes.json` at
`implement` time — do not create branches by hand.

## Definition of Done

- `_DRG_NODE_KINDS` is enum-derived (no literal); no drift possible.
- Behaviour test proves derivation (not tautology) and passes; all 16 `NodeKind`
  values (incl. the 6 previously-dropped) resolve at the gate.
- `ruff` + `mypy --strict` clean on `topic_resolver.py`; no new suppressions.
- `pytest tests/architectural/test_layer_rules.py -q` green (import boundary).
- Targeted: `pytest tests/charter/test_topic_resolver_node_kinds.py -q` green.

## Risks / reviewer guidance

- Import cycle risk (charter→doctrine.drg.models). Reviewer: confirm layer rules
  pass and no cycle introduced.
- Reviewer: reject a tautological equality-only test — the pin must fail if the
  derivation is reverted to a literal (F7). Note: spec FR-002's literal wording
  ("assert equals `{k.value for k in NodeKind}`") is **superseded** here by the
  behaviour pin (T002) + the dropped-kinds gate (T003); accept those, not equality.
