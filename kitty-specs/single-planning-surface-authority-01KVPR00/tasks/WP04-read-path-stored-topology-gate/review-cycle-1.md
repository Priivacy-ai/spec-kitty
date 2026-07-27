---
verdict: approved
reviewer: reviewer-renata
cycle: 1
---

# WP04 Review — Read path consults the STORED topology (structural #2062 read-leg) + differential gate

**Verdict: APPROVED.** Every DoD item confirmed from the diff + live runs, not prose. The two
real risk surfaces flagged in the review brief — (#2) fixture re-shaping and (#5) no-silent-fallback —
were scrutinized against the spec and cleared as legitimate.

## Per-criterion findings

1. **FR-006 — read path consults STORED topology (DoD 1, 1a):** PASS. `_resolve_existing_for_slug`
   gained a keyword-only `topology` parameter. A `SINGLE_BRANCH`/`LANES` stored topology returns
   PRIMARY **before** the `CoordState.MATERIALIZED` arm can fire (`if topology is not None and not
   _topology_routes_through_coord(topology): return primary_candidate ...`). The stale `:262-264`
   comment ("No branch is supplied here…") is removed. The `_declares_coordination_branch` band-aid's
   decision role is retired to the `topology is None` legacy fallback only.

1a. **Topology-as-parameter, pure helper reads no disk (blocking grounding check):** PASS. Topology
   is read ONCE at the `resolve_handle_to_read_path` boundary from the already-in-hand `primary_meta`
   dict via the PURE `stored_topology_from_meta` extractor (no second `meta.json` read). The helper's
   body contains only `Path.exists()` stats — the only `_declares_coordination_branch` reference is
   inside the bypassed `topology is None` legacy branch. The documented no-I/O contract is intact.
   Cross-leg coord-routing authority is reused from WP03's `_topology_uses_coord_surface` (no second
   routing set to drift).

2. **FR-010a pure cell (DoD 2):** PASS. `test_pure_stored_topology_projects_surface_placement`
   feeds `resolve_context_for_mission` for all 4 `MissionTopology` values with a production-shaped
   26-char ULID, zero FS/git fixtures, asserting PRIMARY/`FLATTENED` vs COORDINATION placement. It is
   a SEPARATE `test_*` function added to the owned equivalence file (create_intent stays empty — no
   undeclared new file). Additive, not a replacement.

3. **FR-010b on-disk rows GREEN × 4 handles (DoD 3):** PASS. `_MATRIX` carries
   `flattened-stale-coord` rows for `<slug>-<mid8>`, bare-mid8, full ULID, AND bare-human-slug, all
   `xfail_reason=None`, all GREEN (21 passed). All 3 read legs (read_path, surface_resolver,
   aggregate) asserted PRIMARY. `_assert_equivalent` (the `type(a) is type(b)` + `error_code` gate)
   is UNWEAKENED — the diff did not touch lines 200-228.

4. **Live R1 repro witnessed (DoD 4, NFR-001/C-002):** PASS — re-run independently. A real throwaway
   git repo with `meta.json topology=single_branch` + a stale `-coord` husk resolves PRIMARY on
   read_path + surface + aggregate for ALL 4 handle forms (12/12 PRIMARY). The #2062 verdict is
   correctly scoped NON-TERMINAL/`in-mission` (read leg only); no terminal "#2062 fixed" claim.

5. **Mutation has teeth (DoD 5):** PASS — re-run independently. Neutering the `_read_path_resolver`
   stored-topology early-return (re-inferring from `CoordState.MATERIALIZED`) turns all 4
   flattened-stale-coord rows RED: read_path leg returns the stale `-coord` dir while the surface leg
   returns PRIMARY → legs diverge → C-004 gate fires. Mutation reverted; tree confirmed clean.

6. **C-006 preserved (DoD 6):** PASS. The #1718 create-window and #1848 coord-deleted guards
   (`test_read_path_resolver_transitional`, `test_aggregate_coord_deleted_contract`,
   `test_surface_resolver`) — 28 passed. `probe_coord_state` + branch-signal discrimination survives;
   `CoordinationBranchDeleted` still fires. Pre-existing GREEN matrix rows stay GREEN.

7. **NFR-004 clean (DoD 7):** PASS. `ruff check` clean on all owned files; `mypy` zero issues;
   C901 complexity ≤15 (new helpers are small, single-purpose); no new `# noqa`/`# type: ignore`.
   The `mission_read_path.py` shim is untouched and its re-export forwards unchanged (the resolver
   signature only GAINED a keyword-only param with a default).

8. **Scope respected (DoD 8):** PASS. WP04's commit (`aeb04b537`) touches exactly its owned files
   (`_read_path_resolver.py`, `test_surface_resolution_equivalence.py`) plus a sanctioned boy-scout
   touch to the architectural ratchet (`test_single_mission_surface_resolver.py`). `resolution.py`,
   `cli/commands/agent/mission.py`, `missions/_substantive.py` are NOT in WP04's commit (they appear
   in the cumulative lane diff only as stacked WP01–03 dependency commits). `MissionTopology` /
   `resolve_context_for_mission` are imported from the WP01/WP03 seam, not redefined.

## Adjudication: fixture re-shaping (LEGITIMATE, not a dodge)

The implementer aligned the `flattened-stale-coord` fixture to the canonical R1 shape:
`meta.json topology=single_branch` + `flattened: true` + **NO `coordination_branch`** (the husk
lingers only as an on-disk `.worktrees/<slug>-<mid8>-coord/` dir). I verified this against the spec:

- **quickstart.md R1** shows the exact `{"mission_id": ..., "topology": "single_branch"}` meta with
  no `coordination_branch`.
- **spec.md:61-62**: a mission "had its `coordination_branch` dropped is now `SINGLE_BRANCH`/`LANES`
  with a `flattened` provenance mark; **the residual `-coord` husk is the carved verb's prune
  concern**."
- **spec Primary scenario (spec.md:84-89)**: "A mission flattened mid-flight (its `meta.json`
  topology is now `SINGLE_BRANCH`/`LANES`, with a `flattened` provenance flag) with a stale `-coord`
  worktree still on disk resolves PRIMARY."

The R1 / FR-005 / FR-006 canonical flattened shape is exactly what the fixture models. The
"residual-`coordination_branch`-husk-in-meta" variant is explicitly **carved out** (the prune is the
carved verb's concern, a WP05/aggregate scope), so aligning to R1 is correct spec fidelity, not
narrowing to dodge a failing case. **Legitimate.**

## No-silent-fallback verification (#2065 discipline — PASS)

`_canonicalize_bare_modern_handle` probes the identity resolver (`_canonicalize_handle` →
`resolve_mission`) FIRST. On an ambiguous handle that raises `AmbiguousHandleError`,
`_canonicalize_handle` re-raises `MissionSelectorAmbiguous` — which propagates out of the fold
**before** the bare-modern glob can pick a candidate. Only a genuinely-unresolvable handle (`None`)
falls through to `resolve_bare_modern_mission_dir_name`. The identity-resolver-first ordering is the
exact guard against a numeric-prefix/bare-mid8 handle masking a real ambiguity. Verified live:
`test_handle_equivalence_matrix` (81 passed) exercises this. No silent pick. **No regression.**

## Live evidence + mutation re-run outcomes

- **R1 live repro (re-run by reviewer):** 12/12 legs PRIMARY across {composed, bare-mid8, full-ULID,
  bare-human-slug} × {read_path, surface, aggregate}.
- **Mutation (re-run by reviewer):** disabling the `_read_path_resolver` stored-topology gate →
  4/4 flattened rows RED (read_path leg leaks the stale coord dir). Reverted, tree clean.

## Gates summary

`tests/missions/test_surface_resolution_equivalence.py`: 21 passed. C-006 guards: 28 passed.
Ambiguity matrix: 81 passed. Architectural ratchet + FR-006b tripwire: 18 passed. ruff + mypy clean.
Complexity ≤15. Scope = owned files + sanctioned boy-scout ratchet seed-line drift (composite key
content-anchored on qualname + join token — preserved).

**Lane base note:** lane-e sits on the stale pre-#2081 base, but WP04's owned files are
content-identical at base, so the diff is self-contained. Known pre-existing items
(`test_mission_runtime_surface::test_public_surface_matches_contract` WP01 symbol gap; WP02
`backfill_topology` dead-symbol debt) are NOT WP04 defects and are handled at pre-merge.

Approved with `--force` only across the known-benign lane-base divergence.
