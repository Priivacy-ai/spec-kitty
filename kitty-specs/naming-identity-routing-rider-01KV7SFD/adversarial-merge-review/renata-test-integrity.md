# Adversarial Test-Integrity Red-Team — `naming-identity-routing-rider-01KV7SFD`

**Reviewer:** reviewer-renata (profile-loaded: `src/doctrine/agent_profiles/built-in/reviewer-renata.agent.yaml`)
**Lens:** reverse-speccing + test-scaffolding-as-design-smell + standards-enforcement. Attack = "delete the impl, does the test still pass?" mutation testing.
**Branch:** `feat/naming-rider-3-2-1` (merged), HEAD `2a112b318` (post-merge review that already remediated H-1/M-1).
**Verdict:** **tests CONSTRAIN** (one minor ratchet-hygiene GAP found — non-defeating, latent future-regression window).

> Scope note: the mission-review-report describes the PRE-remediation tree (H-1 import error, M-1 missing markers). HEAD `2a112b318` already fixed both. This red-team is against HEAD, where all 114 target tests pass.

---

## 1. Byte-parity tests — do they run the PRODUCTION routed path or a re-implementation?

### Golden RHS are hard-coded literals — CONFIRMED
- `test_2000_compose_routing.py` `_FROZEN` dict (L43–49): hard literals (`"foo-01KV7SFD"`, `"my-feature-01KV7SFD"`, `"foo-01KV6510-01KV7SFD"`). NOT re-calls.
- `test_mid8_contract_sensitive_routing.py`: `FULL_MID8 = "01KV7SFD"` pinned as a literal, explicitly commented "hard-coded, NOT FULL_ULID[:8]". Per-assertion RHS are string literals.
- `test_mid8_direct_routing.py`: `_GOLDEN_MID8 = "01KV7SFD"` literal.

### The harder check — production path vs re-implementation (the real finding)
Two distinct patterns, and they are NOT equal in strength:

- **`TestScannerContract` (contract test) — STRONG.** Calls real `build_mission_registry(tmp_path)` against on-disk `meta.json` fixtures. This is genuine production. **Mutation proof:** I reverted `dashboard/scanner.py:445` from `resolve_mid8(...) or None` back to the old inline `mission_id[:8] if mission_id else None`. Result: the verification-by-deletion guard `test_no_inline_mid8_slices_remain_after_routing` FAILED (greps the production module for `mission_id[:8]`), AND the ratchet tripped (see §2). So reverting that routed site to its old inline slice is **caught**.
- **The `_routed(...)` static helpers — WEAKER, by design.** `TestDoctorShortIdTolerance`, `TestImplementContract`, `TestWorktreeAllocatorContract`, `TestScannerRoutedExpression` each define a private `_routed()` that **re-implements** the routed expression (e.g. `return resolve_mid8(slug, mission_id=mission_id) or None`) rather than importing the production function. These pin the *contract of the expression shape*, not the production call site. If someone reverted `worktree_allocator.py:172` to inline `[:8]`, these `_routed` tests would still pass (false-negative) — **but** the ratchet (§2) and the grep-guard `test_no_inline_mid8_slices_remain_after_routing` would fire. So the constraint is real; it just lives in the ratchet + grep-guard, not in these per-class tests. This is an acceptable division of labour, not a gap — the byte-parity classes prove *the contract is preserved*; the ratchet proves *the production site routes through the seam*. Flagged for awareness, not as a defect.
- **`test_2000` T017-B/C — adequate.** T017-B asserts the seam function `mission_dir_name(slug, mid8=resolve_mid8(...))` equals the hard literal. T017-C cross-checks seam-output == inline-`mid8`-output. The `_mid8 as mid8` import (the H-1 fix) does NOT weaken this: `_mid8` IS the genuine private production primitive, and T017-C compares two genuinely-different code paths (inline f-string vs `mission_dir_name` seam). The report's "tautology-adjacent" note on L70/L121 is fair but harmless: those lines feed T017-A/C, whose load-bearing assertion (T017-B) is against the hard literal. NOT a tautology.

**Verdict §1:** byte-parity tests genuinely constrain. Reverting a routed *production* site to inline `[:8]` is caught (by ratchet + grep-guard); the per-expression `_routed` helpers are contract-shape pins by design.

---

## 2. The ratchet (WP02, `test_no_worktree_name_guess.py`) — defeatable? Mis-accounted?

### Baseline accounting re-derived independently — CONFIRMED EXACT
I re-ran the AST short-id detector's predicate by hand across `src/`. **Exactly 7 raw mission-identity `[:8]` slices**, identical to the pinned `_SHORTID_BASELINE_RAW_MATCHES = 7`:

| Site | Class |
|------|-------|
| `branch_naming.py:146` | HOME (`_mid8` primitive) |
| `branch_naming.py:199` | HOME (`resolve_mid8`) |
| `branch_naming.py:415` | HOME (`resolve_transaction_mid8`) |
| `mission_runtime/context.py:99` | HOME (`IdentityFragment` invariant) |
| `mission_runtime/context.py:112` | HOME (`IdentityFragment.derive`) |
| `doctor.py:3073` | allow-listed tolerance |
| `doctor.py:3165` | allow-listed tolerance |

= **5 slices in 2 home files + 2 doctor allow-listed = 0 unaccounted consumers.** The report's "7 = 5 homes + 2 doctor" is correct (read "5 homes" as "5 slices across the 2 home files"). I checked each home file: none is a consumer-in-disguise — `branch_naming.py` is the seam; `context.py` is the documented single-derivation point with a self-checking invariant. The doctor entries are genuinely the `or mission_id[:8]` RHS *of an already-routed `resolve_mid8` call* (diagnostic tolerance), not a bypass.

### Negative control actually fails — CONFIRMED
Mutation: reverted `scanner.py:445` to inline `mission_id[:8]`. Both ratchet tests fired correctly:
- `test_no_mission_shortid_slice_or_failover_bypass_outside_seam` → FAIL (new offender `scanner.py:445`).
- `test_shortid_consumer_class_is_empty_against_pinned_baseline` → FAIL (`assert 8 == 7`).
The detector self-tests (`test_shortid_detector_self_test_flags_all_five_shapes`, `_failover_bypass_self_test`) plant all 5 Paula-shapes + the `_mid8(...)` bypass + spare `invocation_id[:8]`, and pass — so the substring predicate genuinely catches the wrapped/suffixed blind spots.

### Trivially defeatable? — the ratchet is HONEST about its own limit
The honesty note (L478–495) correctly states the detector is a **syntax-level tripwire**, defeated by helper indirection (`def _short(x): return x[:8]`). The real guarantee is verification-by-deletion (WP03/04/05 deleted every consumer slice; suite stayed green). I accept this framing — it does not over-claim. The allow-list does NOT hide a real consumer (re-derived above).

### GAP FOUND (minor, ratchet-hygiene) — the name-COMPOSE allow-list is now stale
`_ALLOWED_SITES` (the *name-compose* detector, distinct from the short-id one) still carries three entries described as un-routed pre-existing composes:
```
src/specify_cli/core/mission_creation.py:321
src/specify_cli/core/worktree.py:367
src/specify_cli/core/worktree.py:370
```
But WP05 (#2000) **already routed those sites through `mission_dir_name`/`resolve_mid8`**. I ran `_scan_file()` on both modules: **zero idiom violations** at those lines. So the three carve-outs now exempt nothing.

Why this is a (small) gap, not just dead config: the name-compose detector's only hygiene test, `test_allow_list_entries_are_real_and_benign`, checks **only `lineno <= line_count`** (the line exists) — it does NOT verify the line is still an offender the detector would flag. Contrast the short-id ratchet, which has a `test_shortid_consumer_class_is_empty_against_pinned_baseline` baseline cross-check that *would* catch a stale entry. The name-compose ratchet has **no equivalent baseline cross-check**, so its allow-list can rot undetected. Concrete risk: if a future edit reintroduces a hand-rolled `f"{slug}-{mid8}"` compose at exactly one of those three lines, the ratchet would silently allow it (false-negative window of 3 lines).

This is **not** a behavioral regression and **not** a gameable mission test — the production sites are correctly routed. It is a latent weakening of the ratchet's future-regression guarantee. Recommended follow-up: drop the three now-routed entries from `_ALLOWED_SITES` (the comment already calls them a queued follow-up — that follow-up has effectively landed), and add a name-compose baseline cross-check mirroring the short-id one.

---

## 3. FR-002 (`test_mid8_direct_routing`) — real ExecutionContext + IdentityFragment?

**CONFIRMED genuine, not a stub.**
- `test_execution_context_carries_single_derived_mid8` builds a real `ExecutionContext` + `IdentityFragment.derive(...)` and asserts the carried mid8 is consumed as-is.
- `test_identity_fragment_rejects_inconsistent_mid8` constructs a real `IdentityFragment(mission_id=_FULL, mid8="WRONG888", ...)` and asserts `ValueError("...single-derived...")`.

**Mutation proof:** I disabled the `__post_init__` invariant (`if False and ...`) in `mission_runtime/context.py`. Result: `test_identity_fragment_rejects_inconsistent_mid8` → **FAILED ("DID NOT RAISE")**. The test genuinely binds to the production single-derivation invariant; deleting/weakening the impl breaks it. Restored.

---

## 4. #1888 verify-and-close — phantom-path production path?

**CONFIRMED genuine verify-and-close.**
- `ownership/validation.py` is **byte-unchanged** in the mission diff (`git diff baseline..HEAD --stat` → empty). True verify-and-close (fix pre-landed `991162c0a`).
- `test_validation_existence.py` imports the real `validate_glob_matches` (L27) and constructs real `OwnershipManifest` objects against a real `tmp_path` filesystem — NOT a synthetic dict. The 5 tests exercise the production existence-check branch (`validation.py:370–383`, literal-zero-match → hard error) and create_intent suppression (L364–369).
- **Deletion test:** if `validate_glob_matches` were deleted, the L27 import fails → collection error → all 5 fail. They cannot pass without the production function. Confirmed.

---

## 5. Marker hygiene + `test_2000` import fix

**CONFIRMED (M-1 remediated at HEAD).** All six routing/byte-parity files now carry `pytestmark`:
`test_mid8_contract_sensitive_routing.py`, `test_mid8_direct_routing.py`, `test_mid8_caller_routing.py`, `test_2000_compose_routing.py`, `test_branch_naming_ssot_entrypoint.py`, `test_validation_existence.py` — all `[pytest.mark.unit]`. `test_pytest_marker_convention::test_every_test_file_declares_a_pytestmark_marker` passes. CI will not silently skip them.

The `test_2000` `_mid8 as mid8` import fix (H-1) restores collection AND does not weaken the cross-check — `_mid8` is the genuine production primitive, and T017-C still compares two distinct code paths. Full target suite: **114 passed**. Architectural ratchet: **8 passed** (clean tree).

---

## Final verdict

**Tests CONSTRAIN.** Every load-bearing claim in the mission-review-report's correctness argument survives adversarial mutation:
- Reverting a routed production site to inline `[:8]` is caught (ratchet + grep-guard) — proven by mutation.
- The short-id ratchet's "7 = 5 homes + 2 doctor / 0 unaccounted consumers" accounting is re-derived **exactly**; nothing is mis-counted as a home; the negative control fires.
- FR-002 binds to a real, self-checking `IdentityFragment` invariant — proven by mutation.
- #1888 is a genuine verify-and-close against an unchanged production validator exercised through the real filesystem path.
- Markers present; CI won't skip.

**No false-positive / gameable MISSION test found.** The `_routed()` helper classes are contract-shape pins by design, with the production-routing constraint correctly delegated to the ratchet + grep-guard.

**One ratchet-hygiene GAP (non-defeating, latent):** `_ALLOWED_SITES` retains 3 now-routed entries (`mission_creation.py:321`, `worktree.py:367`, `worktree.py:370`) that the detector no longer flags, and the name-compose ratchet lacks a baseline cross-check to catch the staleness — opening a 3-line future-regression false-negative window. Recommend dropping the stale entries and adding a name-compose baseline cross-check mirroring `test_shortid_consumer_class_is_empty_against_pinned_baseline`. This does not change the mission verdict (behavior correct, no current bypass), but it is a real erosion of the ratchet's forward guarantee.
