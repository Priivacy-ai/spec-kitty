# Issue matrix — operating-procedures-validate-triage-01M0DR8F

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2994 | operating-procedures values never checked against real nodes | fixed | Validator `resolve_operating_procedure_entries` + empty-set gate `test_operating_procedures_resolve.py` (RED@44→GREEN@0) + triage of 44 entries. Commits 7881bb3, 2152509. |
| #3352 | data-drive agent_profile→procedure edges from operating-procedures | fixed | `_emit_operating_procedure_edges` guarded emission + retire 2 op-proc hand-pins; `agent_profile→procedure` 4→8. Commit bfbef7a. |
| #3488 | operating-procedures channel reaches no consumer | fixed | op-proc channel now data-driven into the graph + `doctor doctrine` diagnostic surface. The render/delivery half of #3488 (procedures[] to the agent) is explicitly M4 scope, not this mission. Commits 934b9be, bfbef7a. |
| #2829 | kind-complete cascade (REFERENCE_RELATIONS expansion) | deferred-with-followup | Out of scope for M3 (spec C-002); referenced only as a scope boundary. Owned by M5 (kind-complete cascade + orphan wiring). No code in this mission touches `REFERENCE_RELATIONS`. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission`.
