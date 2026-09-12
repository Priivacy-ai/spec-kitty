# WP01 — residual findings, for WP14's ledger (T068)

Out-of-scope findings are filed here rather than acted on. **`gh issue create` is barred for this
WP**, so none of these was opened as an issue.

---

## R1 — The `blocked → in_progress` FSM edge is unguarded (WP01 T007 step 5 → WP14 T068)

**Verified in this tree, not transcribed** (`src/specify_cli/status/wp_state.py`):

* `:517` `class BlockedState(WPState)`
* `:528` `def allowed_targets(self) -> frozenset[Lane]: return frozenset({Lane.IN_PROGRESS, Lane.CANCELED})`
* **`BlockedState` overrides no `guard_for`** — the class body contains none — so it inherits the
  base hook at `:139`, whose body is `return True, None` and whose own comment states *"the default
  hook is unguarded"*.

Consequence: `blocked → in_progress` requires **no actor, no reason, no `review_ref`, no force and
no operator**, and `blocked → in_progress → for_review → approved` delivers exactly the `approved`
state every downstream WP gates on. A lane state is therefore **not** a halt.

This is why the `|P| ≥ 5` halt is additionally recorded as an append-only comment on issue #3121
(see `HALT.md`). **Filed to WP14 T068 as a tooling gap; not worked around silently.**

---

## R2 — `pytest-repeat` is not a project dependency

The repeated/interleaved arm needs each member re-run ≥2× **in the same process**. Nothing in the
project's `[test]` extra provides in-process repetition, so `pytest-repeat==0.9.4` was installed
**into the external venv only** — it was **not** added to `pyproject.toml` or `uv.lock`, and the
3121 tree is unchanged.

If WP13's parity work needs the same capability, this becomes a real dependency decision (it is an
architectural/packaging call, not an implementer's). Filed for WP14.

---

## R3 — `--count`/`--repeat-scope=session` does not interleave; measured

`--count=2 --repeat-scope=session` runs each test **twice back-to-back** and finishes one module
before starting the next. Measured directly here from the recorded `execution_order`: with
repetition alone, **0 of 196** logical tests had another member's test between their two runs. Any
future WP that reads "repeated ⇒ interleaved" from the flag alone will measure nothing. The
instrument therefore carries `--ablate-interleave` (round-robin across modules) and records an
explicit `execution_order`, because the JSON record is serialised `sort_keys=True` and insertion
order is **not** recoverable from it.

---

## R4 — Prompt/spec figure with two denominators: "11 `HOME` / 8 `LOCALAPPDATA` pinners"

Re-derived by binding-resolving AST (both numbers reproduced, but they are scoped to **different
populations**, which the phrasing hides):

| Figure | Over the **28**-member behaviour class | Over all **47** pin-bearing fixtures |
|---|---|---|
| re-pin `HOME` | **11** (B1 = 9, B2 = 2) | **14** |
| pin `LOCALAPPDATA` | 0 | **8** |

So "11 HOME" is true of the 28 and "8 LOCALAPPDATA" is true of the 47; stated side by side they
read as one population. Everything load-bearing in this WP uses the **28**-member figure, where 11
is correct, so no conclusion here changes. Filed so the phrasing is corrected once rather than
re-litigated per WP.

All other population figures reproduced **exactly**: 2698 `.py` under `tests/`; 47 pin-bearing
fixtures with **0 of 47** carrying an explicit `scope=`; 185 `setenv("SPEC_KITTY_HOME", …)` sites;
28 members in 28 distinct files across 5 directories; A = 17 / B1 = 9 / B2 = 2; 26 `Path.mkdir` +
1 `os.makedirs` + 1 non-creator.

---

## R5 — Instrument defects found and fixed inside this WP (recorded, not hidden)

Both were found by this WP's own gates, and both are the class of defect that would have produced a
**wrong verdict silently**. Superseded raw output is retained under `superseded/`.

1. **Class-defined fixtures need a class-qualified `baseid`.** pytest's `FixtureDef.baseid` for a
   fixture defined inside a test class is `"<module>::<ClassName>"`, not the module path — measured
   on 9.0.3. The first arm-1 run therefore bound **27 of 28** sites and ablated
   `test_identity_value_faults_3030.py` on **zero** of its 6 nodes while still reporting a clean
   `35 failed`. FR-011's zero-ablation refusal **cannot** catch this (27 sites did fire); only the
   expected-vs-observed site comparison did.
2. **`workeroutput` counters were shipped but never merged.** Under `-n auto --dist loadfile` the
   xdist **controller** never runs a test, so it fired nothing and tripped FR-011's refusal on an
   otherwise sound parallel run — precisely the *"a parallel run does not report zero
   suppressions"* failure NFR-005 names. Fixed with a `pytest_testnodedown` merge.

---

## R6 — `docs/adr/3.x/README.md:8-9` documents an INCOMPLETE ADR regeneration procedure (A21 → WP14 T068)

**Filed, not fixed.** `docs/adr/3.x/README.md` is outside C-005's blast radius (`tests/`,
`scripts/mutants/`, and this Mission's own record), and which surface owns the ADR-landing
procedure is an ownership call, not an implementer's. It is recorded here so it is corrected once
rather than re-discovered by the next agent who lands an ADR.

The README says, verbatim at `:8-9`:

> After adding an ADR file, run `python scripts/docs/freshen_adr_inventory.py docs/adr/3.x/<your-adr>.md`
> to update the page-inventory lockfile and add the row to the index table below.

That is true and it is not sufficient. **Three** committed artifacts move when an ADR lands, and
`freshen_adr_inventory.py` writes **two** of them:

| Artifact | Written by `freshen_adr_inventory.py`? | Gated by `check_docs_freshness`? |
|---|---|---|
| `docs/adr/3.x/README.md` index row | **yes** | yes |
| `docs/development/3-2-page-inventory.yaml` | **yes** | yes |
| `docs/development/3-2-docs-retrieval-index.yaml` | **NO** | **yes** — separately, blocking, default-on |

Verified in this tree: `freshen_adr_inventory.py`'s module docstring enumerates exactly two write
targets (the page-inventory row and the era-README row) and the retrieval index appears nowhere in
it; `check_docs_freshness.py:71` names `DEFAULT_DOCS_INDEX_PATH = "docs/development/3-2-docs-retrieval-index.yaml"`
and checks it as a sibling ruler with its own finding class. So an agent that follows the README
exactly lands a **red** `check_docs_freshness`, and the failure surfaces at the gate rather than at
the step that caused it.

**The complete procedure, executed for A21's ADR and recorded here as the correction:**

```bash
python scripts/docs/freshen_adr_inventory.py docs/adr/3.x/<your-adr>.md   # README row + page inventory
python scripts/docs/docs_index.py --write                                  # docs retrieval index
python scripts/docs/check_docs_freshness.py --ci                           # expect EXIT=0
```

**Two hazards to carry with the fix.** (1) All three run from the repository root and need
`scripts` importable — invoked without it they die with `ModuleNotFoundError: No module named
'scripts'`, which reads as a broken script rather than a missing `PYTHONPATH`. (2) The README's
suggested remediation for the gate is a **bare `uv run`**, which is barred for this Mission
(NFR-006 pins `pytest>=9.0.3,<9.1` and WP01 provisioned an **external** venv precisely so that no
venv is created inside the 3121 tree). The instruction was read and refused; the external venv's
interpreter was used instead.

---

## R7 — Two live figures for two different questions: the adopting set is **24**, the parameter-shape count is **23** (A21 → WP14 T068)

`spec.md` §0.6 now records the post-ablation adopting set as **24 of 28**. The Key Entities
silhouette limb records **23** adopters projected to read `(tmp_path, monkeypatch,
canonical_isolated_home)` — adopters taking the owner **as a parameter**, which is what A20's
superset-silhouette argument rests on (`spec.md:452`; `plan.md` IC-02).

**Both figures are real and they answer different questions.** 24 is a cardinality of the adopting
set. 23 is a count of *parameter shapes* among adopters. Neither is "the prize" except 24.

**What A21 did NOT do:** it did not re-derive 23 against the shrunken adopting set. Three members
leave the adopting set under SC-012 discharge (b) and become allowlisted retained definitions —
which by construction do **not** request the owner — so whether 23 survives unchanged depends on
whether any of those three were among the 23, and **that was not measured in this pass**. A21
therefore restates 24 and leaves 23 exactly as A20 wrote it, flagged rather than silently carried.

**Why this was filed rather than fixed.** Re-deriving 23 was thought to require the post-convergence
tree, which does not exist and now will not exist in this Mission's current shape.

### RESOLVED 2026-08-07 (orchestrator) — **23 holds, and it holds structurally**

The question *"were any of the three departers among the 23?"* is answerable from **settled inputs
alone**, without the post-convergence tree. The answer is **no**, and the reason is not arithmetic
luck.

`wps.yaml` WP08 is titled *"Adoption — **the four zero-decoration members that lose their
fixture**"*, and owns exactly:

| zero-decoration member | arm 2 | disposition |
|---|---|---|
| `tests/delivery/test_body_queue_purge_differential_3030.py` | **RED** | **stays** in the adopting set |
| `tests/delivery/test_purge_all_body_uploads_3030.py` | GREEN | departs |
| `tests/delivery/test_purge_all_events_3030.py` | GREEN | departs |
| `tests/specify_cli/identity/test_identity_value_faults_3030.py` | GREEN | departs |

**All three departers are zero-decoration members** — three of exactly those four. A zero-decoration
member *loses its fixture* on adoption and takes the owner through the `usefixtures` / class-decorator
form (plan §3.2 arms J/R), **not as a parameter**. So the three departers were **never in the 23 to
begin with**, and their departure cannot reduce it.

```
pre-halt : 27 adopters − 4 zero-decoration = 23 parameter-takers   (what A20 wrote)
post-halt: 24 adopters − 1 zero-decoration = 23 parameter-takers   (unchanged)
```

**A20's superset-silhouette argument survives verbatim**, because the figure it rests on did not
move. R7's caution was correct and its conclusion is now closed: **24 is the prize; 23 is the
parameter-shape count; both are current.** The one consequence worth carrying: the surviving
zero-decoration member is `test_body_queue_purge_differential_3030.py` in the module-level
`pytestmark` form, so **the class-decorator `usefixtures` form loses its only member** and the
re-scoped Mission exercises one adoption mechanism fewer than the planned one did.

**Still to re-measure in the re-scope** — this resolution settles 23 against *this* Mission's
adopting set. If deletion (route R2) runs first the class is 25, and every figure here must be
re-derived by binding-resolving AST against that population before it is written down again.

**This Mission has been bitten four times by an inherited figure promoted to a gate** — A3's
`KeyError` signature (a scratchpad probe artifact promoted to the gating criterion, corrected by
A16), A5's `15 of 28` floor (name-scoped figures smuggled into an effect-scoped population), A12's
`every file:line was re-derived` claim, and A20's arity axis. Letting 23 and 24 both float as "the
prize" would be the fifth. They are pinned here so they cannot.

---

## R8 — Re-scope route ordering: **deletion before convergence** stales SC-007 transition 1 (A21 → WP14 T068)

Naming collision warning, stated up front: the two re-scope **routes** under discussion are
conventionally called R1 (convergence) and R2 (deletion). **They are not residual IDs.** This
residual is **R8**; the routes are written below as *route-conv* and *route-del*.

If the re-scope runs **route-del (deletion) before route-conv (convergence)**, the behaviour class
shrinks:

```
28  behaviour class today
 −  { test_purge_all_body_uploads_3030.py,
      test_purge_all_events_3030.py,
      test_identity_value_faults_3030.py::TestThePolicyGateAnswersInsteadOfCrashing }
 =  25
```

**SC-007 transition 1 is written as *"reds on the tree as it stands today (28 members outside the
manifest)"*.** After a deletion-first pass that sentence is false by three, and the guard's
red-first demonstration is being asserted against a population that no longer exists. The failure
is quiet: an implementer demonstrating transition 1 on a 25-member tree sees a red and records a
pass, and the `28` in the criterion is never revisited.

**The dependency is explicit and it is one-directional.** route-conv does not stale anything in
route-del. route-del stales SC-007 transition 1, and would also move §0.6's denominator, C-007's
`24 of 28`, FR-004's manifest population, and SC-010's `11 pin HOME / 8 pin LOCALAPPDATA` figures —
every one of which is currently written against **28**.

**Consequence for whoever sequences the re-scope:** either run route-conv first, or amend SC-007
transition 1 (and the denominators above) **in the same pass** that deletes. Deleting first and
amending later is the shape that leaves a criterion silently satisfied by the wrong tree.

**Caveat that must travel with the three deletion candidates.**
`test_identity_value_faults_3030.py`'s arm-2 GREEN reads **147/147**, but its member is a
`self`-bound class-method fixture governing only the **6** tests inside
`TestThePolicyGateAnswersInsteadOfCrashing`. `VERDICT.md` §4: the other **141** nodes are **not
evidence about this pin either way**. Its evidence is over 6 tests — roughly **24× narrower** than
the row's denominator implies. Wherever that member appears beside the other two deletion
candidates, this caveat appears with it.
