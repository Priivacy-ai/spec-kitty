---
affected_files: []
cycle_number: 2
mission_slug: mvp-cli-sync-boundary-completion-01KRX11M
reproduction_command:
reviewed_at: '2026-05-18T10:11:23Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP03
review_artifact_override_at: "2026-05-18T10:24:15Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP03"
review_artifact_override_reason: "Cycle 2 review approved (codex verdict): FR-004 fixed in both --check and --check --json (exits 2 with auth_required=true); NFR-004 render worst case 24 lines at 80 cols; 47 focused tests pass."
---

**Issue 1: `sync status --check` and `--check --json` do not apply the auth-required refusal contract.**

Acceptance impact: FR-004 / `contracts/sync-status-output.md`.

The status-output contract says `SPEC_KITTY_ENABLE_SAAS_SYNC=1` with no authenticated identity exits `2`, and `--check --json` should emit the preflight-shaped refusal result enriched with status fields. The implementation short-circuits JSON through `build_boundary_failure_set()` only (`src/specify_cli/cli/commands/sync.py` `_emit_status_check_json`), so auth absence is ignored. The human `--check` path also does not include auth absence in `_build_boundary_check_failures`; instead it exits through logged-out recovery with code `4` before the boundary gate runs.

Repro from this worktree:

```bash
tmpdir=$(mktemp -d /private/tmp/sk-review-home.XXXXXX)
HOME="$tmpdir" SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run spec-kitty sync status --check --json
# Actual: exit 0, {"ok": true, "exit_code": 0, "foreground": {"server_url": null, "team_or_user": null}, ...}
# Expected: exit 2 with ok=false / exit_code=2 because SaaS sync is enabled and auth is absent.

tmpdir=$(mktemp -d /private/tmp/sk-review-home.XXXXXX)
HOME="$tmpdir" SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run spec-kitty sync status --check
# Actual: exit 4 via logged_out_on_connected_teamspace.
# Expected: exit 2 per the status-output contract, naming the failing boundary/auth category.
```

Fix direction: make the status check paths compose `run_preflight(..., require_auth=is_saas_sync_enabled())` or otherwise layer the same auth-required condition as `PreflightResult`. For human `--check`, ensure the boundary/status gate owns the exit code `2` rather than `handle_unauthenticated_with_teamspace` exiting `4` first. For JSON, use `PreflightResult.to_dict()` data, enriched with the required identity-boundary sections, so `ok` and `exit_code` match the preflight contract.

**Issue 2: worst-case refusal rendering exceeds the NFR-004 25-line budget at a normal 80-column terminal.**

Acceptance impact: NFR-004.

`PreflightResult.render()` can render one remediation line per unique mismatch category, plus orphan, legacy, and auth remediation. With the documented worst case of six mismatches and three orphan records, an 80-column console produces 28 visible lines. That violates the NFR-004 requirement that refusal output be readable in one terminal screen and `<= 25` visible lines.

Repro from this worktree using the real render function and the real remediation hints:

```bash
.venv/bin/python - <<'PY'
import io
from rich.console import Console
from specify_cli.sync.preflight import PreflightResult, OwnerMismatch
from specify_cli.sync.owner import DaemonOwnerRecord

hints = {
    "daemon_package_version": "Run `spec-kitty doctor restart-daemon` to restart the daemon at the foreground version.",
    "daemon_executable_path": "Run `spec-kitty doctor restart-daemon` to restart the daemon at the foreground source.",
    "daemon_source_path": "Run `spec-kitty doctor restart-daemon` to restart the daemon at the foreground source.",
    "daemon_server_url": "Reauthenticate (`spec-kitty auth login`) or restart the daemon against the matching server.",
    "daemon_team_or_user": "Switch to the foreground team/user (`spec-kitty auth switch ...`) or restart the daemon.",
    "daemon_queue_db_path": "Run `spec-kitty doctor restart-daemon`; the scoped queue path changed.",
}
mismatches = tuple(
    OwnerMismatch(field=f, foreground_value=f"fg-{f}", daemon_value=f"daemon-{f}", remediation_hint=hints[f])
    for f in hints
)
orphan = DaemonOwnerRecord(
    pid=99999, port=9400, token="t", package_version="3.2.0",
    executable_path="/bin/python", source_checkout_path="/src",
    server_url="https://example.com", auth_principal=None, auth_team=None,
    auth_scope=None, queue_db_path="/tmp/queue.db",
    started_at="2026-05-18T08:00:00+00:00",
)
result = PreflightResult(
    ok=False, mismatches=mismatches, orphan_records=(orphan, orphan, orphan),
    legacy_event_rows=4, legacy_body_upload_rows=1,
    auth_present=False, auth_required=True,
)
buf = io.StringIO()
result.render(Console(file=buf, width=80, force_terminal=False, color_system=None))
print(len(buf.getvalue().splitlines()))
PY
# Actual: 28
# Expected: <= 25
```

Fix direction: compress the remediation section for the worst case. For example, group all daemon-field mismatches under one restart-daemon remediation and keep auth / orphan / legacy as short single-line hints, then assert the budget at 80 columns using the actual production hints.

**Verification notes**

The required targeted pytest command could not complete in this sandbox with the default `uv` cache:

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest tests/sync/test_sync_status_boundary_check.py tests/sync/test_daemon_owner_record.py -q
# error: failed to open file `/Users/robert/.cache/uv/sdists-v6/.git`: Operation not permitted
```

Retrying with a sandbox-local cache got past the filesystem denial but failed during test import because `spec_kitty_events.normalize_event_id` was unavailable in that recreated environment. The mypy DoD command similarly fails under the sandbox-local cache with existing package/stub import errors. Please rerun the WP verification commands in the normal developer environment after fixing the two blocking issues above.
