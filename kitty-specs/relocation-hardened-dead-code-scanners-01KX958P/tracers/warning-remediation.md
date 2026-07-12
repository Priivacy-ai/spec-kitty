# Tracer: Warning Remediation

**Concern**: IC-WARNINGS (FR-016 / NFR-006 / SC-005) — census + root-remediate the ~40
arch/integration-suite warnings.

**Seed facts (census done, `analysis/test-change-coupling`):**
- 40 warnings, near-all intentional `warnings.warn(UserWarning)` report-only diagnostics.
- In-mission/owned (arch): `test_migration_chain_integrity.py` (~13 patch-skips),
  `test_gate_coverage.py` (duplicate-selection), template-governance / charter-references
  / wp-prompt-latency emitters.
- Tracked-follow-up candidates (cross-package/src): `tests/contract/test_example_round_trip.py`
  (~13 legacy-contract backfill), `src/doctrine/base.py:108` (invalid toolguide YAML skip).

**Seed hypotheses (planning):**
- Preserve the signal, change the channel (record_property/log) OR register expected-with-rationale.
- NO blanket `filterwarnings=ignore`; narrow justified third-party filters only.
- The src schema-skip (`terminology-guard.toolguide.yaml` pydantic `extra_forbidden` on
  `references`) is a genuine data/schema defect — fix the YAML/schema OR file it.

**Append during implement:** (final channel choice; which emitters converted vs
registered; the toolguide YAML root cause; which warnings split to follow-ups + their #s)

**Assess at close:** 0 first-party warnings on re-census? Any load-bearing signal lost?
Follow-up issues filed for the cross-package residuals?
