# Approach Evolution

> Track how your approach changed as the mission progressed.

**Prompting questions**
- What approach did you start with (as stated in the spec or plan)?
- What changed during implementation, and why?
- What would you try differently on a similar mission?

---

## Entries

<!-- YYYY-MM-DD — 1-3 sentences: what approach was tried and what shifted. -->

2026-09-09 — Preserve existing PR, transplant glossary step onto v3.2.6.1, then implement issue-separated commits. Public CLI reproductions precede fixes; run exact fresh-repository acceptance before final CI.

2026-09-09 · codex · Separate mandatory final-head remote CI handoff from local T007 verification. The original task phrasing created a cycle: local review required CI, while committing review changed the CI head. Local review and accept now precede final evidence publication; remote CI still blocks final handoff.
