# Quickstart: verifying the launch defaults by hand

```bash
# 1. Fresh machine, nothing configured
export SPEC_KITTY_HOME=$(mktemp -d)
spec-kitty status            # completes; prints one sign-in hint on stderr
spec-kitty status            # no hint the second time
spec-kitty status --json     # clean JSON, no hint

# 2. Where would hosted traffic go?
spec-kitty auth status       # "Team Kitty target: https://team.spec-kitty.ai (packaged default)"

# 3. Point at the dev deployment via config
printf '[team_kitty]\nserver_url = "https://spec-kitty-dev.fly.dev"\n' > "$SPEC_KITTY_HOME/config.toml"
spec-kitty auth status       # "... (config.toml [team_kitty] server_url)"

# 4. Environment override wins; disagreement fails closed
SPEC_KITTY_SAAS_URL=https://spec-kitty-dev.fly.dev spec-kitty auth status   # environment
SPEC_KITTY_SAAS_URL=https://other.example spec-kitty auth status            # split-brain error naming both

# 5. Sign in, move a work package from an owned checkout, watch the team board
spec-kitty auth login
spec-kitty implement WP01 --owned-checkout /path/to/owned
spec-kitty agent tasks move-task WP01 --to for_review --owned-checkout /path/to/owned
# the moment appears in Team Kitty within the next Pulse poll (≤ 60 s)

# 6. Sign out: hosted behavior is off, local work continues
spec-kitty auth logout
spec-kitty agent tasks move-task WP01 --to in_review   # completes; no hosted request
```

Retired names (`SPEC_KITTY_ENABLE_SAAS_SYNC`, `SPEC_KITTY_SYNC_*`, `[sync]`) have no effect anywhere.
