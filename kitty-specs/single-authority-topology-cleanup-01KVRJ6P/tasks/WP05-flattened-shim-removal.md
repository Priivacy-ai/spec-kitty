---
work_package_id: WP05
title: FLATTENED delete + ensure_topology removal + safe_commit shim campsite (FR-002/FR-003)
dependencies:
- WP04
requirement_refs:
- C-006
- FR-002
- FR-003
- NFR-003
- NFR-004
tracker_refs: []
planning_base_branch: feat/single-authority-topology-cleanup
merge_target_branch: feat/single-authority-topology-cleanup
branch_strategy: Planning artifacts for this mission were generated on feat/single-authority-topology-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-authority-topology-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1846199"
history:
- Created by /spec-kitty.tasks 2026-06-23
agent_profile: python-pedro
authoritative_surface: src/specify_cli/migration/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/migration/backfill_topology.py
- tests/specify_cli/migration/test_backfill_topology.py
- src/specify_cli/cli/commands/agent/mission.py
- src/specify_cli/cli/commands/upgrade.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt its
directives/tactics (or `/ad-hoc-profile-load python-pedro`). State which you applied.

## Objective
Three removals: **FR-002** neutralize `CommitTargetKind.FLATTENED` (its enum member
is deleted with the whole enum LAST, in WP16 — here, convert its remaining
**producers** to plain `CommitTarget(ref=…)`, AST-verify it is write-only-dead, and
verify nothing serializes the former value so WP16 can delete the member cleanly);
**FR-003** remove the dead `ensure_topology` persist shim and retarget its tests;
**campsite** remove the dead `safe_commit` re-export shim.

> NOTE ON SEQUENCING (re-sequenced 2026-06-23): this WP now runs right after WP04
> (dep WP04, NOT WP16). **WP16 — the enum deletion — runs LAST in lane B** (after
> WP07) and deletes the `CommitTargetKind` enum INCLUDING the FLATTENED member. This
> WP does NOT delete the enum or the member; it CONVERTS the FLATTENED **producers**
> to plain `CommitTarget(ref=…)` (the one WP04 did not own, `upgrade.py:214`) + the
> AST-verification of write-only-deadness, and the two non-enum removals (FR-003,
> campsite). Leaving FLATTENED write-only-dead is what lets WP16 delete the member
> cleanly later. If WP04 already neutralized a producer, just assert it here.

## Context
- FLATTENED producers: `resolution.py:156`, `runtime_bridge.py:241` (WP04-owned),
  `upgrade.py:214` (this WP). All emit PRIMARY-equivalent. Zero `is/== FLATTENED`
  decision reads.
- The `flattened` provenance **meta-flag** (`meta.setdefault("flattened", False)`,
  `mission_creation.py` / `doctor.py`) is SEPARATE and SURVIVES (C-006).
  `FLATTENED.value == "flattened"` string-collides — verify by AST/symbol, not grep.
- `ensure_topology` (`backfill_topology.py:110`): zero `src/` callers; mint inlines
  `classify_topology`, backfill uses `backfill_mission_topology`.
- `safe_commit` re-export shim: `cli/commands/agent/mission.py:54-58`
  (`from specify_cli.git import safe_commit  # noqa: F401`) — 0 external importers.

## Subtasks
### T012 — Delete FLATTENED + AST-verify write-only-dead (NFR-003)
Confirm (by AST/symbol) zero `is/== CommitTargetKind.FLATTENED` decision reads and
that nothing serializes the enum value. Remove the `upgrade.py:214` FLATTENED
producer (emit plain `CommitTarget(ref=…)`). Ensure the WP01 guard's FLATTENED arm
flips green. KEEP the `flattened` meta-flag (C-006) — do not touch it.

### T013 — Remove ensure_topology shim + retarget tests
Delete `ensure_topology` from `backfill_topology.py` and drop it from `__all__`.
Retarget its tests in `test_backfill_topology.py` onto `read_topology` (the pure
reader) + `backfill_mission_topology` (the persist path). No production caller
should break (there are none).

### T014 — Campsite: remove dead safe_commit re-export shim
Remove the `safe_commit` re-export shim lines (`mission.py:54-58`). Verify no
repo-wide importer depends on `from specify_cli.cli.commands.agent.mission import safe_commit`
(grep src/tests/scripts — 0 expected). Bounded to those lines.

## Campsite (#1970)
Remove dead imports/`__all__` entries exposed; fix lint/type debt on touched lines.

## Test approach (doctrine standard)

> **Test approach (doctrine standard — DIRECTIVE_034/036/041, #2071 CTn).** Assert the **observable contract** — returned value, resolved surface/ref, persisted JSONL/`meta.json`, CLI `--json` payload, or gate verdict — **never** the internal call graph or "collaborator X was invoked" (CT4/D036). Build mission fixtures by delegating to the **production creation seam** (`create_mission_core` / the existing `_stored_topology` helper), not a hand-rolled `meta.json` writer that rots (CT3); use **production-shaped data** — a real 26-char ULID + 8-char mid8, never a short placeholder (testing-principles). Any architectural guard/ratchet anchors keys on `_ratchet_keys.composite_key` (qualname + token-line) or an AST node — **never `file.py:NNN`** — and reuses `audit.py`/`_ratchet_keys.py` (CT1); resolve symbols by AST, never by grepping a string that collides with a surviving flag (NFR-003). Any xfail/skip is a **RED-by-design ATDD pin that names the WP that drains it** and is removed (not re-keyed) when the fix lands — never a defect mask (CT2). Prove behavior-neutrality via the **differential cell over the `(topology × transient)` matrix** PLUS at least one **absolute** assertion (see below) — never a brittle golden count of sites/LOC/refs (CT5); prefer a **tightening ratchet** (count only drops, keyed by symbol-set) over a fixed `== N`. **Pair every "allow / passes / absorbs / ignores-residue" assertion with its negative control** ("still-blocks / still-raises / wrong-topology-differs") — one-sided gate tests let the over-allow mutant survive. When a touched test goes red, classify it (stale→re-point preserving setup / fakeable→delete / valid→fix the product) and establish causation by **code-path coupling, not git-blame** (D041).

### WP05-specific test-DoD
- **(a) T012 / WP01-coupling negative control.** The WP01 FLATTENED guard's planted self-test must include the `"flattened"` **meta-flag negative control**: a legit `meta["flattened"] = False` provenance flag must NOT trip the guard (`FLATTENED.value == "flattened"` collides — the flag survives, C-006).
- **(b) T013 absent-field absorption + edge-case preservation.** The retargeted `ensure_topology` tests must assert the **absent-field absorption** specifically: a `meta.json` with **no `topology` key** → a concrete derived topology, **never `None`**. Preserve the excavated edge-cases — apply `delete-the-assertion-not-the-test` (re-point the assertion onto `read_topology`/`backfill_mission_topology`, keep the setup and edge-cases; do not delete the whole test to dodge a red).

## Definition of Done
- FLATTENED gone, AST-verified dead, meta-flag intact; `ensure_topology` gone with
  tests retargeted; `safe_commit` shim gone.
- The FLATTENED guard self-test carries the `flattened=False` meta-flag negative
  control; the retargeted `ensure_topology` tests assert absent-field → concrete
  topology (never None) and preserve the prior edge-cases.
- WP01 guard green for both arms; `ruff`/`mypy` clean; full `tests/` green.

## Branch Strategy
`feat/single-authority-topology-cleanup`. Lane B (sequential, after WP04). Worktree from `lanes.json`.

## Reviewer guidance
Confirm the `flattened` meta-flag is untouched (C-006). Confirm FLATTENED deadness
was symbol-verified, not grep-verified. Confirm `ensure_topology` has zero callers
before deletion.

## Activity Log

- 2026-06-23T10:16:14Z – claude:opus:python-pedro:implementer – shell_pid=1777650 – Started implementation via action command
- 2026-06-23T10:38:51Z – claude:opus:python-pedro:implementer – shell_pid=1777650 – Ready: upgrade.py FLATTENED producer -> plain CommitTarget(ref=...), FLATTENED AST-verified write-only-dead (0 decision-reads, 0 .value serialize sites); ensure_topology + safe_commit shims removed; flattened meta-flag (C-006) intact; ratchet shrunk by 2 upgrade.py keys; enum still imports (WP16 deletes it last)
- 2026-06-23T10:39:39Z – claude:opus:reviewer-renata:reviewer – shell_pid=1846199 – Started review via action command
- 2026-06-23T10:44:57Z – user – shell_pid=1846199 – Review passed: FLATTENED producer (upgrade.py) converted to plain CommitTarget(ref=...), enum+member still present (WP16 deletes). AST write-only-dead: 0 is/== FLATTENED decision reads in src; remaining refs are WP04 producers + docstrings. C-006 meta-flag INTACT — live mission_creation.py:433 setdefault untouched, _FLATTENED_KEY survives backfill persist L194; only dead ensure_topology copy removed (symbol-resolved). ensure_topology removed (0 src callers), 4 tests retargeted non-vacuously (absent-field->concrete never None + flattened preservation). safe_commit shim removed (0 importers); 3 monkeypatch tests re-pointed onto real commit_for_mission seam (CT4). Tests 32+75 passed; ruff/mypy clean on owned (3 mission.py no-any-return pre-existing per base). Out-of-owned touches (guard ratchet shrink, inventory.md bookkeeping, monkeypatch files) are mandatory shim-removal fallout.
