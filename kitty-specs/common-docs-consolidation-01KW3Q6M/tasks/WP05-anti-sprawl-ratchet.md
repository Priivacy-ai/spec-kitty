---
work_package_id: WP05
title: Anti-sprawl ratchet (ruler 3, report-only)
dependencies:
- WP01
- WP02
requirement_refs:
- C-002
- C-003
- FR-007
tracker_refs: []
planning_base_branch: docs/2165-consolidation-research
merge_target_branch: docs/2165-consolidation-research
branch_strategy: Planning artifacts for this mission were generated on docs/2165-consolidation-research. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/2165-consolidation-research unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
- T025
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: scripts/docs/anti_sprawl_ratchet.py
create_intent:
- scripts/docs/anti_sprawl_ratchet.py
- tests/docs/test_anti_sprawl_ratchet.py
execution_mode: code_change
owned_files:
- scripts/docs/anti_sprawl_ratchet.py
- tests/docs/test_anti_sprawl_ratchet.py
role: implementer
tags: []
shell_pid: "649003"
---

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load python-pedro` (or read the profile YAML and adopt it). State which directives apply, then proceed.

## Objective

Build the **anti-sprawl ratchet** as a **report-only** ruler with a **concrete content-anchored floor**, a **binding reference to WP02's directive**, and **four injection self-tests** (one per condition). It detects the four sprawl regressions; Mission B flips it to blocking against the cleaned tree.

## Context

Depends on WP01 (the ADR's 13-section structure) **and WP02** (the directive id it must reference — C-003). Read the existing `tests/architectural/` gate patterns (self-mutation test + concrete floor) for the house idiom. **Report-only here** (C-002 — flipping to blocking is Mission B, paired with a full-gate dry-run per C-004). No doc-tree mutation, no new deps.

## Subtasks

### T021 — `scripts/docs/anti_sprawl_ratchet.py` (4 detectors)
Detect: (a) a second top-level doc root (anything outside the single `docs/` root claiming to be docs); (b) any `docs/*/` section directory missing `index.md`; (c) an ADR missing the frontmatter schema; (d) a re-introduced `docs/<version>x` shadow tree. Output `{ violations: [{condition, path}], baseline_count, directive_ref, floor }`; print; **exit 0** (report-only). Add a wired-but-off `--strict` flag for Mission B.

### T022 — The content-anchored floor
Embed a **concrete enumerated baseline** — the 13 canonical section names + "exactly one docs root" — so the ratchet compares against a real value, not an empty set that passes everything. (Mirror the `tests/architectural/` concrete-floor idiom.)

### T023 — Bind to the directive (C-003)
The violation message/config references WP02's directive id, sourced from the **single shared constant** WP02 defines.

### T024 — Four injection self-tests
`tests/docs/test_anti_sprawl_ratchet.py`: four fixtures, one per condition (second-root / missing-`index.md` / un-frontmattered-ADR / shadow-tree), each asserting the ratchet **detects** it (and reds under `--strict`); a clean fixture passes. Assert the floor is the enumerated 13-section list (not empty).

### T025 — Report-only baseline
Run over the live tree; confirm exit 0; record the baseline violation count (the deltas Mission B closes).

## Branch Strategy

Planning + merge target: `docs/2165-consolidation-research`. Worktree per `lanes.json` (Lane C, after WP01 + WP02).

## Definition of Done

- [ ] The ratchet detects all four conditions; exits 0 (report-only).
- [ ] The floor is a concrete enumerated baseline (13 sections / one root).
- [ ] The violation message references WP02's directive id (C-003 binding).
- [ ] **Four injection self-tests each red** on their seeded violation; clean fixture green.
- [ ] Report-only baseline recorded; `ruff`/`mypy` clean; no doc-tree mutation.

## Risks & Reviewer Guidance

- The fakeable trap: each of the 4 conditions is individually vacuous if the ratchet asserts nothing concrete. Reviewer MUST confirm all four injection fixtures red and the floor is non-empty.
- Coordinate the directive id with WP02 before finishing T023.

## Activity Log

- 2026-06-27T07:14:17Z – claude:opus:python-pedro:implementer – shell_pid=619014 – Assigned agent via action command
- 2026-06-27T07:31:47Z – claude:opus:reviewer-renata:reviewer – shell_pid=649003 – Started review via action command
