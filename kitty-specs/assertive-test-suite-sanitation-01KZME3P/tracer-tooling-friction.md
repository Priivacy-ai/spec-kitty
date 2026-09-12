# Tracer: Tooling Friction

| Date | Surface | Evidence | Resolution/status |
|------|---------|----------|-------------------|
| 2026-08-10 | Fresh full parallel pytest | one worker held `.pytest_cache/spec-kitty-test-venv.lock` during editable install; siblings timed out and cascaded setup errors | filed #3283; manual prewarm enabled raw baseline only; red-first repair planned |
| 2026-08-10 | Collection | whole suite collects 37,444 nodes in 94–110s even for narrow marker discovery | freeze collection baseline; explicit route manifests planned |
| 2026-08-10 | `spec-kitty` CLI | repository scan makes some commands take ~20–60s; help output includes long embedded command docs | commands completed; keep updates visible and avoid duplicate invocation |
| 2026-08-10 | Mutation evidence | CI mutation job is disabled | focused local changed-cluster mutation/fault probes required |
| 2026-08-10 | `setup-plan` commit routing | phase completed but auto-commit returned `no_op_wrong_surface`, citing persisted protected `main` despite current PR planning branch | artifacts preserved; manual feature-branch commit; runtime branch contract still targets PR branch |
| 2026-08-10 | Healthy full baseline | 24 failed, 37,298 passed, 108 skipped, 5 xfailed, 2 errors in 1,689.48s after manual #3283 prewarm | #2782 already tracked; filed #3284 for remaining 23 failures + 2 errors before baseline acceptance |
| 2026-08-10 | WP01 review authority | cycles 1–3 were committed byte-identically on PRIMARY and COORD; cycle-4 submission state was dirty on COORD | removed current PRIMARY copies, retained COORD SSOT, committed pending annotation; independent cycle-4 review still required |
| 2026-08-10 | Runtime cutover | `cutover-guard` required PRIMARY seed evidence while topology-aware cutover writes status seeds to COORD | applied both canonical two-target seam and printed CLI remedy; guard passes; retain surface divergence as campsite tooling defect |
| 2026-08-10 | PRIMARY `.venv` | `pytest` imported as namespace-only and `pip` lacked command modules after an interrupted install | rebuilt all 124 frozen packages with `uv sync --frozen --all-extras --reinstall`; entry points verified |
| 2026-08-10 | Grounding evidence | prior squad PASS claims existed only as prose and analysis next actions still referenced cycle 1 | persisted `grounding-report-2026-08-10.md`; analysis/tracer now state point-in-time scope and current STOP conditions |
