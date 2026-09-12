# Approach Evolution

> Track how your approach changed as the mission progressed.

**Prompting questions**
- What approach did you start with (as stated in the spec or plan)?
- What changed during implementation, and why?
- What would you try differently on a similar mission?

---

## Entries

<!-- YYYY-MM-DD — 1-3 sentences: what approach was tried and what shifted. -->

2026-08-24 (planning) — Approach taken by this plan: data-driven presence evaluation, not
code-table registration. No entry is added to `_GUARD_TABLES` for custom mission families — the
ADR from `rc3-charter-gate-predicate-inversion-01M0GGT1`
(`docs/adr/3.x/2026-08-21-1-charter-gate-predicate-inversion.md`) already decided this, and this
mission fulfils it rather than reversing it. The manifest-consulting logic (calling
`required_artifacts_for`, which imports `charter.missions`) lives exclusively in the I/O layer
(`runtime_bridge_io.py`'s `gather_artifact_presence`), never inside the stdlib-only leaf
`runtime_bridge_cores.py`, which stays a pure consumer of a snapshot field
(`ArtifactPresenceSnapshot.blocking_artifact_names: frozenset[str] | None`) it is merely handed.
This keeps `tests/architectural/test_bridge_cores_import_boundary.py` green by construction
rather than by after-the-fact vigilance. Sequencing: the snapshot field + cores.py branch (WP01)
is built and independently ATDD-tested before the org-tier resolution that populates it for real
(WP02), so the hardest-gated file gets its own small, isolable diff.
