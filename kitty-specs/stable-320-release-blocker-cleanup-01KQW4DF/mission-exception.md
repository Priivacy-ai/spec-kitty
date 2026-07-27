# Mission Exception: SaaS Endpoint E2E

**Operator**: Robert Douglass <robert@local>
**Date**: 2026-05-05
**Failing scenario**: `scenarios/saas_sync_enabled.py::test_full_mission_with_sync`
**Failing assertion**: `scenarios/saas_sync_enabled.py:88` calls `pytest.xfail(...)` when the dev SaaS endpoint reachability preflight is false.

The cross-repo E2E gate reported the SaaS sync scenario as an expected environmental block, not a code defect. The scenario checks `https://spec-kitty-dev.fly.dev/` before running product assertions. From this machine, the endpoint timed out with no bytes received, so the scenario correctly xfailed before attempting SaaS-backed CLI operations.

## Reproduction command

```bash
curl --max-time 10 -fsS https://spec-kitty-dev.fly.dev/
```

Observed result on 2026-05-05:

```text
curl: (28) Operation timed out after 10016 milliseconds with 0 bytes received
```

The full gate command was:

```bash
SPEC_KITTY_REPO=/Users/robert/spec-kitty-dev/spec-kitty-20260505-090055-4etGRd/spec-kitty-post-merge-main-clone SPEC_KITTY_ENABLE_SAAS_SYNC=1 UV_CACHE_DIR=/private/tmp/spec-kitty-e2e-uv-cache uv run --python 3.11 python -m pytest scenarios/ -q
```

## Follow-up

Retry the SaaS sync scenario during the next 3.2.0 release-candidate validation window before tagging stable 3.2.0, after `https://spec-kitty-dev.fly.dev/` is reachable again. The infrastructure dependency is tracked by the existing dev SaaS operational follow-up for endpoint availability; the product-code release blocker remains covered by the other five passing E2E tests in the same gate run.
