# Quickstart / Validation: Specify on Protected Primary

These are the acceptance walkthroughs an implementer/reviewer runs to confirm the mission. They map
directly to the Success Criteria.

## V1 — The kentonium3 repro completes on a protected primary (SC-001, US1)

On a repo whose primary is named `main`, staying on the primary:

```bash
# 1. branch context confirms protected primary
spec-kitty agent mission branch-context --json        # current_is_primary: true, target_branch: main

# 2. create mission (mints coord branch; coord worktree NOT yet materialized — expected)
spec-kitty agent mission create "demo" --pr-bound --branch-strategy already-confirmed --json

# 3. author a substantive spec.md (>=1 real FR row)

# 4. THE FIX: sanctioned spec commit — must SUCCEED with no manual git, no env hatch
spec-kitty safe-commit --message "Add spec for demo" kitty-specs/<dir>/
```

**Pass:** step 4 succeeds; the coordination worktree is materialized at the commit boundary and
`spec.md` is committed on `kitty/mission-demo-<mid8>`; the working primary is clean. **No**
`SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS`, **no** `git checkout -b`, **no** manual git.

## V2 — Owner marks the primary unprotected → direct commit (SC-002, US2)

```yaml
# .kittify/config.yaml
protection:
  protected_branches: []      # owner opts the primary out
```

```bash
spec-kitty safe-commit --message "Add spec for demo" kitty-specs/<dir>/
```

**Pass:** the commit lands **directly on `main`** (the documented runbook behavior) with no
coordination worktree created.

## V3 — Default repo unchanged (NFR-004)

With **no** `protection:` block, on a non-`main` feature branch:

```bash
spec-kitty safe-commit --message "..." <files>     # commits directly, exactly as today
```

**Pass:** byte-identical behavior to current; `{main, master}` remain protected; full regression suite green.

## V4 — Single-authority guard (FR-010)

```bash
pytest tests/architectural/<single-resolver-guard>.py
```

**Pass:** the guard is green; introducing a new direct `protected_branches(repo_root)` /
`{"main","master"}` protection decision outside the resolver allowlist turns it RED.

## V5 — #1718 create-window non-regression (NFR-001)

```bash
pytest <create-window invariant tests>
```

**Pass:** during the create→first-write window (coord branch declared, worktree not yet materialized),
reads still resolve to the primary; materialization triggers only at the commit boundary.

## V6 — Runbook ↔ guard agreement (SC-005)

Read `src/doctrine/missions/mission-steps/software-dev/specify/prompt.md`: its spec-commit instruction
on a protected primary matches what the guard permits (no instruction to run a refused command).
