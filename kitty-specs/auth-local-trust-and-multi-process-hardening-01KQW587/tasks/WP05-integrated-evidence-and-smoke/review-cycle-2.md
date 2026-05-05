---
affected_files: []
cycle_number: 2
mission_slug: auth-local-trust-and-multi-process-hardening-01KQW587
reproduction_command:
reviewed_at: '2026-05-05T15:34:43Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP05
review_artifact_override_at: "2026-05-05T15:54:23Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP05"
review_artifact_override_reason: "Review passed: evidence uses lane A 9099a032 and lane B 306bc815; focused suites pass including FR-011 146 passed"
---

**Issue 1**: FR-011 is not satisfied in the integrated evidence and must block WP05 approval.

`evidence.md` correctly records the approved lane heads used for integrated validation (`9099a032` for WP01 lane A and `71ceb773` for WP02-WP04 lane B), but the FR-011 regression slice fails on that integrated code with 15 auth status/logout failures:

```text
uv run pytest tests/auth/test_token_manager.py tests/auth/test_refresh_flow.py tests/auth/test_revoke_flow.py tests/auth/test_auth_doctor_report.py tests/auth/test_auth_doctor_repair.py tests/auth/test_auth_doctor_offline.py tests/cli/commands/test_auth_status.py tests/cli/commands/test_auth_logout.py -q
...
15 failed, 131 passed
```

The same auth status/logout slice passes on root `main` with `37 passed`, and fails on lane B alone with the same `TypeError('expected str, bytes or os.PathLike object, not Mock')`, so this is not a pre-existing baseline failure and is not caused by merging WP01. The likely regression surface is WP04's hot-path changes in `TokenManager`: `_load_hot_path_summary()` and `_publish_hot_path_summary_if_possible()` treat any `storage.store_path` attribute as path-like, but mocked or non-file storage objects can expose a `Mock` attribute. Because `_load_hot_path_summary()` is called before the storage read `try` block, that `TypeError` escapes normal unauthenticated/status/logout behavior.

FR-011 says existing shipped browser/device login, logout revoke, refresh replay, and server-session doctor behaviors must remain supported, with focused regression tests continuing to pass. A caveat in the evidence is useful triage, but it is not acceptable as final closeout for a confirmed requirement.

Required remediation:

- Fix the lane-B/WP04 auth hot-path regression so non-file or mocked storage without a real path-like `store_path` bypasses the hot path and falls back to the durable storage behavior.
- Rerun the FR-011 regression slice above and confirm it passes in the integrated lane-A + lane-B validation worktree.
- Rerun the WP05 focused evidence commands and update `evidence.md` so FR-011 has passing evidence instead of a blocking caveat.

Non-blocking context: WP01 and WP04 have historical rejected review artifacts that remain in their task directories. Current mission status/event history marks both WPs approved with override metadata on the old rejection artifacts; do not delete that history while addressing this blocker.
