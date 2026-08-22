# Tracer: Design Decisions

- **Draft mechanism = net-new canceller** (operator choice) over adopting the existing skip-subset model — literal fail-fast semantics; canceller is non-gating/allowlisted.
- **Full signal = full *relevant* signal** (operator steer): preserve path-filtering; untouched domains stay un-triggered.
- **False-red formula pinned**: (perf_timing_flake+infra_flake)/(…+real); needs_review excluded, reported separately.
- **Half-open completion-time cursor + in-progress low-water mark**: avoids straddle-skip and re-run double-count.
- **Golden fixture** makes NFR-003 reproducible past gh's ~90-day retention.
- **Gate reads needs.<job>.result**, no continue-on-error on gating jobs (anti false-green).

## Decisions during implement
- (append)

## Post-tasks squad resolution
- WP02 owns a SEPARATE `flake_report_cli.py` (imports WP01 core) — no editing WP01's file.
- Golden fixture MUST include `logs/` (classifier inputs are log text).
- WP05 red-first uses pytest `--ff` single-pass (seed lastfailed cache; drop `-p no:cacheprovider`) — no double-run; it's a STEP in an existing job (no new gate context).
- WP04 T015 is an AUDIT: `quality_gate_decision.py` already reads job `.result`. `needs.<job>.result` only inside the decision run-step/payload, NEVER a job-level `if:` (`test_ci_quality_path_filters.py` guard).
- No pyproject version bump (no `__init__.py` touched); tests/ci already collected + importable.
