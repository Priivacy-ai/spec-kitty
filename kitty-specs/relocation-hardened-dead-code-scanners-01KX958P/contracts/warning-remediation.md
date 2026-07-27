# Contract: Warning Remediation (FR-016 / NFR-006 / SC-005)

## Census (done — `analysis/test-change-coupling`, full `tests/architectural/`)

40 warnings; near-all intentional `warnings.warn(UserWarning)` report-only diagnostics:

| Source | ~count | Class | Disposition |
|--------|--------|-------|-------------|
| `tests/architectural/test_migration_chain_integrity.py` | ~13 | patch-skip "may warrant verification" | **in-mission (owned)** |
| `tests/architectural/test_gate_coverage.py` | 1 | 804 tests selected by ≥2 CI gates (report-only) | **in-mission (owned)** |
| `tests/architectural/test_template_governance_payload_contract.py` | a few | governance payload | **in-mission (owned)** |
| `tests/architectural/test_charter_references_resolve.py`, `test_wp_prompt_build_latency.py` | a few | report-only | **in-mission (owned)** |
| `tests/contract/test_example_round_trip.py:514` | ~13 | legacy-contract `# pydantic_model:` backfill | **tracked follow-up** (cross-package) |
| `src/doctrine/base.py:108` | 1 | invalid `terminology-guard.toolguide.yaml` skipped (pydantic `extra_forbidden` on `references`) | **tracked follow-up OR scoped fix** (src-side) |

## Remediation rule (binding)

1. **Preserve the signal, change the channel.** The patch-skip / duplicate-gate /
   legacy-backfill diagnostics are load-bearing. Route them off the `warnings` channel
   (pytest `record_property`, captured log, or a report line) OR register an
   expected-warning with an inline rationale. Do NOT delete the diagnostic.
2. **NO blanket `filterwarnings = ignore`.** A narrowly-scoped, individually-justified
   `@pytest.mark.filterwarnings` (or `filterwarnings` ini entry) is permitted ONLY for a
   third-party warning we cannot fix at source, each carrying an inline rationale.
3. **Scope boundary.** Arch-side emitters (`tests/architectural/*`) are in-mission and
   owned. `tests/contract/test_example_round_trip.py` (legacy-backfill) and
   `src/doctrine/base.py` + the invalid toolguide YAML are cross-package/src-side:
   remediate in-mission ONLY if within a declared owned surface; else **split to a
   tracked follow-up named in `issue-matrix.md`** — never silently suppressed.

## Acceptance (SC-005 / NFR-006)

- Re-run the census (`pytest tests/architectural/ -W default -r w`): **0 first-party
  warnings** from the arch suite.
- Any residual is a documented, individually-justified third-party `filterwarnings`
  entry OR a tracked `src/`/contract follow-up in `issue-matrix.md` — verifiable by
  re-running the census.
