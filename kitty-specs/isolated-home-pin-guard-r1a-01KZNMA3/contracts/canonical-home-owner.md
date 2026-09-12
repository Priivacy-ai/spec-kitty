# Contract — the canonical `SPEC_KITTY_HOME` owner fixture in `tests/conftest.py`

**Status**: binding on WP-a (sole author of the fixture), and on WP-b / WP-c as consumers of the
name it fixes.

**Why this document exists, stated before anything it fixes.** The first planning pass assigned
both owner probes to WP-b while WP-a added the fixture they request. Files were disjoint;
**contracts were not**, and that absent contract is why the `return None` / `tuple[str, str]`
conflict survived planning into FR-005 and SC-005. Naming the fixture is not a local detail:
FR-010's resolver limb treats a parameter naming this owner as `tmp_path` for **both** the
silhouette and value resolution, so **the name is a SCANNER INPUT**. This document is therefore
authored and committed **before** the fixture, and WP-a/T012 **parses it** for the declared name —
the binding is mechanical, not adjacency.

---

## 1. The name

| | |
|---|---|
| **Fixture name** | `canonical_home` |
| **Declaring module** | `tests/conftest.py` |

`canonical_home` is **not a free choice**. `tests/architectural/_home_pin_scan.py`
(`OWNER_PARAM_NAMES`) ships `frozenset({"tmp_path", "canonical_home", "runtime_home"})`, and its
own docstring records that entry as **provisional and unbound**: the name was taken from FR-010's
prose at a moment when no contract named the owner, and *"if WP03 names the owner anything else
this entry silently stays inert and only the shipped tests — which supply the name on both sides
of the equality — stay green."* Measured in WP01's review: removing or renaming `canonical_home`
reds only WP01's own fixture tree, and `runtime_home` can be deleted outright with the suite still
green.

**Therefore, normatively:** the declared name in the table above MUST be a member of
`_home_pin_scan.OWNER_PARAM_NAMES`, and WP-a/T012 asserts exactly that, parsing the name out of
**this file**. Without that assertion FR-010's limb goes **permanently inert with every WP01
assertion still green** — which is the failure FR-010 exists to prevent (*"the guard goes blind in
proportion to R1b's adoption"*).

## 2. Stance

| Property | Value | How it is fixed |
|---|---|---|
| `autouse` | **`False`** | By **absence** of the keyword. C-014 limb (ii) — a module that does not name the owner never instantiates it — is a property of pytest's fixture machinery and is only available while the fixture is non-autouse. |
| Scope | **function** | By **ABSENCE of a `scope=` kwarg**, never by `scope="function"`. An explicit `scope=` on a pin-bearing fixture is registered inert as `SCOPE-EXPLICIT` in `_home_pin_scan.INERT_LIMBS`; writing it here would falsify a population-0 assertion in the module that ships it. |
| Return value | **`None`** | The body contains **no `return` and no `yield`**. AST-asserted. |
| Placement | **strictly after `tests/conftest.py:298`** | Line 298 is the `return home_base` of `_isolated_worker_home`. `git diff -U0` must show **no hunk touching any line at or below 298**. |

### 2a. Why `None`, and why it must not be "improved"

FR-005 states it and the reason is **load-bearing for SC-012's non-circularity**. A fixture that
returns its own path invites

```python
assert os.environ["SPEC_KITTY_HOME"] == canonical_home   # WRONG
```

which compares the environment against **the fixture's own report** and passes for an owner whose
body is `return None` with no `setenv` and no `mkdir`. Returning `None` forces the probe to compute
`str(tmp_path / "home")` **itself**, from **its own** `tmp_path`. A future pass that "helpfully"
returns the path re-opens exactly this hole, so the property is stated here rather than left to be
inferred from the body.

### 2b. `tuple[str, str]` belongs to `E`, not to the fixture

FR-005 and SC-005 both carried the conflation. Stated once, normatively: **`tuple[str, str]` is the
type of the trailing `composite_key` component of the owner's ENTRY IN `E` (`Exempt.key`, whose
full type is `MemberKey = tuple[str, str, str]`), and is NEVER the type of the fixture.** An
implementer told to AST-assert both finds that whichever limb they pick the other is unsatisfiable,
and the cheapest escape is to weaken one — C-002's named failure mode.

## 3. Body

Normative requirements on the body, in full:

1. It establishes the home **ONLY via `monkeypatch.setenv`**, with the literal key
   `"SPEC_KITTY_HOME"` and a value resolving to `str(tmp_path / "home")`.
2. It contains **no `monkeypatch.setattr(Path, "home", …)`** and **no process-global patch** of any
   kind (no `os.environ[...] = `, no `setattr` on any imported module, no `setdefault`).
3. It **creates the directory before the test body runs** — a `mkdir` in the fixture body, so
   `Path(os.environ["SPEC_KITTY_HOME"]).is_dir()` holds **at test-body entry**.
4. It **never overrides a definition keeping its own pin**.

Requirements 2 and 4 are FR-006, and **requirement 2 is only its static half.** FR-006 requires the
rule **DEMONSTRATED BEHAVIOURALLY, not merely asserted from source**: T012 carries the
establishment half (SC-012 limb 1) and T013 the never-wins half (SC-012 limb 2, with its
discriminating negative control).

### 3a. Precedence relative to `_isolated_worker_home`

`tests/conftest.py:272-286` records a decision this fixture **must not violate**: the worker home is
established **only via the HOME/USERPROFILE/XDG env vars**, deliberately **not** by
`monkeypatch.setattr(Path, "home", …)`, because the `setattr` form pinned `Path.home()` regardless
of any later in-test `setenv("HOME", …)` and **silently won over ~16 `tests/sync` cases**. C-005
binds that decision unchanged.

The canonical owner adopts the **same** stance for the **same** reason, one variable over:

| | `_isolated_worker_home` | `canonical_home` |
|---|---|---|
| Variables | `HOME` / `USERPROFILE` / XDG | `SPEC_KITTY_HOME` |
| `autouse` | `True` | **`False`** |
| Scope | function | function |
| Establishment | `monkeypatch.setenv` only | `monkeypatch.setenv` only |

**Ordering:** `_isolated_worker_home` is autouse and function-scoped, so pytest instantiates it
**before** `canonical_home` for any test that requests the owner. The two write **disjoint**
variables, so the ordering is not a precedence question between them. The precedence question this
Mission is actually about is **owner versus a requesting module's own pin**, and it is settled the
way `:272-286` settles it: a later `monkeypatch.setenv` in a fixture that **requests** the owner
runs **after** the owner's setup and therefore wins. **T013's probe (a) must place its pin in a
module-local FIXTURE requesting the owner, never in the test body** — fixture setup completes
before the body runs, so a body-level `setenv` wins by ordering *unconditionally* and proves nothing
about the fixture-versus-fixture precedence this clause is about.

## 4. Placement, and what the diff-shaped check cannot see

The addition is **strictly after line 298**. That criterion alone is satisfiable with its risk
untouched: **inserting the owner *above* line 253 shifts `_isolated_worker_home` down and changes
conftest definition ordering while the old line range shows no modification.**

The only limb that sees that is SC-010/NFR-005, and its form is fixed here:

> Assert the module's **ORDERED LIST of definition names, with the newly-added owner removed**, is
> **equal** to the same list at the merge base. **One known addition, then exact equality**, over
> the **whole module** — ordering on **both** sides of the anchor.

Explicitly **not**:

* a **scalar definition index** — invariant under insert-one-above-plus-delete-one-above, and in a
  Mission governed by C-002 it was the last surviving scalar comparand;
* "unchanged" **outright** — literally unsatisfiable once FR-005 requires this WP to add the owner
  to this very file. (SC-010 records both ends of that axis: the criterion was first written so it
  could not fail, then repaired so it could not pass.)
* narrowed to the names **preceding** `_isolated_worker_home` — that form cannot see a reorder
  *below* the anchor, and conftest fixture resolution depends on the ordering throughout.

## 5. Consumers, and the assertions bound to this file

| Subtask | Binding |
|---|---|
| **T011** | The fixture carries the name in §1 and every property in §2 and §3. |
| **T012** | **Parses this file** for the declared name, `autouse` stance and scope; asserts the `tests/conftest.py` fixture carries **that** name and **those** properties; and asserts **the same parsed name is a member of `_home_pin_scan.OWNER_PARAM_NAMES`** (§1). |
| **T013** | Probe (a) — the `E`-slot member — pins `str(tmp_path / "home")` in a module-local fixture **requesting** the owner (§3a). Probe (b) — the non-member negative control — pins `str(tmp_path / "probe-home")`, a value the owner can never produce, and is the **only** assertion of the pair that can be falsified. |
| **T014** | The owner's entry in `E` is keyed on `tests/conftest.py` at the owner's `setenv` site; `E`'s keys are content-addressed 3-tuples and any `lineno` used to recompute one comes from `discover()` **at runtime**, never from a literal. |

## 6. What this document cannot see

**Whether the owner works.** Nothing about a contract can. SC-011 is pure shape, and C-014 limbs
(i) and (ii) are properties of pytest's fixture machinery rather than of the owner's body — **an
owner whose body is `return None` with no `setenv` and no `mkdir` satisfies both.** SC-012 limb 1
carries the entire behavioural load alone, and **SC-011 green is not evidence the owner works.**
