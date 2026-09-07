# PR 3888 adversarial review and remediation

Date: 2026-09-06
Point-cut: pre-merge
Question: Does this PR enforce the governance/SSOT/runtime boundary and fully resolve #3522?
Reviewed head: a86907a52d20c1a76cad5738101d9eefedf4def1
Base: e7217637594bda83e4db8f8e8b4bf19e61bf6579

## Independent lenses

- Architect Alphonso: modularity SSOT, runtime ledger, import syntax, baseline growth.
- Debugger Debbie: executable mutation checks for both doctrine scan roots and #3522's original regression.
- Reviewer Renata: ADR truth, ownership retirement, live references, scope fidelity.

All reviewers invoked the profile resolver and charter-context CLI, applied the resolved applicable policies, and read the local charter. Charter resolution reported unavailable selected directives and/or sibling-root context; this is a limitation of the governance bootstrap, not evidence of complete structured charter resolution. The legacy profile command worked for the reviewers; `profiles show` is the currently advertised CLI surface.

## Confirmed findings and Ops

| Finding | Evidence | Remediation Op |
| --- | --- | --- |
| CI formatting failure in two changed tests | CI Lint job and local Ruff format check both rejected the files | 01M1V10K60TK4H24JCB782BY8M |
| Deleted ownership manifest leaves a live broken ADR link; implementation mapping still calls the demoted map authoritative | Base/head comparison over 2,882 Markdown links; direct source inspection | 01M1V18DDE2PX1T7JAN8YMWS1Z |
| Root-form specify_cli imports bypass the ledger; ledger growth lacks an independent ratchet | In-memory imports of cli/saas_client passed; adding a new ledger entry plus its import passed | 01M1V19GZXZ7BQME84DE612525 |
| Whole-file doctrine exceptions allow the original #3522 regression | Replacing the charter.drg facade import with charter.offering.drg.org_pack_config in runtime_bridge_composition passed all 17 existing gate functions | 01M1V1A3686C32GJ0NJ884TTR6 |
| Module-level conditional doctrine imports evade immediate-statement and lazy-scope detection | An `if True:` import in the migration-owned _doctrine_collect.py passed all five relevant gates | 01M1V2E61TNTD505NYMSCB9TC1 |

## Initial validation

- `make test-fast`: 1,642 passed, 6 warnings, 209.08 seconds.
- Changed/adjacent architecture and documentation gates: 219 passed, 185.13 seconds.
- Two formatting-corrected tests: 7 passed, 46.88 seconds.
- Repository-wide `ruff check .` and `ruff format --check .`: passed after formatting repair.
- Initial independent doctrine matrix rejected all eight ordinary top-level/lazy mutations across two roots and two spellings, but did not reject the whole-file-exception regression. This demonstrates why green existing tests alone were insufficient.

## Scope and concessions

- The removed ownership-manifest schema test enforced only the deleted artifact; independent shim-registry coverage survives.
- Runtime imports into already allowed first-level subpackages remain grandfathered. Dependency inversion behind ports is outside this PR (#2173).
- Frozen retrieval inventories and deferred codemap regeneration are outside the live-reference repair.
- No production runtime behavior changes are intended.
- The experimental-only CI suite is intentionally skipped in this public repository; local architectural checks below provide the direct gate evidence in addition to the public CI checks.

## Remediation evidence

- Formatting-only repair: seven affected tests passed; both full-repository Ruff commands pass.
- Ownership references: independent reviewer cleared both findings; all 11 added relative links resolve. Three related edges validate and the scoped docs structural checks are clean.
- Runtime collector: root-form, dotted, aliased, top-level, and lazy imports now reach the same ledger and hard-boundary checks. Legitimate root functions/attributes remain root imports. Independent source injection verified 16 cases and 32 guard outcomes.
- Independent baseline caps: runtime 23, mission_runtime 10, lazy doctrine file/import pairs 11, orphan doctrine file/import pairs 2. Runtime 23-to-24 and mission_runtime 10-to-11 growth mutations now fail. Shrinkage is reported by the existing baseline machinery.
- Runtime regression evidence: 16 initially failing cases plus two sibling-ledger failures before repair; 75 targeted tests pass after repair.
- Doctrine exceptions now identify exact file/import pairs. The original facade-to-direct-import mutation fails both lazy and orphan gates for legacy and current spellings. Partial exception removal is detected.
- Doctrine regression evidence: 18 initial failures; 68 tests passed after the first repair, followed by 12 passing focused cases for metadata member, multiple-member, and wildcard variants. Strict mypy reports no issues in the two edited doctrine gate files.
- All five Ops listed above are completed with outcome `done` and link their changed artifacts and this report. Their canonical CLI-generated JSONL records are included in this PR.

The combined integration selection passed 210 tests in 115.60 seconds. Independent final doctrine review verified 27 in-memory mutations and cleared the original #3522 regression, metadata variants, ordinary root/spelling/scope matrix, and stale-pair checks.

The final conditional-import fix had seven failing regression cases before repair and 19 passing focused cases afterward (32 deselected, 40.25 seconds). Independent re-review passed all three controls: the exact module-level conditional regression is rejected, TYPE_CHECKING imports remain excluded, and the existing allowed lazy step_contracts import remains correctly classified. Ruff, strict mypy for the edited doctrine gates, repository formatting, and diff whitespace checks pass.

## Final verdict

All three independent lenses approve their scoped fixes. No unresolved merge-blocking finding remains. Issue #3522 can close within its explicit scan-root and reported-regression scope. Both roots are scanned, and the original forbidden import is rejected even inside a file carrying a sanctioned exception.

Accepted limits: enforcement is static and operates at file/module or first-subpackage granularity. Dynamic imports, relative-import resolution, subsequent attribute use through an allowed metadata binding, and additional symbols or occurrences from an already allowed module are not covered. Recognized TYPE_CHECKING blocks remain excluded. These limits are not represented as complete enforcement.

Final verification commands (environment: SPEC_KITTY_ENABLE_SAAS_SYNC=0):

```sh
make test-fast
.venv/bin/pytest -q --tb=short tests/architectural/test_layer_rules.py tests/architectural/test_doctrine_census.py tests/architectural/test_runtime_charter_doctrine_boundary.py tests/architectural/test_ratchet_baselines.py tests/architectural/test_adr_hygiene_convergence_retirement.py tests/architectural/test_shared_package_boundary.py tests/docs/test_docs_structural_lint.py tests/docs/test_related_validator.py
.venv/bin/ruff check .
.venv/bin/ruff format --check .
git diff --check
```

The 210-test combined run preceded the final conditional-only patch; the 19-test follow-up and three independent controls validate that final change. No whole-repository suite was claimed. Public CI must complete on the pushed head before merge. PR #3888 is to land before #3885; add `Closes #3522` to the PR description and verify GitHub closes the issue on merge.
