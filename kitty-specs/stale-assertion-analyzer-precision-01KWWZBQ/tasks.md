# Work Packages: Stale-assertion analyzer precision

**Mission**: `stale-assertion-analyzer-precision-01KWWZBQ` | **Issues**: Closes #2031 + #2343 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Subtask Format: `[Txxx] Description (WP)`

## Path Conventions
Repo-root-relative. Single cohesive WP — both precision fixes live in `stale_assertions.py` + share the suppression mechanism + the same test suite.

| Subtask | Description | WP | Requirement |
| --- | --- | --- | --- |
| T001 | Head-importability check: suppress a removed identifier when the origin file's head re-exports/imports it (`from X import Y`, `as _Y`, `__all__`, `__init__` re-export) | WP01 | FR-001, FR-002 |
| T002 | Generic-literal suppression: `_is_generic_literal` gates on **genuineness** (pinned generic-token set / all-punctuation), **NOT length** — a short literal (`"E001"`) can be assert-critical; suppress matching removed literals | WP01 | FR-004 |
| T003 | Regression fixtures incl. the name-collision guard + FP-ceiling; genuine deletion still flagged | WP01 | FR-005, FR-006 |

---

## Work Package WP01: Relocation/re-export + generic-literal suppression (Priority: P1)
**Prompt**: `/tasks/WP01-analyzer-precision.md`
**Goal**: `stale_assertions.py` suppresses relocation/re-export false positives (keyed on head-importability, not bare-name) + generic-literal noise, without blinding genuine deletions.
### Included Subtasks
- [ ] T001 Head-importability suppression (WP01)
- [ ] T002 Generic-literal suppression (WP01)
- [ ] T003 Regression fixtures incl. collision + ceiling (WP01)
### Dependencies
None (single WP).
### Risks & Mitigations
- Over-suppression blinding genuine stale → key on head-importability (not bare-name); fixture (d) proves a common-name deletion isn't suppressed.
- Render/ceiling coupling → suppress (don't emit), so `merge/executor.py` + `cli/.../tests.py` need no change.
