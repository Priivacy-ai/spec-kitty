# NFR-001 Release-Stability Smoke Recipe

**Mission**: quality-devex-hardening-3-2-01KRJGKH
**Requirement**: NFR-001 — post-merge `main` MUST support a fresh-user
`init → specify → plan → tasks → implement → review → merge → PR` cycle
without manual state repair, prompt repair, or branch reconstruction.
**Authored by**: WP10 (claude:sonnet:python-pedro:implementer running as
reviewer-renata)
**Audience**: Operator (HiC). The cycle takes 20–30 minutes of interactive
command sequencing, which exceeds a sub-agent's autonomous WP session.
**Result home**: paste outcomes into `mission-review.md` under the
"NFR-001 Smoke Results" section after execution.

---

## Prerequisites

- The mission has merged to `fix/quality-check-updates` (or `main` if
  the operator promoted the branch).
- A fresh `pipx` environment, OR a throwaway venv, OR a fresh user account.
  Do not reuse an existing developer machine state for this smoke.
- `gh` CLI authenticated against the upstream remote (needed for the
  final PR step).
- A throwaway empty directory created for the smoke run.

## Pass / Fail Rubric

- **PASS**: every step exits 0; no manual repair commands are issued
  between steps; the final `gh pr create` opens a PR without conflict
  resolution; no `spec-kitty doctor` invocation is required.
- **FAIL**: any step exits non-zero, requires `spec-kitty doctor --fix`
  or equivalent manual repair, requires branch surgery, or fails to
  produce the artifact the next step depends on.

If any step fails, **stop the smoke**, capture the exit code and stderr
in the results table below, and surface the failure to the mission-review
"Open Items" section. NFR-001 fails — the mission cannot be marked
release-ready.

## Recipe

Run all commands from the throwaway directory unless otherwise noted.

### Step 0 — Install fresh CLI

```bash
mkdir -p ~/nfr-001-smoke && cd ~/nfr-001-smoke
pipx install --force spec-kitty-cli  # or the post-merge tag/branch tarball
spec-kitty --version
```

Capture the installed version. If `pipx install` fails, FAIL.

### Step 1 — `init`

```bash
spec-kitty init smoke-test --agent claude
cd smoke-test
```

Expected: a `.kittify/` directory exists, a `.claude/` directory exists,
and `git status` is clean (modulo gitignored artifacts).

### Step 2 — `specify`

```bash
spec-kitty specify "Hello world: print 'hello, world' from the CLI"
```

Expected: a `kitty-specs/<slug>/spec.md` file lands; no prompt for manual
repair; exit 0.

### Step 3 — `plan`

```bash
spec-kitty plan
```

Expected: a `kitty-specs/<slug>/plan.md` file lands; exit 0.

### Step 4 — `tasks`

```bash
spec-kitty tasks
spec-kitty agent mission finalize-tasks
```

Expected: `tasks.md` and `tasks/WP*.md` exist; finalize-tasks exits 0 and
commits the finalized task set.

### Step 5 — `implement`

```bash
spec-kitty implement WP01
```

The recipe assumes WP01 is trivially implementable by the agent. The
operator may choose to run an agent inside the resolved workspace
manually if needed; that is fine. The smoke is about state-machine
correctness, not about the agent's ability to author code.

Expected: a workspace resolves (lane-based or per-WP); the worktree
exists at the printed path.

### Step 6 — `review`

```bash
# After WP01 implementation lands and the WP is moved to for_review:
spec-kitty review WP01
```

Expected: a review surface renders without errors; the operator can
approve the WP. Approval may be manual.

### Step 7 — `merge`

```bash
spec-kitty merge
```

Expected: merge completes without conflict, without requiring
`spec-kitty merge --resume` or `--abort`. If a stale-lane auto-rebase
attempt was triggered by WP08's classifier, it must complete without
manual conflict resolution.

### Step 8 — open PR

```bash
git push -u origin <feature-branch>
gh pr create --fill --base main
```

Expected: `gh pr create` returns a PR URL with no manual conflict
resolution intervening.

---

## Results Table (operator fills in)

| Step | Command | Exit code | Manual repair? | Notes |
|---|---|---|---|---|
| 0 | `pipx install --force spec-kitty-cli` | | | |
| 1 | `spec-kitty init smoke-test --agent claude` | | | |
| 2 | `spec-kitty specify "..."` | | | |
| 3 | `spec-kitty plan` | | | |
| 4 | `spec-kitty tasks` + finalize | | | |
| 5 | `spec-kitty implement WP01` | | | |
| 6 | `spec-kitty review WP01` | | | |
| 7 | `spec-kitty merge` | | | |
| 8 | `git push` + `gh pr create` | | | |

**Overall result**: ☐ PASS  ☐ FAIL

**Operator signature / date**: ___________________________________________

**Notes** (if FAIL — list manual repair steps required and which step
surfaced them):

```
(operator entry)
```

---

## Cleanup

After PR is opened (or smoke fails and is documented):

```bash
cd ..
rm -rf ~/nfr-001-smoke   # tear down the throwaway directory
pipx uninstall spec-kitty-cli  # if installed via pipx in step 0
```
