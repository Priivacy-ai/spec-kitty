# Contract: target visibility in `auth login` / `auth status`

Both commands print, before any network activity, one line of the form:

```
Team Kitty target: https://team.spec-kitty.ai (packaged default)
Team Kitty target: https://spec-kitty-dev.fly.dev (config.toml [team_kitty] server_url)
Team Kitty target: https://x.example (SPEC_KITTY_SAAS_URL)
```

- `auth status` and `auth whoami` reuse `_auth_saas_target.print_saas_target`; `auth login` calls the same printer.
- The existing issuer-mismatch warning is unchanged.
- `--json` variants carry `target.url` and `target.source` fields; no token or session value appears in any output (NFR-004).
- The retired "Set SPEC_KITTY_SAAS_URL … and try again" remediation text is removed; the only remaining remediation is the split-brain message.
