# Phase 0 Research — R1a

The spec's **settled population figures** were not re-derived from scratch. Figures this pass DID measure —
because a decision or a blocker turned on them — are marked *(measured here)* and listed in R7 and R8.
*(The first pass opened with a blanket "not re-measured" claim that R7 contradicted three lines later.)*
Sections run R1-R8 in order.

---

## R1 — OD-001: which tracker reference `owed_to` names

- **Decision**: `#3121`, on all 40 rows.
- **Rationale**: `gh issue view 3121` returns `state: OPEN`, assignee `MOES-Media`, labels `priority:P2` +
  `tech-debt`, and a title whose subject is precisely the adjudication R1b performs. It is a live creditor.
  R1a cannot create issues (C-013), and a row naming a not-yet-minted number resolves to nothing — the
  failure OD-001 itself names. `^#[0-9]+$` (FR-003) admits it.
- **Alternatives considered**: (i) an operator-minted R1b ticket — rejected because it makes WP-c's landing
  depend on an action outside the Mission and risks an unresolvable `owed_to`; (ii) per-row differentiated
  creditors — rejected as a `reason` column in disguise, which FR-003 struck.
- **Reversal cost**: zero. Re-pointing `owed_to` is a regeneration (FR-004(2)), and the baseline hash is
  over the sorted `composite_key` set, not the file — so no hash changes and no tombstone is needed.

## R2 — OD-002: how C-003 form (i) is discharged, and at what strength

- **Decision**: form (a), both-passes set identity, at NFR-002's 90 s budget. **No hybrid.**
- **Rationale**: the hybrid's entire case was that (a) is "separable and non-gating" and therefore might
  not run on a normal PR. Read at `.github/workflows/ci-quality.yml`, the always-on `arch-adversarial` pole
  selects `-m '<shard> and not windows_ci and (git_repo or integration or architectural) and not timing'`,
  so an `architectural`-marked, non-`timing` module runs on 100% of pushes and PRs. Form (a) measured
  ≈18.6 s against 90 s. **"Separable" means separable from NFR-001's budget, not from CI.** With that
  established, (b) is strictly weaker, assumes the member set it exists to help establish, and would supply
  a cheap green for anyone tempted to delete the strong proof.
- **Alternatives considered**: (b) alone — rejected as a criterion weakening; the hybrid — rejected once
  its premise was falsified by measurement.
- **Implementation constraint**: both passes must be **one classifier called twice**
  (`discover(root, prefilter=True|False)`), never two implementations agreeing with each other.
- **Stated limitation**: neither form closes the key-indirection hole; with respect to it, 90 s buys nothing
  over 0.056 s. SC-002b is separate, unconditional and not substitutable.

## R3 — OD-003: the CI-runner factor in NFR-001

- **Decision**: discharge by measurement on the mission's own draft PR, not by argument.
- **Finding**: the runner is `blacksmith-4vcpu-ubuntu-2404`, a 3-shard matrix under `-n auto --dist
  loadfile`, `if: always()`, no path filter, no `needs:` edge to the fast lane.
- **Complication found, and resolved by an existing job**: the pole excludes `timing`-marked tests, and a
  wall-clock assertion under `-n auto` contention on 4 vCPUs is a flake generator — so SC-007's budget test
  belongs outside the pole. The repository already ships its home: **`timing-nfr-serial`**
  (`ci-quality.yml:2193-2211`) runs `-m timing -n0` over `tests/` on the same
  `blacksmith-4vcpu-ubuntu-2404`, with `if: always()`, no filter gate, no `needs:` edge, and it **is wired
  into `quality-gate.needs`, so a red timing gate blocks merge**.
- **Method**: mark the budget test `timing`, land WP-b on the draft PR, read the figure out of
  `timing-nfr-serial`. **The budget may be raised with that evidence; the walk may never be narrowed.**
- **Residual, stated**: that job measures the guard *uncontended*, while `arch-adversarial` runs it under
  `-n auto`. The serial figure is a floor, not the worst case. Raising the budget against it requires the
  contention headroom to be stated, not assumed.

## R4 — Where a new architectural test actually runs (repository finding)

- **Question**: does landing in `tests/architectural/` suffice for OD-004's "100% of PRs"?
- **Answer**: **no.** The pole selects `(git_repo or integration or architectural)` and **no conftest hook
  auto-applies any of them**, so a module declaring none of the three is collected and then deselected on
  every PR. Declaration is by convention across `tests/architectural/`. *(A count was published here and is
  **withdrawn** — see this section's correction below.)*
- **Second finding** — **[WITHDRAWN — see the fourth finding below]**: `tests/architectural/test_arch_shard_marker_completeness.py` asserts a **total
  partition** — every test collected under the arch pole roots carries exactly one `arch_shard_N` marker,
  applied from `tests/_arch_shard_map.py`. **The conclusion drawn here was WRONG**: it read *"a new arch test
  file with no row reds that existing guard, so editing that table is mandatory."* `default_fallback=True`
  auto-covers any unregistered under-root file, so **editing the table is optional balance pinning** — see
  the fourth finding. The C-006 enumeration gap the finding identified was real; the premise was not.
- **Third finding**: markers live in `pytest.ini`, not `pyproject.toml`, and single-sourcing is guarded by
  `test_marker_registry_single_source.py`. This is a reason **not** to mint a new marker for NFR-002 — and
  form (a) needs none. `timing` and `architectural` are both already registered.
- **Correction to this section's own first finding**: the pole selects `(git_repo or integration or
  architectural)`, so the requirement is that **disjunction**, not the `architectural` marker alone. The
  "161 of 164" count is **withdrawn** — by AST it is 162/165 recursive and 161/164 top-level, it is
  sensitive to whether a per-function decorator counts alongside a module-level `pytestmark` (which is how
  `test_resume_non_reemission_guard.py` differs), and it was originally a text-search figure, which C-003
  bars. The qualitative claim carries the argument.
- **Fourth finding, and the first pass got its consequence backwards**: `test_no_new_orphan_surfaces` is a
  hard ratchet with an **empty** committed baseline, so every new test file must be selected by at least one
  job. But `tests/_arch_shard_map.py:419` sets `default_fallback=True` and `tests/_shard_registry.py:181`
  hash-buckets any unregistered under-root file, so **a new file is auto-covered and no table edit is
  required to keep main green** — the module's own docstring says so twice. The prior-mission incident the
  first pass quoted as current behaviour ends *"...until the `default_fallback` hash-bucket auto-cover
  picked them up"*. Editing the table is **optional balance pinning**, and the plan's conflict pre-emption
  design is deleted because the conflict does not exist.
- **Fifth finding**: the shard table is keyed *"by whole test-file (for `tests/architectural/*.py`) or
  whole directory (for the other three pole roots)"* — a `tests/architectural/<subdir>/` module falls in
  the gap between those rules. All R1a modules therefore land flat at `tests/architectural/*.py`.

## R5 — The C-011 evidence artefact (RESOLVED — recovered and checked in)

- **Question**: where is the published `composite_key` set that SC-001 and SC-003 assert against?
- **First-pass answer**: it did not exist. Every commit from `11ef62051` to `96b2b0910` touched only
  `spec.md` and `meta.json`; `research/` and `checklists/` were empty.
- **Resolution**: the operator recovered the post-spec gate's independent reproduction. It is checked in
  **verbatim** at `research/spec_kitty_home_pin_evidence/` (`clf.py`, `step3.py`, `members.json`,
  `README.md` with `sha256` pins) and is now named by path in C-011.
- **Why it beats the one-shot oracle the first pass proposed**: authored by an independent third lens from
  the spec's predicate text alone, never compared against the author's classifier before publication, and
  it reproduced every headline figure on the first run with no tuning. The oracle is dropped, and with it
  the unauthorised scope and the C-006 gap it created.
- **Verified here, not trusted**: re-running `step3.py` rewrites `members.json` byte-for-byte;
  `git diff --stat 5d49d31ed HEAD -- tests/` is empty so the measured tree is this tree; and it reproduces
  40/36, the 30/10/0 split, 39-under-innermost with symdiff exactly `:1165`, and 30 under the superseded
  predicate — the arithmetic that settles FR-001's corrected `10 against 0`.

## R7 — The census key type (BLOCKER-1, OPEN)

- **Question**: does `composite_key` uniquely identify each of the 40 members?
- **Answer**: **no** *(measured here)*. With the repo's own `composite_key_from_file` against the evidence
  artefact: 40 member sites yield **19** distinct bare keys; the path-qualified 3-tuple yields **40**.
  Three distinct figures, published separately: **19 keys / 21 surplus rows / 29 invisibly-removable
  members** (any member of a class of size >= 2). The 3-tuple is **also** non-injective over the 191 sites
  the guard walks — 190 distinct, one live class of two at
  `tests/paths/test_runtime_root_spec_kitty_home.py:91,93` — closed by an import-time exactly-one assertion. The largest
  collision class is **11** members sharing `('_isolated_home', 'monkeypatch . setenv ( , str ( tmp_path / ) )')`
  — `normalized_token_line` strips string literals, and the tree has 22 identically-named `_isolated_home`
  fixtures (the subject of #3121's own title).
- **Consequence**: FR-003's "40 rows" is unsatisfiable; FR-004's ratchet greens on the removal of any of
  the 21 members in a collision class; SC-006's transitions 3/4/5/7 do not red for the most likely 41st
  member.
- **Resolution lies inside C-012**, which both names the bare key *and* names the sole-door idiom as the
  one to follow — and that idiom is already path-qualified (`ConstructionSite(rel_path, qualname, token,
  …)`, `_sole_door_scan.py:524-529`). `(rel_path, enclosing_qualname, normalized_token_line)` satisfies
  both clauses and measures 40/40.
- **Resolved by the operator as an INTERPRETATION of C-012, not an amendment**: all three authorities C-012
  names already use the 3-tuple for row identity. C-012's *justification* sentence is corrected, since the
  3-tuple does express two sites in one definition. The key is formed at the **write site** — the two
  readings give 40-row censuses with **zero overlap** (19 vs 21 keys) *(measured here)*.

## R9 — `home_partition`: the rule, and the second external anchor *(measured here)*

- **The rule was never undefined.** It is at `spike/isolated-home-3121:.../evidence/ablation/VERDICT.md:38-41`
  — **A** does not re-pin `HOME`, **B1** re-pins to `tmp_path/"home"`, **B2** to `tmp_path/"user-home"` — and
  it **keys on a second environment variable**, which is why no arrangement of R1a's existing limbs produced
  it. The plan's first report ("undefined") had the symptom right and the cause wrong.
- **Imported verbatim** to `research/m4_ablation_evidence/` via `git show` (no merge/rebase/cherry-pick),
  `sha256`-pinned, cited from FR-003 and C-006. Partial by design: 3 of ~20 ablation files.
- **Measured over the current 40**: A = 27, B1 = 11, B2 = 2, zero `other`.
- **Cross-check**: intersection with M4's 28 is **28** (measured, not assumed — it could have been smaller,
  since the 28 came from the superseded predicate); **28 agreements, 0 disagreements**. The delta decomposes
  exactly: the 10 limb-drop members are all `test-body`/`A`; the 2 #3108 arrivals are both fixtures/`B1`.
- **Falsified**: §0.3's *"trap rose from 7 to 9"* is **9 to 11**. Its companion claim — that both arrivals
  are B1 — is verified by the same measurement.
- **Pre-filter soundness for the second variable**: a member's scope chain is within one file, so every
  partition-relevant `HOME` write is in a byte-hit file. Stated, not assumed.

## R8 — Figures measured by this pass

| Figure | Value | Why it was measured |
|---|---|---|
| Distinct bare / 3-tuple keys over 40 members | 19 / 40 | BLOCKER-1 |
| Surplus rows / invisibly-removable members | 21 / 29 | BLOCKER-1's three figures |
| 3-tuple injectivity over all 191 sites | 190 distinct, 1 class of 2 | B5 |
| Write-site vs def-line key sets | 19 vs 21, **overlap 0** | B4 |
| `ast.Constant` valued `"SPEC_KITTY_HOME"` in `src/` u `tests/` | **229** in 98 files | B6 — SC-002b was false as written |
| Assignment-bound such constants | **0** | B6 — the population §0.6a actually argues |
| UNRESOLVED write sites | 3, **0 members-in-waiting** | A2 — widening admits 0 new members |
| Band states over consequences | 806 total: 380 go / 364 halt / 62 inadmissible | C5's oracle, and data-model's 682 slip |
| `architectural` marker declarations | withdrawn as a contested ratio | C12 |
| `home_partition` over the 40 | A=27 / B1=11 / B2=2 | R9 |
| M4 intersection / agreement | 28 / 28 agree, 0 disagree | R9 — second external anchor |
| Cited paths unresolvable on this branch | 19 of 79, 3 load-bearing | plan §7.7 |

## R6 — Binding-resolution edge cases the resolver must handle (from the spec, consolidated)

| Form | Requirement | Why it matters |
|---|---|---|
| `with pytest.MonkeyPatch.context() as mp:` then `mp.setenv(...)` | **Receiver-agnosticism on the CALL** — this is what admits `:1165` | Measured by removing `withitem` binding entirely: **all 40 members are still found and `:1165` is still admitted**. The real discriminator is that a receiver-**qualified** matcher drops it. `withitem`-bound-receiver *resolution* matters only when a **value** expression references a with-bound name — population **0**, asserted-inert |
| `setenv` as attribute **or** bare name | Receiver-agnostic; test the **call** | §0.8 states this is not an incidental word |
| `os.environ[...] = ` and `environ[...] = ` | 3 live sites | 188 vs 191 is the reconciliation |
| `.setdefault("SPEC_KITTY_HOME", …)` | Population **0** — asserted-inert | A limb matching nothing must be known to match nothing (FR-007) |
| `str` / `Path` / `os.fspath` / `joinpath` / f-strings, **plus `os.path.join`, `%`-format, `.format()` and `+` concat** | Unwrap and join — **eight forms, not four** (FR-001's widening) | Value must resolve to `tmp_path/"home"`. Each widened form is a sub-form with its own positive control, registered inert at both keys (`SKH-VAL-*` / `HOME-VAL-*`) |
| Unresolvable value | `None`, and `None` never matches anything | Rename pairing must not pair on unknowns |
| Absent `scope=` | Function scope; only an explicit non-function value is rejected | 0 of 49 pin-bearing fixtures carries one (FR-007) |
| A parameter naming the canonical owner | Counts as `tmp_path` for **both** silhouette and value resolution | FR-010 — without it the guard goes blind in proportion to R1b's adoption |
