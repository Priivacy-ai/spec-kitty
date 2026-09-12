---
affected_files:
- path: docs/adr/3.x/2026-08-07-1-a-mission-halting-instrument-is-worth-its-cost.md
cycle_number: 1
mission_slug: isolated-home-pin-guard-r1a-01KZNMA3
reproduction_command: /home/jeroennouws/dev/sk-missions/3157/.venv/bin/python -m pytest
  tests/architectural -q -p no:cacheprovider
reviewed_at: '2026-08-12T04:47:34+02:00'
reviewer_agent: reviewer-renata
verdict: approved
wp_id: WP06
---

# WP06 (WP-d) review — cycle 1 — **APPROVE**

Directives applied: **DIR-024** (locality of change — the blast-radius question),
**DIR-030** (test and typecheck quality gate), **DIR-032** (conceptual alignment — the
`census` / `class` / `E` vocabulary), **DIR-001** (boundaries — the record/spec/lane
ownership split), **DIR-041** (tests as scaffold, not friction — the population-0 and
positive-control claims). Project charter: Terminology Canon and Code Review Checklist,
loaded via `spec-kitty charter context --action review`.
Tactics applied: `code-review-incremental`, `language-driven-design` (the `40 in 36`
overload is a terminology finding first and a numeric one second),
`architectural-gate-non-vacuity` in spirit — **every population-0 or "all green" claim in
this package was re-derived with a positive control before it was believed**.

This review is deliberately construction-heavy. WP06's own closing claim is that **no gate
in this repository validates `record.md` at all**. I confirmed that: `record.md` lives under
`kitty-specs/`, which `test_no_legacy_terminology.py::_EXCLUDED_PATH_FRAGMENTS` excludes,
and no other collected test or docs script reads it. Review is the only check on it.

---

## 1. What I constructed rather than read

Every figure below was re-derived under the pinned interpreter
`/home/jeroennouws/dev/sk-missions/3157/.venv/bin/python` (pytest 9.0.3). No venv was
created; no `uv run` / `uv sync` was issued; no lane worktree was entered — lane content was
read with `git show` / `git archive` only. `spike/isolated-home-3121` was not touched.

### 1.1 The ADR import (T027)

| Claim | Constructed result |
|---|---|
| source `sha256` | `88f5b668678ca46551a7f3c5dac2295a813963de0e7d586d7ba610142a31298b`, 209 lines — **matches** |
| landed `sha256` | `73838631d7d737d11e1039b5ab3dde5091068f84989053a1a5776e072b14ac21`, 210 lines — **matches** |
| body-only `sha256` both sides | `727658bee495b760aadbfc61a7200540f6f04bacc2130f031285adcc39fec5ee` — **identical**, computed from the text after the second `---` on each side |
| `diff` against the spike blob | **`2a3` and nothing else** — exactly one added line |
| the added line | `description:` frontmatter key, **154 characters** — matches the reported length |

**The body is genuinely untouched.** The relaxation of T027's literal byte-identity is
sound on the operator's own reasoning: a `description` key adds no account of the halt and
alters no sentence of the imported one, so it cannot produce the divergent second record
byte-identity existed to prevent.

**The two forbidden-term occurrences are unedited.** Landed lines **102** and **112**
(`…and no ceremony.` / `…in the same ceremony the`) sit inside the body whose hash is
identical to the spike blob's — so they provably were not touched. They are legal:
`tests/architectural/test_no_legacy_terminology.py:42-51` exempts `docs/adr/`. Editing them
would have minted the second record. **Correctly left alone.**

### 1.2 The docs gates — all green, and one of them proven able to see

| Gate | Result (live tree, `PYTHONPATH=.`) |
|---|---|
| `freshen_adr_inventory.py --check --all` | `clean (missing_rows=0 inventory_stale=False)`, **exit 0** |
| `description_length_check.py --strict` | `checked 677 page(s); 0 violation(s)`, **exit 0** |
| `inventory_lockfile.py --strict` | `generated=701 committed=701 drift=False`, **exit 0** |
| `docs_index.py --strict` | `generated=701 committed=701 drift=False`, **exit 0** |
| `check_docs_freshness.py` | **exit 0**, `findings=3 errors=0 warnings=3` (all `LINK-HEALTH-FAILED`, offline probes) |
| `pytest tests/architectural/test_no_legacy_terminology.py` | **10 passed** |
| `pytest tests/docs/` | **1388 passed** |

*(The reported `5` link-health warnings came back as `3` for me — the count is
network-dependent, all warnings, `errors=0` either way. Not a discrepancy.)*

**Positive control on the gate that caught the self-reported defect.** In a scratch copy of
`docs/` I deleted the ADR's row from `docs/adr/3.x/README.md` and re-ran the freshener with
`--repo-root` pointed at the copy:

```
unmodified copy : clean (missing_rows=0 inventory_stale=False)   exit 0
row removed     : ADR-README-ROW-MISSING …-worth-its-cost.md
                  STALE (missing_rows=1 inventory_stale=False)    exit 1
live tree       : clean                                           exit 0
```

The instrument is injective on exactly the defect it is being credited with catching.

**Spot-checks requested.** `docs/development/3-2-page-inventory.yaml:893-898` carries the
one new entry (six lines, pure insertion). `docs/adr/3.x/README.md:136` carries the index
row with the correct date and title. `3-2-docs-retrieval-index.yaml:2631` carries the page
with the `abstract` taken from the new `description`.

### 1.3 The figures — the mission's own headline defect, hunted for

I re-derived the populations from `git archive` extractions of both SHAs and ran WP01's
`discover()` over them:

| Population | `5d49d31ed` (baseline) | `fe5d492ed` (freeze) |
|---|---|---|
| `.py` under `tests/` | **2737** | **2752** |
| files hitting `b"SPEC_KITTY_HOME"` | **100** | **111** |
| write sites | **191** | **194** |
| **class** members / files | **40 / 36** | **42 / 38** |
| **census** rows / files | — | **40 / 36** |

and the subtraction:

```
class(fe5d492ed) − census = {
  ('architectural/test_home_owner_never_wins.py', 'retained_pin_home', 'monkeypatch . setenv ( , str ( home ) )'),
  ('conftest.py', 'canonical_home', 'monkeypatch . setenv ( , str ( home ) )'),
}
census − class(fe5d492ed) = ∅
```

Those two tuples are **byte-equal to `RETAINED_PIN_PROBE_KEY` and `OWNER_KEY`** in
`tests/architectural/_home_pin_exempt.py`. So:

- **the comment does NOT repeat the headline defect.** It says the class is **42 in 38** at
  the freeze SHA and the **census** is 40 in 36, and names the difference as `E`'s two
  entries. The dispatch's earlier draft ("40 at the freeze SHA") would have published the
  `census` / `census ∪ E` conflation to a public issue; the posted body does not.
- **the real names are used.** `conftest.py::canonical_home` (owner fixture) and
  `test_home_owner_never_wins.py::retained_pin_home` (member probe) — **not two probes**.
  I confirmed `probe_home_pin` is the *non-member sibling* that costs no slot, and that
  `E`'s own `why` says exactly that; the record quotes it verbatim
  (`_home_pin_exempt.py`, slot 2). No invented labels anywhere in either artefact.

### 1.4 The comment — seven items, and the gate outputs against the artefact

The comment is **posted, irreversible, and byte-identical to the copy embedded in
`record.md`**: I extracted the fenced block from `record.md` and diffed it against
`gh api …/comments/5261252413`. **202 lines each, unified diff empty.**

All seven T028 items are discharged:

| # | Item | Where | Verified |
|---|---|---|---|
| 1 | three separately labelled reach figures + two-frame warning | §1 | 40/40, 36/36, 40/191 — **all three constructed above**; warning present |
| 2 | explicit retraction of 26.06% | §2 | present in those digits, with both the numerator and denominator errors named |
| 3 | census-is-not-a-manifest + reviewer test over *anything that makes a definition acceptable to the guard*, with `E` failing it | §3 | present, stated at the wider scope, `E` named as the failure |
| 4 | §0.3 provenance correction, authored-vs-committed, refusal to state a growth rate | §4 | present, with the refusal in a blockquote |
| 5 | R1a adjudicates nothing | §5 | present |
| 6 | unconditional `r`, `\|R\|`, `\|R_f\|`, both SHAs, every attempted window incl. the VOID at `709a59534` (`\|R\| = 3`), band verdict | §6 | **every scalar re-read from `research/home_pin_gate/verdict.yaml`** — see below |
| 7 | the window **MOVED**; `28 → 30` **SUPERSEDED**, in those words | §7 | present, both words literal |

Item 6 against the artefact (`git show …lane-e:research/home_pin_gate/verdict.yaml`):

```
verdict = proceed            |R| = 33   |R_f| = 33   r = 1.0
start_sha  = ba0db69ade41f0fd788adea360e03456caf0c3e4
end_sha    = 5d49d31ed6505627d98d8f95d8502c9bf6a2f5ac
attempted_windows = 314      bands = {VOID: 313, proceed: 1}
(R_size, R_f_size) multiset  = {(3,3): 313, (33,33): 1}      # no VOID outlier
index 0   = 709a59534a1b8aac7e55a1cf6f5d2106a32c31ea  (3,3)  VOID
index 313 = ba0db69ade41f0fd788adea360e03456caf0c3e4  (33,33) proceed
renames = 0   refused_ambiguous = 0   unpaired_arrivals = 33   unpaired_departures = 0
stability = stable; perturbations (32,33) and (33,34) → proceed-degraded → go
start_sha_crosscheck.symmetric_difference = 0
FLOOR = 10   (_home_pin_gate.py:121)
```

Every published number matches. `window_accepted` (`_home_pin_gate.py:609`) is
`size >= FLOOR and stability(len(measurement.caught), size).stable` — it reads `|R|` and the
stability boolean and **nothing else**, which is exactly the "stopping criterion never reads
`r`" claim, confirmed at the source rather than taken from the prior review.

### 1.5 Two record claims I re-proved because they are the strongest ones in the file

**Residual F — the `|R| ± 1` axis is decision-irrelevant.** Re-implemented `band`,
`consequence`, `admissible_perturbations` and `stability` from
`_home_pin_gate.py` (`THRESHOLD = 0.5`, `FLOOR = 10`) and swept
`|R| ∈ [10, 4000] × |R_f| ∈ [0, |R|]` — **8 005 946 states, 3991 window sizes**:

```
states differing when the |R|+1 limb is dropped   : 0
states differing when the whole |R| axis is dropped: 0
```

The record's "zero differing states across 3991 window sizes" is exact. This is a
spec-level inert limb, correctly attributed to the spec and not to WP02.

**Residual H — the driver half has no coverage.** `git grep` over `tests/` on lane-e for
`detect_renames`, `window_accepted`, `measure_window`, `widening_walk`,
`effect_class_sites`, `verdict_document`, `crosscheck_start_sha`, `extracted_tests`:
**each appears in `_home_pin_gate.py` and in no other file**. "Nothing in the tree would
notice if it stopped being right" is literally true.

### 1.6 Citations, not re-filings

`#3121`, `#3285`, `#2991`, `#3170`, `#3226`, `#2642` — **all six verified OPEN**, and their
live titles match the record's one-line descriptions. `gh issue list --state all` shows **no
issue created on 2026-08-12** by this author. C-013 held: nothing merged, no branch
integration, no PR un-drafted, no `gh issue create`. `git diff` over WP06's two commits
touches **6 files**, all documentation or mission artefacts, **zero Python**.

`ruff check .` reports 43 errors, **all** in
`kitty-specs/.../research/spec_kitty_home_pin_evidence/{clf,step3}.py`, last modified by
`69ec12a60` — pre-WP06 and not this package's. `ruff format` was not run.

---

## 2. The self-reported defect — verified, and the generalisation is constructed-true

The claim is that landing an ADR needs three index updates, that the first pass made two,
and that **all four gates it had run were green anyway**. I did not take this on trust.

In a scratch `docs/` copy with the ADR's README row deleted:

| Gate | With the row | Without the row |
|---|---|---|
| `description_length_check --strict` | 677 / 0 violations, exit 0 | **677 / 0 violations, exit 0** |
| `inventory_lockfile --strict` | 701/701, drift False, exit 0 | **701/701, drift False, exit 0** |
| `docs_index --strict` | 701/701, drift False, exit 0 | **701/701, drift False, exit 0** |
| `check_docs_freshness` | *(differential)* | **output byte-identical after path normalisation — 0 diff lines over ~2100 findings** |

Three gates are blind by construction; the fourth produces **exactly the same finding set**
with and without the row. So the generalisation the record draws —

> a green gate set is not evidence the task was done the supported way: green over a
> population that does not include the thing you changed

— is not rhetoric. It is a measured property of this gate set, and it is the mission's own
"124 passed" finding turned on the implementer. The cause is correctly identified as **not
using the canonical tool**: `freshen_adr_inventory.py`'s docstring says in as many words
that it exists *because agents repeatedly forget one of these*, and
`docs/adr/3.x/README.md` states the rule itself. `CLAUDE.md`'s "Use Canonical Sources, Never
Improvise" was binding here, not style advice. Detected by positive control
(`ADR-README-ROW-MISSING`, exit 1, `missing_rows=1`) and repaired with the tool, never by
hand. **Self-report accepted in full, and it improves the package rather than damaging it.**

## 3. The blast-radius call — right, and rightly flagged

The operator's ruling expanded the radius by **one** generated file
(`3-2-page-inventory.yaml`); the ADR invalidates **two**, because the added `description`
becomes the page's `abstract` in `3-2-docs-retrieval-index.yaml`. Leaving it stale made
`check_docs_freshness` **newly red** with `DOCS-INDEX-DRIFT`.

The three available moves were: land a knowingly-red gate; regenerate and flag; or stop and
ask. **Regenerate-and-flag was correct.**

- Landing a red would breach DIR-030 and hand the operator a red gate to discover at merge.
- The file is **generated, regenerated by canonical tooling, never hand-edited**; the diff is
  `20 +`, `0 -`, entirely the new ADR's own entry. Under DIR-024 this is not scope
  expansion — it is the mechanical closure of the sanctioned change. A ruling that permits
  adding a `description` necessarily permits the index that derives from it.
- It was **flagged in the commit body and in `record.md`**, not landed silently, which is
  the part that makes it a reviewable decision rather than a quiet one.

The third update (`docs/adr/3.x/README.md`) is likewise not a radius expansion — it is one
of the two things the canonical tool does in one command.

## 4. The three dispatch corrections — all three confirmed

1. **`check_docs_freshness.py` is NOT red on this branch.** Independently: **exit 0, 0
   errors**, warnings only. The record states this as Red D and **withdraws the prior
   claim** while keeping the framing that produced it (*a pytest-shaped baseline capture
   cannot see a gate-shaped red*). Retracting the fact and keeping the true generalisation
   is the right shape.
2. **`plan.md:52` is not an independent frame.** `:52` carries `2737 / 100 / 191 / 40-in-36`;
   `:53` reads *"All figures are settled and not re-measured by this plan (spec §0.8,
   independently reproduced)."* The record says exactly this at lines 31-35.
3. **"Four transferable findings" is not what the artefacts contain.** Residual **K** states
   that exactly one finding is self-labelled transferable and that the four-shape list is a
   **pre-existing taxonomy this mission extended to a fifth**. I checked the source:
   `WP01/review-cycle-4.md:20-37` is the one labelled transferable, and the record quotes
   its generalisation verbatim. **The record does not overstate it — it corrects it.**

## 5. `record.md` against its mandate

Sixteen mandated items (the prompt numbers **12** twice; carried as **12a**/**12b** rather
than one being dropped — the right call, and the record says why), three carry-forwards, and
twelve further residuals **A–L**. All present, all labelled, all findable by heading.

Judged against T030's actual requirement — *findable and actionable without reading the
spec* — the file passes. Spot-checks of the three items a mission is least likely to write
down:

- **item 4 (the leak)** is stated in the mandated terms, names `r = 100%` at
  `|R| = 9, 33, 34`, says the gate's power to halt **was spent**, and separates what
  survives (a rule whose stopping criterion never reads `r`) from what is lost (the
  analyst's blindness). It also **corrects its own attribution**: those `|R|` values came
  from the independent lens, not the walk — which I verified, the walk contains only
  `|R| ∈ {3, 33}`.
- **items 1-3 (the vacuous criteria)** name C-014 limb (iii) as vacuous *over adopters R1a
  does not have*, SC-011 as pure shape, and SC-012 limb 2 as vacuous-as-specified with the
  WP03 mutation that proved it (deleting probe (a)'s `setenv` left the naming test
  **passing**).
- **item 13 (procedural halt enforcement)** says plainly that the first lock is a human
  performing two discretionary transitions at the worst possible moment, that marking WP-0b
  `approved` out of habit opens the gate, and that the collected verdict test is
  defence-in-depth *behind* it, not the enforcement.

**Residual A is stated exactly as required** — a **population-0 assertion with no positive
control**, with the structural reason (`_EXCLUDED_PATH_FRAGMENTS` excludes both
`kitty-specs/` and `docs/adr/`, which is exactly and only where WP06's two owned files live)
and the constructed proof (the ADR sits in the tree carrying the forbidden term twice while
the guard reports 10 passed). I re-confirmed both halves. **Running that guard green proves
nothing whatever about either WP06 deliverable, and the record says so first.**

**TG-5 is recorded as unresolved and the operator's.** The DIR-013 / C-013 conflict — DIR-013
obliges an agent meeting pre-existing reds to open a GitHub issue; C-013 forbids this
implementer opening one — appears both in the TG table (row TG-5, *"Routed to the operator;
unresolved by design"*) and in item 14 (*"a live governance conflict between DIR-013 and
C-013 that R1a does not resolve"*). **Not silently resolved. Correct.**

---

## Findings

- **[LOW]** `#3121` comment §6 (posted) / `record.md:633` — §6 cites
  `research/home_pin_gate/verdict.yaml` as the source of the machine-readable verdict, but
  that path exists on **no branch a reader of #3121 can reach**: it is present only on lanes
  b–e, which C-013 keeps unmerged. `record.md:43-48` states this; the public comment does
  not. — *No in-package remedy: the comment is irreversible. Recommend the operator decide
  whether a follow-up comment adds the branch qualifier. Do not rewrite.*
- **[LOW]** `#3121` comment §6 — "EVERY attempted window — 314 of them" is discharged as an
  equivalence-class summary (`{VOID: 313, proceed: 1}`, all VOIDs `(3,3)`, accepted at index
  313 of a contiguous first-parent walk) rather than 314 enumerated rows. I verified the
  summary is **lossless** — there is no VOID outlier — so every window is recoverable from
  the stated rule. — *Recorded so the operator sees this judgement was made deliberately,
  not missed. I do not consider it an FR-008 failure.*
- **[LOW]** `#3121` comment §6 / `record.md:195-217` — the leaked-lens figures
  (`|R| = 9, 33, 34` at ≈300 / ≈600 / ≈2000 commits back) sit oddly beside the published
  walk (`|R| = 3` at 0-312 back, `33` at 313). Both artefacts explicitly attribute the leak
  to an **independent lens** and warn against reading those values into the walk, so no false
  claim is made — but the instrument disagreement is stated and never explained. — *Carry to
  R1b as an open question about the two instruments, not a defect in WP06.*
- **[LOW]** `kitty-specs/isolated-home-pin-guard-r1a-01KZNMA3/spec.md:9` — still reads that
  the ADR *"does NOT exist on `feat/isolated-home-pin-guard`"*. T027 step 5 required only
  that the **citation resolve**, and it does; `spec.md` is not WP06's owned file. But a
  record whose thesis is honesty about state does not note that its own spec is now stale on
  this sentence. — *Recommend R1b or the operator strike the clause; out of WP06's ownership,
  so not a rejection ground.*
- **[LOW]** `record.md:84` — *"100 of the 101 ADRs under `docs/adr/3.x/` already carry a
  `description`"*. Constructed: the directory holds **100 ADRs plus `README.md`**; the "101"
  counts the index page as an ADR. The arithmetic is consistent (99 ADRs + README carried
  one; the import was the sole holdout, and all 101 files carry one now) but the noun is
  loose in a file that is otherwise scrupulous about naming its populations. — *Cosmetic;
  fix opportunistically if the file is ever touched again.*
- **[INFO]** No `spec-kitty agent tasks mark-status T0xx --status done` events exist for
  T027-T030 — but none exist for T001-T026 either, across five approved WPs. This is
  mission-wide practice, not a WP06 deviation. — *No action against WP06.*
- **[INFO]** `#3345` (filed 2026-08-12) reports the ADR freshener writing to `README.md`
  when the era authority has moved to `index.md` after a "Common Docs structural move". On
  **this** branch `docs/adr/3.x/index.md` does not exist and `README.md` is the real index
  table, so WP06's row landed in the right file. — **Merge-time watch item:** if that
  structural move lands on the target branch before this one does, WP06's row will be in a
  redirect stub and the freshener check will disagree. Re-run
  `freshen_adr_inventory.py --check --all` at merge.

**No [HIGH] or [MED] findings. Nothing here is a rejection ground, and none of it is
repairable inside WP06.**

---

## What I could not check

Stated plainly, because this is the last gate before a PR that may be flipped to
ready-for-review.

1. **`record.md` has no automated validator, and I confirmed that.** It is excluded from the
   only repo-wide prose guard by path, and no collected test or docs script reads it. This
   review is the sole check on 877 lines. I verified every claim in it that is cheaply
   constructible; I did **not** independently re-derive the escape populations in item 6
   (`getfixturevalue` 0, env-key indirection 0 of 73 non-literal keys, delegation 0,
   unmodelled value forms 3 unresolved), residual **D**'s "28 of 40 M4 labels", or residual
   **G**'s attribution of 30 arrivals to `2bad3228…`. Each is attributed to a named prior
   artefact and each was accepted on that attribution.
2. **D-1's `147/147` → `6/6` correction and D-2's 15 false positives** live only on
   `spike/isolated-home-3121` and were not re-measured — the record says so itself for D-2.
3. **The comment's `37 → 40` across the stated window** is not in `verdict.yaml` (which
   carries `sites_at_start = 7`, `sites_at_end = 40` for the *selected* window — the `7 → 40`
   figure, which I did verify). The stated-window endpoint was not reconstructed.
4. **CI.** Everything above ran locally on the pinned interpreter. `tests/architectural/`
   full-suite behaviour under CI parallelism was not exercised; the record's Red A/Red B
   wall-clock analysis was accepted on the WP02 reviewer's deselect control, which is
   documented and is the strongest merge-base evidence in the mission.

**Re-examine at merge time:** (a) `freshen_adr_inventory.py --check --all` against the
integrated tree, because of `#3345`; (b) `check_docs_freshness.py`, because a docs-shaped
red is invisible to a pytest-shaped baseline — this mission's own Red D lesson; (c) that the
comment's `verdict.yaml` path becomes reachable once the lanes land, which resolves the first
finding above by itself.

---

## Verdict

**APPROVE.**

The ADR is an import, not an authorship, and I proved it at the byte level. The comment
carries all seven FR-008 items unconditionally, every published scalar reconciles against the
artefact, and it does **not** repeat the `census` / `census ∪ E` conflation the mission
exists to name. `record.md` states the leak, the two vacuous criteria and the procedural halt
enforcement in the terms the mandate demanded, carries all sixteen items plus three
carry-forwards plus twelve residuals, files DIR-013 vs C-013 as **unresolved** rather than
quietly settling it, and — the part that decides this review — **hunts and reports its own
defect, then proves the generalisation instead of asserting it.** A package whose only check
is a reviewer, that hands the reviewer a positive control for its own failure, has earned the
approval.
