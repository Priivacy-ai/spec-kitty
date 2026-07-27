# Implementation Plan: Op Record Git Durability

**Branch**: `main` | **Date**: 2026-06-05 | **Spec**: [spec.md](spec.md)  
**Mission**: op-records-git-durability-01KTB49K (`mid8`: 01KTB49K)  
**Input**: [kitty-specs/op-records-git-durability-01KTB49K/spec.md](spec.md)

---

## Branch Contract (repeated per workflow requirement)

- **Current branch at plan start**: `main`
- **Planning/base branch**: `main`
- **Final merge target**: `main`
- **Branch matches target**: yes

---

## Summary

Move Op record storage from `.kittify/events/profile-invocations/` (gitignored) to `kitty-ops/` (git-tracked). Wire an auto-commit after every successful Op completion, guarded by an orphan invariant (started-but-never-completed Ops are never committed). Add `mission_id` and `wp_id` optional fields to `InvocationRecord` for timeline correlation. Fix the zero-persistence gap in `do_cmd._build_executor`. This is Step 1 of 3 from issue #1688; SaaS propagator replacement and module rename are out of scope.

---

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: pydantic v2 (InvocationRecord model), python-ulid (ULID generation), subprocess/git (auto-commit), stdlib pathlib / json / datetime  
**Storage**: `kitty-ops/` JSONL files on the local filesystem, git-tracked  
**Testing**: pytest (90%+ coverage on changed modules), mypy --strict, integration tests require git repo fixture  
**Target Platform**: Cross-platform (Linux, macOS, Windows 10+)  
**Project Type**: Single Python CLI package (`specify_cli`)  
**Performance Goals**: Op write + commit latency must not add visible delay beyond what `safe_commit` already takes for status commits  
**Constraints**: No `.gitignore` changes; no external dependencies added; `InvocationRecord` model must stay frozen (Pydantic v2 `frozen=True`)

---

## Charter Check

*Gate: must pass before Phase 0 research. Re-check after Phase 1 design.*

| Check | Status | Notes |
|-------|--------|-------|
| DIRECTIVE_003: Material decisions documented | ✅ | Commit strategy decision (direct git vs `safe_commit`) documented in research.md |
| DIRECTIVE_010: Implementation faithful to spec | ✅ | Plan covers all 10 FR items |
| NFR: 90%+ test coverage for new code | ✅ Planned | 7 test scenarios mapped in data-model.md |
| NFR: mypy --strict passes | ✅ Planned | New fields use `str \| None` with Pydantic default |
| No `.gitignore` changes (C-001) | ✅ | `kitty-ops/` not currently listed; tracked by default |
| Step 2 / Step 3 out of scope (C-003, C-004) | ✅ | Propagator and module rename excluded from all work packages |

---

## Project Structure

### Documentation (this feature)

```
kitty-specs/op-records-git-durability-01KTB49K/
├── plan.md              # This file
├── research.md          # Phase 0 findings
├── data-model.md        # Field contracts and test matrix
├── contracts/           # JSONL event schema, commit message contract
└── tasks.md             # Phase 2 output (/spec-kitty.tasks)
```

### Source Code (affected files)

```
src/specify_cli/invocation/
├── writer.py            # EVENTS_DIR, INDEX_PATH constants + _append_to_index fix
├── lifecycle.py         # LIFECYCLE_LOG_RELATIVE_PATH constant
├── record.py            # InvocationRecord: add mission_id, wp_id fields + MVTP update
├── executor.py          # complete_invocation(): wire auto-commit after write_completed()
└── propagator.py        # PROPAGATION_ERRORS_PATH path (move to kitty-ops/)

src/specify_cli/cli/commands/
└── do_cmd.py            # _build_executor: no change needed (executor owns the commit)

src/specify_cli/doctor/
└── ops.py               # NEW: spec-kitty doctor ops orphan listing

tests/specify_cli/invocation/
├── test_writer.py       # Add: EVENTS_DIR resolves to kitty-ops/, index in kitty-ops/
├── test_executor.py     # Add: complete_invocation wires git commit; orphan not committed
├── test_record.py       # Add: mission_id/wp_id field presence, null for standalone
└── test_doctor_ops.py   # NEW: orphan listing via doctor ops
```

---

## Key Implementation Decision: Commit Mechanism

`safe_commit` (in `src/specify_cli/git/commit_helpers.py`) requires a `worktree_root`
parameter and refuses commits to protected branches (including `main`). Op commits
must work from **any** invocation context — including standalone `ask`/`advise`/`do`
on `main`. Therefore Op auto-commits use direct git subprocess calls rather than
`safe_commit`. See `research.md §Commit Strategy` for full rationale.

The commit sequence:
```
git -C <repo_root> add -- kitty-ops/<op_id>.jsonl kitty-ops/ops-index.jsonl
git -C <repo_root> commit --no-verify -m "op(<profile_id>): <action> [<op_id[:8]>]"
```

`--no-verify` skips pre-commit hooks. This is intentional: Op JSONL files are
audit-trail records, not source code, so hook enforcement (e.g. ruff, mypy)
is not applicable. The same pattern is used by `safe_commit` for bookkeeping
commits in lane worktrees.

This is consistent with how planning commands (specify, plan, tasks) commit
their artifacts to main — they also use direct git, not `safe_commit`.

---

## Complexity Tracking

| Concern | Why Acceptable |
|---------|----------------|
| Direct git commit instead of `safe_commit` | `safe_commit` is a *status mutation* guard designed for lane-worktree bookkeeping commits. Op records are audit trail artifacts, not mission status — the same class as `kitty-specs/` planning artifacts which also commit directly. |

---

## Phase 0 Output

See [research.md](research.md) — all technical unknowns resolved.

## Phase 1 Output

See [data-model.md](data-model.md) and [contracts/](contracts/).

---

## Branch Contract (final report)

- **Current branch**: `main`
- **Planning/base branch**: `main`
- **Final merge target for completed changes**: `main`

**Next step**: `/spec-kitty.tasks`
