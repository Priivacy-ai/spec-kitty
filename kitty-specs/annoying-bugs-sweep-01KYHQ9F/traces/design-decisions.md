# Design Decisions

> Capture the rationale that would otherwise evaporate.

**Prompting questions**
- What decision was made?
- What alternatives were considered?
- What was the rationale - why this option over the others?

---

## Entries

### 2026-07-27

**Decision**: Fix #2985 with per-WP seed ordering below existing transition and annotation history.
**Alternatives**: seed suppression and reducer precedence. **Rationale**: suppression loses claim
slots; precedence changes the global state machine for a migration-only defect.

**Decision**: Use a pure-Python reference scan and an explicit undeterminable dead-code verdict.
**Alternatives**: `git grep` and silent clean on empty discovery. **Rationale**: pure Python is
portable and retains filesystem semantics; unsupported analysis must not claim success.
