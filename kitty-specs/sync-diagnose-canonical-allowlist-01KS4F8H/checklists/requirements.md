# Requirements Checklist — sync-diagnose-canonical-allowlist

Verify each functional requirement before submitting the PR.

## Functional

- [ ] FR-001 — diagnose recognises every type in `_EVENT_TYPE_TO_MODEL`.
- [ ] FR-002 — diagnose continues to recognise CLI-internal types not in registry.
- [ ] FR-003 — diagnose rejects truly unknown types with a clear error.
- [ ] FR-004 — drift-detector test: monkeypatched-registry case is recognised without diagnose code changes.
- [ ] FR-005 — no remaining hardcoded event-type list in `diagnose.py`.
- [ ] FR-006 — existing `tests/sync/test_diagnose.py` cases all pass.
- [ ] FR-007 — `emitter.VALID_EVENT_TYPES` is unchanged; outbound gate tests still pass.

## Non-functional

- [ ] NFR-001 — comment explains the `_EVENT_TYPE_TO_MODEL` import precedent.
- [ ] NFR-002 — `git diff main...HEAD pyproject.toml` is empty.
- [ ] NFR-003 — only `diagnose.py`, `test_diagnose.py`, and mission dir are touched.
- [ ] NFR-004 — fixtures use canonical pydantic models for payload-shape construction.

## Operating rules

- [ ] C-001/002/003 — no SaaS DB mutation, no new pip deps, no out-of-scope edits.
- [ ] C-004 — `unset GITHUB_TOKEN` used before `gh` writes.
- [ ] C-005 — PR opened (not pushed direct-to-main).
- [ ] C-006 — Renata persona invoked.
- [ ] C-007 — canonical pydantic models used in fixtures.

## Acceptance

- [ ] `pytest tests/sync/test_diagnose.py -v` green.
- [ ] `pytest tests/sync/test_forward_compatibility.py tests/contract/test_handoff_fixtures.py -v` green.
- [ ] Diff scope: only the three locations listed in NFR-003.
- [ ] PR body cites `Closes Priivacy-ai/spec-kitty#1222`.
- [ ] `mission-review.md` lists any other hardcoded allowlists spotted (follow-ups for `#1198`).
