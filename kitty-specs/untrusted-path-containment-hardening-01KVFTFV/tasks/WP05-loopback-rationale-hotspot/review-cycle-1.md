# WP05 Review — Cycle 1 (reviewer-renata)

**Verdict: CHANGES REQUESTED.** One blocking gate failure (mypy --strict). All
other acceptance criteria pass, including an independent mutation check that
confirms the new binding tests are genuine (not fake).

## BLOCKING

**Issue 1 — mypy --strict fails on the new test (T024 / Code Review Checklist).**

`tests/core/test_loopback_http.py:111` raises:

```
error: "HTTPServer" has no attribute "bound_address"  [attr-defined]
```

Reproduce (from the lane worktree):

```bash
python -m mypy --strict src/specify_cli/core/loopback_http.py tests/core/test_loopback_http.py
# Found 1 error in 1 file (checked 2 source files)
```

Root cause: the new test `test_create_loopback_server_does_not_bind_non_loopback_host`
(lines 107–120) calls `create_loopback_server(...)`, which is annotated to return
`HTTPServer`, then accesses `server.bound_address`. `HTTPServer` has no such
attribute — that attribute exists only on the test double `_RecordingServer`.

The *existing* sibling test `test_create_loopback_server_binds_loopback_only`
(lines 75–82) avoids this by narrowing first:

```python
assert isinstance(server, _RecordingServer)
```

The new test omits that narrowing line, so mypy cannot see `bound_address`.

How to fix: add `assert isinstance(server, _RecordingServer)` immediately after
the `create_loopback_server(...)` call in
`test_create_loopback_server_does_not_bind_non_loopback_host`, mirroring the
existing test. (The `serve_loopback_server` test already reads
`_RecordingServer.instances[0]`, which is correctly typed, so only the
`create_loopback_server` test needs the narrowing.) After the fix, re-run the
mypy command above and confirm `Success: no issues found`.

CLAUDE.md is explicit: "New code MUST pass ruff and mypy with zero issues and
zero warnings ... fix the code instead." T024's DoD requires mypy clean on the
touched files. The narrowing fix is purely additive to the test and does not
affect behaviour or the mutation-kill property.

## PASSING (recorded for the next cycle — do not regress)

- **Criterion 1 — diff-shape / no behavioural change**: PASS. The diff to
  `src/specify_cli/core/loopback_http.py` is exclusively docstring + comment
  additions. No executable line (`return`, assignment, logic) changed; helpers
  still bind `127.0.0.1` and still use plain HTTP.
- **Criterion 2 — two-sided binding test + independent mutation**: PASS.
  Independently mutated source `LOOPBACK_HOST = "0.0.0.0"`, ran
  `PWHEADLESS=1 python -m pytest tests/core/test_loopback_http.py -q`: both new
  (b)-side tests FAILED with `assert '0.0.0.0' != '0.0.0.0'` (mutation-killing,
  not fake). Reverted; worktree clean; tests green again (7 passed).
- **Criterion 3 — hotspot record**: PASS. Module docstring records both hotspots
  by Sonar rule key (`encrypt-data`) + function location + PR #2036 + the
  do-not-force-HTTPS rationale (C-001 / C-005).
- **Criterion 4 — ruff**: PASS (`All checks passed!`); loopback tests green.
- **Criterion 5 — scope**: PASS. Only the two owned files changed; no HTTPS
  forced; no unrelated edits.

## Anti-pattern checklist

1. Dead code — N/A (no new production symbols). 2. Synthetic fixture — PASS
(mutation-verified). 3. Silent empty return — N/A. 4. FR coverage (FR-006) —
PASS (tests reference the binding behaviour). 5. Frozen surface — N/A.
6. Locked decision (C-001 do-not-force-HTTPS) — PASS (not violated). 7. Shared
ownership — N/A (WP05 owns lane-e alone). 8. Production fragility — N/A.

Fix Issue 1 and resubmit.
