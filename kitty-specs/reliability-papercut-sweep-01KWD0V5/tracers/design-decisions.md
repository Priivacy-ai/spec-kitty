# Tracer: Design Decisions

**Mission**: reliability-papercut-sweep-01KWD0V5
**Seeded**: 2026-06-30 (planning)
**Lifecycle**: seed at planning → append during implement → assess at close (experiment #2095)

One entry per non-trivial design decision: the choice, the alternatives, and why. Capture
decisions made at plan time and any made/revised during implementation.

## Planning-phase decisions (seed)

- **D-01 — `classify_topology` stays pure (BINDING, C-001).** The intuitive fix for #2250
  ("make the topology classifier git-existence-aware") is wrong: `classify_topology` is the
  pure FR-001 SSOT with 8 consumers; a git probe there ripples into `resolution.py` /
  `runtime_bridge` and collides with Lane B. **Decision:** add the git-existence check at the
  *backfill / surface-resolver boundary*, keep the SSOT a pure `(str|None, bool) → Topology`
  mapper. (pre-flight, paula)
- **D-02 — #2139 full reader-collapse via thin adapters, not one public function.** The three
  readers (`get_feature_target_branch` str, `resolve_merge_target_branch` tuple+provenance,
  `resolve_target_branch` BranchResolution) serve different concerns. **Decision:** one shared
  read primitive (field-absent vs read-failed) with the three kept as thin adapters → ~18 call
  sites unchanged (not a bulk rename, C-005). Operator chose full collapse over fail-closed-only.
- **D-03 — #2250 scoped to "lead-with-flatten + stop mis-classifying", not reflog provenance.**
  "Never created" vs "torn down" isn't reliably distinguishable without reflog; don't claim it.
- **D-04 — #2138 fail-closed both sites + flat-path ULID source.** Removing `or mission_slug`
  alone would break flat missions that legitimately carry a ULID via a legacy caller; the flat
  path must source the real ULID (meta or mint) before the fallback is removed. The stale test
  that asserts slug-as-id is inverted, not preserved (a correct sibling already coexists).
- **D-05 — Lane/parent framing.** Parent epic #1878 for both lanes. Cite-don't-fold precedent:
  #2102 (dirty-tree), #1890 (doctor-hint), #2219 (backfill-topology), #2136 (canonical handle),
  #2065 (surface-resolver). #2157 explicitly out of scope (standalone, #1619).

## Implement-phase log (append below)

<!-- decisions made/revised while coding -->

## Close assessment (fill at mission close)

<!-- which decisions held; which were revised under contact with the code -->
