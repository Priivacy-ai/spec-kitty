# Contracts: Verdict-Seam Boundary Hardening

Interface/behavioral contracts this mission establishes or hardens. These are the invariants downstream code and the architectural gates rely on. (Non-goal: the verdict authority model and read semantics are unchanged — C-001.)

## C-FACADE-1 — `status` is the sole import surface for the verdict bridge
- The full `verdict_vocab` public surface (`artifact_verdicts`, `event_verdicts`, `emission_artifact_verdicts`, `to_event_verdict`, `to_artifact_verdict`, `emission_event_verdict`, `is_changes_requested`, `is_approved`), the `EventVerdict` type alias, and the constants `APPROVED`/`REJECTED`/`CHANGES_REQUESTED` are exported on `specify_cli.status.__all__`.
- `review_result_from_state` (the single reducer-owned `review_result` decode) is exported on `specify_cli.status.__all__`.
- No production module imports a `specify_cli.status.<submodule>` **object** (`verdict_vocab`, `emit`, `store`, `lane_reader`, …). Consumers import façade symbols.
- Documented, permanent exceptions: `status/aggregate.py` (boundary-owner-internal) and `coordination/status_transition.py` / `coordination/transaction.py` (C-004 plumbing exemption in the guard's `_EXEMPT_FILES`).

## C-GUARD-1 — the boundary guard actively forbids submodule-object imports (non-vacuous)
- `tests/architectural/test_status_module_boundary.py` flags `from specify_cli.status import <submodule>` by inspecting `alias.name` on `ImportFrom`, resolving submodule names via a real `status/<name>.py` filesystem check (NOT a bare `startswith`, which would false-flag façade-symbol imports).
- Two-way teeth: a synthetic `import verdict_vocab` MUST be flagged; a legitimate `import is_approved` MUST NOT.

## C-DEDUP-1 — one decode on the merge-blocking path
- `post_merge/review_artifact_consistency.py::_event_sourced_gate_verdict` delegates to `review_result_from_state`; no duplicated inline `ReviewResult.from_dict` decode. Behavior is identical across all 5 decode cases (absent slot / raw-None / non-Mapping / from_dict-raises / valid).

## C-CENSUS-1 — the verdict-seam census sees every reader (direct + helper-constructed)
- Exclusion is function-level (`_EXCLUDED_FUNCTIONS`), not wholesale module-level. `migration/verdict_provenance_backfill.py::_legacy_frontmatter_verdict` surfaces as a reader row; only its write-side helper is excluded by name.
- The classifier recognizes helper-constructed readers keyed on the `review_artifact_override_*` marker, surfacing `migration/backfill_runtime_state.py::_review_from_frontmatter` — and does NOT match the external `--review-result-json` ingress shape.
- Both blind-spot fixes carry dedicated two-way non-vacuity teeth.

## C-ARBITER-1 — arbiter override survives a damaged latest artifact
- `ReviewCycleArtifact.latest_cycle_number()` resolves the highest cycle number from **filenames only** (no body/frontmatter parse), reusing `_cycle_number_or_zero`.
- `persist_arbiter_decision` uses `latest_cycle_number`; a conflict-marked latest `review-cycle-N.md` no longer crashes the override path.
- `.latest`/`from_file` parse contracts are **unchanged** (C-004) — the full-body consumer (`workflow_executor.py:1134`) is unaffected.
- `latest_cycle_number` is a cycle-number loader, not a verdict reader/writer — it contributes no `verdict_seam_census.yaml` row.

## C-ACCEPT-JSON-1 — the SC-008 advisory is machine-visible
- `spec-kitty accept --json` emits a top-level `advisories: list[str]` on all four non-error payloads (diagnose / checklist / not-ok / success); it carries the SC-008 stranded-verdict backfill advisory when stranded, and `[]` when converged. The ~8 error payloads do not carry it.
- The advisory is injected at the CLI emit layer only — the acceptance domain model (`AcceptanceSummary`/`AcceptanceResult`) is untouched (C-005).

## C-STRESS-LANE-1 — heavyweight stress tests are isolated
- A dedicated `stress-tests-serial` CI job selects `-m "stress and not windows_ci" -n0` (POSIX/fork-only), wired into `quality-gate.needs`.
- `test_two_concurrent_distinct_verdicts_are_both_durable` is excluded from the fast pool via the `fast-tests-status` selector negation (`or stress`), without sweeping the 5 genuinely-fast sibling tests out of the pool.
- `pytest.ini` marker documentation matches reality; a `#3235` coordination pointer prevents stranding that P0's repro.
