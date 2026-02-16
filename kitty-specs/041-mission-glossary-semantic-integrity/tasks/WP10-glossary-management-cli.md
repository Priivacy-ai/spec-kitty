---
work_package_id: WP10
title: Glossary Management CLI
lane: planned
dependencies: []
subtasks: [T044, T045, T046, T047]
history:
- event: created
  timestamp: '2026-02-16T00:00:00Z'
  actor: llm:claude-sonnet-4.5
---

# Work Package: Glossary Management CLI

**ID**: WP10 **Priority**: P3 **Estimated Effort**: 1-2 days

## Objective

Provide CLI commands for glossary inspection and async conflict resolution.

## Implementation Command

```bash
spec-kitty implement WP10 --base WP09
```

Can run in parallel with WP11.

---

## Subtasks

### T044: `spec-kitty glossary list --scope <scope>`

List terms in a scope with Rich table.

---

### T045: `spec-kitty glossary conflicts --mission <mission>`

Show conflict history from events.

---

### T046: `spec-kitty glossary resolve <conflict_id>`

Async resolution: prompt for choice, emit events.

---

### T047: CLI tests

Mock event log, verify Rich output.

---

## Definition of Done

- [ ] 4 subtasks complete
- [ ] 3 commands work
- [ ] Tests >90% coverage

---

## Reviewer Guidance

**Acceptance**:
- [ ] Commands output correctly
- [ ] Async resolution works
