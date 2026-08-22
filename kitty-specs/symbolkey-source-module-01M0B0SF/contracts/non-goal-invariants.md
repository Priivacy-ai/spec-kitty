# Contract: source_module non-goal invariants (G1–G6)

These guards live in `tests/unit/test_symbol_key.py` and MUST be present and green.
They pin the #3552 non-goals so a future edit cannot silently violate them.

## G6 — keystone: field is non-comparing

```python
import dataclasses
f = {f.name: f for f in dataclasses.fields(SymbolKey)}["source_module"]
assert f.compare is False
```
Fails the instant someone makes the field comparing (closes critical risk R1).

## G1 — equality ignores source_module

Two `SymbolKey`s equal in `(bare_name, body_hash[, module_path])` but differing in
`source_module` (incl. `None` vs set) compare **equal**.

## G2 — hash / frozenset membership ignores source_module

The same two keys hash-equal and are mutual members of a `frozenset`; a resolver-minted
key with `source_module=None` is `in` an allowlist frozenset whose entry carries a
non-None `source_module` (models `final_key in allowlist`).

## G3 — no tier escalation

A content-tier key (`module_path=None`) with `source_module` set is still
`is_content_tier`, and `key_tier(...)` returns it **unescalated** (no `module_path`
minted from provenance). Preserves D-1 relocation-tolerance (non-goal: no content→collision).

## G4 — as_tuple() excludes source_module

`SymbolKey("Foo", "h", source_module="pkg.mod").as_tuple() == ("Foo", "h")`;
collision-tier → `("Foo", "m", "h")`. Provenance never enters the identity tuple.

## G5 — body_hash unaffected; resolver key has no provenance

`body_hash` is identical with or without `source_module`; a resolver-minted key for a
still-dead symbol has `source_module is None`. Adding a provenance peer does not change
any other key's `body_hash`.

## Acceptance anchor (FR-005 / SC-002) — comment-independent recovery

With `source_module` set on an allowlist entry, deleting or garbling its `# module::Name`
provenance comment does **not** change the module the helper recovers or the refresh
decision it reaches. Red-first constructible against today's comment-parsing path (which
*would* change the decision when the comment is broken).

**Explicitly NOT the anchor (post-plan squad):** a genuine *live* same-`bare_name`+same-`body_hash`
collision still escalates to `NEEDS_MODULE_PATH` — correct, and unchanged by this mission.
`source_module` is `compare=False`, so it cannot enter `final_key in allowlist` and cannot
exempt a live collision (that would forfeit relocation-tolerance, C-002/G3). Such a collision
is resolved by a hand-authored collision-tier `module_path=` entry, orthogonal to `source_module`.
The two #3558 Finding-1 tests (`test_decide_escalates_content_tier_entry_needing_collision_tier`,
`..._escalates_end_to_end`) assert `NEEDS_MODULE_PATH` and **stay green**.

## Completeness + integrity guards (FR-006 / FR-007)

- **FR-006 completeness**: `test_every_content_tier_entry_has_source_module` — fails if any allowlist-scoped content-tier `SymbolKey(...)` call lacks a `source_module=` kwarg. Replaces the deleted parseable-comment gate so SSOT is kept as the corpus grows.
- **FR-007 integrity**: every entry's `source_module` names a module in the **live importable corpus** that declares the symbol (reuse `classify_collisions`' corpus walk; do **not** re-parse the `# module::Name` comment — that would recreate the machine comment-parser SC-004 retires, under a new name). Replaces `_recover_provenance`'s `Name == bare_name` cross-check so drift cannot silently move onto the field. If any comment-adjacent parsing is unavoidable, it must be added by name to SC-004's grep-ban so it can't be cloned silently.
