---
affected_files: []
cycle_number: 4
mission_slug: private-teamspace-ingress-safeguards-01KQH03Y
reproduction_command:
reviewed_at: '2026-05-01T08:24:23Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP01
---

**Issue 1**: WP01 does not meet its required strict mypy validation gate.

The implementation behavior is aligned with the resolver contract, and the
pytest and ruff checks pass. However, the work package explicitly requires
`mypy --strict` to be green for both touched files. Running:

```bash
uv run mypy --strict src/specify_cli/auth/session.py tests/auth/test_session.py
```

fails with `no-untyped-def` errors in `tests/auth/test_session.py`, including
the newly added resolver tests:

- `test_require_private_team_id_returns_private_when_present`
- `test_require_private_team_id_returns_none_when_no_private_team`
- `test_require_private_team_id_ignores_default_team_id`
- `test_require_private_team_id_never_returns_first_team_fallback`
- `test_require_private_team_id_wins_over_drifting_default`

Fix by adding explicit return annotations, typically `-> None`, to the new
tests and any other functions in `tests/auth/test_session.py` needed to make
the exact command above pass. Re-run the command before resubmitting.

Verification already run:

- `uv run pytest tests/auth/test_session.py -v` passed: 25 passed.
- `uv run pytest tests/auth -v` passed: 342 passed, 2 skipped.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check src/specify_cli/auth/session.py tests/auth/test_session.py` passed.
- `uv run mypy --strict src/specify_cli/auth/session.py` passed.

Downstream dependency note: WP04 and WP05 depend on WP01. If those agents have
started local work, rebase after WP01 is corrected and resubmitted:

```bash
git fetch origin
git rebase kitty/mission-private-teamspace-ingress-safeguards-01KQH03Y-lane-a
```
