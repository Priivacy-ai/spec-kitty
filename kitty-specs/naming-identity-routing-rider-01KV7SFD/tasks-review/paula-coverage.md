# Paula Patterns — Post-Tasks Coverage Review (WP decomposition)

**Mission:** `naming-identity-routing-rider-01KV7SFD` · **Reviewer:** paula-patterns (architecture-scout)
**Date:** 2026-06-16 · **Posture:** adversarial completeness — default "GAPS" until every derivation site
is proven to land in exactly one WP. All claims verified with a FRESH exhaustive `rg` over `src/`.

## Verdict (headline)

**GAPS-FOUND (2 site gaps + 1 ratchet-reach hole).**

1. **`lanes/worktree_allocator.py:169` (`mid8(lanes_manifest.mission_id)`) is owned by NO WP** — a true
   coverage gap **and** a build-breaker once WP01 renames `mid8`→`_mid8` and drops it from `__all__`
   (the module-level `from …branch_naming import …, mid8, …` at line 28 raises `ImportError` on load).
   The plan (IC-05) explicitly assigned it to "IC-02 → `resolve_mid8`", but neither WP03 nor WP04 lists
   it in `owned_files`. It is contract-sensitive (`try/except ValueError → short_id = None`), so it
   belongs in the WP03 contract class.
2. **WP02's guard self-test (T021) is underspecified** — it plants only a bare `mission_id[:8]`. A
   detector that misses the `str(raw_mission_id)[:8]` / intermediate-var shapes would still pass T021,
   re-introducing the exact blind spot the mission exists to kill. The self-test must plant all 5 Paula
   shapes, and the detector's name predicate must match `raw_mission_id` (see §Ratchet reach).

Everything else is COMPLETE: 18 of the 19 derivation sites land in exactly one WP, no double-covers,
WP01's internal-caller list is exact, and the deferred `parent.parent` class is correctly fenced.

---

## Site → WP coverage matrix

Complete fresh-`rg` inventory of live mission-`mid8` derivations in `src/` (docstrings/comments and
foreign-id `[:8]` excluded — see True Negatives). "Shape" marks the 5 var-name-independent forms Paula
found in the scope review.

### Slice sites (`<expr>[:8]`)

| # | site | shape | owning WP | flag |
|---|------|-------|-----------|------|
| 1 | `mission_runtime/resolution.py:171` `str(raw_mission_id)[:8]` | **M1** | WP04 (T012) | OK (but see ratchet) |
| 2 | `context/mission_resolver.py:163` `mid8=mission_id[:8]` | — | WP04 (T011) | OK |
| 3 | `doctrine_synthesizer/apply.py:745` `mid8=mission_id[:8]` | — | WP04 (T011) | OK |
| 4 | `doctrine_synthesizer/apply.py:831` `mid8=mission_id[:8]` | — | WP04 (T011) | OK |
| 5 | `git/sparse_checkout.py:286` `mid8 = mission_id[:8]` | — | WP04 (T011) | OK¹ |
| 6 | `runtime/next/_internal_runtime/retrospective_terminus.py:69` (local `_mid8` def) | — | WP04 (T011) | OK² |
| 7 | `retrospective/generator.py:112` `mid[:8] == mission_handle` | **M5** | WP04 (T012) | OK³ |
| 8 | `status/aggregate.py:250` `mission_id[:8] if mission_id else ""` | — | WP03 (T005) | OK |
| 9 | `cli/commands/doctor.py:3070` `mission_id[:8]` (except-fallback) | — | WP03 (T007) | OK⁴ |
| 10 | `cli/commands/doctor.py:3162` `mission_id[:8]` (except-fallback) | — | WP03 (T007) | OK⁴ |
| 11 | `cli/commands/mission_type.py:643` `mission_id_meta[:8]` | **M2** | WP04 (T012) | OK |
| 12 | `cli/commands/agent/workflow.py:292` `mid[:8]` | **M3** | WP04 (T012) | OK⁵ |
| 13 | `dashboard/scanner.py:438` `mission_id[:8] if mission_id else None` | — | WP03 (T006) src + WP02 ratchet-test | OK (split, not dup) |
| 14 | `cli/commands/implement.py:386` `mission_id[:8] …` | — | WP03 (T008) | OK |
| 15 | `cli/commands/agent/mission.py:772` `raw_mid[:8]` | **M4** | WP04 (T012) | OK |

### Call sites (`mid8()` / hand-rolled compose)

| # | site | owning WP | flag |
|---|------|-----------|------|
| 16 | `lanes/worktree_allocator.py:169` `mid8(lanes_manifest.mission_id)` | **NONE** | **GAP + build-breaker** |
| 17 | `core/mission_creation.py:321` `f"{human_slug}-{mid8(mission_id)}"` | WP05 (T015) | OK |
| 18 | `core/worktree.py:367` `f"{human_slug}-{mid8(mission_id)}"` | WP05 (T016) | OK |
| 19 | `lanes/branch_naming.py:206/257/473` internal `mid8(...)` | WP01 (T001) | OK |

Footnotes:
1. WP04 T011 quotes the site as `mid8 = _mid8(mission_id)`; the actual current code is
   `mid8 = mission_id[:8]`. Same site, slightly stale wording — still owned and routed. Not a gap.
2. `retrospective_terminus.py` carries its **own local `_mid8` shadow function** (def at :67,
   `return mission_id[:8]` at :69). WP04 owns the file; FR-009 deletion applies. OK.
3. M5 is a `==` selector comparison (`mid[:8] == mission_handle`), not a producer — WP04 T012 notes
   "preserve the guard semantics". Routing must compare against `resolve_mid8(...)`, not blindly
   substitute a producer. Flagged in WP04 risk note; adequate.
4. doctor.py:3070/3162 are the `except ValueError:` **fallback** arms; the primary call (`_mid8` →
   `from branch_naming import mid8 as _mid8`) is at 3068/3160. WP03 T007 routes both to `resolve_mid8`
   and removes the now-dead try/except. After WP01's rename the `import mid8 as _mid8` would break, but
   WP03 (depends on WP01) rewrites it — covered.
5. workflow.py:292 already has `resolve_mid8` imported at :299 for a sibling helper — the seam is
   on-hand, routing is mechanical.

**Coverage tally:** 18/19 sites owned exactly once. **1 uncovered** (#16). **0 double-covered**
(scanner.py's WP02 entry is a `tests/`-only ratchet entry, not a source edit — the intended split).

---

## WP01 internal-caller completeness check — PASS

Fresh `rg '\bmid8\(' src/specify_cli/lanes/branch_naming.py`:

```
122: def mid8(mission_id: str) -> str:   (the def)
206: suffix = f"-{mid8(mission_id)}"
257: return f"{_MISSION_PREFIX}{human_slug}-{mid8(mission_id)}"   (mission_branch_name)
473: return f"{_MISSION_PREFIX}{human_slug}-{mid8(mission_id)}-{lane_id}"   (lane_branch_name)
```

WP01 T001 names exactly `206 / 257 / 473`. **Complete and accurate — no missed internal caller.**

**Adjacent hazard (not WP01's, but unowned):** WP01 drops `mid8` from `__all__` and renames the def.
There are **three module-level `from …branch_naming import …, mid8`** importers in the tree:
- `core/mission_creation.py:28` — owned by WP05 (removes the import; OK).
- `core/worktree.py:364` — owned by WP05 (removes the call; OK).
- `lanes/worktree_allocator.py:28` — **owned by NO WP (gap #16)** → ImportError at load after WP01.

A `from x import mid8 as _mid8` (doctor.py:3066/3158) also breaks after the rename, but WP03 owns and
rewrites those. Only worktree_allocator falls through.

---

## Ratchet-reach check (WP02) — PARTIAL / HOLE

WP02 T018 names the detector targets as: `mission_id`, `mid`, `raw_mid`, `*_id_meta`, and `str(<id>)[:8]`
calls; T020 keeps `invocation_id[:8]` from tripping. Mapping the 5 Paula shapes:

| shape | site | T018 named pattern | caught as-specified? |
|-------|------|--------------------|----------------------|
| M1 `str(raw_mission_id)[:8]` | resolution.py:171 | `str(<id>)[:8]` | **ONLY IF** the inner-name predicate matches `raw_mission_id` — it is **not** literally `mission_id`/`mid`/`raw_mid`/`*_id_meta`. If the predicate is an exact-name set of those four, M1 ESCAPES. |
| M2 `mission_id_meta[:8]` | mission_type.py:643 | `*_id_meta` | yes |
| M3 `mid[:8]` | workflow.py:292 | `mid` | yes |
| M4 `raw_mid[:8]` | mission.py:772 | `raw_mid` | yes |
| M5 `mid[:8]` | generator.py:112 | `mid` | yes |

**The hole:** M1's operand inside `str(...)` is `raw_mission_id`, which is **none of** the four exact
names in T018's list. The subtask says "catch `str(<id>)[:8]` calls" and "the 5 shapes Paula found", so
the *intent* is correct — but the *named predicate* is underspecified: an implementer who builds an
exact-name allow-set `{mission_id, mid, raw_mid, *_id_meta}` satisfies the literal subtask wording and
**still misses M1** (the original blind-spot regrowing). Fix: the predicate must be a substring/glob
match on `*mission_id*` (so `raw_mission_id` matches) OR `raw_mission_id` must be added explicitly.

**The amplifier:** WP02 T021's guard self-test plants only `mission_id[:8]`. It does **not** plant
`str(raw_mission_id)[:8]` (M1) or `mid[:8]`/`raw_mid[:8]`/`mission_id_meta[:8]`. So a detector blind to
M1 would **pass T021 green** — the self-test cannot detect the very regression it must prevent. This is
the most dangerous gap on the ratchet side because it is silent.

**Remediation (one subtask edit):** make T021 plant all 5 shapes (string-wrapped, intermediate-var,
`_meta`-suffixed) and assert each is flagged; and make T018's name predicate substring/glob, not
exact-set. These are the cheapest changes that make SC-005's "the ratchet's coverage demonstrably
includes the missed shapes" honest.

(Honesty-note scope is correct: WP02 T020 already requires the docstring to name the deferred
`feature_dir.parent.parent` repo-root class and the helper-indirection limit — matches Paula Finding 3.)

---

## Deferred-class boundary check — PASS (with one watch)

The `feature_dir.parent.parent` repo-root class (~9 sites, deferred to #1716/#1832) is NOT pulled into
any WP subtask. Confirmed two of these live **inside files a WP edits**:
- `cli/commands/agent/workflow.py:793,820` — WP04 owns the file but scopes the edit to line 292 only
  (and the risk note says "do not refactor the module"). Not pulled in.
- `dashboard/scanner.py:255,571` — WP03 owns the file but scopes to line 438. Not pulled in.

**Watch (not a gap):** WP03/WP04 do not carry an *explicit* "do NOT touch the `parent.parent` sites in
this same file" line; the fence is the global C-005 + the per-line targeting + WP02's honesty note. An
implementer in scanner.py/workflow.py could be tempted. Recommend a one-line reviewer note in WP03/WP04
("the `feature_dir.parent.parent` reads in this file are the deferred repo-root class — leave them").
Adequate as-is, cheap to harden.

---

## owned_files vs reality — PASS

Every `owned_files` path across WP01–WP07 exists post-flatten (spot-checked the non-obvious ones:
`src/runtime/next/_internal_runtime/retrospective_terminus.py`, `src/mission_runtime/resolution.py`,
`scripts/docs/_typer_walker.py`, `tests/architectural/test_docs_cli_reference_parity.py`,
`src/doctrine/skills/spec-kitty-charter-doctrine/SKILL.md`). No typo'd or non-existent module paths.
`create_intent` test paths are new-file declarations (expected absent). No issue.

---

## True negatives (verified out-of-scope, correctly excluded by all WPs)

- `invocation/executor.py:469` `invocation_id[:8]` — foreign identity domain; WP02 T020 explicitly
  must not trip on it.
- `runtime/next/runtime_bridge.py:183` — a **comment** describing `resolve_mid8`; the actual derivation
  (:191) already routes through `resolve_mid8`. Already-adopted, not a shadow.
- SHA/hash `[:8]`/`[:12]` (glossary, dossier, skills/manifest_store, charter fixture_adapter, auth
  loopback state, git sha) — non-mid8.
- `branch_naming.py:139/192/408` and `mission_runtime/context.py:99/112` — the **seam internals / the
  single sanctioned derivation home** (KEEP; WP02 sanctions these as the only `[:8]` homes).

---

## Recommendations to the planner (smallest safe edits)

1. **Add `src/specify_cli/lanes/worktree_allocator.py` to WP03's `owned_files`** (it is contract-sensitive:
   `mid8(...) → try/except ValueError → None`; route to `resolve_mid8(...) or None`). Closes gap #16 and
   the WP01-rename build-breaker. Add a subtask mirroring T007's "conscious-decision" pattern.
2. **WP02 T021: plant all 5 Paula shapes** (`str(raw_mission_id)[:8]`, `mid[:8]`, `raw_mid[:8]`,
   `mission_id_meta[:8]`, bare `mission_id[:8]`) in the guard self-test; **WP02 T018: make the inner-name
   predicate substring/glob** (`*mission_id*` matches `raw_mission_id`) so M1 cannot escape.
3. **(Cheap hardening)** Add a one-line "leave the `feature_dir.parent.parent` reads — deferred class"
   note to WP03 (scanner.py) and WP04 (workflow.py) reviewer guidance.
