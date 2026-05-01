# Quickstart — Verifying CLI Private Teamspace Ingress Safeguards

**Mission**: `private-teamspace-ingress-safeguards-01KQH03Y`
**Audience**: operator / engineer verifying the fix locally after implementation merges.

---

## TL;DR

After this mission lands, a CLI session containing only shared Teamspaces will:

1. Make exactly one `GET /api/v1/me` per CLI process.
2. Never send a `POST /api/v1/events/batch/` with `X-Team-Slug` set to a shared team.
3. Never post a shared team id to `/api/v1/ws-token`.
4. Emit a structured `direct ingress skipped: …` warning to stderr with category, rehydrate flag, and endpoint.
5. Allow `spec-kitty agent mission create --json` and other local commands to exit `0` and produce strict-JSON-parseable stdout.

---

## Prerequisites

- The feature branch is merged and a fresh `spec-kitty` is installed.
- You have a real auth session on disk (run `spec-kitty auth status` first).
- You have an httpx-traffic capture tool such as `mitmproxy` or are willing to read CLI logs at INFO/WARNING level.
- Sync side-effects are enabled for the smoke commands:

  ```bash
  export SPEC_KITTY_ENABLE_SAAS_SYNC=1
  ```

---

## Smoke 1 — Healthy session (regression check)

Goal: confirm Scenario 1 — when the session has a Private Teamspace, the change is byte-identical.

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=1 \
  spec-kitty agent mission create cli-private-team-smoke-healthy --json \
  > /tmp/healthy.json 2> /tmp/healthy.err

# Must succeed, must be strict JSON:
python3 -c 'import json; json.load(open("/tmp/healthy.json"))'

# Must not contain "/api/v1/me" in the captured network trace
# Must contain a successful POST /api/v1/events/batch/ with private X-Team-Slug
```

Expected: exit code 0, `/tmp/healthy.json` parses, stderr contains no `direct ingress skipped` warnings.

---

## Smoke 2 — Shared-only session, rehydrate succeeds

Goal: confirm Scenario 2 — session lacks a Private Teamspace, rehydrate fixes it.

Pre-condition: arrange a stale local session that lacks a Private Teamspace but the SaaS account does have one provisioned. Common setup: run an old build that wrote shared-only `teams[]`, then upgrade.

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=1 \
  spec-kitty agent mission create cli-private-team-smoke-rehydrate --json \
  > /tmp/rehy.json 2> /tmp/rehy.err

python3 -c 'import json; json.load(open("/tmp/rehy.json"))'
```

Expected:
- Exit code 0.
- `/tmp/rehy.json` parses.
- Network trace shows exactly one `GET /api/v1/me`.
- The local session file is updated; rerunning Smoke 1 immediately afterward shows zero `/api/v1/me` GETs.
- `POST /api/v1/events/batch/` carries the Private Teamspace slug.

---

## Smoke 3 — Shared-only session, rehydrate also fails

Goal: confirm Scenario 3 — graceful skip, structured diagnostic, local command still succeeds.

Pre-condition: a session whose authenticated user has no Private Teamspace at all (e.g., legacy account that has not been migrated). If you cannot reproduce this naturally, you can simulate it in a test (`tests/sync/test_strict_json_stdout.py`) — this smoke is documentation-only for that case.

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=1 \
  spec-kitty agent mission create cli-private-team-smoke-skip --json \
  > /tmp/skip.json 2> /tmp/skip.err

python3 -c 'import json; json.load(open("/tmp/skip.json"))'
grep "direct ingress skipped" /tmp/skip.err
```

Expected:
- Exit code 0 (the **local** command succeeds).
- `/tmp/skip.json` parses.
- `/tmp/skip.err` contains at least one `direct ingress skipped` warning with `category=direct_ingress_missing_private_team`, `rehydrate_attempted=True`, `ingress_sent=False`, and `endpoint` ∈ {`/api/v1/events/batch/`, `/api/v1/ws-token`}.
- Network trace shows **exactly one** `GET /api/v1/me` for the entire CLI process even when batch + ws-token both attempt ingress (this is the negative-cache contract).
- No `POST /api/v1/events/batch/` and no `POST /api/v1/ws-token` are sent.

---

## Smoke 4 — Strict-sync command fails loudly

Goal: confirm the explicit-sync escape hatch (FR-010 carve-out for sync-primary commands) still exits non-zero when missing Private Teamspace blocks the only thing the command exists to do.

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=1 \
  spec-kitty sync now --strict ; echo "exit=$?"
```

Expected: non-zero exit code, with the same structured stderr diagnostic as Smoke 3.

(Other strict-sync commands inherit the same behavior; mission-/task-/status-primary commands do **not**.)

---

## Smoke 5 — `auth status` does not regress

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=1 spec-kitty auth status
```

Expected: same output shape as before this mission. Login/UI default-team display still uses `pick_default_team_id` and is unaffected.

---

## Failure-mode reference

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `json.load` raises on a `--json` command's stdout | A `print()` snuck back into `sync/client.py` or a sibling | Run `grep -rn '\bprint\s*(' src/specify_cli/sync/`; replace with `logger.*` |
| Multiple `GET /api/v1/me` per CLI process on a shared-only session | Negative cache not being set or being cleared mid-process | Inspect `TokenManager._membership_negative_cache` lifecycle in `set_session` |
| Stale session keeps using shared `X-Team-Slug` | Refresh flow not triggering forced rehydrate | Verify `auth/flows/refresh.py` calls `rehydrate_membership_if_needed(force=True)` when local private identity is missing |
| `auth-doctor` repair does not refresh teams | Negative cache hiding success | `auth-doctor` paths must pass `force=True` to `rehydrate_membership_if_needed` |
