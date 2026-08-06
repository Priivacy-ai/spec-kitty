# Quickstart — Verdict-Seam Write-Side Unification

How to run the gates that define "done" for each concern. All targeted (charter: run affected
packages, not the full suite). Parallel locally: `-n auto --dist loadfile`; real-port/daemon `-n0`.

## Per-concern gate commands

```bash
# IC-01 — census predicate hardening (.from_dict), lands first
pytest tests/architectural/test_verdict_seam_census.py -q

# IC-02 — backfill + durability (event authority populated)
pytest tests/status/test_reducer.py tests/review/test_cycle.py -q
PWHEADLESS=1 pytest tests/integration/test_review_durability_matrix.py -n0 -q   # 50×2 processes, serial

# IC-03 — reader collapse (safety-critical; run after IC-02)
pytest tests/architectural/test_2093_authority_invariant.py \
       tests/specify_cli/cli/commands/agent/test_tasks_parsing_validation.py \
       tests/review/ -q

# IC-04 — write-partition flip (non-safety-critical prose relocation)
pytest tests/coordination/test_analysis_report_rehome.py \
       tests/architectural/test_verdict_seam_census.py -q

# IC-05 — arbiter root threading
pytest tests/review/ -k arbiter -q

# IC-06 — gate artifacts (#2804/#2404), parallel lane
pytest tests/regression/test_issue_2804_merge_resets_gate_artifacts.py -q

# Cross-cutting, before push (charter):
pytest tests/architectural/test_no_legacy_terminology.py -q
ruff check . && mypy --strict src/specify_cli/review src/specify_cli/status
```

## The two carry-red pins (already red — green them, don't rewrite)

```bash
pytest tests/regression/test_issue_2804_merge_resets_gate_artifacts.py -q   # IC-06 greens this
# (#3086's pin test_issue_3086_* is OUT OF SCOPE — parallel session)
```

## Safe-order smoke (the load-bearing sequence)

1. IC-01 green (census can see `.from_dict` readers).
2. IC-02 green + provenance gate reports **zero** stranded WPs.
3. IC-03 green (every reader on the snapshot; SC-002/SC-004).
4. IC-04 green (`.md` on COORD, no verdict field; SC-001/SC-007).
5. IC-06 green in parallel (SC-005).

If IC-03 is attempted before IC-02's gate is clean, the provenance gate **blocks** it — that is the
designed safety interlock (SC-008).
