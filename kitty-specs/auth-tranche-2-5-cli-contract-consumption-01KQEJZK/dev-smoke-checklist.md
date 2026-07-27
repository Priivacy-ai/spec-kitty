# Dev Smoke Checklist: CLI Auth Tranche 2.5

## Prerequisites

```bash
cd /path/to/spec-kitty
export SPEC_KITTY_ENABLE_SAAS_SYNC=1
export SPEC_KITTY_SAAS_URL=https://spec-kitty-dev.fly.dev
```

Verify `spec-kitty --version` shows the Tranche 2.5 build.

## Step 1 — Login

```bash
spec-kitty auth login --force --headless
```

Expected:
- [ ] Login completes (browser or device flow).
- [ ] No error about missing SAAS_URL.

## Step 2 — Status

```bash
spec-kitty auth status
```

Expected:
- [ ] Shows email, session ID, token expiry.
- [ ] Access token is valid (not expired).

## Step 3 — Auth Doctor (offline, default)

```bash
spec-kitty auth doctor
```

Expected:
- [ ] Output includes Identity, Tokens, Storage, Refresh Lock, Daemon, Orphans, Findings sections.
- [ ] Ends with hint: "Run `spec-kitty auth doctor --server` to verify server session status."
- [ ] No outbound network calls (can verify with Wireshark or network proxy if needed).
- [ ] Exit code 0 (no critical findings).

## Step 4 — Auth Doctor with --server

```bash
spec-kitty auth doctor --server
```

Expected:
- [ ] Output includes all offline sections PLUS a "Server Session" section.
- [ ] Server Session shows "active" with a session ID.
- [ ] No raw token values, token_family_id, or revocation_reason in output.
- [ ] Exit code 0.

## Step 5 — Logout

```bash
spec-kitty auth logout
```

Expected:
- [ ] "Server revocation confirmed." (or "not confirmed" with a reason — depends on server state).
- [ ] "Local credentials deleted." or "+ Logged out."
- [ ] Exit code 0 regardless of server revocation outcome.
- [ ] Local session is gone: `spec-kitty auth status` shows "not logged in".

## Step 6 — Post-Logout Status

```bash
spec-kitty auth status
```

Expected:
- [ ] "Not authenticated" or equivalent.

## Known Non-Issue

`spec-kitty sync now` may report `server_error` for non-private teamspace ingress.
This is pre-existing issue #889 and is not related to Tranche 2.5 auth changes.
