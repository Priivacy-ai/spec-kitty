# M2 tracer — design decisions

Append design rationale as the mission runs.

- #3604 relation `scope`, source node `mission_type` (operator-decided, C-003) —
  matches action-grain governance semantics so cascade traversal needs zero churn.
- #3605 must preserve edge TRIPLE identity (NFR-002/AC-009): add only when/reason.
- AC-003 rewrites the named test `test_cascade.py:449`
  (`test_plan_cascade_is_empty_...`), revising its rationale comment — not a silent
  add-to-set. New count assertions (31/23/160/0) are net-new (none exist to update).

## Post-plan adversarial squad (2026-08-21)
- LENS 2 (MAJOR, folded → WP02 T014): #3604's `mission_type --scope--> gov` edges
  falsify `RELATION_DESCRIPTIONS[Relation.SCOPE]` ("only from a mission-step action
  node"; "165 edges"), byte-mirrored to docs/architecture/doctrine-relationships.md
  and parity-enforced, but the count is not graph-checked → silent drift. WP02 now
  updates the authority + mirrored doc in lockstep.
- LENS 3 (NOTE, follow-up issue): `ContextSources` (context-sources.doctrine-layers/
  .tactics/.toolguides/.styleguides/.additional) is schema-legit but the pydantic
  `context_sources` attr is never read — extractor reads raw `.get("directives")`
  only; real profiles author `context-sources.additional` (e.g. architecture-
  decision-records) that reach NO delivery path. OUT OF SCOPE (never reaches the DRG,
  so FR-008's seam-bind can't see it). File as a follow-on issue at mission close.
- LENS 1 (SOUND): paradigm block (extractor.py:863-876) is the verbatim template for
  the WP01 procedure fix; AC-009 triple-diff is a sufficient backstop.
