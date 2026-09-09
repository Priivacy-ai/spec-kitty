# Quickstart — reinstated CI

## What runs when
- **Open a PR touching `src/**`** → router selects the affected module shards + fast always-on gates
  (terminology/layer-rule); heavy arch battery only if code-scoped groups match. **PR mode = fail-fast**:
  a red predecessor short-circuits its dependents (fewer jobs run; a skipped successor is NOT a pass).
- **Docs-only / packs-only PR** → 0 code shards; only docs checks / the packs workflow + fast always-on gates.
- **Nightly (schedule) or "Run workflow" → run full** → **full mode**: every job runs regardless of
  failures (full-spectrum signal), incl. performance/e2e + the above-3.12 interpreter lane + Sonar.
- **Any workflow** → manually dispatchable from the Actions tab (`workflow_dispatch`).

## Local pre-PR parity
- `make test-fast` — the fast tier (unchanged baseline).
- Use the single **gate-selection authority** (E5/#2476) to preview which shards/gates your diff selects
  before pushing — the same authority CI uses, so "green locally / red on CI" drift is closed.
- `spec-kitty regen --check`, `ruff check .`, `ruff format --check` — the shift-left front, run locally first.

## Interpreting a run
- **Green PR** ⇒ every enumerated must-run gate executed (its own job is green) and no test was
  zero-gated (integrity oracle) and no dead-code test was in the run/denominator (census).
- **A skipped job in PR mode** ⇒ its predecessor red; fix the predecessor. It is NOT mergeable-green.
- **Nightly red** ⇒ the full failure set is present (no early abort); plan one remediation pass.

## Warmup / dependencies
- PR builds resolve a **pinned `spec_kitty_events` rev** (deterministic, cache-hit); nightly resolves
  **latest mainline** (upstream-drift signal). The warmup composite builds the env once; shards reuse it.

## Adding/retiring a workflow (governance)
- Net-new workflow → add an `introduced` row to `docs/convergence/interim-ci-producer.md` **and**
  `tests/release/test_release_ci_ownership.py` in the same change, or the ownership test reds.
- Stock runners only; never `SK_CI_TOKEN` on a public job.
