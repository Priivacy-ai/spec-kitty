# Pedro — Single-Context-Factory Seam Feasibility

**Author:** python-pedro (profile-loaded; pragmatic implementer, TDD-first, bounded change,
DIR-010 spec-fidelity, DIR-024 locality, ruff/mypy-clean, complexity ≤15).
**Date:** 2026-06-16
**Mission:** `read-path-error-fidelity-adoption-01KV8NPC`
**HEAD context:** `resolution.py` 823 LOC, `context.py` 276 LOC.
**Question:** Can a minimal *single context factory seam* — one construction point both read and
(future) write draw from — be laid in THIS bounded mission, without dragging in the deferred
write-side topology rewrite (#1716/#1878), respecting C-001 (adopt, don't build a new authority)
and NFR-005 (bounded conflict surface)?

**Note on inputs:** `alphonso-symmetry-design.md` was NOT yet present when this was written;
this assessment is grounded on `randy-adoption-census.md`, `alphonso-ssot-intent.md`, and direct
code reading of `mission_runtime/{context,resolution}.py` + `lanes/branch_naming.py`. If
alphonso's symmetry design lands and contradicts the "construction is already centralized"
finding below, re-reconcile — but the code evidence is unambiguous (one constructor site).

---

## Executive answer (lead)

**A bounded factory seam is FEASIBLE in this mission — and it is *smaller* than the operator
fears, because construction is ALREADY single-sited.** There is exactly **one**
`ExecutionContext(...)` constructor call in production (`resolution.py:739`), and exactly **one**
fragment-assembly path (`_assemble_core_fragments`), which `resolve_placement_only` already
shares. The "one factory" the operator wants is therefore not a *new* thing to build — it is the
existing `_assemble_core_fragments` + the `ExecutionContext(...)` construction site, which need
to be **named, frozen, and made the sole construction door** rather than re-architected.

**IC-01 ABSORBS this.** Re-scope IC-01 from "freeze + assert invariant" to "**establish the named
single factory + freeze + assert invariant**", staying entirely within its already-owned files
(`mission_runtime/{context,resolution}.py`) and ≤ ~7 subtasks. No new WP. No new owned files. No
new conflict surface (NFR-005 preserved — IC-01 already solely owns both files).

**Est. size:** ~40–70 LOC net in `resolution.py` (mostly a moved/renamed extraction, not new
logic) + ~6 LOC `frozen=True` + invariant in `context.py`; **5–6 subtasks**; risk LOW-MEDIUM
(the one real risk — the post-construction WP-field mutation at `:800-808` — is INSIDE the
factory's own file and is the exact thing freezing forces us to fix, which the plan already
anticipates as IC-01's named risk).

---

## 1. Minimal seam proposal

### 1.1 The decisive code fact — construction is already single-sited

`grep` for `ExecutionContext(` across `src/` (non-test) returns **one** production hit:
`resolution.py:739`, inside `resolve_action_context`. (`core/context_validation.py:41` is an
unrelated `class ExecutionContext(StrEnum)` — a different symbol, not the value object.)

`grep` for post-construction mutation `context.<field> =` returns hits **only** at
`resolution.py:800-808` — i.e. the WP-bearing branch of `resolve_action_context` mutating the
context it itself just built. The only *external* reference, `workspace/context.py:452`, is a
**read** (`if context.branch_name == branch_name`), not a write.

So the topology is already:

```
resolve_action_context ─┐
                        ├─> _assemble_core_fragments  (the ONE fragment builder)
resolve_placement_only ─┘        └─> IdentityFragment.derive / branch_naming collaborators
                                  └─> CommitTarget / Branch/Status/Workspace fragments
resolve_action_context ──> ExecutionContext(...)   (the ONE constructor site, :739)
                       └─> :800-808 post-construction WP-field mutation  (the only mutator)
```

The operator's "single factory" already exists in substance. What is missing is (a) a **named**
function that *is* the construction door (today it is an inline `ExecutionContext(...)` literal
buried mid-function), and (b) the **freeze** that makes "draw from the factory" enforceable
rather than conventional.

### 1.2 The seam: extract + name `build_execution_context`, freeze the composite

Extract the construction (lines `:739-808`) into a private, named, single builder and make both
the base path and the WP-bearing path produce the context through it. Because the dataclass
becomes `frozen=True`, the `:800-808` mutation must be folded INTO construction (build once, with
all fields) — which is the natural, correct shape.

**Signature (private factory, the named construction door):**

```python
# mission_runtime/resolution.py

def build_execution_context(
    *,
    action: ActionName,
    mission_slug: str,
    feature_dir: Path,
    target_branch: str,
    fragments: _AssembledFragments,        # identity/branch_ref/status_surface/workspace/...
    commands: dict[str, str],
    wp_fields: _WorkPackageFields | None = None,   # None for mission-lifecycle actions
) -> ExecutionContext:
    """The SINGLE construction door for ExecutionContext (C-CTX-1 / FR-009).

    Asserts the build-time invariant `target_branch == branch_ref.target_branch`
    (reject-on-mismatch, never normalize — a mismatch is a builder bug) and
    constructs the frozen composite in ONE shot. No caller constructs an
    ExecutionContext directly; no caller mutates one post-build.
    """
    if fragments.branch_ref.target_branch != target_branch:
        raise ActionContextError(
            "CONTEXT_INVARIANT_VIOLATED",
            f"target_branch {target_branch!r} != branch_ref.target_branch "
            f"{fragments.branch_ref.target_branch!r} (single-derivation, FR-012).",
        )
    return ExecutionContext(
        action=action,
        mission_slug=mission_slug,
        feature_dir=str(feature_dir),
        target_branch=target_branch,
        detection_method="explicit",
        commands=commands,
        identity=fragments.identity,
        branch_ref=fragments.branch_ref,
        status_surface=fragments.status_surface,
        workspace=fragments.workspace,
        artifact_placement=fragments.artifact_placement,
        prompt_source=fragments.prompt_source,
        **( _wp_kwargs(wp_fields) if wp_fields else {} ),
    )
```

`resolve_action_context` then becomes a thin orchestrator: resolve slug + target_branch + WP
state (the *read* side, unchanged), package them into the small param objects, and call
`build_execution_context` **once** at the end — for BOTH the lifecycle branch and the WP-bearing
branch. The current "construct base, then mutate WP fields" pattern collapses into "gather WP
fields, then construct once".

**Why this is the right "one factory":**
- `resolve_placement_only` already shares `_assemble_core_fragments`; this proposal simply makes
  the *context-object* construction (not just the placement projection) share a single named
  door too. Read path (`resolve_action_context`) and the future write path both call
  `build_execution_context` → same builder, same invariant, same naming/identity/path logic
  (which already lives in the `_assemble_*` helpers calling `branch_naming.py`).
- It does NOT touch `branch_naming.py`: the factory **calls** those composers (as collaborators,
  exactly as `_assemble_core_fragments` already does via `IdentityFragment.derive` /
  `mid8_from_slug`). It does not absorb them — that is mission #2012's territory and stays OUT.

### 1.3 Owned files (unchanged from IC-01's existing ownership)

| File | Change | Est. LOC |
|------|--------|----------|
| `src/mission_runtime/context.py` | `@dataclass` → `@dataclass(frozen=True)`; optional `__post_init__` cross-field assert (or assert in factory only) | ~6 |
| `src/mission_runtime/resolution.py` | Extract `build_execution_context` + two tiny param dataclasses (`_AssembledFragments`, `_WorkPackageFields`); rewrite the `:739-808` block to gather-then-build-once; route both branches through the door | ~40–60 net (mostly moved code, not new) |

**No other production files change.** This is exactly IC-01's existing affected-surface set
(`plan.md:97`). NFR-005's zero-file-overlap is preserved.

### 1.4 Subtasks (≤ ~7, TDD-first)

1. **(test-first)** Add `test_build_execution_context_is_single_construction_door` — assert
   `resolve_action_context` and (a direct call to) `build_execution_context` yield equivalent
   composites for a topology-true fixture; assert mismatch raises `CONTEXT_INVARIANT_VIOLATED`.
2. **(test-first)** Add `test_execution_context_is_frozen` — `dataclasses.FrozenInstanceError`
   on attribute set; and a regression asserting `target_branch == branch_ref.target_branch`.
3. Freeze the dataclass (`frozen=True`) in `context.py`.
4. Extract `build_execution_context` + `_AssembledFragments` / `_WorkPackageFields` param
   objects in `resolution.py`.
5. Rewrite `resolve_action_context` WP-bearing branch to gather WP fields and construct ONCE
   through the factory (delete the `:800-808` mutation).
6. Run the existing `mission_runtime` + `tests/agent/test_context_validation_unit.py` +
   topology suites; fix any surfaced mutator (expected: none outside `:800-808`).

(An optional 7th: a one-line docstring/`__all__`-internal note naming the door as canonical.
`build_execution_context` stays **private** to the package — it does NOT join the public
`__all__`, because the public surface is `resolve_action_context` / `resolve_placement_only`,
per ADR-06-07-1's lean-four-symbol API. Adding a public factory would *widen* the surface and
fight that ADR — keep it internal.)

---

## 2. Does IC-01 absorb this? — YES, re-scope (no new WP)

**Current IC-01** (`plan.md:94-99`): "Freeze the `ExecutionContext` composite and assert
`context.target_branch == branch_ref.target_branch` at build (reject-on-mismatch)." Owned files:
`mission_runtime/{context,resolution}.py`. Risk already named: "freezing may surface a downstream
mutator — that mutator is itself a bug to fix."

**Re-scope IC-01 to:** "**Establish `build_execution_context` as the single named construction
door, freeze the composite, and assert the build-time invariant.**"

This is the *natural completion* of the existing IC-01, not an expansion:
- **Same owned files** — `context.py` + `resolution.py`. No new surface; NFR-005 intact.
- **The freeze REQUIRES the factory.** You cannot freeze `ExecutionContext` without resolving
  the `:800-808` post-construction mutation, and the only clean resolution is "construct once
  with all fields" — i.e. funnel through one builder. So the factory is not bolted on; it is the
  *mechanism* by which IC-01's freeze is achievable. IC-01 already owns the mutation site as its
  named risk.
- **The invariant assertion is the factory's body.** "Assert `target_branch ==
  branch_ref.target_branch` at build" is literally one `if` in `build_execution_context`. The
  factory is where the assertion lives.

**Subtask budget:** the re-scoped IC-01 is the 5–6 subtasks in §1.4 — within the ≤ ~7 bound. It
does NOT need its own WP, and splitting it OUT would be worse: a separate "factory" WP would
either (a) share `resolution.py` with the freeze WP → reintroduce file overlap (violates NFR-005),
or (b) freeze-without-factory first → impossible (the `:800-808` mutator blocks the freeze). The
two are inseparable; keep them one IC.

**Recommendation: ABSORB into IC-01, re-titled.** Update IC-01 Purpose to name the factory.

---

## 3. Risk / blast radius

**What breaks if construction is funneled through one factory?**
- **Internal-only blast radius.** The only post-construction mutator is `resolution.py:800-808`,
  inside the factory's own file and owned by IC-01. No external module constructs or mutates an
  `ExecutionContext`. The single external touch (`workspace/context.py:452`) is a read — frozen
  reads are unaffected. So funneling construction breaks **nothing outside `resolution.py`**.
- **`resolve_placement_only` is untouched** — it never constructed an `ExecutionContext` (it
  projects a `CommitTarget` from `_assemble_core_fragments`). It already shares the builder; this
  proposal does not change its path.
- **Serialization (`to_dict`) unaffected** — `to_dict` reads fields; frozen dataclasses serialize
  identically. NFR-001 byte-shape preserved.

**TDD-ability with topology-true fixtures: YES.** The factory is a pure function over already-
resolved inputs (fragments + WP fields) — exactly the `test-scaffolding-as-design-smell` ideal: it
needs no real git/files to test the invariant + construction. The slug/target_branch *resolution*
(the part that needs topology fixtures) stays in `resolve_action_context` and is already covered.
The new tests in §1.4 are pure-input unit tests (invariant raise, frozen-ness) plus one
equivalence test through the existing topology fixtures. No mock expansion.

**Complexity / mypy:**
- `resolve_action_context` complexity should DROP, not rise: replacing the inline 9-line mutation
  block (`:800-808`) with a single `build_execution_context(...)` call removes statements from a
  function already near the ceiling. The cyclomatic count is unchanged (same branches); statement
  count falls. Keep `build_execution_context` itself ≤15 (it is one `if` + one constructor →
  trivial).
- mypy: the two small param dataclasses (`_AssembledFragments`, `_WorkPackageFields`) are fully
  typed; `**_wp_kwargs(...)` needs a typed helper returning `dict[str, Any]` or — cleaner — pass
  WP fields explicitly as keyword args to avoid `**`-splat typing friction. Prefer explicit
  kwargs over splat to keep mypy strict-clean (no `# type: ignore`).
- The `frozen=True` flip: mutable default `field(default_factory=list)` for `dependencies` /
  `commands` / `warnings` is compatible with `frozen=True` (frozen forbids *reassignment*, not
  mutable-default construction). No mypy issue. (Note: a frozen dataclass with mutable
  *contents* — e.g. `dependencies.append(...)` — would still mutate the list in place; if any
  consumer does that it is a latent bug, but the census found none. Tests in §1.4 guard it.)

**One genuine MEDIUM risk:** a hidden mutator outside the grep (e.g. via `setattr` or
`dataclasses.replace`). Mitigation: the §1.4 frozen-ness test + a full `pytest tests/agent
tests/integration -k "context or runtime"` pass will surface any. The census (randy) +
alphonso's read both independently conclude the API is coherent and the only mutation is the
post-build WP write — so the probability is low.

---

## 4. Explicit NON-goals (stay deferred — do NOT pull into this mission)

1. **Write-side coordination topology rewrite (#1716/#1878).** alphonso confirms ADR-06-07-1 §4
   scopes this surface to Stage-C (read-side façade) and puts the Stage-B operation/commit-seam
   OUT (C-008). The factory must NOT grow write-routing, commit-target *selection* logic, or a
   coord-vs-primary write decision. It constructs context; it does not decide where writes land.
   The "future write path draws from the same factory" is a *direction*, realized in #1878 — this
   mission only makes the door exist and be the sole read-side constructor.
2. **No public factory symbol.** `build_execution_context` stays package-private. Do NOT add it
   to `mission_runtime.__all__` — the public API is the lean four symbols (ADR-06-07-1). Widening
   the surface is a different decision and would fight the ADR.
3. **No `branch_naming.py` change.** The factory CALLS the naming/identity composers as
   collaborators (already does, transitively). Absorbing them is mission #2012 (AST ratchet +
   naming SSOT) and stays OUT — `plan.md:186-187` already excludes it.
4. **No flat-substrate retirement / fragment-model reduction.** randy proposes RETIRE-WIDE of the
   unconsumed fragments (~200 LOC). That is a larger #1619 grain and is explicitly OUT
   (`plan.md:185`). The factory constructs whatever fragments the builder assembles today,
   unchanged — do NOT delete fragments under cover of the freeze. (If anything, the freeze makes
   a *later* reduction safer, but that is a follow-on, not this mission.)
5. **No second/parallel resolver.** C-001: the factory is the *existing* construction site named
   and frozen, not a new authority. Verification-by-deletion: after the seam, there is still
   exactly one `ExecutionContext(...)` call site in production.

---

## Bottom line

- **Feasible in THIS mission? YES.** Construction is already single-sited; the work is to *name*
  the door (`build_execution_context`), *freeze* the composite, and *fold* the one post-build
  mutation into the single construction. It is a bounded extraction, not an architecture build —
  fully consistent with C-001 (adopt) and NFR-005 (bounded surface).
- **IC-01 absorbs it? YES** — re-title IC-01 to "establish the single factory + freeze +
  invariant", same two owned files, 5–6 subtasks (≤7 bound). No new WP; splitting it out would
  reintroduce file overlap or make the freeze impossible.
- **Est. size:** ~6 LOC `context.py` + ~40–60 net LOC `resolution.py` (mostly moved code);
  5–6 TDD subtasks; LOW-MEDIUM risk, blast radius confined to `resolution.py`.
