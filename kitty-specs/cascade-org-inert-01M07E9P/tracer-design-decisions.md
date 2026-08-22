# Tracer: Design Decisions — cascade-org-inert-01M07E9P

Three genuinely non-obvious design calls this plan makes, each with rationale (not silently
defaulted):

## 1. `resolve_layer_roots`'s widened shape is additive, not destructive (IC-01)

**Decision**: keep the existing `roots["org"]` key holding a single representative `Path` (pack 1,
unchanged), and add the full declaration-ordered chain under a NEW key (shape left to the
implementing WP, e.g. `roots["org_chain"]: list[Path]`).

**Why not just change `roots["org"]` to be a list?** `resolve_layer_roots` has a THIRD consumer
beyond the two cascade renderers this mission is fixing: `charter list --all-layers`
(`list_cmd.py:165`), which feeds `roots["org"]` into `CharterPackManager.list_available_detailed`
and `_template_tier_roots`, both of which have a documented `layer_roots: dict[str, Path] | None`
contract — one `Path` per layer, not a list. Changing the VALUE TYPE of an existing key silently
breaks that third consumer at the type level (a `dict[str, Path]` handed a `list[Path]` under the
same key), with no test in this mission's scope that would catch it unless one is deliberately
added. The additive-field approach avoids the type break entirely, and mirrors an established
pattern already in this codebase: `_resolve_action_bundle`'s `effective_org_root` (back-compat
single value) / `effective_org_roots` (full chain) dual-field design.

**Rejected alternative**: widen `charter list --all-layers` in the same mission to also consume
the new chain field, showing pack-2+ availability. Rejected because it is a separate,
display-only concern outside issue #3527's filed scope, and would touch
`pack_manager.list_available_detailed`'s consumption contract too — a larger, separately-reviewable
change. Filed as a follow-up recommendation instead (spec.md User Story 3).

## 2. FR-002 requires TWO changes together, verified empirically not merely asserted (IC-02)

**Decision**: the WP's own red-first test must prove BOTH halves are independently necessary
(apply half (a) alone → still red; apply half (b) alone → still red; apply both → green) before
being considered done — not just a single before/after test on the combined change.

**Why**: this mission's own spec-review squad (SPEC-ARCH-002) caught the FIRST drafted version of
this fix as a no-op — a plausible-sounding change (swap one internal function call) that measurably
did nothing, because the actual truncation happens one layer up, in the CLI command, before either
candidate function is ever reached. A single before/after test on the FINAL combined fix would not
have caught that the first draft's fix (swap-only) was insufficient — it would simply have reported
the final state as correct without exercising the failure mode the review found. The stricter
two-halves-independently-proven test design is the concrete mechanism that would have caught
Round 1's mistake automatically, had it existed then. This is the direct implementation of the
orchestrator's explicit instruction: "prove your replacement fix for FR-002 is not itself inert."

## 3. FR-003's derivation is gated on a worktree investigation, not assumed (IC-03)

**Decision**: the assigned WP must investigate whether spec-kitty execution worktrees can carry
their own dossier snapshots BEFORE implementing derivation (B) (`feature_dir.parent.parent`), and
document whichever answer it finds with file:line evidence — not silently assume single-checkout-
only.

**Why**: derivation (B) is correct ONLY if a recorded snapshot's `feature_dir.parent.parent` always
resolves to the project's REAL, org-pack-configured checkout root. If a worktree ever produces its
own `kitty-specs/<slug>/.kittify/dossiers/...` tree, that assumption breaks silently — the
derivation would read the WORKTREE's local (likely absent or stale) `.kittify/config.yaml` instead
of the primary checkout's real one, which is exactly the class of silent-wrong-data defect this
mission exists to close, not reintroduce. The spec's own investigation found this plausible but
NOT determined (the sole confirmed production caller, `migrate_cmd.py`, always resolves `repo_root`
via `locate_project_root()` from wherever the operator invoked `spec-kitty migrate` — which
suggests single-checkout, but does not by itself prove no snapshot ever originates from a worktree
path). Rather than gamble on the plausible answer, the plan makes the investigation a hard
prerequisite, with both possible outcomes stated as acceptable as long as they are documented, not
silently picked.
