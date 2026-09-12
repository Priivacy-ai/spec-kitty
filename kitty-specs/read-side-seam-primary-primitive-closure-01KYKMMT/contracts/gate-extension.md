# Contract: Gate Extension, Sanctions, and Floor Transfer

Binding contract for **FR-001 / FR-005 / FR-006 / FR-007 / FR-012** and NFR-004/005/007
(IC-01, IC-05, IC-06).

## E1 — Close the holes BEFORE migrating (FR-001, IC-01)

Two holes exist today; migrating into them would trade visible semi-compliance for
invisible non-enforcement.

| Hole | Requirement |
|---|---|
| One site passes a handle from a canonicalizer the fold set does not recognise — neither routed nor allow-listed, passing **by omission** | either route the site or teach the gate that canonicalizer; the choice MUST be recorded, not implicit |
| The fold-prescription gate's three allow/flag sets bless only the **blind** primitive, so a directory obtained from the seam is in neither the sanctioned nor the flagged set | widen the sets to know the tier-1 seam idiom, so migrated sites are **affirmatively** sanctioned |

**Loosening guard**: widening a blessing set is a relaxation unless paired with a bite test
proving the gate still flags a bad read in a migrated module (NFR-005, SC-004).

## E2 — Censused callees (FR-012)

- The censused-callee set grows **2 → 4**: the kind-blind, topology-routed resolver that no
  gate covers (`resolve_feature_dir_for_mission`), **and** the primary primitive, which
  inherits the guarantee transferred from the retired use-count floors (E5).
- **Superseded framing (recorded so it is not re-derived):** an earlier draft excluded the
  primary primitive on the grounds that its fail-loud surface is zero and it was already
  censused on the anchoring axis. That held while the floors survived. Once the operator
  prescribed delegate-then-remove and FR-007 retired the floors, exclusion would leave the
  primitive policed by nothing — so it is censused here, with its end-state sanctions
  (resolver-internal + the four named foundation sites of FR-005). The ~34 in-flight sites
  are **expected red** between the gate landing and the migration completing; that red is
  the mission's acceptance signal (US8 / FR-023), not a defect.
- The ledger's Known-gap section still records which gate covers each *non*-censused
  primitive, on which axis, with its sized residual (FR-016/FR-017).
- **Alias resolution** MUST hold: an aliased import cannot defeat the census.

## E3 — Sanctions: asserted, never silently skipped

| Requirement | Detail |
|---|---|
| Per-file rationale | each sanctioned module carries a written reason |
| **Per-primitive** non-vacuity | the meta-test MUST prove a sanctioned module carries a real finding **for the newly censused primitive**, not merely for a previously censused one — otherwise the new primitive's sanctions are vacuously "proved" |
| Blanket-excluded seam internals | sites under the pinned scan-scope prefix cannot be brought into scope (the prefix set is frozen and guarded); accountability is a per-file rationale entry plus the per-primitive assertion above |
| Foundation sites (FR-005) | the four sites beneath the seam are recorded **by name** with their recursion rationale and remain unrouted (NFR-009) |

## E4 — Allow-list

- Entries are **per-site content descriptors**; no path-scoped blankets (C-003).
- **Shrink-only**, with a staleness twin-guard that reds until an entry whose site was
  routed or removed is deleted.
- For preserved sites, the existing production comment is the **rationale of record**.

## E5 — Floor retirement / transfer (FR-007, NFR-007, IC-06)

The two use-count floors count *uses of the blind primitive*. After Step 2 their subject
population is only resolver-internal and named-sanctioned sites, where a raw handle is
correct by contract — so the floors would guard nothing and instead **oblige the primitive to
keep being used**, inverting their purpose.

| Requirement | Detail |
|---|---|
| Preferred end state | **retire** both floors and transfer the guarantee to the bypass census (E2/E3) |
| Mechanical fallback | re-pin to the honest post-migration numbers, respecting the existing margin rule |
| Either way | record the **before/after integers and the reason** ("a routing shrink"), per the floors' own doctrine — never relax silently |
| Two-file edit | the floor values are asserted as bare literals in a second module too; both MUST move together |
| Companion bookkeeping | the blessed-name allow-list in the trio gate shrinks (its own failure text prescribes this — a tightening); the pin-existence test paired with the retired residual pin is retired with it (FR-014) |

## E6 — Acceptance

| Check | How verified |
|---|---|
| Bite | planted direct call reds; planted **aliased** call reds; prose mention stays green |
| No green-by-omission | planted bad read in a **migrated** module still flagged |
| Per-primitive non-vacuity | assertion parameterised by primitive; passes for the new one on its own merits |
| Allow-list integrity | stale entry reds; no path blanket present |
| Ledger parsed | mutation per primitive reds (see `ledger-grammar.md` G3) |
| Floors | either absent with the guarantee transferred, or re-pinned with before/after recorded; no test obliges the primitive to remain in use |
| Foundation sites | recorded by name, still unrouted, no resolution cycle |
| Verification scope | only the named gates run locally (C-008); the exhaustive sweep is CI's |
