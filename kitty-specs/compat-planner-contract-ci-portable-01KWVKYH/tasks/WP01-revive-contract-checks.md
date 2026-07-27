---
work_package_id: WP01
title: Revive both compat-planner.json contract checks and fix the drift
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- NFR-001
tracker_refs: []
planning_base_branch: fix/compat-planner-contract-ci-portable
merge_target_branch: fix/compat-planner-contract-ci-portable
branch_strategy: Planning artifacts for this mission were generated on fix/compat-planner-contract-ci-portable. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/compat-planner-contract-ci-portable unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
agent: "claude"
shell_pid: "203732"
history:
- 'Created by planner for #2419 tasks phase'
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/specify_cli/cli/commands/test_upgrade_command.py
- tests/specify_cli/compat/test_messages.py
- src/specify_cli/upgrade/migrations/m_3_2_0rc35_unified_bundle.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Revive both compat-planner.json contract checks and fix the drift

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude` · **Model**: `claude-sonnet-5`

---

## Objective

Make sure **no dead enforcer of `compat-planner.json` survives**. Two test surfaces validate `spec-kitty upgrade`/`render_json` payloads against that stable contract, and **both** currently no-op in CI because they resolve the contract via a bad worktree-relative path and then silently skip. Fix the paths, make validation unconditional and fail-hard, and remediate the one real drift the revival catches — so the suite is green with the checks genuinely live, never by re-suppressing.

## Context (read before editing)

- `compat-planner.json` lives at `kitty-specs/cli-upgrade-nag-lazy-project-migrations-01KQ6YDN/contracts/compat-planner.json` (present, ~11 KB). Its `pending_migrations.items.description` caps at `maxLength: 256`.
- **Dead check A** — `tests/specify_cli/cli/commands/test_upgrade_command.py` (file is **4-deep**, `_WORKTREE_ROOT = Path(__file__).parents[4]` is already the repo root). Lines ~62-69 then hop `_WORKTREE_ROOT.parent.parent.parent / "spec-kitty" / "kitty-specs" / …` — three levels **above** the root into a sibling checkout; resolves only in a `.worktrees/<name>/` layout, never in CI. Lines ~72-75 guard with `.exists()` + `contextlib.suppress(Exception)` → `_CONTRACT = None`; line ~116 `if _CONTRACT is not None:` skips `jsonschema.validate`. Helper is shared by ~12 call sites.
- **Dead check B** — `tests/specify_cli/compat/test_messages.py` (file is **3-deep**). Lines ~44-50 use `Path(__file__).parents[4]` which **overshoots one level above the repo root** (dead in every layout). `_get_contract` (~279) `.exists()→None` / `except Exception: return None`; `_validate_against_schema` (~288) `if contract is None: return`. 5 `render_json` call sites (311,325,340,353,366).
- **The drift** — reviving check A makes it catch a real violation: `UnifiedBundleMigration.description` in `src/specify_cli/upgrade/migrations/m_3_2_0rc35_unified_bundle.py` (lines ~89-95) is **283 chars > 256**. This is the #2339-class catch working; the only legitimate green is to trim the description.

## Branch Strategy
Planning/base + merge target: `fix/compat-planner-contract-ci-portable`. Execution runs in the lane worktree allocated by `lanes.json`.

## Detailed Guidance

### T001 — Repo-root-anchor the path in `test_upgrade_command.py` (FR-001, NFR-001)
Replace the `_CONTRACT_PATH` computation so it is `_WORKTREE_ROOT / "kitty-specs" / "cli-upgrade-nag-lazy-project-migrations-01KQ6YDN" / "contracts" / "compat-planner.json"` — no `.parent.parent.parent` hop, no `"spec-kitty"` segment. `_WORKTREE_ROOT` (`parents[4]`) is already the repo root; reuse it (C-001).

### T002 — Always-validate + fail-hard in `test_upgrade_command.py` (FR-002, FR-003)
Load the contract unconditionally (module import or first use) so `_CONTRACT` is always a dict. Drop the `if _CONTRACT_PATH.exists():` guard and the `contextlib.suppress(Exception)` — a missing/unreadable/invalid contract must raise with a clear message (e.g. `FileNotFoundError`/`json.JSONDecodeError` surfaced, or an explicit `pytest.fail(...)`), never leave `_CONTRACT = None`. Remove the `if _CONTRACT is not None:` guard in `_validate_json_contract` so `jsonschema.validate` runs every time. No skip. Remove any now-unused `contextlib` import.

### T003 — `parents[3]`-anchor + fail-hard in `test_messages.py` (FR-006)
Set `_CONTRACT_PATH = Path(__file__).parents[3] / "kitty-specs" / "cli-upgrade-nag-lazy-project-migrations-01KQ6YDN" / "contracts" / "compat-planner.json"` (this file is 3-deep — parents[3], **not** parents[4]). In `_get_contract`, drop `.exists()→None` and `except Exception: return None` so a missing/unreadable contract fails hard. In `_validate_against_schema`, remove the `if contract is None: return` short-circuit so the 5 `render_json` call sites validate for real. If there is a `jsonschema`-absent branch, keep it honest (fail-hard / real check), not a silent return.

### T004 — Trim the drifted description (FR-005)
Trim `UnifiedBundleMigration.description` (`m_3_2_0rc35_unified_bundle.py`) from 283 to **≤256** chars, preserving meaning. Suggested: condense the trailing "Idempotent. Does NOT scan worktrees, remove symlinks, or reconcile .gitignore." clause. Do **not** change the contract's `maxLength: 256`. Verify the final length is ≤256.

### T005 — Non-vacuous witnesses for BOTH checks (FR-004, SC-002)
Prove each revived check is non-vacuous, not green-by-construction:
- **Check A** (`_validate_json_contract`, `test_upgrade_command.py`): construct a payload violating the contract (e.g. `pending_migrations[].description` > 256) and assert `jsonschema.ValidationError` is raised **through the helper**.
- **Check B** (`_validate_against_schema`, `test_messages.py`): feed a `render_json`-shaped payload that violates the schema (e.g. inject a `>256`-char description or a wrong-typed field) and assert `jsonschema.ValidationError` is raised **through the helper**. Check B's normal tests pass whether it is dead or live (`pending_migrations` defaults to `()`), so `28 pass` is NOT proof — a reject-path witness is required.

Both witnesses must go RED if the respective `validate` call is deleted (mutation-checkable). Also add a check that in a simulated non-`.worktrees` layout the contract still loads (path is `__file__`-anchored). Then run the full `test_upgrade_command.py` and `test_messages.py` green.

### T006 — Fail-hard coverage for a missing/unreadable contract, BOTH files (FR-003, SC-003, SC-005)
FR-003/SC-003's hard-fail branch must be **exercised by a test**, not asserted-by-construction — this is the exact silent-`None` defect that kept the check dead for ~14 months, so a reintroduced `.exists()→None` fallback must be caught by the suite. For EACH of `test_upgrade_command.py` and `test_messages.py`: add a test that points the contract path at (a) a nonexistent file and (b) a malformed/non-JSON file, and asserts the load/validate **fails hard** (raises, or the test fails with a clear reason) — never skips, never returns `None`. These tests must go RED if a silent-`None` fallback is reintroduced.

## Test Strategy (red-first, mandatory)
1. **Prove the drift catch is real**: after T001-T003 (before T004), `test_upgrade_command.py` must FAIL on the 283-char description — capture that RED. This is the #2339-class catch demonstrated.
2. After T004, the same test passes — capture GREEN.
3. The T005 witness must FAIL if you neuter validation (delete the `validate` call) and pass otherwise.

## Definition of Done
- [ ] `_CONTRACT`/`_get_contract()` load the real contract in a plain checkout (no `.worktrees` dependency); a missing contract fails hard in BOTH files.
- [ ] Validation runs unconditionally at all `_validate_json_contract` and `_validate_against_schema` call sites (no skip, no `None`-guard).
- [ ] `UnifiedBundleMigration.description` is ≤256 chars, meaning preserved; contract `maxLength` unchanged.
- [ ] Non-vacuous reject-path witness for BOTH `_validate_json_contract` AND `_validate_against_schema` (schema violation → `ValidationError` through each helper; mutation-checkable — deleting a `validate` call goes RED).
- [ ] Fail-hard coverage: a **missing** AND a **malformed** contract make BOTH files' checks fail hard (a test exercises the branch; a reintroduced silent-`None` fallback goes RED).
- [ ] `PWHEADLESS=1 uv run pytest tests/specify_cli/cli/commands/test_upgrade_command.py tests/specify_cli/compat/test_messages.py -q` green.
- [ ] `ruff check` + `mypy --strict` clean on all three files; no new `# type: ignore` / `# noqa` / silent `suppress`.

## Reviewer Guidance
Confirm green is reached by the description trim (T004), **not** by re-suppressing/skipping/gaming a fixture. Mutation-check **both** witnesses (delete each `validate` call → both must go red — a live check B is not proven by "28 pass"). Confirm the fail-hard tests actually execute the missing AND malformed branches (reintroduce a silent-`None` fallback → they must go RED). Verify `parents[4]` (check A) vs `parents[3]` (check B) are file-correct. Confirm the contract file and `spec-kitty upgrade` runtime behavior are untouched.

## Activity Log

- 2026-07-06T13:03:41Z – claude – shell_pid=179689 – Assigned agent via action command
- 2026-07-06T13:24:39Z – claude – shell_pid=179689 – Moved to for_review
- 2026-07-06T13:24:41Z – claude – shell_pid=203732 – Started review via action command
