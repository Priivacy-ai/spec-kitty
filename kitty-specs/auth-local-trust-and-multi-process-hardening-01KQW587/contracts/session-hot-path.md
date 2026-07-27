# Contract: Local Session Hot Path

## Scope

Applies to many short-lived local CLI processes that need hosted auth/session state.

## Authority Model

```
encrypted file-only session storage
  |
  | authoritative read/write
  v
derived local handoff/cache
  |
  | fast-path read when fresh and valid
  v
short-lived CLI process
```

The derived handoff/cache never becomes the durable root of trust.

## Required Behavior

- If handoff state is fresh and matches durable session identity, a process may use it to avoid repeated expensive local session work.
- If handoff state is missing, stale, unreadable, mismatched, or invalid, the process falls back to encrypted durable storage.
- Refresh remains coordinated across processes by the existing machine-wide lock semantics or an equivalent proven boundary.
- Benign refresh replay and lock contention are handled as coordination outcomes, not fatal user errors.

## Security Rules

- No Keychain, keyring, Secret Service, or OS credential-manager dependency.
- No raw token material in user output, logs, or diagnostics.
- No raw token material in any plaintext handoff artifact unless a later reviewed design proves equivalent local protection; default plan assumes no plaintext token cache.
- Handoff/cache invalidation must be tied to durable session change.

## Tests

- Many short-lived processes sharing a valid session avoid repeated expensive work.
- Concurrent refresh peers converge on a consistent session result.
- Stale handoff falls back to encrypted storage.
- Packaging checks still prove no forbidden credential-manager dependency.
