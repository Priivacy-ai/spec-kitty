# Design Decisions

> Capture the rationale that would otherwise evaporate.

**Prompting questions**
- What decision was made?
- What alternatives were considered?
- What was the rationale — why this option over the others?

---

## Entries

<!-- YYYY-MM-DD — Decision: [what]. Alternatives: [what else]. Rationale: [why this one]. -->

2026-09-09 — Choose direct-authored artifact registration (gist option b), retaining canonical source files and reference extraction. Resynthesis must preserve registration and validate the proposed activation set before writes.

2026-09-08 · implementer-ivan · Direct project registration preserves canonical authored files and per-artifact provenance. Fresh resynthesis must retain populated project doctrine; default first-load context must resolve activated project roots. These acceptance failures were reproduced and fixed before remote CI.
