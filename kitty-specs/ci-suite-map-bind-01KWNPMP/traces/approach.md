# Approach Evolution

> Track how your approach changed as the mission progressed.

**Prompting questions**
- What approach did you start with (as stated in the spec or plan)?
- What changed during implementation, and why?
- What would you try differently on a similar mission?

---

## Entries

<!-- YYYY-MM-DD — 1-3 sentences: what approach was tried and what shifted. -->

- 2026-07-04 — SEED (backfilled same-day). Starting approach per spec rev 4 / plan: CI-validated invariants over the parsed `_gate_coverage` model (WS5's "or CI-validated" arm), NO workflow generator; 5-WP topology with two single-owner spines (WP01 parse model, WP03 workflow pair) and the FR-011 decision logic EXTRACTED to a script (WP02) so yml wiring stays thin; WP01 ∥ WP02 → WP03 → WP04 → WP05.
- 2026-07-04 — Pre-implement refresh: rather than trusting 3-day-old prep after the #2337 landing, ran a 3-lens refresh squad (census recount / surface collision / live tooling drift) against the rebased HEAD. Paid off: caught the unshim-wave2 residue (dead critical-path entry + 4 dead globs) that would have red-flagged WP04's invariants mid-flight; folded as FR-004(e) before any implementer started. Cadence worth repeating whenever upstream moves between tasks-finalize and implement.
- 2026-07-04 — Orchestration division of labor: implementers are code-only in their lane worktrees (no spec-kitty status commands, no pushes except the C-004 probe); the orchestrator owns all lane transitions, subtask mark-status, and bookkeeping commits from the primary checkout. Kept status authority in one place; cost is the manual commit-after-every-transition loop (see friction log).
- 2026-07-04 — Review discipline: independent profile-loaded reviewer (reviewer-renata) per WP, verifying every implementer claim LIVE (red→green from git topology, tripwires re-run with crafted payloads, table semantics reverse-specced from tests alone). WP02's review confirmed all 9 checklist items with zero rejects — the detailed WP prompts (per-FR DoD checklists from the post-tasks squads) appear to be what makes one-pass implementation achievable.
- 2026-07-04 — C-004 de-risk ordering held: WP01 ran the workflow-scope push preflight FIRST (probe push over SSH succeeded, probe branch deleted) before any parse-model work — the mission's biggest external unknown was retired in the first hour of implementation.
