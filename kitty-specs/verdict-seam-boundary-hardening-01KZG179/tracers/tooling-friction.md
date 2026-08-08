# Tracer: Tooling Friction — verdict-seam-boundary-hardening-01KZG179

> Every place the tooling fought us. Append during implementation. Feeds the tooling-gap backlog at mission close.

## Planning phase

- **`spec-commit` no-op on first-spec-of-a-fresh-mission.** `spec-kitty spec-commit --mission <slug> spec.md` returned `{"success": true, "committed": false, ...}` ("Spec artifact(s) unchanged, no commit needed") even though `git add spec.md && git diff --cached` showed a real 166-line diff and the file was untracked. Traced through `spec_commit_cmd → commit_for_mission (kind=SPEC) → _commit_partition_group → safe_commit`: for an unprotected primary it should be a direct `git add`+commit in the repo root, but `safe_commit`'s pre-commit stash/restore dance returned "unchanged" and, when files were pre-staged, mangled the index (left a dangling `spec-kitty-safe-commit:<uuid>` stash and "Index was not unstashed"). **Workaround:** direct `git commit` on the unprotected feature branch (functionally identical to the SPEC-kind path). **→ File upstream gap.**
- **`pre-commit` hook pinned a dead interpreter.** `.git/hooks/pre-commit` had `exec ".../.claude/worktrees/agent-a70a2fd890d02ddc9/.venv/bin/python3" -m specify_cli.policy.commit_guard_hook` — that agent worktree venv was gone (`exec: ... not found`), so every commit failed. **Fix:** repointed the hook to the repo-local `.venv/bin/python` (an editable install resolving to repo source). Matches the known "commit hook pins interpreter" footgun — the installer should pin a stable interpreter, not an ephemeral agent-worktree venv. **→ File upstream gap.**

## Implementation phase

_(append as encountered)_
