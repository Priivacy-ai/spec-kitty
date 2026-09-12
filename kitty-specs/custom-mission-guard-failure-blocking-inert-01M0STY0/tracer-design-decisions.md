# Design Decisions

> Capture the rationale that would otherwise evaporate.

**Prompting questions**
- What decision was made?
- What alternatives were considered?
- What was the rationale — why this option over the others?

---

## Entries

<!-- YYYY-MM-DD — Decision: [what]. Alternatives: [what else]. Rationale: [why this one]. -->

2026-08-24 — Decision: the manifest-consulting logic for FR-006's `blocking_artifact_names`
signal is computed entirely in `runtime_bridge_io.py` (I/O layer) and handed to
`runtime_bridge_cores.py` as plain snapshot data. Alternatives considered: calling
`required_artifacts_for` directly from inside `evaluate_guards_strict`. Rejected — that would
import `charter.missions` (non-stdlib) into `runtime_bridge_cores.py`, redding the live
`tests/architectural/test_bridge_cores_import_boundary.py` AST-walk gate. Rationale: the spec's
own FR-006 layering note already mandates this split; this plan carries it through to concrete
module/function placement rather than re-deciding it.

2026-08-24 — Decision: `ArtifactPresenceSnapshot.blocking_artifact_names`'s `None` (no manifest
anywhere) vs. real `frozenset` (manifest resolved, possibly empty) states are kept strictly
distinct, checked only via `is None`, never via falsiness. Alternatives considered: collapsing
both to `frozenset()` and using a separate boolean "manifest_found" flag. Rejected — that would
duplicate the same information as two fields that could disagree, and would still risk a future
`if not blocking_artifact_names:` bug reintroducing the exact SPEC-FRESH-001 collapse this
mission fixes. Rationale: one field, one `is None` check, is the smallest surface area for the
invariant to be violated by a future edit.

2026-08-24 — Decision: `doctrine/missions/step_projection.py::project_artifact_name_set` is left
unedited despite being named in the mission's blast-radius list. Alternatives considered: routing
the blocking-filtered set through a modified `project_artifact_name_set` instead of
`required_artifacts_for`. Rejected — `project_artifact_name_set` is a different, still-needed
projection (artifact_key -> path_pattern, used by `resolve_configured_artifact_name` and
`_presence_filenames_for`'s presence *set*), and `required_artifacts_for` already has its own
independent `blocking`-filtering logic that FR-006 explicitly names as the mechanism to reuse.
Rationale: reusing an existing, already-correct, already-tested function beats modifying a
differently-scoped one to grow a second responsibility.

2026-08-24 — Decision: WP sequencing stages `blocking_artifact_names`'s population in two steps —
a minimal test-only stub in WP01 (to ATDD-test `evaluate_guards_strict`'s new branch in
isolation), replaced by the real org-tier resolution in WP02. Alternatives considered: building
both in a single WP. Both are spec-compliant; this plan chose the staged form for
reviewability — it isolates the change to the hardest-gated file (`runtime_bridge_cores.py`,
bound by the import-boundary gate) into its own small, easily-audited diff, separate from the
larger org-tier plumbing change.

2026-08-24 — Decision: the Contract-moves-check classifies the new `blocking_artifact_names`
field/Protocol-property as additive/backward-compatible/internal, requiring no `spec-kitty-events`
coordination. Alternatives considered: treating any dataclass/Protocol shape change as a
contract move by default, requiring a flagged operator decision. Rejected as overcautious here —
the spec's own Key Entities section states both consumers are internal to this repo, and neither
type crosses a process boundary or is serialized. Rationale: the spec's own text answers this
question; escalating past it would be re-litigating a settled point rather than exercising real
judgment.
