# Contract: `spec-kitty review` mode resolution

**WP**: WP03 | **FRs**: FR-005, FR-006, FR-023 | **Diagnostic codes**: `MISSION_REVIEW_MODE_MISMATCH`

## Inputs

- `meta.json.baseline_merge_commit: str | None` — present iff the mission has been merged via `spec-kitty merge`.
- CLI argument `--mode {lightweight | post-merge}` (optional).

## Resolution rule (precedence order)

1. **CLI flag override.** If `--mode <m>` is present on the command line, the mode is `<m>`.
2. **Auto-detect: post-merge.** Else, if `meta.json.baseline_merge_commit` is set, the mode is `POST_MERGE`.
3. **Auto-detect: lightweight.** Else, the mode is `LIGHTWEIGHT`.

## Mode-mismatch detection

When step 1 sets mode to `POST_MERGE` and step 2's signal is absent (`baseline_merge_commit` not in `meta.json`), the command exits non-zero with `MISSION_REVIEW_MODE_MISMATCH`. The diagnostic body MUST contain:

1. A "What this means" paragraph naming the missing signal.
2. Three remediation options (run `spec-kitty merge`, re-run with `--mode lightweight`, or run identity backfill for pre-083 missions).

The reverse case (`--mode lightweight` with `baseline_merge_commit` present) is **not** a mismatch — operators may legitimately want a quick consistency check on an already-merged mission.

## Output

- Stdout (JSON): `{"mode": "lightweight" | "post-merge", "auto_detected": bool, "baseline_merge_commit": "<sha>" | null}`
- Persisted in `mission-review-report.md` frontmatter under the `mode` key.

## Acceptance fixtures

- Pre-merge mission, bare `spec-kitty review`: mode is `lightweight`, exits 0.
- Pre-merge mission, `--mode post-merge`: mode-mismatch diagnostic; exits non-zero.
- Post-merge mission, bare invocation: mode is `post-merge`; required artifacts validated.
- Post-merge mission, `--mode lightweight`: mode is `lightweight`; report explicitly says so; exits 0.

## Invariants

- The mode is recorded in the report; consumers downstream (cross-surface harness #992 Phase 0, dashboard) must read mode from the report, not infer it.
- The auto-detect default never changes within a release minor without a deprecation cycle.
