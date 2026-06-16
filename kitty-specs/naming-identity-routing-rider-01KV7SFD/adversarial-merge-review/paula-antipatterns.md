# Paula Patterns — Adversarial Post-Merge Anti-Pattern Red-Team

**Mission:** `naming-identity-routing-rider-01KV7SFD`
**Branch:** `feat/naming-rider-3-2-1`
**Diff base:** `40e5209a5` … **HEAD:** `2a112b3187`
**Lens:** architecture-scout / recurring boundary-leak & whack-a-field detector
**Date:** 2026-06-16

---

## Headline verdict: FINDINGS

The **committed merged tree is CLEAN** on every anti-pattern axis (silent-empty,
dead-code, synthetic-fixture, completeness, read-path ripple). But the **working
tree carries two uncommitted edits that revert the mission's core guarantees**
and break the ratchet. These are not in any commit (HEAD and the squash both
hold the correct code), so they are working-tree contamination — but they are
live on disk right now and red-light the architectural gate.

---

## 1. Silent-empty-return — CLEAN (committed) / 1 working-tree regression

Every routed `resolve_mid8` site preserves its prior `""`/`None`/short-id
contract with an explicit sentinel and a per-site rationale comment. Audited all
bare-result sites for a decline-to-`""` that previously produced a real value or
raised:

| Site | Old | New | Equal? |
|------|-----|-----|--------|
| `worktree_allocator.py:170` | `mid8(id)` raised→`None` | `resolve_mid8(slug,id) or None` | YES — `id<8`→`""`→`None`; `id>=8`→`id[:8]` |
| `agent/mission.py:772` | `raw_mid[:8]` (guarded `>=8`) | `resolve_mid8(slug,raw_mid)` (same guard) | YES — declared governs |
| `agent/workflow.py:293` | `mid[:8]` (guarded `>=8`) | `resolve_mid8(name,mid)` (same guard) | YES |
| `doctor.py:3073/3165` | `mid8(...)` w/ dead try/except | `resolve_mid8(...) or mission_id[:8]` | YES — `or` tolerance preserved |
| `status/aggregate.py`, `implement.py`, `mission_type.py`, `apply.py`, `sparse_checkout.py`, `core/*` | inline `[:8]` / compose | `resolve_mid8(...)` + sentinel / `mission_dir_name` | YES |

**`retrospective/generator.py:115` — intentional semantic tightening (NOT a silent
failure).** Old `mid[:8] == handle` vs new `resolve_mid8(slug,mid) == handle`.
Byte-equal for any real `mission_id >= 8`. Diverges ONLY when `mid` is a 1–7-char
string equal to the handle: old matched, new declines (`""`). That is a
deliberate correctness improvement (an identity-less meta no longer spuriously
matches a short handle) and the call is a *selector* comparison, not a name
compose. Defensible; worth a one-liner in the spec, no behavioral risk.

**No bare `except Exception: return ""/None/[]` introduced** in any routed file.
The `doctor.py` dead `try/except ValueError` was consciously *removed* (the
raising `mid8` it guarded is gone).

---

## 2. Dead code — CLEAN

Every new helper has a live caller:

- WP07 guard helpers `_extract_command_path`, `_is_registered_path`,
  `_doctrine_source_snippets`, `_chop_at_shell_stop`, `_build_live_app` — all
  called from `tests/architectural/test_docs_cli_reference_parity.py`
  (`_build_live_app` used at 5 sites; the rest by the 3 guard self-tests).
- Ratchet detector helpers in `test_no_worktree_name_guess.py` — exercised by the
  self-test that plants all 5 recurrence shapes.
- `_mid8_from_primary_meta` (resolution.py) — called at `resolution.py:118`
  (the read-path producer) + 5 direct tests.
- `retrospective_terminus.py` shadow `def _mid8` — genuinely DELETED (FR-009).

No new function is importer-less outside tests.

---

## 3. Synthetic-fixture tests — CLEAN

The FR-002 / direct-routing tests invoke the **real production path**, not a
hand-built dict:
- `test_mid8_direct_routing.py` writes real `meta.json` to `tmp_path` and calls
  `_mid8_from_primary_meta(tmp_path, slug)` — the actual producer.
- The FR-002 IdentityFragment test constructs a real `IdentityFragment` and
  asserts its `__post_init__` guard fires.
- Byte-parity assertions use frozen HEAD-captured literals, not
  `resolve_mid8(x)==resolve_mid8(x)` tautologies.

---

## 4. Completeness re-grep — CLEAN on the committed tree

`rg --pcre2 '(mission_id|mid|raw_mid|*_id_meta)[:8]'` over `src/` yields **8 raw
code slices on disk right now**, but only **7 on the committed tree (HEAD)**. The
committed-tree 7 are fully accounted by the ratchet's pinned baseline:

```
branch_naming.py:146 / 199 / 415   → 3 SEAM HOMES
mission_runtime/context.py:99 / 112 → 2 SEAM HOMES (IdentityFragment)
doctor.py:3073 / 3165               → 2 allow-listed diagnostic tolerances
=> 0 unaccounted consumers.
```

`str(...)[:8]` wrapped: NONE. The ratchet's `_SHORTID_HOME_FILES`,
`_SHORTID_NAMED_EXCLUSIONS` (`invocation_id[:8]`), and `_SHORTID_ALLOWED_SITES`
match the live homes+doctor set exactly. **Against the committed tree the full
ratchet passes (verified: 30 passed, 0 unaccounted).**

The 8th slice exists only because of Finding **W-1** below.

---

## 5. resolution.py:171 read-path ripple — CLEAN

`_mid8_from_primary_meta` is the read-path mid8 producer feeding
`resolve_mission_read_path` (its only non-test consumer, `resolution.py:118`).
The route replaced `return str(raw_mission_id)[:8]` with
`resolve_mid8(mission_slug, mission_id=str(raw_mission_id))`. Under the
`len(raw_mission_id) >= 8` guard, `resolve_mid8` returns `mission_id[:8]` in
**both** of its branches (declared governs; a divergent slug tail never wins), so
the value is byte-equal regardless of `mission_slug`. The decline/empty contract
(`return ""`) below the guard is untouched. Downstream consumers see no change.

---

## FINDINGS (working-tree contamination — not in merged history)

### W-1 (HIGH) — `src/specify_cli/dashboard/scanner.py:445` — FR-003 route reverted to a raw inline slice
```
HEAD/squash:  else (resolve_mid8(feature_dir.name, mission_id=mission_id) or None)
working tree: else (mission_id[:8] if mission_id else None)
```
This re-introduces an **8th unaccounted `mission_id[:8]` slice** outside the seam
homes+doctor allow-list — exactly the whack-a-field anti-pattern the mission
exists to kill. The rationale comment above it still claims "Route through the
authoritative resolver" — so the **comment now lies about the code**. This
single edit fails three tests:
`test_no_worktree_name_guess.py::test_no_mission_shortid_slice_or_failover_bypass_outside_seam`,
`::test_shortid_consumer_class_is_empty_against_pinned_baseline` (8 != pinned 7),
and `test_mid8_contract_sensitive_routing.py::test_no_inline_mid8_slices_remain_after_routing`.
**Uncommitted** (`git diff HEAD` only; not in `f617d857a` or HEAD). Fix: `git restore src/specify_cli/dashboard/scanner.py`.

### W-2 (HIGH) — `src/mission_runtime/context.py:100` — FR-002 IdentityFragment guard neutered
```
HEAD:         if self.mid8 != expected:
working tree: if False and self.mid8 != expected:
```
This dead-codes the IdentityFragment consistency invariant — the single
derivation home the whole seam relies on — so a mismatched `mid8` no longer
raises. Classic guard-defeat. **Uncommitted.** Fix: `git restore src/mission_runtime/context.py`.

> Both W-1 and W-2 are absent from every commit in `40e5209a5..HEAD`; HEAD is
> clean. They are live edits on the working tree. If they were committed they
> would be MERGE-BLOCKERS; as working-tree dirt they are a "discard before you
> trust the gate" hazard. No evidence they originated from the mission.

---

## Scout matrix summary

| Anti-pattern | Committed tree | Working tree |
|--------------|----------------|--------------|
| Silent-empty-return | CLEAN | W-1 (comment/code lie) |
| Dead code | CLEAN | W-2 (dead-coded guard) |
| Synthetic-fixture | CLEAN | CLEAN |
| Completeness (unaccounted mid8) | CLEAN (7=7) | W-1 (8th slice) |
| Read-path ripple | CLEAN | CLEAN |

**Release decision (Paula):** The *mission as merged* is releasable on these five
axes — routing core is honest, severable, byte-equal, zero unaccounted
consumers, no dead code, no synthetic fixtures. **Do not run the gate against the
dirty working tree** — restore `scanner.py` and `context.py` first, or the
architectural ratchet red-lights on contamination the mission did not introduce.
