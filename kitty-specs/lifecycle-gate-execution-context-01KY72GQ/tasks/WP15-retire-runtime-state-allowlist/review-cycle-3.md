---
affected_files:
- src/specify_cli/bulk_edit/diff_check.py
- tests/architectural/test_exemption_registry_ratchet.py
- tests/architectural/tool_artifact_enrolment/registry/_is_review_lifecycle_basename.md
cycle_number: 3
mission_slug: lifecycle-gate-execution-context-01KY72GQ
reproduction_command: PWHEADLESS=1 uv run --extra test pytest tests/architectural/test_exemption_registry_ratchet.py tests/specify_cli/bulk_edit/ -q
reviewed_at: '2026-07-24T08:35:00Z'
reviewer_agent: reviewer-renata (claude/opus)
verdict: approved
wp_id: WP15
---

# WP15 Review — Cycle 2 (artifact cycle-3): APPROVE

**Reviewer:** reviewer-renata (claude / opus) · **WP:** WP15 — Retire `RUNTIME_STATE_ALLOWLIST` (IC-07e)
**Commit reviewed:** `80c24ebe6` (supersedes the cycle-1 reject on `2927fb737`) · **Verdict:** APPROVE

## Focused re-verification of the silent-survivor fix (the sole cycle-1 defect)

The cycle-1 blocking defect — `_is_review_lifecycle_basename` was a load-bearing filename
exemption with no registry row (a silent survivor forbidden by plan.md L233-235) — is fully
resolved. Verified against the real files at commit `80c24ebe6`:

1. **Enumerated & visible (no longer silent).** New row
   `tests/architectural/tool_artifact_enrolment/registry/_is_review_lifecycle_basename.md`
   exists: `mechanism`/`symbol` `_is_review_lifecycle_basename`, `module`
   `src/specify_cli/bulk_edit/diff_check.py`, `literals: (none)`, `status: justified-survivor`.
   Added to the census `required` set in `test_registry_covers_every_known_mechanism`, so a
   dropped row file now fails loudly.

2. **Held accountable by a genuinely NEGATIVE arm.**
   `test_every_registry_symbol_is_present_in_its_module` iterates ALL rows (including this
   survivor) and asserts `_module_references_symbol(module, symbol)` — the `def
   _is_review_lifecycle_basename` is present, so it passes, and it goes RED if the predicate
   is ever removed without deleting the row. The survivor is not a free pass. The
   literal-based undercount/overcount arms correctly do not apply (`literals: (none)`).

3. **`justified-survivor` status extension is MINIMAL and correct.**
   `_ROW_STATUSES = frozenset({"expected-present", "justified-survivor"})`; the ONLY status
   assertion (`test_registry_is_non_empty_and_enumerated`) was relaxed from `== "expected-present"`
   to `in _ROW_STATUSES`. No other row's status changed; the shrink narrative for every
   `expected-present` row is intact. Acceptable as-is — no broader WP10 follow-up needed.

4. **Prose genuinely justifies the survivor (C-010).** The row records why it cannot route
   onto the owner: neither `notes.md` nor `review-cycle-*.md` has a `MissionArtifactKind`;
   `is_toolchain_generated_churn` returns `False` for both (empirically confirmed;
   `review-cycle-*.md` under `tasks/<WP>/` resolves to PRIMARY `WORK_PACKAGE_TASK`, not coord
   residue); forcing them onto the owner would pollute its boundary or reintroduce a false
   block. This satisfies plan.md L233-235 ("explicit, justified registry row, never a silent
   survivor").

5. **diff_check.py comments corrected.** The predicate docstring + block comment no longer
   claim "deliberately avoiding registration"; they now cite the registry row as the source
   of truth.

## Gate evidence (commit 80c24ebe6)

- `tests/architectural/test_exemption_registry_ratchet.py` → **12 passed** (accepts `justified-survivor`).
- `tests/specify_cli/bulk_edit/` → **130 passed** (C6 behaviour preserved; no regression).
- `ruff check` + `mypy` on `diff_check.py` and the ratchet test → **clean**.
- Per-symbol absence (C5) still holds: `grep RUNTIME_STATE_ALLOWLIST|_runtime_state_exemption|_is_runtime_state_basename src/` → EMPTY.

Everything verified in cycle 1 (per-symbol absence, C6 behaviour, the delegate-vs-local
split correctness) still holds. **APPROVED.**
