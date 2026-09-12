# Carried forward from WP04's inventory — two surfaces WP05 and WP06 must know about

WP04 was approved at round 2 with one MEDIUM carried rather than spending a third round. This is
that finding, written where the two packages that consume the inventory will look. Established by
WP04's independent reviewer, which walked two frames deeper than the document's own trace.

## The read-set closure stops one frame short

`process-global-inventory-3115.md:159-165` states that *"the **only** state outside the test's own
mocks that this path reads"* is (a) the filesystem and (b) the registered
`_egress_consent_resolver` singleton. That closure was derived to the resolver frame and no further.

Below it, the executed path continues: the resolver slot holds a callable
(`sync/__init__.py:327-372`) whose body reaches `resolve_checkout_sync_routing_readonly` and
`consented_project_uuids` → `resolve_project_consent` (`consent.py:608`) → iterating
`PROJECT_CONSENT_PRECEDENCE` (`consent.py:104`), dispatched through **`LEVEL_RESOLVERS`
(`consent.py:581`) — a module-level mutable `dict`** → `_answer_project_local` /
`_answer_machine_index` (`:522-534`) → `SyncConfig().read_project_consent(uuid)`, the
**machine-global uuid-keyed consent index**, a `SPEC_KITTY_HOME`-derived file outside `tmp_path`.

Neither surface is an inventory entry.

## Why no verdict changed — and the condition that would change them

The reviewer checked each reason rather than assuming:

1. **`_answer_project_local` is level 1 and answers for `test_429`**, because E22's second limb —
   `_compat_init:150-151` injecting `project_root=_consenting_project_root()` — writes
   `.kittify/config.yaml` with `sync: enabled: true`. **The chain short-circuits before
   `_answer_machine_index` reads anything.**
2. `_answer_env` (`consent.py:561-571`) returns `None` **unconditionally** and reads no environment
   variable at all — so `SPEC_KITTY_ENABLE_SAAS_SYNC` appears in the chain but is never consulted.
3. All 15 machine-index-writing files set `SPEC_KITTY_HOME` themselves.
4. Nothing in the cone mutates `LEVEL_RESOLVERS`; the two cone imports
   (`test_consent_read_fault_3030.py:42-43`) are read-only membership assertions.

**The 1 `depends` / 52 `does not depend` / 0 `undetermined` split stands.**

## What WP05 needs to know

WP05's guard is scoped to **this inventory**, so an entry absent here is a global the guard will
never watch. Two surfaces sit on `test_429`'s chokepoint path and are absent:

- **`consent.py:581 LEVEL_RESOLVERS`** — squarely inside FR-006's definition (module-level mutable,
  worker-process lifetime), but it lives in `src/` and **is not mutated by the cone**, so no cone
  test can leak it. Watching it is cheap and would be defensible.
- **The machine-global consent index** — written **94 times across 15 files** in `tests/sync/` via
  `set_project_consent()` (`consent.py:447-451`). Its lifetime is the **machine**, not the worker
  process, so it falls outside FR-006's own definition and outside what an in-process snapshot guard
  can watch at all. **Whether WP05's guard should extend to machine-lifetime state is a scope
  question, not a defect** — decide it deliberately and record the decision either way.

## What WP06 needs to know

**E22's second limb is what keeps the consent chain short-circuiting at level 1.** WP06 inherits
only the first limb if that row is read carelessly. If the `project_root` injection ever changes,
`_answer_machine_index` comes into play, the 94 cone write sites become reachable, and several
`does not depend` verdicts would need re-deriving before they could be relied on.

## One evidence-attribution error, corrected here

E20's evidence cell attributes its conclusion to a grep of the wrong file — it cites
`egress_consent.py:147-190` (the wrapper) as having zero `os.environ`/`getenv` references, when the
resolver body is `sync/__init__.py:327-372` and the chain is `sync/consent.py`. **The conclusion is
true** — the reviewer verified `_answer_env` reads nothing — **but it is true for a reason the
document did not check.** Recorded because that is the round-1 HIGH in miniature, in a document
whose subject is the gap between a verdict and its evidence.

## Limit of the reviewer's own check

The reviewer walked two frames deeper than the document but stopped at
`_answer_project_local`/`_answer_machine_index`, without walking
`resolve_checkout_sync_routing_readonly`'s full body or `SyncConfig`'s constructor. It flagged that
rather than letting its own depth become the new asserted bound. **A further global could exist
below that closure.**
