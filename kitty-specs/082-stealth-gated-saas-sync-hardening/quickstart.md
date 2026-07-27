# Quickstart — 082 Stealth-Gated SaaS Sync Hardening

**Audience**: Operators verifying the mission's three core invariants on a real machine after implementation lands.

**Time required**: ~10 minutes.

**Pre-requisite**: A clean spec-kitty install at the new version (built from this branch). No prior `SPEC_KITTY_ENABLE_SAAS_SYNC` set in your shell.

---

## Scenario 1 — Customer Machine (Stealth Default)

**Goal**: Verify that without the env var, the hosted tracker surface is invisible and no network or daemon activity occurs.

```bash
# Make sure the env var is NOT set
unset SPEC_KITTY_ENABLE_SAAS_SYNC

# 1. Tracker group must be hidden in --help
spec-kitty --help | grep -i tracker
# Expect: NO output. Exit code 1 from grep is the success signal.

# 2. Direct invocation must fail closed
spec-kitty tracker --help
# Expect: typer "no such command: tracker" style error.
# Expect: NO network requests. NO daemon process.

# 3. Confirm the daemon is not running
ls ~/.spec-kitty/sync-daemon* 2>/dev/null
# Expect: no sync-daemon state file or lock file.

# 4. A local-only command must succeed without touching the network
spec-kitty status
# Expect: prints local mission status. NO outbound network. NO daemon spawn.
```

**Pass criteria**:
- `tracker` is absent from `--help`.
- `spec-kitty tracker` exits non-zero with the typer "no such command" error.
- No `sync-daemon` lock or state file is created.
- `spec-kitty status` works without any network call (verify with `lsof -i` or by disconnecting WiFi).

---

## Scenario 2 — Internal Tester Machine (Enabled Mode, Per-Prerequisite Failures)

**Goal**: Verify that with the env var set, the hosted surface is visible and that each missing prerequisite produces a specific, actionable failure message.

```bash
# Opt in
export SPEC_KITTY_ENABLE_SAAS_SYNC=1

# 1. The tracker group is now visible
spec-kitty --help | grep -i tracker
# Expect: "tracker  Hosted SaaS tracker commands" (or similar).

# 2. With NO auth, a hosted command fails at MISSING_AUTH
rm -f ~/.spec-kitty/auth.json   # ensure no token
spec-kitty tracker status
# Expect stdout (stable wording):
#   No SaaS authentication token is present.
#
#   Run `spec-kitty auth login`.
# Expect exit code 1.

# 3. With auth but no host config, fail at MISSING_HOST_CONFIG
spec-kitty auth login   # follow the dev-saas flow
# Manually clear the host:
python -c "
import tomllib, pathlib
p = pathlib.Path.home() / '.spec-kitty/config.toml'
data = tomllib.loads(p.read_text())
data.setdefault('sync', {})['server_url'] = ''
p.write_text(tomllib.dumps(data) if hasattr(tomllib, 'dumps') else '[sync]\nserver_url = \"\"\n')
"
spec-kitty tracker status
# Expect: "No SaaS host URL is configured." + next action.

# 4. With auth + host but no mission binding, fail at MISSING_MISSION_BINDING
# Restore the host first
spec-kitty config set sync.server_url https://spec-kitty-dev.fly.dev
cd /tmp && mkdir empty-repo && cd empty-repo && git init
spec-kitty tracker status
# Expect: "No tracker binding exists for feature ..." + "Run `spec-kitty tracker bind`."

# 5. Bind the mission, then a remote command runs end-to-end
spec-kitty tracker bind
spec-kitty tracker sync run
# Expect: command runs against the dev SaaS at https://spec-kitty-dev.fly.dev.
```

**Pass criteria**:
- `--help` lists `tracker`.
- Each artificial failure produces a **different** message that names the missing prerequisite by name.
- Each failure message includes a single concrete `next_action` line.
- The happy-path `sync run` reaches the dev SaaS.

---

## Scenario 3 — Manual Daemon Policy

**Goal**: Verify that `sync.background_daemon = "manual"` prevents auto-start even on enabled internal machines, and that hosted commands explain the manual-mode behavior.

```bash
export SPEC_KITTY_ENABLE_SAAS_SYNC=1

# 1. Set policy to manual
spec-kitty config set sync.background_daemon manual

# 2. Help and local-only commands still do not start the daemon
spec-kitty --help
spec-kitty status
ls ~/.spec-kitty/sync-daemon.lock 2>/dev/null
# Expect: no lock file.

# 3. A REMOTE_REQUIRED tracker command yields the manual-mode message
spec-kitty tracker sync run
# Expect stdout (stable wording):
#   Background sync is in manual mode (`[sync].background_daemon = "manual"`).
#   Run `spec-kitty sync run` to perform a one-shot remote sync.
# Expect exit code 0 (this is not an error — the operator chose this).
ls ~/.spec-kitty/sync-daemon.lock 2>/dev/null
# Expect: still no lock file.

# 4. Switch back to auto and confirm the daemon spawns on a remote command
spec-kitty config set sync.background_daemon auto
spec-kitty tracker sync run
ls ~/.spec-kitty/sync-daemon.lock
# Expect: lock file now exists; daemon is running.
```

**Pass criteria**:
- In `manual` mode, no daemon spawns even after a `REMOTE_REQUIRED` command.
- The CLI prints the manual-mode message and exits 0.
- Switching back to `auto` restores normal startup.

---

## Negative Verification (Cross-Scenario)

After every scenario, run:

```bash
# 1. Tracker package was not modified
pip show spec-kitty-tracker | grep Version
# Expect: 0.3.0 (unchanged from before this mission)

# 2. The two BC shims still work for any third-party caller
python -c "from specify_cli.tracker.feature_flags import is_saas_sync_enabled; print(is_saas_sync_enabled())"
python -c "from specify_cli.sync.feature_flags import is_saas_sync_enabled; print(is_saas_sync_enabled())"
# Expect: both print True or False matching the current env state.
```

---

## Cleanup

```bash
unset SPEC_KITTY_ENABLE_SAAS_SYNC
spec-kitty config set sync.background_daemon auto
rm -rf /tmp/empty-repo
```

---

## What This Quickstart Validates Against the Spec

| Spec acceptance scenario | Quickstart step |
|---|---|
| US1 / SC-001: Customers do not see hosted features | Scenario 1, steps 1–3 |
| US2 / SC-002: Internal testers see and use hosted features | Scenario 2, steps 1, 5 |
| US3 / NFR-002: Per-prerequisite failure messages | Scenario 2, steps 2–4 |
| US4 / SC-003: Daemon respects intent + policy | Scenario 3, all steps |
| C-002: Tracker package is not modified | Negative Verification, step 1 |
