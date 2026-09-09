# Contract — Governance verdict-map schema (E1)

Authority: `docs/convergence/interim-ci-producer.md` (map) + `tests/release/test_release_ci_ownership.py`
(enforcer). This contract adds the `introduced` disposition.

## Dispositions (closed vocabulary → extended)
| disposition | meaning | set membership asserted by enforcer |
|---|---|---|
| `restore` | pre-fork workflow reinstated | exact set |
| `defer` | pre-fork workflow not yet restored | exact set |
| `never-restore` | pre-fork workflow retired forever (dead subject) | exact set |
| **`introduced`** *(new)* | net-new workflow, no pre-fork ancestor (router, module-*, aggregate, sonar, nightly, packs) | exact set |

## Invariants (enforcer MUST assert)
1. Every `.github/workflows/*.yml` maps to exactly one disposition.
2. `introduced` + `restore` workflows use **stock runners** (`"blacksmith" not in text`) and carry **no `SK_CI_TOKEN`** on public jobs.
3. Any de-defer (`defer→restore`) or net-new (`∅→introduced`) edits the map **in the same change** (C-001).
4. The enforcer runs on **every workflow-changing PR** (not only tag push).
5. Adding `introduced` must not weaken the existing three-set assertions (self-mutation test: deleting a row reds).
