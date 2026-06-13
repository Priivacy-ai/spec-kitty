# WP04 Review Feedback — Cycle 1

**Profile:** reviewer-renata  
**Date:** 2026-06-13  
**Overall status:** CHANGES REQUESTED

---

## Positive findings

- **C-004 (binding) — PASS.** All edits are SOURCE-only. The WP04 commit touches exactly three files, all source:
  - `src/doctrine/skills/spec-kitty.advise/SKILL.md` (doctrine source)
  - `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` (doctrine source)
  - `src/specify_cli/session_presence/content.py` (out-of-map, with inline rationale — accepted, see below)
  No generated agent copies were touched (`.claude/`, `.agents/skills/`, etc.).

- **Manifest no-entry claim — VERIFIED CORRECT.** `spec-kitty.advise` has no entry in `.kittify/command-skills-manifest.json`. All 11 manifest entries are CANONICAL_COMMANDS from `command_installer.py`. `advise` is not in `CANONICAL_COMMANDS`. The skill is installed via `SkillRegistry` (not the manifest), so no manifest hash refresh is correct and consistent with the plan's IC-06 note about the install path. The implementer's claim in the commit message is accurate.

- **Terminology canon — PASS.** `pytest tests/architectural/test_no_legacy_terminology.py` exits 0 (2 passed). No forbidden terms (`feature`, `ceremony`, `status-writing`) introduced. `spec-kitty dispatch` used as canonical throughout.

- **Skill content — CORRECT.** `src/doctrine/skills/spec-kitty.advise/SKILL.md` now leads with `dispatch` as canonical; `do`/`ask`/`advise` documented as retained first-class aliases with identical Op lifecycle. Invariants section updated. Quick-reference table updated. T015 and T016 are correctly implemented in the prose.

- **Out-of-map edit (session_presence/content.py) — ACCEPTED.** The edit is a behavior-preserving routing-prose update to the orientation block generator — the only source that emits this block. All 203 session_presence tests pass. The rationale is documented in the commit message. This is a reasonable rationale-backed edit per the ownership-map leeway policy; it is not a masking workaround.

- **spec-kitty-runtime-next/SKILL.md — CORRECT.** This is a doctrine source skill (not a generated agent copy). The routing-prose table and governance injection loop section correctly updated to lead with `dispatch`.

- **#1804 closure readiness — HONEST.** The activity log entry and commit message accurately describe the state: #1810 is substantially delivered by WP03 + this WP's propagation; #1804 is substantially complete pending terminal verdicts at the accept gate. The "ready for terminal verdicts" framing is correct and not a forced closure.

- **mypy / ruff — PASS.** Both `src/specify_cli/session_presence/content.py` and `tests/specify_cli/session_presence/` pass mypy clean. ruff clean on all touched files. The prior cycle's 17 mypy errors are resolved.

- **Dispatch parity tests (WP03 commit) — PASS.** All 11 `test_dispatch_parity.py` tests pass, covering NFR-001 behavioral parity.

---

## Required Changes

### Issue 1 (BLOCKING) — Anti-pattern 4: FR-006 has no test assertion

**Finding:** FR-006 is in `requirement_refs`. Its behavior: "`dispatch` documented in `src/doctrine/skills/spec-kitty.advise/SKILL.md`." No test asserts this. The WP's own Test Strategy states: "Assert `dispatch` appears in the SOURCE SKILL.md and the manifest hash is refreshed (a focused test or the existing command-skills manifest test). Paste commands + exit codes into handoff."

The manifest alternative was correctly identified as N/A. That means the "focused test" path is mandatory. No focused test was written.

**Why this blocks:** If someone later accidentally reverts or overwrites the SKILL.md source, no automated gate will catch the regression. The WP strategy recognized this risk and required a pinning test. The anti-pattern 4 check requires every FR in `requirement_refs` to have at least one test assertion naming the behavior.

**Fix:** Add a focused doctrine test (e.g., in `tests/doctrine/`) that reads `src/doctrine/skills/spec-kitty.advise/SKILL.md` and asserts `dispatch` is present as the canonical command. Example pattern:

```python
# tests/doctrine/test_advise_skill_content.py
from pathlib import Path
from tests.doctrine.conftest import DOCTRINE_SOURCE_ROOT

def test_advise_skill_documents_dispatch_as_canonical() -> None:
    """FR-006: dispatch is documented as canonical in the advise SOURCE skill."""
    skill_path = DOCTRINE_SOURCE_ROOT / "skills" / "spec-kitty.advise" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    assert "spec-kitty dispatch" in content, (
        "FR-006: dispatch must be documented as canonical in the SOURCE skill; "
        "do/ask/advise are retained aliases."
    )
    # Aliases must still be present
    assert "spec-kitty do" in content
    assert "spec-kitty ask" in content
    assert "spec-kitty advise" in content
```

Paste `pytest tests/doctrine/test_advise_skill_content.py -v` exit code into the activity log.

---

### Issue 2 (ADVISORY — not blocking) — session_presence content test does not pin the T016 change

**Finding:** `tests/specify_cli/session_presence/test_content.py` line 37 asserts `"spec-kitty do" in rendered`, which was the pre-WP04 canonical form. After T016, `dispatch` is the new leading form in the orientation block. The existing assertion still passes (the string `spec-kitty do` appears as an alias), but no test verifies that `dispatch` now appears. If the T016 change is accidentally reverted in `content.py`, no test fails.

**Recommendation:** Add an assertion in `TestRenderCloseContract` or a new test class:
```python
assert "spec-kitty dispatch" in rendered
```
This is advisory (the existing test still passes and the out-of-map edit was accepted), but adding this pin would close the regression gap for T016.

---

## Anti-pattern checklist

| # | Pattern | Result | Notes |
|---|---------|--------|-------|
| 1 | Dead code | PASS | All touched modules have live callers |
| 2 | Synthetic-fixture test | PASS | dispatch parity tests invoke real CLI via CliRunner |
| 3 | Silent empty return | PASS (N/A) | No new exception handlers in WP04 changes |
| 4 | FR coverage | **FAIL** | FR-006: no test asserts `dispatch` in SOURCE SKILL.md |
| 5 | Frozen surface | PASS | No frozen files identified |
| 6 | Locked decision | PASS | C-004 respected; no MUST NOT violations |
| 7 | Shared-file ownership | PASS | session_presence/content.py not owned by any other WP |
| 8 | Production fragility | PASS (N/A) | No new raise statements in WP04 production changes |
