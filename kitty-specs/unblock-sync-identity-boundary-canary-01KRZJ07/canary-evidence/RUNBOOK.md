# Canary Local Verification Runbook — WP04

Mission: `unblock-sync-identity-boundary-canary-01KRZJ07`
WP: WP04 (canary local verification)
Date executed: 2026-05-19

This document records the actual local canary verification performed for WP04.
The procedure manual lives in [`../quickstart.md`](../quickstart.md) Step 3;
this file is the **record of what was actually done** plus the outcome.

---

## 1. Why this is a *local* verification (not against a published rc)

The mission was orchestrated such that WP04 runs **before** the mission merge to
`main` so the canary evidence is part of the mission PR rather than a post-merge
operator step (decision `01KRZKFYKHE9V2PE5FJD0QCS69` — resolved
`final_wp_local_canary_verification`). At the time of WP04, **no** rc bump
(e.g. `3.2.0rc14`) has been built on PyPI carrying WP01+WP02+WP03 — the lane
branches still hold those fixes individually. Therefore "the rc bump" is
synthesised locally by merging the three approved lane branches into the
mission branch and installing the result editable into a venv that the
sibling-repo canary harness consumes.

This is the canary-against-merged-mission-state pattern the spec authorises.

## 2. Mission branch state used

- Repo: `/Users/robert/spec-kitty-dev/1122-1123-1124-43/spec-kitty`
- Mission branch tip (planning base): `45edd287` (`chore: planning artifacts for unblock-sync-identity-boundary-canary-01KRZJ07`)
- Lane branches merged (approved, in-mission):
  - `kitty/mission-...-lane-a` tip: `c2ea4516` — `feat(WP01): row-family classification (closes #1124)` — WP01 fix (shape_registry / detectors row-family + 395-line test file).
  - `kitty/mission-...-lane-b` tip: `58700be4` — `feat(WP02): render boundary file paths outside Rich Table (closes #1123)` — WP02 fix (sync.py renders `Active queue path` / `Legacy queue path` rows outside the Rich Table so width-driven ellipsis cannot truncate them).
  - `kitty/mission-...-lane-c` tip: `dc725639` — WP03 fix (`spec-kitty doctor restart-daemon` command + remediation hints in preflight).
- Merge worktree: `/tmp/sk-merged-canary` checkout of mission branch, octopus-equivalent of all three lanes merged sequentially with strategy `ort`. No conflicts.
- Merge head used as "rc": `8b8c3487` (Merge branch '...-lane-c' into mission branch).

Verification that the synthesised CLI carries all three fixes:

```text
$ spec-kitty --version
spec-kitty-cli version 3.2.0rc13              # pyproject version not bumped; commit identity is the proof

$ spec-kitty doctor restart-daemon --help     # WP03 surface present (exit 0, command exists)
Usage: spec-kitty doctor restart-daemon [OPTIONS]
Stop the registered sync daemon and respawn it at the foreground.

$ python3 -c "from specify_cli.audit.shape_registry import is_mission_lifecycle_row; print('OK')"
OK                                            # WP01 import works
```

The `spec-kitty-cli version 3.2.0rc13` string reflects the unbumped `pyproject.toml`;
the actual code is the merge head `8b8c3487` (mission branch + lane-a + lane-b + lane-c).

## 3. Sibling canary repo state

- URL: `https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing.git`
- Cloned at: `/tmp/canary-repo`
- Branch checked out: `kitty/pr/sync-identity-boundary-deployed-dev-canary-01KRXVW4-to-main` (PR #42 of the sibling repo — the canary tests live there; the canary work has not yet merged to `main` of the sibling)
- HEAD commit used: `dcee6b2bb634626fc7158b1fd4d3e47a902bccb3`
- `tests/identity_boundary/` contains all four scenario files (1, 2, 3, 4).

Per constraint **C-001** ("no commits to the sibling repo") — no files in the
sibling clone were modified or committed.

## 4. Environment

- OS: `Darwin Roberts-MacBook-Pro-4.local 24.6.0 Darwin Kernel Version 24.6.0: Wed Nov 5 21:33:58 PST 2025; root:xnu-11417.140.69.705.2~1/RELEASE_ARM64_T6000 arm64`
- Python: `Python 3.14.4`
- Canary venv: `/tmp/canary-repo/.venv` (Python 3.14.4)
- Full-pytest venv: `/tmp/sk-merged-canary/.venv-pytest` (Python 3.14.4)
- `spec-kitty-cli` installed editable from `/tmp/sk-merged-canary` (the merge head)
- `spec-kitty-events` 5.1.0, `spec-kitty-tracker` 0.4.3 (PyPI pulls)

## 5. Exact canary invocation

```bash
cd /tmp/canary-repo
source .venv/bin/activate
SPEC_KITTY_ENABLE_SAAS_SYNC=1 pytest tests/identity_boundary/ -v --capture=no -m sync_identity_boundary_deployed_dev 2>&1 | tee /tmp/canary-run.log
```

The marker `-m sync_identity_boundary_deployed_dev` opts in to the canary
selector (the marker is deselected by default per the sibling repo's
`pyproject.toml` `addopts`). `SPEC_KITTY_ENABLE_SAAS_SYNC=1` opts past the
preflight gate's "skip_no_env" branch.

Note: we do **not** set `SPEC_KITTY_E2E_TRUSTED_RUNNER=1` because this run is
not authenticated against the real deployed-dev SaaS. The preflight inferred
`is_trusted_runner=True` from heuristics other than the env var (likely the
presence of `SPEC_KITTY_ENABLE_SAAS_SYNC=1` + a non-empty `saas_url`); the
scenarios then proceed and fail at the contract-mismatch point documented
below rather than skipping. This is honest evidence of what the merged CLI
emits, not a SaaS-auth gate problem.

## 6. Exact full-pytest invocation (NFR-004)

```bash
cd /tmp/sk-merged-canary
source .venv-pytest/bin/activate
pytest tests/ -q --timeout=60 -p no:cacheprovider 2>&1 | tee /tmp/full-pytest.log
```

## 7. Artifacts captured

All under `kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/canary-evidence/`:

- `RUNBOOK.md` — this file.
- `canary-run.txt` — full stdout of the canary pytest run (4 scenarios + tracebacks). (Renamed from `.log` because the repo's `.gitignore` excludes `*.log`.)
- `latest.json` / `run-1.json` — canary harness's `BoundaryEvidence` document (`outcome=fail`, four `ScenarioResult`s).
- `full-pytest.txt` — full stdout of `pytest tests/` on the merged mission state. (Renamed from `.log` because of `.gitignore`.)

---

## 8. OUTCOME SUMMARY (cycle 1/3 re-run, 2026-05-19 11:11 UTC)

> **Build identifier:** mission branch `kitty/mission-unblock-sync-identity-boundary-canary-01KRZJ07` re-merged with lane-a `c2ea4516`, lane-b `8df762db` (WP02 cycle 1/3 B-1 fix), lane-c `dc725639` at `/tmp/sk-merged-canary` (merge head `e16e913c`). `pip show spec-kitty-cli` reports `3.2.0rc13` (pyproject not bumped — actual code is the merge head).
>
> **Sibling-repo HEAD commit:** `dcee6b2bb634626fc7158b1fd4d3e47a902bccb3` (PR #42 branch `kitty/pr/sync-identity-boundary-deployed-dev-canary-01KRXVW4-to-main`). Sibling working tree unmodified (C-001 honoured).
>
> **Invocation:** `cd /tmp/canary-repo && source .venv/bin/activate && SPEC_KITTY_ENABLE_SAAS_SYNC=1 pytest tests/identity_boundary/ -v --capture=no -m sync_identity_boundary_deployed_dev`
>
> **B-1 status:** **RESOLVED**. The new WP02 cycle 1/3 fix (`8df762db`) emits the `Path` row directly under each section header (`Active queue:` / `Legacy queue:`), and the sibling canary `status_parser` (`src/spec_kitty_e2e/identity_boundary/status_parser.py`) successfully extracts `active_queue_db_path` and `legacy_queue_db_path` from the new format. The pre-flight smoke test (parsing a captured `spec-kitty sync status --check` log into a structured dict) is green. Concretely: `active_queue_db_path: /Users/robert/.spec-kitty/queue.db`, `legacy_queue_db_path: /Users/robert/.spec-kitty/queue.db`, `active_event_count: 8716`, no missing-field errors.

### Per-scenario results

| Scenario | Marker | Result | Failure point | Cause classification |
|---|---|---|---|---|
| 1 — fresh authenticated mission reaches SaaS | `scenario_id(1)` | **FAIL** (new failure, NOT B-1) | `spec-kitty sync now` exits 1 with `TeamSpace Migration Required` panel: "Found 2 TeamSpace blocker(s) across 2 mission(s). Finding codes: FORBIDDEN_KEY". Scenario gets past the boundary parser cleanly. | **NEW REGRESSION** — surfaced only after B-1 was fixed. Mission-state audit detects FORBIDDEN_KEY blockers in the test's own fresh mission lifecycle, even though WP01's row-family exemption was supposed to whitelist mission-lifecycle event rows. Suggests WP01 (cycle 1/3 lane-a `c2ea4516`) does not fully exempt the rows that scenario 1's `mission create` → `setup-plan` → `move-task` lifecycle emits. |
| 2 — legacy queue row migration | `scenario_id(2)` | **FAIL** | Same `TeamSpace Migration Required` panel at `spec-kitty sync now`. Connect attempt does NOT reach SaaS endpoint — blocked at local audit gate. | **NEW REGRESSION** (same root cause as scenario 1). The original B-2 (trusted-runner credentials) cannot even be reached because the local audit gate fails earlier. |
| 3 — daemon owner mismatch refusal | `scenario_id(3)` | **FAIL** | AssertionError: `sync status --check did not name every injected mismatch field. injected=['version', 'source', 'server', 'queue_db'] parsed=['package_version', 'executable_path', 'server_url', 'auth_scope', 'queue_db_path'] missing=['version', 'source', 'server', 'queue_db']` at `test_scenario_3_owner_mismatch.py:290`. | **Sibling-repo contract drift (C-002, pre-existing).** The canary scenario injects short keys (`version`, `source`, `server`, `queue_db`) but the CLI emits long-form keys (`package_version`, `executable_path`, ...). This is the sibling-repo #43 issue. UNCHANGED from prior cycle. |
| 4 — review rejection contract | `scenario_id(4)` | **FAIL** (new failure, NOT B-1) | `AssertionError: peeked row is not the rollback we triggered: from='for_review' to='in_review' payload=...` at `test_scenario_4_review_rejection_contract.py:543`. The most-recent `WPStatusChanged` row in the queue is from a prior lifecycle step, not the requested `in_review -> planned` rollback. Either (a) the rollback `move-task --to planned` failed silently (it ran with `check=False`), or (b) the spec-kitty CLI no longer emits a `WPStatusChanged` row for backward force-promoted transitions, or (c) the WP was never actually in `in_review` when the rollback ran. | **NEW REGRESSION OR CONTRACT MISMATCH** — surfaced only after B-1 was fixed. Needs investigation: is the canonical rollback path emitting a force=True row as the contract requires? |

### Acceptance criterion (revised pragmatic criterion from review-cycle-1.md)

| Requirement | Target | Observed | Verdict |
|---|---|---|---|
| Hard: Scenario 1 GREEN | PASS | FAIL (TeamSpace blocker, not B-1) | **NOT MET** |
| Hard: Scenario 4 GREEN | PASS | FAIL (peeked row is wrong transition) | **NOT MET** |
| Soft: Scenario 2 RED only because of B-2 (auth) | Connect must reach SaaS endpoint and be rejected for auth | FAIL — does NOT reach SaaS endpoint; blocked at local TeamSpace audit gate | **NOT MET** |
| Doc: §8 documents scenario 2 as maintainer post-merge step | Yes | Documented below | **MET** |

**Mission done criterion: NOT MET** in this cycle. B-1 (sibling parser contract) is genuinely fixed — that's the good news. But two new failure modes surfaced once the parser stopped masking them:

1. **TeamSpace mission-state audit blocks `sync now`** for newly created missions (scenarios 1 + 2). This was previously hidden because scenarios 1, 3, 4 never reached `sync now` — they died at the parse step first.
2. **Scenario 4 rollback contract** — the `WPStatusChanged` row the canary expects to see emitted by the rollback (`in_review -> planned`, force=True) is not present; the latest queue row is a prior lifecycle step.

Per the WP04 prompt's HALT clause ("If scenario 1, 2, or 4 is RED: Capture the failure detail from the run log. Open a tracking issue describing the regression. Halt this WP and route back to the relevant earlier WP."), this WP04 cycle 1/3 should be routed back to:
- **WP01** for the TeamSpace `FORBIDDEN_KEY` blocker on freshly created missions (scenarios 1 + 2 root cause).
- **Investigation needed** for scenario 4 — could be a spec-kitty regression in the `move-task --to planned` backward-transition handler, or a canary expectation that was never correct against the current CLI.

### Scenario 2: post-merge maintainer step (documentation requirement)

Even with the new failure modes resolved, **scenario 2's full pass requires** `SPEC_KITTY_E2E_TRUSTED_RUNNER=1` plus real deployed-dev credentials (B-2). This is environmental, not a WP defect, and is acceptable as a documented post-merge maintainer step. The maintainer post-merge workflow is:

1. Cut a real `3.2.0rc14` (or successor) PyPI build that includes WP01+WP02+WP03 once they merge to `main`.
2. From a host that holds the deployed-dev trusted-runner credentials (Fly token, etc.), run the four-run protocol described in `scripts/run-sync-identity-boundary-canary.sh` of the sibling canary repo against that rc.
3. Attach the four `latest.json` evidence documents to the mission tracking issue.

This step is explicitly out of scope for the local WP04 verification per decisions `01KRZKFYKHE9V2PE5FJD0QCS69` (final WP runs canary locally), C-001 (no sibling mods), C-002 (sibling #43 deferred), NFR-003 (scenarios 1, 2, 4 must turn green on a re-run against the rc bump — which is now scheduled as a post-merge operator step).

### Full-pytest gate (NFR-004)

**Mode used in cycle 1/3 re-run: scoped re-validation** (per charter update authorising scoped runs for known-surface changes; the only code change since the prior full-suite run is WP02 cycle 1/3 inside `src/specify_cli/cli/commands/sync.py`).

Scoped invocation (executed in `/tmp/sk-merged-canary` after re-installing):

```
pytest tests/specify_cli/cli/commands/test_sync_status_check_paths.py \
       tests/sync/test_sync_status_boundary_check.py \
       tests/specify_cli/audit/ \
       tests/specify_cli/cli/commands/test_doctor_restart_daemon.py \
       tests/specify_cli/sync/test_preflight_remediation_hints.py -v
```

Result captured in `canary-evidence/scoped-validation.txt` (58 passed, 1 warning in 11.57s) — see §7.

The full-suite results from the prior WP04 cycle (`canary-evidence/full-pytest.txt`) remain valid for the WP01 and WP03 surfaces:

| Metric | Value (prior cycle, retained) |
|---|---|
| Command exit | non-zero |
| Passed | 17,656 |
| Failed | 279 |
| Skipped | 65 |
| xfailed | 23 |
| xpassed | 1 |
| Warnings | 405 |
| Wallclock | 1063s (17m 43s) |

The three sampled failures (`test_status_does_not_import_sync`, `test_doctor_healthy`, `test_no_legacy_path_literals_in_cli_commands`) were verified pre-existing on the pre-mission base commit `ded236ee`; tracked in #1134 and #1135.

### What this cycle proves

- **B-1 is genuinely fixed.** Both `_print_boundary_section` and `_print_boundary_paths` helpers are present in `src/specify_cli/cli/commands/sync.py`. The captured `spec-kitty sync status --check` output now contains `"Path"` rows under `"Active queue:"` and `"Legacy queue:"`. The sibling canary parser successfully extracts both paths into the dict it returns.
- **WP01, WP02, WP03 code is present in the merged tree.**
- **Scoped tests for the WP02 surface still pass** after the cycle 1/3 fix.

### What this cycle reveals (new failures masked previously by B-1)

- **Scenarios 1 and 2** are now blocked at the `TeamSpace Migration Required` audit gate, not at the parser. The canary's freshly created mission produces `FORBIDDEN_KEY` blockers that WP01's row-family exemption (lane-a `c2ea4516`) does not whitelist. Without resolving this, scenario 1 cannot reach the SaaS endpoint and scenario 2 cannot reach the auth boundary (B-2).
- **Scenario 4** fails with a rollback-contract mismatch unrelated to B-1. The `move-task --to planned` rollback either failed silently (it runs with `check=False` in the test) or did not emit a backward `WPStatusChanged` row.

### Mission done criterion (NFR-003: scenarios 1, 2, 4 turn green against the merged-mission CLI)

**NOT MET** in this environment, even with the revised pragmatic criterion. B-1 was the gate, and removing it surfaced two new gates (TeamSpace `FORBIDDEN_KEY` blockers, scenario-4 rollback emission). Per the WP04 HALT clause this re-run must be routed back. Recommendation:

1. **Investigate the TeamSpace `FORBIDDEN_KEY` blocker on fresh missions.** This is the root cause for scenarios 1 and 2. Likely a WP01 (cycle 2/3) follow-up: the row-family predicate needs to also exempt the row shapes that scenario 1/2's `setup-plan`/`move-task` lifecycle emits. Reproduce with the canary's exact lifecycle in a fresh `SPEC_KITTY_HOME`.
2. **Investigate scenario 4's rollback emission.** Check (a) whether `move-task --to planned` from `for_review` is supposed to succeed (or whether the canary expects the WP to be in `in_review`, not `for_review`, when the rollback runs); (b) whether the backward force-promoted transition still emits a `WPStatusChanged` row at all in the merged CLI. The captured payload (`from='for_review' to='in_review' force=False`) suggests the rollback was rejected or the previous step's row is the most-recent one.
3. **Cut a real `3.2.0rc14` PyPI build only after (1) and (2) resolve**, and then the maintainer can run the four-run trusted-runner protocol from a host with deployed-dev credentials (B-2).

### Anomalies vs. the previous cycle

- B-1 parse error (`ValueError: missing required string field 'active_queue.Path'`) is **gone** from all scenarios — confirming WP02 cycle 1/3 actually fixed the contract.
- Scenarios 1 and 2 now fail later in the lifecycle, at the TeamSpace audit gate, with a different error class (`TeamSpace Migration Required` panel + exit code 1).
- Scenario 3 still fails for the same C-002 sibling-repo #43 reason (key naming: `version` vs `package_version` etc.), unchanged.
- Scenario 4 now fails at the rollback-emission assertion (was previously failing at the parser).

---

## 9. Diagnostic detail — the WP02 / sibling-canary contract drift (B-1) — RESOLVED

### Resolution summary (cycle 1/3)

B-1 was the cross-repo contract drift between WP02's outside-table path-row format and the sibling canary's `status_parser.py` expectation of an indented `"Path"` row under each section header. The WP02 cycle 1/3 fix (commit `8df762dbb` on lane-b) introduces a `_print_boundary_section` helper that emits the section header followed by an indented `"  Path  <value>"` row directly, matching the parser's expected shape. The canary parser now consumes the output without error.

Verification (executed during the cycle 1/3 smoke test):

```python
from spec_kitty_e2e.identity_boundary.status_parser import parse_sync_status_check_output
text = open('/tmp/post-fix-sync-status.txt').read()
parse_sync_status_check_output(text)
# -> {'active_queue_db_path': '/Users/robert/.spec-kitty/queue.db', ...}
```

### Historical context (pre-cycle-1/3, retained for traceability)

The original B-1 failure mode was that WP02's earlier implementation pulled path rows *out* of the Rich Table to avoid width-driven ellipsis truncation, rendering them at top-level as `"Active queue path"` / `"Legacy queue path"`. The sibling canary parser, written before WP02 landed, walked rows of each section looking for a child `"Path"` row and raised `ValueError: missing required string field 'active_queue.Path'` because the row never appeared inside the section.

The WP02 cycle 1/3 fix preserves the no-truncation property (path rows are still rendered outside Rich's truncating column layout) while restoring the parser-compatible row shape (`<section>` header + indented `"Path"` row under it). See lane-b commit `8df762db` for the implementation.

---

## 10. Reproducibility

To re-run from a clean state:

```bash
# 1. Build the test CLI from local mission-branch state
cd /Users/robert/spec-kitty-dev/1122-1123-1124-43/spec-kitty
git worktree add /tmp/sk-merged-canary kitty/mission-unblock-sync-identity-boundary-canary-01KRZJ07
cd /tmp/sk-merged-canary
git merge --no-edit kitty/mission-unblock-sync-identity-boundary-canary-01KRZJ07-lane-a
git merge --no-edit kitty/mission-unblock-sync-identity-boundary-canary-01KRZJ07-lane-b
git merge --no-edit kitty/mission-unblock-sync-identity-boundary-canary-01KRZJ07-lane-c

# 2. Clone the sibling canary and check out PR #42
cd /tmp
git clone https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing.git canary-repo
cd canary-repo
gh pr checkout 42 --repo Priivacy-ai/spec-kitty-end-to-end-testing

# 3. Set up canary venv and install both the canary and the merged CLI
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
pip install -e /tmp/sk-merged-canary

# 4. Verify the three fixes are present
spec-kitty doctor restart-daemon --help                                          # WP03
python3 -c "from specify_cli.audit.shape_registry import is_mission_lifecycle_row; print('OK')"  # WP01
# (WP02 is exercised indirectly by scenario tests via `sync status --check`)

# 5. Run the canary
SPEC_KITTY_ENABLE_SAAS_SYNC=1 pytest tests/identity_boundary/ -v --capture=no -m sync_identity_boundary_deployed_dev 2>&1 | tee /tmp/canary-run.log

# 6. Run the full pytest gate on the merged state
cd /tmp/sk-merged-canary
python3 -m venv .venv-pytest && source .venv-pytest/bin/activate
pip install -e ".[test]"
pytest tests/ -q --timeout=60 -p no:cacheprovider 2>&1 | tee /tmp/full-pytest.log
```

Cleanup:

```bash
git worktree remove --force /tmp/sk-merged-canary   # from the spec-kitty repo root
# /tmp/canary-repo intentionally left in place for reviewer re-runs
```
