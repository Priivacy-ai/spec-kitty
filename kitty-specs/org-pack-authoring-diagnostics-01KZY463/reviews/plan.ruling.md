# Operator ruling #2 — FR-004's `org_validate` carve-out

**Date**: 2026-08-14
**Issued by**: operator, via Orchestrator Orry
**Status**: BINDING. This ruling **replaces** the acceptance bar for FR-004's carve-out
treatment in `spec.md`, and for every passage of `plan.md` that depends on it. Any verifier,
refuter or later-phase agent evaluating FR-004's carve-outs evaluates them against *this*
ruling, not against the original FR-004 text or the review findings that shaped it.

This is the second ruling on this mission. The first
([`spec.ruling.md`](./spec.ruling.md)) narrowed FR-001 to documentation-only and remains in
force, untouched by this one.

---

## Why this ruling exists

Plan-phase fresh sweep finding **PLAN-FRESH3-001** (severity 4) established that open PR
**#2719** ("feat: doctrine org init from local/git template") adds a `--template` path to
`org init` that renders an arbitrary template tree instead of the minimal three-file stub.
FR-004's carve-out at `org_validate` — `validate_pack(pack_path, check_drg_root=False)` — is
justified in the spec by the claim that `org init` output is always that minimal stub. For a
`--template`-rendered pack, that justification fails.

The operator was offered three resolutions (accept a merge-order constraint with a tracked
follow-up; hold the work package until #2719 lands; or make the carve-out premise-independent)
and chose **premise-independent**. A read-only investigation was then commissioned to
establish whether that was achievable before this ruling bound anything. Its report is at
`/home/jeroennouws/dev/SK-missions/_readiness/3387-fr004-carveout-assessment.md`.

The investigation found something stronger than expected, verified independently by the
orchestrator against this checkout:

- **The check is already content-conditional.** FR-004's diagnostic fires only when
  `drg_dir.glob("*.graph.yaml")` is non-empty and the pack root's is empty — mirroring the
  existing `_validate_drg` fragment scan at `pack_validator.py:506-508`. It keys off pack
  *content*, never off which caller is asking or how the pack was produced.
- **`org_init`'s scaffold writes `drg/fragment.yaml`** — a filename that cannot match
  `*.graph.yaml`. Verified directly in `src/specify_cli/cli/commands/doctrine.py`.
- Therefore the `org_validate` carve-out **has never protected against anything** for the
  shape its own justification cites. It is decorative today and actively harmful tomorrow: it
  suppresses the diagnostic precisely when a pack that began as a stub later accumulates real
  `drg/*.graph.yaml` content with no pack-root graph — the exact destructive shape FR-004
  exists to catch, and the shape sibling mission #3384 documents.
- PR #2719 is therefore a *second* way the written premise breaks, not the only way. The
  premise was already false against `main` as it stands today.
- **No implementation exists yet.** `grep -rn "check_drg_root" src/ tests/` returns zero hits;
  `status.events.jsonl`'s latest event is `PlanCompleted` with no work packages materialised.
  The entire cost of this change is editorial.

## The ruling

### 1. `doctrine.py:org_validate` — the carve-out is DROPPED

`org_validate`'s `validate_pack()` call does **not** pass `check_drg_root=False`. The
diagnostic is live there by default.

The call site passes **`check_drg_root=True` explicitly**, with a brief comment recording why
it is written out rather than left implicit. Rationale, and it is this mission's own subject:
if a future refactor changes `validate_pack()`'s default, an implicit reliance on that default
would change `org_validate`'s behaviour silently and nothing would fail. Writing it explicitly
makes the dependency visible and lets AC-7 assert it directly. The one-line addition is
semantically inert against today's default.

This keeps `doctrine.py` in the mission's touched-file set as a benign, non-functional edit.
That is accepted. The overlap with PR #2719 is then an ordinary co-edit — #2719 does not call
`validate_pack` anywhere in its 5483-line diff — and carries no premise risk.

### 2. `pack_assembler.py` — the carve-out STANDS, unconditional

`assemble_pack()`'s `validate_pack(output_dir, check_drg_root=False)` at
`pack_assembler.py:335` is unchanged. Its justification is structural, not an assumption about
callers: no write path in the assembler (`_copy_artifacts`, `_copy_drg_fragments`) can produce
a pack-root `*.graph.yaml`. It is load-bearing —
`tests/specify_cli/doctrine/test_pack_assembler.py:184-188` uses fragment names matching
`*.graph.yaml`, so without the carve-out that test's `assert result.ok is True` breaks.

**The two carve-outs do not stand or fall together.** Any text treating them as one shared
architectural guarantee is wrong and must be split.

### 3. The false passage must be corrected regardless

`spec.md:413-424` asserts that a uniformly-applied default-error severity "would fail both
call sites on every invocation… and `org_validate`'s call on every freshly-scaffolded org
pack, including the currently-passing `test_doctrine_org_validate_accepts_valid_pack`". This
is **factually false against this checkout**: the onboarding scaffold's `drg/fragment.yaml`
never trips the check, so that test would not fail. This inaccuracy predates the operator's
decision and would need correcting even had the decision gone the other way.

### 4. The merge-order constraint is DISSOLVED

`plan.md`'s "Resolution — a merge-order constraint for the operator to decide" block and the
"Open-PR premise risk" bullet in IC-04's Risks are removed. There is no longer an operator
decision pending here. The Chokepoint section's open-PR write-scope check itself **stays** —
it was a genuine gap, and its enumeration of the 18 open PRs is verified accurate — but the
#2719 sub-section shrinks to a short statement that FR-004's correctness no longer depends on
`org_init`'s output shape.

### 5. AC-7 inverts, and gains a positive-fire case

AC-7 currently asserts `check_drg_root=False` is passed at `org_validate`'s call. It must
assert the opposite. It also gains a new positive case with no fixture in the suite today: a
pack scaffolded by `org init`, then given a real `drg/*.graph.yaml` fragment and no pack-root
graph, produces the `drg_root_graph_missing` diagnostic through `doctrine org validate`. That
case is the whole point of dropping the carve-out and must be tested, not merely asserted.

## Scope limits

- **FR-001, FR-002 and FR-003 are untouched.** Do not re-open them. The FR-001
  documentation-only ruling remains binding in full.
- This ruling does not change the mission's scope boundary, its topology (`lanes`,
  create-time and irreversible), or its one-PR shape.
- It does not authorise any other spec change. The edits it requires are confined to FR-004's
  own section, its one Verified-Code-Surfaces row at `spec.md:90`, and the `plan.md` passages
  that depend on them.

## Instruction to the next verifier

The acceptance bar for FR-004's carve-outs is **this file**. A verifier handed the original
spec text will re-derive the original verdict and file the dropped carve-out as a regression.
That would be wrong.

Verify that: the two carve-outs are treated **separately** and for their own reasons; the
`org_validate` call passes an explicit `True` rather than silently relying on a default; the
false passage at `spec.md:413-424` is corrected rather than merely reworded; AC-7 asserts the
absence of the override **and** carries the new positive-fire case; and the plan's merge-order
constraint is gone while the open-PR write-scope check survives. A change that drops the
carve-out but leaves the shared-justification prose, the false passage, or the merge-order
block standing is an **incomplete** application and is a finding.
