---
work_package_id: WP01
title: The shared scan module and its inert sub-form registry
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-007
- FR-009
- FR-010
- NFR-004
- C-003
- C-004
- C-006
- C-012
- C-013
planning_base_branch: feat/isolated-home-pin-guard
merge_target_branch: feat/isolated-home-pin-guard
branch_strategy: Planning artifacts for this mission were generated on feat/isolated-home-pin-guard. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/isolated-home-pin-guard unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
history: []
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/_home_pin_scan.py
- tests/architectural/test_home_pin_scan_limbs.py
execution_mode: code_change
owned_files:
- tests/architectural/_home_pin_scan.py
- tests/architectural/test_home_pin_scan_limbs.py
role: implementer
tags: []
task_type: code-implementation
tracker_refs: []
---

# Work Package Prompt: WP01 (alias WP-0a) – The shared scan module and its inert sub-form registry

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Build `tests/architectural/_home_pin_scan.py` — the **one** importable scanner for the `SPEC_KITTY_HOME`
behaviour class (enumerator, mandatory byte pre-filter, `SyntaxError`-propagating parser, binding resolver,
key-parameterised write-site finder, scope-chain silhouette keyer, `discover()`, census/baseline generators)
— plus the shared vocabulary (`MemberKey`, `Member`, `Exempt`, `INERT_LIMBS`) that three downstream
packages bind to. Ship `tests/architectural/test_home_pin_scan_limbs.py`, the inert **sub-form** registry with
a positive control for every population-0 claim and a completeness check that does not grade its own homework.

## Context

- **Why one module.** This repository has the drift failure on record as a live incident:
  `tests/architectural/_sole_door_scan.py:13-27` documents Gates 4 and 5 each rolling an independent,
  drifting copy of the same primitives, Gate 4's copy having already lost Gate 1's docstring rationale.
  Prose ("WP-b imports it") did not prevent it there. The binding contract is
  `contracts/home-pin-scan-seam.md` — **read it before writing a line**; it is normative on this WP,
  which is its sole author.
- **Who depends on you.** WP02 (`_home_pin_gate.py`) is your *first consumer* and exercises FR-009's root
  parameter via `git archive` extraction before anybody else. WP03's `E`, WP04's mypy harness and WP05's
  baseline all bind to the `Exempt`/`MemberKey` you export here. Measured precondition: `class Exempt`
  exists **nowhere** under `tests/` or `src/` today — that is why this module owns the types.
- **Plan concerns**: IC-01 (the shared scanning module and its anti-drift seam), IC-08 (CI landing).
- **The key type is settled, not open** (`data-model.md`, plan §7 BLOCKER-1):
  `MemberKey = tuple[str, str, str] = (relpath_posix, *composite_key_from_file(path, lineno))`, formed at the
  **write site**. The bare 2-tuple yields 19 distinct values over the 40 members and is refused.
- **Do not redesign.** `wps.yaml`'s subtask DoDs are the product of two adversarial gates. If you believe a
  subtask is wrong, **record it in `record.md` and raise it — do not silently repair it.**

---

### Subtask T001: `_home_pin_scan.py` — the walk, the byte pre-filter, a parse that never swallows `SyntaxError`, and the shared types

**Purpose**: Lay the module's floor: an un-narrowed walk, the mandatory pre-filter, a parser that raises, and
the shared vocabulary three packages bind to. Nothing here sees membership — this is the walk and the words.

**Steps**:

1. Create `tests/architectural/_home_pin_scan.py` with the public surface from
   `contracts/home-pin-scan-seam.md` §"Public surface". Export, at module level:
   `MemberKey`, `Member`, `Exempt`, `INERT_LIMBS`. No other module in the Mission may define any of them.
2. `enumerate_py_files(root: Path)` — every `.py` under `root`. **Never narrowed**: not by directory, not
   by filename. C-003 states that narrowing by directory or filename qualifies under neither carve-out form.
3. `byte_prefilter(paths)` — files whose raw bytes contain `b"SPEC_KITTY_HOME"`. FR-002 makes this
   **mandatory, not an optimisation**; keep it deliberately separate from the walk so the walk stays
   assertable while the parse set shrinks.
4. `parse_module(path)` — **propagates `SyntaxError`**. `except SyntaxError: continue` is forbidden: it
   narrows the walk with nothing firing and buys budget headroom, which is NFR-001's defeat wearing an
   exception handler.
5. Fix `MemberKey` composition **explicitly**, because the types differ:
   `MemberKey = (relpath_posix, *composite_key_from_file(path, lineno))`. The repository primitive returns
   `tuple[str, str]`, so a direct comparison against a 3-tuple is a `mypy --strict` **type error**, not
   merely a wrong assertion. `Member` also carries a non-authoritative `lineno`, never part of the key.
6. Write the T001 limbs into `test_home_pin_scan_limbs.py`:
   - `enumerate_py_files(root)` returns a set **EQUAL** to `set(Path(root).rglob("*.py"))` **computed inline
     in the test and never obtained from the module under test**, asserted over the real `tests/` tree **and**
     over a materialised tree reached through FR-009's **root parameter** containing an `_`-prefixed
     directory, a `conftest.py`, a nested package and a non-`.py` file. The count is **REPORTED, never
     asserted**. Every population in this WP is an AST set, never a text search (C-003).
   - `byte_prefilter` over a tree with three `b"SPEC_KITTY_HOME"` files and three non-hit files returns
     **exactly** the three hits — **set equality naming BOTH the included and the excluded**, so a
     pass-through implementation reds.
   - `parse_module` **RAISES** `SyntaxError`; plus an AST assertion over this module's own source proving
     **zero** `except SyntaxError` handlers, with a **positive control** proving the matcher finds one where
     it exists (the control must return a hit or the check is vacuous).

**Files**: `tests/architectural/_home_pin_scan.py` (new, ~250 lines at this stage);
`tests/architectural/test_home_pin_scan_limbs.py` (new, ~120 lines at this stage).

**Validation**: A walk narrowed by directory or filename fails the materialised root's set equality.
`except SyntaxError: continue` fails the self-AST check.

**What this cannot see**: nothing about membership — it is the walk and the vocabulary.

---

### Subtask T002: The binding resolver and the key-parameterised, receiver-agnostic write-site finder

**Purpose**: One finder, two environment variables; one resolver, eight value forms. Prove receiver-agnosticism
on the **call**, which is what actually admits the `:1165` boundary case.

**Steps**:

1. Implement `find_write_sites(tree, *, key: str) -> list[WriteSite]` — **parameterised by environment
   variable**, called with `key="SPEC_KITTY_HOME"` for membership and `key="HOME"` for `home_partition`.
   **One implementation, two keys; never a second finder.**
2. The three-form write, **receiver-agnostic, tested on the call**: `setenv` as attribute **or bare name**
   with a literal first argument; `os.environ[...] = ` / `environ[...] = `; `.setdefault(..., ...)`.
   Receivers bound by a `with ... as` item must bind — not only `ast.Assign`.
3. Implement `resolve_value(node, bindings) -> str | None` — single-assignment local bindings, unwrapping
   `str` / `Path` / `os.fspath` / `joinpath`, joining f-strings, plus `os.path.join`, `%`-format, `.format()`
   and `+` concatenation. **`None` is unresolvable and never matches anything.**
4. Test limbs, in `test_home_pin_scan_limbs.py`:
   - Over **one materialised module containing exactly one instance of every write form** —
     `monkeypatch.setenv`, a **BARE-NAME** `setenv`, `os.environ[...] = `, `environ[...] = `,
     `.setdefault(...)`, and `with pytest.MonkeyPatch.context() as mp:` then `mp.setenv(...)` —
     `find_write_sites(tree, key="SPEC_KITTY_HOME")` returns a set of `(lineno, form)` pairs **EQUAL** to
     the enumerated expected set.
   - The **same function** with `key="HOME"` over a module writing both returns **exactly** the `HOME` sites
     and none of the others. One implementation, two keys, **proven by the second call**.
   - `resolve_value` returns `tmp_path/"home"` for each of `str(tmp_path / "home")`, `Path(tmp_path, "home")`,
     `os.fspath(...)`, an f-string, `os.path.join(...)`, `%`-format, `.format()` and `+` concatenation —
     **each enumerated separately**; and `None` for a `Name`-keyed and a dynamic form, with `None` asserted
     **never to compare equal to any target**.

**Files**: `tests/architectural/_home_pin_scan.py` (+~150 lines);
`tests/architectural/test_home_pin_scan_limbs.py` (+~130 lines).

**Validation**: **The discriminator is NOT what the plan first said.** Measured by removing `withitem`
binding entirely: all 40 members are still found and `:1165` is **still admitted**. What admits `:1165` is
**receiver-agnosticism on the call** — a receiver-*qualified* matcher is what drops it and biases `r`
toward *proceed*, and **the bare-name case is what catches that**. `withitem`-bound-receiver *resolution*
matters only when a VALUE expression references a with-bound name, whose real-tree population is 0; it is an
inert sub-form registered in T004, not a load-bearing limb.

**What this cannot see**: whether a site is inside a member — that is T003.

---

### Subtask T003: The keyer, `discover()` over both variables, and the identity/attribution separation

**Purpose**: The single most reversible decision in the Mission. Getting it backwards fails SC-001 two packages
downstream.

**Steps**:

1. **IDENTITY AND ATTRIBUTION ARE SEPARATE AND THEY DISAGREE** (C-012(1)-(4)):
   - **(a)** The `MemberKey` qualname component is the **WRITE-SITE enclosing qualname**, i.e. the repository
     primitive's value, which is the **INNERMOST** dotted qualname (`anchoring.py:173,211` — the `def` and
     docstring head at `:173`, the `min(candidates)` span-width selection at `:211`). Measured:
     innermost keying gives symmetric difference **0** against the C-011 anchor; outermost gives **2**, both
     at `:1165`.
   - **(b)** The **KEYED def** — the **outermost** def in the chain satisfying the silhouette —
     determines **MEMBERSHIP**, `kind`, and the rename signature's parameter set, and **is NOT IN THE KEY**.
   - **(c)** C-004 is therefore mechanised by the **`kind` DISTRIBUTION**, asserted as a mapping:
     `{fixture: 30, test-body: 10, helper: 0}` at the keyed def against `{30, 9, 1}` at the innermost —
     the withdrawn split. **That assertion, not the key set, is what reds if an implementer attributes to the
     innermost.**
   - **(d)** Keys are formed **FROM THE ALREADY-PARSED TREE** `discover()` holds, **never by re-reading**:
     `composite_key_from_file` reaches `anchoring.py:192-195`, which swallows `SyntaxError` and returns
     `"<module>"`, so re-reading would silently degrade a broken file and leave SC-013's guarantee holding
     only on the `parse_module` path. It is used **ONLY** for the independent live recomputation, where the
     file is known-parseable.
2. Implement the silhouette over the **enclosing scope chain's union of parameter sets**, leading `self`/`cls`
   stripped, superset test (never arity-exact, never order-sensitive). FR-010: a parameter naming the canonical
   owner counts as `tmp_path` for **both** silhouette and value resolution.
3. Implement `discover(root: Path, *, prefilter: bool = True)` resolving **both** variables and attaching
   `home_partition` (A / B1 / B2 / other per `research/m4_ablation_evidence/VERDICT.md:38-41`).
4. `discover()` **asserts exactly-one at import** over its own output, using the repo's D-1 rule
   (`assert_descriptor_unique_within_qualname` / `ContentDescriptor.occurrence`).
5. Test limbs: `discover(root=<materialised>)` returns a `MemberKey` set **EQUAL** to an enumerated expected
   set containing, **each named**:
   - a member in a **nested closure** whose own parameters are neither `tmp_path` nor `monkeypatch`;
   - a member satisfying the silhouette **only through the chain union**;
   - a member declaring `(monkeypatch, <a fixture yielding a home root>)` with **no `tmp_path`**, admitted by
     FR-010;
   - a **NON-member** resolving to `tmp_path/"other"`;
   - a **NON-member** whose value is unresolvable.
6. `home_partition` is produced for **every** member with one materialised example each of `A`, `B1`, `B2`
   and `other`. `other` has real-tree population **0**, so its example **is** its registered positive control.
7. The import-time exactly-one assertion **RAISES** on a tree carrying two members with a byte-identical
   3-tuple, and **does not raise** on `discover(Path("tests"))`.

**Files**: `tests/architectural/_home_pin_scan.py` (+~200 lines);
`tests/architectural/test_home_pin_scan_limbs.py` (+~160 lines).

**Validation**: Both discriminators for (a)/(c) currently rest on **one real-tree site**, `:1165`, held in the
class by an unused `monkeypatch` parameter that `ruff`'s relaxed `ARG` for `tests/**` will not defend. The
synthetic outermost-versus-innermost witness that removes that dependency is a permanent-guard obligation and
lands in **WP04/T017** — do not attempt it here.

**What this cannot see**: whether the real member set is the right one — that anchor is external (C-011)
and asserted in WP05/T023.

---

### Subtask T004: `test_home_pin_scan_limbs.py` — the inert SUB-FORM registry, its controls, and a completeness check that does not grade its own homework

**Purpose**: Name every shape whose real-tree population is 0, prove each claim with a control, and bind the
registry to the specification rather than to itself.

**Steps**:

1. Declare `_home_pin_scan.INERT_LIMBS: frozenset[str]`, naming every **SUB-FORM** whose real-tree population
   is 0. **SUB-FORM, NOT LIMB**: a limb is a whole clause of the predicate, a sub-form is one shape within it.
   Any registry entry whose real-tree population is **NON-ZERO** is a **REGISTRY DEFECT**, not a matcher
   defect (FR-001, amended).
2. The **fifteen** entries, with the populations FR-007's table publishes:
   `setdefault` at `SPEC_KITTY_HOME` **0**; **BARE-NAME `setenv` 0**; `os.path.join` / `%`-format /
   `.format()` / `+` concat in a value at `SPEC_KITTY_HOME` **0 each**; the same four at `HOME` sites
   **0 each**; `HOME` via `setdefault` **0**; explicit `scope=` among the 49 pin-bearing fixtures **0**;
   `home_partition == "other"` **0**; `withitem`-bound receiver referenced by a VALUE expression **0**; and
   SC-002b's **assignment-bound `"SPEC_KITTY_HOME"` constant 0** (id `assignment_bound_env_key_constant`).
   SC-002b is the one **not** in FR-007's table — it is named separately in the same FR-007 row, and the
   delta must be **stated in the module** so a reviewer can check it.
3. **THE `HOME` ENUMERATION IS NOT REGISTERED.** Measured, it is the most heavily populated limb in the
   classifier — **85 write sites in 50 files, with 13 of the 40 members re-pinning `HOME`** — and
   registering it would mandate a FALSE empty-set assertion whose cheapest repairs are both catastrophic:
   narrow the `HOME` matcher until it returns `set()`, collapsing B1/B2 into A and surfacing only in a
   different WP; or delete the id, keeping the equality green.
4. For **EVERY** id ship both: **(i)** an empty-**SET** assertion over the real tree, and **(ii)** a
   **POSITIVE CONTROL** running the **same production matcher** over a materialised module containing the
   shape, asserting **exactly that one hit**. **Any control returning `set()` fails the module.**
5. **THE COMPLETENESS CHECK HAS FOUR OPERANDS, AND THE MIDDLE ONE MAY NOT BE THE ONLY ONE:**
   `inline_expected == INERT_LIMBS == {ids of shipped controls}` is only the code-versus-code core, where
   `inline_expected` is a frozenset **ENUMERATED LITERALLY IN THIS TEST MODULE** and **NEVER imported from
   `_home_pin_scan.py`**.
6. **AND THE LITERAL IS BOUND TO THE SPECIFICATION, NOT MERELY TRANSCRIBED FROM IT**: the test **PARSES
   FR-007's inert sub-form table out of `spec.md`** — the table carries an explicit **`id` column**, **one
   sub-form per row**, no four-way cells and no anaphoric rows, with each id backticked in the first column —
   and asserts **both**:
   - `spec_table_ids | {"SC-002b"} == inline_expected`
   - `spec_table_ids - inline_expected == set()`

   **The delta is exactly one and it is named.** FR-007's table carries the **fourteen** classifier
   sub-forms; `SC-002b`'s assignment-bound-constant assertion is a criterion in its own right rather than a
   sub-form of the classifier, so it is in the control set and **not** in the table — and FR-007 says so in
   the sentence directly under the table. **Do not assert the parsed id set EQUALS `inline_expected`**: that
   is false on day one against a fourteen-row table holding a fifteen-element control set, and its cheapest
   repair is to drop the operand. **The row count (14) is REPORTED, never asserted** — asserting it would red
   on a table that legitimately grows, while the set delta already reds when the table grows and the registry
   does not follow. The check is therefore the **quadruple**:
   `spec_table_ids ∪ {SC-002b} == inline_expected == INERT_LIMBS == {control ids}`.
   Without that fourth operand the three code artefacts stay internally consistent and green while **diverging
   from the spec that defines the population** — and a spec/code divergence is exactly the defect that
   produced the `HOME`-limb registration in the first place, so a mechanism that only watches code-versus-code
   guards the wrong axis of its own motivating failure.
7. The same "parse the authoritative document and assert the code matches" shape recurs in **WP03/T012** (the
   owner contract) and **WP05/T026** (M4's `TABLES.md`); this is the third instance and the one where the
   completeness argument actually lives.
8. **STATED COST**: this makes an always-on collected test depend on a `kitty-specs/` document. If the mission
   directory is ever flattened or archived the test must be re-pointed. **That obligation is recorded in
   WP06/T030** rather than discovered by whoever flattens it — do not drop it.

**Files**: `tests/architectural/test_home_pin_scan_limbs.py` (+~250 lines).

**Validation**: Comparing `INERT_LIMBS` only against controls the same author ships proves "every id I
remembered to register has a control", and **can be shrunk to zero and stay green** — the same circularity
C-011 diagnoses for the census, relocated into the registry built to prove the census's proofs were complete.
**The inline literal is what reds when a sub-form is removed from production.**

**What this cannot see**: a shape nobody enumerated. The quadruple closes the gap between the sub-forms the
spec defines, the sub-forms production claims, and the controls that exist; it cannot close the gap between
reality and the specification.

---

### Subtask T005: `render_census` / `render_baseline` and the one documented regeneration entry

**Purpose**: The generators live here (contract §Ownership), so WP05 never needs to edit this module. Prove
the baseline hashes the **key set**, not the file.

**Steps**:

1. `render_census(members, *, sha, owed_to)` emits YAML. Over a **three-member materialised set**:
   - parsed **row key set EQUALS** the input key set;
   - **HEADER key set asserted BY SET EQUALITY**:
     `set(header) == {"generated_by", "regeneration_command", "frozen_at_sha", "owed_to", "fragility_note"}`,
     enumerated, mirroring the row assertion. **A count plus a prose exclusion is the wrong shape**: FR-003's
     whole argument is that a per-row constant is a header scalar wearing row clothing, and the symmetric
     failure is a `reason` **IN THE HEADER**;
   - **row column names EQUAL** `{key, lineno, kind, home_partition}`;
   - `owed_to` matches `^#[0-9]+$`.
2. `render_baseline(members, *, exempt)` is proven to hash the **SORTED KEY SET** and not the file bytes by
   **the only triple that construction satisfies**:
   - **INVARIANT** under an `owed_to` re-point,
   - **INVARIANT** under a header/comment edit,
   - **CHANGES** when one member key is removed.
3. The baseline's **header key set is likewise asserted**, and **it is the tombstone list's named home**:
   `set(baseline) == {"generated_by", "regeneration_command", "census_key_set_sha256", "exempt_set_sha256",
   "tombstones"}` — because FR-004(1) is "paths, named, not described" and the tombstone list had none;
   putting it in the census header would collide with the header set above.
4. `__main__` takes `--exempt-module`, **DEFAULT `None`**, **IMPORTED INSIDE `main()`** so the module-level
   import graph stays acyclic and **WP01 never depends on WP03**. This subtask demonstrates it **ABSENT**
   (empty `E`); WP05/T022 passes it.
5. A second run is **byte-identical**.

**Files**: `tests/architectural/_home_pin_scan.py` (+~120 lines);
`tests/architectural/test_home_pin_scan_limbs.py` (+~90 lines).

**Validation**: `sha256(path.read_bytes())` passes any "a hash exists" check and **fails the first two
invariance assertions** — that is plan §5's day-thirty failure.

**What this cannot see**: whether the real census content is right — that is WP05.

---

## Definition of Done

Every item below is verbatim in substance from `wps.yaml`; per-subtask completion is a
`spec-kitty agent tasks mark-status <Txxx> --status done` event, **not** a ticked checkbox.

1. `_home_pin_scan.py` exports `MemberKey`, `Member`, `Exempt` and `INERT_LIMBS`; **no other module defines
   any of them**. Measured precondition: `class Exempt` exists nowhere under `tests/` or `src/` today.
2. The registry completeness check is the **QUADRUPLE**
   `spec_table_ids ∪ {SC-002b} == inline_expected == INERT_LIMBS == {ids of shipped controls}` — four
   operands: FR-007's parsed table, the literal frozenset written **in the test module**, the production
   export, and the controls actually shipped (T004(6)).
   **This WP owns the registry ENTIRELY** — no downstream package edits `_home_pin_scan.py` or
   `test_home_pin_scan_limbs.py`, and **no DoD here is completed by a downstream WP**.
3. Every positive control parses its materialised source through `_home_pin_scan.parse_module` **ONLY**.
   Direct `ast.parse` and `ast.NodeVisitor` are **banned** in every module importing `_home_pin_scan`,
   **including this one** — WP02/T007's guard enforces it, and a control that calls `ast.parse` directly
   would red the guard it exists to serve.
4. `_home_pin_scan.py` contains **no `subprocess`**, **no git surface**, and **no `except SyntaxError`**, all
   AST-asserted with positive controls.
5. **IC-08 landing, mechanically not by observation**: `test_home_pin_scan_limbs.py` is **TOP-LEVEL** under
   `tests/architectural/`, declares `pytestmark = pytest.mark.architectural`, and is selected locally by
   `-m '(git_repo or integration or architectural) and not timing'`. The orphan ratchet
   `tests/architectural/test_gate_coverage.py::test_no_new_orphan_surfaces` against
   `_gate_coverage_baseline.json` (`orphan_files: []`, `orphan_test_count: 0`) fails on any new test file
   selected by zero CI gates — cite it and the obligation is self-enforcing. **`tests/_arch_shard_map.py`
   is NOT edited**: `default_fallback=True` (`:419`) plus hash-bucketing (`_shard_registry.py:181`) auto-covers
   by construction.
6. `tests/architectural/test_ratchet_positional_anchor_ban.py::test_no_int_line_sink_in_architectural_python_seeds`
   stays green: **no int literal reaches `composite_key_from_file(path, N)`'s second positional argument from
   a module-level seed**, anywhere under `tests/architectural/`.
7. Identical results under `-n0` and `-n auto --dist loadfile` (NFR-003).
8. **NFR-004**: `ruff check` and `mypy --strict` clean on every touched file, **no new suppression, never
   `ruff format`**. CI runs mypy only over `src/specify_cli src/charter src/doctrine` and only as an
   **ADVISORY** step, so `tests/` has no CI backstop and this is a **local obligation**.
9. **C-006 blast radius**: no file under `src/` changes and no existing test module changes; this WP touches
   only its two owned files.

## Not Done If

- `INERT_LIMBS` is compared only against a set derived from `_home_pin_scan.py` — the inline literal
  operand is missing, or the literal is transcribed from FR-007's table **without being asserted against it**.
- The `HOME` enumeration limb is registered as inert, or any registry entry has a non-zero real-tree population.
- The `MemberKey` qualname is taken at the **keyed** def rather than at the **write site**, or C-004 is
  mechanised through the key set rather than through the `kind` distribution.
- A positive control calls `ast.parse` directly instead of `_home_pin_scan.parse_module`.
- Any population-0 assertion ships without its positive control.

## Risks

| Risk | Mitigation |
|---|---|
| A second copy of the predicate drifts into a consumer (live incident at `_sole_door_scan.py:13-27`). | The seam is mechanised by WP02/T007, not asserted in prose. Keep the public surface complete so no consumer has a reason to re-implement. |
| Attribution keyed at the outermost def — the natural reading of "keyed". | `discover()` then fails SC-001 **two packages downstream**. The `kind`-distribution mapping in T003(c) is the assertion that reds locally. |
| The registry's completeness check drifts from `spec.md` while staying internally green. | The fourth operand (T004(6)) parses FR-007's table. Do not drop it to make a red quiet. |
| An always-on test now depends on a `kitty-specs/` document. | Stated cost, accepted; the re-pointing obligation is carried in WP06/T030. |
| Pre-existing reds (C-009 vs DIR-013). | Classify per CLAUDE.md's baseline-red gotcha; record command, failure summary and merge-base evidence in `record.md`; route to the **OPERATOR** as a TG-item. **DIR-013's GitHub issue is the operator's to open — C-013 forbids `gh issue create` here.** |

## Reviewer Guidance

- Check T003(a)/(c) first: identity at the **innermost** write-site qualname, attribution at the **outermost**
  satisfying def, mechanised through the `kind` **distribution**. Everything downstream rests on it.
- Check that **every** population-0 assertion has a control that returns a **non-empty** hit. A control
  returning `set()` is a green that proves nothing.
- Check the completeness operand count: **four**, not three, and `inline_expected` written literally.
- Check `render_baseline`'s triple: invariant / invariant / changes. `sha256(file.read_bytes())` passes a
  "a hash exists" review and fails on day thirty.
- Confirm no `subprocess` and no git surface in `_home_pin_scan.py` — the gate driver lives in WP02.

## Implementation

```bash
spec-kitty agent action implement WP01 --agent <name>
```

**C-013 standing rules**: nothing merged, no branch integration, **never `gh issue create`** (#2991, #3170,
#3226 and #2642 are already filed — cite them), explicit-path `git add <paths>` only, every long command
bounded with `timeout`, and a timeout is a datum — never silently retried. Never `ruff format`. Never a
bare `uv run` or `uv sync`.
