# Issue matrix — wp-lane-state-machine-fsm-01KTGZAZ

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1589 | WP-lane status split-brain (dual transition authority, genesis/planned conflation, finalize clobber) | deferred-with-followup | WP01 commit b46f8bebf delivers the FSM single-authority slice (guards+force in WPState, validate_transition delegator, ALLOWED_TRANSITIONS gate eliminated). Read/write parity + finalize halves land in remaining WPs. Follow-up: #1589 stays open until WP02–WP06 land; final disposition at mission accept. |
| #1666 | Execution-state canonicalization epic | deferred-with-followup | WP01 ratifies the FSM-as-sole-transition-authority (US1, spec.md §265–266). Parent epic — remaining scope tracked across mission WPs and follow-on missions. Follow-up: #1666 epic close/triage at mission review. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`.
