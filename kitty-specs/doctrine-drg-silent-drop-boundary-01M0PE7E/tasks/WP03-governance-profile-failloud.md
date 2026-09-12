---
work_package_id: WP03
title: 'Governance-profile fail-loud: built-in e2e + org-tier implement (#3629 p2)'
dependencies: []
requirement_refs:
- FR-008
planning_base_branch: fix/doctrine-drg-silent-drop-boundary
merge_target_branch: fix/doctrine-drg-silent-drop-boundary
branch_strategy: Planning artifacts for this mission were generated on fix/doctrine-drg-silent-drop-boundary. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/doctrine-drg-silent-drop-boundary unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
history:
- at: '2026-08-23T00:00:00Z'
  actor: tasks
  note: WP created
agent_profile: python-pedro
authoritative_surface: src/doctrine/drg/org_governance.py
create_intent:
- src/doctrine/drg/org_governance.py
- tests/doctrine/drg/migration/test_governance_scope_e2e.py
- tests/doctrine/drg/test_org_governance_failloud.py
execution_mode: code_change
owned_files:
- src/doctrine/drg/org_pack_loader.py
- src/doctrine/drg/org_governance.py
- src/doctrine/drg/validator.py
- tests/doctrine/drg/migration/test_governance_scope_e2e.py
- tests/doctrine/drg/test_org_governance_failloud.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (+ `spec-kitty charter context --action
implement --json`). Apply + state what you applied. Shadow venv:
`export PATH="$PWD/.venv/bin:$PATH"`.

## Objective

Make a nonexistent governance-profile `selected_*` selection fail loud on **both**
tiers. The built-in guard already exists but is only unit-tested with synthetic
edges — add an end-to-end test. The org tier has **no scope path at all** today —
implement it. This is #3629 part 2 (built-in verify-and-close + org-tier build).

## Context (from squad findings F8, F9)

- Built-in: `assert_governance_scope_edges_resolve` (`extractor.py:1406`) is wired
  into `generate_graph` (`:1574`) and raises on unresolved `selected_*` targets.
  Its tests (`test_extractor.py:1608-1653`) call it with **synthetic** edges — they
  never drive `generate_graph`. The commit message for `d8beee2761` admits this.
- Org tier: `extract_governance_profile_scope_edges` (`extractor.py:1336`) reads
  **only** built-in missions (`_missions_root`). `org_pack_loader.py` has **no**
  governance/`selected_*` handling — an org-tier typo is unread AND unguarded (a
  total no-op, not even a silent prune).

**Ownership notes (post-tasks G1/G2)**:
- WP02 owns `extractor.py` — do NOT edit it. **Import**
  `_GOVERNANCE_PROFILE_SCOPE_FIELDS` from `extractor` (a read, not an edit) rather
  than copying it (G2: a hand-copy is the anti-pattern WP01 kills). If it must stay
  private, add a C-009 drift-guard parity test instead.
- **The raise cannot live in `org_pack_loader.py`** (G1): `merge_three_layers`
  (`merge.py:1185-1194`) deliberately **warns, not raises** on dangling org
  endpoints, and its docstring names `doctrine.drg.validator.validate_dangling_references`
  as the escalation home. A pre-merge, single-pack guard also can't see built-in
  targets → false positives. So the escalation belongs in **`validator.py`** and is
  **invoked post-merge**. The org-consuming callers are `executor.py:362` /
  `action_doctrine_bundle.py:192` — **owned by WP04**. Therefore **WP04 depends on
  WP03 and invokes this guard** (WP03 defines it; WP04 wires the one-line call).
  Do not edit WP04's caller files from here.

## Subtasks

### T013 — Built-in end-to-end `generate_graph` characterization pin  [P]
- New `tests/doctrine/drg/migration/test_governance_scope_e2e.py`.
- Build a temp doctrine root whose built-in `governance-profile.yaml` has a
  fictional `selected_*` id; assert `generate_graph(...)` raises `ValueError`
  naming `mission_type:field=id` (pins the `:1574` wiring, not just the pure
  extractor). Valid selections → no raise.
- **Not red-first** (G8): the built-in guard already exists, so this test passes on
  arrival — it is a **characterization/regression pin** protecting the existing
  wiring, not a bug fix. That is legitimate; do not force it to go red.

### T014 — Implement org-tier governance-profile scope extraction
- In `org_governance.py`, read each org pack's governance-profile selections.
  **Import** `_GOVERNANCE_PROFILE_SCOPE_FIELDS` from `extractor` (no copy). Note
  org packs carry governance at `<pack>/mission_types/<type>/governance-profile.yaml`
  (per `mission_type_profiles.py:807`), a different path shape than built-in — this
  is genuinely net-new, not reuse.
- Mint the org-tier `scope` edges (via `org_pack_loader.py` fragment handling) so
  org-tier selections enter the merged DRG rather than being unread.

### T015 — Org-tier fail-loud guard (post-merge, in `validator.py`)
- Add a governance-scope escalation in `validator.py` (alongside / extending
  `validate_dangling_references`): after merge, any governance-`scope` edge whose
  target is not in the merged node universe raises a triage-required error naming
  `mission_type:field=id` — while ordinary org edges keep merge's WARN semantics.
- This function is **defined here** and **invoked by WP04** post-merge at the two
  org-consuming callers (see ownership note). Provide it with a clear signature so
  WP04 can call it with one line.

### T016 — Org-tier fail-loud tests
- New `tests/doctrine/drg/test_org_governance_failloud.py`: red-first — an org pack
  whose governance-profile names a nonexistent `selected_*` id fails loud; a valid
  org-tier selection resolves and mints its scope edge with no false positive.

## Branch Strategy

Planning base + merge target: `fix/doctrine-drg-silent-drop-boundary`. Worktrees
per computed lane from `lanes.json` at implement time.

## Definition of Done

- Built-in e2e `generate_graph` raise test passes (closes #3629 p2 built-in).
- Org-tier governance-profile scope extraction implemented + wired; org-tier
  selections reach the DRG.
- Org-tier fail-loud guard raises on nonexistent selection naming the id; valid
  selections pass (no false positive). Red-first tests demonstrate both.
- `ruff` + `mypy --strict` clean; no new suppressions; touched functions ≤15
  complexity (NFR-004). Terminology guard green
  (`pytest tests/architectural/test_no_legacy_terminology.py -q`, NFR-003 — this WP
  touches `src/doctrine/`). No edits to `extractor.py` (import the field constant)
  and no edits to WP04's caller files (WP04 invokes the guard).
- Targeted greens: `pytest tests/doctrine/drg/migration/test_governance_scope_e2e.py tests/doctrine/drg/test_org_governance_failloud.py -q`.
- The org-tier fail-loud test (T016) drives the guard via a constructed merged
  graph OR through the WP04-wired path once available; it must genuinely go red
  before T014/T015.

## Risks / reviewer guidance

- Scope creep: org-tier extraction is net-new; keep it minimal (parity with the
  built-in selectors), do not redesign governance-profiles.
- Reviewer: reject any "document the gap" close for the org tier — FR-008 requires
  a passing org-tier fail-loud test (C-002). Confirm the field constant is
  **imported**, not copied (G2). Confirm the raise is in `validator.py` (post-merge),
  not `org_pack_loader.py` (pre-merge would false-positive on built-in targets, G1).
