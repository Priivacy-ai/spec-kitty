# Adversarial Post-Merge Behavioral Review — Debugger Debbie

**Mission:** `naming-identity-routing-rider-01KV7SFD` · **Branch:** `feat/naming-rider-3-2-1` (merged)
**Diff base:** `40e5209a5` (3.2.0) → HEAD `2a112b318`
**Lens:** dual-system-divergence mapping — prove byte-equivalence OR find a divergence the frozen-literal tests missed.
**NFR under attack:** NFR-001 "identity-derived names/paths are byte-identical before and after, for all reachable inputs."

---

## TL;DR

- The operator's **headline hypothesis is FALSIFIED**: a slug that embeds a mid8 tail *diverging* from the
  declared `mission_id` does **NOT** break parity. `resolve_mid8` returns `mission_id[:8]` (declared
  governs) for any `len(mission_id) >= 8`, **identical** to the old blind `mission_id[:8]`. The slug tail
  is never consulted when `mission_id` is present.
- The **real divergence** is in a different input dimension the frozen-literal tests never exercised:
  a **short (1–7 char) truthy `mission_id`** at the sites where the *old* code did an **unguarded
  `mission_id[:8]`** and the new code routes through `resolve_mid8` (which **declines to `""`** below 8
  chars). Old returned the short slice; new returns `""`.
- **VERDICT: DIVERGENCE-FOUND.** One MEDIUM (control-flow flip in `status/aggregate.py` → `save()`),
  three LOW (display/registry/event-payload `mid8` fields). Reachable from malformed / hand-edited /
  test-fixture `meta.json` (short `mission_id` literals are present in the test corpus, e.g. `"01KMID"`,
  `"test"`, `"m1"`); **not** reachable from the clean production mint path (`str(ULID())` is always 26 chars).

---

## The divergence primitive

`resolve_mid8(slug, *, mission_id)`:
- `mission_id` present and `len >= 8` → `mission_id[:8]` — **ignores the slug tail entirely** (declared identity governs, NFR-003).
- `mission_id` present but `len < 8` → `""` (the `len >= 8` branch is not taken; falls through to the decline).
- `mission_id is None` → `""` (declines an unconfirmable coincidental tail).

Old pre-merge idioms it replaced:
- `mission_id[:8]` (inline, **unguarded**) — slices anything, including short ids.
- `mid8(mission_id)` (raising primitive, now `_mid8`) — raised `ValueError` below 8.
- `mid8(mission_id)` inside `try/except ValueError: short = mission_id[:8]` (doctor tolerance).

The decisive question per site is therefore **NOT** the slug tail (always byte-equal) but: *does an unguarded
`[:8]` reach `resolve_mid8` with a `mission_id` of length 1–7?* If yes → old returns the short slice, new
returns `""` → **DIVERGES**.

### Empirical input-matrix proof (the primitive)

| input (slug, mission_id) | old `mission_id[:8]` | new `resolve_mid8` | verdict |
|---|---|---|---|
| `('foo', '01KV7SFD56KRZBDV977S9FMQMM')` full ULID | `'01KV7SFD'` | `'01KV7SFD'` | byte-equal |
| `('foo', '01KV7SFD')` exactly 8 | `'01KV7SFD'` | `'01KV7SFD'` | byte-equal |
| `('foo-01KV7SFD', '01KV7SFD…')` **matching** embedded tail | `'01KV7SFD'` | `'01KV7SFD'` | byte-equal |
| `('foo-01KV6510', '01KV7SFD…')` **DIVERGENT** embedded tail | `'01KV7SFD'` | `'01KV7SFD'` | **byte-equal** — operator hypothesis FALSIFIED |
| `('foo', '01KV7SF')` 7 chars | `'01KV7SF'` | `''` | **DIVERGES** |
| `('foo', '01KMID')` 6 chars (test fixture) | `'01KMID'` | `''` | **DIVERGES** |
| `('foo', 'test')` 4 chars (test fixture) | `'test'` | `''` | **DIVERGES** |
| `('foo', 'm1')` 2 chars (test fixture) | `'m1'` | `''` | **DIVERGES** |

The divergence window is exactly **`1 <= len(mission_id) <= 7`** (truthy but sub-mid8).

---

## Per-site input-matrix verdicts

Legend: **GUARDED** = an explicit `len(mission_id) >= 8` (or `isinstance ... and len >= 8`) check gates the
`resolve_mid8` call, so the short-id window is unreachable → byte-equal. **`or None`-ABSORBED** = the
`""` decline is mapped back to the old sentinel, so the short-id window collapses to the same value →
byte-equal. **UNGUARDED** = old did a bare `mission_id[:8]`; short-id window reaches `resolve_mid8` →
**DIVERGES**.

| Site | Old code | New code | Short-id (1–7) | None | Full / embedded-divergent | Verdict |
|---|---|---|---|---|---|---|
| `mission_runtime/resolution.py:177` `_mid8_from_primary_meta` | `str(raw_mission_id)[:8]` inside `if … >= 8` | `resolve_mid8(slug, mission_id=str(raw))` inside same `>= 8` guard | unreachable (guarded) | returns `""` (early) | `[:8]` == `[:8]` | **GUARDED → byte-equal** |
| `coordination/status_transition.py:267` (WP01 deletion) | `if mid8 is None and mid and len>=8: mid8=_seam_mid8(mid)` then `resolve_transaction_mid8(mid8=mid8,…)` | drop pre-derivation, `mid8=None`, let `resolve_transaction_mid8` cascade | byte-equal (old guard `>=8` == cascade's own `>=8`; short → both fall to slug/legacy cascade) | byte-equal | byte-equal | **byte-equal across full matrix** |
| `cli/commands/implement.py:391` | `mid8(...) or (mid[:8] if isinstance and len>=8 else None)` | `meta["mid8"] or (resolve_mid8(...) or None)` | `""`→`or None`→`None` == old `None` | `None` == `None` | byte-equal | **`or None`-ABSORBED → byte-equal** |
| `lanes/worktree_allocator.py:172` | `try: mid8(mid) except ValueError: None` | `resolve_mid8(...) or None` | `""`→`or None`→`None` == old `None` (ValueError path) | `None` == `None` | byte-equal | **`or None`-ABSORBED → byte-equal** |
| `cli/commands/agent/mission.py:774` | `raw_mid[:8] if isinstance and len>=8 else None` | `resolve_mid8(...) if isinstance and len>=8 else None` | unreachable (guard kept) | `None` | byte-equal | **GUARDED → byte-equal** |
| `cli/commands/agent/workflow.py:293` | `meta["mid8"] or (mid[:8] if isinstance and len>=8 else None)` | same guard wrapping `resolve_mid8` | unreachable (guard kept) | `None` | byte-equal | **GUARDED → byte-equal** |
| `cli/commands/mission_type.py:647` | `mission_id_meta[:8] if len>=8 else ""` | `resolve_mid8("", mid=…) if len>=8 else ""` | unreachable (guard kept) | n/a (`""` default) | byte-equal | **GUARDED → byte-equal** |
| `git/sparse_checkout.py:290` | `mission_id[:8]` after a `continue` on `len<8` | `resolve_mid8(...)` after same `len>=8` continue-guard | unreachable (guarded by `continue`) | unreachable | byte-equal | **GUARDED → byte-equal** |
| `retrospective/generator.py:117` (selector compare) | `mid[:8] == handle` (3rd OR-clause; `mid==handle` is 1st) | `candidate_mid8 == handle` | clause only decides when `len(mid) >= 9` (else 1st clause `mid==handle` already fired); at `>=9` `resolve_mid8==mid[:8]` | `mid=""`→`""` never spuriously matches a real handle (same as old `""[:8]==""`) | byte-equal | **byte-equal (clause-order defends it)** |
| `runtime/.../retrospective_terminus.py:135` | `_mid8(mid)` = `mid[:8]` (deleted shadow), terminus holds full ULID | `resolve_mid8(slug, mid)` | divergent only on a short id; terminus is documented to always hold a full ULID | — | byte-equal | **byte-equal under stated precondition** |
| `core/mission_creation.py:323` / `core/worktree.py:367` (#2000 compose) | `f"{strip_numeric_prefix(slug)}-{mid8(mission_id)}"` | `mission_dir_name(slug, mid8=resolve_mid8("", mid))` | `mission_id` is a freshly-minted `str(ULID())` (26) — short window unreachable | — | byte-equal (verified in mission review §4) | **byte-equal (full-ULID precondition)** |
| `doctrine_synthesizer/apply.py:746,832` | `mid8=mission_id[:8]` (event payload) | `mid8=resolve_mid8(slug, mid)` | **UNGUARDED** — short `mission_id` → old short slice, new `""` | `mission_id` is a param; if a short id is supplied the emitted event `mid8` diverges | byte-equal | **DIVERGES (LOW — event payload field)** |
| `context/mission_resolver.py:163` `_build_index` | `mid8=mission_id[:8]` (guard only `if not mission_id: continue`) | `mid8=resolve_mid8(entry.name, mid)` | **UNGUARDED** — short id → old `'m1'`, new `''` | not reachable (`continue`) | byte-equal | **DIVERGES (LOW — display only; see below)** |
| `dashboard/scanner.py:445` | `mission_id[:8] if mission_id else None` | `resolve_mid8(feature_dir.name, mid) or None` | **UNGUARDED** — short id → old short slice, new `None` | `None` == `None` (the `else None` / `or None`) | byte-equal | **DIVERGES (LOW — registry `mid8` field)** |
| `status/aggregate.py:256` `MissionStatus` | `mid8 = mission_id[:8] if mission_id else ""` | `mid8 = resolve_mid8(mission_slug, mission_id)` | **UNGUARDED** — short id → old short slice (truthy), new `""` (falsy) | `""` == `""` | byte-equal | **DIVERGES (MEDIUM — flips `save()` control flow)** |

---

## Confirmed DIVERGENCES

### D-1 (MEDIUM) — `status/aggregate.py:256` flips `MissionStatus.save()` from proceed → raise

**Input:** `meta.json` with a short truthy `mission_id`, e.g. `{"mission_id": "01KMID", "mission_slug": "shortid-mission"}` (6 chars; `"01KMID"` is a literal already used in the test corpus, `tests/unit/mission_loader/test_command.py:446`).

**Old behavior:** `mid8 = "01KMID"[:8] = "01KMID"` (truthy).
**New behavior:** `mid8 = resolve_mid8("shortid-mission", mission_id="01KMID") = ""` (declined, falsy).

**Reproduced end-to-end** via `MissionStatus.load(root, slug)`:

```
mission_id = '01KMID'
NEW mid8   = ''
OLD mid8   = '01KMID'
save() guard (mission_id is None or not mid8) NEW -> True   (RAISES MissionMetadataUnavailable)
save() guard                                  OLD -> False  (proceeds to BookkeepingTransaction.acquire)
```

This is the one site where the diverged `mid8` is **not** a leaf display value but **drives control flow**:
`MissionStatus.save()` (aggregate.py:683) guards `if self.mission_id is None or not self.mid8: raise
MissionMetadataUnavailable`. A short-id mission that previously *committed a bookkeeping transaction* (with
the wrong-but-truthy `mid8="01KMID"`) now *raises* before acquiring the transaction. The downstream
`BookkeepingTransaction.acquire(..., mid8=...)` call no longer runs.

**Severity: MEDIUM.** It is a genuine NFR-001 violation (control-flow output is not byte-identical for a
reachable input), but: (a) the input is a *malformed* `mission_id` (a real ULID is always 26 chars; the
clean mint path `str(ULID())` cannot produce it; no read-side ULID-length validation exists, so only
hand-edited/corrupted/test meta hits it); (b) arguably the new raise is *more correct* than committing a
transaction keyed on a bogus 6-char "mid8". But the spec promised byte-parity, not an improvement, and this
path is not covered by any frozen-literal test (all used full ULIDs). It is a behavioral change that slipped
the NFR-001 net.

### D-2 (LOW) — `context/mission_resolver.py:163` `ResolvedMission.mid8` empties for short ids

Old `mid8 = mission_id[:8]` → e.g. `"m1"`; new `resolve_mid8(entry.name, "m1") = ""`. **Bounded impact:**
`resolve_mission()` matches on `m.mission_id` (`== handle` / `.startswith(handle)`), **never on `m.mid8`** —
so resolution itself is unaffected. The diverged value surfaces only in `AmbiguousHandleError.__str__` /
`.to_dict()` (the displayed `mid8 {c.mid8}` line and the `--mission {c.mid8}` recovery hint, and the JSON
`"mid8"` field). For a short-id mission the recovery hint goes from `--mission m1` to `--mission ` (empty).

### D-3 (LOW) — `dashboard/scanner.py:445` registry `mid8` goes `short → None`

Old `mission_id[:8]` (e.g. `"test"`); new `resolve_mid8(...) or None = None`. The dashboard registry record
`mid8` field changes for a short-id mission. `tests/test_dashboard/test_scanner_mission_id.py:239` asserts
`record["mid8"] == record["mission_id"][:8]` — but only against **full-ULID** fixtures, so it never exercised
the short-id case. A short-id fixture would now break that very assertion (new `None != "test"`).

### D-4 (LOW) — `doctrine_synthesizer/apply.py:746,832` event-payload `mid8` empties for short ids

Old `mid8=mission_id[:8]`; new `mid8=resolve_mid8(slug, mission_id)`. If a short `mission_id` is passed to
`_apply_one` / `_emit_conflict_rejections`, the emitted `retrospective.proposal.applied` /
`.rejected` event carries `mid8=""` instead of the old short slice. Lowest reachability (retrospective
apply path; `mission_id` typically a full ULID resolved upstream), but the unguarded `[:8]→resolve_mid8`
swap is the same shape as D-1/D-2/D-3.

---

## Falsified hypotheses (so they are not re-litigated)

- **F-1 (operator's headline) — "a slug whose embedded tail diverges from `mission_id` makes `resolve_mid8`
  disagree with old `[:8]`." FALSIFIED.** When `mission_id` is present (`len >= 8`), `resolve_mid8` returns
  `mission_id[:8]` and never consults the slug tail (matching/divergent/absent all yield the same value).
  This is exactly the old blind `[:8]`. Proven for both matching (`foo-01KV7SFD`) and divergent
  (`foo-01KV6510`) tails against `mission_id=01KV7SFD…` → both `'01KV7SFD'`.
- **F-2 — "the WP01 `status_transition.py` pre-derivation deletion changes routing." FALSIFIED.** The deleted
  `if … len>=8: mid8=_seam_mid8(mission_id)` guard is byte-equivalent to `resolve_transaction_mid8`'s own
  `if mission_id >= 8: return mission_id[:8]` cascade step; for short/None ids both old and new fall through
  to the identical slug/legacy cascade. Byte-equal across the full {full, 8, short, None, NNN-, embedded} matrix.
- **F-3 — "`doctor.py` `or mission_id[:8]` tolerance diverges." FALSIFIED.** Old `try: mid8(mid) except
  ValueError: short=mid[:8]`; new `resolve_mid8(...) or mission_id[:8]`. For a short id both yield
  `mission_id[:8]` (old via the except branch, new via the `or` fallback since `resolve_mid8` returns the
  falsy `""`). Byte-equal — the `or mission_id[:8]` was correctly chosen to absorb the decline.
- **F-4 — "`implement.py` / `worktree_allocator.py` `or None` sites diverge." FALSIFIED.** `resolve_mid8`'s
  `""` is mapped to `None` by `or None`, matching the old `else None` / `except: None` sentinel exactly.

---

## Site tally

- **Routed sites examined:** 16 (the ~15 FR-001 sites + the WP01 `status_transition` deletion + the two #2000 composes).
- **Confirmed byte-equivalent:** 12 (resolution `_mid8_from_primary_meta`, status_transition WP01 deletion,
  implement, worktree_allocator, agent/mission, agent/workflow, mission_type, sparse_checkout,
  retrospective/generator selector, retrospective_terminus, mission_creation #2000, worktree #2000).
- **Confirmed DIVERGENT:** 4 — `status/aggregate.py` (MEDIUM, control-flow), `context/mission_resolver.py`
  (LOW, display), `dashboard/scanner.py` (LOW, registry), `doctrine_synthesizer/apply.py` ×2 (LOW, event payload).

The single common root cause across all four: **an old *unguarded* `mission_id[:8]` was routed to
`resolve_mid8` without a `len >= 8` gate and without an `or <old-sentinel>` absorber**, so the
new decline-to-`""` is observable for the short-`mission_id` (1–7 char) input class — which the
frozen-literal tests never exercised (they all used full 26-char ULIDs).

## Suggested structural close (single intervention, not 4 point-fixes)

The guarded/absorbed sites prove the safe pattern. Bring the four divergent sites onto it:
- Sites that need the old short-slice value preserved → restore a `len >= 8` gate or use
  `resolve_mid8(...) or mission_id[:8]` (the doctor.py pattern) so a short id keeps its old slice.
- Or, if the *new* `""`/raise behavior is intended (treat a sub-ULID `mission_id` as invalid), record it as a
  deliberate NFR-001 carve-out in the spec and add a short-`mission_id` regression test at each of the four
  sites — closing the test-coverage gap that let the divergence merge.

---

## FINAL VERDICT: **DIVERGENCE-FOUND** — byte-parity holds for the slug-tail dimension (operator hypothesis falsified) but BREAKS for a short (1–7 char) `mission_id` at 4 unguarded sites; the consequential one (`status/aggregate.py` → `save()` proceed→raise) is MEDIUM, the other three LOW; all reachable only via malformed/test `meta.json`, none via the clean production ULID mint path.
