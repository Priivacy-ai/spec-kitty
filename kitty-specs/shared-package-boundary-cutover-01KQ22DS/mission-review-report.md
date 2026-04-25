# Mission Review Report — `shared-package-boundary-cutover-01KQ22DS`

**Mission:** `shared-package-boundary-cutover-01KQ22DS`
**Squash sha:** `c92bf800` (single landing on `main` per C-007)
**Final main sha after all post-merge work:** `bad32549`
**Verdict:** **PASS WITH NOTES** (see findings + remediation below)

This report is the durable artifact of the mission-review verdict and the
subsequent post-merge work. It supersedes transcript-only state per the
program-review process gap (Priivacy-ai/spec-kitty#792).

---

## Mission-review verdict

**PASS WITH NOTES** at the time of mission-review (post-squash, pre-cleanup).
The hard cross-repo invariants — every item PR #779 was rejected for — were
intact on `main`. The findings recorded below were treated as remediation
items (not blockers); each was either closed inline via the
`post-merge/<slug>-mission-review-fixes` branch or filed as a follow-up issue.

## Findings, by severity

### HIGH (blocking until remediated)

**RISK-1 — FR-020 stale-runtime deprecation notice was unimplemented.**

- **Spec contract:** FR-020 — "The CLI MUST emit, where feasible without re-introducing runtime imports, a single one-time operator notice on first post-cutover invocation if `spec-kitty-runtime` is still installed in the user's environment, pointing them at the migration doc."
- **Observed at squash:** No WP owned the FR-020 deliverable; the deprecation-notice module did not exist.
- **Remediation:** Implemented `src/specify_cli/next/_runtime_pkg_notice.py` using `importlib.metadata.distribution("spec-kitty-runtime")` (which does NOT trigger an import of the package), with a 6-test unit suite at `tests/next/test_runtime_pkg_notice_unit.py`. Wired into `src/specify_cli/cli/commands/next_cmd.py` as a one-shot first-run hook.
- **Closed in:** Post-merge mission-review remediation merge `09f3b198` (`Merge post-merge mission-review fixes for shared-package-boundary-cutover-01KQ22DS`).

### MEDIUM

**DRIFT-2 — stale `spec-kitty-runtime` docstrings/comments/data labels in 5 source files.**

- **Spec contract:** C-001 / FR-002 prohibit production imports; the spec was permissive on docstring references that document the migration history. Mission-review flagged a stronger stance: post-cutover docstrings should not lead readers to think the module still depends on the retired package.
- **Remediation:** Audited the 5 files (`_internal_runtime/__init__.py`, `_runtime_pkg_notice.py`, `next_cmd.py`, plus two adapters). Tightened docstrings to make clear these are *historical* references and that the production runtime is now CLI-internal. The architectural test (`tests/architectural/test_shared_package_boundary.py`) enforces no actual import statements via AST scan.
- **Closed in:** `09f3b198` (same remediation merge as RISK-1).

**RISK-2 — required-status-checks branch protection for `clean-install-verification` is configured out of band.**

- **Spec contract:** A6 — "CI passes without shared-package drift failures."
- **Observation:** The `clean-install-verification` job exists in `.github/workflows/ci-quality.yml` and runs on every PR. Whether GitHub branch protection lists it as a required status check is a maintainer-only setting that lives outside the repo.
- **Disposition:** Documented as a manual maintainer step in the migration runbook. Not closable by code in this repo.
- **Filed as follow-up:** Captured in the cleanup acceptance-record. The maintainer step is to add the `clean-install-verification` job to the branch protection's required-status-checks list under repository settings.

### LOW

**DRIFT-1 — `uv lock --check` zero-diff CI gate missing.**

- **Spec contract:** NFR-005 — "Lockfile reproducibility. `uv.lock` resolves deterministically from `pyproject.toml` + a fresh `uv lock --check` run, with zero diff."
- **Observation:** A committed `uv.lock` existed but no CI gate asserted reproducibility. A future contributor could land a `pyproject.toml` change without regenerating `uv.lock` and CI would not catch it.
- **Remediation:** Added `uv-lock-check` job to `.github/workflows/ci-quality.yml` using `astral-sh/setup-uv@v6`; wired into the `quality-gate` aggregator's `needs:` list and result-check loop. Verified locally: `uv lock --check --python python3.12` resolves zero-diff.
- **Closed in:** Deferred-follow-ups merge `9cad3cda` (`Merge post-merge deferred follow-ups for shared-package-boundary-cutover-01KQ22DS`).

**DRIFT-3 — C-006 quarantine comment missing on `tests/fixtures/runtime_parity/_capture_baselines.py`.**

- **Spec contract:** C-006 — "Test fixtures that reference `spec_kitty_runtime` MUST be quarantined under `tests/` and time-bound by an explicit comment naming the cutover mission slug."
- **Observation:** `_capture_baselines.py` is a parity-recording fixture used by the test suite to lock in pre-cutover runtime behavior; it intentionally references the migration history. The mission shipped without an explicit `QUARANTINED-BY-C-006` comment naming the mission slug.
- **Remediation:** Added 7-line top-of-file quarantine comment naming `QUARANTINED-BY-C-006`, dev-only, never invoked from runtime code, mission slug, and removal milestone.
- **Closed in:** `9cad3cda`.

**RISK-3 — `pytest.mark.contract` not registered.**

- **Spec contract:** Process hygiene; the consumer-contract suite uses `@pytest.mark.contract` to gate the FR-009 contract tests.
- **Observation:** Marker was used but not declared, producing `PytestUnknownMarkWarning` on collection.
- **Remediation:** Registered `contract` marker in `pytest.ini` and `pyproject.toml` `[tool.pytest.ini_options]`; added `pytestmark = [pytest.mark.contract]` to the two consumer-contract test files. Verified: `pytest --collect-only -q` is warning-free.
- **Closed in:** `9cad3cda`.

### Silent-failure candidate (uncovered until program review)

**H1 — `tests/contract/test_handoff_fixtures.py` had 10 regressions on `main` after squash.**

- **Cause:** The cutover changed the import from the now-deleted vendored `specify_cli.spec_kitty_events.models.Event` to the public `spec_kitty_events.Event` (events 4.0.0). The public envelope adds three required fields the inline `FIXTURE_EVENTS` had not been populating: `build_id`, `project_uuid`, `correlation_id`. Three more (`project_slug`, `schema_version`, `data_tier`) were also unpopulated.
- **Why mission-review missed it:** The mission-review skill ran the spec/plan/tasks fidelity audit but did not re-run the full `tests/contract/` suite against the post-squash main. This is filed as a process improvement: Priivacy-ai/spec-kitty#792.
- **Remediation:** Updated the 8 inline FIXTURE_EVENTS plus the JSON fixture files (`contracts/fixtures/fixture_01_*.json`, `fixture_02_*.json`) with placeholder constants matching the events 4.0.0 schema. All 32 tests now pass. Commit `76af36ee`.
- **Closed in:** Program-review fix-ups merge `bad32549`.

## Cross-repo invariant verification (PASS at `bad32549`)

| Invariant | Verification | Result |
|---|---|---|
| C-001/FR-002 No production `spec_kitty_runtime` imports | `grep -rn "^[[:space:]]*\(from spec_kitty_runtime\\|import spec_kitty_runtime\)" src/` | empty (only docstring references) |
| C-002/FR-003 No vendored events tree under `src/` | `ls src/specify_cli/spec_kitty_events` | does not exist |
| C-005/FR-013 Empty `[tool.uv.sources]` | `awk '/^\[tool.uv.sources\]/,/^\[/' pyproject.toml` | section absent |
| FR-006 No `spec-kitty-runtime` in `pyproject.toml` deps | `grep "spec-kitty-runtime" pyproject.toml` | only a comment explaining its intentional absence |
| FR-007/C-004 Compatible ranges, not exact pins | `grep -E "spec-kitty-(events\|tracker)" pyproject.toml` | `spec-kitty-events>=4.0.0,<5.0.0`, `spec-kitty-tracker>=0.4,<0.5` |
| FR-011 Architectural enforcement (pytestarch) | `tests/architectural/test_shared_package_boundary.py` | 64/64 architectural tests pass |
| FR-019 Wheel-shape (no vendored events in built wheel) | `tests/contract/test_packaging_no_vendored_events.py` | 2/2 pass |
| FR-020 Deprecation notice via `importlib.metadata` | `tests/next/test_runtime_pkg_notice_unit.py` | 6/6 pass |
| FR-017 `spec-kitty next` parity vs pre-cutover | `tests/next/test_internal_runtime_parity.py` | 8/8 pass (4-snapshot byte-equal) |
| C-007/A9 Single landing on main; no hybrid mid-flight | `git log --first-parent main` | mission landed as squash `c92bf800`; post-merge fixes `--no-ff` |
| NFR-005 `uv lock --check` zero diff | `uv lock --check --python python3.12` | resolved 115 packages in 1ms (verified locally), CI gate added |
| NFR-007 No stale "install spec-kitty-runtime" copy in docs | `grep -rn "install spec-kitty-runtime" docs/ README.md CHANGELOG.md` | only `pip uninstall spec-kitty-runtime` in migration doc — correct |

## Open NFRs (tracked, in flight)

These three NFRs were marked Required but the mission shipped them as accepted
deviations. A `post-merge/<slug>-nfr-closure` branch is in flight to close
them properly; results will be appended here when that lands.

| NFR | Spec threshold | At-merge state | Tracking |
|---|---|---|---|
| **NFR-001** Coverage ≥90% on `src/specify_cli/next/_internal_runtime/` | ≥90% line | 50% measured | Priivacy-ai/spec-kitty#788 |
| **NFR-002** `mypy --strict` zero errors on changed files | 0 errors | 32 errors / 5 files | Priivacy-ai/spec-kitty#789 |
| **NFR-003** `spec-kitty next` ≤20% latency regression vs pre-cutover | ≤20% delta | post-cutover 527ms baseline only; no pre-cutover comparison number | (filing or folding into #788/#789 — pending NFR-closure agent verdict) |

## Cross-cutting follow-ups filed

| Issue | Title | Disposition |
|---|---|---|
| #783 | `mark-status` checkbox parsing bug | spec-kitty CLI bug surfaced during this mission; not blocking |
| #784 | Post-merge phantom staged deletions | spec-kitty merge driver bug; workaround documented |
| #785 | `spec-kitty merge` silently drops lane-planning content | spec-kitty merge driver bug with full root-cause analysis; impacts other repos in the program but did not affect this mission (single lane-a only) |
| #788 | NFR-001 coverage deviation | tracking; in flight |
| #789 | NFR-002 mypy --strict zero-errors deviation | tracking; in flight |
| #790 | Pre-existing terminology guard test | inherited, not caused by mission |
| #791 | Pre-existing `test_cross_repo_consumers.py` events-3.2.0 assertion | inherited, not caused by mission |
| #792 | Mission-review skill should run full `tests/contract/` as hard gate | process improvement that would have caught H1 |

## Definition-of-Done check at `bad32549`

| DoD criterion | Status |
|---|---|
| All FRs marked Required are implemented and verified in tests | PASS — 20/20 verified per spec; FR-020 added in mission-review remediation |
| All NFR thresholds are met or have documented, reviewed exceptions | PARTIAL — NFR-005, NFR-007 PASS; NFR-001/NFR-002/NFR-003 documented as accepted deviations with tracked closure work in flight |
| All Constraints hold on `main` after merge | PASS — C-001 through C-011 verified |
| All Acceptance criteria pass | PASS — A1 through A9 verified, including A9 single-landing |
| Mission lands as a single change on `main` | PASS — squash `c92bf800` |
| Prior hybrid PR (#779) is formally superseded | PASS — recorded in ADR `architecture/2.x/adr/2026-04-25-1-shared-package-boundary.md` frontmatter, in `docs/migration/shared-package-boundary-cutover.md` "Supersedes" section, and referenced in `docs/development/local-overrides.md` as a cautionary case study |

## Process notes for future missions

The `H1` finding (10 contract-test regressions silently shipping past the
mission-review verdict) is the most operationally interesting finding here.
The current `spec-kitty-mission-review` skill audits FR/NFR/C fidelity but
does not run the full `tests/contract/` suite against the post-squash main
and compare to the pre-mission baseline. Adding that as a hard gate is the
single highest-leverage process improvement surfaced by this program (filed
as #792).

The other recurring failure mode worth recording: `spec-kitty merge`
silently dropped lane-planning content in the runtime mission's merge
because of the `lane-planning` → target-branch aliasing in
`src/specify_cli/lanes/branch_naming.py:169-170` (issue #785). The CLI
mission was not affected because the planner collapsed everything to
`lane-a`, but the bug pattern is real and will trip future missions until
the merge driver is fixed.
