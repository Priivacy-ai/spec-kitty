# Phase 1 Data Model — R1a

Five entities. All are frozen and hashable; all counts are content, never thresholds (C-002), and every
comparison in the Mission is a **set** comparison (C-011).

---

## `Member` — a discovered class member

| Field | Type | Notes |
|---|---|---|
| `key` | **`MemberKey`** | **`MemberKey = tuple[str, str, str]` — `(rel_path, enclosing_qualname, normalized_token_line)`**, formed **at the WRITE SITE**, at the boundary, from this record. **Composition is explicit because the types differ**: `MemberKey = (relpath_posix, *composite_key_from_file(path, lineno))`, since the primitive returns `tuple[str, str]` — comparing the two directly is a **`mypy --strict` type error**, not merely a wrong assertion. **`enclosing_qualname` is the INNERMOST dotted qualname** (`anchoring.py:173,211`), which is what the C-011 anchor matches (symdiff **0**; keying at the keyed def gives **2**, both at `:1165`). The bare 2-tuple yields **19** distinct values over the 40 and is refused. Content-addressed; survives blank-line and comment drift. |
| `lineno` | `int` | The write site's line. **Explicitly NON-AUTHORITATIVE**, per `_sole_door_scan.py:87-89` — carried because `normalized_token_line` takes only **4** distinct values across the 40 members, so without it a maintainer cannot reach the site. Never part of `key`. |
| `home_partition` | `Literal["A","B1","B2","other"]` | The **EFFECT** axis (A1). Derived from `HOME` writes in the member's own scope chain: **A** = does not re-pin `HOME`; **B1** = re-pins to `tmp_path/"home"`; **B2** = to `tmp_path/"user-home"`; **other** = anything else. Rule imported and cited at `research/m4_ablation_evidence/` (`VERDICT.md:38-41`). Measured over the 40: **A=27, B1=11, B2=2** (0 `other`), cross-checked **28/28 agreeing, 0 disagreements** against M4's independent labels. The 17/9/2-of-28 figure is **superseded-frame** and is not R1a's. |
| `relpath` | `str` | POSIX, relative to the walk root — so a synthetic tree and the real tree produce comparable keys (FR-009). |
| `kind` | `Literal["fixture", "test-body", "helper"]` | Taken **at the KEYED def**, never the innermost (C-004). Today **30 / 10 / 0**; at the innermost it is **30 / 9 / 1**, the withdrawn split. **That difference is how C-004 is mechanised** — the key cannot carry it, because the key must be innermost for identity (above). The keyed def determines membership, `kind` and the rename signature's parameter set, and is **not in the key**. |
| `params` | `frozenset[str]` | The **union** over the enclosing `def` chain, leading `self`/`cls` stripped. The silhouette limb is a superset test — never arity-exact, never order-sensitive (A20(a)). |
| `resolved_value` | `str \| None` | `None` is unresolvable and **never matches anything**. |

**Invariants.** A `Member` exists only where `params ⊇ {tmp_path, monkeypatch}` (with FR-010's owner
parameter counting as `tmp_path`) and `resolved_value == tmp_path/"home"`. Keying is at the **outermost**
def in the chain satisfying the silhouette. Two write sites inside one definition are two `Member`s with
distinct `composite_key`s — which is precisely why `(file, qualified_name)` was refused (C-012).

**Identity**: `key`, the `MemberKey` 3-tuple. Every set operation in the Mission is over this field, so the
ratchet is only as sound as the key — with the bare 2-tuple, deleting any of the **29** members sitting in a
collision class leaves the key set unchanged and the guard greens on a removal.

**`kind` is a SHAPE key and is retained only for the rename signature; `home_partition` is the EFFECT key.**
Recorded because a census keyed on shape would contradict §0.1a's shape-to-effect correction, which is the
entire argument for this Mission's predicate.

**`discover()` asserts exactly-one at import over its own output, at MEMBER level** — if two **members**
produce the same `MemberKey`, red at import. The 3-tuple is **also** non-injective over the 191 **sites** the
guard walks (190 distinct, one class of two at
`tests/paths/test_runtime_root_spec_kitty_home.py:91,93`, whose values are `tmp_path/"one"` and
`tmp_path/"two"` — **neither is a member, so the member-level population is 0**), so a future collision reds at import instead of
silently deduplicating.

## `Exempt` — an entry of `E`

| Field | Type | Notes |
|---|---|---|
| `key` | `MemberKey` | Same key space as `Member`. |
| `why` | `str` | Prose. Entitles nothing that the type does not already grant. |

`E: tuple[Exempt, Exempt]` — **fixed arity by type**, so a third entry is a `mypy --strict` error and not a
one-line literal (FR-004, SC-005). Exactly two entries, both named in the spec: the canonical owner
(FR-005) and the single retained-pin probe (FR-011).

**`E` fails the reviewer test, and that is the point.** An entry in `E` entitles its definition to exist
forever with no `owed_to`, no `frozen_at_sha` and no tombstone — strictly more than a census row. No honest
answer of "nothing" is available, because the owner must exist forever. What closes `E` is mechanism, not
prose: fixed arity by type **plus** a hash of its sorted entry set held outside the declaring module. Any
delta to `E` or its hash reds **unconditionally** — `E` never legitimately changes, in R1a or in R1b.

## `CensusRow` — one row of the frozen census

| Field | Type | Notes |
|---|---|---|
| `key` | `MemberKey` | Sort key. |
| `lineno` | `int` | Non-authoritative; the route back to the site. |
| `kind` | `Literal["fixture","test-body","helper"]` | Shape; rename signature only. |
| `home_partition` | `Literal["A","B1","B2","other"]` | Effect. Rule at `research/m4_ablation_evidence/VERDICT.md:38-41`; 40-member distribution A=27 / B1=11 / B2=2. |

**`frozen_at_sha` and `owed_to` are FILE-HEADER SCALARS, not row columns** (A1): 40 rows times two columns
held exactly two distinct values, which is §0.4's argument against a `reason` column one level over.
`owed_to` is `^#[0-9]+$` — `#3121` (OD-001) — and FR-004's per-row `frozen_at_sha` equality limb is struck,
because with one scalar there is no per-row divergence to catch. **The load it carried is inherited by
FR-004(b)'s shrink-only key-set hash**, which is what detects an added row; (a) was a **redundant** defence,
not a vacuous one, so **removing (b) is barred while (a) is struck.**

**There is no `reason` column, and its absence is load-bearing.** Rationale that would otherwise be a
per-row reason goes in the **file header**, following `tests/architectural/census/verdict_seam_IC01.yaml`.

**Direction**: monotonically non-increasing. A row may be **removed** with a tombstone when R1b adjudicates
its definition; a row may **not** be added. `census == ∅` is R1b's definition of done — reachable only
because the owner is outside the census.

**Cardinality at freeze: 40.** Published as a key set, never asserted as the number (C-002, C-011).

## `Baseline` — the direction mechanism

Lives at `tests/architectural/spec_kitty_home_pin_baseline.yaml`, **a different file from the census**, so
the pin is not editable in the same hunk as its subject.

| Field | Type | Notes |
|---|---|---|
| `census_key_set_sha256` | `str` | `sha256` over the **sorted, newline-joined `MemberKey` triples** — **not** over the file bytes. See plan §5. |
| `exempt_set_sha256` | `str` | Same construction over `E`'s sorted entry set. |
| `tombstones` | `list[Tombstone]` | Every census delta must be accounted for by one. |

`Tombstone`: `key` (`MemberKey`), `removed_at_sha`, `adjudication` (`deleted` \| `adopted` \| `manifest_row`).
The three values are R1b's only legitimate removal causes; a manifest row must carry a **distinct measured
cause**, or bulk-migrating 40 rows under boilerplate empties the census while burning down nothing.

**Co-edit rules differ by artefact, deliberately.** `E`: any delta reds unconditionally. Census: the guard
**recomputes** `census_key_set_sha256` from the census and compares, and every delta needs a tombstone — so
a co-edit that removes a row *and* re-pins the hash still reds unless a tombstone explains it, while a
legitimate adjudication passes. A blanket "touching both reds" is refused: it would forbid R1b's job.
Git-state inspection is not used — it does not survive rebase or squash; content comparison does.

## `Verdict` — WP-0's gate output

| Field | Type | Notes |
|---|---|---|
| `verdict` | `Literal["proceed", "proceed-degraded", "halt"]` | Machine-readable. A **collected test** reds until this reads `proceed`/`proceed-degraded`, gating all four packages — not "WP-a's first task", which gates only whichever package is sequenced first (C4). |
| `start_sha` / `end_sha` | `str` | `709a595…` → `5d49d31ed…`. Non-tunable **in the sense that neither may be chosen to obtain a band**: the start SHA moves **only** under §0.9's pre-committed widening schedule, which reads `|R|` and ±1 stability and never `r`. The end SHA never moves. |
| `sites_at_start` / `sites_at_end` | `list[MemberKey]` | **The operands** — so the difference is recomputable by a reviewer without re-running anything (SC-000(i)). |
| `renames` | `list[RenamePair]` | Every excluded pair with its matching keys. |
| `refused_ambiguous` | `list[...]` | Candidates refused for not being a unique mutual best match. |
| `unpaired_departures` / `unpaired_arrivals` | `list[...]` | Published in full. |
| `R`, `R_f` | `list[...]`, `list[...]` | Sets, not counts. `r = \|R_f\| / \|R\|`. |
| `attempted_windows` | `list[Window]` | Every attempt, including discarded ones, with `(start_sha, \|R\|, \|R_f\|, band)`. |
| `invocation` | `str` | The exact command. |
| `stability` | `Stability` | ±1 in **both** axes over **consequence classes**, with the clamp. |
| `start_sha_crosscheck` | `StartShaCrosscheck` | **The start SHA's independent anchor** (§0.9). Sub-fields: `instrument` (the checked-in C-011 classifier used), `start_sha`, `symmetric_difference` (against `discover()`'s site set at that SHA), `explanation`. Without it the end SHA is externally anchored by C-011 and the start SHA is not, and the symmetric circularity is *tune until `r >= 50%`*. |

### Banding — state transitions

```
|R| < 10                          -> VOID (a precondition, NOT a band; evaluated BEFORE banding)
any admissible ±1 changes the
  CONSEQUENCE class               -> INADMISSIBLE
r == 100%                         -> proceed          ─┐ one consequence class:
50% <= r < 100%                   -> proceed-degraded  ─┘ {proceed, proceed-degraded}
r < 50%                           -> HALT (operator sign-off required; the implementer may not proceed)
```

**Clamp**: `|R_f| − 1` skipped at `|R_f| = 0`; `|R_f| + 1` at `|R_f| = |R|`; `|R| − 1` at `|R| = |R_f|`;
and `|R| − 1` also skipped when it would fall below the floor, **because VOID is not a band**. Stability
evaluated over *labels* rather than consequences makes `proceed` unreachable in every state — 0 of **806**
enumerated states (`|R| in [10,40]`, `|R_f| in [0,|R|]`; re-verified this pass: **380 go / 364 halt / 62 inadmissible** over consequences). *(The first pass wrote 682, which is 318+364 — the admissible subset of the LABEL enumeration, not the state total: §0.1's own wrong-denominator error in miniature.)* — which would turn the halting instrument into a guaranteed no-verdict.

**Rename detection**: a departure and an arrival in the same file matching on
`(resolved_value, params_at_keyed_def, kind)`, required to be a **unique mutual best match** or the pairing
is refused and both sites retained. `None` values never match. Excluding a fixture rename biases toward
halt; excluding a non-fixture rename biases toward proceed — the effects are opposite-signed, so the
**rename mix must be published**.

**Widening**: walk the start SHA backwards along `upstream/main`'s first-parent history **one first-parent
commit at a time** (`main` is rebase-merged — there are no merge commits to step over), stopping at the first
SHA where **both** `|R| >= 10` and ±1 consequence-class stability hold. **No attempt cap.** The stopping rule
reads `|R|` and stability **only, never `r`** — that independence is what keeps an unbounded walk
forking-path-free. Measured at the stated window: **`|R| = 3`, VOID**; the floor is first met between ~300
and ~600 first-parent commits back. If the window moves, the record must state whether §0.3's 28 → 30 figure is re-derived at
the moved SHA or explicitly superseded.
