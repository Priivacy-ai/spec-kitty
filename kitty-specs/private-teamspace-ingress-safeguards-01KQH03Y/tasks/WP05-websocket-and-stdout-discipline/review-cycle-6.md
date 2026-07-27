---
affected_files: []
cycle_number: 6
mission_slug: private-teamspace-ingress-safeguards-01KQH03Y
reproduction_command:
reviewed_at: '2026-05-01T11:42:48Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP05
---

**Issue 1**: `tests/sync/test_strict_json_stdout.py` still does not make the subprocess test execute the in-tree `specify_cli` package. `_run_cli_isolated()` copies the current environment and runs `[sys.executable, "-m", "specify_cli", ...]`, but it never sets `PYTHONPATH` to this worktree's `src/` directory or otherwise installs/points the subprocess at the checked-out implementation. On this machine, the same command resolves to `/opt/homebrew/lib/python3.14/site-packages/specify_cli`, whose `sync/client.py` does not contain the WP05 changes. That means the strict-JSON subprocess test can pass while exercising a global/old package, leaving the WP05 regression unverified.

Fix: update `_run_cli_isolated()` or its caller to force the subprocess import path to the worktree under test, for example by prepending `str(_repo_root() / "src")` to `PYTHONPATH` in the subprocess environment. Add or adjust the test so it would fail if the subprocess imports anything outside the current repo's `src/specify_cli`.

Reproduction:

```bash
tmp=$(mktemp -d)
HOME="$tmp/home" \
XDG_CONFIG_HOME="$tmp/home/.config" \
SPEC_KITTY_HOME="$tmp/home/.kittify" \
SPEC_KITTY_ENABLE_SAAS_SYNC=1 \
python -c 'import specify_cli, pathlib; print(pathlib.Path(specify_cli.__file__).resolve())'
```

From this worktree, that prints `/opt/homebrew/lib/python3.14/site-packages/specify_cli/__init__.py`, not `.../lane-a/src/specify_cli/__init__.py`.

**Issue 2**: The subprocess strict-JSON test no longer proves the WP's requested failure mode. The WP asked for an end-to-end strict-JSON regression around `agent mission create ... --json` with sync forced into a diagnostic/failure path, or an equivalent subprocess path that proves a sync diagnostic stays off stdout. The current subprocess test runs `agent tasks status --json` with an empty isolated auth state; in that path stderr is empty, so the test only proves that a JSON command remains parseable when sync exits quietly. The in-process `WebSocketClient.connect()` test is useful and should stay, but it does not replace the subprocess contract because it bypasses CLI startup and the background/sync invocation path that originally corrupted strict JSON output.

Fix: keep the in-process stdout/stderr test, and strengthen the subprocess test so it runs against the in-tree package and observes a real sync diagnostic on stderr while stdout remains exactly parseable JSON. If `agent mission create --json` is impractical to isolate, use the narrowest CLI command that actually triggers the same sync/WebSocket diagnostic path, but document why it is equivalent and assert the diagnostic appears on stderr, not just that stdout lacks it.
