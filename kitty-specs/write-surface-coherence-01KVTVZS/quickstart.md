# Quickstart: Verify Write-Surface Coherence

How to confirm the placement bifurcation works (the behavioral, two-ref check).

## The split being fixed (red, pre-mission)

A coord-topology mission's `spec-commit` lands the spec on the coordination branch
while `finalize-tasks` reads primary → "all requirements unmapped". Reproduced
live during planning (mission's own spec landed on
`kitty/mission-write-surface-coherence-01KVTVZS`, not the feature branch).

## After the mission (green)

1. Create a coord-topology mission on a feature branch.
2. Run specify → plan → tasks. Each planning-artifact commit lands on the **primary
   `target_branch`**:
   ```bash
   git log <target_branch> -- kitty-specs/<mission>/spec.md   # present
   git log <coordination_branch> -- kitty-specs/<mission>/spec.md  # absent
   ```
3. A status transition still lands on the **coordination branch**:
   ```bash
   git log <coordination_branch> -- kitty-specs/<mission>/status.events.jsonl  # present
   ```
4. `finalize-tasks --validate-only` reports **100% of requirements mapped** — no
   manual coordination-worktree step.

## The behavioral guard (NFR-002)

For a coord-topology fixture, assert both refs from the same mission:

```python
planning_target = resolve_placement(mission, ArtifactClass.PLANNING)
status_target   = resolve_placement(mission, ArtifactClass.STATUS)
assert planning_target.ref == mission.target_branch          # primary
assert status_target.ref   == mission.coordination_branch    # coord
```

This kills both the "always coord" and "always primary" mutants — a structural
"resolved in one function" count would pass vacuously and is explicitly rejected.

## Flattened regression (NFR-001)

For a flattened/single-branch mission, both planning and status resolve to
`target_branch` — identical to pre-mission behavior. Existing flattened-mission
planning tests must stay green.

## Protected-primary refusal (FR-008)

A coord-topology mission whose `target_branch` is `main`/`master` must refuse a
planning commit with guidance to start a feature branch (no coord transit).
