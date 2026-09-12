# WP01 source verification

Source head: `6136d4ce8`. Initial real CLI regression was committed red at `f555dcb9f`: the old command rejected `--owned-checkout`. Root-approved ownership extension adds the small charter-only `activation/checkout_scope.py` leaf. It uses the existing Git topology and checkout ownership classifier; default canonical identity helpers are unchanged. The curator reviewed the explicit context-scope design before implementation. A type-only Typer cast makes the touched decorator checkable under strict mypy; no runtime behavior changes there.

Verification in the runtime-owned lane:

- New and existing charter creation/rendering CLI suites: 40 passed in 39.92 seconds.
- Complete owning charter subsystem: 2,850 passed, 22 skipped in 417.77 seconds.
- Required `make test-fast`: 1,787 passed, 5 skipped in 398.47 seconds. Reused the prewarmed all-extras environment with `UV_PROJECT_ENVIRONMENT` and `UV_NO_SYNC=1`; the first attempt used a fresh lane environment missing pytestarch and failed during collection. The failed setup was not treated as a passing test run.
- Final new scope/CLI regression: 15 passed in 19.85 seconds; new checkout_scope.py coverage 100% (25 statements).
- Strict mypy across all four changed production modules: passed. Whole configured Ruff lint and format checks: passed. Unrelated legacy doctrine formatting was restored to keep the change focused.

Installed CLI3.2.7's default GateCoverageScopeSource selected an unbounded scope and timed out after300 seconds. A first supported DeclaredCommandScopeSource attempt covering the whole charter suite also exceeded that ceiling. Both genuine failed baseline receipts are retained alongside the final baseline; neither is called a clean baseline. The underlying timeout issue is reported on upstream issue3046.

For comparable review evidence, temporary local `.kittify/config.yaml` review settings use the supported `review.test_command`, `test_output_format: junit_xml` and enabled regression gate. The same command at baseline/head covers sync, sync-paths, context authority, include activation, service seams, existing charter rendering and discovered charter/doctrine CLI suites. Real baseline at `afb25560fe7ca1009eeee713a775cea591601830` completed with zero failures and `DeclaredCommandScopeSource/junit_xml`. The CLI serializes failure counts rather than total test counts in this receipt; zero total there is not a claim that no tests ran. Broader subsystem and mandatory baseline evidence is recorded above separately.

Temporary review settings are local execution configuration, not shipped product changes. Original sections are preserved in workspace `cli-review-config-original.json` and must be restored after both child WPs' review gates. No installed CLI source, gate implementation, failure result or regression-block setting was patched. Independent review and full Factory/installed CLI consumption remain separate gates.
