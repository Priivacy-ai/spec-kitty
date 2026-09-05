# R2-T1 commit-history attribution notes

This file exists solely to correct a misattribution flagged by Renata's
attempt-6 review (MEDIUM finding) that cannot be fixed by editing git
history, because this repo's own hard constraint forbids amending a
reviewed commit -- rework is always a new commit, never a rewrite of one
already reported. It records, out-of-band, what the affected commit's
message alone does not say.

## `006aaebff9a2b61b662db093687a72dfe6541792` — mixed-purpose commit

Subject: `fix(R2-T1): register the new retirement test in the real-port
serial family`

The stated purpose (registering `tests/sync/test_legacy_daemon_retirement_r2t1.py`
in `FIXED_RANGE_SUITES` / `ci-quality.yml`'s serial `-n0` lane, alongside the
`.github/workflows/ci-quality.yml` and `tests/_real_port_suites.py` diff
hunks) is accurate for two of the commit's three changed files.

The same commit's diff also introduces the entire new file
`tests/cli/commands/test_sync_doctor_legacy_daemon_retirement_r2t1.py`
(112 lines) — the RED test for the `sync doctor` wiring feature
(`_render_legacy_daemon_retirement`) that was made GREEN two commits later,
in `5a40192c5` (`feat(R2-T1): wire legacy daemon retirement into "sync
doctor" (WP a)`). The commit message never mentions this file, so a reader
reconstructing RED-before-GREEN evidence from `git log --stat` alone for
that file lands on a commit whose stated purpose is unrelated port-range
registration.

**Correct attribution:** the RED addition of
`tests/cli/commands/test_sync_doctor_legacy_daemon_retirement_r2t1.py`
belongs with `5a40192c5`'s GREEN implementation as the RED half of that
same WP, not with `006aaebff`'s real-port-suite registration fix. Both
commits are already landed and reviewed-in-sequence; this note is the
record of that fact for any later reader or closure-script methodology
(the #3167-style module-qualified, evidence-cited precedent this repo
already established) walking the history rather than a rewrite of it.
