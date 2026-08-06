# Mission Specification: meta.json fail-closed routing, and #2804's returning red

**Mission Branch**: `feat/meta-fail-closed-3162`
**Created**: 2026-08-05
**Status**: Draft
**Input**: Close #3162 (13 `meta.json` reads left unrouted after `#3155` routed 170+) and #3138
(#2804's red marker failing again). Both traced in `research.md`; `#3162`'s census is
`research/3162-census.md`.

**Baseline**: the measurement head is `upstream/main` **`96494e5ec`**, and every count below holds
**equally on the current branch `HEAD`**: `git diff --name-only 96494e5ec HEAD | grep -v '^kitty-'` prints
**0** files, so no non-mission file differs and no number moves. `src/` and `tests/` are also
byte-identical to current `upstream/main` (**`98198e980`**), so the counts are not stale despite upstream
having advanced past the measurement head. Branch-head measurements therefore *are* baseline
measurements — say "the measurement baseline", not "`96494e5ec` only". Every count was re-derived, not
inherited: three inherited counts were wrong and are corrected in the research, and a fourth (the gate's
false-positive breakdown) was refuted in the post-plan pass and is corrected in `FR-006`.

## Sequence

**#3162 → #3138.** `#3139` dropped out of this mission entirely: it was already fixed on `main` by landing
fold `50d7d8e10`, which regenerated all 14 files at +44 lines each.

## What is settled before implementation starts

| | Decision | Where it came from |
|---|---|---|
| **D4 = (a)** | Route all 13 through `load_meta_fail_closed`, **preserving each site's existing refuse-vs-degrade arm**. Option (c) — the 7 raw-escape sites only — is the named fallback if the budget bites. Option (b), uniform refusal, is **rejected**: it changes behaviour at sites that deliberately degrade. **Rider R-2 (operator, 2026-08-05):** `load_meta_fail_closed`'s own docstring at `core/paths.py:648-651` currently names *this exact caller class* as non-clients ("Callers that must stay deliberately silent about corruption (placement probes, best-effort displays) … are not routed here"). D4=(a) is kept **and the docstring is amended in the same commit as the routing** — see `FR-012`. A canonical authority may not keep documenting a client contract its own client set contradicts. | Operator, 2026-08-04 / 2026-08-05 |
| **#3138** | **Widen #2804's acceptance-matrix assertion**, exactly as its own issue-matrix sibling was already widened by the same author, and **supersede #2804** to record that its pin changed shape. **Rejected**: a scaffold-row suppression rule in the reconciler — it would fix the product consequence *and* let the pin pass unchanged, but the driver has zero scaffold awareness today, so it amends the row-union authority model shipped as `#3076`'s FR-008 (see the ID-qualification rule in Standing rules). | Operator, 2026-08-05 |
| **Non-negotiable rider on #3138** | The pending-poisons-the-aggregate **product defect is not fixed here and must be filed**, with `acceptance/gates_core.py:525` as evidence. Widening the pin without filing it would make a red go away without addressing what the red pointed at. | Operator, 2026-08-05 |
| **R-1** | The gate widening has **no charter-compliant green landing state** under diagnosable-only: a diagnosable edit leaves `json.loads(param)` inside `_parse_meta_object` (`ref_advance.py:181-189`) fed by `meta_path.read_text()`, so the widened scanner still flags `ref_advance.py:247` and live inline goes 7 → 8 against a shrink-only ceiling of 7. Every escape is closed (`test_allowlist_matches_floor` is an **equality**, so floor→8/allowlist→7 reds; allowlist→8 reds `test_allowlist_shrink_only`; baseline→8 is the re-freeze the charter forbids). **Ruling: route `ref_advance.py:247`, and re-derive both floors in the same change.** `load_meta_fail_closed(meta_path.parent)` is exact there — the call at `ref_advance.py:315` is gated on `Path(path).name == _META_FILENAME`, so `meta_path.parent / "meta.json" == meta_path` by construction. `Q2` becomes "diagnosable-only **except the one gate-reachable site, which is routed**". `NFR-002`'s immovable-floor clause is **struck**. | Operator, 2026-08-05 |

### Spec-level calls made here, and open to reversal

The research left ten open questions. Eight are answered below or in the Open Decisions table on the
evidence; two remain open and are named there rather than silently decided.

- **Q1 — bypass scope is 5 read expressions / 6 invocation sites, and that is the current count, not the
  closure.** The issue names two in `git/ref_advance.py`; the census found a third and fourth in
  `cli/commands/implement_cores.py:259 _parse_meta_mapping`; the post-spec pass found a **fifth**,
  `cli/commands/merge_driver.py:167 _load_json_object`, blind for a **third** distinct reason — read and
  parse are same-function so clause 2 passes, but the path arrives as a bare parameter so clause 3 fails.
  **The two counts use two conventions and both are stated wherever a count appears** (see Standing rules):
  **5 read expressions** — `ref_advance.py:203` (`git show`), `ref_advance.py:244` (`read_text`),
  `implement_cores.py:335` (`show_blob`), `implement_cores.py:427` (`read_bytes`), `merge_driver.py:171`
  (`read_text`) — versus **6 invocation sites**, because `merge_driver._load_json_object` is invoked from
  **two** call sites (`:243`, `:244`). The call-site convention is the one this mission uses elsewhere: it
  is exactly why census rows 10/11 count `read_primary_meta` twice and yield 13 rather than 12. Mixing the
  two silently inside one document is the defect; declaring which is in force is the fix. `Q11` is enrolled
  as a bypass site for `FR-005`/`SC-012` purposes and remains an **operator scope question only** for full
  routing — it is not a deliverable (see Open Decisions).
- **Q3 — the widening reaches ONE site, not two, and allowlisting is NOT AVAILABLE.** Measured by
  implementing the proposed anchor-move and running it over `src/`: **exactly 1 new site**,
  `ref_advance.py:247`. `implement_cores.py:427` is *not* reachable — it is `read_bytes()`, which
  `_extract_read_base` does not match, **and** its path is a runtime-gated variable, so clause 3 fails
  independently. So the split is **1 widened / 4 not**.
  **And the allowlist route is closed unconditionally, not merely "closed without a baseline bump":**
  `test_allowlist_entries_are_still_live` requires every entry to match a **live detected** site, so an
  entry for a scanner-invisible shape is stale **on arrival and red at any baseline**;
  `test_allowlist_shrink_only` (`len(keys) <= baseline`) and `test_allowlist_matches_floor`
  (`len(allowlist) == INLINE_META_READ_FLOOR`, an **equality**) close the rest. The loader has **no date
  field**, so "dated rationale" was unchecked prose. The unreachable sites are therefore **deferred by a
  filed issue plus a committed unreachability control with a positive twin**, and
  `inline_meta_read_baseline` stays at **7**.
- **Q9 — supersede #2804 with a new issue** rather than reopening it. Its pin genuinely changed shape;
  reopening implies the original ask still stands.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A malformed `meta.json` produces a typed refusal, not a raw crash (Priority: P1)

An operator's `meta.json` is corrupt. Today, at 7 of 13 read sites, a raw `ValueError` reaches them with
no indication that the mission's metadata is the cause. Those sites route onto the fail-closed seam and
raise `MissionMetaReadError`, which names the path.

**Why this priority**: it is the user-visible half of #3162 and the only half where someone is currently
harmed.

**Independent Test**: corrupt a fixture `meta.json`, exercise each of the 7 sites through its own public
entry point, and assert the error type, that the message names the file, **and that the raiser is the seam**
— not a local translation wrapper at the call site (`SC-001`'s seam proof; without it the whole story is
satisfiable with zero routing).

**Acceptance Scenarios**:

1. **Given** a malformed `meta.json`, **When** any of the 7 route-unwrapped sites reads it, **Then** a
   `MissionMetaReadError` is raised **by `load_meta_fail_closed`**, and its message names the path.
2. **Given** the same file, **When** any of the **4 degrade** sites reads it, **Then** it still degrades
   exactly as before — `""`, `None`, `legacy-<slug>`, `None` respectively — and **no** exception escapes.
3. **Given** the same file, **When** either of the **2 refuse-typed** sites reads it, **Then** it still
   raises its own domain error (`DecisionError`, `PlanningBranchResolutionFailed`), not
   `MissionMetaReadError`.

---

### User Story 2 - The degrade sites keep degrading after the exception type changes (Priority: P1)

`MissionMetaReadError` is a **`RuntimeError`, not a `ValueError`**. Every one of the 4 degrade handlers
catches `ValueError` today. Routing them without changing the handler turns four silent fallbacks into
four crashes.

**Why this priority**: P1 alongside User Story 1, deliberately. This is the way this mission most
plausibly breaks production, and it is invisible unless someone states it. Three of the four are on
`mission_runtime/resolution.py`'s resolution paths.

**Independent Test**: the same corrupt fixture, exercising the 4 degrade sites, asserting the fallback
value and that nothing propagates — across all three input shapes (`NFR-003`, `SC-002`).

**Acceptance Scenarios**:

1. **Given** a routed degrade site, **When** the read fails, **Then** its handler catches
   `MissionMetaReadError` and returns its documented fallback.
2. **Given** the 3 sites that pass `allow_missing=False` today (rows 8, 9, 12), **When** the file is
   **absent**, **Then** each still refuses — noting the wrapper returns `None` where they currently
   receive `FileNotFoundError`, so each needs an explicit `if result is None:` arm **in the same commit as
   its routing** (`FR-014`). **Not a drop-in swap**, and at row 8 the omission is a fail-open, not a
   cosmetic gap (`FR-004`).
3. **Given** `resolution.py:509`'s handler, which also swallows the **traversal-guard** `ValueError`,
   **When** it is **extended to `MissionMetaReadError` while retaining `ValueError`**, **Then** the
   traversal-guard behaviour is unchanged — verified by a test that trips the guard and captures the
   returned `""` pre and post, not by inspection. Stated this way because the earlier wording
   ("narrowed to `MissionMetaReadError`" ∧ "traversal-guard behaviour unchanged") was
   **self-contradictory**: it is satisfiable only by `except (MissionMetaReadError, ValueError)`, which is
   not a narrowing. Retaining `ValueError` is not a licence to catch more: the handler must name both types
   and **never** `except Exception` (`C-002`, all 6 handlers).

---

### User Story 3 - A read that bypasses the seam can no longer hide from the gate (Priority: P1)

Five read expressions (six invocation sites) reach `meta.json` **without `load_meta` at all**, via three
private parsers. The architectural floor test passes today **without ever seeing them**, because it anchors
on `json.loads`/`json.load` and resolves the first argument through same-function hops only. The
cross-function split alone defeats it.

**Why this priority**: P1. A gate whose green never established why the thing would otherwise have
appeared is the defect class this programme exists to close, and this one is load-bearing: it is why 13
sites were called "the remainder" while 5 further read expressions (6 invocation sites) were never counted
at all. The two totals are deliberately not added: the 13 is a **call-site** count and the 5 a
**read-expression** count, and summing across conventions is the error `Q1` exists to stop.

**Independent Test**: the widened gate flags a synthetic delegated-parse read **and** its positive twin
prints `sites: 1` while the inlined-but-unreachable control prints `sites: 0` (`SC-005`); and for the
**4** read expressions the widening structurally cannot reach, **no allowlist entry is written** — each is
covered by a filed issue plus the committed control. The denominator is an integer: **1 reached by the
widening and routed / 4 deferred with a control**.

**Acceptance Scenarios**:

1. **Given** the widened gate, **When** a read delegates its parse to a private same-module helper,
   **Then** the gate flags it — demonstrated with a synthetic module under `tests/architectural/` fixtures,
   since the real reachable one is routed.
2. **Given** the `git show` / `show_blob` / bare-parameter reads the widening cannot reach, **When** the
   gate runs, **Then** each is **absent from the allowlist** and instead carries a filed issue number plus
   the committed unreachability control. An allowlist entry is **forbidden**, not merely discouraged: it
   would be stale on arrival (`test_allowlist_entries_are_still_live`), break the floor equality
   (`test_allowlist_matches_floor`) and force the baseline up — the re-freeze the charter forbids. No
   "dated rationale" is required or possible: `load_allowlist` has **no date field**.
3. **Given** the widening raises the live count against a **shrink-only** ceiling, **When** it lands,
   **Then** the reachable site is **routed** in the same change so live returns to **7**, and
   `INLINE_META_READ_FLOOR`, `FLOOR_MARGIN`, `inline_meta_read_baseline` **and**
   `ROUTED_LOAD_META_FLOOR` are re-derived and printed in that same change — a stale ceiling reds nothing
   and silently leaves room for the next unrouted read.
4. **Given** a corrupt `meta.json` at any bypass site, **When** it is read, **Then** the operator learns
   the file is corrupt. Today all of them degrade to "blocks the advance" behind a generic dirty-worktree
   message that never says `meta.json`.

---

### User Story 4 - #2804's pin says what the design actually guarantees (Priority: P2)

`tests/regression/test_issue_2804_merge_resets_gate_artifacts.py` asserts **twice** under one
`# --- CONTRACT (RED on base) ---` banner, and **both** assertions are false after the merge, by two
different mechanisms:

1. `assert post_matrix.get("overall_verdict") == "pass"` (`:482`) — false because `overall_verdict` is a
   computed property where `any(v == "pending")` dominates, and the row-union admits the scaffold row.
2. `assert SCAFFOLD_TODO_MARKER not in json.dumps(post_matrix)` — false because the admitted scaffold row's
   `description` and `notes` **are** the marker (fixture rows at `:172-185`).

Measured directly through the reconciler, control first: `CONTROL filled fixture contains marker? False`;
merged `criterion_ids: ['AC-001', 'FR-001', 'FR-003']`; `overall_verdict: pending`;
`POST contains SCAFFOLD_TODO_MARKER? True`. Widening only the verdict assertion therefore cannot make the
marker pass — and the second assertion's content **is** the real #2804 contract, unsatisfiable *by design*
under the row-union authority model rather than merely stale. Two tests in the repository pin contradictory
answers for the same input, and the same commit shipped both.

**Why this priority**: P2 — it changes no product behaviour. But a repository that pins two answers to one
question cannot be reasoned about, and the contradiction is a **genuine pre-existing red**: reproduced on
pristine `upstream/main` `98198e980`, same selection, `1 failed in 96.97s`, `E assert 'pending' == 'pass'`.

**Independent Test**: both re-pinned assertions pass **on branch head with `src/` unchanged from the
measurement baseline** (the widened marker lives on the branch, so "passes on current `main`" is
unrunnable); its sibling `test_merge_driver_acceptance_matrix_writes_result_to_ours` still passes unchanged.

**Acceptance Scenarios**:

1. **Given** both re-pinned assertions, **When** the marker runs **on branch head with `src/` unchanged
   from the measurement baseline**, **Then** it passes — the verdict assertion satisfied whether the merge
   cleanly resolves *or* surfaces a structured conflict (the same widening the issue-matrix sibling already
   carries), and the marker assertion **re-pinned, not deleted**, to evidence-survival.
2. **Given** the widening, **When** `test_row_aware_merge_driver.py` runs, **Then** it is **unchanged and
   still green** — the two must stop contradicting each other without the new design being weakened.
3. **Given** #2804's pin has changed shape, **When** the tracker is read, **Then** a superseding issue
   records what is pinned now and why (including that `b04da00e1` **deleted** the unit gate
   `tests/merge/test_gate_artifact_merge_drivers_2804.py`, −249 lines, which held this invariant), and
   #2804 points at it.
4. **Given** the re-pinned assertions, **When** someone asks what they still pin, **Then** the answer is
   written down: assertion 1 pins that the verdict is one of the design's admissible values, assertion 2
   pins **evidence survival** — the accepted evidence handle appears in the merged document, negatively
   controlled against a take-theirs fixture (measured: `accepted evidence survives in merged doc: True`;
   `take-theirs control (placeholder alone): False`). `Q10` is **settled: no — keep the marker**; `"fail"`
   is the concrete disallowed verdict that makes the widened predicate falsifiable (`SC-010`).

---

### Edge Cases

- **A degrade site's fallback is itself derived from the malformed file** → it must not silently produce a
  plausible-but-wrong value; state which of the 4 this applies to.
- **`load_meta_fail_closed` takes one positional arg and no kwargs** (`core/paths.py:638`) — it hard-codes
  `allow_missing=True, on_malformed="raise"`. A site needing different semantics cannot use it as-is; say
  so rather than widening the wrapper. **Consequence in scope:** because `allow_missing=True` is hard-coded,
  `except FileNotFoundError` becomes **unreachable** at rows 8, 9 and 12 once they route — see `FR-013`.
- **A bypass site's parse succeeds but yields a non-mapping** → `_parse_meta_object` returns `None`;
  distinguish that from absent.
- **`_committed_meta_object` conflates absent-at-HEAD with corrupt-at-HEAD** via `{}` — but its
  `returncode != 0` check already separates them internally, so a fail-closed variant is writable without
  losing the newly-added case.
- **The gate widening produces false positives** → measured **0** over `src/`, from a triage of **19
  candidates → 17 rejected at clause 2 → 1 rejected at clause 3 → 1 accepted**. The precedent that a prior
  structural tightening was measured to have non-zero false positives and was therefore **not adopted**
  belongs to another mission and no requirement ID in *this* spec; it is cited as a precedent only, with no
  ID (the requirement ID cited in earlier drafts exists nowhere in this mission — see Standing rules). Measure before adopting, and
  if the count is non-zero, say so and pin. **And attribute the zero correctly: clause 2 holds it, not
  clause 3** (`FR-006`).
- **Two tests still disagree after the widening** → the mission has failed User Story 4 even if both are
  green; the point is one answer, not two passes.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Route the 7 raw-escape sites | As an operator, I want a malformed `meta.json` to raise a typed error naming the file, not a bare `ValueError` — **and raised by the seam, not by a translation wrapper at the call site** (`SC-001`). | High | Open |
| FR-002 | Preserve the 4 degrade arms | As a maintainer, I want each degrade site to keep degrading, with its handler changed to `MissionMetaReadError` in the same **work package**. **Land the routing first and quote the resulting escape as the red**, then change the handler — that ordering is the only way this requirement has a real red, and it is the **single** sanctioned exception to `C-002`'s "same edit" (see `FR-014`), because a routed-but-unhandled degrade site crashes loudly rather than fabricating a value. | High | Open |
| FR-003 | Preserve the 2 typed refusals | As a maintainer, I want the two sites that raise domain errors to keep raising those, not the wrapper's — routing and handler extension in **one commit** per site (`C-002`, `FR-014`). | High | Open |
| FR-004 | Handle the 3 `allow_missing=False` sites explicitly — routing, `None` arm and handler are ONE edit | As a maintainer, I want each to keep refusing on an absent file via an explicit `None` arm — **and the missing-file message must move into that arm**. **Name the fail-open, because it is the regression this mission would otherwise have shipped:** at `context/resolver.py:68-78` (row 8), routing without the `None` arm turns `or {}` from a mypy no-op into load-bearing control flow — absent `meta.json` → `{}` → `mission_id = feature_dir.name` (`:80`) → **a fabricated identity, silently**, with `MissingIdentityError` **never raised**. That is exactly the "removed legacy tolerance" the site's own comment (`:68-73`) was written to prevent. Rows 9 and 12 are the same shape with milder symptoms — the pre-existing arms raise the *same* exception types with the wrong cause (`decisions/service.py:141` → "has no mission_id field" instead of "meta.json not found"; `_resolve_planning_branch.py:127-131` → "not a JSON object", losing the `--target-branch` remediation). **One** existing test pins row 8: `tests/specify_cli/context/test_resolver.py:256` — `pytest.raises(MissingIdentityError, match="meta.json not found")`. `tests/integration/test_coord_loop_workspace.py:611,627` is **docstring prose**, not assertions — its class asserts `resolve_context` *succeeds*, so it cannot fail under arm-deletion. Run it as a real `_read_meta_json` consumer; never cite it as a pin. | High | Open |
| FR-005 | Make the bypass reads diagnosable (**5 read expressions / 6 invocation sites**; `Q11` enrolled) | As an operator, I want a corrupt `meta.json` at a bypass site to say so, instead of a generic dirty-worktree message. Criterion: `SC-012` — previously this requirement had **none**, which made `IC-04` closable with zero evidence. Scope is diagnosable-only **except `ref_advance.py:247`, which is routed** (R-1). | High | Open |
| FR-006 | Widen the gate to the one reachable bypass shape | As a maintainer, I want the floor test to see a read whose parse is delegated to a private same-module helper. **State the predicate, not just the count.** The scanner accepts a call iff: **(1)** it is `json.loads`/`json.load`, import-binding resolved, with ≥1 arg; **(2)** `_read_source_base(args[0], fn)` resolves the argument — through same-function assignment/`with`-binding hops — to a `read_text`/`open` call (**`read_bytes` added by this requirement**); **(3)** `is_meta_path_expr(base, fn)` holds: a canonical meta-path name (`meta_path`/`meta_file`/`meta_json`/`target_meta_path`), a `<dir> / "meta.json"` join, or a bare `Name` resolved through ≤`_MAX_ASSIGNMENT_HOPS` same-function reassignments to such a join. The widening adds **one hop into a private same-module single-parameter parse helper** at clause 2's boundary. Measured: **19 candidates → 17 rejected at clause 2 → 1 rejected at clause 3 → 1 accepted** (`ref_advance.py:247`), **0** false positives over `src/`. **Clause 2 is the load-bearing guard that holds false positives at zero; clause 3 rejects exactly ONE candidate** — the earlier "31 candidates, 30 rejected at clause 3" reproduces under no definition and is refuted. Recorded because it licenses the wrong future move: a later widening of clause 2 unlocks ~17 candidates with **no** measured clause-3 protection. The `read_bytes` half adds **0** new sites over `src/`, so it is marked **"no red possible — synthetic pin required"** (`tmp_path` fixture pair, measured 1 → 2). | High | Open |
| FR-007 | Do NOT allowlist the unreachable sites — defer them with a control | As a maintainer, I want the scanner-invisible reads **excluded from the allowlist**, deferred by a filed issue, and covered by a **committed unreachability control with a positive twin** (`SC-005`). `inline_meta_read_baseline` stays **7**. **The closure is unconditional — say so, so nobody bumps the baseline and then weakens the staleness guard:** `test_allowlist_entries_are_still_live` requires every entry to match a live **detected** site, so an entry for a scanner-invisible shape is stale at **any** baseline. Bumping `inline_meta_read_baseline` does not open this door; it only invites the follow-on move of weakening `test_allowlist_entries_are_still_live`, which is forbidden. | High | Open |
| FR-008 | Re-derive **both** floors in the same change | As a maintainer, I want `INLINE_META_READ_FLOOR`, `FLOOR_MARGIN` **and** `ROUTED_LOAD_META_FLOOR` re-derived and printed when the widening plus the `ref_advance.py:247` routing lands (R-1), so no shrink-only ceiling or growth floor goes stale. The inline re-derivation confirms **7** (routing returns live inline to 7); the routed floor **moves**, by the precedented rule below (`NFR-002`, `SC-011`). Marked **"no red possible"** in the red-first register: a floor is only stale *after* the change it accompanies, so its correction cannot precede it. | High | Open |
| FR-009 | Re-pin **both** of #2804's red assertions | As a maintainer, I want the marker to assert what the design guarantees. **Assertion 1** (`:482`, `overall_verdict == "pass"`) is **widened**, matched to its issue-matrix sibling's already-widened form. **Assertion 2** (`assert SCAFFOLD_TODO_MARKER not in json.dumps(post_matrix)`) is **re-pinned, not deleted** — to **evidence survival**: the accepted evidence handle must appear in `json.dumps(post_matrix)`, negatively controlled against a **take-theirs fixture** where it must not (measured: `True` / `False`). Deleting it would discard the only remaining executable statement of the real #2804 contract; leaving it unchanged is impossible, since the row-union admits the scaffold row whose `description`/`notes` **are** the marker. | Medium | Open |
| FR-010 | Supersede #2804 in the tracker | As the operator, I want a new issue recording what is pinned now, with #2804 pointing at it, and citing that `b04da00e1` deleted `tests/merge/test_gate_artifact_merge_drivers_2804.py` (−249 lines) — the unit gate that held this invariant. | Medium | Open |
| FR-011 | File the product defect | As the operator, I want the pending-poisons-the-aggregate defect filed with `gates_core.py:525` as evidence and the suppression rule as its candidate fix. | High | Open |
| FR-012 | Amend `load_meta_fail_closed`'s docstring in the same commit as the degrade routing (R-2) | As a maintainer, I want `core/paths.py:648-651` to stop stating that "callers that must stay deliberately silent about corruption (placement probes, best-effort displays) … are not routed here", because D4=(a) routes exactly that class onto this seam. The docstring is the canonical authority's own client contract; leaving it contradicting its client set re-opens the "is this `meta.json` readable" question `NFR-002` exists to keep closed. Criterion: `SC-014`. | High | Open |
| FR-013 | Remove the handlers that routing makes dead | As a maintainer, I want the `except FileNotFoundError` arms at census rows 8, 9 and 12 **removed** once those sites route, because `load_meta_fail_closed` hard-codes `allow_missing=True` and therefore never raises `FileNotFoundError` — the arm becomes effect-free and unreachable. Both the charter's review checklist and `CLAUDE.md` reject empty or effect-free exception handlers ("either remove it and let the exception propagate, or add the concrete recovery logic"). The refusal each arm used to provide moves into the `if result is None:` arm (`FR-004`), so removal loses no behaviour. Criterion: `SC-015`. | High | Open |
| FR-014 | Per-site atomicity of routing + `None` arm + handler | As a maintainer, I want each `allow_missing=False` site's **routing, its `if result is None:` arm and its `except` handler** to be **one indivisible edit**, owned by whichever work package routes that site — sliced **by site, not by arm**. Splitting routing (rows 8/9/12) from the `None` arm is what produced the fail-open in `FR-004`; splitting a refuse-typed site's routing from its handler makes `SC-001` pass and `SC-003` fail (`MissionMetaReadError` is a `RuntimeError`). The **only** sanctioned exception is `FR-002`'s 4 degrade sites, where "same edit" reads "same work package" so the routing-first red exists. Criterion: `SC-016`. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Fail closed per refuse site | At the **9 refuse** sites, zero malformed reads yield a value indistinguishable from a valid one — asserted per site, and **asserted on the absent-file arm too**, because that is where the indistinguishable value would come from: at row 8 an omitted `None` arm returns `{}` and yields `mission_id = feature_dir.name`, a **fabricated identity** that is exactly "a value indistinguishable from a valid one". This NFR is therefore only satisfiable if `FR-014`'s per-site atomicity holds; a routing that lands without its `None` arm violates *this* NFR even while `SC-001` passes. **The 4 degrade sites are knowingly indistinguishable** (`""`, `None`, `legacy-<slug>`, `None` are all values a *valid* file also yields); D4=a preserves that arm, so the residue is **recorded and filed** (`SC-009` register), with `Q4` as its remedy. The un-scoped form of this NFR was false by construction and closable only by narration. | Security | High | Open |
| NFR-002 | No second predicate answering "is this `meta.json` readable"; the routed count is two-sidedly bounded | **Kept clause (architecturally real):** the count of distinct predicates answering "is this `meta.json` readable" does not increase. A 1:1 `load_meta` → `load_meta_fail_closed` swap *is* count-neutral (both are in `ROUTED_CALLEES`). Criterion: `SC-013` — enumerate the predicate symbols pre and post; previously this clause had none, so 4–5 sites could each author a local answer. **Struck clause:** the "routed budget is ONE call / the floor is immovable" claim. It had no stated justification and was self-inflicted: `ROUTED_CALLEES` matches **callee names**, not the call graph (it counts `doc_analysis/doc_state.py`'s *locally defined* `_require_meta`), and the census is global over `src/`, so any unrelated commit adding a call named `load_meta*` moves the number — the gate's own header records **three** prior false reds from this miscount. Raising a growth floor toward live is the ratchet *tightening*: the precedented operation, performed on 2026-08-04 (`117 → 126`, "to restore the established 3-below-live gap"), and already required of the inline floor by `FR-008`. That asymmetry was the load-bearing error. **Two-sided bound:** live routed measures **129** with `ROUTED_LOAD_META_FLOOR = 126` and `ROUTED_LOAD_META_FLOOR_MARGIN = 4`, and `test_routed_load_meta_floor` asserts **three** things — `len >= FLOOR`, `len > FLOOR` (explicitly anti-vacuous: "never a tautological `>= len(routed)`") and `len - FLOOR <= MARGIN`. The strict inequality makes the admissible band **`[127, 130]`**, not `[126, 130]`: **126 is RED**. So the constraint binds **downward as well as upward** — a routing pass that *collapses* two calls into one reds this gate from below, and this programme has already had three floor mismatches caused by exactly that kind of fold. Under R-1 the `ref_advance.py:247` routing spends the headroom (**129 → 130**) and `ROUTED_LOAD_META_FLOOR` is **re-derived in the same change** to restore the established 3-below-live gap, printed by the change rather than assumed here. | Maintainability | High | Open |
| NFR-003 | Behaviour preserved at the degrade sites | For each of the 4, the fallback is identical pre- and post-change across **all three** input shapes — malformed, **absent**, and **valid**. The malformed-only form let a routing that preserved one arm and broke another pass. Enumerated by `SC-002` as **4 sites × 3 shapes = 12 captured lines**, with the input count printed; a probe that captures fewer than 12 does not satisfy this NFR regardless of what its `diff` says. | Reliability | High | Open |
| NFR-004 | The gate's green means something | The widened gate flags a synthetic delegated-parse read **and** its positive twin prints `sites: 1` (`SC-005`) — a bare `sites: 0` negative is the vacuous gate `architectural-gate-non-vacuity` forbids. **No allowlist entry is written for the unreachable sites** (`FR-007`), so the old form of this NFR — "the allowlist entries are shown to be necessary … with a dated rationale" — is void twice over: the entries must not exist, and `load_allowlist` has no date field. What replaces it: for each of the **4** deferred read expressions, the committed control demonstrates the shape is undetected by the **widened** scanner, and the twin demonstrates the scanner is not simply broken. Denominator, as an integer: **1 reached and routed / 4 deferred with a control / 0 allowlisted**. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Preserve refuse-vs-degrade | Per D4=a, no site's arm changes. The split is **4 degrade / 2 refuse-typed / 7 refuse-raw** — re-derived; the inherited "6 divergent-wrapper / 7" was wrong. | Technical | High | Open |
| C-002 | `MissionMetaReadError` is a `RuntimeError` | Not a `ValueError`. **All SIX `except ValueError` handlers must change in the same edit as their routing** — enumerated at `mission_runtime/resolution.py:514`, `:853`, `:1108`; `decisions/service.py:141`; `missions/_resolve_planning_branch.py:122`; `upgrade/feature_meta.py:43`. That is the 4 degrade sites *and* the 2 refuse-typed ones, which would otherwise leak the wrapper instead of `DecisionError` / `PlanningBranchResolutionFailed`. `FR-003`/`SC-003` assert that outcome; this constraint is what mandates the mechanism. Scoping it to "every degrade handler" left two sites unmandated. **The never-`except Exception` rule applies to all SIX handlers, not only the 2 refuse-typed ones** — `MissionSelectorAmbiguous` is confirmed **not** a `ValueError` (`_read_path_resolver.py:44`, plain `Exception`) and is raised *inside* `resolution.py:509`'s `try`, so a broadened catch there silently swallows an ambiguous-handle refusal (`SC-007`). **Reconciliation with `FR-002`:** "same edit" means one commit everywhere except `FR-002`'s 4 degrade sites, where it means one work package (two commits) so the routing-first red exists; as previously written the two requirements contradicted each other and an implementer would have picked silently. | Technical | High | Open |
| C-003 | Name the resolver by symbol | Three envelope→`project_uuid`-style resolvers exist and disagree; and three private parse paths exist. Cite `load_meta_fail_closed` at `core/paths.py:638` and `MissionMetaReadError` at `:506` by symbol, never by line alone. | Technical | Medium | Open |
| C-004 | Do not widen the wrapper — but name the alternative, and get the reason right | `load_meta_fail_closed(feature_dir)` hard-codes its policy, and all 13 routable sites do pass a directory, so **there is no dead end among the 13**. **The earlier claim that the bypass sites "hold text/bytes or a temp path and structurally cannot use it" was wrong on two counts.** (1) **2 of the 5 hold real filesystem paths whose parents are feature dirs**, so the seam fits **verbatim**: `ref_advance.py:242` (`meta_path = worktree / path`, and `:315` gates on `Path(path).name == _META_FILENAME`) and `implement_cores.py:421-427` (`source = (repo_root / Path(repo_rel)).resolve()`, under a `name == _META_JSON_FILENAME` gate). The real obstacle there is the **routed budget**, not structure — and R-1 spends it on the first of the two. (2) **`_parse_meta_text` cannot serve the two blob sites at all**: it takes a `Path` and performs the read itself (`mission_metadata.py:331-349`), so it can accept neither `git show` stdout (`str`) nor `show_blob` output (`bytes`). A public entry "over `_parse_meta_text`" is writable for exactly one site — `merge_driver.py:167`, a temp-blob path. **Recorded seam family, three tiers:** **L1** pure decode (`text\|bytes → dict\|None`, typed) — **the missing primitive; filed, not built here** (`SC-009`); **L2** path-level (`_parse_meta_text`, exists, needs a public fail-closed entry for the temp-blob case); **L3** dir-level (`load_meta_fail_closed`, exists, reachable by 2 of the 5). Diagnosable-only remains the right *scope* call for the four non-routed sites, but it rests on the **budget**, not on a false structural claim. The `_committed_meta_object` note is correct as written — `returncode != 0` does separate absent-at-HEAD from corrupt-at-HEAD. The seam question is adjudicated **here**, by this constraint plus `NFR-002`/`SC-013`; it is no longer deferred to an `NFR-002` that never answered it. | Technical | High | Open |
| C-005 | Measure gate false positives before adopting | Measured **0** over `src/`, from **19 candidates → 17 rejected at clause 2 → 1 at clause 3 → 1 accepted**. The precedent (a structural tightening measured to have non-zero false positives and therefore **not** adopted, with the case pinned red instead) is cited without a requirement ID, because the ID earlier drafts used exists in no artifact of this mission (see Standing rules). Measure first; if non-zero, pin rather than adopt. **This constraint survives on the number and previously failed on the reasoning** — it attributed the zero to clause 3, which rejects one candidate; clause 2 is the guard (`FR-006`). | Process | High | Open |
| C-006 | Do not fix the product defect here | The scaffold-row suppression rule is rejected for this mission. File it (`FR-011`). | Process | High | Open |
| C-007 | Sweep serialisation | `tests/sync` and `tests/cli` must never sweep concurrently. **A sibling mission may hold the `tests/sync` window** — check before sweeping. This mission's cone is `tests/specify_cli`, `tests/mission_runtime`, `tests/regression`, `tests/merge`, `tests/architectural`, plus the 9 directories the import-line grep proved were under-declared: `tests/integration`, `tests/missions`, `tests/runtime`, `tests/next`, `tests/context`, `tests/status`, `tests/upgrade`, `tests/coordination`, `tests/lanes`. **None of those is `tests/sync` or `tests/cli`**, so none collides with the sibling window. Note `tests/specify_cli/cli/commands/` is *inside* `tests/specify_cli` and is **not** the barred top-level `tests/cli`. | Process | High | Open |
| C-008 | Red first, where a red is possible | Requirements whose red is achievable land red-first with the red as the *consequence*. Those already true at baseline, or whose correction cannot precede the change it accompanies, are declared with the exception spelled out in the red-first register below — never padded with an inspection claim. | Process | High | Open |
| C-009 | File, do not absorb | Out-of-scope findings become issues. **Criterion: the `SC-009` filing register — this constraint previously had zero enforcement anywhere, while the work package that edits `_VCS_LOCK_META_FIELDS` and the three duplicated lock-only comparisons is exactly the one that would be tempted to absorb them.** The `Q8` finding (lock-only comparison duplicated ×3; `_VCS_LOCK_META_FIELDS` declared twice) is register row 4 and must be filed **before** that code is edited, with the issue number cited in a comment at the surviving comparison. The L1 seam primitive (`C-004`) and the `_baselines.yaml` register deviation are rows 6 and 7. | Process | High | Open |

### Key Entities

- **`load_meta_fail_closed(feature_dir)`** — `core/paths.py:638`, one positional arg, no kwargs, in
  `__all__`. Hard-codes `allow_missing=True, on_malformed="raise"`. Its docstring at `:648-651` names the
  degrade caller class as non-clients and is amended by `FR-012`.
- **`MissionMetaReadError(meta_path, cause)`** — `core/paths.py:506`, MRO `RuntimeError → Exception`.
  **Not a `ValueError`.**
- **The 13 sites** — enumerated with arms in `research/3162-census.md` §1; arms **4 degrade / 2
  refuse-typed / 7 refuse-raw**.
- **The 6 `except ValueError` handlers** — `mission_runtime/resolution.py:514`, `:853`, `:1108`;
  `decisions/service.py:141`; `missions/_resolve_planning_branch.py:122`; `upgrade/feature_meta.py:43`.
  All six catch bare `ValueError`. (A naive `grep -c` gives **9** — it catches a comment at
  `resolution.py:491` plus two unrelated handlers.)
- **The bypass sites — 5 read expressions / 6 invocation sites** — `git/ref_advance.py`
  `_committed_meta_object` (`:192`, read at `:203` via `git show`) and `_meta_change_is_vcs_lock_only`
  (`:231`, read at `:244` via `read_text`, path built at `:242`), both parsing via `_parse_meta_object`
  (`:181`); `cli/commands/implement_cores.py` `_parse_meta_mapping` (`:259`) fed by `git.show_blob`
  (`:335`) and `source.read_bytes()` (`:427`, path built at `:421-427`); `cli/commands/merge_driver.py`
  `_load_json_object` (`:167`, read at `:171` via `read_text`), **invoked twice** — `:243` and `:244` —
  which is the whole difference between the two counts.
- **The ledger** — `tests/specify_cli/test_meta_fail_closed_full_census_contract.py`, `pending-batch-a`
  rows, exact-equality in **both** directions: routing a site without deleting its row fails the "stale
  row" arm, deleting a row without routing fails the "unaccounted" arm. Each routing and its row deletion
  are therefore one commit.
- **The floor test** — `tests/architectural/test_inline_meta_read_gate.py`: `INLINE_META_READ_FLOOR = 7`
  (`:127`), `FLOOR_MARGIN = 2` (`:134`), `ROUTED_LOAD_META_FLOOR = 126` (`:221`),
  `ROUTED_LOAD_META_FLOOR_MARGIN = 4` (`:220`); allowlist `tests/architectural/inline_meta_read_allowlist.yaml`
  (7 entries, baseline 7). The mutually-locking assertions are `test_inline_meta_read_floor` (`:1061`),
  `test_routed_load_meta_floor` (`:1084`), `test_inline_meta_read_gate_green_against_seeded_allowlist`
  (`:1109`), **`test_allowlist_matches_floor` (`:1116`, an EQUALITY —
  `len(allowlist) == INLINE_META_READ_FLOOR`)**, `test_allowlist_shrink_only` (`:1125`) and
  `test_allowlist_entries_are_still_live` (`:1166`). The equality is the assertion that forecloses the
  floor→8/allowlist→7 escape, and no earlier mission artifact mentioned it.
- **#2804's marker** — `tests/regression/test_issue_2804_merge_resets_gate_artifacts.py`, **two** red
  assertions under one `# --- CONTRACT (RED on base) ---` banner: the verdict at `:482` and
  `assert SCAFFOLD_TODO_MARKER not in json.dumps(post_matrix)`; scaffold fixture rows at `:172-185`.
- **Its contradicting sibling** — `tests/specify_cli/cli/commands/test_row_aware_merge_driver.py:427-448`.
- **`overall_verdict`'s value set** — `pass`, `pending`, `fail`, `pass_pending_consolidation`
  (`acceptance/matrix.py:247-272`); `fail` is reachable from a one-criterion fixture (`:259`).

## Success Criteria *(mandatory)*

Every criterion below is a command or an artifact, not a claim. The post-plan pass showed **9 of 11** were
satisfiable in full while the defect survived; each is restated with its input count, its positive control,
and — where the criterion is a negative — its positive twin.

- **SC-001**: Of the 7 raw-escape sites, **7/7** raise `MissionMetaReadError` from a **real corrupt
  `meta.json` on disk**, called through the site's own public entry point — **no patching of
  `load_meta_fail_closed`** — with each test id naming its census row (rows 4, 5, 6, 7, 8, 10, 11). The
  input count is printed — **except row 11, whose corrupt-file arm is structurally unreachable.** See the
  `Q7` row in Open Decisions: canonicalization indexes candidate dirs via
  `load_meta(entry, on_malformed="none")` (`context/mission_resolver.py:176`), which **skips** a corrupt
  meta, so a corrupt file makes the handle unresolvable and `:862`'s re-read never executes. The two
  readers' accept-sets are identical, so no content can be valid for the indexer and corrupt for the
  re-read. **Row 11's denominator is therefore 6/7 behavioural + 1 execution-traced**, and the substitute
  is stronger than an AST-only fallback: a `sys.setprofile` trace asserting `read_primary_meta` enters
  `load_meta_fail_closed` **exactly twice** on a **real, valid** file through a public entry — **0** before
  routing, **2** after, **1** under a collapsing fold. That is the seam proof and the anti-fold control in
  one instrument, and it patches nothing.
  **Seam proof — the hole this criterion previously left open.** Type + message + real file + real entry
  point is satisfied with **zero routing**, by wrapping the 7 public entries in
  `except ValueError: raise MissionMetaReadError(...)`: routed count unchanged at 129, inline gate silent.
  So each site additionally requires **both**: (a) *behavioural* — the raised exception's traceback contains
  a `core/paths.py` frame inside `load_meta_fail_closed`, and its `__cause__` is the underlying decode
  error; and (b) *structural* — the site's read expression is a `load_meta_fail_closed(` call, the module
  contains **no** `raise MissionMetaReadError` of its own, and the site's `pending-batch-a` ledger row is
  deleted in the same commit (`tests/specify_cli/test_meta_fail_closed_full_census_contract.py`).
- **SC-002**: For each of the 4 degrade sites, the fallback is captured by **one probe script run twice** —
  once with `PYTHONPATH=<worktree at the measurement baseline>/src`, once at branch head — both redirected
  to files, and `diff pre.txt post.txt` empty with both files quoted at non-zero `wc -l`. **The probe's
  inputs are enumerated, not left to the implementer: 4 sites × 3 shapes (malformed, absent, valid) = 12
  captured lines per run, and the input count is printed with the capture.** A malformed-only probe
  satisfied the earlier form while the absent-file arm regressed untouched — the exact defect `NFR-003` was
  rewritten to catch — so a capture of fewer than 12 lines fails this criterion regardless of its `diff`.
  **Positive control first:** deliberately break one handler, show the `diff` non-empty, and quote it. A
  same-run double-print, or an empty diff over two empty captures, is not evidence.

  **Scope limit — what SC-002 structurally cannot see (recorded 2026-08-06).** This criterion's
  subject is the routed **site**: 4 sites × 3 shapes. A *stranded arm* is by construction **not** at
  a site — it is an `except` clause on a transitive **caller**, several hops from the edit, that
  catches `ValueError`/`OSError` and therefore stops absorbing corruption the moment the site starts
  raising `MissionMetaReadError` (a `RuntimeError`). No number of shapes per site reaches it: the two
  axes are orthogonal, so **a green `SC-002` is not evidence about that class at all**. WP02's blocker
  — four stranded arms in `cli/commands/agent/` — passed straight through a green `SC-002` and was
  caught only by a chain-local sweep. The instrument for that class is
  `scripts/sweep_degrade_arms_on_routed_chain_3162.py`, run with `--self-check` so its silence is
  calibrated; every WP that routes a site must run it seeded with the routed function, using dotted
  qualnames. Do not read this criterion as covering caller-chain strandings, and do not widen it to
  try: the site-scoped probe is correct for what it measures.
- **SC-003**: Of the 2 typed-refusal sites, **2/2** still raise their own domain error — and each handler
  catches `MissionMetaReadError` **by name, never `except Exception`** — plus a negative control showing a
  **valid** file returns cleanly.
- **SC-004**: Of the 3 `allow_missing=False` sites, **3/3** still refuse on an **absent** file via an
  explicit `None` arm carrying the **missing-file** message. **The assertion is on the MESSAGE, not the
  exception type.** A type-only guard is green at baseline, green after, **and green under arm-deletion at
  rows 9 and 12**, because the pre-existing arms raise the *same* types with the wrong cause — so a
  type-only form proves nothing. Each site is proven by a guard captured green on the measurement baseline
  **and** a mutation probe: delete the `if result is None:` arm, quote the failing assertion (which must be
  the message assertion), restore it. Row 8's message assertion is `match="meta.json not found"`, already
  pinned at `tests/specify_cli/context/test_resolver.py:256`. (A plain base-branch red is impossible here —
  the absent-file behaviour is already correct at baseline; see the register.)
- **SC-005**: The widened scanner flags the **1** reachable site (`ref_advance.py:247`), demonstrated. The
  4 scanner-invisible read expressions are **not allowlisted**; each carries a filed issue **and** a
  committed unreachability control — a scratch module with the read fully inlined, scanned by the
  **widened** scanner, printing `sites: 0`, the post-widening repeat of control `C3`. **The control is
  accompanied by a POSITIVE TWIN: the same scratch module with the read inlined and the path named
  `meta_path`, scanned by the same widened scanner, printing `sites: 1`.** A bare `sites: 0` is
  indistinguishable from a broken scanner and is the vacuous negative `architectural-gate-non-vacuity`
  forbids. **Both fixtures live under `tests/architectural/` and are scanned by explicit argument — NOT
  under `src/`**: `scan_inline_meta_reads` walks `SRC_ROOT`, so a fully-inlined read committed there would
  raise the live census and red the very floor the control exists to prove.
  **`inline_meta_read_baseline` is unchanged at 7.**
- **SC-006**: Run the widened scanner **twice** — against `src/` at the measurement baseline and against
  branch head — printing both counts, and report the **widening delta** (sites the predicate change adds at
  a fixed tree) and the **code delta** (sites the source change adds at a fixed predicate) **separately, as
  two numbers**. The ratchet cannot itself distinguish "the widening found a real site" from "a new unrouted
  read landed", so reporting one number hides both. Admissible outcome: the reachable site is **routed**,
  live returns to **7**, and `INLINE_META_READ_FLOOR`, `FLOOR_MARGIN` and `inline_meta_read_baseline` all
  stay at 7. **The earlier branch "or made diagnosable → live returns to 7" is STRUCK: it is false.**
  Diagnosability changes neither the `json.loads` in `_parse_meta_object` (`ref_advance.py:181-189`) nor the
  call at `:247`, so the widened scanner still flags it and live stays at 8; measured
  (`ref_advance.py DIAGNOSABLE → widened: FLAGGED :247`). **Any raised inline floor requires the code delta
  printed as 0 and the raise argued in the PR body.**
- **SC-007**: `resolution.py:509`'s traversal-guard behaviour is unchanged, proven by a test that **trips
  the guard** and asserts the **stated outcome: the call still returns `""`**, captured pre and post — not
  merely `pytest.raises(ValueError)`, which is red at baseline and green after while the degrade-to-`""`
  behaviour `US2` scenario 3 protects is silently deleted. **Second assertion:** an **ambiguous** mission
  handle still propagates `MissionSelectorAmbiguous` — confirmed **not** a `ValueError`
  (`_read_path_resolver.py:44`, plain `Exception`) and raised *inside* the same `try`, so
  `resolution.py:493-498`'s note must still hold after the handler change. **Third:** none of the **6**
  handlers listed in `C-002` is `except Exception` — asserted over all six, not only the 2 refuse-typed
  ones, because a broadened catch at `:509` would swallow the ambiguity refusal.
- **SC-008**: Both of #2804's re-pinned assertions pass **on branch head with `src/` unchanged from the
  measurement baseline** — verified by `git diff --stat <baseline> -- src/` printing **nothing**, quoted.
  ("Passes on current `main`" is unrunnable as phrased: the widened marker lives on the branch.) **And**
  `git diff --stat upstream/main -- tests/specify_cli/cli/commands/test_row_aware_merge_driver.py` prints
  **nothing** — quoted. Both runs redirected with node counts. Because the marker's own path crosses this
  mission's routing (`merge/executor.py:116` → `resolve_placement_only` → `_assemble_core_fragments` →
  census rows 2 and 3) and runs `spec-kitty merge-driver-meta` **as a subprocess** (so an edit is invisible
  until `pip install -e .`), this evidence is **re-captured at final integration**, not only in the lane
  that widens the marker.
- **SC-009**: **A filing register — one row per mandated filing, each verified with
  `gh issue view <n> --json number,title,body` and the number recorded here.** ≥5 filings are mandated by
  this spec and only 2 were previously pinned:

  | # | Filing | Mandated by | Issue |
  |---|---|---|---|
  | 1 | Superseding issue for #2804: what is pinned now, why the shape changed, and that `b04da00e1` deleted `tests/merge/test_gate_artifact_merge_drivers_2804.py` (−249 lines) | `FR-010`, `Q9` | #3232 |
  | 2 | The pending-poisons-the-aggregate product defect, `acceptance/gates_core.py:525` as evidence, the scaffold-row suppression rule as candidate fix | `FR-011`, `C-006` | #3231 |
  | 3 | Deferral of the 4 scanner-invisible bypass read expressions (no allowlist entry is possible) | `FR-007`, `NFR-004` | `[to record]` |
  | 4 | `Q8`: lock-only comparison duplicated ×3, `_VCS_LOCK_META_FIELDS` declared twice — filed **before** that code is edited, number cited in a comment at the surviving comparison | `C-009` | **#3228** (filed `2026-08-06T01:11:16Z`, before WP05's first code commit). **Measured correction: ×2, not ×3** — 2 declarations (`ref_advance.py:42`, `implement_cores.py:50`) and 2 comparators (`ref_advance:_is_vcs_lock_only_meta_change:210`, `implement_cores:_is_vcs_lock_only_meta_diff:241`). The third candidate, `specify_cli.acceptance:ACCEPTANCE_PROVENANCE_FIELDS` (`acceptance/__init__.py:76`), is a 7-field acceptance-provenance overlay, a different concept |
  | 5 | `NFR-001`'s residue: the 4 degrade sites remain knowingly indistinguishable under D4=a, with `Q4` (log on degrade?) as the candidate remedy | `NFR-001`, `Q4` | `[to record]` |
  | 6 | The **L1 pure-decode primitive** (`text\|bytes → dict\|None`, typed) — the missing seam tier without which the two blob sites cannot route | `C-004` | **#3229** (filed `2026-08-06T01:11:41Z`, before WP05's first code commit) |
  | 7 | `inline_meta` is absent from `tests/architectural/_baselines.yaml` (verified: `grep -c` → 0), so the allowlist this mission governs sits **off** the charter's Burn-down-Policy register | charter Burn-down Policy (a) | `[to record]` |
  | 8 | Full routing of the 4 non-routed bypass sites (the `Q2` residue after R-1) | `Q2`, `C-004` | **#3230** (filed `2026-08-06T01:12:07Z`, before WP05's first code commit). Deferred on the **routed budget** + the missing **L1** tier — **not** on `C-004`'s struck structural claim |

- **SC-010**: The widened assertion is pinned by a companion test
  `test_widened_2804_assertion_rejects_wrong_verdict` that shows the widened predicate **fails**, and
  the failing case is **the defect's own fixture — not merely some disallowed value**. This is the
  correction: `overall_verdict` ∈ {`pass`, `pending`, `fail`, `pass_pending_consolidation`}
  (`acceptance/matrix.py:247-272`), the sibling test pins `pending`, so a widened predicate must admit
  `pending` — and **`pending` IS the #2804 defect's signature**. A predicate of the form
  `verdict in {"pass","pending"}` therefore passes with the regression fully present, while a companion test
  fed a `fail` fixture reports "non-vacuous" about a value unrelated to the defect. So the companion's
  fixture must be **the defect's own shape**: the take-theirs / scaffold-clobber document in which the
  criteria are reset to the placeholder and the accepted evidence handle is **absent** (measured:
  `take-theirs control (placeholder alone): False`), and the **re-pinned pair of assertions must FAIL on
  it**. `"fail"` is recorded as the concrete disallowed verdict for assertion 1 (reachable from a
  one-criterion fixture, `acceptance/matrix.py:259`) and named in the docstring, but a companion fed only a
  `fail` verdict is **not** sufficient evidence: `pending`, the defect's actual signature, must be
  *admitted* by the widened predicate, so assertion 2's evidence-survival pin is what carries the
  falsifiability. **`Q10` is settled: no — the marker is kept.**
- **SC-011**: The live **routed** count is printed pre and post. **Pre must be 129 and inside `[127, 130]`**
  — `ROUTED_LOAD_META_FLOOR = 126`, `MARGIN = 4`, and the band's bottom is **127, not 126**, because
  `test_routed_load_meta_floor` asserts `len > FLOOR` **strictly** (its own docstring: "never a tautological
  `>= len(routed)`") in addition to `len >= FLOOR` and `len - FLOOR <= MARGIN`. **126 is RED.** The
  constraint is therefore **two-sided**: post must be **130** (R-1 spends the one call of headroom on
  `ref_advance.py:247`) and must lie inside the band re-derived in the same change, and a routing pass that
  *collapses* call sites downward reds this gate just as surely as one that adds too many. The re-derived
  `ROUTED_LOAD_META_FLOOR` restores the established 3-below-live gap and is **printed by the change**
  (precedent: `117 → 126` on 2026-08-04, for exactly this reason). A criterion that only bounds from above
  is satisfied by a change that breaks the gate.
- **SC-012** *(new — `FR-005` previously had NO criterion, which made its work package closable with zero
  evidence)*: For **each bypass site — 5 read expressions / 6 invocation sites, convention declared and
  input count printed** — a corrupt fixture produces an operator-visible message that names **`meta.json`**
  **and** the path, asserted on the message text, not the exception type. **Negative control on the valid
  file:** the same site returns its normal result and emits no such message. The generic
  dirty-worktree message must no longer be the only thing the operator sees at any of them.
- **SC-013** *(new — `NFR-002`'s kept clause previously had no criterion)*: Enumerate the symbols that
  answer "is this `meta.json` readable" **pre and post**, printed as two lists with their counts, and show
  the post list is not longer and contains no new local predicate. The enumeration is by symbol name over
  `src/` (the same population `ROUTED_CALLEES` scans, plus locally-defined predicates such as
  `doc_analysis/doc_state.py`'s `_require_meta`, `_parse_meta_object`, `_parse_meta_mapping`,
  `_load_json_object`). **Mutation probe:** add a second local predicate at one bypass site, show this
  criterion goes red, revert.
- **SC-014** *(new — `FR-012`)*: `core/paths.py:648-651` no longer states that the degrade caller class is
  not routed here; the amended text names the routed degrade callers as clients and states which arm they
  keep. Verified by quoting the docstring pre and post, **and** by `git show --stat <sha>` for the routing
  commit containing **both** `src/specify_cli/core/paths.py` and the routed degrade site files — the
  docstring amendment and the routing are one commit (R-2).
- **SC-015** *(new — `FR-013`)*: After routing, `grep -n "except FileNotFoundError"` over the three
  functions at census rows 8, 9 and 12 returns **0 matches**, quoted with the input count. Justification
  printed alongside: `load_meta_fail_closed` hard-codes `allow_missing=True` (`core/paths.py:638`), so the
  arm is unreachable, and the refusal it carried now lives in the `if result is None:` arm (`SC-004`'s
  message assertions are the proof that no behaviour was lost). This criterion is red before the removal
  (the greps return 3) and green after.
- **SC-016** *(new — `FR-014`)*: For each `allow_missing=False` site, `git show <sha> -- <file>` shows the
  routing hunk, the `if result is None:` arm and the `except` change **in one commit**, quoted. **Mutation
  probe per site:** re-apply that commit with only the `None` arm removed and quote the failing assertion —
  at row 8 it must be `tests/specify_cli/context/test_resolver.py:256`'s
  `match="meta.json not found"` — **that assertion alone**, proving the
  arm is load-bearing rather than decorative. `tests/integration/test_coord_loop_workspace.py:611,627` is **docstring prose**, not assertions — its class asserts `resolve_context` *succeeds*, so it cannot fail under arm-deletion. Run it as a real `_read_meta_json` consumer; never cite it as a pin. The 4 degrade sites are the declared exception: their two
  commits must sit inside **one** work package, and `git log --oneline` for that lane is quoted to show it.
- **SC-017** *(new)*: `ruff check` and `mypy --strict` over the changed files print zero issues and zero
  warnings, quoted with the file list and count. No `# noqa`, `# type: ignore` or per-file ignore is added
  to achieve it.

### Which requirements can be red-first, and which cannot

`C-008` demanded this register; the first draft never wrote it and the second named **no test**. Stated as
a table so nothing is closed by narration. **Charter `C-011` (ATDD-first) requires the red on the work
package's `planning_base_branch`; four classes below cannot have one, and each states the documented
exception plus what the reviewer verifies instead.** Where a red is only reachable on an intermediate
state, the register says whether that state may be **committed** (`FR-002` only) or must stay in the
**working tree** (`FR-003`, `FR-004` — committing routing-without-arm at rows 8/9/12 *is* the fail-open).

| Requirement | Class | Test id / path | Why it is RED before the change | What makes it GREEN |
|---|---|---|---|---|
| `FR-001` | Red-first achievable (base-branch red) | New per-row tests named `test_row<N>_malformed_meta_raises_mission_meta_read_error`, one per census row 4, 5, 6, 7, 8, 10, 11, in each site's own cone module; row 11 reuses the existing fixture pattern at `tests/status/test_aggregate_coord_deleted_contract.py:70-92` | At baseline the site lets a bare `ValueError`/`JSONDecodeError` escape, so `pytest.raises(MissionMetaReadError)` fails; the seam-proof half (`SC-001`b) also fails, since the site calls `load_meta`, not `load_meta_fail_closed` | Routing the site onto `load_meta_fail_closed` and deleting its `pending-batch-a` ledger row in the same commit |
| `FR-002` | **Intra-mission red-first, mandatory ordering — two commits inside ONE work package** (the single sanctioned exception to `C-002`; documented `C-011` exception) | The 4 degrade sites' new fallback tests plus `SC-002`'s 12-line probe | Commit 1 routes the site **without** touching the handler: `MissionMetaReadError` is a `RuntimeError`, so it escapes `except ValueError` and the fallback test fails — that escape is quoted as the red | Commit 2 extends the handler to `MissionMetaReadError`. Reviewer verifies red→green across the two commits inside the lane, not against `planning_base_branch` |
| `FR-003` | **Intra-mission red on an UNCOMMITTED intermediate tree** (documented `C-011` exception) | New `test_row<N>_malformed_meta_raises_domain_error` for `decisions/service.py:141` and `missions/_resolve_planning_branch.py:122` | With routing applied and the handler not yet extended, the site leaks `MissionMetaReadError` instead of `DecisionError` / `PlanningBranchResolutionFailed`; that state is captured and quoted in the working tree and **never committed** — committing it would breach `C-002`/`FR-014` | Handler extended to catch `MissionMetaReadError` by name in the **same commit** as the routing |
| `FR-004` | Same class as `FR-003` — uncommitted intermediate red, plus `SC-004`'s mutation probe | Existing: `tests/specify_cli/context/test_resolver.py:256` **only** — the `test_coord_loop_workspace.py` citation was docstring prose and is withdrawn. New absent-file message tests for `decisions/service.py:141` and `missions/_resolve_planning_branch.py:122` | Routing without the `None` arm: row 8 returns `{}` → `mission_id = feature_dir.name` → **fabricated identity**, `MissingIdentityError` never raised (BLOCKER-2's fail-open); rows 9/12 report the wrong cause. Captured in the working tree only | The `if result is None:` arm carrying the **missing-file message**, plus the handler, in one commit with the routing (`FR-014`, `SC-016`) |
| `FR-005` | Red-first achievable | New `test_bypass_site_names_meta_json_on_corruption`, one per bypass site (5 read expressions / 6 invocation sites) — `SC-012` | Today every bypass site degrades to a generic dirty-worktree message that never says `meta.json`, so the message assertion fails | A diagnosable message naming `meta.json` and the path (and, at `ref_advance.py:247`, routing) |
| `FR-006` — widening half | Red-first achievable | `tests/architectural/test_inline_meta_read_gate.py::test_new_inline_meta_read_is_flagged`, extended with the delegated-parse fixture (research control `C1`), plus `SC-005`'s positive twin | The unwidened scanner returns **0** for a delegated parse (measured: inlined → 1 flagged, delegated → 0), so the fixture's `sites: 1` assertion fails | The clause-2 hop into a private same-module single-parameter parse helper |
| `FR-006` — `read_bytes` half | **No red possible — synthetic pin required** (documented `C-011` exception) | New `test_read_source_base_direct_read_bytes` beside the existing `::test_read_source_base_direct_read_text` (`:789`) and `::test_read_source_base_direct_open_call` (`:800`), plus a `tmp_path` scan fixture | `read_bytes` adds **0** sites over `src/`, so no live census and no floor moves — there is nothing on the real tree to go red | The synthetic fixture pair goes **1 → 2** when `read_bytes` joins `_extract_read_base` (measured control: expected before=1 after=2, got 1→2) |
| `FR-007` | Not red-able; evidence is a filed issue plus a committed control with its positive twin | `SC-005`'s control + twin under `tests/architectural/` fixtures; `SC-009` row 3 | — (a deferral has no red) | `gh issue view <n>` quoted, control printing `sites: 0`, twin printing `sites: 1`, allowlist and baseline both unchanged at 7 |
| `FR-008` | **No red possible** (documented `C-011` exception) | `::test_inline_meta_read_floor` (`:1061`), `::test_allowlist_matches_floor` (`:1116`), `::test_routed_load_meta_floor` (`:1084`) | A floor is stale only *after* the change it accompanies; re-deriving it first would itself red the gate. The reviewer verifies instead that the three assertions are green **in the same commit** as the widening + routing, with both re-derived integers printed | The re-derived integers: inline stays **7** (routing returns live to 7); `ROUTED_LOAD_META_FLOOR` moves to restore the 3-below-live gap at live **130** |
| `FR-009` | **Inverted red — pre-existing, not caused by a new test.** Protocol below is mandatory | `tests/regression/test_issue_2804_merge_resets_gate_artifacts.py` (**both** assertions) + companion `test_widened_2804_assertion_rejects_wrong_verdict` (`SC-010`) | **Inverted-red protocol.** (1) Quote the failing selection **pre-change** on a pristine base: `upstream/main` `98198e980`, same selection, `git worktree add`, `rootdir: /tmp/repro-3162-main`, `1 failed in 96.97s`, `grep -c '^ERROR tests/'` → 0, `E assert 'pending' == 'pass'`. (2) Name **every** failing assertion: `:482`'s `overall_verdict == "pass"` **and** `assert SCAFFOLD_TODO_MARKER not in json.dumps(post_matrix)` — a one-assertion account is what made `SC-008` look reachable by widening the verdict alone. (3) Cite the tracked defect: #3138 for the red, plus `SC-009` row 2 for the product defect the red pointed at. (4) The companion falsifiability test must fail on **the defect's own fixture**, not on an unrelated disallowed value | Assertion 1 widened to the design's admissible verdicts; assertion 2 re-pinned to evidence survival with the take-theirs negative control; the companion test demonstrating that the re-pinned pair **fails** on the defect's own fixture (`SC-010`) |
| `FR-010`, `FR-011`, `FR-012`'s docstring, `FR-007`'s deferral | Not red-able; evidence is a quoted `gh issue view` / a quoted diff | `SC-009` rows 1, 2, 3; `SC-014` | — | Issue numbers recorded and viewed; `git show --stat` showing the docstring and the routing in one commit |
| `FR-013` | Red-first achievable (structural) | `SC-015` | Before removal the three greps return **3** matches, so the `0 matches` assertion fails | Removing the three unreachable `except FileNotFoundError` arms once their sites route |
| `FR-014` | Not red-able by a test; verified by commit shape plus a per-site mutation probe | `SC-016` | — (atomicity is a property of the commit, not of the tree) | Each site's routing + `None` arm + handler in one commit, with the arm-removal probe naming the failing message assertion |
| `NFR-001` | Rides on `FR-001`/`FR-003`/`FR-004`'s reds for the 9 refuse sites; **no red possible for the 4-degrade residue**, which is filed rather than fixed | `SC-001`, `SC-003`, `SC-004` per-site assertions; `SC-009` row 5 for the residue | At baseline 7 of the 9 refuse sites surface a raw `ValueError` with no indication of the cause, and rows 8/9/12's absent-file arms are the ones that could return an indistinguishable value | Routing + the `None` arms; residue filed with `Q4` as the candidate remedy |
| `NFR-002` | Regression guard with a mutation probe — the predicate count is already correct at baseline, so no base-red exists (documented `C-011` exception) | `SC-013`; `::test_routed_load_meta_floor` (`:1084`) | — | Pre/post predicate enumeration equal-or-shorter; mutation probe (add a second local predicate → red → revert) quoted; routed count `129 → 130` inside the re-derived two-sided band |
| `NFR-003` | **Regression guard, declared not red-first** — the requirement *is* that behaviour be identical pre/post, so a base-red cannot exist by construction (documented `C-011` exception; the reviewer verifies the pre-capture instead) | `SC-002`'s probe, 12 captured lines per run | — | `diff pre.txt post.txt` empty over **12** non-empty captured lines each side, with the positive control's `diff` quoted non-empty |
| `NFR-004` | Red-first achievable | `SC-005` (control + positive twin); `::test_new_inline_meta_read_is_flagged` (`:1136`) | At baseline the unwidened scanner does not flag the delegated-parse fixture, so the twin's `sites: 1` assertion fails | The widening, plus the twin that distinguishes "undetectable shape" from "broken scanner" |

## Open Decisions — for the operator, not the implementer

| ID | Question | Status / why it is not decided here |
|---|---|---|
| ~~**Q2**~~ | Route the bypass sites, or only make them diagnosable? | **SETTLED (R-1): diagnosable-only, EXCEPT the one gate-reachable site, which is ROUTED.** `ref_advance.py:247` is routed via `load_meta_fail_closed(meta_path.parent)` — exact there, because `:315` gates on `Path(path).name == _META_FILENAME`, so `meta_path.parent / "meta.json" == meta_path` by construction, same encoding. Without it the widening has **no charter-compliant green state**: diagnosability leaves the `json.loads` in `_parse_meta_object` untouched, live inline goes 7 → 8, and every escape reds something (see the R-1 row above). Full routing of the remaining 4 is deferred to a filed issue (`SC-009` row 8), on the **routed budget**, not on `C-004`'s refuted structural claim. |
| **Q4** | Should the 4 degrade sites **log** when they degrade? They are silent today, and D4 preserves behaviour — but a silent degrade is how this class stayed invisible. | **OPEN. Owner: the work package that owns the degrade sites' routing** (it is the only surface that can implement or measure it). Adding logging is a behaviour change D4 did not authorise, so it is not done here; the residue it would address is filed as `SC-009` row 5, and this question is that filing's candidate remedy. |
| ~~**Q7**~~ | Do rows 5 and 11 need fixtures nothing provides? | **SETTLED, then CORRECTED (WP02, 2026-08-06).** Row 5 is reachable, but **not** by the fixture originally prescribed: a corrupt `kitty-specs/<slug>-<mid8>/meta.json` driven through `get_or_start_run` raises from **row 10**, because `_workflow_runtime_template`'s own first statement calls `_resolve_runtime_feature_dir` → `read_primary_meta` → `_read_path_resolver.py:846`, shadowing its read at `:380`. The fixture that does reach `:380` is a **coord topology** — a valid primary declaring `coordination_branch` plus a materialized `.worktrees/<slug>-<mid8>-coord/` whose `meta.json` is corrupt. **Row 11's corrupt-file arm is structurally unreachable**, and the earlier settlement was wrong: it claimed writing corrupt JSON into `tests/status/test_aggregate_coord_deleted_contract.py:70-92`'s fixture "reaches `:862`". It does not — `:862`'s subject is `_canonicalize_handle`'s resolved dir, and canonicalization indexes via `load_meta(entry, on_malformed="none")` (`context/mission_resolver.py:176`), which skips corrupt metas, so the handle becomes unresolvable and the re-read never runs. Measured for bare `mid8`, full ULID and bare human slug — all three return `({}, False)` without reading the corrupt file. **(Corrected, review cycle 2:** this sentence originally included the **composed handle** and claimed "all four". That is false: the composed handle is the exact on-disk directory name, so `_compose_primary_feature_dir` joins it literally and the very first read hits the corrupt file, raising `MissionMetaReadError` from **row 10** — which is precisely what WP02's own row-10 test drives, and why its row-11 test correctly omits that handle form. The conclusion below is unaffected: row 11's corrupt-file arm remains structurally unreachable, because unreachability rests on the three *non-composed* forms being canonicalized through an index that skips corrupt metas.**) **Provenance:** a review lens asserted the fixture existed, the orchestrator recorded it as settled without constructing it, and WP02 refuted it by measurement. A cited fixture is not evidence that the fixture reaches the site. |
| ~~**Q10**~~ | If the widened #2804 assertion pins nothing meaningful, delete the marker? | **SETTLED: no — keep the marker.** `"fail"` is a concrete disallowed verdict reachable from a one-criterion fixture (`acceptance/matrix.py:259`), so the widened predicate is falsifiable, and assertion 2 is re-pinned to evidence survival rather than deleted. `SC-010` additionally requires the companion test to fail on the **defect's own fixture**, because `pending` — the defect's signature — must be *admitted* by the widened predicate. |
| **Q11** | Does `cli/commands/merge_driver.py:167 _load_json_object` belong to the bypass class for **full routing**? Its subject is a merge-driver temp blob rather than a mission's own `meta.json`; `C-004` records that a public entry over `_parse_meta_text` is writable for exactly this site. | **OPEN — and it is a QUESTION, not a deliverable.** It was previously listed as a *requirement* of a work package, which no unanswered question can be: an implementer cannot deliver an operator's scope call. For this mission it is enrolled in `FR-005`/`SC-012` (diagnosability, and it is why the bypass count is 6 invocation sites rather than 5); full routing awaits this answer and is otherwise covered by `SC-009` row 8. Note the site runs **as a subprocess** inside #2804's marker (`lanes/merge.py:84` registers `spec-kitty merge-driver-meta` for `kitty-specs/**/meta.json`), so any edit is invisible until `pip install -e .` — the documented stale-install false-red class. |

## Standing rules carried into every work package

Never pipe a suite whose exit status you intend to trust — redirect, quote the `N passed` line. Print the
input count alongside any pass. `-ra`, never `-rf`; count `^ERROR tests/`, not `^ERROR `. Control every
probe against a case whose answer you already know. A killed run is neither a pass nor a fail. Explicit-path
staging; `ruff check` only — this repo is not `ruff format`-clean. Cite foreign issues as
`owner/repo#NNNN` or backticked (`` `#3076` ``, `` `#3140` ``, `` `#1732` ``); this mission's **own**
issues (#3162, #3138, #2804) are written bare so they mint their matrix rows. **"The failing node belongs
to a known class tracked elsewhere" is not a pre-existing classification — only a same-selection
reproduction on a pristine base is one.**

**Declare the convention with every count.** Bypass reads are **5 read expressions / 6 invocation sites**;
`meta.json` reads are **13 sites** under the call-site convention (which is why rows 10/11 count
`read_primary_meta` twice). Both conventions are defensible; mixing them silently inside one document is
not.

**Qualify every foreign requirement ID (`DIR-032`).** This spec's IDs are bare; any ID belonging to another
mission or to a source comment is written `<mission-or-issue>#ID`. Four IDs collide today and each must be
qualified at every use:

| ID | This spec's meaning | The foreign meaning, qualified |
|---|---|---|
| `FR-008` | Re-derive both floors in the same change | `` `#3076` ``#FR-008 — the row-union authority model (`merge_driver.py:18,295,507,564`), "never silently discard" |
| `FR-004` | Handle the 3 `allow_missing=False` sites | `` `#3076` ``#FR-004 — `merge_driver.py:163,212`'s `meta.json` field merge |
| `FR-007` | Do NOT allowlist the unreachable sites | `` `#3140` ``#FR-007 — `load_meta_fail_closed` as "the ONE public reader" (`core/paths.py:638-643`) |
| `C-002` | `MissionMetaReadError` is a `RuntimeError` | `` `#1732` ``#C-002 — the `-X theirs` mission-authoritative note (`merge_driver.py:75,220`) |
| `NFR-003` | Behaviour preserved at the degrade sites | the inline-gate allowlist's shrink-only rule, cited in `tests/architectural/test_inline_meta_read_gate.py:1125`'s docstring |

The false-positive precedent cited in the Edge Cases and in `C-005` carried a **phantom requirement ID**
in earlier drafts — an `FR-`-prefixed handle existing in no artifact of this mission, with no owning mission
named, which is unresolvable for an implementer. Both citations now describe the precedent without an ID.
The retired handle is recorded in `analysis-report.md` rather than here, deliberately: the
requirement-mapping gate scans **this file** with a bare `\b(?:FR|NFR|C)-\d+\b` token match
(`src/specify_cli/requirement_mapping.py:16`), so naming a phantom ID in prose registers it as a *declared*
requirement and fails `finalize-tasks` with `Unmapped functional requirements`. Filed upstream. Do not
reintroduce the literal token in this file. `` `#3113` `` ("the rejected predicate") is plan-only provenance, absent from this spec and
from `research.md`; keep it backticked so it does not mint an unresolvable issue-matrix row.
