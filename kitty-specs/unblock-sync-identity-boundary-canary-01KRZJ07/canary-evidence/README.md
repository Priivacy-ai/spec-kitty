# Canary Evidence

This directory is populated by WP04 with the output of the local canary run against the rc bump that bundles the mission's CLI fixes.

Expected contents after WP04 completes:

- `latest.json` — the canary harness's `latest` run summary (copied from `spec-kitty-end-to-end-testing/artifacts/sync_identity_boundary/<rc-bump>/latest.json`).
- `run-1.json` — at least one full run record showing scenarios 1, 2, and 4 green; scenario 3 may remain red per C-002.
- Optional: console capture (`canary-run.log`) of the `pytest tests/identity_boundary/ -v --capture=no` invocation.

This directory is intentionally empty at plan time. Do not commit placeholder evidence — the only artifacts here should be real canary output.
