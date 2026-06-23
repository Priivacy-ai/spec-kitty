---
work_package_id: WP10
title: 'C2 sweep cluster 2a: cli/dashboard/doc (FR-006c)'
dependencies:
- WP08
requirement_refs:
- FR-006
- NFR-001
- NFR-004
tracker_refs: []
planning_base_branch: feat/single-authority-topology-cleanup
merge_target_branch: feat/single-authority-topology-cleanup
branch_strategy: Planning artifacts for this mission were generated on feat/single-authority-topology-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-authority-topology-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T021
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "1479036"
history:
- Created by /spec-kitty.tasks 2026-06-23
- 'Split into 2a (this WP: cli/dashboard/doc) and 2b (WP18: retrospective/review/ tracker/upgrade/verify, incl. the silent-empty-dict sites) for context-window fit, sizing squad 2026-06-23. Both parallel under WP08, disjoint owned_files.'
agent_profile: python-pedro
authoritative_surface: src/specify_cli/dashboard/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/mission_type.py
- src/specify_cli/bulk_edit/gate.py
- src/specify_cli/dashboard/diagnostics.py
- src/specify_cli/doc_analysis/doc_state.py
- src/specify_cli/merge/baseline.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt its
directives/tactics (or `/ad-hoc-profile-load python-pedro`). State which you applied.

## Objective
**FR-006c (cluster 2a)** — convert the **cli / dashboard / doc** meta-readers to
the canonical polymorphic `load_meta` (from WP08), reproducing each site's current
behavior exactly. Behavior-neutral. The silent-empty-dict sites
(`retrospective/generator`, `review/__init__`) are **WP18's** (cluster 2b) — not
here.

## Context
- Split of the cluster-2 sweep for context-window fit (sizing squad 2026-06-23):
  **WP10 (this WP) = cli/dashboard/doc**; **WP18 = retrospective/review/tracker/
  upgrade/verify** (incl. the silent-empty-dict contract). Both parallel under WP08,
  **disjoint** owned_files.
- EXCLUDE (owned by other lanes): all Lane B files, `acceptance/__init__.py` (E),
  `merge.py`/`lanes/merge.py`/`auto_rebase.py` (F), `task_helpers.py` (D),
  `status/*`/`migration/*`/`commit_router.py`/`task_utils/support.py` (WP09),
  and WP18's 5 files.

## Subtasks
### T021 — Convert cluster-2a sites (cli/dashboard/doc)
For each owned file, replace inline `json.loads(meta_path)` / local `_load_meta`
with the canonical `load_meta(dir, allow_missing=…, on_malformed=…)` matching the
current contract. Remove dead local readers. Add a focused contract test per
distinct (missing, malformed) behavior present in the owned files.

## Campsite (#1970)
Remove dead local readers; hoist S1192; fix lint/type debt on touched lines.

## Test approach (doctrine standard)

> **Test approach (doctrine standard — DIRECTIVE_034/036/041, #2071 CTn).** Assert the **observable contract** — returned value, resolved surface/ref, persisted JSONL/`meta.json`, CLI `--json` payload, or gate verdict — **never** the internal call graph or "collaborator X was invoked" (CT4/D036). Build mission fixtures by delegating to the **production creation seam** (`create_mission_core` / the existing `_stored_topology` helper), not a hand-rolled `meta.json` writer that rots (CT3); use **production-shaped data** — a real 26-char ULID + 8-char mid8, never a short placeholder (testing-principles). Any architectural guard/ratchet anchors keys on `_ratchet_keys.composite_key` (qualname + token-line) or an AST node — **never `file.py:NNN`** — and reuses `audit.py`/`_ratchet_keys.py` (CT1); resolve symbols by AST, never by grepping a string that collides with a surviving flag (NFR-003). Any xfail/skip is a **RED-by-design ATDD pin that names the WP that drains it** and is removed (not re-keyed) when the fix lands — never a defect mask (CT2). Prove behavior-neutrality via the **differential cell over the `(topology × transient)` matrix** PLUS at least one **absolute** assertion (see below) — never a brittle golden count of sites/LOC/refs (CT5); prefer a **tightening ratchet** (count only drops, keyed by symbol-set) over a fixed `== N`. **Pair every "allow / passes / absorbs / ignores-residue" assertion with its negative control** ("still-blocks / still-raises / wrong-topology-differs") — one-sided gate tests let the over-allow mutant survive. When a touched test goes red, classify it (stale→re-point preserving setup / fakeable→delete / valid→fix the product) and establish causation by **code-path coupling, not git-blame** (D041).

### WP10-specific test-DoD
- **Contract test per distinct (missing, malformed) behavior present in the owned file** — NOT one test per module. Assert **both arms' observable RETURN value** (None / raise / `{}`), NOT the `load_meta` call args (CT4). (The silent-empty-dict `== {}`-on-malformed cell is WP18's — those sites are not owned here.)

## Definition of Done
- All cluster-2a sites use the canonical reader; duplicates removed; behavior
  unchanged (one contract test per distinct missing/malformed behavior, observable
  return — not call args). `ruff`/`mypy` clean; full `tests/` green. Net LOC down.

## Branch Strategy
`feat/single-authority-topology-cleanup`. Lane C (after WP08, parallel to WP09/WP18 —
disjoint files). Worktree from `lanes.json`.

## Reviewer guidance
Spot-check 2 sites: the chosen `allow_missing`/`on_malformed` reproduces the exact
pre-change behavior. Reject any contract drift. (The silent-empty-dict sites are
WP18's.)

## Activity Log

- 2026-06-23T07:55:46Z – claude:sonnet:python-pedro:implementer – shell_pid=1366956 – Assigned agent via action command
- 2026-06-23T08:09:24Z – claude:sonnet:python-pedro:implementer – shell_pid=1366956 – Ready: cluster-2a sites on canonical load_meta, contract tests per distinct behavior (silent-empty sites are WP18's)
- 2026-06-23T08:10:50Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=1479036 – Started review via action command
- 2026-06-23T08:16:48Z – user – shell_pid=1479036 – Review passed: contract mappings verified — _read_mission_mid8/_delete_legacy_coordination_branch (on_malformed=none → None→'') and read_documentation_state (allow_missing=False,on_malformed=raise → FileNotFoundError/ValueError) both reproduce prior behavior exactly. bulk_edit/gate, dashboard/diagnostics, merge/baseline confirmed already canonical (no-op scope). 4/4 contract tests green, paired negative controls non-vacuous, ruff+mypy clean, WP10 touches only owned files, no --feature CLI regressions.
