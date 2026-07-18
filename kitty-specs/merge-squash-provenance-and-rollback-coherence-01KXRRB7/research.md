# Research — merge-squash-provenance-and-rollback-coherence-01KXRRB7

Pre-spec research squad findings (four lenses) live in [`research/`](./research/):

- [`lens-a-squash-artifact-reconciliation-2709.md`](./research/lens-a-squash-artifact-reconciliation-2709.md) — #2709 clobber site (`lanes/merge.py` `-X theirs`) + reconciliation seam.
- [`lens-b-rollback-resume-coherence-2711.md`](./research/lens-b-rollback-resume-coherence-2711.md) — #2711 structural root cause (non-transactional rollback/resume).
- [`lens-c-shared-root-cause-boundary.md`](./research/lens-c-shared-root-cause-boundary.md) — shared-root verdict + scope boundary.
- [`lens-d-red-first-repro-design.md`](./research/lens-d-red-first-repro-design.md) — red-first ATDD repro design.

Post-spec, post-plan, seam-fit, and post-tasks adversarial-squad findings are folded into
[`spec.md`](./spec.md) and [`plan.md`](./plan.md) (see their "Squad Findings" sections).

**Root cause (both):** the merge core wrote to the committed target/coord branch without
reconciling against the durable event-log authority. Two distinct fix surfaces, no shared
call path — #2709 (happy-path `-X theirs` content loss) and #2711 (failure-path
non-transactional rollback/resume). Fixes: per-artifact-class squash reconciliation (#2709)
and Option A coord-`done`-revert + durable-log resume (#2711).
