# Contract — `tests/architectural/_home_pin_scan.py`, the shared scanning seam

**Status**: binding on WP-0 (sole author), WP-b and WP-c (consumers).

This repository has the failure this contract prevents **on record as a live incident**:
`tests/architectural/_sole_door_scan.py:13-27` documents Gates 4 and 5 each rolling an independent,
drifting copy of the same primitives, Gate 4's copy having *"already lost Gate 1's docstring rationale …
a live drift, not a hypothetical one"*, and names the promoted shared module as the fix. R1a follows that
precedent rather than re-earning it. Prose did not prevent it there; §3c below is why it will here.

---

## Ownership

| Package | May do |
|---|---|
| **WP-0** | Author the module end to end, including `render_census` / `render_baseline` and the `__main__` regeneration entry. |
| **WP-b / WP-c** | **Import and invoke. NEVER edit the module.** `_home_pin_scan.py` is in lane-a's write scope only; a downstream package editing it fails WP01's DoD and WP02's `not_done_if`. Guard-only helpers belong in the guard's own module, not here. |

Putting the generators in WP-0 is a deliberate strengthening of the spec's "WP-b then extends": FR-004(2)
already requires both artefacts to be emitted by this module, so WP-0 owning them removes the only reason
WP-c would touch it — and removes a shared-file conflict from the parallel section of the plan.

## Public surface

```python
def enumerate_py_files(root: Path) -> list[Path]: ...
def byte_prefilter(paths: Iterable[Path]) -> list[Path]: ...
def parse_module(path: Path) -> ast.Module: ...
def resolve_value(node: ast.AST, bindings: Mapping[str, ast.AST]) -> str | None: ...
def find_write_sites(tree: ast.Module, *, key: str) -> list[WriteSite]: ...
def key_member(site: WriteSite, chain: Sequence[ast.AST]) -> Attribution | None: ...
def discover(root: Path, *, prefilter: bool = True) -> set[Member]: ...
def render_census(members: Iterable[Member], *, sha: str, owed_to: str) -> str: ...
def render_baseline(members: Iterable[Member], *, exempt: tuple[Exempt, Exempt]) -> str: ...
```

| Symbol | Contract |
|---|---|
| `enumerate_py_files` | Every `.py` under `root`. **Never narrowed** — not by directory, not by filename (C-003 states narrowing by directory or filename qualifies under neither carve-out form). SC-007 asserts this **set**, with the count reported and not asserted. |
| `byte_prefilter` | Files whose raw bytes contain `b"SPEC_KITTY_HOME"`. **Mandatory, not an optimisation** (FR-002). Deliberately separate from the walk so the walk stays assertable while the parse set shrinks. |
| `parse_module` | Propagates `SyntaxError`. **`except SyntaxError: continue` is forbidden** — it narrows the walk with nothing firing and buys budget headroom, which is NFR-001's defeat wearing an exception handler (SC-013). |
| `resolve_value` | Single-assignment local bindings. **Eight value forms, not four**: unwraps `str` / `Path` / `os.fspath` / `joinpath`, joins f-strings, and — added by FR-001's widening — resolves **`os.path.join`**, **`%`-format**, **`.format()`** and **`+` concatenation**. Each widened form is a **sub-form** carrying its own **positive control** (FR-007), and all four are registered inert at both keys (`SKH-VAL-*`, `HOME-VAL-*`, population 0 each). Returns `None` when unresolvable, and **`None` never matches anything**. |
| `find_write_sites` | **Parameterised by environment variable** — called with `key="SPEC_KITTY_HOME"` for membership and `key="HOME"` for `home_partition` (FR-003). One implementation, two keys; **never a second finder**. The three-form write, **receiver-agnostic, tested on the call**: `setenv` as attribute **or** bare name with a literal `"SPEC_KITTY_HOME"` first argument; `os.environ["SPEC_KITTY_HOME"] = ` / `environ[...] = `; `.setdefault("SPEC_KITTY_HOME", …)`. Receivers bound by a `with … as` item must bind — **not only `ast.Assign`** — for correctness. **That binding is NOT what admits `:1165`, and the claim that it is was struck as FALSE (§0.8):** measured by removing `withitem` binding entirely, all 40 members are still found and `:1165` is still admitted. **Receiver-agnosticism on the call** is what admits it; a receiver-*qualified* matcher is what would drop it. `withitem`-bound-receiver *resolution* fires only when a **value** expression references a with-bound name — population **0**, registered inert as `WITHITEM-VALUE-REF`. `setdefault` has population 0 and its limb is **asserted-inert** (FR-007). |
| `key_member` | **Returns an `Attribution`, NOT a `Member` — the two jobs are done by different functions.** *(Corrected from WP01: the row previously gave `-> Member | None`, which is unsatisfiable against this contract's own key rule. A `Member` carries `relpath` and a source-derived `MemberKey`, and **neither `WriteSite` nor `chain` can supply either**, while the key-type section below says the key is formed "at the boundary, from the record" and **never inside `key_member`**. The signature demanded the keyer return a keyed record; the key rule forbade it from keying.)* **`Attribution` is the silhouette verdict — attributed def, `kind`, parameter set — and `discover()` composes the key at the boundary through the single builder `member_key`.** **The keyer decides WHETHER and WHERE; the boundary decides WHAT IT IS CALLED.** That is the identity-versus-attribution split C-012 already binds; this surface table simply never inherited it. **Two different jobs, and the word "keyed" must not be read as doing both.** **ATTRIBUTION** — silhouette over the **union of the enclosing `def` chain's parameter sets**, leading `self`/`cls` stripped; the member is attributed to the **OUTERMOST** satisfying def, and `kind` plus the rename signature's parameter set are read **there**. Innermost *attribution* is refused (C-004). **IDENTITY** — the `MemberKey`'s qualname component is the **write-site enclosing qualname**, which the repository primitive returns as the **INNERMOST** dotted scope (C-012), and the attributed def is **not in the key**. Measured, and this is not cosmetic: innermost-keyed `discover()` matches the C-011 anchor with symmetric difference **0**; outermost-keyed gives **2**, both at `:1165`. **An implementer who keys identity at the attributed def ships a `discover()` that fails SC-001 two packages downstream.** Absent `scope=` is function scope. A parameter naming the canonical owner counts as `tmp_path` for **both** silhouette and value resolution (FR-010). |
| `discover` | The whole pass, resolving **both** variables and attaching `home_partition`. **Pre-filter soundness for the second variable, stated not assumed**: a member's scope chain lies within one file, so every `HOME` write that can change its partition sits in the same file as that member's `SPEC_KITTY_HOME` write — a byte-hit file by construction; **widening the pre-filter is not permitted as a substitute for this argument**. **Measured, with the denominator published**: of the **50** files holding a `HOME` write, **21 are invisible to the pre-filter** (33 sites), **none of them holds a member**, and no member file is non-hit; the truly unfiltered `HOME` pass (**85 sites / 50 files**) and the pre-filtered pass (**52 / 29**) give **identical partitions for all 40 members**. The `HOME` limb ships a **positive control** (FR-007/B6), and it is a **limb**, not an inert sub-form — 13 of the 40 members re-pin `HOME`. **Root-parameterised** (FR-009) so every guard behaviour is exercisable against a synthetic tree without editing a real test module, and **prefilter-parameterised** so OD-002 form (a) is one classifier called twice rather than two implementations agreeing with each other. |
| `render_census` / `render_baseline` | The generators. Both outputs carry a header stating they are generated and naming the single regeneration command. `render_baseline` hashes the **sorted `composite_key` set**, never the file bytes. |

## Anti-drift mechanism (the teeth)

An architectural test asserts, by AST, that no module under `tests/` other than `_home_pin_scan.py`
contains a second implementation of the predicate. Concretely: `test_spec_kitty_home_pin_guard.py`,
`test_spec_kitty_home_pin_prefilter.py` and `test_spec_kitty_home_pin_census.py` contain

- **zero** `ast.parse` calls,
- **zero** `ast.NodeVisitor` subclasses,

and obtain everything through `from tests.architectural._home_pin_scan import …`.

This is AST rather than text (C-003), it is cheap, and it converts the §0.8 instruction from an intention
into a red. **The seam is not the import; it is the test that makes the import the only option.**

**And the ban reaches the test modules themselves, which is why synthetic sources go through the seam.**
Every module importing `_home_pin_scan` is subject to the ban — including the positive-control modules,
whose controls must parse a synthetic source. They parse it with **`_home_pin_scan.parse_module` only**;
a control calling `ast.parse` directly would red the very guard it exists to serve, and the cheapest
repair for that red is to exempt the control, which reopens the seam. Stated here because three separate
subtasks ship such controls and each would otherwise resolve it locally.

## WP-0 is its own first consumer

The gate obtains `R` by extracting each window SHA's `tests/` with `git archive` into a temporary directory
and calling `discover(root=<extracted>/tests)`. FR-009's root parameter is therefore **exercised by WP-0
before WP-b depends on it**, and the two-SHA measurement is evidence the seam works rather than a claim
that it will.

## The C-011 evidence artefact is explicitly NOT part of this seam

The independent reproduction at `kitty-specs/isolated-home-pin-guard-r1a-01KZNMA3/research/spec_kitty_home_pin_evidence/`
is checked in **verbatim** and must never be imported by, merged into, or "tidied" against this module. It
is evidence precisely because the party it checks did not write it. `discover()` is compared *against* it;
it is never derived *from* this module.

## Key type — settled

`MemberKey = tuple[str, str, str]` — `(rel_path, enclosing_qualname, normalized_token_line)` — formed **at
the WRITE SITE**, at the boundary, from the `Member` record, and **from the already-parsed tree `discover()`
holds — never by re-reading the file**. `anchoring.py:192-195` swallows `SyntaxError` and returns
`"<module>"`, so re-reading would silently degrade a broken file instead of raising and would leave SC-013's
guarantee holding only on the `parse_module` path. `composite_key_from_file` is used **only** for the
independent live recomputation, where the file is known-parseable because `discover()` just parsed it;
not re-reading also saves a measured 0.19 s per pass. Composition:
`MemberKey = (relpath_posix, *composite_key_from_file(path, lineno))` — the primitive returns a **2-tuple**,
so a direct comparison is a `mypy --strict` type error. Never inside `find_write_sites` or
`key_member`. The bare 2-tuple yields 19 distinct values over the 40 members and is refused; all three
authorities C-012 names already use the 3-tuple for row identity. `Member` also carries `lineno`, which is
**explicitly non-authoritative** and never part of the key.

`discover()` **asserts exactly-one at import over its own output, at MEMBER level**: if two **members**
produce the same `MemberKey`, red at import rather than silently deduplicate. The 3-tuple is non-injective
over the 191 walked **sites** (190 distinct, one class of two) but the **member-level collision population is
0** — the pair's values are `tmp_path/"one"` and `tmp_path/"two"`, so neither is a member. Hazard real,
population 0, one string literal away.

**Do NOT implement this with `assert_descriptor_unique_within_qualname` per member.** Measured under the D-1
rule (`occurrence=None`), it **raises on 11 of the 40**: `code_tokens_by_line` strips string literals, so
`_isolated_home`'s three consecutive `setenv` calls in `tests/cli/commands/test_sync_commands.py`
(`SPEC_KITTY_HOME`, `HOME`, `LOCALAPPDATA`) share one normalized token line while **only one is a member**.
Source-scoped descriptor uniqueness fires on sites the guard does not own. `ContentDescriptor` is retained as
the **diagnostic vehicle** for reporting a collision, never as the uniqueness predicate.

## The gate driver is NOT in this module

The window measurement — git-archive extraction at two SHAs, the rename detector, ±1 stability, banding, the
widening schedule, verdict emission — lives in `tests/architectural/_home_pin_gate.py` and **imports
`discover`**. This module holds **no `subprocess` and no `git`**: collected tests import it under a
6-second budget on every PR. The gate is a consumer, and it owns no predicate, so the
no-second-copy property is preserved.
