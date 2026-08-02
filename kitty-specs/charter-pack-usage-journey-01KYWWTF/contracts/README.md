# Behavioral Contracts — Charter Pack Usage Journey

The plan's Phase-1 behavioral contracts for this mission are realized **directly as executable
journey acceptance tests** (ATDD-first, NFR-002) rather than as standalone contract stubs. Each
contract below is a named, runnable test that pins the behaviour of one seam; this file is the index.

| Contract (seam) | Behavioural guarantee | Executable contract (test) | WP |
|-----------------|-----------------------|----------------------------|----|
| Dispatch-net predicate | `is_charter_empty` keys on compiled-bundle presence + org/profile routability; apply-no-compile keeps the generic-agent net (#3104); presence-only ("empty = bundle absent") | `tests/specify_cli/invocation/test_is_charter_empty_bundle_predicate.py` | WP01 |
| `apply --compile` bridge | opt-in `--compile` chains the existing compile seam (no new compiler); default `apply` names `charter generate` and stays git-agnostic (C-004) | `tests/specify_cli/cli/commands/charter/test_apply_compile_bridge.py` | WP02 |
| Fourth-producer convergence | `apply --compile` and the upgrade finalize migration produce a convergent `charter.yaml` catalog shape from the same activation input (FR-008) | `test_apply_compile_bridge.py::test_apply_compile_converges_with_finalize_migration_producer` | WP02 |
| Read-surface presence authority | `charter context`/`status` key presence on `charter.yaml` (OR-gate with legacy `charter.md`), survive `charter.md` deletion; `--json project_charter.present` flips to `charter.yaml` (FR-005/006) | `tests/charter/test_presence_gate_bundle_authority.py` | WP03 |
| Single directive authority | `resolve_project_governance` sources the activated directive set (three-state: `None`→catalog default, `frozenset()`→empty, `{ids}`→those); no 29-catalog fallback (FR-007) | `tests/charter/test_resolve_project_governance_single_authority.py` | WP04 |
| Section-selector graceful-degrade | advertised `section:terminology-canon`/`section:code-review-checklist` resolve to an honest placeholder, never dead-end (FR-010) | `tests/charter/test_section_selector_graceful_degrade.py` | WP05 |
| `analyze` surface agreement | no documented-but-absent bare `spec-kitty analyze` CLI subcommand; docs/skill point at `agent mission record-analysis` (FR-011) | `tests/specify_cli/cli/commands/test_analyze_surface_agreement.py` | WP06 |
| Path-filtered CI | doctrine/charter/invocation PRs get an isolated fast signal; unrelated PRs skip-with-green (FR-012) | `.github/workflows/doctrine-charter-tests.yml` (workflow contract) | WP07 |

**Negative invariants** are encoded inline in the same suites: the `frozenset()` opt-out pins (WP01 dispatch,
WP04 directives) guard against an `is not None`→truthiness collapse; the bootstrapped-empty-bundle-keeps-net-OFF
pin (WP01) guards against re-importing the #3064 exhaustiveness trap; the fresh-minimal-pack integration test
(WP05) guards against the hand-authored-`charter.md` false-green.
