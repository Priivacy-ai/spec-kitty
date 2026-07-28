---
affected_files: []
cycle_number: 2
mission_slug: read-side-seam-primary-primitive-closure-01KYKMMT
reproduction_command:
reviewed_at: '2026-07-28T11:37:43Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP02
---

---
affected_files:
- path: docs/development/read-side-seam-classification.md
- path: tests/architectural/test_no_read_side_bypass.py
cycle_number: 1
mission_slug: read-side-seam-primary-primitive-closure-01KYKMMT
reproduction_command: PWHEADLESS=1 uv run pytest tests/architectural/test_no_read_side_bypass.py -q
reviewed_at: '2026-07-28T12:10:00Z'
reviewer_agent: reviewer-renata
verdict: changes_requested
wp_id: WP02
---

**Verdict: CHANGES REQUESTED.** Most of this WP is strong and independently
verified — all six G1 grammar rules are genuinely *enforced* (I mutation-verified
each on a scratch copy, results below), the per-primitive reconciliation bites
for all four primitives on their own rows, the 32 in-flight reds are recorded and
**not** allow-listed away, and the corrected Known-gap text is right. Two
findings block, both of them the "reads as covered but isn't" shape this WP
exists to eliminate.

---

## Issue 1 (BLOCKING) — the per-site index cannot address several sites of the *same* primitive in one qualname (FR-009 / G2 / SC-015 unmet)

`contracts/ledger-grammar.md` G2 requires the index key to gain a discriminator
"(trailing `primitive` **+ site token**, or an equivalent composite) **so each
site is distinct**", and states the requirement against a named case: the
qualname carrying **four** sites — one existing primitive plus **three** of the
newly censused one.

The implementation added the `primitive` column but **not** a site token. The
index key is `(rel_path, qualname, primitive)`, so the three
`primary_feature_dir_for_mission` sites inside
`status/aggregate.py::MissionStatus._find_meta_path` (`:499`, `:522`, `:543`)
collapse to **one** key. Verified by construction against your own parser:

```
G2 - can the index address 3 same-primitive sites inside ONE qualname?
  index REJECTS them: AssertionError("ledger section '## Stay-lenient allow-list
  index (machine-checked)' has a DUPLICATE key
  ('src/specify_cli/status/aggregate.py', 'MissionStatus._find_meta_path',
  'primary_feature_dir_for_mission')")
```

Two consequences, both concrete:

1. `docs/development/read-side-seam-classification.md:274-278` tells a later WP
   that if `:499`/`:522`/`:543` are `stay-lenient` it should "add their **rows**
   here". Under the shipped key shape that reds with `DUPLICATE key`, and the
   companion cardinality assertion at
   `test_no_read_side_bypass.py:1009` (`len(_ALLOW_LIST_SEED) == len(seed_index)`)
   reds too if the seed carries three descriptors against one ledger row. So the
   ledger's own forward instruction is unfulfillable.
2. `tasks.md` §6 is explicit that WP04–WP07 may edit **nothing** in this ledger
   or this gate — "a routing WP that finds a gap **reports it as a WP02 gap**".
   WP07 owns `status/aggregate.py`. The gap therefore has to close here, now,
   not downstream.

**Why this was not caught:** `test_index_discriminator_represents_a_four_site_qualname`
(`:1650`) is named and documented as proving "the trailing `primitive`
discriminator (G2) makes all four independently addressable and non-colliding",
but it asserts distinctness of `_Finding.as_allow_key()` —
`(rel_path, qualname, **token_line**)`. That key does not contain the `primitive`
discriminator at all; it would be four-way distinct with or without this WP's
change. The property the test *names* (index addressability) is false; the
property it *measures* is true by pre-existing construction. That is exactly the
vacuity mode C-009 and the four-element non-vacuity tactic are aimed at.

**Fix direction (your call on shape, not prescribed):** make the index key an
honest per-site composite — e.g. append a fourth `site token` column carrying the
descriptor's normalised `token_substring` (or its `occurrence` ordinal) so the key
becomes `(rel_path, qualname, primitive, site_token)` — and re-point
`test_index_discriminator_represents_a_four_site_qualname` at
`_ledger_stay_lenient_index`'s own key shape so it fails if the index grain ever
coarsens again. Note G1's trailing-append rule applies to the new column too, and
`expected_columns` must move with it.

---

## Issue 2 (BLOCKING) — the live-census Summary carries as-of-WP02 counts, not the prescribed post-migration end-state counts (T010.3)

T010 step 3 resolves the "live" ambiguity explicitly and gives the reason:

> "the parsed count columns carry the POST-MIGRATION END STATE. 'Live' is
> ambiguous between as-of-WP02 (≈30 unrouted primary sites) and end-state (0),
> and the two have opposite consequences. As-of-WP02 counts go green now and red
> the moment WP05 lands — with no owner able to fix them... So write end-state
> counts, record the resulting reconciliation red in your `## WP02` section of
> `research/expected-reds.md`, and name **WP08** as its greening owner."

`tasks.md:103` states the same thing as settled fact ("WP02 writes post-migration
end-state counts and names WP08 the greening owner").

What shipped is as-of-WP02: `| expected-red (unrouted) | 31 | 17 |` and
`| Total real call sites | 34 | 19 |` for `primary_feature_dir_for_mission`,
which reconciles **green** today — while the section heading nonetheless reads
"(machine-checked, **end-state**)". The predicted failure is real; I proved it by
substituting the gate's own live-census function and leaving your ledger
untouched:

```
reconciliation today: []
after WP04 routes its 4 sites:  ['primary_feature_dir_for_mission: ledger declares 34
  total real call sites but a fresh census finds 31', '... 19 total files but a fresh
  census finds 17']
after WP05 routes its 10 sites: ['... declares 34 ... finds 24', '... 19 ... finds 15']
after WP07 routes its 8 sites:  ['... declares 34 ... finds 26', '... 19 ... finds 15']
```

So `test_ledger_summary_counts_reconcile_with_the_allow_list_and_themselves` reds
for **every** routing WP from WP04 onward, on a node those WPs are forbidden to
touch, and that red is recorded nowhere as expected. WP08 — the only permitted
editor of the count rows — runs last.

**Fix direction:** either write end-state counts as instructed (primary:
`sanction-infra 3 / 2`, `expected-red (unrouted) 0 / 0`, total `3 / 2`;
`resolve_feature_dir_for_mission`: `migrate-fail-loud 0`, total `7 / 6`), report
the resulting reconciliation red for the `## WP02` section of
`research/expected-reds.md` naming WP08 as greening owner — **or**, if you judge
end-state counts wrong, say so explicitly with the reasoning and a named owner
for every intermediate red, rather than silently taking the other branch of an
ambiguity the prompt had already closed. Do not resolve it by re-labelling: the
heading currently claims end-state over as-of-now figures, which is the one
option that is wrong either way.

---

## What I verified and accepted (do not redo this work)

**Grammar rules — mutation-verified, not read (all six ENFORCED).** Independent
scratch-copy mutations against your parser, not your tests:

| G1 rule | Mutation | Result |
|---|---|---|
| 1 — exactly one table per parsed heading | second pipe-table appended under the index heading, and separately under the live-summary heading | RED, `SECOND pipe-table` (both) |
| 2 — headings verbatim | index / live-summary / foundation headings each renamed | RED, `has no '<heading>' section` (all three) |
| 3 — leading column positions | `rel_path` ⇄ `qualname` swapped in one index row | RED via membership set inequality |
| 4 — `primitive` appended, never inserted | leading column inserted in one row, and a consistent table-wide 4-column rewrite | RED, `expected exactly 3` (both) |
| 5 — no duplicate key | row duplicated in the index, the live-summary, and the foundation table | RED, `DUPLICATE key` (all three) |
| 6 — non-numeric counts are an error | sites → `many`, files → `-`, sites → `` (empty) | RED, `non-numeric` (all three) |

**Per-primitive reconciliation bites on its own merits (point 2).** I did not
trust the parameterised test's needle; I mutated each primitive's **own** total
row and stay-lenient row explicitly and confirmed the error text names that
primitive. All four bite independently, `primary_feature_dir_for_mission`
included (its stay-lenient row is an honest `0`, and bumping it to `3` reds).
The sanctioned-module per-primitive non-vacuity assertion also holds on its own
merits: `surface_resolver.py:739` and `resolution.py:426/755/801/995` are real
`primary_feature_dir_for_mission` call sites, so neither exclusion rides on a
previously-censused primitive's finding.

**Index keying (point 3).** No line number anywhere in the key —
`CompositeKey` is `(rel_path, qualname, normalised token_line)` from the shared
`specify_cli.contracts.anchoring.composite_key`; the ledger index is
`(rel_path, qualname, primitive)`. DIRECTIVE_041 respected. (The *grain* is the
problem — Issue 1 — not the anchoring.)

**Per-disposition counts (point 4).** Published, including the honest zero:
"migrate-fail-loud = 1, stay-lenient = 7, sanction-infra = 0". T012's vacuity
guard correctly discharged (one `migrate-fail-loud` site exists, so SC-005's
zero-case does not apply) and said so.

**Honest bounds and Known-gap (point 5).** All five bounds carry sizes
(wrong-`kind`: zero known instances; wrapper laundering: one wrapper, zero
additional censused sites; latent sibling `resolve_feature_dir_for_slug`: zero
call sites; sanctioned foundation + resolver-internal: 4 + 2 modules; no-kind
artifacts: `gap-analysis.md`). The Known-gap text names both the **gate**
(`test_resolution_authority_gates.py`) and the **axis** (anchoring), and states
the narrower true gap (call-site-bypass axis). #3014 is CLOSED with the
corrected finding.

**Ratchet not inverted (point 6).** The gate reds with exactly **32** offenders,
matching `research/expected-reds.md` § WP02 item-for-item. Nothing that should be
routed later was absorbed: the allow-list grew 16 → 23 only for newly-censused
sites that were previously policed by *nothing*, which is a net tightening, and
zero of the 31 unrouted `primary_feature_dir_for_mission` sites was
pre-populated.

**The 7 `stay-lenient` verdicts — I confirm all 7, with one caveat.** Each is a
per-site content descriptor with an individual rationale; no path-scoped blanket
(C-003 satisfied). Six quote the site's own production comment as the rationale
of record and I verified each comment exists and says what is claimed:
`decision.py::_resolve_repo_root_and_slug`, `mission_type.py::current_cmd`,
`mission_type.py::close_cmd`, `context/resolver.py::resolve_context` (the
strongest — it canonicalises a handle to a directory *name*, it is not an
artifact read at all), `lanes/recovery.py::reconcile_status` (a STATUS-write leg
that must stay coord-aware), and `agent_tasks_ports.py::RealCoordCommitRouter.feature_write_dir`.
The seventh, `widen/state.py::WidenPendingStore.__init__`, has **no** protective
comment and is honestly flagged "ambiguous — reviewer confirm": I accept lenient
for now — the store's "a missing file is an empty store, never raises" invariant
is real and a COORD-kind swap could break it — but the underlying question (which
partition `widen-pending.jsonl` actually lives on) is a genuine open decision, not
a closed one, and it is correctly recorded as such. 7-of-8 lenient is defensible
here because these are *existence probes and structured-error dependencies*, not
artifact reads; routing was not avoided.

**NFR-008 historical preservation.** The pre-migration 2-primitive record is
preserved under its own distinct heading, labelled "historical … audit record …
not reconciled by any gate", with 90/54 and the 60-file census intact. No
historical figure was rewritten. The two summary tables correctly carry
*different* headings so G1 rule 1 cannot be satisfied by two differently-scoped
tables sharing one heading — a good call.

**Ownership.** The diff is exactly the two owned files. `ruff` clean, `mypy`
clean (project mode, with `pytest` importable), `test_no_legacy_terminology.py`
4 passed. The frozen scan-scope prefix set was not touched; the shared
`scan_scope()` was reused, not forked, and the symmetry meta-test proves it.

---

## Non-blocking notes (fold in if convenient; none of these alone would reject)

1. **`test_per_primitive_summary_mutation_reds` locates its row by count value,
   not by primitive.** The needle is `f"| stay-lenient | {n} | "` with
   `replace(..., 1)`. Today each of the four counts (12 / 4 / 7 / 0) is unique so
   each needle matches exactly one row — I checked. But if two primitives ever
   share a stay-lenient count, the parameterised run mutates the *same* row twice
   and still passes, and the per-primitive claim silently becomes false. Keying
   the needle on the primitive name (or asserting the returned error mentions the
   parameterised primitive) makes it robust.
2. **Drifted definition-line reference at the top of the ledger.** Line 13-14
   still says `resolve_artifact_surface` at `:1634`; it is at
   `src/mission_runtime/resolution.py:1705`. `read_dir` at `:1404` is correct.
   T014 step 2 asked for the drifted definition-line reference to be updated and
   this one came through unchanged from the base revision.
3. **Two 6-line drifts in the gate's module docstring**: it cites
   `_read_path_resolver.py:1432` and `:1473` for the internal
   `candidate_feature_dir_for_mission` calls; they are at `:1438` and `:1479`.
4. **`verdict_files_total` is computed and then `del`-ed** at
   `test_no_read_side_bypass.py:1144-1169`. The comment explains why it is not
   asserted, which is the right instinct, but a comment alone would carry the
   same information without the dead computation.
5. **The `expected-red (unrouted)` bucket** is a fifth verdict name outside the
   three canonical dispositions. As a *counting* bucket in the summary that is
   defensible, but it is also the mechanism by which as-of-now counts reconcile
   (Issue 2); if end-state counts land, its rows all become `0 | 0` and its
   purpose should be restated as such.

## Reproduction

```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty/.worktrees/read-side-seam-primary-primitive-closure-01KYKMMT-lane-b
PWHEADLESS=1 uv run pytest tests/architectural/test_no_read_side_bypass.py -q
# 50 passed, 1 failed (the 32-offender expected red) -- correct as designed.
```

Issue 1 reproduces by adding three identical
`| src/specify_cli/status/aggregate.py | MissionStatus._find_meta_path | primary_feature_dir_for_mission |`
rows to a scratch copy of the ledger's stay-lenient index and calling
`_ledger_stay_lenient_index` on it. Issue 2 reproduces by substituting
`_live_primitive_site_counts` with any count below 34 for
`primary_feature_dir_for_mission` and calling `_reconciliation_errors` on the
unmodified ledger.
