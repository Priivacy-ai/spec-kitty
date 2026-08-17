# Design Decisions Tracer — org-pack-authoring-diagnostics-01KZY463

Seeded at the plan phase per the mission-tracer-files procedure (Charter Standing Order #3).
Records decisions worth remembering later (implement, review, post-merge) that are not
self-evident from the spec text alone.

## 1. FR-001 re-scope: documentation-only, per binding operator ruling

The spec's original FR-001 (a shared suffix constant + a `pack_validator.py` near-miss mismatch
diagnostic for `*.contract.yaml` files + removal of `snapshot.py`'s dead `_ARTIFACT_BUCKETS`
table) was written on the premise that ADR `2026-08-13-1`
(`docs/adr/3.x/2026-08-13-1-built-in-mission-subtree-stays-nested-retire-legacy-step-contracts.md`,
shipped in unmerged PR #3378) was proposed-and-unratified, making the legacy
`MissionStepContract`/`step_contracts.py` surface fair game for a small consolidating change.

That premise was false: the ADR's own frontmatter/body both read `status: Accepted`, deciding
Option B — the nested `packs/built-in/missions/` layout is canonical and the legacy
step-contract surface is retired **in its entirety**. The operator ruled (`reviews/spec.ruling.md`,
2026-08-13, binding) that FR-001 is narrowed to exactly two things: (a) correct the guide's
documented suffix at `:65`/`:140` from `*.contract.yaml` to `*.step-contract.yaml`, and (b) cite
ADR `2026-08-13-1` in the same guide section so the reader learns the corrected suffix is not a
durable authoring target. No code, no constant, no diagnostic. **Why this matters later**: a
reviewer handed only the original spec text (not the ruling) will re-derive the old, larger
verdict and flag the docs-only FR-001 as under-specified — the ruling document, not the spec's
FR-001 prose, is the acceptance bar. This plan's Charter Check and Implementation Concern Map
(IC-01) both cite the ruling explicitly for this reason.

## 2. `check_drg_root` as a keyword-only parameter, default `True`

FR-004's new DRG-root-graph-mismatch check would unconditionally fail two pre-existing, currently
passing call sites if applied uniformly: `pack_assembler.py:assemble_pack()`'s internal
round-trip `validate_pack(output_dir)` call (the assembler never writes a pack-root graph, only
`drg/*.graph.yaml` fragments — `_copy_drg_fragments`, `:475-539`) and
`doctrine.py:org_validate`'s call against a pack scaffolded by `doctrine org init` (which writes
exactly three files — `org-charter.yaml`, `drg/fragment.yaml`, `README.md` — never a pack-root
graph, by design: it's an additive DRG-extension-fragment stub, not a standalone pack).

Two alternatives to a parameter were considered and rejected:

- **Extend the assembler to also emit a pack-root graph** — rejected: an unrelated, larger
  architecture change to the assembler that this mission doesn't otherwise need.
- **Default the whole check to advisory instead of error** — rejected: blunts the diagnostic for
  the author-facing case that is this mission's actual target, given the destructive
  "zeroes the action grain" consequence sibling mission #3384 documented.

**Decision**: `validate_pack()` gains `*, check_drg_root: bool = True`. The default (`True`)
serves the author-facing CLI entry point (`pack validate`) and any other full-pack-authoring
caller with zero code change at those call sites. The two call sites whose own architecture
*guarantees* the drg/-fragments-only shape regardless of authoring correctness pass
`check_drg_root=False` explicitly — a narrow, single-call-site carve-out rather than a broader
exemption. **Why this matters later**: if a third caller of `validate_pack()` is ever added, the
default must be reasoned about explicitly (author-facing → keep `True`; architecturally
guaranteed drg/-only shape → `False`) rather than copy-pasted from whichever call site is nearest
in the diff.

## 3. `profile_skipped` diagnostics are uniformly `severity="error"`

`SkippedProfile` (`src/doctrine/agent_profiles/diagnostics.py`) carries `layer`, `path`,
`profile_id`, `error_summary` — no severity field of its own. The spec's acceptance criteria say
the new `ValidationIssue` lands in "the existing `errors` or `advisories` array (per its
severity)" without specifying which. This plan decides: **always `error`**, matching
`schema_invalid`'s severity for the equivalent real-world consequence (the profile is entirely
unusable — either it never validated, or it validated but failed to merge into a usable profile).
Treating a skip as merely advisory would understate a defect this mission's own stated purpose is
to stop treating as silent/soft. **Why this matters later**: if a future mission wants to
introduce a genuinely advisory-severity skip class (e.g. a cosmetic field mismatch that doesn't
prevent the profile from loading), that would require `SkippedProfile` itself to carry a severity
signal — a doctrine-layer (`src/doctrine/`) change, out of scope for this CLI-layer-only mission,
and worth remembering as the reason this mission didn't attempt a finer-grained severity mapping.
