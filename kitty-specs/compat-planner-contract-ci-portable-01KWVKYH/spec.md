# Mission Specification: Revive the compat-planner.json contract check (CI-portable) and fix the drift it surfaces

**Status**: Draft
**Issue**: [#2419](https://github.com/Priivacy-ai/spec-kitty/issues/2419)

## User Scenarios & Testing *(mandatory)*

**Primary actor**: a CI run (and any maintainer running the suite) validating that `spec-kitty upgrade --dry-run --json` payloads still conform to the committed, stable `compat-planner.json` JSON contract.

**Problem**: `tests/specify_cli/cli/commands/test_upgrade_command.py` shares a module-level helper `_validate_json_contract` that resolves the contract path as `_WORKTREE_ROOT.parent.parent.parent / "spec-kitty" / "kitty-specs" / …` — hopping **three levels above the repo root** into a sibling checkout literally named `spec-kitty`. That resolves only by coincidence, inside a maintainer landing-worktree (`.worktrees/<name>/`). In a real GitHub Actions checkout (`/home/runner/work/spec-kitty/spec-kitty`) the path does not exist, so `_CONTRACT` stays `None`, the guarded `jsonschema.validate(...)` early-`return`s, and **every one of the ~12 call sites** validates nothing in CI — the "contract-conformance" tests have enforced nothing since `abcd730cfa` (2026-04-27). This is why #2339 (an 83-of-89-migration contract-pattern bug) reached main uncaught.

**Post-spec finding (empirically confirmed)**: resurrecting the check does **not** produce a clean green — it immediately catches a real, pre-existing drift: `UnifiedBundleMigration.description` (`src/specify_cli/upgrade/migrations/m_3_2_0rc35_unified_bundle.py`) is **283 chars**, violating the contract's `pending_migrations.items.description` `maxLength: 256`. This is the #2339-class catch working as intended, and the mission must remediate it to land green (exactly one such violation exists: a live run is 48 pass / 1 fail).

**Post-plan finding (empirically confirmed)**: a *second* dead enforcer of the same contract exists — `tests/specify_cli/compat/test_messages.py`'s `_validate_against_schema` (5 `render_json` call sites) computes `_CONTRACT_PATH` with `parents[4]` from a 3-deep file, overshooting one level **above** the repo root, so it is dead in **every** layout (worse than the sibling, which at least resolved coincidentally in a maintainer worktree) with the same `.exists()→None` / `except→None` silent-skip. Closing the defect class means reviving both; activating this one with the corrected `parents[3]` anchor is empirically green (28 pass, no new violations).

### User Story 1 - Contract validation actually executes in CI (Priority: P1)
As a CI run, I want the shared helper to load the committed `compat-planner.json` and run `jsonschema.validate` against the real `--dry-run --json` payloads, so drift from the stable contract (renamed field, changed type, narrowed pattern, over-long string) is caught on every PR instead of silently skipped.

**Independent test**: in a GitHub-Actions-style checkout, `_CONTRACT is not None` and validation runs at every call site.

### User Story 2 - A contract violation fails the test (Priority: P1)
As a maintainer, I want a payload that violates the contract schema to make the test FAIL, so the check earns its name — a #2339-style regression is caught. (The revival itself demonstrates this: it catches the 283-char description.)

### User Story 3 - A missing/unreadable contract fails HARD (Priority: P2)
As a maintainer, I want a missing or unreadable contract file to **fail the test hard** with a clear reason — never a skip. A skipped test is green to CI gating and would silently re-deaden the check, reintroducing the exact failure mode this mission exists to kill.

### Edge Cases
- Run from a maintainer landing worktree (`.worktrees/<name>/`) — must resolve from the repo root, not the coincidental sibling-checkout path.
- Run from an arbitrary CWD — resolution is anchored on `__file__`, never CWD.
- Contract legitimately relocated in future — the test fails loudly (prompting a path update) rather than passing vacuously.
- A second, unexpected non-conformance surfaces once the check is live — triaged as a real violation (fix payload or contract), never re-suppressed. (Empirically only the one is present today.)

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
| --- | --- | --- | --- | --- |
| FR-001 | Repo-root-anchored contract path | As a CI run, I want the contract resolved from the real repo root (`_WORKTREE_ROOT / "kitty-specs" / "cli-upgrade-nag-lazy-project-migrations-01KQ6YDN" / "contracts" / "compat-planner.json"`), with no hop above the repo root into a sibling `spec-kitty/` dir, so it resolves in any checkout layout. | High | Open |
| FR-002 | Validation always executes at every call site | As a CI run, I want `jsonschema.validate(payload, contract)` to run with the contract always loaded — activating validation at **all ~12 `_validate_json_contract` call sites** (today all no-op because `_CONTRACT` is `None`), not just the one named test — so no contract-checked payload is silently skipped. | High | Open |
| FR-003 | Fail HARD on missing/unreadable contract | As a maintainer, I want a missing or unreadable/invalid contract to **fail the test** with a clear message — never skip — replacing the silent `.exists()` + `contextlib.suppress(Exception)` → `None` fallback. | High | Open |
| FR-004 | Non-vacuous regression witness | As a maintainer, I want coverage proving a schema-violating payload is rejected, so the check is demonstrably live, not green-by-construction. | Medium | Open |
| FR-005 | Remediate the drift the revived check surfaces | As a maintainer, I want the one real violation the resurrected check exposes remediated so the suite is green with validation live: trim `UnifiedBundleMigration.description` (`m_3_2_0rc35_unified_bundle.py`, 283 chars) to ≤256 while preserving its meaning, satisfying `pending_migrations.items.description` `maxLength: 256`. | High | Open |
| FR-006 | Close the class: revive the sibling render_json check | As a maintainer, I want the second dead enforcer (`test_messages.py::_validate_against_schema`, 5 `render_json` call sites) revived too — anchor its `_CONTRACT_PATH` on the repo root (`Path(__file__).parents[3]`, since the file is 3-deep) and drop its `.exists()→None` / `except→None` silent-skip so a missing contract fails hard — so no dead enforcer of `compat-planner.json` survives the mission (empirically green: 28 pass). | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
| --- | --- | --- | --- | --- | --- |
| NFR-001 | Layout-agnostic resolution | Contract path resolution is deterministic and independent of CWD, worktree, and CI layout — verified against the GitHub Actions layout (`/home/runner/work/spec-kitty/spec-kitty`), a plain local checkout, and a `.worktrees/<name>/` landing worktree. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
| --- | --- | --- | --- | --- | --- |
| C-001 | Reuse the correctly-computed root | Anchor on the already-correct `_WORKTREE_ROOT` (`Path(__file__).parents[4]`); do not introduce a new repo-root-finding mechanism. | Technical | High | Open |
| C-002 | No new suppressions | `mypy --strict` + `ruff` clean; no new `# type: ignore` / `# noqa` / silent `contextlib.suppress`. | Technical | High | Open |
| C-003 | Bounded scope: 2 test files + one drifted string | Change spans both dead-check test files (`test_upgrade_command.py`, `test_messages.py`) plus the single over-long migration description string (`m_3_2_0rc35_unified_bundle.py`) the revived check surfaces. The `compat-planner.json` contract (incl. `maxLength: 256`) and all `spec-kitty upgrade` runtime **behavior** stay unchanged — only the drifted description text is trimmed. | Technical | High | Open |

### Key Entities
- **`compat-planner.json`** — the committed, stable JSON-schema contract at `kitty-specs/cli-upgrade-nag-lazy-project-migrations-01KQ6YDN/contracts/`; `pending_migrations.items.description` caps at `maxLength: 256`.
- **`_validate_json_contract`** (`test_upgrade_command.py`) — the shared test helper (~12 call sites) that currently no-ops in CI.
- **`_validate_against_schema`** (`test_messages.py`) — the sibling dead enforcer of the same contract (5 `render_json` call sites), path-broken via a `parents[4]` overshoot.
- **`UnifiedBundleMigration.description`** — the 283-char production migration description that violates the cap (the drift the revived check catches).

## Success Criteria *(mandatory)*

### Measurable Outcomes
- **SC-001**: Simulating the GitHub Actions checkout layout, `_CONTRACT` loads (non-`None`) and `jsonschema.validate` runs. (Currently `_CONTRACT is None` → skipped.)
- **SC-002**: A payload violating the contract schema makes the test FAIL (red-first proof) — and the revival itself is demonstrated to catch the 283-char description before FR-005 trims it.
- **SC-003**: A missing/unreadable contract makes the test FAIL (hard, with a clear reason) — never skip, never silently pass.
- **SC-004**: With validation genuinely live across all `_validate_json_contract` call sites (`test_upgrade_command.py`) AND the sibling `_validate_against_schema` call sites (`test_messages.py`), **both** files are green — achieved by trimming the one drifted description (FR-005), NOT by neutering or re-suppressing any check; `ruff` + `mypy --strict` clean.
- **SC-005**: No dead enforcer of `compat-planner.json` survives — both resolvers load the real contract from the repo root, and both silent-skip fallbacks are removed (a missing contract fails hard in each).

## Out of Scope
- Revising the contract's `maxLength: 256` cap — keep the "stable across patch releases" contract stable and bring the drifted description back into compliance instead.
- Any `spec-kitty upgrade` runtime **behavior** change (only the description string is trimmed).
- Remediating additional non-conformances beyond the one known violation — the empirical post-spec run showed exactly one (48 pass / 1 fail); a second, unexpected one would be triaged as a real violation, not re-suppressed.
- Broader test-isolation / CI-topology work (sibling members under epic #1931 — separate missions).

## Assumptions
- The contract stays at its repo-root-relative path `kitty-specs/cli-upgrade-nag-lazy-project-migrations-01KQ6YDN/contracts/compat-planner.json` (confirmed present, ~11 KB).
- `jsonschema` is a hard dependency (`pyproject.toml`), already imported by the test.
- Reviving the check surfaces exactly one pre-existing violation (`UnifiedBundleMigration.description`, 283 > 256) — empirically confirmed by the post-spec squad (48 pass / 1 fail). The mission remediates that one; it does not assume a clean-green revival.
