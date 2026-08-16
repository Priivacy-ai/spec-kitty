# M4 ablation evidence — the `home_partition` rule and its independent 28-member labels

**Why this is here.** `home_partition` (FR-003) is derived from a rule that lives in the halted parent
Mission's M4 ablation evidence. Those files exist **only on `spike/isolated-home-3121`**; on
`feat/isolated-home-pin-guard` the directory `kitty-specs/isolated-home-pin-convergence-01KZCTWC/`
contains **only empty directories**. A specification whose evidence citations resolve to nothing on its own
branch cannot be checked by a reviewer, which is the entire point of citing — so the three load-bearing
files are imported here, following the C-011 pattern.

**Extraction, and what was NOT done.** Each file was extracted with
`git show spike/isolated-home-3121:<path> > <here>/<file>`. **No merge, no rebase, no cherry-pick, no
branch integration of any kind.** The spike branch is untouched and unmerged.

## Contents, hash-pinned

| File | `sha256` |
|---|---|
| `VERDICT.md` | `e25ffaad6983d674c0102d2b62cdee2f5f71b4fbfeccd7911a9f9f69743f2396` |
| `TABLES.md` | `ab3ddf7af45c935c6a16cdd9f27d26266f2349060ed5bf0333dcf1ccdc03a224` |
| `RESIDUALS.md` | `a0a8d870b17099fc7b21d889d6dfb034049f54ec2f68f2b0c6df38141fcb5ad0` |

**The import is deliberately PARTIAL** — 3 of roughly 20 files under `evidence/ablation/`. The three
imported files contain relative cross-references to siblings that were not imported (`arm1/raw-output.txt`,
`arm2/control/raw-output.txt`, `nfr005/raw-output.txt` and others); **those resolve only on
`spike/isolated-home-3121`**. Only the `home_partition` rule and its per-member labels are load-bearing for
R1a, and importing the full ablation tree would carry the parent's raw run output into a Mission that
adjudicates nothing.

All three are **verbatim**. `VERDICT.md` carries the known presentation defect D-1 (`GREEN 147/147` where
the fixture governs 6 tests); it is deferred to R1b and deliberately not repaired here — an imported
artefact that the importing Mission edits stops being external evidence.

## The rule, verbatim from `VERDICT.md:38-41`

| partition | definition | n (of 28) |
|---|---|---|
| **A** | does **not** re-pin `HOME` | **17** |
| **B1** | re-pins `HOME` → `tmp_path/"home"` | **9** |
| **B2** | re-pins `HOME` → `tmp_path/"user-home"` | **2** |

Corroborated at `RESIDUALS.md:56-58` — *"re-pin `HOME` | **11** (B1 = 9, B2 = 2)"* over the 28-member class,
so A = 17 is the non-re-pinners and 17 + 11 = 28.

**The partition keys on a SECOND environment variable — `HOME`, not `SPEC_KITTY_HOME`.** That is why no
arrangement of R1a's existing scanner limbs could produce it, and why the plan phase first reported the rule
as "undefined": it was defined precisely, on a branch this one cannot see, over a variable this scanner did
not enumerate. FR-001 now enumerates both.

`TABLES.md` carries a **per-member partition label for all 28**, which is what makes the cross-check below
possible.

## The cross-check — R1a's derivation against M4's labels

Measured during the plan phase by resolving `HOME` writes in each member's own scope chain, with the same
three-form receiver-agnostic write test and the same value resolution used for `SPEC_KITTY_HOME`:

| Figure | Value |
|---|---|
| `home_partition` over the **current 40** members | **A = 27, B1 = 11, B2 = 2** |
| M4's labels over its **28** | A = 17, B1 = 9, B2 = 2 *(parser reproduces `VERDICT.md` exactly)* |
| **Intersection of the 28 and the 40** | **28** — every M4 member is among R1a's 40 |
| **Agreements / disagreements on the intersection** | **28 agree, 0 disagree** |
| Members in M4 but not in R1a's 40 | **0** |

The intersection was **measured, not assumed**: the 28 were identified under the superseded
decorator-limbed predicate, so it could have been smaller, and it is not.

**The decomposition is exact, which is the real strength of the check:**

```
M4's 28        A=17  B1=9   B2=2
  + 2 fixture arrivals (#3108), both B1        ->  30:  A=17  B1=11  B2=2
  + 10 test-body members from the limb drop, all A  ->  40:  A=27  B1=11  B2=2
```

Every one of the 12 members M4 never saw is accounted for by kind and by partition: the 10 from dropping the
decorator limb are **all `test-body` and all `A`**; the 2 from #3108 are **both fixtures and both `B1`**.

**This gives R1a a SECOND external anchor**, authored by a different actor than both R1a's classifier and
C-011's instrument — strictly better than a self-derived column, and the reason the operator ruled for
extending the scanner rather than dropping the field.

## What this import falsified

**§0.3's *"the `HOME` orphaned-binding trap rose from 7 to 9"* is wrong and is corrected to 9 → 11.**
M4 measures B1 = **9** over its 28; both #3108 arrivals are B1 (confirmed here, and §0.3's own claim that
"both arrivals are partition-B1 trap cases" is thereby **verified**); so B1 went **9 → 11**, not 7 → 9. The
endpoints were each low by two. Found only because this artefact was imported — the figure had been cited
in prose for five passes against a definition that lived on another branch.

## Re-deriving the cross-check

The derivation script is not checked in: it is a planning measurement, not a shipped instrument, and WP-0's
extended `find_write_sites` / `resolve_value` supersede it. The method is stated so it can be repeated:
set the scanned key to `"HOME"`, classify all of `tests/`, index resolved values by each member's
`(path, keyed_def_line)`, and label per the table above. WP-0 reproduces this and **publishes the
intersection size and every disagreement** as part of the census evidence.
