---
work_package_id: WP18
title: 'C2 sweep cluster 2b: retrospective/review/tracker/upgrade/verify (FR-006c)'
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
- T030
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "1481504"
history:
- Created by sizing-squad re-slice 2026-06-23 (split 2b of WP10's cluster-2 sweep; carries the silent-empty-dict contract sites). Parallel to WP09/WP10 under WP08, disjoint owned_files.
agent_profile: python-pedro
authoritative_surface: src/specify_cli/retrospective/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/retrospective/generator.py
- src/specify_cli/cli/commands/review/__init__.py
- src/specify_cli/tracker/origin.py
- src/specify_cli/upgrade/feature_meta.py
- src/specify_cli/verify_enhanced.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt its
directives/tactics (or `/ad-hoc-profile-load python-pedro`). State which you applied.

## Objective
**FR-006c (cluster 2b)** — convert the **retrospective / review / tracker / upgrade
/ verify** meta-readers to the canonical polymorphic `load_meta` (from WP08),
reproducing each site's current behavior exactly. Behavior-neutral. This WP carries
the **silent-empty-dict** contract sites: `retrospective/generator._load_meta:126`
and `review/__init__._load_meta:382` (map onto `on_malformed=empty, allow_missing=True`).

## Context
- Split of the cluster-2 sweep for context-window fit (sizing squad 2026-06-23):
  WP10 = cli/dashboard/doc; **WP18 (this WP)** = retrospective/review/tracker/upgrade/
  verify (incl. silent-empty-dict). Both parallel under WP08, **disjoint** owned_files.
- EXCLUDE (owned by other lanes): all Lane B files, `acceptance/__init__.py` (E),
  `merge.py`/`lanes/merge.py`/`auto_rebase.py` (F), `task_helpers.py` (D),
  WP09's status/migration/coordination files, and WP10's cli/dashboard/doc files.

## Subtasks
### T030 — Convert cluster-2b sites (retrospective/review/tracker/upgrade/verify)
For each owned file, replace inline `json.loads(meta_path)` / local `_load_meta`
with the canonical `load_meta(dir, allow_missing=…, on_malformed=…)` matching the
current contract. Remove dead local readers. **The silent-empty-dict sites
(`retrospective`, `review`) must stay silent-empty** — map onto
`on_malformed=empty, allow_missing=True`. Add a focused contract test per distinct
(missing, malformed) behavior present in the owned files.

## Campsite (#1970)
Remove dead local readers; hoist S1192; fix lint/type debt on touched lines.

## Test approach (doctrine standard)

> **Test approach (doctrine standard — DIRECTIVE_034/036/041, #2071 CTn).** Assert the **observable contract** — returned value, resolved surface/ref, persisted JSONL/`meta.json`, CLI `--json` payload, or gate verdict — **never** the internal call graph or "collaborator X was invoked" (CT4/D036). Build mission fixtures by delegating to the **production creation seam** (`create_mission_core` / the existing `_stored_topology` helper), not a hand-rolled `meta.json` writer that rots (CT3); use **production-shaped data** — a real 26-char ULID + 8-char mid8, never a short placeholder (testing-principles). Any architectural guard/ratchet anchors keys on `_ratchet_keys.composite_key` (qualname + token-line) or an AST node — **never `file.py:NNN`** — and reuses `audit.py`/`_ratchet_keys.py` (CT1); resolve symbols by AST, never by grepping a string that collides with a surviving flag (NFR-003). Any xfail/skip is a **RED-by-design ATDD pin that names the WP that drains it** and is removed (not re-keyed) when the fix lands — never a defect mask (CT2). Prove behavior-neutrality via the **differential cell over the `(topology × transient)` matrix** PLUS at least one **absolute** assertion (see below) — never a brittle golden count of sites/LOC/refs (CT5); prefer a **tightening ratchet** (count only drops, keyed by symbol-set) over a fixed `== N`. **Pair every "allow / passes / absorbs / ignores-residue" assertion with its negative control** ("still-blocks / still-raises / wrong-topology-differs") — one-sided gate tests let the over-allow mutant survive. When a touched test goes red, classify it (stale→re-point preserving setup / fakeable→delete / valid→fix the product) and establish causation by **code-path coupling, not git-blame** (D041).

### WP18-specific test-DoD
- **Contract test per distinct (missing, malformed) behavior present in the owned file** — NOT one test per module. Assert **both arms' observable RETURN value** (None / raise / `{}`), NOT the `load_meta` call args (CT4).
- **Silent-empty-dict sites assert `== {}` on a MALFORMED file specifically.** For `retrospective` and `review` (the silent-empty contract), the test must assert `== {}` against a **malformed** `meta.json` (the drifting branch), not merely a missing file — the malformed arm is where silent-empty drift hides (paired negative control: a missing file also `== {}`, but the malformed arm is the mutation-killer).

## Definition of Done
- All cluster-2b sites use the canonical reader; duplicates removed; behavior
  unchanged (one contract test per distinct missing/malformed behavior, observable
  return — not call args; silent-empty sites assert `== {}` on a malformed file).
  `ruff`/`mypy` clean; full `tests/` green. Net LOC down.

## Branch Strategy
`feat/single-authority-topology-cleanup`. Lane C (after WP08, parallel to WP09/WP10 —
disjoint files). Worktree from `lanes.json`.

## Reviewer guidance
Verify the silent-empty-dict sites still return `{}` (not raise) on a **malformed**
file. Reject any contract drift.

## Activity Log

- 2026-06-23T07:55:55Z – claude:sonnet:python-pedro:implementer – shell_pid=1366956 – Assigned agent via action command
- 2026-06-23T08:10:30Z – claude:sonnet:python-pedro:implementer – shell_pid=1366956 – Ready: cluster-2b sites on canonical load_meta; silent-empty sites assert =={} on a MALFORMED file
- 2026-06-23T08:11:34Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=1481504 – Started review via action command
- 2026-06-23T08:17:24Z – user – shell_pid=1481504 – Review passed: silent-empty-dict contract verified on malformed fixture for retrospective/generator and review/__init__ (load_meta_or_empty → {} on missing and genuinely malformed {'a':} input); verify_enhanced None-contract preserved (load_meta_or_empty → {} → falsy → None, replacing broad except Exception: pass); tracker/origin.py and upgrade/feature_meta.py independently confirmed already-canonical (no changes needed); 9/9 contract tests green with production-shaped ULIDs and real malformed arm; ruff clean; 2 mypy errors pre-existing in untouched review/__init__ lines (370, 391), confirmed pre-existing on mission branch; WP18 commit scope is exactly 3 owned production files + 1 new test file; rebase conflicted on parallel-lane planning artifacts (not WP18 scope) — using --force.
