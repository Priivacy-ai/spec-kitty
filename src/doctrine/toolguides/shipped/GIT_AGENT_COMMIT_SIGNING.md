# Git Agent Commit Signing

Agent-authored commits should be unsigned.

## Required behavior

- Use `git commit --no-gpg-sign -m "..."` for normal agent-authored commits.
- Alternatively use `git -c commit.gpgsign=false commit -m "..."`.
- Do not assume GPG or SSH signing keys are configured in worktrees, CI, or ephemeral environments.

## Examples

```bash
git commit --no-gpg-sign -m "Fix local init self-copy regression"
git -c commit.gpgsign=false commit -m "Add doctrine template references"
```

## Avoid

- plain `git commit -m "..."` in automation where global signing may be enabled
- workflows that require interactive signing setup for agent-authored commits
