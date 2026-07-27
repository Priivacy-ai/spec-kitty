---
affected_files: []
cycle_number: 6
mission_slug: auth-local-trust-and-multi-process-hardening-01KQW587
reproduction_command:
reviewed_at: '2026-05-05T15:37:35Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP04
review_artifact_override_at: "2026-05-05T15:43:29Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP04"
review_artifact_override_reason: "Review passed: 306bc815 bypasses non-path storage; FR-011 146 passed; WP04 focused 13 passed/2 skipped; auth concurrency 23 passed; BLE001 guard 5 passed and 0 findings"
---

---
affected_files: []
cycle_number: 5
mission_slug: auth-local-trust-and-multi-process-hardening-01KQW587
reproduction_command: "uv run pytest tests/auth/test_token_manager.py tests/auth/test_refresh_flow.py tests/auth/test_revoke_flow.py tests/auth/test_auth_doctor_report.py tests/auth/test_auth_doctor_repair.py tests/auth/test_auth_doctor_offline.py tests/cli/commands/test_auth_status.py tests/cli/commands/test_auth_logout.py -q"
reviewed_at: '2026-05-05T15:40:00Z'
reviewer_agent: wp05-review
verdict: rejected
wp_id: WP04
---

**Issue 1**: WP04 hot-path probing breaks non-file and mocked storage objects.

WP05 integrated evidence review found that the FR-011 auth status/logout regression slice fails on lane B and on integrated lane A + lane B code with `TypeError('expected str, bytes or os.PathLike object, not Mock')`. The same slice passes on root `main`, so the regression is introduced by the approved WP02-WP04 lane.

The likely source is `TokenManager._load_hot_path_summary()` and `_publish_hot_path_summary_if_possible()`: they treat any `storage.store_path` attribute as path-like. Mocked/non-file storage can expose a `Mock` attribute, and the resulting `Path(store_path)` call escapes before the normal durable-storage read fallback. This violates FR-011 because existing auth status/logout/doctor tests must keep passing.

Required remediation:

- Make WP04 hot-path probing opt in only when storage exposes a real path-like `store_path`; otherwise bypass the hot path and use durable storage normally.
- Add focused coverage for non-path-like mocked storage.
- Rerun the FR-011 auth regression slice and WP04 focused evidence after the fix.
