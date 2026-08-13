# Tracer: approach — org-pack-drg-root-graph-guard

Charter standing order 3. Architectural-approach summary for the plan phase, and how the
approach evolved from the spec's clarification Q&A into a concrete code shape.

## The spec already fixed the shape; the plan's job was pinning the mechanics

The operator's pre-specify clarification answered the two questions that would normally drive
a plan's research phase: fix shape (guard **and** scan `drg/`, not either) and mission scope
(#3384 only, #3385 stays separate). That meant this plan phase skipped Phase 0/1
(research.md/data-model.md/contracts/) entirely — there was no NEEDS CLARIFICATION left, and
no new data entity to model. The plan's actual work was reading the real code
(`_drg_helpers.py`, `action_doctrine_bundle.py`, `doctrine/drg/loader.py`,
`doctrine/drg/validator.py`) closely enough to turn "guard and scan `drg/`" into an exact,
grounded function shape, line-cited against the checkout.

## The FR-004 distinguishability requirement drove the biggest design decision

The spec's hardest constraint wasn't the load-guard itself (FR-001/FR-002 are a
straightforward existence-check-then-load) — it was FR-004's requirement that a malformed
`drg/` fragment produce a "structurally distinguishable failure signal," scoped *only* to the
org branch, while the pre-existing project-layer swallowing stays untouched. The natural-seeming
approach — add a new `except` branch somewhere, or a boolean flag threaded through — would have
either widened the existing wide catch (violating the Non-Goals scope) or required editing
`action_doctrine_bundle.py`'s except-clause code (growing the touched surface). Tracing the call
chain instead (`_load_org_layer` → `load_validated_graph` → `_load_action_doctrine_bundle`'s
`except DRGLoadError` → the CLI's own `except Exception` catch-all in
`context.py` → `_emit_error`) surfaced a cleaner mechanism: a new exception type that
deliberately does **not** subclass `DRGLoadError` sails past the existing narrow catch by
construction, with zero code change needed in `action_doctrine_bundle.py`'s actual except-clause
or in the CLI layer at all. The existing Typer JSON error surface already turns any uncaught
exception into a machine-checkable `{"result": "error", ...}` payload — the fix rides that
existing mechanism instead of adding a new one.

## The merge_layers()-reuse constraint shaped the root-vs-drg/ precedence design

C-001 forbids touching `merge_layers()`'s implementation and mandates reusing
`doctrine.drg.validator.duplicate_edge_triples` as the sole "duplicate" definition. Reading
`merge_layers`'s existing semantics (its second/`project` argument already wins label conflicts
against the first/`built_in` argument) meant FR-003's "`drg/` authoritative" requirement could
be satisfied for free, just by choosing argument order (`merge_layers(root_graph, drg_graph)`)
rather than writing new conflict-resolution logic. The dedup step composes on top of that
existing call's *output*, before that output is fed into the existing three-layer merge — no
new merge algorithm, just one new filtering pass over the sub-merge's edges.

## What would change on a similar future mission

Reading `duplicate_edge_triples`'s docstring closely (it returns the *second-and-later*
occurrence of each repeated triple, in edge order) mattered for getting the "exactly one
retained copy" outcome right by construction — worth flagging in a plan's Test Strategy section
explicitly (which occurrence survives) rather than assuming, since a future
maintainer changing edge order (e.g. `merge_layers(drg_graph, root_graph)` instead) would flip
which side's copy survives without changing the *count* the test checks.
