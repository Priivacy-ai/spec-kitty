# Contract: Row-Aware Matrix Merge Driver Algorithm (FR-008)

**Not a new ADR** — a citation contract for the driver rewrite. The row-aware drivers replace the whole-file `_write_more_filled_side` behavior (`merge_driver.py:333/347/357`) for `spec-kitty-acceptance-matrix` and `spec-kitty-issue-matrix` over the FR-002 structured JSON schema. Cites `2026-06-24-1` (partition authority), `2026-07-23-2` (no consolidation abort).

## Inputs — 3-way, base-aware
Git invokes the driver with the merge placeholders:
- `%O` — the **common-ancestor (base)** version of the matrix.
- `%A` — **our** (current-branch / consolidation-base) version.
- `%B` — **their** (incoming-lane) version.

The driver MUST use all three. A 2-way (`%A`/`%B` only) merge cannot distinguish "the other side added a row" from "our side deleted a row" and re-leaks clobber. The base-aware requirement is why FR-009 (a real common ancestor) is a **hard predecessor** of the durability regression (IC-08 → IC-01): without a shared `%O` the driver degrades to 2-way.

## Row-key canonicalization
Rows are keyed by a **canonical identity**, not by line position or dict order:
- acceptance-matrix rows → `criterion_id` (e.g. `FR-001`, DoD id).
- issue-matrix rows → the canonicalized `issue_ref` (e.g. `#1726`; normalize `GH-1726`/`#1726`/bare `1726` to one form before keying).

Two rows with the same canonical key are the *same* row; the merge reconciles their fields. Distinct keys union.

**Intra-side collision guard:** if two *distinct* raw rows on **one** side (`%A`, `%B`, or `%O`) normalize to the same canonical key (e.g. `GH-1726` and `#1726` in the same file), the driver MUST NOT silently collapse them — it raises a structured error (or deterministically dedupes with a recorded warning). A silent collapse drops a row and is a clobber by another name.

## Per-row reconciliation (base-aware three-way)
For each key present in `%O ∪ %A ∪ %B`:
1. **Added on exactly one side** (absent in `%O`, present on one of `%A`/`%B`) → take the added row.
2. **Added on both sides** with equal content → take either; with differing content → field-level merge, else structured conflict (never silent pick).
3. **Changed on one side only** (differs from `%O` on exactly one side) → take the changed side.
4. **Changed on both sides** → field-level merge where fields are disjoint; if the same field diverges, emit a **structured conflict** result (fail-closed, no consolidation abort per `2026-07-23-2`).

## Delete-vs-stale disambiguation (the base-aware payoff)
A key **present in `%O`** but **absent on one side**:
- absent on one side, **unchanged on the other** → **intentional delete**; drop the row.
- absent on one side, **changed on the other** → the change wins (a stale non-edit does not resurrect-then-delete); keep the changed row.

A key **absent in `%O`** and absent on one side is simply a one-sided add (rule 1) — never a delete. This is precisely the case a 2-way merge gets wrong.

## Output & determinism
- Output rows in a **stable canonical order** (sorted by key) so the merge result is byte-deterministic regardless of input row order — required for idempotence (FR-012) and clean re-merges.
- Preserve computed/derived fields' provenance; the driver reconciles stored fields only and never re-authors a computed verdict (acceptance `overall_verdict` stays a property, not a merged field).

## Registration (M6 — 3 sites, see IC-08)
The driver binding MUST be updated in all three places or the algorithm is inert on real repos: the `.gitattributes` pattern (repointed `**/issue-matrix.md` → `issue-matrix.json`), `cli/commands/init.py:73,194` (new-repo attributes), and a **new forward migration** (do NOT mutate historical `m_3_2_6`).

## Security campsite (#2970 — E1)
The row-aware rewrite folds the 5 S2083 path-injection BLOCKERs in `merge_driver.py`: a red-first repro of the injection precedes the fix; the hardened path handling must not weaken any merge-reconciliation rule above.

## Verification
- Disjoint-row union test (two lanes, different keys) → no clobber.
- Stale-residue test (base row deleted on one side, untouched on the other) → row dropped.
- Same-field divergence test → structured conflict, no silent pick, no abort.
- Byte-determinism test (shuffled input row order → identical output).
- #2970 path-injection red-first regression.
