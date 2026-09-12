# Approach Evolution

> Track how your approach changed as the mission progressed.

**Prompting questions**
- What approach did you start with (as stated in the spec or plan)?
- What changed during implementation, and why?
- What would you try differently on a similar mission?

---

## Entries

<!-- YYYY-MM-DD — 1-3 sentences: what approach was tried and what shifted. -->

## 2026-09-07 — planning
- Extend the single target authority (`auth/server_target.py`) and the single printer (`_auth_saas_target.py`); delete the gate module rather than re-gating.
- Order: ADR → target → visibility; opt-outs and readiness in parallel; gate-module deletion after both; docs sweep; public-CLI acceptance last.
- Bulk-edit occurrence map governs the vocabulary retirement; archives untouched.
