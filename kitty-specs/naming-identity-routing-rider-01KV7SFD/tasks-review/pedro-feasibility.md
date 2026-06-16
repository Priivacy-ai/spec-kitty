# Python-Pedro feasibility + anti-laziness review — Naming/Identity Routing Rider

**Reviewer:** python-pedro (profile-loaded) · **Date:** 2026-06-16 · **Branch:** `feat/naming-rider-3-2-1`
**Method:** every cited `file:line` verified against HEAD with `rg`/`sed`; seam contracts re-derived from
`branch_naming.py`; #1888 surface re-traced to its actual wiring; the 5 byte-parity landmines re-checked.

**Verdict: NEEDS-REMEDIATION** before `/spec-kitty.implement`. The routing core is sound and the file:line
refs are mostly accurate, but there are **two build-breaking gaps** (an orphaned `mid8()` caller and an
import-alias breakage), **one ticket the fix already landed for** (#1888 — the existence check exists on
HEAD), and **three mis-framed sites** that invite fake/short-cut "routing." All are fixable with prompt
edits; none require re-planning the mission.

---

## File:line accuracy summary

| Ref (WP) | Status | Note |
|----------|--------|------|
| `branch_naming.py:122/206/257/473` (WP01) | ✅ accurate | `def mid8` @122; internal callers @206/257/473 |
| `status/aggregate.py:250` (WP03) | ✅ accurate | `mid8 = mission_id[:8] if mission_id else ""` |
| `dashboard/scanner.py:438` (WP03) | ✅ accurate | `None if is_pseudo else (mission_id[:8] if mission_id else None)` |
| `doctor.py:3070/3162` (WP03) | ⚠️ accurate-but-misdescribed | already call `_mid8` (imported `mid8 as _mid8` @3066/3158), not `mid8`; see F2 |
| `implement.py:386` (WP03) | ✅ accurate | `meta.get("mid8") or (mission_id[:8] …)` |
| `git/sparse_checkout.py:286` (WP04) | ✅ accurate | `mid8 = mission_id[:8]` |
| `doctrine_synthesizer/apply.py:745/831` (WP04) | ✅ accurate | `mid8=mission_id[:8]` |
| `context/mission_resolver.py:163` (WP04) | ✅ accurate | `mid8=mission_id[:8]` |
| `retrospective_terminus.py:69` (WP04) | ❌ **wrong line + wrong framing** | `:67` is `def _mid8`; a **shadow def + 14 callers**, not a one-line route; see F3 |
| `mission_runtime/resolution.py:171` (WP04) | ✅ accurate | `return str(raw_mission_id)[:8]` |
| `agent/mission.py:772` (WP04) | ✅ accurate | `raw_mid[:8] if isinstance(raw_mid, str)…` |
| `mission_type.py:643` (WP04) | ⚠️ accurate-but-misbucketed | inside `_read_mission_mid8`, prefers `meta["mid8"]` → contract-sensitive (belongs with WP03 pattern); see F5 |
| `agent/workflow.py:292` (WP04) | ✅ accurate | `mid[:8] if isinstance(mid, str)…` |
| `retrospective/generator.py:112` (WP04) | ❌ **wrong framing** | a **comparison** `mid[:8] == mission_handle`, not a name/path derivation; see F4 |
| `core/mission_creation.py:321` (WP05) | ✅ accurate | `f"{human_slug}-{mid8(mission_id)}"` |
| `core/worktree.py:367/370` (WP05) | ✅ accurate | `branch_name = f"{human_slug}-{mid8(mission_id)}"` |
| `core/paths.py:48` chain (WP06) | ✅ accurate | authoritative `locate_project_root` |
| `ownership/validation.py` #1888 (WP06) | ❌ **fix already landed** | literal-zero-match hard error exists @ `validate_glob_matches`; see F1 |
| `invocation/executor.py:469` non-target (WP02) | ✅ accurate | `invocation_id[:8]` log message |
| `_typer_walker.walk` @145, `test_docs_cli_reference_parity.py` (WP07) | ✅ accurate | infra present, profile-subcommand parity check present |
| **`lanes/worktree_allocator.py:28/169`** (FR-010/IC-05) | ❌ **orphaned — owned by NO WP** | bare `mid8()` import+call; see F0 |

**Count of inaccurate / materially-misframed file:line refs: 5** (F0 orphan, F1 already-fixed, F2
import-alias, F3 shadow-def, F4 comparison-not-derivation) + 1 minor misbucket (F5).

---

## F0 (CRITICAL, build-breaking) — `lanes/worktree_allocator.py` is orphaned

- FR-010 and plan IC-05 **explicitly** name it: *"1 consumer `lanes/worktree_allocator.py:169` — routed
  to `resolve_mid8` by IC-02."* Verified live:
  - `:28` `from specify_cli.lanes.branch_naming import lane_branch_name, mid8, worktree_path as _worktree_path`
  - `:169` `short_id = mid8(lanes_manifest.mission_id)` (inside a `try/except ValueError` — a **contract-sensitive** site, mirrors doctor.py).
- **It is in NO WP's `owned_files`** (WP03 owns aggregate/scanner/doctor/implement; WP04 owns the 9
  direct/missed sites; neither lists worktree_allocator).
- **Consequence:** WP01 T001 renames `def mid8` → `def _mid8`. The moment WP01 lands, `worktree_allocator.py:28`
  raises `ImportError` at import time → the package won't import → **WP01's own DoD ("tests green, ruff/mypy
  clean") cannot pass**, and WP01 may not edit a file it doesn't own. This is a hard sequencing deadlock,
  not a style nit.
- **Hardening (apply before implement):** add `src/specify_cli/lanes/worktree_allocator.py` to **WP03**'s
  `owned_files` (it is a contract-sensitive `try/except` site like doctor.py) and add a subtask:
  *"route `:169` to `resolve_mid8(mission_slug, mission_id=lanes_manifest.mission_id) or None`, preserve the
  `short_id is None → skip register_lane_sparse_checkout` semantics, drop `mid8` from the `:28` import."*
  Pin a characterization test on the `None` branch (no sparse-checkout registration when mid8 absent).

## F1 (CRITICAL anti-laziness) — #1888 existence check ALREADY EXISTS on HEAD

- WP06 T022 demands a *failing* repro that "ownership validation passes a phantom/non-existent owned path
  silently," and T023 says "add the missing existence check."
- **It is already present and wired:** `ownership/validation.py::validate_glob_matches` classifies each
  `owned_files` entry and emits a **hard error** on a literal path with zero matches, a **soft warning** on
  a zero-match glob, and an **info note** when a literal zero-match is suppressed by `create_intent`
  (lines ~354–390). It is **called twice** from `cli/commands/agent/mission.py` (the WP and lane finalize
  paths), and `tests/tasks/test_finalize_ownership_routing.py` already exercises literal-zero-match → hard
  error, glob-zero-match → warning, and create_intent suppression. (Landed in `991162c0a`, mission
  01KTZVQ2 — *after* the scope review was written, which is why the synthesis still calls it "MISSING.")
- **Consequence (fakeable DoD):** T022's "failing repro" **will not fail** — the current behavior is already
  correct. An implementer will either (a) burn time confused, (b) get stuck, or (c) write a test that
  passes immediately and tick "repro fails before, passes after" **without any code change** — a textbook
  tautological-characterization fake. The DoD checkbox "phantom paths now rejected" is satisfiable with
  zero work.
- **Hardening:** re-disposition WP06's #1888 half to **verify-and-close** (matching #1971-tail). Replace
  T022/T023 with: *"Confirm `validate_glob_matches` rejects literal zero-match owned_files (it does, landed
  991162c0a), confirm it is wired into both finalize paths in `agent/mission.py`, and ADD the missing
  edge-case test if any of {create_intent suppression of a literal, zero-match `**` glob warns-not-fails,
  nested-glob literal} lacks coverage in `test_finalize_ownership_routing.py`. Issue-matrix verdict for
  #1888 = fixed-upstream/verified."* If the planner still believes there is a residual gap, the WP must
  name the **specific** uncovered path with a repro that genuinely fails on HEAD — otherwise this is not a
  code WP.

## F2 — `doctor.py:3070/3162` import alias breaks; framing says "was mid8()"

- WP03 T007 context: *"These already wrap `_mid8()` (was `mid8()`)…"*. Verified: doctor.py does
  `from specify_cli.lanes.branch_naming import mid8 as _mid8` (@3066/3158) **today** — the `_mid8` is a
  local alias of the *public* `mid8`, not WP01's future private `_mid8`. After WP01 renames the def, this
  import (`import mid8 as _mid8`) **ImportErrors**.
- WP03 owns doctor.py, and T007's "route to `resolve_mid8` + delete the dead try/except" *does* remove the
  `_mid8` usage — but the WP **never says to drop the now-invalid `from … import mid8 as _mid8` line**. An
  implementer who routes the call but leaves the import will ship an ImportError; ruff (F401) would catch
  the unused import only if nothing else uses it, but the import itself is already broken at module import.
- **Hardening:** add to T007 DoD: *"remove the `from specify_cli.lanes.branch_naming import mid8 as _mid8`
  import at both `:3066` and `:3158`; confirm `python -c 'import specify_cli.cli.commands.doctor'` succeeds
  after WP01's rename."*

## F3 — `retrospective_terminus.py` is a SHADOW DEF, not a one-line route

- WP04 T011 says: *"`retrospective_terminus.py:69 — return …`."* Wrong line and wrong shape:
  - `:67` `def _mid8(mission_id: str) -> str:` — a **duplicate private helper**;
  - `:137` `mid = _mid8(mission_id)`; then `mid` is reused at **14 call sites** (`mid8=mid` kwargs throughout).
- This is precisely the "shadow path implementation" FR-009/C-004 want **deleted**, not a value to re-route
  at one line.
- **Consequence (fakeable DoD):** an implementer can change the **body** of `_mid8` (line 69) to call
  `resolve_mid8` and tick "routed + shadow deleted" while the **duplicate `def _mid8` still exists** as a
  second implementation — exactly the shadow-survives-elsewhere fake the spec warns about (Scenario 3).
  Verification-by-deletion is defeated because the wrapper hides the shadow.
- **Hardening:** rewrite T011's terminus bullet to: *"DELETE `def _mid8` (@67); replace the single producer
  `mid = _mid8(mission_id)` (@137) with `mid = resolve_mid8('', mission_id=mission_id)` (the 14 downstream
  `mid8=mid` uses are unchanged). DoD: `grep -n 'def _mid8' retrospective_terminus.py` returns nothing."

## F4 — `retrospective/generator.py:112` is a COMPARISON, not a naming derivation

- Verified: `if mid == mission_handle or mid[:8] == mission_handle or slug == mission_handle:` — a
  **handle-matching predicate** (does the caller's handle match this mission's full id, its mid8, or its
  slug?). It does not *produce* a branch/worktree/display name.
- Routing it through `resolve_mid8` is semantically dubious: `resolve_mid8` is "name proposes, authority
  disposes" with failover + a one-shot `DeprecationWarning`. Calling it inside a tight directory-scan loop
  for a *comparison* could (a) fire the legacy-failover warning spuriously, (b) change matching semantics
  (resolve_mid8 returns `""` on decline → `"" == mission_handle` is a different predicate than the guarded
  slice), and (c) is a behavior change masquerading as a route.
- **Hardening:** either **drop this site from WP04** (it is not an identity-*derivation* shadow; it's a
  short-id *equality test*) and record it as a non-target in WP02's allow-list with justification, OR if
  kept, the WP must specify the **exact** equivalent: `_mid8`-style truncation for comparison is fine, but
  it must NOT route through the failover resolver. Pin a test that `mid[:8] == handle` semantics
  (including the `len(mid) < 8` and empty-`mid` cases) are byte-identical.

## F5 (minor) — `mission_type.py:643` is contract-sensitive, mis-bucketed into WP04

- `_read_mission_mid8` (@635) prefers `meta["mid8"]` then falls back to `mission_id_meta[:8] if len>=8 else
  ""` — the **same `meta["mid8"]`-preference + `""`-on-decline pattern** as `implement.py:386` (a WP03
  contract-sensitive site). WP04 is the "direct, no special `""`/`None`" bucket; this site has an empty-string
  decline contract.
- **Hardening:** either move `mission_type.py` to WP03's table or add an explicit per-site contract note in
  WP04 T012: *"preserve `meta['mid8']` preference; the fallback must return `''` on decline (resolve_mid8's
  natural contract), NOT raise."*

---

## Per-WP feasibility notes

### WP01 — seam SSOT entrypoint (blocked by F0)
- T001/T002 accurate. **But** removing `mid8` from `__all__` AND renaming the def to `_mid8` strands the
  external importers. `core/worktree.py` + `core/mission_creation.py` are handled by WP05; **doctor.py
  (F2) and worktree_allocator.py (F0) are not handled in time.** Because WP03/WP04/WP05 all `depend_on:
  WP01`, WP01 lands *first* and alone — at which point the tree won't import. **WP01's DoD ("tests green")
  is unachievable until F0/F2 are resolved.**
- **Fakeable DoD:** "composed names byte-identical (NFR-001)" — T004 must compare **actual composed output
  strings** for `mission_branch_name`/`worktree_dir_name`/`lane_branch_name` against frozen literals, not
  merely assert "the function still returns a value." Harden the DoD to require a snapshot/parametrized
  equality against pinned expected strings (the WP04 reviewer note already gestures at this — make it a
  hard checkbox).
- **Stuck-point:** T002 asks to confirm `resolve_mid8("", mission_id=full) == old mid8(full)`. Verified the
  body supports it (empty slug ⇒ no embedded tail ⇒ `mission_id[:8]`), so this is feasible — good.

### WP02 — ratchet AST detector
- Feasible and honestly scoped. **Sequencing risk:** `dependencies: [WP03, WP04, WP05]` but **not WP01**.
  T019's failover-bypass rule keys on "bare `_mid8(...)` outside the sanctioned homes" — `_mid8` only
  *exists* after WP01. If WP02 is allowed to start before WP01 merges, the rule references a symbol that
  isn't private yet. Add WP01 to WP02's `dependencies` (cheap, removes ambiguity).
- **Fakeable DoD:** "allow-list empty/minimal & justified" + "allow-list actually shrank" — an implementer
  can seed a *new* empty frozenset and claim "shrank from N to 0" without ever having had the N entries
  (the detector is new, so there's no prior allow-list baseline for *this* detector). Harden: require the
  self-test (T021) to **plant each of the 5 Paula shapes** (`str(x)[:8]`, `mid[:8]`, `raw_mid[:8]`,
  `_id_meta[:8]`, `mission_id[:8]`) and assert each is flagged — proving the detector has teeth, not just
  an empty list. Also require an explicit assertion that `invocation_id[:8]` is **not** flagged.

### WP03 — contract-sensitive routing (add F0's worktree_allocator)
- Site refs accurate; the contract table is correct and matches live code. T009 characterization-first is
  the right discipline.
- **Fakeable DoD:** "characterization tests … green before AND after." A test that asserts
  `resolve_mid8(slug, mission_id=x) == <hardcoded>` is only a parity proof if the hardcoded value was
  captured from the **pre-change** code. Harden: require T009 to assert the **current** site output by
  calling the *existing* code path (or pinning the literal observed from a real meta.json), and the
  post-change test to call the routed path — the reviewer must see the two converge on the same literal,
  not on `resolve_mid8`'s output compared to itself (tautology).
- **Stuck-point:** T007 doctor.py — implementer needs to know the slug to pass to `resolve_mid8`. At
  `:3066` the surrounding code has `mission_slug`; confirm it's in scope (it is — `worktree =
  CoordinationWorkspace.worktree_path(repo_root, mission_slug, short)` two lines down). Fine, but state it.

### WP04 — direct + missed sites (F3, F4, F5)
- See F3 (terminus shadow-def), F4 (generator comparison), F5 (mission_type contract). Beyond those:
- **Stuck-point:** every "missed shape" site (`resolution.py:171`, `agent/mission.py:772`,
  `mission_type.py:643`, `workflow.py:292`) reads `mission_id` from a `meta` dict and has **no slug in
  hand** at the derivation point. `resolve_mid8(slug, *, mission_id)` needs a slug arg. The WP says "pass
  the slug they have (or `""`)" — for these dict-readers the answer is `""`, which is correct
  (`resolve_mid8("", mission_id=x) == x[:8]`). **State explicitly that `""` is the right slug arg for
  meta-dict readers** so the implementer doesn't go hunting for a slug that isn't there.
- **god-module guard:** WP04 correctly warns `agent/mission.py` is a 3k-line module, edit only ~772. Good
  anti-scope-creep note. Same needed for `mission_type.py` (large) — add the locality reminder.
- **Fakeable DoD:** T013 "FR-002 verification test … no ExecutionContext-held re-derivation." This is
  un-falsifiable as written (asserting a negative across the tree). Harden: require the test to assert the
  **specific** known context-carriers (`IdentityFragment.mid8` is the only one) and to fail if a *planted*
  `ctx.mission_id[:8]` appears — otherwise it's a no-op test that always passes.

### WP05 — #2000 compose routing (seam-signature mismatch)
- Site refs accurate. **But the seam signatures differ:** `worktree_dir_name(mission_slug, *, mission_id,
  lane_id)` takes a **mission_id** (good — eliminates the `mid8()` call). `mission_dir_name(mission_slug,
  *, mid8: str)` takes a **mid8 string** (NOT mission_id). So for `mission_creation.py:321`, routing
  through `mission_dir_name` **does not remove the mid8 derivation** — the implementer still has to derive
  `mid8` to pass as the kwarg. T015's DoD "no inline `<human>-<mid8>` f-string or bare `_mid8` remains" is
  achievable for the *compose* but the *derivation* must move to `resolve_mid8('', mission_id=mission_id)`
  per FR-010, not to a fresh `_mid8` call.
- **Hardening:** T015 must say: *"derive `m8 = resolve_mid8('', mission_id=mission_id)` then
  `mission_dir_name(mission_slug, mid8=m8)`"* — otherwise the implementer either keeps a bare slice (defeats
  the WP) or re-imports the now-private `_mid8` (a ratchet violation WP02 would flag). Also note
  `mission_creation.py:321` uses the *canonical NNN-stripped* grammar; confirm `mission_dir_name` (which
  strips NNN-) matches the current `f"{strip_numeric_prefix(slug)}-{mid8}"` byte-for-byte (it should — both
  strip — but pin it; the docstring warns coord paths do NOT strip).
- **Fakeable DoD:** "byte-identical (NFR-001)" — T017 must pin the *worktree dir name* AND the *branch
  name* against frozen literals for: legacy `NNN-` slug, already-embedded-mid8 slug, plain slug. The
  `worktree.py:367/370` path also builds `feature_dir = worktree_path / KITTY_SPECS_DIR / branch_name` —
  the dir name and the feature_dir must both stay byte-identical; assert the full path, not just the
  branch.

### WP06 — #1888 (F1) + #1971-tail
- #1971-tail half is feasible and honest (the 3-entry convergence chain verified: `paths.py:48` authority,
  `project_resolver.py` deferred delegate, `__init__.py` deferred delegate). T024 is a real test, good.
- #1888 half is **mis-dispositioned** — see F1. As written it is the single biggest fake-work risk in the
  mission.

### WP07 — #2007 command-drift guard
- Infra verified: `scripts/docs/_typer_walker.py::walk` (@145) exists; `test_docs_cli_reference_parity.py`
  exists with the profile-subcommand parity check (`test_skill_docs_profile_subcommands_are_registered`).
  T028's "reuse `_typer_walker.walk`" is feasible.
- **Stuck-point / dependency:** T026 says "read
  `docs/engineering_notes/3-2-0-training-bugs-2007/pedro-command-drift.md` (the exact drift inventory)."
  **Confirm that file exists** before implement — if it was never written, the implementer has no
  authoritative line list for the 11+1 doctrine `list/show` hits and will guess. (I did not find it in this
  pass — flag for the planner to verify, or inline the line numbers into T025.)
- **Fakeable DoD:** "the 15 SOURCE drift refs repointed to registered surfaces." An implementer can repoint
  to a *syntactically* valid command that is still semantically wrong guidance. T025 already says "keep the
  guidance correct, not just syntactically valid" — make it a reviewer checkbox: *"each repointed command
  both exists in the Typer registry AND preserves the original instructional intent."*
- T027's "grep SOURCE; if absent, record and skip — do not invent" is good honesty discipline. Keep.
- **Fakeable DoD:** T029 self-test — require it to plant **a path-level miss AND a flag-level miss** and
  assert the right finding code (`unregistered-path` vs `unknown-flag` vs `internal-as-public`), and assert
  placeholders (`<mission>`, `…`) and `--no-mark-loaded` do NOT trip it. Otherwise "guard self-test green"
  is satisfiable by a single trivial planted case.

---

## Top fakeable DoDs to harden (priority order)
1. **WP06 #1888 "failing repro"** — the fix already exists (F1). Re-disposition to verify-and-close +
   edge-case test, or the WP must name a real uncovered path with a HEAD-failing repro.
2. **WP04 terminus "shadow deleted"** (F3) — require `grep 'def _mid8'` to return nothing; deleting the
   `def`, not editing its body.
3. **WP01 / WP05 "byte-identical"** — require frozen-literal equality on the **composed strings/paths**,
   captured from pre-change code, not `resolve_mid8` compared to itself.
4. **WP02 "allow-list shrank" / detector teeth** — require the self-test to plant all 5 Paula shapes and
   assert each flagged, plus `invocation_id[:8]` not flagged.
5. **WP04 FR-002 "no context re-derivation"** — require a planted-positive (a fake `ctx.mission_id[:8]`
   trips it), not an always-green negative assertion.

## Build-breaking gaps to fix BEFORE implement
- **F0:** add `lanes/worktree_allocator.py` to WP03 owned_files + a route subtask (the rename strands it).
- **F2:** WP03 T007 must drop the `import mid8 as _mid8` lines in doctor.py after routing.
- **WP02 dependencies:** add WP01 (the bypass rule references `_mid8`, which WP01 creates).
