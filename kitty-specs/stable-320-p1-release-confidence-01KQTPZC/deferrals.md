# Deferrals

This mission intentionally keeps release scope to #966, #848, fresh smoke
evidence, and release-readiness artifacts.

## Explicit Deferrals

| Issue | Decision | Reason |
| --- | --- | --- |
| #971 | Deferred | The broad strict mypy gate was not included. WP01 ran strict mypy only for `src/specify_cli/status/progress.py`, the changed progress module. |
| #662 | Deferred P2 | Not touched by this mission; no fresh stable-blocking repro was found. |
| #630 | Deferred P2 | Not touched by this mission; no fresh stable-blocking repro was found. |
| #629 | Deferred P2 | Not touched by this mission; no fresh stable-blocking repro was found. |
| #631 | Deferred P2 | Not touched by this mission; no fresh stable-blocking repro was found. |
| #771 | Deferred P3 | Not touched by this mission; no current repro promoted it to stable blocker. |
| #726 | Deferred P3 | Not touched by this mission; no current repro promoted it to stable blocker. |
| #728 | Deferred P3 | Not touched by this mission; no current repro promoted it to stable blocker. |
| #729 | Deferred P3 | Not touched by this mission; no current repro promoted it to stable blocker. |
| #644 | Deferred P3 | Not touched by this mission; no current repro promoted it to stable blocker. |
| #740 | Deferred P3 | Not touched by this mission; no current repro promoted it to stable blocker. |
| #323 | Deferred P3 | Not touched by this mission; no current repro promoted it to stable blocker. |
| #306 | Deferred P3 | Not touched by this mission; no current repro promoted it to stable blocker. |
| #303 | Deferred P3 | Not touched by this mission; no current repro promoted it to stable blocker. |
| #317 | Deferred P3 | Not touched by this mission; no current repro promoted it to stable blocker. |
| #973 | Deferred P3 | Not touched by this mission; no current repro promoted it to stable blocker. |
| #869 | Stale | No fresh repro appeared during this mission. |

## Prior P0 Issues

Issues #967, #904, #968, and #964 are treated as fixed by PR #972 for this
release-confidence pass. No fresh regression appeared during this mission.

## Smoke Limitation

WP03's SaaS-enabled smoke completed the lifecycle with
`SPEC_KITTY_ENABLE_SAAS_SYNC=1`, but final hosted drain proof was unavailable
because the local daemon reported lock/auth-refresh contention and WebSocket
offline. This is a bounded workstation sync limitation, not a tracker rollout
gate and not a stable-release blocker.
