# Post-tasks anti-laziness squad — findings & dispositions

Squad (profile-loaded, opus, read-only): reviewer-renata (fakeable DoDs / contract-vs-impl), planner-priti (decomposition/sequencing). Both grounded findings in the actual code.

## Blockers folded (accepted)

**B1 [HIGH] WP02 cache key omitted a THIRD file (renata).** `_compute_synthesized_drg` (`computer.py:648-669`) reads TWO off-bundle files: `graph.yaml` AND `.kittify/charter/synthesis-manifest.yaml` (`MANIFEST_PATH`). The verdict depends on the manifest (`built_in_only` short-circuit `:655`; `stored_hash = manifest.bundle_content_hash` vs current `:761-767`). A `(charter, graph)` key serves a stale "fresh" verdict when the manifest changes — the exact NFR-002 class we caught for graph but missed for manifest. **Disposition: accepted.** Key is now `sha256(bundle_hash + ":" + graph_hash + ":" + manifest_hash)`; added a manifest-invalidation contract guarantee + test. (contract, data-model, WP02/T006/T009.)

**B2 [HIGH] WP01 import lever can't move real-query cold-start (renata + priti).** A real `next --json` query runs `_run_query_mode → runtime_bridge` (`next_cmd.py:185`), which re-pulls the full foundation (doctrine/charter/events/pydantic/status.models). Deferring imports in `next_cmd.py` helps only `--help`/no-op paths; the residual cost is in `runtime_bridge`'s graph under `src/runtime/next/` (shared-package boundary, outside WP01 scope + arguably outside C-004). **Disposition: operator-decided — keep WP01 as honest hygiene.** WP01 re-scoped to deferring `checkout_ownership` (`next_cmd.py:37`, the movable import; runs only when `owned_checkout is not None`) for no-op/startup paths. NFR-001 reframed: ≥50% is NOT claimed for the CI fixture (import-floor-bound); the real durable win is WP02 (charter projects). T004 asserts a measured footprint delta on the no-op path, not module absence on a real query. The real import-floor reduction (lazy `runtime_bridge`/`DoctrineService`/`status.models`) is deferred to a separate architect-led follow-up.

## Tightenings folded (accepted)

- **WP04 scope too narrow (priti+renata):** widened owned_files to `tests/ci/**` + `scripts/ci/flake_report.py` (live `check_nfr_003_latency` ref at `flake_report.py:78`). T018 made MANDATORY: assert (a) no blocking-set step invokes a wall-clock latency ceiling, (b) the structural smoke step is retained (C-001), (c) `ci_target_median_seconds` is absent from `nfr-003-baseline.json`. T016 DoD = repo-wide `grep -rn check_nfr_003_latency` clean.
- **FR-005 re-credit (priti+renata):** the ceiling is read by exactly one consumer — `check_nfr_003_latency.py` (`:56,146`) — which T016 deletes. FR-005's "ceiling removed" is satisfied by-construction by T016 + the T018 absence-assert; T017 (baseline JSON edit) is provenance hygiene done at consolidation.
- **WP01 anchor corrected (both):** the heavy tree enters transitively via `specify_cli.core.checkout_ownership` (`next_cmd.py:37`), NOT module-scope `charter`/`status.models` imports at `:21-48`. T003 (lazy command registration) is ALREADY implemented (`cli/commands/__init__.py:176 register_commands` `_is_next_fast_path`) → reframed to "verify + regression-test the existing fast-path."
- **WP03 baseline realism (both):** T013 must verify the deferred imports/cache are present in the worktree (run WP01 footprint test green + confirm dep lanes merged) BEFORE `--benchmark-save`, so a pre-fix base fails loudly.
- **WP02 bundle.py hedge dropped (priti):** `_doctrine_graph_path`/`MANIFEST_PATH` already live in `computer.py`; WP02 needs no `src/charter/bundle.py` edit. Parallelism claim (WP01‖WP02) verified TRUE at code level.
- **Anchor drift (renata):** `compute_freshness` is `computer.py:793`; the latency step is `ci-quality.yml:4081`.

## Conceded / not blocking

- NFR-004 is well-protected (masked-`canonical()` ban correct; only `timestamp` per-call). Dependency graph A‖B→C→D is sound (verified, do not re-sequence).
