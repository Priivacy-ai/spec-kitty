# Clean-Before-Touch Synthesis — Mission B (write-side adoption)

**Squad:** randy (code smells), paula (test smells), pedro (feasibility/sequencing) — all profile-loaded,
2026-06-17, HEAD stacked on Mission A (`feat/read-path-error-fidelity`).
**Charter:** clean up / refactor the surfaces we will touch BEFORE touching them, so the adoption is
mechanical (operator directive). Folds into plan **D-9** (pre-refactors), **D-10** (Fix-don't-litigate /
C-008 / #1970), **D-11** (user-doc). Source files: `randy-code-smells.md`, `paula-test-smells.md`,
`pedro-feasibility.md`.

---

## The one thing that changes the plan

**paula's CRITICAL (S-1 / A-1): the write-side suites are BLIND to the swap.**
`tests/.../test_status_transition.py` passes `repo_root=` explicitly at every call, so they exercise the
*caller-supplied* root, never the re-derivation the adoption deletes. The FR-004 idempotency divergence
(flattened-arm `destination_ref`=`target_branch` vs inline `_current_branch`=git HEAD) has **zero
witnessing test today**. Verification-by-deletion (NFR-003) is therefore unsafe until a characterization
net exists — deleting an inline walk would keep a green suite that proves nothing.

**Consequence (already folded into plan D-9 + contracts C-SIMPLECASE/C-TARGET):** the characterization
net (**IC-CHARNET**) lands FIRST, before any adoption WP. It is the gate that makes every later deletion
provable.

---

## Pre-refactor verdicts (pedro, code-grounded on HEAD)

| Move | Verdict | Folds into |
|------|---------|-----------|
| PR-2 topology-true characterization net (5 root-walk sites, full ULID + real coord-worktree + submodule) | **SAFE-NOW, FIRST** | **IC-CHARNET** |
| PR-1 extract byte-identical lock-root (`emit::_feature_status_lock_root` ≡ `wpl::_repo_root_for_lock`) into one `workspace/root_resolver.py` helper | **SAFE-NOW** | **IC-DEDUP** |
| PR-4 retire `prompt_source` + `aggregate.py` `surface=` (0 readers, grep-proved) | **SAFE-NOW** | **IC-RETIRE** (FR-006) |
| PR-3 `store.py` ancestor-scan early-return tidy | SAFE-NOW (thin, free boy-scout) | in-WP IC-STORE |
| PR-5 placement-compose helper in `core/worktree.py` (collapse :384/:396 join) | SAFE-NOW (thin) | in-WP IC-WT |
| PR-6 unify `status_transition._repo_root_for_feature` toward canonical resolver | **RISKY** — feeds `destination_ref`/write-target, NOT equivalence-only | → **IC-COORD** under its own FR-004 guard |
| PR-7 "tidy" `_identity_for_request` second factory | **SKIP** — entrance to deferred #1716 ~2094-LOC authority | OUT (C-003 / D-1) |
| PR-8 unify `_read_contract_from_transaction_target` S2 ladder | **SKIP** — the #1716 topology-authority root | OUT (C-003 / D-1) |

**Key code facts pedro verified by reading bodies (not the inventory):**
- emit/wpl lock-root bodies are **byte-identical** (same topology classifier, same `resolve_canonical_root`,
  same 3 `.parent.parent` fallbacks) → PR-1 is the highest-confidence de-dup.
- `status_transition._repo_root_for_feature` is a **different, simpler** bare `.parent.parent` walk — NOT
  the same helper; do not assume "all 5 root walks are one body." It is the RISKY one because it feeds the
  write-target.
- A shared home already exists (`workspace/root_resolver.py::resolve_canonical_root`); the residual is only
  the primary/ad-hoc fallback shape.

## randy (code smells) — the latent bug is the feature

`research/reduction-census.md` already pinned it: the flattened arm computes `destination_ref` =
`target_branch` (CWD-invariant) while the inline path uses `_current_branch` = git HEAD
(`status_transition.py:291`). That divergence is the FR-004 correction — reframed from a defer-reason into
the guarded feature, witnessed by the IC-SIMPLECASE all-base keystone test (NFR-006) + the C-TARGET
before/after on-disk-target idempotency test.

## paula (test smells) — deletion targets encoded as contracts

Beyond S-1/A-1: S-2/S-3 flagged that existing tests encode the FR-006 deletion targets (`prompt_source`,
`surface=`) **as contracts**. Those test retirements must be **atomic with** the FR-006 deletion (one WP),
or the suite goes red on a correct deletion. Folded into plan: IC-RETIRE owns both the src deletion and its
test retirement.

---

## Sequencing (now the plan's canonical order)

```
IC-CHARNET (characterization net — makes deletions provable)  ─┐  land FIRST
IC-DEDUP   (lock-root shared helper — before EMIT/WPL fan out) ─┘
        ↓
adoption ICs (EMIT / WPL / LE / STORE / WT / COORD / LANES) — parallel, each consumes a factory fragment
        ↓
IC-SIMPLECASE (keystone flat test) + IC-DOCS — any time
IC-RETIRE (FR-006 deletion + its test retirement, atomic)
```

PR-6 does NOT land as a pre-refactor — it is absorbed by IC-COORD under FR-004's guard (the only place the
write-target change is proven, not assumed).
