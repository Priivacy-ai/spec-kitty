---
work_package_id: WP08
title: Polymorphic load_meta + 3-contract adapters (FR-006a)
dependencies:
- WP01
requirement_refs:
- FR-006
- NFR-001
tracker_refs: []
planning_base_branch: feat/single-authority-topology-cleanup
merge_target_branch: feat/single-authority-topology-cleanup
branch_strategy: Planning artifacts for this mission were generated on feat/single-authority-topology-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-authority-topology-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T019
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1350114"
history:
- Created by /spec-kitty.tasks 2026-06-23
agent_profile: python-pedro
authoritative_surface: src/specify_cli/mission_metadata.py
create_intent:
- tests/specify_cli/test_mission_metadata.py
execution_mode: code_change
owned_files:
- src/specify_cli/mission_metadata.py
- tests/specify_cli/test_mission_metadata.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt its
directives/tactics (or `/ad-hoc-profile-load python-pedro`). State which you applied.

## Objective
**FR-006a** — build the ONE canonical polymorphic
`load_meta(dir, *, allow_missing, on_malformed)` (in `mission_metadata.py`) that
absorbs the 3 distinct error contracts the codebase currently spells ~131 ways,
plus the 2 genuinely-distinct adapters. WP09/WP10 then sweep the call sites onto
it. Behavior-neutral per call site.

## Context (the 3 contracts, alphonso-verified)
1. `mission_metadata.load_meta:252` — None-on-missing, raise-on-malformed (canonical today).
2. `task_helpers.load_meta:420` / `task_utils/support.load_meta:363` — raise-on-missing,
   **utf-8-sig BOM-tolerant** decode.
3. `retrospective/generator._load_meta:126` / `review/__init__._load_meta:382` —
   silent empty-dict on any error.
The `allow_missing` (bool) and `on_malformed` (enum/callable: `raise` | `empty` |
`none`) parameters must reproduce all three. Preserve the utf-8-sig BOM decode as
an option. Keep the **absent vs malformed** split consistent with FR-004's
boundary (missing field → None/absorb; corrupt → raise/typed).

## Subtasks
### T019 — Build the polymorphic reader + adapters
Implement `load_meta(dir, *, allow_missing: bool = …, on_malformed: … = …)` in
`mission_metadata.py` covering the 3 contracts + utf-8-sig. Provide the 2 thin
adapters that map the legacy call shapes (the raise-on-missing one; the
silent-empty one) onto it. Add focused unit tests exercising EACH contract branch
(missing+allow / missing+raise / malformed+raise / malformed+empty / malformed+none
/ utf-8-sig BOM file). Do NOT yet convert call sites (that is WP09/WP10).

## Campsite (#1970)
Hoist S1192 literals (the `meta.json` filename, encodings); fix lint/type debt on
touched lines.

## Test approach (doctrine standard)

> **Test approach (doctrine standard — DIRECTIVE_034/036/041, #2071 CTn).** Assert the **observable contract** — returned value, resolved surface/ref, persisted JSONL/`meta.json`, CLI `--json` payload, or gate verdict — **never** the internal call graph or "collaborator X was invoked" (CT4/D036). Build mission fixtures by delegating to the **production creation seam** (`create_mission_core` / the existing `_stored_topology` helper), not a hand-rolled `meta.json` writer that rots (CT3); use **production-shaped data** — a real 26-char ULID + 8-char mid8, never a short placeholder (testing-principles). Any architectural guard/ratchet anchors keys on `_ratchet_keys.composite_key` (qualname + token-line) or an AST node — **never `file.py:NNN`** — and reuses `audit.py`/`_ratchet_keys.py` (CT1); resolve symbols by AST, never by grepping a string that collides with a surviving flag (NFR-003). Any xfail/skip is a **RED-by-design ATDD pin that names the WP that drains it** and is removed (not re-keyed) when the fix lands — never a defect mask (CT2). Prove behavior-neutrality via the **differential cell over the `(topology × transient)` matrix** PLUS at least one **absolute** assertion (see below) — never a brittle golden count of sites/LOC/refs (CT5); prefer a **tightening ratchet** (count only drops, keyed by symbol-set) over a fixed `== N`. **Pair every "allow / passes / absorbs / ignores-residue" assertion with its negative control** ("still-blocks / still-raises / wrong-topology-differs") — one-sided gate tests let the over-allow mutant survive. When a touched test goes red, classify it (stale→re-point preserving setup / fakeable→delete / valid→fix the product) and establish causation by **code-path coupling, not git-blame** (D041).

### WP08-specific test-DoD
- **Genuinely un-parseable malformed fixture (identity-input trap).** The malformed-meta fixture must be **genuinely un-parseable JSON** (e.g. `{"a":`), NOT an empty file — an empty file hits the *missing* arm and masks the *malformed* branch (the input-identity trap). Each of the contract branches (missing+allow / missing+raise / malformed+raise / malformed+empty / malformed+none / utf-8-sig BOM) is asserted by its **observable result** (returned dict / raised typed error / `{}`), never by the reader's internal call args.

## Definition of Done
- The polymorphic reader + 2 adapters exist with per-contract tests; ≥90%
  diff-coverage on the new branches. `ruff`/`mypy` clean; full `tests/` green
  (no call site changed yet, so behavior unchanged).
- The malformed fixture is genuinely un-parseable JSON (not an empty file); each of
  the 6 contract branches is asserted by observable result.

## Branch Strategy
`feat/single-authority-topology-cleanup`. Lane C. Worktree from `lanes.json`.

## Reviewer guidance
Confirm all 3 contracts + utf-8-sig are covered by direct tests (not just the
happy path). Confirm absent-vs-malformed matches FR-004's None-vs-raise boundary.

## Activity Log

- 2026-06-23T07:37:56Z – claude:opus:python-pedro:implementer – shell_pid=1326489 – Assigned agent via action command
- 2026-06-23T07:47:20Z – claude:opus:python-pedro:implementer – shell_pid=1326489 – Ready: polymorphic load_meta absorbs 3 contracts + 2 adapters, each pinned with negative controls + BOM fixture. Lane base predates mission tip; rebase conflicts only on stripped planning artifacts (not owned files) so used --force; code commit a29a86112 is self-contained.
- 2026-06-23T07:48:25Z – claude:opus:reviewer-renata:reviewer – shell_pid=1350114 – Started review via action command
- 2026-06-23T07:54:10Z – user – shell_pid=1350114 – Review passed: polymorphic load_meta + 3 adapters reproduce all 3 contracts. (a) default byte-identical to historical (missing->None, content-error->ValueError); only addition is OSError wrapped as ValueError, behavior-neutral since sole exception-handling caller _safe_load_meta catches (ValueError,OSError) identically. (b) strict: FileNotFoundError-on-missing + real BOM-tolerant decode, bom_tolerant=False negative control proves tolerance opt-in. (c) silent: {} on missing AND same-malformed-input that raises under (a); input-identity trap avoided. All 6 branches asserted by observable result, every allow paired with negative control. 17/17 green, ruff+mypy exit 0 no suppressions, |None via value-preserving 'or {}'. Diff scoped to 2 owned files (extra cross-base files are WP01 unmerged lane). Flagged test_feature_metadata failure verified genuinely pre-existing: untouched _read_path_resolver default-raise+'or {}' never caught ValueError pre-WP08; WP09/10/17 sweep target. --force: 'behind' is expected cross-base lane divergence not stale review.
