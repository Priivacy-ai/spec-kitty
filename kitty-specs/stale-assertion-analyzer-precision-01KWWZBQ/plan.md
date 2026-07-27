# Implementation Plan: Stale-assertion analyzer precision

**Branch**: `fix/stale-assertion-analyzer-precision` | **Issues**: Closes #2031 + #2343 (M3 of #1931) | **Spec**: [spec.md](./spec.md)

## Summary

Two precision fixes to `src/specify_cli/post_merge/stale_assertions.py`, both by **suppressing** (not emitting) false findings:
1. **Relocation/re-export (#2031)**: a removed identifier still **importable from its origin file in head** (re-exported/aliased back) is relocated, not deleted → suppress. Keyed on **head-importability, NOT bare-name-anywhere** — the analyzer has no qualname primitive (only bare `node.name`), so matching "same name in another changed file" collides on common names (`run`/`main`) and would blind genuine deletions. (The extraction case that produced 180 false findings re-exports the moved symbols back → head-importability catches it.)
2. **Generic-literal noise (#2343)**: removed string literals matching an explicit **genuineness** rule (a pinned generic-token set / all-punctuation, **NOT length** — a short literal can be assert-critical) are suppressed. (The ~108-finding class.)

**Suppress, not downgrade-to-`info`** — deliberately, because `info` is mislabeled by `merge/executor.py`'s renderer, dropped by the CLI `stale-check` render, yet still counted by the FP-ceiling; a not-emitted finding avoids all three and keeps FR-006 honest. The **line-shift concern is out** — the code already strips `lineno` before the set-difference, so pure line-shifts are already unflagged.

## Technical Context
**Language/Version**: Python 3.11; `ast`, `git diff`.
**Project Type**: single project — one module (`stale_assertions.py`) + its test suite.
**Constraints**: heuristic honesty preserved (never "definitely_stale", NFR-001); same-diff scope only (C-001 — a symbol that vanished entirely is still removed); `ruff` + `mypy --strict` clean; no new suppressions.
**Scale/Scope**: `stale_assertions.py` (`_extract_changed_symbols` + a new same-diff qualname/re-export index + literal-genericness rule) + `tests/post_merge/` (relocation + generic-literal + genuine-deletion fixtures). The render surfaces (`merge/executor.py`, `cli/.../tests.py`) are **not** modified (suppression avoids them).

## Charter Check
- **No masking** — suppression is correct (a relocated/re-exported symbol is genuinely not stale); a genuine deletion is still flagged (FR-005). ✅
- **Non-vacuous / red-first** — a genuine deletion still reds; the extraction + generic-literal fixtures prove ~0 false findings. ✅
- **Canonical sources** — extend the existing analyzer + its confidence model; reuse the already-parsed diff/AST set (no full-repo scan). ✅
- **Heuristic honesty** (NFR-001) — no fabricated certainty. ✅

## Implementation Concern Map → Work Package

Single cohesive WP — both fixes live in `_extract_changed_symbols`/the emit path of one module and share the suppression mechanism + the same test suite.

### WP01 — Relocation + re-export + generic-literal suppression
- **Requirements**: FR-001, FR-002, FR-004, FR-005, FR-006; NFR-001/002; C-001/002; SC-001..005.
- **Affected surfaces**:
  - `stale_assertions.py`: in `_extract_changed_symbols`, before appending a removed identifier, check whether the **origin file's HEAD still re-exports/imports the name** — parse the origin file's head AST for `from <mod> import X` (incl. `as _X`), `X` in `__all__`, and module/`__init__` re-exports. If still importable-from-origin → **suppress**. **Do NOT** key on "the bare name appears in another changed file" — the analyzer has only bare names (`_extract_identifiers:121`), so that collides on common names (`run`/`main`) and would blind genuine deletions (SC-003). Add a `_is_generic_literal(value)` rule (a pinned generic-token set / all-punctuation, **NO length threshold** — a short literal can be assert-critical) → suppress matching removed literals. Reuse the already-parsed base/head trees; no per-finding repo scan (NFR-002).
  - `tests/post_merge/…`: regression fixtures — (a) extraction (symbols re-exported back from the origin file) → ~0 findings; (b) generic-literal removals → ~0; (c) a GENUINE deletion (origin head not re-exporting) → still flagged high/medium; (d) **name-collision**: genuine deletion of `X` in file C while an unrelated `X` is defined in changed file B (C's head not re-exporting `X`) → **still flagged** (the key collision guard); (e) relocate-**and-rename** → still flagged; (f) an assert-critical short literal → still emitted; (g) the FP-ceiling not tripped on the extraction fixture (FR-006).
- **Sequencing**: none (single WP). **Risks**: over-suppression blinding a genuine stale (mitigate: key on **head-importability not bare-name**; fixture (d) proves a common-name deletion isn't suppressed); re-export detection missing a shim form (mitigate: cover `from X import Y`, `import Y as _Y`, `__all__`, `__init__` re-export).

## Project Structure
```
kitty-specs/stale-assertion-analyzer-precision-01KWWZBQ/  spec · plan · tasks
src/specify_cli/post_merge/stale_assertions.py            # WP01 — relocation + re-export + generic-literal suppression
tests/post_merge/  (or tests/specify_cli/post_merge/)     # WP01 — regression fixtures
```
**Structure Decision**: single project, one WP (one module + its suite; render surfaces untouched by design).
