# Work Packages: Revive the compat-planner.json contract check (CI-portable) and fix the drift

**Mission**: `compat-planner-contract-ci-portable-01KWVKYH` | **Issue**: #2419 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Subtask Format: `[Txxx] [P?] Description (WP)`

## Path Conventions
Repo-root-relative. This mission spans two dead-check test files and one production description string; it is a single coherent unit (reviving the checks makes the suite catch the 283-char drift, which the trim fixes) so it lands as one work package.

| Subtask | Description | WP | Requirement |
| --- | --- | --- | --- |
| T001 | Repo-root-anchor `_CONTRACT_PATH` in `test_upgrade_command.py` (drop the sibling-`spec-kitty` hop) | WP01 | FR-001, NFR-001 |
| T002 | Always-validate + fail-hard on missing/unreadable contract in `test_upgrade_command.py` (drop `.exists()`+`suppress`, remove the `None`-guard) | WP01 | FR-002, FR-003 |
| T003 | `parents[3]`-anchor + fail-hard in `test_messages.py` (`_get_contract`/`_validate_against_schema`) | WP01 | FR-006 |
| T004 | Trim `UnifiedBundleMigration.description` to ≤256 preserving meaning | WP01 | FR-005 |
| T005 | Non-vacuous reject-path witnesses for BOTH checks (schema violation → `ValidationError` through each helper) + CI-layout load check | WP01 | FR-004, SC-002 |
| T006 | Fail-hard coverage: missing + malformed contract → hard fail in BOTH files; both files green; `ruff`/`mypy --strict` clean | WP01 | FR-003, SC-003, SC-005 |

---

## Work Package WP01: Revive both compat-planner.json contract checks and fix the drift (Priority: P1)

**Prompt**: `/tasks/WP01-revive-contract-checks.md`

**Goal**: No dead enforcer of `compat-planner.json` survives — both `_validate_json_contract` (`test_upgrade_command.py`) and `_validate_against_schema` (`test_messages.py`) load the real contract from the repo root, validate unconditionally, and fail hard on a missing contract. The one real drift the revival surfaces (`UnifiedBundleMigration.description`, 283 > 256) is trimmed so the suite is green with validation genuinely live — never by re-suppressing.

**Independent test**: In a simulated GitHub-Actions layout, `_CONTRACT`/`_get_contract()` load the real contract; a deliberately schema-violating payload raises `jsonschema.ValidationError`; the full `test_upgrade_command.py` and `test_messages.py` are green.

### Included Subtasks
- [ ] T001 Repo-root-anchor `_CONTRACT_PATH` in `test_upgrade_command.py` (WP01)
- [ ] T002 Always-validate + fail-hard on missing/unreadable contract in `test_upgrade_command.py` (WP01)
- [ ] T003 `parents[3]`-anchor + fail-hard in `test_messages.py` (WP01)
- [ ] T004 Trim `UnifiedBundleMigration.description` to ≤256 preserving meaning (WP01)
- [ ] T005 Non-vacuous reject-path witnesses for BOTH checks + CI-layout load check (WP01)
- [ ] T006 Fail-hard coverage: missing + malformed contract → hard fail in both files; both green; ruff/mypy clean (WP01)

### Implementation Notes
Reuse the already-correct repo-root anchors: `_WORKTREE_ROOT = Path(__file__).parents[4]` in `test_upgrade_command.py` (4-deep) and `Path(__file__).parents[3]` in `test_messages.py` (3-deep) — do NOT copy an index across files. Remove every silent-skip surface (`.exists()→None`, `contextlib.suppress`, `except Exception: return None`, `if contract is None: return`, `if _CONTRACT is not None:`). Keep the contract file and `spec-kitty upgrade` runtime behavior untouched.

### Parallel Opportunities
None — single WP; the revive (red) and trim (green) must land together.

### Dependencies
None.

### Risks & Mitigations
- **Re-suppression temptation**: activating validation surfaces the 283-char drift; the ONLY legitimate green is trimming that description (T004), never neutering the check or gaming a fixture. — Mitigate via the non-vacuous witness (T005).
- **Wrong anchor index**: `parents[4]` vs `parents[3]` differ by file depth. — Verify each resolves to the present contract before relying on it.
- **jsonschema-absent branch**: if a file has an `ImportError` fallback, keep it honest (fail-hard), not a silent return.
