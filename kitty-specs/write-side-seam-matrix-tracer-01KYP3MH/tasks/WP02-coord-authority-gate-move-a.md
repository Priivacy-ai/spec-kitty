---
work_package_id: WP02
title: Coord-authority gate + emit.py Move A
dependencies: []
requirement_refs:
- FR-007
- FR-010
- NFR-005
planning_base_branch: feat/write-side-seam-matrix-tracer
merge_target_branch: feat/write-side-seam-matrix-tracer
branch_strategy: Planning artifacts for this mission were generated on feat/write-side-seam-matrix-tracer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/write-side-seam-matrix-tracer unless the human explicitly redirects the landing branch.
created_at: '2026-07-29T09:24:15+00:00'
subtasks:
- T006
- T007
- T008
- T009
- T046
history:
- at: '2026-07-29T09:24:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/decisions/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/decisions/emit.py
- tests/architectural/test_resolution_authority_gates.py
- tests/architectural/resolution_gate_allowlist.yaml
- docs/adr/3.x/2026-06-26-1-single-authority-seam-and-call-site-gate.md
role: implementer
tags: []
task_type: implement
tracker_refs:
- '3055'
- '2966'
---

# Work Package Prompt: WP02 – Coord-authority gate + emit.py Move A

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

## Objective

Route `decisions/emit.py` off the coord-authority allow-list to the kind-aware seam and re-pin the census floor **4→3** — a single **atomic** change ("Move A", strengthening) — so routing COORD writes is unblocked while the gate stays **non-vacuous** (#3055). See [contracts/coord-authority-gate.md](../contracts/coord-authority-gate.md).

## Context

- The coord-authority gate (`tests/architectural/test_resolution_authority_gates.py`) scans kind-blind `resolve_feature_dir_for_mission` writes and enforces a floor of by-design coord writes to prove non-vacuity (`test_resolution_authority_gates.py:704-723/1661-1716`). The floor/baseline and allow-list live in the **test module + `resolution_gate_allowlist.yaml`**, not in `src`.
- **Route ONLY `emit.py`.** The other three sites — `widen/state.py:63`, `agent_tasks_ports.py:322`, `lanes/recovery.py:765` — are **by-design sanctioned** kind-blind coord writes and MUST stay on the kind-blind resolver. Routing all four → live census 0 → vacuous gate (forbidden by ADR `2026-06-26-1-single-authority-seam-and-call-site-gate`).
- **Nothing depends on this WP.** Per D-6, the `write_target`-routed matrix/tracer writers are gate-invisible; they route via `write_target` (kind-aware) and never trip the gate. This WP is the atomic Move A only.

## Subtasks

### T006 — Red-first non-vacuity tests (DIRECTIVE_003)
Before touching `emit.py`, add tests proving the gate still **FAILS** on: (a) a `write_target()` call with **no `kind`**, and (b) a re-introduced kind-blind wrong-surface write. A literal-vs-literal assertion is vacuous and disallowed — the test must exercise the real predicate.

### T007 — Route `decisions/emit.py:71`
Convert `decisions/emit.py:_mission_dir:71` to the kind-aware seam (`write_target(<DECISION kind>)`) so it no longer calls the kind-blind `resolve_feature_dir_for_mission`. The `status.events.jsonl`/decision COORD write MUST still land on the coord surface — **no regression to primary**.

### T008 — Re-pin the floor + drop the allow-list/by-design entries (same change)
- Re-pin `COORD_AUTHORITY_WRITE_FLOOR` 4→3 and `coord_authority_baseline` (with rationale).
- Remove the stale `resolution_gate_allowlist.yaml` `emit.py` entry (staleness twin-guard).
- Remove `emit.py` from **every** by-design assertion site in `test_resolution_authority_gates.py`, not just one: the `_COORD_WRITE_BY_DESIGN` set (`:720`) **and** the explicit assertions/docstrings at `:1151`, `:1228`, `:1641` (else a stale assertion reds). After removal the three genuine by-design sites (`widen/state.py`, `agent_tasks_ports.py`, `lanes/recovery.py`) remain → floor 3, margin 2, non-vacuous.

### T009 — Assert the three by-design sites remain
Add/keep an assertion that `widen/state.py`, `agent_tasks_ports.py`, and `lanes/recovery.py` are still counted as by-design kind-blind coord writes, so the floor of 3 is non-vacuous. Document the non-vacuity invariant: the live census MUST NOT drop below 3.

### T046 — Ratify the governing ADR (operator-approved 2026-07-29)
Flip `docs/adr/3.x/2026-06-26-1-single-authority-seam-and-call-site-gate.md` from `status: Proposed` to `status: Accepted`. This WP re-pins the census floor that ADR governs (Move A) and names it the Move B amendment target, so it is the natural ratification site (post-tasks squad m5 / architect M3; HiC-approved). Keep the two-ADRs-share-`2026-06-26-1` cite-by-slug discipline intact.

## Branch Strategy

Both planning and merge target are `feat/write-side-seam-matrix-tracer`. Allocate via `/spec-kitty.implement WP02`.

## Definition of Done
- `emit.py` routed; floor at 3; allow-list + by-design entries updated in the **same commit**.
- The four named gate tests pass; non-vacuity tests (T006) pass; three by-design sites still counted.
- ADR `2026-06-26-1-single-authority-seam-and-call-site-gate` ratified Proposed→Accepted (T046, HiC-approved).
- `ruff`/`mypy` clean; complexity ≤ 15.

## Risks / Reviewer guidance
- **Do NOT route the other three sites.** Verify the census lands at exactly 3.
- A gate-predicate widen (Move B) is out of scope here and would be an **ADR amendment** of `2026-06-26-1-single-authority-seam-and-call-site-gate`, def-use gated with an alias-bite non-vacuity test — not a contract-only change.
- Confirm the decision/status COORD write still lands on coord (no primary regression).
