---
affected_files: []
cycle_number: 1
mission_slug: assertive-test-suite-sanitation-01KZME3P
reproduction_command:
reviewed_at: '2026-08-10T02:06:37Z'
reviewer_agent: reviewer-renata
wp_id: WP01
---

# WP01 review cycle 1 — changes requested

**Issue 1 — census is incomplete and collection-state reconciliation can false-pass.** `audit.py:163-193` walks only module functions and direct `Test*` methods. Recursive AST census finds 29,766 test-like functions and the required 173 docstring-normalized groups / 365 members; the artifact reports 29,755 and 171 / 357 (`foundation-summary.yaml:8,17-18`). Eleven nested test-like functions are omitted, including eight duplicate members. A zero-function `tests/test_empty.py` is also reported as an empty root. `audit.py:453-456` classifies a deselected item as collected because the plugin retained the pre-deselection list. Planted `pytest_collection` and `pytest_collection_modifyitems` crashes returned exit 3 with no error row while reconciliation still said complete/zero-node. Discover all required test-like files/functions, regenerate/version both canonical manifests, classify deselection correctly, and fail closed on unaccounted nonzero collection exits.

**Issue 2 — typed ledger validation accepts invalid and contract-violating rows.** `audit.py:751-846` accepts `members: "abc"`, scalar `source_paths`, mapping `platforms`, observationally divergent families declared equivalent without node rows, arbitrary stale members, and a ledgered `KEEP` without causal proof. Enforce all `data-model.md` types, observed family equivalence, census references, and class/verdict rules including causal proof for every KEEP.

**Issue 3 — workload/aggregate validation is not fail-closed.** `audit.py:590-635` accepts duplicate route IDs, scalar `argv`, and unknown environment references; malformed edge shapes can trigger missing-key access. `audit.py:903-915` crashes with uncaught `AttributeError` for `dispositions: "abc"`. Validate container/field types before iteration, unique routes, environment refs, safe edge shapes, and controlled aggregate failures.

**Issue 4 — frozen command evidence is not exact.** The measured run was `PWHEADLESS=1 .venv/bin/pytest tests/ -n auto --dist loadfile -p no:cacheprovider --durations=200 --ignore=tests/sync/test_orphan_sweep.py`, but `base-full-suite-summary.txt:3` omits the env/options and `base-workloads.yaml:52` omits `--durations=200`. Record the actual invocation/environment verbatim and give sibling E2E a truthful separate lock/install/environment identity.

**Issue 5 — strict typecheck fails.** `.venv/bin/mypy --strict docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/audit.py` fails at `audit.py:264` (`int | None` increment). Fix and retain green evidence.

Positive checks: selftest PASS; base validate PASS; ruff PASS; hashes/content proof match. Dependents must use regenerated foundation.

Anti-patterns: 1 N/A (mission-local standalone); 2 N/A (no permanent FR-tagged tests); 3 PASS; 4 FAIL (adversarial FR paths untested); 5 PASS; 6 FAIL (causal KEEP/stale member/family divergence); 7 PASS; 8 N/A (nonproduction, but malformed inputs still need controlled failure).
