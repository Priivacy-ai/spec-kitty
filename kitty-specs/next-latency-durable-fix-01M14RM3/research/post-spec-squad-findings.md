# Post-spec research squad — convergent evidence

**Point-cut**: post-`specify`, brownfield. **Question**: is the durable projection-cache fix feasible/safe, where does `next` cold-start cost actually live, and what is the correct invalidation key?

**Squad** (profile-loaded, model-disciplined): debugger-debbie (opus, live-evidence profiling), architect-alphonso (opus, seams/blast-radius), python-pedro (sonnet, implementer feasibility/tests). All three forced `PYTHONPATH=src` (the global `spec-kitty` shim resolves the **sibling fork** `/home/stijn/…/fork/spec-kitty`, not this checkout — known footgun; validation/pytest must force `PYTHONPATH=src`).

## Headline: the brief's target is a dead end (3-lens convergence)

`step_projection.project_action_sequence` cumulative time = **0.000s / 4 calls** (cProfile, all three agents). The seam is pure, complexity ≈2-3, **already `@functools.cache`d** at `src/doctrine/missions/mission_step_repository.py:456` (`_resolve_all_for_mission_type_cached`) and `mission_type_repository.py:62,275,453`. Caching it — in-process or on-disk — moves cold-start by ~0ms. **FR-001/FR-002 as originally framed (cache the projection) are re-scoped.** The premise was inherited from `scripts/check_nfr_003_latency.py`'s own docstring ("the cost is command execution, not imports"), which measurement **refutes**.

## The real cost centers (split by context)

**Context 1 — CI clean-install fixture (`tests/fixtures/clean_install_fixture_mission`, ships NO `charter.yaml`): the import floor.**
- In-process phase split (debbie): `import specify_cli` 135ms; `_build_app()` (imports all command modules) **503ms (66%)**; command execution 118ms (16%). `-X importtime` total self-import = **637ms / 1074 modules = 84% of cold-start**.
- cProfile: `pydantic _model_construction.__new__` = **0.418s across 336 model classes** built at import, pulled transitively by `src/specify_cli/cli/commands/next_cmd.py:21-48` top-level imports → `charter`, `spec_kitty_events` (154ms), `doctrine.*.models`, `status.models`.
- `spec-kitty next --help` (zero work) = **0.72s wall** — the pure import/startup floor.
- Pedro's independent chain: `src/doctrine/__init__.py:5` eagerly imports `DoctrineService → AgentProfileRepository → jsonschema → rfc3987_syntax` = **~458ms** on that path.
- **This floor dominates the CI-fixture number that red-blocks PRs, and worsens on a cold runner (fresh .pyc compile, cold FS).**

**Context 2 — real project with a charter (this repo, `next` in-process = 0.885s): charter preflight freshness.**
- `_run_charter_preflight_for_next` (`src/specify_cli/cli/commands/next_cmd.py:523`) → `compute_freshness` (`src/specify_cli/charter_runtime/freshness/computer.py:794`) → `_safe_load_yaml` ruamel-parse of the **1588-line `charter.yaml`** = **0.504s (57%)**. Self-time top-20 is entirely `ruamel/yaml/*`.
- `_run_query_mode` → `query_current_state` → `_canonicalize_primary_read_handle` = 0.193s (22%).
- The fixture short-circuits this (no charter.yaml), which is why the CI number is import-bound, not charter-bound.

**Local reality**: debbie measured **0.752s median locally — already at the 0.745s baseline**. The 1.8s is slow-shared-runner variance + cold-FS. This confirms US2 (remove the blocking wall-clock ceiling) stands on its own.

## Durable fix = two levers (operator chose BOTH)

**Lever A — trim the `next`-path import graph.** Defer eager pydantic doctrine/charter/events model imports (and httpx/rich) not needed on the read-only `kind:"query"` path. Highest-leverage anchor: `next_cmd.py:21-48` top-level imports. Secondary: lazy command registration in `src/specify_cli/__init__.py:161 _build_app` (~43ms only — the cost is `next`'s own dep tree, not sibling command modules).

**Lever B — cache the charter freshness verdict.** Persist `CharterFreshness` to a sidecar keyed on the **already-existing** `compute_bundle_content_hash()` (`src/charter/bundle.py`, per-file mtime-agnostic BOM/CRLF-normalized sha256). On `next`, compute the cheap hash; on a match, **skip the ruamel parse + freshness computation**.
- **Invalidation key MUST fold in the synthesized-DRG graph file** (`_compute_synthesized_drg`, `computer.py:803`) — it is NOT in `BUNDLE_CONTENT_HASH_FILES`, so a bundle-hash-only key could serve a stale `synthesized_drg` sub-state. This is the NFR-002 stale-risk, transplanted to the charter domain.
- **Content hash only — never mtime** (git checkouts don't preserve mtime; DIR-010/011 footgun class). Fail-closed to recompute on any key miss.

## Blast radius / correctness

- **Top risk**: caching the charter freshness verdict could serve a stale **"fresh"** governance verdict — strictly higher-stakes than a stale projection. Mitigated only if the key folds in the DRG graph file. Warrants a pre-merge adversarial review pass.
- Projection consumers do **not** mutate the return in place (`mission_type.py:1493`, `mission_type_profiles.py:1195`, `runtime_bridge_io.py:945`, `mission_type_repository.py:263` each reassign to a fresh local) — no shared-mutable hazard today, but if any memo returns a shared object, verify `project_action_sequence`'s list consumer at `mission_type_repository.py:263`.
- Charter freshness is repo-global (keyed on `repo_root`) → a single sidecar, no per-mission fan-out.

## Tests / benchmark (Pedro + architect)

- **NFR-002 no-stale test**: mutate a charter bundle file (and separately the DRG graph file) between two `next` calls; assert the **served** verdict changes (not just that the sidecar rewrote). Existing in-process cache-clear seams: `MissionStepRepository.cache_clear()` (`mission_step_repository.py:456`), `MissionTypeRepository.cache_clear()`/`.default.cache_clear()`.
- **NFR-004 byte-identical test**: run `spec-kitty next … --json` twice (cold vs warm cache) via subprocess, diff stdout byte-for-byte. Do **NOT** reuse the masked `canonical()` oracle from `tests/runtime/test_bridge_parity.py` — NFR-004 wants literal byte-identity.
- **FR-003 benchmark**: **subprocess-based** (`benchmark.pedantic(subprocess.run([sys.executable,"-m","specify_cli","next",…]), rounds=…, warmup_rounds=…, iterations=1)`) — cold-start = fresh process; in-process `benchmark.pedantic` measures the wrong thing. Exemplar: `tests/review/test_verdict_save_performance.py`. Lands under `tests/specify_cli/next/` (or `tests/runtime/`) → fits `performance.yml:99` next-domain leg, no workflow change. Seed baseline post-fix via `--benchmark-save` (workflow_dispatch `update_baseline`, `performance.yml:67`); `tests/performance/baselines/Linux-CPython-3.11-64bit/` has only `0001_seed.json` today.

## CI-migration half (clean, independently valuable)

- `.github/workflows/ci-quality.yml:4076` — the "NFR-003 latency regression gate" step is a **discrete named step** inside `clean-install-verification`, separate from the structural smoke steps (`:4031` run-next + JSON-shape assert). FR-004/005 = surgical deletion of that one step + `scripts/check_nfr_003_latency.py` (185 lines) + the pinned baseline JSON's absolute ceiling. C-001 smoke stays.
- `.github/workflows/performance.yml:99` — `next` domain leg already exists (`paths: tests/next tests/runtime tests/specify_cli/next`).

## Plan-phase prerequisite (all three flagged)

Run `-X importtime` + `cProfile` (and `check_nfr_003_latency.py`) **on the actual CI runner / cold-wheel path** once, to (a) attribute the runner's absolute floor and (b) settle whether a cold FS inflates the `_inject_projected_fields` step.yaml load slice (`mission_type_repository.py:209`, ~70ms local) enough to matter. Local measurements are warm-FS.
