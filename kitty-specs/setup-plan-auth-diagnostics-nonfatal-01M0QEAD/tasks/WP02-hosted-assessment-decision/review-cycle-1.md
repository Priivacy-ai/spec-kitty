---
affected_files: []
cycle_number: 1
mission_slug: setup-plan-auth-diagnostics-nonfatal-01M0QEAD
reproduction_command:
reviewed_at: '2026-08-23T19:51:51Z'
reviewer_agent: user
wp_id: WP02
---

# WP02 review feedback — cycle 1

## Blocking finding 1: returned preflight evidence can disclose raw exception detail

`evaluate_boundary()` serializes `PreflightResult.to_dict()` and `_sanitize_preflight_evidence()` removes only `unreadable_owner_record.detail` (`src/specify_cli/cli/commands/agent/setup_plan_hosted.py:144`, `:296-302`). Canonical preflight also places raw exception type and text into `project_store_diagnostic` (`src/specify_cli/sync/preflight.py:697`, `:703`), and `PreflightResult.to_dict()` exposes that field. A direct production-path check using `PreflightResult(project_store_diagnostic="RuntimeError: token=top-secret ciphertext=/tmp/session.enc")` proved that the complete string survives in `HostedSyncDecision.to_dict()`.

This violates C-007, FR-012, the result-envelope contract's prohibition on credentials/raw exception dumps, and WP02's explicit completion criterion that no raw exception, credential, session, or token content appear in details.

Remediation: sanitize or replace every free-form preflight diagnostic field at the setup-plan adapter boundary with stable reason/evidence values. Add a regression using a returned non-passing `PreflightResult` whose `project_store_diagnostic` contains exception, token, session, ciphertext, and path material, and assert none survives the boundary evaluation or decision serialization. Keep canonical `sync.preflight` unchanged.

## Blocking finding 2: the public adapter has no production consumer

Targeted call-site search found only the definition of `assess_hosted_sync()` in `src/`; no production module imports or invokes the new adapter. The review prompt's dead-code guard is explicit that zero production hits for a new module is a failure. WP04 is planned to add the consumer, but it has not done so yet, so WP02 cannot independently demonstrate that its single decision is the live authority guarding setup-plan hosted effects.

Remediation: coordinate the mission slicing/review order so WP02's adapter and WP04's production integration are reviewed together, or otherwise provide a live production consumer without crossing the declared ownership boundary. Do not add an artificial caller solely to satisfy the grep.

## Verified behavior and gates

- ATDD ordering is correct: `b795fe6d7` adds the tests while the imported production module is absent; `cd0d4353e` adds the implementation and the focused tests are green.
- Exhaustive 18-row authenticated/logged-out/auth-unknown × safe/unsafe/unknown boundary × route available/unavailable evaluation passed; only authenticated + safe + route available permits effects, with stable auth → boundary → route ordering.
- SaaS-disabled probe short-circuit, no-raise auth/boundary/route acquisition, distinct diagnostics, `require_auth=False`, and refusal behavior pass.
- No hosted sink, queue-scope reader, transport, or token-manager import exists in the adapter. Only the two owned files changed; canonical preflight is untouched.
- `uv run pytest -q tests/specify_cli/cli/commands/agent/test_setup_plan_hosted.py tests/sync/test_sync_boundary_preflight.py`: 43 passed, 1 skipped.
- `uv run pytest -q tests/readiness/test_auth_probe.py tests/auth/test_token_manager.py tests/sync/test_routing.py`: 80 passed.
- Ruff on both owned files: passed.
- `mypy --strict` on the production module: passed.

## Downstream coordination

WP04 depends on WP02. Because WP02 is returning to planned, any WP04 work must wait for the corrected WP02 decision surface and rebase/refresh against the repaired commit before integration.
