# Issue Traceability Matrix — execution-state-canonical-surface-01KTG6P9

**Mission:** Execution-State Canonical Domain Surface (#1666 Strangler Slice 2)
**Branch:** feat/execution-state-strangler
**Created:** 2026-06-07
**WP column status:** _pending `/spec-kitty.tasks`_ — work-package IDs are filled in at task authoring; this matrix is the spec→issue trace and is re-checked at tasks-finalize.

---

## Source issue → requirement → scenario → success criterion

| Source issue | State | Workstream | Functional reqs | Scenario(s) | Success criteria | WP (pending tasks) |
|--------------|-------|------------|-----------------|-------------|------------------|--------------------|
| **#1673** ExecutionContext hardening (+ inherited #1681 residue) | OPEN | Canonical surface + path-builder strangling | FR-001 … FR-012 | C, E, F | SC-1, SC-3, SC-4, SC-7 | _pending_ |
| **#1664** status/ public API not enforced (~225 bypasses) | OPEN | Repo-wide facade enforcement | FR-013 … FR-016 | B | SC-3 | _pending_ |
| **#1667** MissionStatus aggregate (landed) | CLOSED | Consistent MissionStatus usage | FR-017 … FR-019 | F | SC-5 | _pending_ |
| **#1672** e2e parity ratchet | OPEN | Full-sequence ratchet | FR-020 … FR-024 | A | SC-2 | _pending_ |
| **#1663** MissionRun → Mission back-reference (field-drop) | OPEN | Mission-identity fold-in | FR-025 … FR-027 | D | SC-6 | _pending_ |
| **#1666** parent epic | OPEN | Umbrella / design authority | (all) | (all) | (all) | n/a (epic) |

---

## Reverse check — every FR maps to a source issue (coverage)

| FR range | Mapped issue |
|----------|--------------|
| FR-001..FR-006 (canonical module + ADR + layer guard) | #1673 + #1666 (doc 06 §4) |
| FR-007..FR-012 (residue routing, dup-resolver deletion, mode-correct branch) | #1673 (inherited #1681) |
| FR-013..FR-016 (facade promotion + repo-wide boundary test) | #1664 |
| FR-017..FR-019 (MissionStatus consistent usage) | #1667 |
| FR-020..FR-024 (full-sequence ratchet + de-overclaim) | #1672 |
| FR-025..FR-027 (snapshot mission-identity carry-through) | #1663 |

**No orphan FRs.** Every FR-001..FR-027 traces to a source issue. Every source issue has ≥1 FR.

---

## Double-check notes

- **#1667 is CLOSED** — included for the consumption workstream (route bypasses onto the landed aggregate); it is not re-opened or re-claimed.
- **#1681 is CLOSED** — it tracked the path-builder residue; that residue (~125 sites / ~160 files) is inherited by #1673's workstream here, not re-opened.
- **#1666 is the epic** — design authority, not an implementation ticket to claim.
- Tickets being actively claimed/assigned for this mission: **#1672, #1664, #1673, #1663** (the open implementation issues).
- Persona ICs (Randy Reducer / Paula Patterns) attach to the shaping WPs at `/spec-kitty.tasks`; they enforce NFR-002 (leanness) and NFR-003 (single ownership), which trace to SC-7.
