# Phase 0 Research — Single-Authority Topology Cleanup & Dedup

All four unknowns were resolved by a live code probe during planning (the design
was pre-decided by spec.md + the post-spec consistency squad). No open
`[NEEDS CLARIFICATION]`.

## R1 — FR-013 conditional gate: does FR-001's `.kind` removal touch `CommitResult`?
- **Decision**: NO — `CommitResult` is **disjoint** from the `.kind` work → FR-013 is a standalone lane (IC-08), not folded into IC-02.
- **Rationale**: `CommitResult` (`src/specify_cli/git/commit_helpers.py:422`) is a frozen dataclass `{sha: str, destination_ref: str, worktree_root: Path}` — it has **no `.kind` field and no `CommitTargetKind` reference** (probe: `"kind" in body == False`, `"CommitTargetKind" in body == False`). The #1891 `is not JSON serializable` failure is the un-serializable `Path` field (`worktree_root`), unrelated to the enum eradication.
- **Alternatives considered**: folding FR-013 into the FR-001 anchor WP (rejected — the probe proved no coupling; folding would create a false dependency and bloat the anchor lane). Carving FR-013 to a separate follow-up ticket (rejected — the fix is ~one method on a dataclass, already in the issue-matrix + assigned; a separate ticket defers a trivial bugfix for no benefit).

## R2 — FR-005 vs C-002: are the 6 predicates disjoint from the genuine-fallback relays?
- **Decision**: YES, disjoint — FR-005 consolidates only the **projection predicates**; the C-002 relays are KEPT untouched.
- **Rationale**: the six predicates (`destination_kind_for_topology`, `_topology_uses_coord_surface`, `_topology_routes_through_coord`, `_mission_routes_through_coordination`, `_read_contract_routes_through_coordination`, `routes_through_coordination`) are pure `topology → bool` projections. The three relays (`status_transition.py:599`, `surface_resolver.py:562`, `resolution.py:765`) read **stored topology first** and call `classify_topology` only on the `except` arm (un-backfilled-legacy fallback). A relay is an exception-arm meta-read, structurally opposite to a projection. (alphonso verified all three relays directly.)
- **Alternatives considered**: collapsing relays into the consolidated predicate (rejected — would delete the migration fallback contract, C-002).

## R3 — FR-004 boundary: absent-field vs corrupt-meta
- **Decision**: collapse only the **absent-field** `topology is None` arms; KEEP the corrupt/unreadable-meta typed fallback (C-004).
- **Rationale**: the meta reader returns `None` for a *missing* `topology` field (→ `classify_from_meta` can classify from `coordination_branch` + lanes) but **raises** for *malformed* JSON (→ cannot classify without readable meta). The two are different return paths, so the collapse cannot accidentally delete the corrupt-meta fallback. `read_topology` (`backfill_topology.py:68`) already absorbs `None` by deriving a concrete topology; the husk-arms it makes dead are the absent-field ones.
- **Alternatives considered**: collapsing all `topology is None` arms including the malformed path (rejected — un-classifiable meta has no shape to derive; C-004).

## R4 — IC-04 ownership strategy (the C2 sweep's collision risk)
- **Decision**: linearize the broad C2 `meta.json`-reader sweep **after** the smaller disjoint lanes (IC-06 accept, IC-07 merge, IC-08 #1891), OR scope per-subdirectory WPs with disjoint `owned_files`; `finalize-tasks --validate-only` must pass.
- **Rationale**: FR-006 touches ≥66 named call sites + ~107 inline reads across ~20 wrappers — including `tasks.py` and `mission.py`, which IC-06/IC-08 also touch. Parallel WPs with overlapping `owned_files` would fail finalize validation. The C2 lane is the biggest LOC reducer (~300+) and the most ownership-sensitive.
- **Alternatives considered**: one monolithic C2 WP (rejected — exceeds the 10-subtask ceiling and would own half the CLI surface, colliding with every other lane). A single global `load_meta` rename in one pass (rejected — too large to review; tasks will split by subdirectory).

## Sizing note (carried into FR-006/NFR-004; brownfield-corrected)
The original ~45 `load_meta` estimate is low (squad-verified: **66 named + ~71 inline** `json.loads(meta_path)`; the earlier ~107 inline figure was ~1.5× high — corrected by the post-plan brownfield pass). The meta-reader has **3 distinct error contracts** (None-on-missing+raise-on-malformed; raise-on-missing+utf-8-sig; silent-empty-dict), not 2 adapters. NFR-004's ~750–1,000 LOC band remains a realistic **floor** (C6 ~400 + C2 ~250–300 + enum/predicate ~200); realized reduction reported per-cluster in the PR body.
