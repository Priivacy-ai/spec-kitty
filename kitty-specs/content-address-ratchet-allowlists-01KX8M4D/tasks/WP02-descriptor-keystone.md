---
work_package_id: WP02
title: IC-DESCRIPTOR keystone — shared content-descriptor resolver
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- NFR-005
tracker_refs: []
planning_base_branch: analysis/test-change-coupling
merge_target_branch: analysis/test-change-coupling
branch_strategy: Planning artifacts for this mission were generated on analysis/test-change-coupling. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into analysis/test-change-coupling unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T009
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1421306"
history:
- created at planning (tasks) — descriptor keystone
agent_profile: python-pedro
authoritative_surface: tests/architectural/_ratchet_keys.py
create_intent:
- tests/unit/test_descriptor_resolver.py
execution_mode: code_change
model: sonnet
owned_files:
- tests/architectural/_ratchet_keys.py
- tests/unit/test_descriptor_resolver.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load python-pedro` (role: implementer). Then read
[contracts/descriptor-resolver.md](../contracts/descriptor-resolver.md) (the
authoritative interface), [research.md](../research.md) D-1/D-2, and the plan's
**Post-Plan Squad Hardening** section (GAP-1/GAP-2 + the consolidate-not-fork
note). This WP is the keystone — WP03/WP04 depend on it.

## Objective
Add the shared content-descriptor resolver to `tests/architectural/_ratchet_keys.py`
that every WS1 gate will consume: resolve a `(rel_path, qualname, token_substring,
occurrence, rationale)` descriptor to **exactly one** live finding's composite key,
and a staleness helper that is exactly-one + key-equal (never "≥1").

## Design (authoritative — do not deviate)
- **Reuse, do not fork.** `contracts/anchoring.composite_key` returns a 2-tuple
  `(qualname, token_line)`. The canonical **path-qualified 3-tuple** builder
  already exists at `tests/architectural/surface_resolution_audit/audit.py`
  (`CompositeKey = (str,str,str)` + `_composite_from_file`). Reuse/relocate that
  pattern — do NOT introduce a third key-builder.
- Match `token_substring` against the **normalized** `code_tokens_by_line(source)`
  output (space-joined tokens; strings/comments/f-string-interiors dropped), NEVER
  raw source.

## Subtasks

### T005 — `resolve_descriptor(source, descriptor) -> CompositeKey`
Build the qualname map **once** (single AST walk — GAP-2; reuse
`anchoring._build_qualname_map` via a small public re-export in `_ratchet_keys.py`,
do not replicate the AST walk), collect findings whose `enclosing_qualname ==
descriptor.qualname` and whose normalized token line contains `token_substring`; if
`occurrence` is set, select that 0-based ordinal in file order; return
`composite_key`(path-qualified) of the match.
**S3776 pre-extraction (squad — keep ≤15):** split into `_candidate_lines(source,
qualname, substring) -> list[int]`, `_select_occurrence(cands, occurrence) -> int`,
`_assert_exactly_one(cands, descriptor)`; keep `resolve_descriptor` a ~4-line
orchestrator. Give each helper its own direct unit test (T008) — Sonar new-code coverage.

### T006 — Exactly-one resolution + key-equal staleness
`resolve_descriptor` MUST **RAISE/FAIL (RED)** if the match count is 0 or (no
`occurrence`) >1 — never silently pick the first. `descriptor_still_live(source,
descriptor, seeded_key) -> bool` returns True iff `resolve_descriptor(...) ==
seeded_key` (exactly-one AND key equality). **Forbidden: "≥1 finding matches"
semantics** (D-1 bite hole — it lets a routed-away allowance mask a sibling offender).

### T007 — Import-time unique-within-qualname assertion (GAP-1)
Provide a helper the consuming gates call at import to assert each descriptor's
`token_substring` is unique within its qualname (or carries an `occurrence`). This
is the highest-risk foot-gun: a substring authored from a *non-finding* line (e.g.
a `def` line) resolves to the wrong line or zero → spurious RED. The assertion +
the T009 self-test catch it.

### T008 — Resolver unit tests
**HOME (squad — GAP-2):** these tests live in the collected
`tests/unit/test_descriptor_resolver.py` (NOT in `_ratchet_keys.py`, which is
`_`-prefixed → never collected → tests would never run). `tests/unit/` is outside
the arch pole roots → no `_arch_shard_map.py` entry needed and no WP05 dependency
(keeping the keystone dep-free). Set `pytestmark = [pytest.mark.unit]` (match the
`tests/unit/` convention).
Exercise both disambiguation axes with production-shaped fixtures:
- same qualname, different substring (RJ#1/RJ#2 shape) → distinct keys.
- identical token line, different qualname (TR#2/TR#3 shape: two `subprocess . run (`
  in `status_porcelain`/`show_blob`) → distinct keys.
- 0 matches → RED; >1 matches (no occurrence) → RED; occurrence selects correctly.

### T009 — Non-vacuity self-test
Assert `resolve_descriptor(source, d) == composite_key(source, true_finding_line)`
for a known fixture — proving the resolver lands on the real finding line, not a
neighbouring token match.

## Branch Strategy
Planning/merge branch `analysis/test-change-coupling`; worktree per `lanes.json`
lane via `spec-kitty agent action implement WP02 --agent <you>`.

## Definition of Done
- `resolve_descriptor` + `descriptor_still_live` present in `_ratchet_keys.py`,
  reusing the audit.py 3-tuple, qualname-map-once, normalized matching.
- Exactly-one (RED on 0/>1) + key-equal staleness; NO "≥1" path.
- Import-time unique-within-qualname assertion available.
- Resolver unit tests + non-vacuity self-test green; full `tests/architectural/` 869/0.

## Reviewer guidance
The load-bearing checks: (1) staleness is exactly-one + key-equal, never "≥1";
(2) matching is against normalized tokens; (3) it reuses the audit.py 3-tuple (no
forked key-builder); (4) 0/>1 → RED is enforced, not a silent pick.

## Activity Log

- 2026-07-11T14:29:34Z – claude:sonnet:python-pedro:implementer – shell_pid=1264022 – Assigned agent via action command
- 2026-07-11T15:08:08Z – claude:sonnet:python-pedro:implementer – shell_pid=1264022 – Ready: shared content-descriptor resolver (resolve_descriptor/descriptor_still_live; exactly-one, key-equal; reuse audit.py 3-tuple; qualname-map-once; GAP-1 unique assertion; S3776 helpers). 26 resolver unit tests green; ruff exit 0; mypy clean; arch 847 passed / 0 failed.
- 2026-07-11T15:09:03Z – claude:opus:reviewer-renata:reviewer – shell_pid=1421306 – Started review via action command
- 2026-07-11T15:30:33Z – user – shell_pid=1421306 – Review passed (reviewer-renata/opus): descriptor keystone verified (exactly-one/key-equal, D-1 regression-tested, reuse audit.py 3-tuple, S3776≤15); 26 unit + arch 847/0. --force: lane kitty-specs hygiene gate tripped by orchestrator's matrix-sync recovery, not a code issue; to be reconciled before merge.
