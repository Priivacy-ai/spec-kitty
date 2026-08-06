# Post-plan adversarial squad — findings and remediation directive

**Mission**: `meta-fail-closed-3162-01KZ7FSQ` · **Point-cut**: post-plan · **Date**: 2026-08-05
**Squad**: architecture (architect-alphonso), sequencing (planner-priti), traceability (reviewer-renata),
measurement (debugger-debbie). Four independent lenses, each told not to duplicate the others.

**Verdict: unanimous — `tasks` could not be run against `plan.md` as authored.** Three blockers, one of
them a fail-open regression the plan would have shipped. This file records the findings, the operator's
two rulings, and the exact remediation applied to `spec.md` and `plan.md`.

Every number below was re-derived on the tree by the lens that reports it. `src/` and `tests/` are
byte-identical to the measurement baseline `96494e5ec` (`git diff --stat upstream/main -- src/ tests/`
prints nothing), so branch-head measurements *are* baseline measurements.

---

## Operator rulings (2026-08-05)

| # | Question | Ruling |
|---|---|---|
| **R-1** | The gate widening has no green landing state under diagnosable-only | **Route `ref_advance.py:247`, and re-derive both floors.** Reverses `Q2` for exactly one of the five bypass sites. Spends the one routed call (129 → 130) and re-derives `ROUTED_LOAD_META_FLOOR` to restore the established 3-below-live gap in the same change. `NFR-002`'s immovable-floor clause is **struck** — it was self-inflicted and unjustified. |
| **R-2** | `D4=(a)` routes 4 silent-degrade sites onto a seam whose docstring names them non-clients | **Keep `D4=(a)`, and amend the docstring.** `core/paths.py:648-651` is amended in the same commit as the routing, so the canonical authority stops documenting a client contract its own client set contradicts. |

---

## BLOCKER-1 — the widened gate had no charter-compliant green state (all three lenses, independently)

**The claim.** `IC-05`'s widening flags exactly one new site, `git/ref_advance.py:247`. `IC-04` scoped the
bypass sites **diagnosable-only** (`Q2` "settled, not deferred"). A diagnosable-only edit does not remove
that site from the widened scanner — the widening exists to see `json.loads(param)` inside a private
same-module helper fed by `meta_path.read_text()`, and diagnosability changes neither the `json.loads` in
`_parse_meta_object` (`ref_advance.py:181-189`) nor the call at `:247`. So live inline goes 7 → 8 against
a shrink-only ceiling of 7.

**The counterfactual that settles it**, reproduced independently by two lenses with controls first:

```
CONTROL inlined read          unwidened: FLAGGED   widened: FLAGGED
CONTROL delegated read        unwidened: -         widened: FLAGGED    (the widening works)
ref_advance.py as-is          unwidened: -         widened: FLAGGED :247
ref_advance.py DIAGNOSABLE    unwidened: -         widened: FLAGGED :247   <-- the finding
ref_advance.py ROUTED at :247 unwidened: -         widened: -              <-- the remedy
```

**Why every escape is closed.** Four assertions in `tests/architectural/test_inline_meta_read_gate.py`
lock jointly:

| State | Result |
|---|---|
| widen, diagnosable-only | RED `test_inline_meta_read_floor` (`count <= 7`) + RED `test_inline_meta_read_gate_green_against_seeded_allowlist` |
| widen, FLOOR → 8, allowlist 7 | RED `test_allowlist_matches_floor` (`len(allowlist) == INLINE_META_READ_FLOOR`, an **equality**) |
| widen, FLOOR → 8, allowlist 8, baseline 7 | RED `test_allowlist_shrink_only` |
| widen, FLOOR → 8, allowlist 8, baseline 8 | all green — **the re-freeze the charter forbids** |
| **widen, site ROUTED (live back to 7)** | **all green** |

`test_allowlist_matches_floor` is the assertion the plan missed, and it is the one that forecloses the
middle escape. `plan.md` named `test_allowlist_shrink_only` + `test_allowlist_entries_are_still_live` as
the coupling; the real bidirectional coupling is the **equality**, and no mission artifact mentioned it
(`grep -rn "matches_floor"` over the mission dir returned nothing).

Two further corrections to `IC-05`'s framing: the allowlist closure is **unconditional**, not "impossible
without bumping the baseline" — `test_allowlist_entries_are_still_live` requires every entry to match a
live *detected* site, so an entry for a scanner-invisible shape is stale on arrival and red at **any**
baseline. An implementer reading the plan literally would have bumped the baseline, still been red, and
then been tempted to weaken the staleness guard.

**Applied (R-1).** `Q2` becomes "diagnosable-only **except the one gate-reachable site, which is
routed**". `load_meta_fail_closed(meta_path.parent)` is exact there: the call at `ref_advance.py:315` is
gated on `Path(path).name == _META_FILENAME`, so `meta_path.parent / "meta.json" == meta_path` by
construction, same encoding. `SC-006`'s false "or made diagnosable → live returns to 7" branch is struck.

---

## BLOCKER-2 — `IC-02` shipped a **fail-open** at `context/resolver.py`, in a guard whose own comment forbids it

**The claim.** All three `allow_missing=False` sites (census rows 8, 9, 12) are routed by `IC-02`, while
`FR-004`'s `if result is None:` arms were assigned to `IC-03`. Between the two WPs the tree silently drops
a guard.

**The evidence.** `src/specify_cli/context/resolver.py:68-78`, verbatim:

```python
# FR-005 / post-#2091: this site hard-fails on a missing meta.json
# (MissingIdentityError) and propagates a malformed-JSON failure rather
# than silently tolerating it -- allow_missing=True or on_malformed="empty"
# would MASK that guard and silently re-introduce the removed legacy
# tolerance. ``allow_missing=False`` never returns None, so ``or {}`` only
# narrows the type for mypy (mirrors mission_metadata.load_meta_strict).
try:
    data = load_meta(feature_dir, allow_missing=False, on_malformed="raise") or {}
except FileNotFoundError as exc:
    msg = f"meta.json not found at {feature_dir / 'meta.json'}."
    raise MissingIdentityError(msg) from exc
```

`load_meta_fail_closed` **does** return `None` on absence. Routing this site therefore turns `or {}` from
a mypy no-op into load-bearing control flow: absent `meta.json` → `{}` → `mission_id = feature_dir.name`
(`:80`) → **a fabricated identity, silently**, and `MissingIdentityError` never raised. That is precisely
the "removed legacy tolerance" the comment was written to prevent — re-introduced by a mission whose
purpose is fail-closed reads.

Rows 9 and 12 are the same shape with milder symptoms: the pre-existing arms raise the *same exception
types* with the wrong cause (`decisions/service.py` → "has no mission_id field" instead of "meta.json not
found"; `_resolve_planning_branch.py:127-131` → "not a JSON object", losing the `--target-branch`
remediation).

**Two existing tests pin row 8, and one is outside the declared cone** — so the WP's own verification
would not have caught it:

- `tests/specify_cli/context/test_resolver.py:256` — `pytest.raises(MissingIdentityError, match="meta.json not found")`
- `tests/integration/test_coord_loop_workspace.py:611,627` — meta-less husk raises `MissingIdentityError`

**Applied.** Re-sliced **by site, not by arm**: each site's routing + its `None` arm + its handler is one
indivisible edit, owned by whichever WP routes it. This is what `C-002` already mandated.

---

## BLOCKER-3 — `FR-009`/`SC-008` were impossible as scoped: #2804's marker carries a **second** red assertion

**The claim.** The mission treated the marker's red as one assertion. `tests/regression/test_issue_2804_merge_resets_gate_artifacts.py`
asserts **twice** under one `# --- CONTRACT (RED on base) --- ` banner:

```python
assert post_matrix.get("overall_verdict") == "pass", ...
assert SCAFFOLD_TODO_MARKER not in json.dumps(post_matrix), (
    "#2804: spec-kitty merge reset acceptance-matrix.json's criteria back "
    "to the scaffold placeholder ..., discarding the real accepted evidence.")
```

The second is also false after the merge, by a *different mechanism*: the row-union admits the scaffold
row, whose `description` and `notes` **are** the marker (fixture rows at `:172-185`). Measured directly
through the reconciler, control first:

```
CONTROL filled fixture contains marker?  False
merged criterion_ids: ['AC-001', 'FR-001', 'FR-003']
overall_verdict: pending
POST contains SCAFFOLD_TODO_MARKER?      True
```

So widening only the verdict assertion cannot make `SC-008` pass. Worse: the second assertion's content
**is** the real #2804 contract, and under the row-union authority model it is unsatisfiable by design,
not merely stale.

**Applied.** `FR-009` widened to name **both** assertions. The second is **re-pinned, not deleted**, to
evidence-survival — `"<accepted-evidence-handle>" in json.dumps(post_matrix)` — negatively controlled
against a take-theirs fixture. Measured:

```
accepted evidence survives in merged doc: True
take-theirs control (placeholder alone):  False
```

---

## BLOCKER-4 — `SC-010` passed while the defect it exists to catch was fully present

`overall_verdict` ∈ {`pass`, `pending`, `fail`, `pass_pending_consolidation`} (`acceptance/matrix.py:247-272`).
The sibling test pins `pending`, so a widened predicate must admit it. `SC-010`'s "fails on some
disallowed verdict" is then satisfied by `verdict in {"pass","pending"}` plus a fixture with one
`pass_fail: "fail"` row. **But the #2804 defect's own signature is `pending`** — the marker passes with
the regression fully present, and the non-vacuity test is satisfied by a value unrelated to the defect.

**Applied.** `SC-010` re-pinned: the companion test must fail against **the defect's own fixture**, not
against any disallowed value. `Q10` is settled **no — keep the marker**; `"fail"` is recorded as the
concrete disallowed value, reachable from a one-criterion fixture.

---

## Falsifiability audit — 9 of 11 success criteria were satisfiable while the defect lived

The traceability lens constructed an adversarial implementation for each. Only `SC-003` and `SC-009`
survived. The sharpest:

| SC | How it passed while broken |
|---|---|
| `SC-001` | Leave every read unrouted; wrap the 7 public entries in `except ValueError: raise MissionMetaReadError(...)`. Real corrupt file, real entry point, correct type, message names the path — routed count unchanged at 129, inline gate silent. Nothing asserted the read goes *through the seam*. |
| `SC-002` | Feed the probe **malformed only**. `NFR-003` demands three input shapes (malformed, absent, valid); `SC-002` named none, so the absent-file arm could regress untouched — the exact defect `NFR-003` was rewritten to catch. |
| `SC-004` | Write **type-only** guards. Green at baseline, green after, and green under arm-deletion at rows 9/12, because the pre-existing arms raise the same types with the wrong cause. |
| `SC-005` | Commit an "unreachability control" whose read is undetectable for an *unrelated* reason (path in a bare parameter, cf. `merge_driver.py:167`). Prints `sites: 0` — and so does a broken scanner. A negative with no positive twin is the vacuous gate `architectural-gate-non-vacuity` forbids. |
| `SC-007` | Narrow `:509` strictly and assert `pytest.raises(ValueError)` on the traversal guard. Red at baseline, green after, `SC-007` reported met — while the degrade-to-`""` behaviour `US2` scenario 3 protects is silently deleted. |
| `SC-011` | Change nothing: print 129 pre and 129 post. The census counts callee **names**, so it cannot see whether routing happened. |

**Applied.** Each criterion restated as a command with its input count, its positive control, and — where
the criterion is a negative — its positive twin. `SC-002` now enumerates 4 sites × 3 shapes = 12 captured
lines. `SC-004` must assert the **message**, not the type. `SC-005` gains a positive twin (same scratch
module, read inlined, path named `meta_path` → `sites: 1`).

---

## The band was wrong, three times over

`NFR-002`, `SC-011` and `plan.md`'s measured table all stated the admissible routed band as `[126,130]`.
`test_routed_load_meta_floor` asserts **three** things, not two — `len >= FLOOR`, `len > FLOOR`
(explicitly anti-vacuous: *"never a tautological `>= len(routed)`"*), and `len - FLOOR <= MARGIN`. With
`FLOOR = 126, MARGIN = 4` the admissible band is **`[127, 130]`**. A routing pass that *collapsed* calls
to 126 would satisfy the criterion as written while the gate went red. Corrected in all three places,
citing the strict inequality as the reason.

Measured live state, reproduced by three lenses: **routed 129** (floor 126, margin 4), **inline 7**
(floor 7, margin 2, allowlist 7, baseline 7).

---

## `NFR-002`'s immovable floor was self-inflicted (struck under R-1)

`ROUTED_CALLEES` matches **callee names**, not the call graph — the gate says so itself, and counts
`doc_analysis/doc_state.py`'s *locally defined* `_require_meta`. The census is global over `src/`, so any
unrelated commit anywhere that adds a call named `load_meta*` moves the number; the gate's own header
records **three** prior false reds from exactly this miscount. The fix applied on 2026-08-04 — by the
immediately preceding landing pass — was to **raise the floor** `117 → 126` "to restore the established
3-below-live gap". Raising a growth floor toward live is the ratchet *tightening*: the sanctioned,
precedented operation, not a re-freeze.

`NFR-002` forbidding it had no stated justification, and it was the constraint that made `IC-04`'s scope
call look forced. Split: the architecturally real clause — **no new predicate answering "is this
`meta.json` readable"** — is kept and given a criterion that enumerates predicate symbols pre and post.
The integer-budget clause is struck, and the floor is re-derived in the same change, exactly as `FR-008`
already required for the inline floor. That asymmetry between `FR-008` and `NFR-002` was the load-bearing
error.

---

## Structural gaps in `plan.md`

**Two canonical template sections were absent**, and their absence was load-bearing:

| Section | Why it matters |
|---|---|
| `## Project Structure` | Where the source-file map lives. Without it every IC's "Surfaces" is prose, and `tasks` has nothing to turn into `owned_files` globs — the input the no-overlap guard and lane computation consume. |
| `## Complexity Tracking` | Charter Check row 5 says "Check per file"; nothing owned the ceiling-15 rule. |

**Five pieces of mandated work had no owner:**

| Work | Mandated by |
|---|---|
| Deleting `pending-batch-a` ledger rows as sites route | `test_meta_fail_closed_full_census_contract.py` — *"If you ROUTE a site, DELETE its row"*, exact-equality gate in **both** directions. The file appeared in **no** IC's surfaces. |
| The `SC-002` probe harness + a baseline worktree at `96494e5ec` | `SC-002` |
| The `tests/sync` sweep-window handshake with mission 3167 | `C-007` |
| Filing `Q8` (lock-only comparison duplicated ×3, `_VCS_LOCK_META_FIELDS` declared twice) | `C-009` — which had **zero** enforcement anywhere, while `IC-04` edits exactly that code |
| Commit slicing, PR landing, `SC-006`'s "the raise argued in the PR body" | charter Standing Order 7 |

**The test cone was under-declared, not conservatively declared.** Import-line grep (control:
`INLINE_META_READ_FLOOR` returns only the 2 architectural files, confirming no over-match) found 26 test
files outside the declared cone that import a changed module — 9 top-level directories missing:
`tests/integration`, `tests/missions`, `tests/runtime`, `tests/next`, `tests/context`, `tests/status`,
`tests/upgrade`, `tests/coordination`, `tests/lanes`. None is `tests/sync` or `tests/cli`, so none
collides with mission 3167's window. Two matter most: `tests/integration/test_coord_loop_workspace.py:611`
pins the exact arm BLOCKER-2 broke, and `tests/status/test_aggregate_coord_deleted_contract.py:81-92`
pins census rows 10/11.

Note `tests/specify_cli/cli/commands/` is *inside* `tests/specify_cli` and is **not** the barred
top-level `tests/cli`; the census conflated the two.

---

## Atomicity — the plan flagged one coupling; there are five

1. **The widening + the floor/allowlist triple are one commit.** `test_inline_meta_read_floor`,
   `test_allowlist_matches_floor` (equality) and `..._green_against_seeded_allowlist` are mutually
   locking; any one moving alone reds another. *(The plan had this, but named the wrong two tests.)*
2. **Each routing + its ledger-row deletion are one commit** — the exact-equality gate makes the
   "unaccounted" arm pass and the "stale row" arm fail simultaneously.
3. **Each `allow_missing=False` site's routing + its `None` arm are one commit** — else fail-open
   (row 8) or wrong cause (rows 9, 12). This is BLOCKER-2.
4. **Each refuse-typed site's routing + its `except` narrowing are one commit** (`C-002`) —
   `MissionMetaReadError` is a `RuntimeError`, so routing alone makes `SC-001` pass and `SC-003` fail.
5. **Not atomic, deliberately:** the 4 degrade sites' routing and handler change are two commits inside
   one WP — that is `FR-002`'s red-first device. This is the single case where `C-002`'s "same edit" must
   read as "same work package". Stated explicitly, because as written `C-002` and `FR-002` contradicted
   each other and an implementer would have picked silently.

---

## Open decisions settled from evidence already in hand

| Q | Settlement |
|---|---|
| `Q2` | Diagnosable-only **except** `ref_advance.py:247`, which is routed (**R-1**). |
| `Q4` | Given an owner (`IC-04`) and an SC; it was cited in `spec.md` and appeared **nowhere** in `plan.md`. |
| `Q7` | **Row 11's fixture already exists** — `tests/status/test_aggregate_coord_deleted_contract.py:70-92` already drives `read_primary_meta`'s canonicalize-on-miss path with bare-`mid8`/full-ULID handles; writing corrupt JSON instead of valid reaches `:862`. Row 5's cost claim rested on no attempted construction. `SC-001`'s denominator is **7/7**; my "fixtures that do not exist" was unsupported. |
| `Q10` | **No — keep the marker.** `"fail"` is a concrete disallowed value, reachable from a one-criterion fixture (`matrix.py:259`). `IC-06` becomes sizable. |
| `Q11` | Kept as an operator question, but **struck from `IC-04`'s Requirements list** — an IC cannot own an unanswered question as a deliverable. |

---

## Phantom and colliding identifiers (`DIR-032`)

| Cited | Reality |
|---|---|
| `Q11` as a requirement in `IC-04` | An Open Decision, not a requirement. |
| `FR-015` (spec `C-005`, plan `IC-05`) | No `FR-015` in this spec; the owning mission is never named — unresolvable for an implementer. |
| `#3113` "the rejected predicate" | Plan-only provenance; absent from `spec.md` and `research.md`. Already backticked once this mission to stop it minting an unresolvable issue-matrix row. |
| `FR-008`, `FR-004`, `C-002`, `NFR-003` | Each used with **two** meanings — this spec's, and a foreign mission's (`#3076`'s row-union model; `merge_driver.py`'s field-merge). Every foreign ID now qualified as `<mission>#FR-nnn`. |

---

## Charter Check — three rows were not grantable as written

| Row | Correction |
|---|---|
| ATDD-first / `C-011` "Pass" | The charter requires red **on the WP's `planning_base_branch`**. `FR-002`'s red is on an *intermediate commit*, and `NFR-003` requires degrade behaviour be identical pre/post, so no base-red can exist for it by construction. Restated as a **documented exception** with the reviewer verification spelled out, plus `FR-008` and `FR-006`'s `read_bytes` half marked "no red possible — synthetic pin required" (`read_bytes` adds **0** sites, measured). |
| Architectural gate discipline "Pass" | Three reasons it was not: the only baseline-held green state was the one the plan forbade (BLOCKER-1); `SC-005`'s control was a negative with no positive twin; and **`inline_meta` is absent from `tests/architectural/_baselines.yaml`** (verified: `grep -c` → 0), so the allowlist this mission governs sits off the charter's Burn-down-Policy register. Deferring `FR-007` with a control **is** charter-compliant in principle — the alternative is the forbidden re-freeze — but as specified it was a gate-discipline breach wearing a vacuous control as cover. Fixed by adding the positive twin and filing the baseline-register deviation. |
| Single canonical authority "Pass, advanced" | Downgraded to **"Partial — one seam decision open"**. `C-004` deferred the bypass seam question *to* `NFR-002`, which never adjudicated it and had no predicate-counting criterion — so 4–5 sites would each author a local answer to "is this `meta.json` readable", i.e. the second predicate `NFR-002` forbids. |

---

## Corrections to `C-004`'s factual basis

`C-004` claimed the bypass sites "hold text/bytes or a temp path and structurally cannot use the seam".
Wrong on two counts:

- **2 of the 5 hold real filesystem paths.** `ref_advance.py:242` (`meta_path = worktree / path`) and
  `implement_cores.py:421-427` (`source = (repo_root / Path(repo_rel)).resolve()`, under a
  `name == _META_JSON_FILENAME` gate). Both parents *are* feature dirs; the seam fits verbatim. The real
  obstacle there was the routed budget, not structure.
- **`_parse_meta_text` cannot serve the blob sites.** It takes a `Path` and performs the read itself
  (`mission_metadata.py:331-349`), so it cannot accept `git show` stdout (`str`) or `show_blob` output
  (`bytes`). A public entry "over `_parse_meta_text`" is writable for exactly one site —
  `merge_driver.py:167`, a temp-blob path — and not for the two blob sites without first extracting a
  pure decoder.

**Recorded seam family, three tiers:** L1 pure decode (`text|bytes → dict|None`, typed) — **the missing
primitive, filed**; L2 path-level (`_parse_meta_text`, exists, needs a public fail-closed entry for the
temp-blob case); L3 dir-level (`load_meta_fail_closed`, exists, reachable by 2 of the 5). Diagnosable-only
remains the right *scope* call for the other four, but resting on the budget, not on a false structural
claim. The `_committed_meta_object` note is correct as written — `returncode != 0` does separate
absent-at-HEAD from corrupt-at-HEAD.

---

## `IC-06` is not independent

Two couplings the plan missed:

- **Code path.** `IC-03`'s three `resolution.py` degrade sites sit on the path `IC-06`'s marker exercises
  for real: the marker imports `_run_lane_based_merge`; `merge/executor.py:116` imports
  `resolve_placement_only`; AST-resolved, that reaches `_assemble_core_fragments` →
  `_resolve_mission_id` (row 3) and `_resolve_coordination_branch` (row 2). So `SC-008` captured in an
  `IC-06`-only lane is not evidence it still passes once `IC-03` lands.
- **Subprocess + stale install.** `Q11`'s subject `merge_driver.py:167` runs *as a subprocess* inside the
  marker (`lanes/merge.py:84` registers `spec-kitty merge-driver-meta` for `kitty-specs/**/meta.json`),
  and the marker asserts on its result. Because it goes through the installed console script, an edit is
  invisible until `pip install -e .` — the documented stale-install false-red class.

**Applied.** `IC-06` still starts anytime, but its `SC-008`/`SC-010` evidence is re-captured at final
integration in a terminal verification WP.

---

## Minor findings folded

- `IC-02`'s Surfaces named `mission_runtime/`, where it owns nothing — all three `resolution.py` sites are
  degrade (`IC-03`). As an `owned_files` glob it would have forced a needless lane union. Struck.
- The unreachability control must **not** live under `src/` — `scan_inline_meta_reads` walks `SRC_ROOT`,
  so a fully-inlined read there raises the live census and reds the floor it exists to prove. Path named
  under `tests/architectural/` fixtures, scanned by explicit argument.
- `tests/architectural/tool_artifact_enrolment/registry/_is_self_write_only_diff.md` is an `IC-04` surface
  living in `IC-05`'s directory — `owned_files` there must be **file-level**, not a directory glob.
- **Dead handlers after routing:** `except FileNotFoundError` becomes unreachable at rows 8, 9, 12
  (`load_meta_fail_closed` hard-codes `allow_missing=True`). No requirement removed them; the charter
  review checklist and `CLAUDE.md` both reject effect-free handlers. Now in scope.
- No criterion required `ruff check` or `mypy --strict` (`DIR-030`). Added.
- `SC-008`'s "passes on current `main`" was unrunnable as phrased — the widened marker lives on the
  branch. Restated as "on branch head with `src/` unchanged from `96494e5ec`".
- **The deleted unit gate is unowned.** `tests/merge/test_gate_artifact_merge_drivers_2804.py` was deleted
  in `b04da00e1` (−249 lines) — the gate that held this invariant. Research names it; no requirement did.
  Now cited in `FR-010`'s superseding issue.
- `MissionSelectorAmbiguous` is confirmed **not** a `ValueError` (`_read_path_resolver.py:44`, plain
  `Exception`) and is raised *inside* `resolution.py:509`'s `try`. The never-`except Exception` rule was
  scoped only to the 2 typed-refusal sites; extended to all 6 handlers, and `SC-007` gains a second
  assertion that an ambiguous handle still propagates.
- `US2` scenario 3 was self-contradictory: "narrowed to `MissionMetaReadError`" ∧ "traversal-guard
  behaviour unchanged" is satisfiable only by `except (MissionMetaReadError, ValueError)` — i.e. not a
  narrowing. Restated as "extended to `MissionMetaReadError` while retaining `ValueError`".
- `US3`'s Independent Test, `US3` scenario 2 and `NFR-004` all still mandated the allowlist entry `FR-007`
  forbids, and demanded a "dated rationale" that `load_allowlist` has **no date field** for. Rewritten to
  the deferral+control form; the denominator stated as an integer.
- `FR-005` had **no success criterion** — `IC-04` was closable with zero evidence. One added: each bypass
  site against a corrupt fixture, asserting the message names `meta.json` and the path, controlled on the
  valid file.
- Filing obligations: ≥5 mandated, only 2 pinned. `SC-009` extended into a filing register, one row per
  obligation, each verified by `gh issue view <n>`.

---

## Measurement lens — 7 of 8 claims reproduced, 1 refuted

Every claim in `plan.md`'s measured table was independently re-derived with controls. The baseline label
was stale but harmless: `HEAD` is `1e5bc865b`, not `96494e5ec`, and
`git diff --name-only 96494e5ec HEAD | grep -v '^kitty-'` → **0** files, so no number moves. Stronger, all
load-bearing files are byte-identical to current `upstream/main` (`98198e980`), so the table is not stale
despite upstream advancing 32 commits. Relabelled anyway.

| Claim | Reproduced | Verdict |
|---|---|---|
| 13 sites; arms 4 degrade / 2 refuse-typed / 7 refuse-raw | 13; 4/2/7 | **REPRODUCED** — ledger sum 13, live 13, ledger == live; own AST classifier agrees. Controls: 9/9 synthetic, 6/6 hand-read |
| 6 `except ValueError` handlers, "not 4" | 6, enumerated | **REPRODUCED** — trap control: naive `grep -c` gives **9** (catches a comment at `resolution.py:491` plus two unrelated handlers) |
| ≥5 bypass sites, "5 is the count not the closure" | 5 read expressions / **6** invocation sites | **REPRODUCED with a convention caveat** (see below) |
| widening reach 1 site (`ref_advance.py:247`) | 1 | **REPRODUCED** under two independent definitions |
| 0 false positives over `src/` | 0 | **REPRODUCED** |
| `read_bytes` ⇒ 0 new sites | 0 | **REPRODUCED** — control fixture: expected before=1 after=2, got 1→2 |
| routed 129, floor 126, margin 4 | 129 (stable over 3 runs) / 126 / 4 | **REPRODUCED** — independent AST walk over 1199 files agrees; naive grep gives **296** |
| inline 7 = FLOOR, allowlist 7, shrink-only | 7 / 7 / 7 | **REPRODUCED** — `5 passed`, `^ERROR tests/` = 0 |
| **#2804 marker red on `main` today** | **red on pristine `upstream/main` `98198e980`** | **REPRODUCED** — `git worktree add`, `rootdir: /tmp/repro-3162-main`, `1 failed in 96.97s`, `^ERROR tests/` = 0, `E assert 'pending' == 'pass'`; branch identical. A genuine same-selection pre-existing red |
| **31 candidates, 30 rejected at clause 3** | **19 candidates, 17 at clause 2, 1 at clause 3, 1 accepted** | **REFUTED** |

**The 6 handlers, at `file:line`** — `mission_runtime/resolution.py:514`, `:853`, `:1108`;
`decisions/service.py:141`; `missions/_resolve_planning_branch.py:122`; `upgrade/feature_meta.py:43`. All
six catch bare `ValueError`; matches `C-002`'s two cited refuse-typed lines exactly.

### The refuted claim, and why the arithmetic is the smaller half

`31/30-at-clause-3` reproduces under **no** definition — eight variants were swept (helpers ∈ {11,14,21},
call sites ∈ {18,19}, wider populations 100/121/150); 31 appears in none. The measured breakdown is
**19 candidates → 17 rejected at clause 2 → 1 rejected at clause 3 → 1 accepted**.

**The substance is worse than the number.** The plan attributed the zero false-positive count to
**clause 3** (the meta-path clause). Clause 3 rejects exactly **one** candidate. What actually holds the
count at zero is **clause 2** — the requirement that the call-site argument resolve to a
`read_text`/`open`/`read_bytes` call. As written the plan licenses precisely the wrong future move: a
later widening of clause 2 would unlock ~17 candidates with **no** measured clause-3 protection, while the
plan implies clause 3 is the guard. `C-005`'s "measure false positives before adopting" survives on the
number and fails on the reasoning. Corrected in `FR-006` to state the predicate, the true breakdown, and
clause 2 as the load-bearing guard.

### The band is also wrong at the *bottom*, and that is a live risk

Fourth independent confirmation of `[127,130]`, with an angle the other three did not raise: **126 is
RED**, so the routing must not *reduce* the live count below 127 either. This programme has already had
three floor mismatches caused by folds that *collapsed* call sites — so a routing pass that replaces two
calls with one is a real way to red this gate downward. Stated in `NFR-002` as a two-sided constraint, not
a ceiling.

### The bypass count depends on an undeclared convention

The 5 are 5 *read expressions*: `ref_advance.py:203` (git show) and `:244` (`read_text`);
`implement_cores.py:335` (`show_blob`) and `:427` (`read_bytes`); `merge_driver.py:171` (`read_text`). But
`merge_driver._load_json_object` is invoked from **two** call sites (`:243`, `:244`), so under the
*call-site* convention — which this mission uses elsewhere, and which is exactly why census rows 10/11
count `read_primary_meta` as 2 and yield 13 rather than 12 — the total is **6**, not 5. Both are
defensible; mixing them silently inside one document is not. The convention is now declared per count.

Triage that produced the set, with input counts at every step: files containing `"meta.json"` **172** →
zero routed `load_meta*` calls **103** → candidate bypass files **30** → parse sites **41** → meta-ish
**13** → 7 allowlisted inline, 3 ruled out (metadata.yaml / evidence-json), **3 bypass parsers**. Closure
probes: constants-vector **0**; call-surface probe over **20 276** calls → 70 candidates, no new site. So
"5 is the current count, not the closure" is sound as a caveat.

---

## Process note

Three lenses independently reported that a shared scratchpad file was overwritten mid-run by a concurrent
lens, and each re-derived under a unique filename. No conclusion was affected — the three widening
prototypes agree on the load-bearing result — but per-agent scratch paths are the fix. Separately, a
background agent co-located in a sibling mission's worktree silently reverted a regenerated file with no
HEAD reflog entry (a bare `git restore` leaves no trace). Do not co-locate a background agent with your
own edits.

---

## Correction (2026-08-05, found while authoring WP03) — BLOCKER-2's severity argument was wrong

BLOCKER-2 above states that **two** existing tests pin census row 8's guard and that
**one of them sits outside the declared cone**, "so the WP's own verification would not
have caught it". **Both halves of that are false.** The defect is real; the escalation
was not.

**There is one pin, not two.** `tests/integration/test_coord_loop_workspace.py:611,627`
are **docstring prose**, not assertions — verified: `grep -n MissingIdentityError` over
that file returns exactly those two lines and nothing else, and both sit inside
`TestResolveContextReadsFromPrimary`, a class describing a *historical* red-first proof
for a **different mission's** WP05. Its test asserts that `resolve_context`
**succeeds**. It therefore cannot fail under row 8's arm-deletion, and citing it as a
mutation-probe victim would send an implementer hunting a failure that cannot occur.

**The real pin is inside the cone, not outside it.**
`tests/specify_cli/context/test_resolver.py:255-257`:

```python
def test_missing_meta_json_raises(self, tmp_path: Path) -> None:
    repo = _setup_project(tmp_path)
    (repo / "kitty-specs" / "057-test-feature" / "meta.json").unlink()
    with pytest.raises(MissingIdentityError, match="meta.json not found"):
        resolve_context("WP01", "057-test-feature", "claude", repo)
```

That file is `tests/specify_cli/context/**`, which WP03 owns. So the fail-open **would**
have been caught by the work package's own test run.

**What survives unchanged:** the fail-open itself, and the remedy. Routing row 8 without
its `None` arm in the same commit still yields `{}` → `mission_id = feature_dir.name` →
a fabricated identity, and the per-site re-slice is still the correct fix. What does not
survive is the claim that the cone under-declaration hid it. The cone was still
under-declared by nine directories — that finding stands on its own evidence — but it was
**not** what made row 8 dangerous.

**Provenance of the error, since it matters more than the error.** The sequencing lens
reported the two line numbers; three artifacts (`spec.md` `FR-004`, `plan.md` IC-03, this
report's BLOCKER-2) and `SC-016` then described them as assertions, and I repeated the
claim twice in the operator log without opening the file. A cited line number is not
evidence that the line asserts anything. It cost nothing here only because a WP author
opened the file.

Two further corrections from the same pass:

- **Row 12's `None` arm already exists** at `_resolve_planning_branch.py:127-131`. The
  complexity register says "add an `if result is None:` arm" uniformly for all three
  sites; at this one the edit **re-purposes** an existing block, and `SC-004`'s mutation
  probe deletes that block rather than one the mission added.
- **`plan.md` IC-04's risk bullet is factually wrong**, and it propagated into
  `wps.yaml` T021: it says row 3's `legacy-<slug>` fallback is "derived from the malformed
  file" and could therefore produce a plausible-but-wrong value. It is not.
  `resolution.py:1114` returns `f"legacy-{mission_slug}"` from the **caller's argument**,
  and `meta` is `None` on that path. **All four degrade fallbacks are constant with
  respect to file content.** The instruction to state derived-vs-constant per site is kept;
  the claim is withdrawn.

---

# Post-tasks adversarial squad — findings, adjudication, remediation directive

**Point-cut**: post-tasks · **Date**: 2026-08-06 · Run through the canonical `adversarial-squad` skill.
**Squad**: anti-laziness (`reviewer-renata`), decomposition/boundaries (`paula-patterns`), implementer
feasibility (`python-pedro`) — three profile-loaded lenses on one framed question: *can these eight work
packages be marked done without the mission actually being done?*

**Verdict: yes, in five of eight — but every defect is a prose amendment, not a re-decomposition.**
WP02, WP03 and WP07 came back sound from the lens that owns fakeability. All three lenses independently
found the same WP01/WP08 blocker.

---

## BLOCKER-1 — WP01 and WP08's Definition of Done forbids creating the only file each owns (all three lenses)

Both frontmatters declare `owned_files: [scripts/verify_*_3162.py]` with matching `create_intent`. Both
bodies then forbid it: WP01 DoD item 1 — *"No other file is created, modified or deleted"* — and item 11
*"planning artifacts only"*; WP08 DoD *"is the **only** file this WP wrote"* plus its Objective *"This WP
writes no code."* The script is named **only** in frontmatter and the boilerplate ownership note; no
subtask, step, Files line, Validation line or DoD item mentions it.

So two of eight units can be marked done with their entire declared write surface empty — and an
implementer who *does* create the script violates DoD item 1. Nothing re-checks it: `create_intent` is
consumed solely to **suppress** the zero-match error (`ownership/validation.py:411-433`), and no review or
accept gate revisits existence.

### The premise behind it was half false — this is the orchestrator's error

The ownership note claims the script was *"forced by `finalize-tasks`"*. Half true. The
`kitty-specs/` prohibition is real (`mission_parsing.py:153-157`, `_invalid_mission_specs_owned_files` at
`:207-215`). The conclusion is not: **`owned_files: []` is an explicitly supported planning-artifact
shape** (`mission_finalize.py:796-801`; `_owned_files_yaml_is_explicit_empty_list`,
`mission_parsing.py:161-187`), and `execution_mode: planning_artifact` routes the WP to the **repository
root** (`workspace/context.py:752,761`) — precedented in five sibling missions.

The invented constraint had a second cost. Declaring `code_change` gives both WPs a **lane worktree**, and
**nothing provisions `.venv` into a git worktree** (`.gitignore:31-32`; zero venv references across
`workspace/`, `lanes/`, `git/`). Every `.venv/bin/python` command in WP08 is unrunnable there. It also
trips the repo's own validator, measured: `code_change WP does not own any files under src/ or tests/` —
`scripts/` is in neither `_PLANNING_PREFIXES` nor `_CODE_PREFIXES` (`ownership/validation.py:75-77`).

**Applied.** WP01 and WP08 become `execution_mode: planning_artifact` with `owned_files: []`,
`create_intent` dropped, the script dropped, and the false premise struck from both ownership notes.

### Adjudicated divergence

The decomposition lens instead wanted the measurement relocated into `tests/` as a committed contract test
(lint + collection scope, under the no-overlap guard, self-invalidating on drift) — partly to give WP08 a
write surface so the floor calibration could move to a terminal owner. Per the squad protocol this is not
averaged: **the `planning_artifact` shape wins** (precedented, simpler, and it is what makes the commands
runnable), and the budget problem it would have solved is closed by the alternative below instead.

---

## BLOCKER-2 — nobody owns the CI ratchet baselines that five WPs will move (decomposition lens)

`tests/architectural/_gate_coverage_baseline.json` states: *"The ratchet (`test_gate_coverage.py`) **fails
on any NEW orphan file not listed here**"*, with `"orphan_files": []`.
`_golden_count_baseline.json` states: *"A directory absent here has an implicit ceiling of 0 — any
convert-classified site appearing there **fails the guard immediately**"*, and its `ceilings` map omits
`tests/regression`, `tests/missions`, `tests/context`, `tests/mission_runtime`, `tests/upgrade`,
`tests/merge`.

**Five WPs create new test files in exactly those directories.** `grep` for either baseline across the
whole mission directory returns **nothing**, and no `owned_files` entry matches either file. WP08's sweep
would surface the red, but its own Risk 10 says the owning WP repairs it — and the owning WP is nobody.

**Applied.** Both baselines join **WP06**'s `owned_files` (already `authoritative_surface:
tests/architectural/`, already owns `_baselines.yaml`, sequential with WP05, file-disjoint from lane B —
so the addition unions no lane), plus a subtask requiring an orphan check and a golden-count check over
every directory this mission adds a file to.

*Concession carried from the lens:* the ownership gap is demonstrated; the **red** is inferred — no gate
was run. If gate selection is directory-globbed such that a new file in an already-selected directory is
never an orphan, this drops to MAJOR. The ownership gap survives either way.

---

## BLOCKER-3 — WP06's floor criterion inverts: doing the work makes it unsatisfiable

At the post-WP05 live count of **130** with `ROUTED_LOAD_META_FLOOR = 126` and `MARGIN = 4`, all three
clauses of `test_routed_load_meta_floor` pass: `130 >= 126`, `130 > 126`, `130 - 126 = 4 <= 4`. **The gate
is green with the floor untouched**, and nothing in the DoD asserts the committed value differs from 126.

Worse, the DoD requires an *"anti-copy grep quoted proving `127` and `[128,131]` were **not** pasted"* —
while the derivation rule it is told to apply (3-below-live at live 130) **produces 127**. Doing the work
makes that bullet unsatisfiable; skipping it makes it pass. The guard was written against a copied
*number* when what was missing was its *provenance*.

**Applied.** Replace the anti-copy grep with a provenance requirement that cannot invert —
`git show <sha> -- tests/architectural/test_inline_meta_read_gate.py | grep '^[-+]ROUTED_LOAD_META_FLOOR'`
must show **both** the old and the new value — plus an explicit criterion that the committed value **is
not 126**. Keep the anti-copy grep scoped to `contracts/`, where WP01's DoD already has it correctly.

---

## BLOCKER-4 — WP04's routing-commit red is unachievable in the order given

T022 step 4 says to run the cone at commit 1 and quote the traceback of `MissionMetaReadError` escaping
`except ValueError`. The only tests that can produce it are the four malformed-input fallback tests — added
in **T024**, i.e. after commit 2. Measured: no pre-existing test in `tests/mission_runtime` or
`tests/upgrade` drives those four sites with corrupt JSON, and absent/valid behaviour is unchanged
(`load_meta_fail_closed` hard-codes `allow_missing=True`, `core/paths.py:676`). So the cone at commit 1
runs **green**, and the only way to tick the box is a hand-rolled scratch traceback — meaning `FR-002`'s
red never enters the repository. That red is the entire basis on which the charter ATDD exception was
granted.

**Applied.** The four fallback tests move to a **commit 0**, before the routing: green at baseline
(degrade already works, `NFR-003`), red on commit 1, green on commit 2. A real red-then-green sandwich,
and it makes the reviewer-verification steps checkable by re-checkout.

---

## MAJOR — the split-tree hazard, unnamed anywhere in the mission

`.venv/lib/python3.11/site-packages/_editable_impl_spec_kitty_cli.pth` pins `specify_cli` / `runtime`
imports to the **main** tree's `src/`. But `SRC_ROOT` in the gate (`test_inline_meta_read_gate.py:61`) and
`_SRC_ROOT` in the ledger test (`:54`) are derived from **the test file's own location** — the worktree. In
a lane worktree the AST census therefore reads the *edited* `src/` while every behavioural assertion
imports the *unedited* one: a structural assertion goes green while its behavioural twin stays red, with no
diagnosable cause. No WP mentions `PYTHONPATH`.

Compounding it: every WP opens with `spec-kitty agent action implement WP## --agent <name>` described as
resolving the workspace. It does not — `--help` says *"Display work package prompt…"*, and `CLAUDE.md` is
explicit that `spec-kitty implement WP##` is the only supported way to prepare one. The effect is
benign **by accident**: the implementer stays in the repository root, which is where `.venv` lives.

**Applied.** State once per WP that it runs from the **repository root**, correct the start command, and
put `PYTHONPATH=<workspace>/src` on every `python -c` / `pytest` invocation that could run elsewhere.

---

## MAJOR — the single-call budget is enforced by narration, and its one automated consequence is owned by the wrong lane

WP06 (lane D) computes `ROUTED_LOAD_META_FLOOR` from **its own** worktree, which contains WP05's `+1` and
**nothing from lane B** — lanes B and D are concurrent with zero shared files. So it commits a number whose
correctness on the merged tree is a promise made by files it does not own, cannot see, and shares no guard
with. A file-overlap check can never detect this coupling, because it is not file-mediated.

The downward direction is invisible where it matters: at `126/4` a lane-B worktree that *folded* one call
reads 128 and satisfies all three clauses; after WP06 sets 127, the merged tree at 129 is green too. The
fold survives both gates, caught only by narrated pre/post prints and WP08's "Expected 130" — neither an
assertion. WP02 T011 step 3's AST assertion (*exactly two* `load_meta_fail_closed(` calls, *zero*
`load_meta(`) is the right instrument, but it exists for **one** of twelve ledger rows.

**Applied (decomposition lens option (b), since option (a) needed the write surface BLOCKER-1 removes).**
Require the per-site structural call-count assertion in **every** routing subtask of WP02, WP03 and WP04 —
twelve executable assertions instead of seven print obligations plus one integration expectation.

---

## MAJOR — `mark-status` has no evidence channel, and every WP's preamble says it does

`spec-kitty agent tasks mark-status --help` exposes only `--status`, `--mission`, `--auto-commit`,
`--json`. Its payload is `WPInnerStateDelta.subtasks: Mapping[str, Status]` (`status/models.py:481`) — a
bare `{T0xx: DONE}`. WP02's preamble claims the record *"carries the evidence named in that subtask's
Validation block"*; that field does not exist. And the evidence has nowhere else to go: `tasks.md` is a
read-only roster, the WP prompt files are in no `owned_files`, their checkboxes are decorative, and
WP02/WP05 route every capture to `/tmp` explicitly uncommitted.

**Applied.** Correct the factual claim, and name one committed destination per WP — the `contracts/`
evidence files for WP01/WP08 (out-of-map planning writes, which is what `planning_artifact` is for), and
for WP02–WP07 a committed evidence path rather than `$EV` under `/tmp`.

*Carried, not resolved:* the platform gap is arguably upstream. The prompts asserting a capability the tool
lacks is a defect in the prompts regardless of where the remedy belongs.

---

## MAJOR — WP04's ledger grep keys are elided, and unelided one matches two rows with opposite arms

T022 step 4 gives the keys as `(…, "_resolve_coordination_branch")` and `(…, "_resolve_mission_id")`.
Copied literally, `grep` matches nothing — printing nothing at exit 1, which reads exactly like *"already
deleted"*. With the ellipsis dropped, `"_resolve_mission_id"` matches **two** ledger rows: `:200`
(`mission_runtime/resolution.py`, WP04's row 3, **degrade**) and `:222` (`decisions/service.py`, WP03's
row 9, **refuse-typed** — the opposite arm). It survives today only because `dependencies: [WP01, WP03]`
means row 9 is already gone. **Applied:** write both keys out in full, as WP02 and WP03 do.

---

## MAJOR — WP05's byte-identity bullet is unpathed, reopening a cheat this mission already suffered

*"Ledger, routing-manifest and `test_row_aware_merge_driver.py` **byte-identical**"* — no path, no base
ref, no command. The real file is `tests/specify_cli/cli/commands/test_row_aware_merge_driver.py`;
`git diff --stat -- tests/merge/test_row_aware_merge_driver.py` prints nothing **because the path does not
exist**. WP04, WP07 and WP08 all carry the full path and flag the nonexistent variant; WP05's DoD carries
neither. **Applied:** write the bullet as the command with its base ref, and require `ls` on the path to
succeed, quoted.

---

## MAJOR — WP02 trains a commit shape WP03 auto-rejects

WP02 lands **ten** commits (a red guard commit, then routing+ledger, per row). WP03 requires exactly
**three** — *"Three commits, one per site"* — and its Reviewer Guidance opens by rejecting any other count.
WP03 explains why no base-red exists but never says where its guard tests are committed, and never draws
the contrast; WP04, by comparison, opens with *"Unlike WP03"*. An implementer arriving with WP02's habit
lands six commits and is rejected on a **count**, not a contract. **Applied:** one line in WP03 — the guard
test rides in the same commit as its site, and unlike WP02 there is no separate red commit because no
base-red is possible.

---

## MAJOR — WP08's fourteen-directory sweep is unpriced, and the prompt forbids the only documented way to finish it

Measured on this tree: `--collect-only -q` on **one** file took **50.22 s**; one node of the inline-meta
gate took **58.20 s**. `tests/specify_cli`, `tests/integration` and `tests/architectural` are among the
fourteen. The prompt gives no budget, does not use `CLAUDE.md`'s documented `-n auto --dist loadfile`,
forbids substituting the full suite, and says a timed-out run *"is neither pass nor fail — re-run it"*
without saying how to make it terminate. **Applied:** a per-directory timeout, and `-n auto --dist
loadfile` permitted for the twelve directories that are not real-port/daemon suites.

---

## Structural findings that came back CLEAN — do not re-litigate

- **All 12 concurrent WP pairs share zero files.** Verified by expanding every glob against `git ls-files`
  and computing transitive ancestors the way `validation.py:127-158` does.
- **The ledger's 12 rows partition exactly**: WP02 `:201,:202,:203,:204,:243` (5 rows / 6 call sites),
  WP03 `:215,:222,:244`, WP04 `:198,:199,:200,:249`. `5+3+4 = 12`, no gap, no double-claim. `grep -c`
  returns 13 because `:185` is the legend — exactly as WP01 T001 step 3 says.
- **The `0.32` parallelization flag is a directory-prefix false positive.** Lane B ∩ lane C is **empty** at
  file granularity; the score measures shared 2-segment package prefixes.
- **`SC-008`'s byte-identical file is owned by no glob** — the file-level rule for `tests/architectural/`
  and WP05's single-file claim both held.
- **No cross-WP evidence laundering.** Every WP that consumes a sibling's artifact re-runs its *command*,
  never cites its result; WP08 re-derives all six captures on the merged tree.
- **Import surgery is per-site and correct**, including the `gate.py` case that serves two rows (keep the
  import at the first routing, remove it at the second) and the in-function import at
  `_read_path_resolver.py:843` while deliberately leaving `:113` alone. Following any of them literally
  leaves no `F401` and no `NameError`.
- **The two commit shapes are unambiguous from WP03 + WP04 alone.** The gap is WP02 → WP03.
- **`mypy --strict` is clean today** on all four of WP02's owned files, so that criterion is reachable.
- **The `doc_state.py` `_require_meta` claim is true** and contributes 8 of the 129 routed sites — one lens
  initially thought it false and retracted.
- **All three cited SHAs resolve**, and `git diff --name-only 96494e5ec HEAD | grep -v '^kitty-'` = **0**.

## Off-by-one corrections (all `[MINOR]`, all applied)

`WP07` assertion 2 `:488` → **`:489`**, banner `:477` → **`:476`**, sibling evidence `:513` → **`:512`** ·
`WP05` `missing → {}` `:168` → **`:169-170`**, `merge_driver_meta` `:245-247` → **`:246-248`** ·
`lanes/merge.py:84` → **`:83`** in WP05, WP07 and WP08 · `WP03` `test_missing_meta_json_raises` `:250` →
**`:251`** · `WP04` `MissionSelectorAmbiguous` note `:493-498` → **`:496-498`** (`:493-495` is the
traversal-`ValueError` note, a different fact).

## Map corrections

`wps.yaml` `tests/specify_cli/context/**` over-claims `test_resolver.py`, which WP03 declares run-only —
narrow it. `core/paths.py` is granted whole-file to WP04 for a 4-line docstring while concurrent WP05
depends on its contract — add a docstring-only DoD proof that no signature, exception class or return
contract changed. Add the **`WP01 → WP07`** edge (WP07 quotes WP01's measurement command verbatim; zero
scheduling cost, no lane union). Redraw `plan.md`'s dependency diagram, which shows IC-02/03/04 as parallel
siblings and contradicts its own lane table.
