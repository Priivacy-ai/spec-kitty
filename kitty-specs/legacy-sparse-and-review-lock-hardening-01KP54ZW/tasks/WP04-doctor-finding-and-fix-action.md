---
work_package_id: WP04
title: Doctor Finding and --fix sparse-checkout Action
dependencies:
- WP02
- WP03
requirement_refs:
- FR-002
- FR-023
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
phase: Phase 1 — Doctor surface
agent: "claude:opus-4.6:implementer:implementer"
shell_pid: "96308"
history:
- timestamp: '2026-04-14T05:26:49Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/status/doctor.py
execution_mode: code_change
mission_id: 01KP54ZWEEPCC2VC3YKRX1HT8W
owned_files:
- src/specify_cli/status/doctor.py
- tests/integration/sparse_checkout/test_doctor_finding.py
- tests/integration/sparse_checkout/test_doctor_non_interactive.py
- tests/integration/sparse_checkout/test_remediation_primary.py
- tests/integration/sparse_checkout/test_remediation_primary_and_worktrees.py
- tests/integration/sparse_checkout/test_remediation_refuses_on_dirty.py
tags: []
wp_code: WP04
---

# Work Package Prompt: WP04 — Doctor Finding and `--fix sparse-checkout` Action

## Implementation Command

```bash
spec-kitty agent action implement WP04 --agent <your-agent-name> --mission 01KP54ZW
```

Depends on WP02 and WP03. Rebase onto the lane where those land.

---

## Branch Strategy

- **Planning branch**: `main`
- **Final merge target**: `main`
- Lane allocation by `finalize-tasks`; resolve from `lanes.json`.

---

## Objective

Surface the sparse-checkout condition through `spec-kitty doctor`, offer the remediation action through `spec-kitty doctor --fix sparse-checkout`, and produce correct behaviour in both interactive TTY and CI / non-interactive environments.

---

## Context

- Quickstart Flow 1 is the acceptance spec for this WP: the exact messages and sequence the user sees.
- FR-002 (doctor finding), FR-023 (CI / non-interactive handling), SC-001 (one-command remediation).
- This WP is the only caller of `remediate()` from WP03. Preflights in WP05 only emit the preflight error; they do not call remediation.

---

## Subtask Guidance

### T016 — Doctor finding surfacing sparse-checkout scan

**Files**: `src/specify_cli/status/doctor.py`

**What**: Add a new finding to `doctor` that imports `scan_repo()` from `specify_cli.git.sparse_checkout` and formats output per quickstart Flow 1.

Match the existing doctor finding conventions in `doctor.py` (inspect the file before implementing). If the file uses a `Finding` dataclass pattern, instantiate one; if it uses functions returning `(name, status, message)` tuples, follow that style. Do not introduce a new output format.

Finding content:
- Name: `"sparse_checkout"` (snake_case; matches CLI `--fix <name>` convention).
- Status: emit `⚠` warning level when `report.any_active` is True; no finding otherwise.
- Plain-language explanation that sparse-checkout was removed in v3.x but state lingers in user repos.
- List of affected paths (primary + each active worktree).
- Pointer to `spec-kitty doctor --fix sparse-checkout`.
- Link to Priivacy-ai/spec-kitty#588 for context.

---

### T017 — `doctor --fix sparse-checkout` action

**Files**: `src/specify_cli/status/doctor.py`

**What**: Wire the `--fix sparse-checkout` subcommand / flag (follow whatever dispatch pattern doctor already uses for other fix actions). Behaviour:

1. Call `scan_repo(repo_root)`. If `not report.any_active`, print "No sparse-checkout state to remediate." and exit 0.
2. Determine interactive mode via a helper:
   ```python
   def _is_interactive_environment() -> bool:
       if not sys.stdin.isatty():
           return False
       for var in ("CI", "GITHUB_ACTIONS", "GITLAB_CI", "BUILDKITE", "JENKINS_URL", "CIRCLECI"):
           if os.environ.get(var, "").lower() in ("true", "1", "yes"):
               return False
       return True
   ```
3. If non-interactive: print the finding plus a one-line remediation pointer and exit non-zero. Do NOT run remediation. This matches FR-023 / Quickstart Flow 1 CI behaviour.
4. If interactive:
   - Print the step-by-step plan (per Quickstart Flow 1).
   - Prompt once: `"Proceed? [y/N]"`. A non-`y` response aborts with exit 0 and a "no changes made" message.
   - On `y`, call `remediate(report, interactive=False, confirm=None)` — we already got consent for the whole plan.
   - Print one line per path with the `✓ / ✗` marker.
   - Exit 0 iff `report.overall_success`.

Error handling:
- If remediation raises unexpectedly, print `error_detail` for the failing path and exit non-zero.
- If the dirty-tree refusal fires, surface the per-path `dirty_before_remediation` flags and exit non-zero with the "commit or stash" message from Quickstart Flow 1.

---

### T018 — Integration tests [P]

**Files**: `tests/integration/sparse_checkout/test_doctor_finding.py`, `test_doctor_non_interactive.py`, `test_remediation_primary.py`, `test_remediation_primary_and_worktrees.py`, `test_remediation_refuses_on_dirty.py` (all new).

Each test uses a temp git repo fixture. Cases:

- `test_doctor_finding.py`:
  - Doctor on clean 3.x-born repo: no sparse-checkout finding emitted.
  - Doctor on sparse-configured repo: finding emitted with expected text and path list.
  - Doctor on sparse-configured repo with 2 sparse-inherited worktrees: finding lists primary + both worktrees.

- `test_doctor_non_interactive.py`:
  - With `stdin.isatty()=False` (mocked): `doctor --fix sparse-checkout` prints remediation pointer and exits non-zero without mutating state.
  - With `CI=true` env var set (real `isatty` can be true): same behaviour.

- `test_remediation_primary.py`:
  - Interactive `y` response: primary remediated; `git config --get core.sparseCheckout` is empty; pattern file absent; `git status` clean.

- `test_remediation_primary_and_worktrees.py`:
  - Interactive `y` response with 2 inherited worktrees: primary + both worktrees cleaned up.

- `test_remediation_refuses_on_dirty.py`:
  - Primary dirty: refusal message printed; no state changed.
  - Worktree dirty (primary clean): still refuses (all-or-nothing); no state changed.

Run with `pytest tests/integration/sparse_checkout/ -v`.

---

## Definition of Done

- [ ] Doctor emits the new finding on sparse-configured repos and is silent on clean ones.
- [ ] `spec-kitty doctor --fix sparse-checkout` runs remediation in interactive mode.
- [ ] Non-interactive mode prints a remediation pointer and exits non-zero without mutating state.
- [ ] All 5 integration test files exist and pass.
- [ ] Clean-repo regression tests still pass (no regression in unrelated doctor findings).
- [ ] `pytest tests/integration/sparse_checkout/` passes.
- [ ] `mypy --strict src/specify_cli/status/doctor.py` passes.

## Risks

- **Doctor output contract**: doctor's output is scraped by some users' scripts. Adding a new finding is safe; reordering existing findings is not. Append the new finding at the end of the existing list rather than reordering.
- **Prompt capture in tests**: `pytest` prompt capture needs explicit `input` monkeypatch. Use `monkeypatch.setattr("builtins.input", lambda _: "y")`.
- **CI env-var detection**: the list of recognized CI env vars should be conservative — false positives (flagging a local session as CI) would prevent the user from remediating. Use only well-known ones.

## Reviewer Guidance

- Verify the finding text matches the Quickstart Flow 1 template (mission spec acceptance).
- Verify no remediation happens in non-interactive mode.
- Verify existing doctor findings are not reordered.
- Verify `--fix sparse-checkout` is the ONLY way remediation runs; no other CLI path calls `remediate()`.

## Activity Log

- 2026-04-14T06:55:03Z – claude:opus-4.6:implementer:implementer – shell_pid=96308 – Started implementation via action command
