# Adversarial Scope-Boundary Review — Naming/Identity Routing Rider (01KV7SFD)

**Reviewer:** Architect Alphonso (adversarial, scope-BOUNDARY lens)
**Date:** 2026-06-16
**Method:** Attack the three architectural bets + the out-of-scope severability claim, verified against
live code (`rg`/file reads), not against the plan's prose.

> Directive lens applied: 001 (architectural integrity / component boundaries), 003 (decisions documented
> with options + rationale), 031 (bounded-context boundaries; cross-context interactions explicit), 032
> (confirm domain terminology against the actual surface before acting).

---

## Bet 1 — C-002 "carry-with-adoption" for #1993 (extract `resolve_lanes_dir` + adopt ~10 read sites in one WP)

### Verdict: **WRONG** (the bet rests on a false call-site inventory)

The bet is internally coherent *given its premise*, but the premise is factually wrong. The premise is:
"the lanes file path is composed inline as `feature_dir / "lanes.json"` … across ~10 read sites"
(research.md Decision 4), so a bare extraction would leave a `_lanes_feature_dir` twin (the half-strangle
C-002 forbids), therefore adoption must ship in the same WP.

**What the code actually shows.** The lanes-file *path composition is already encapsulated* behind the
existing `persistence.py` seam (`read_lanes_json` / `require_lanes_json` / `write_lanes_json`), all of which
do the `feature_dir / LANES_FILENAME` join internally. Inventory of the 8 files research.md names for
"inline join adoption":

| File (research.md IC-03 target) | Inline `feature_dir / "lanes.json"` joins | Reality |
|---|---|---|
| `lanes/persistence.py` | 2 | **The seam's own canonical body** — must NOT be "routed"; it IS the SSOT. |
| `workspace/context.py` | 1 | An **error-message f-string** (`…not assigned to any lane in {feature_dir / 'lanes.json'}`). Already reads via `require_lanes_json`. |
| `context/resolver.py` | 1 | An **error-message f-string**. Already reads via `require_lanes_json`. |
| `lanes/worktree_allocator.py` | 0 | Already consumes the seam (or no join). |
| `lanes/compute.py` | 0 | — |
| `lanes/recovery.py` | 0 | Already calls `read_lanes_json` (3×). |
| `lanes/merge.py` | 0 | Already calls `read_lanes_json` (3×). |
| `core/worktree_topology.py` | 0 | Already calls `read_lanes_json`; the one `lanes.json` literal is an error string. |

Repo-wide: `rg 'feature_dir / "lanes.json"'` outside `persistence.py` returns **exactly two hits, both
inside error-message f-strings** (`workspace/context.py:798`, `context/resolver.py:203`). There is **no
fleet of ~10 inline read joins** to strangle.

**Architectural consequence (the real finding).** The *path-resolution authority already exists* — it lives
inside `read/require/write_lanes_json`. Introducing a separate `resolve_lanes_dir(feature_dir)` seam in
`lanes/persistence.py` **creates a second path-authority for the same concept** (path-to-lanes-file),
which is precisely the C-001 "no new authority / no parallel helper" prohibition this mission is built to
honor. The only honest adoption surface for a standalone `resolve_lanes_dir` is the two error strings — and
routing *those* through a resolver buys nothing (an error message interpolating a path is not a shadow read
path; it cannot drift behaviorally because it is never read).

**Strongest case AGAINST the plan's choice (and what I actually recommend):**
1. The carry-vs-defer framing is a false dilemma. The third option — **#1888-style verify-and-close** — is
   the correct disposition for #1993: the lanes-file path is *already consolidated* behind `persistence.py`;
   confirm that, add a regression test that the two error strings (or, better, a single
   `lanes_json_path(feature_dir)` thin accessor *exported from the existing seam*) are the only composers,
   and close the ticket. No new module-level authority.
2. If a named accessor is still wanted for readability, it must be **a thin function in `persistence.py`
   next to `LANES_FILENAME` that the existing `read/require/write` functions also call** — i.e. fold the
   internal join into one named helper *that the seam itself consumes*, so there is provably one composer.
   That is a ~3-line internal refactor, not a "~10-site adoption WP."
3. `lanes/persistence.py` is the right *home* (no import cycle — it already owns `LANES_FILENAME` and the
   I/O). The home is fine; the **scope and the "new seam" framing are wrong**. A bare extraction is not
   "safer" — there is nothing to extract; the encapsulation already happened in 3.2.0.

**Net:** This is the one bet where the boundary is mis-drawn on a counterfactual. IC-03 as written would
add redundant authority and ~8 no-op edits while claiming to strangle a duplication that does not exist.

---

## Bet 2 — Ratchet-as-tripwire honesty (IC-01)

### Verdict: **RISKY** (honest about *form*, but materially understates the *new* detector work, and the
"syntax-level" self-description is now false — the ratchet is already AST-based)

Two distinct issues, and the plan conflates them.

**(a) The honesty framing is sound but the limit is wider than admitted.** Documenting the ratchet as a
"tripwire, not a completeness oracle" (defeated by `mid[:8]` / helper indirection) is the right
intellectual posture and matches doctrine (don't claim the ratchet proves consolidation). No objection to
*calling* it a tripwire.

**(b) The plan misdescribes the existing ratchet and undersizes FR-004.** The current
`test_no_worktree_name_guess.py` is **already a full `ast`-walk detector** (`_scan_file` walks the AST;
`_collect_mid8_suffix_names`, `_is_bare_mid8_dir_compose`, `_references_mid8`). Critically, **every existing
idiom keys on the `mid8` *token*** (idiom 1 = `.worktrees` join, idiom 2 = `kitty/mission-` f-string,
idiom 3 = `endswith(f"-{mid8}")` / `f"{slug}-{mid8}"`). It does **not** currently detect a bare
`mission_id[:8]` / `…_id[:8]` / `[0:8]` slice subscript at all — that is why ~10 sites escape. So FR-004
("detect bare `…_id[:8]` repo-wide") is **a genuinely new AST detector** (a `Subscript` with a `Slice`
`upper=8` whose value is a `*_id`-named expression), not a one-line pattern tweak.

This has two scope hazards the plan glosses:
- The plan repeatedly calls the ratchet "syntax-level" (spec C-007-adjacent, plan IC-01, research Decision 5)
  while the implementation is AST-based and would have to *stay* AST-based to do the `_id[:8]` slice match
  without false-positiving on string slices. Calling it "syntax-level" invites an implementer to bolt on a
  regex, which **will** false-positive on `invocation_id[:8]` (executor.py:469, a different identity domain)
  and on any `something_id[:8]` that is not a mission id. The plan flags the `invocation_id[:8]` non-target
  but offers "pattern specificity or a justified allow-list entry" — for an AST slice detector you cannot
  distinguish `mission_id` from `invocation_id` structurally; **you are forced into a name allow-list**,
  which is exactly the brittle, defeatable surface the "tripwire" disclaimer is covering for.
- Because the detector keys on the *variable name* (`mission_id`), it is trivially defeated by
  `mi = mission_id; mi[:8]`. That is fine *for a tripwire* — but it means **verification-by-deletion
  (Scenario 3 / C-004) is doing the real correctness work**, and the ratchet is decorative for new
  regressions introduced via a renamed local. The plan should say so plainly and not lean on the ratchet
  as the FR-004 guarantee.

**Should a stronger (semantic) check be in THIS mission?** No — and here I *defend* the boundary. A
semantic "is this value a mission_id-derived short-id" check requires type/dataflow analysis the repo has no
harness for; building it would be new authority (a static-analysis engine) and violates the low-risk-opener
charter. The correct move is: keep the AST tripwire, **state the name-rebind limit in the test docstring**
(the plan already gestures at this), and rely on verification-by-deletion for the genuine guarantee. The
risk is not "too weak a check"; the risk is **the plan presenting FR-004 as a near-free extension** when it
is a new AST detector forced onto a name allow-list — size it as real work with focused tests, or it will be
under-built.

---

## Bet 3 — Ownership claim "no WP edits `branch_naming.py`" / "at most one owner"

### Verdict: **RISKY** (the `branch_naming.py` claim is plausibly true, but a *different* genuine
ownership collision exists on `lanes/recovery.py`, and the seam already has the parse helper IC-04 would reach for)

**`branch_naming.py` claim — mostly holds.** The two live static composes are:
- `lanes/recovery.py:135` — `pattern = f"kitty/mission-{mission_slug}*"`, a `git branch --list` **glob**.
  This is a *search* pattern, not a name *composition*; the seam's job is to produce canonical names, not
  glob patterns. Routing it through a new `branch_naming` glob helper is optional; it is already an
  allow-listed benign site in the ratchet ("a `git branch --list` GLOB pattern, not a compose"). **No
  `branch_naming.py` edit is forced here.**
- `core/vcs/detection.py:161` — already calls `parse_mission_slug_from_branch(f"kitty/mission-{worktree_name}")`,
  i.e. it **already routes through the seam's existing parser** (`branch_naming.py:771`). The only smell is
  the inline `f"kitty/mission-{...}"` compose feeding the parser; if anything that should consume a
  `compose`/`parse` round-trip helper — but the parser exists, so at most this is a tiny consume, not a new
  helper. **No new `branch_naming.py` helper is forced.**

  So the "at most one owner of `branch_naming.py`" claim is **likely true in practice** — but it is true
  *because IC-04 probably needs no helper at all*, not because the plan's sequencing guarantees it. The plan
  hedges with "IC-04 may edit it … only if a glob helper is genuinely required." Given the above, that
  conditional almost certainly resolves to "no edit." Good — but the plan should **decide this at tasks
  time, not leave it as a runtime maybe**, because a maybe-owner is not an owner-map.

**The real collision the plan missed — `lanes/recovery.py` is double-claimed.**
- IC-03 lists `lanes/recovery.py` in its lanes-dir adoption surface (data-model.md + plan IC-03).
- IC-04 owns `lanes/recovery.py:135` (the glob compose).

The plan's ownership section only defends `branch_naming.py` and never notices that **`recovery.py` is
named by both IC-03 and IC-04.** In reality IC-03 has *nothing to do* in `recovery.py` (it already uses
`read_lanes_json`; 0 inline joins — see Bet 1), so the collision is *latent, not active* — but that is luck,
not design. If a WP slicer takes the plan literally and assigns `recovery.py` to IC-03 for "adoption," two
WPs now co-edit one file and you get the exact linearization conflict the ownership map was supposed to
prevent. **Mitigation:** drop `recovery.py` (and the other 5 zero-join files) from IC-03's surface entirely
(it has no work there), leaving IC-04 the sole `recovery.py` owner.

---

## Bet 4 — Out-of-scope severability (does routing surface the deferred builder split-brain?)

### Verdict: **SOUND** (the fence holds; the rider cannot surface the `branch_name ≠ branch_ref.target_branch` bug)

This is the sharpest of the four bets and it survives attack.

The worry: adopting `IdentityFragment` / routing a read path could expose the builder's internal split-brain
where the flat `ExecutionContext.branch_name` (set at `resolution.py:797` from `wp_workspace.branch_name`)
diverges from `branch_ref.target_branch` (resolved once at `resolution.py:536`). These are genuinely two
different surfaces written by two different code paths — the latent inconsistency the deferred 3.2.x
builder-hardening (#1619) is meant to fix is real and present in the code.

**Why the rider does not touch it — verified.** I checked all ten route-sites
(`retrospective_terminus.py`, `status/aggregate.py`, `git/sparse_checkout.py`, `dashboard/scanner.py:438`,
`doctor.py:3070/3162`, `doctrine_synthesizer/apply.py:745/831`, `implement.py:386`,
`context/mission_resolver.py:163`). **None of them touch `ExecutionContext`, `IdentityFragment`,
`branch_ref`, or `branch_name`.** Every one of them derives `mid8` from a **raw `mission_id` string**
(`mission_id[:8]` from a meta dict or a scanned value). Routing them to `mid8(mission_id)` / `resolve_mid8`
changes *only the short-id derivation*, an operation on a 26-char string → 8-char string. It never reads,
constructs, or compares a branch name, and it never consumes the builder's `branch_name`/`branch_ref`
fields. Research.md Decision 1 is correct here: **0 genuine fragment-adopt sites** — FR-002 is a
verification, not a change.

Therefore the routing work is **orthogonal** to the `branch_name`/`branch_ref` invariant: the rider cannot
*newly* surface that bug because no routed site reads either field. The `dashboard/scanner.py:438` site —
the one runtime consumer — derives `mid8` from a scanned `mission_id` for display only; it does not assemble
a context. The fence around #1619/#1716/#1832 is real, not aspirational.

**One caveat to record (not a scope breach):** IC-03's standalone `resolve_lanes_dir` (Bet 1) is the *only*
piece that flirts with builder territory, because lanes-dir resolution is adjacent to
`workspace`/`coord_worktree` topology. But since (per Bet 1) IC-03 should collapse to verify-and-close on the
*already-encapsulated* `persistence.py` seam — which takes a `feature_dir` argument and never consults the
builder — even that adjacency does not breach the fence. Keep `resolve_lanes_dir` (if it survives at all)
**pure over its `feature_dir` argument**, exactly as data-model.md mandates, and the severance holds.

---

## Summary table

| Bet | Verdict | One-line reason |
|-----|---------|-----------------|
| 1 — C-002 carry-with-adoption (#1993) | **WRONG** | The "~10 inline lanes-path joins" do not exist; path is already encapsulated in `persistence.py`. A new `resolve_lanes_dir` is redundant authority (C-001 risk); correct disposition is verify-and-close. |
| 2 — Ratchet tripwire honesty (IC-01) | **RISKY** | Honesty framing fine, but FR-004 is a *new AST slice detector* forced onto a name allow-list (cannot distinguish `mission_id` from `invocation_id` structurally); plan undersizes it and mis-labels the ratchet "syntax-level." |
| 3 — `branch_naming.py` single-owner | **RISKY** | `branch_naming.py` claim holds (likely *no* helper needed), but `lanes/recovery.py` is double-claimed by IC-03 and IC-04 — latent collision, fixed by removing recovery.py from IC-03. |
| 4 — Out-of-scope severability | **SOUND** | All 10 route-sites operate on a raw `mission_id` string; none read `branch_name`/`branch_ref`/`IdentityFragment`, so the deferred builder split-brain cannot be surfaced. |

## Highest sequencing/ownership hazard

**The single highest hazard is Bet 1's false inventory feeding IC-03.** It is a *double* hazard: (a) it
risks **building new path-authority (`resolve_lanes_dir`) in violation of C-001**, the mission's own central
constraint, while (b) its phantom adoption surface lists `lanes/recovery.py` — the very file IC-04 owns for
the glob compose — manufacturing the **only real two-WP file collision** in the plan. Both evaporate with one
correction: **re-scope #1993 to verify-and-close** (the lanes-file path is already consolidated behind
`read/require/write_lanes_json`; at most fold the internal join into one named accessor *inside the existing
seam*, add a regression test, close the ticket) and **strip the 6 zero-join files (incl. recovery.py) from
IC-03's surface.** Recommended sequencing unchanged otherwise: IC-01 (tripwire, sized as real AST work)
first, then IC-02 routing, then IC-04 verify-and-close — with #1993 demoted into the IC-04 verify-and-close
bucket alongside #1888/#1971-tail.

## Final verdict

**Boundaries: NEEDS-ADJUSTMENT.** Bet 4 (severability) is sound and Bet 3's headline claim survives, but
Bet 1 is built on a counterfactual that would both breach C-001 and create the plan's only genuine file
collision, and Bet 2 undersizes the one piece of net-new detector code. Adjust IC-03 to verify-and-close and
re-size FR-004 before `/spec-kitty.tasks`.
