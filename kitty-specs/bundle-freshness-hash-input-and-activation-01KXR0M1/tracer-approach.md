# Tracer — Approach

## Execution shape

- Driven end-to-end via the **mission-runner** (spec → plan → tasks → implement, adversarial-squad
  gate at every phase), stopping at a draft PR (operator merges).
- **Topology: `single_branch`** on a dedicated mission branch `gk/2758-2759`, itself stacked on
  `fix/2681-synthesized-drg-stale` (PR #2732). Rationale: a cohesive single-slice fix to one
  subsystem — strictly-linear WPs, no lane/coord worktree sprawl, no tmpfs pressure. The mission
  branch is deliberately separate from the #2732 branch so Mission A's PR stays distinct (dependent
  on #2732 landing, per the operator's "stack on #2732 now" decision).
- **Model routing: Sonnet-first**, Opus by exception. Adversarial squad + reviewers ran on Sonnet.

## Adversarial gate cadence (post-spec)

Three distinct lenses (architecture / correctness-testability / root-cause), Sonnet, run
concurrently, then two re-review rounds. The squad did exactly its job — it killed the initial fix
direction with code-verified blockers and handed over the superior Option C. See
`tracer-design-decisions.md`.

## Validation surfaces (targeted, per charter)

- `tests/charter/**` (bundle content-hash, activation/pack-manager, synthesizer/perf envelopes)
- `tests/specify_cli/charter_freshness/**` (the freshness computer/reader)
- Reader-side (`src/specify_cli/charter_runtime/*`) coverage self-policed — it is NOT in the
  CI-enforced `critical_paths` diff-coverage gate (only `src/charter/*` is).
- Pre-push: `pytest tests/architectural/test_no_legacy_terminology.py` + dead-symbol gate.
