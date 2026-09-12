# Research: SymbolKey source_module provenance field (#3552)

Condensed from the four-lens research squad (design / invariants / code-state /
related-work). Full dossiers: `scratchpad/research-3552/`.

## Decision 1 — Field shape

- **Decision**: `source_module: str | None = field(default=None, compare=False)` on the existing `@dataclass(frozen=True) SymbolKey`.
- **Rationale**: `compare=False` excludes it from generated `__eq__` **and** `__hash__`. Empirically verified (probe): keys differing only in `source_module` stay equal, hash-equal, and mutual frozenset members; `as_tuple()` unchanged; `module_path` still discriminates the escalated tier. Satisfies all non-goals by construction — never passed to `body_hash()`, never read by `key_tier()`, content-tier equality stays location-free (D-1 preserved).
- **Alternatives considered**: custom `__eq__`/`__hash__` (more surface, error-prone); a separate provenance sidecar dataclass (splits identity from provenance, more plumbing); comparing field (rejected — false-reds the whole allowlist, R1).

## Decision 2 — Helper consumption

- **Decision**: the #2853 refresh helper reads a `source_module=` kwarg from each allowlist entry, preferring it over the recovered comment; `AllowlistEntry.module_path` returns it directly.
- **Rationale**: `source_module` is a *narrowing* discriminator, not an *exemption* one — `decide()` and the `NEEDS_MODULE_PATH` fail-closed guard need **no logic change**. The exemption relation `final_key in allowlist` is unchanged (resolver-minted keys always have `source_module=None`, outside the membership relation).
- **Alternatives considered**: keeping comment-parsing as a fallback (rejected — whack-a-field; leaves two provenance representations alive).

## Decision 3 — Migration (locked: D2 = all 338)

- **Decision**: backfill `source_module=` on all 338 content-tier entries via a scripted AST rewrite (mirrors `_refresh_dead_symbol_hashes.py::_apply` in-place rewrite); source values from today's parseable provenance comments (all 338 recoverable — the parseable-comment gate passes today).
- **Rationale**: SSOT — one canonical provenance source; unblocks retiring the parse path. Scripted, not hand-edited (highest regression risk).
- **Alternatives considered**: backfill only the 2 genuine duplicates (rejected — leaves comment-parsing live for 336 entries; SSOT gap persists).

## Decision 4 — Comment fate (locked: D1 = delete parse-path, keep comment text)

- **Decision**: delete the 7 machine comment-parse surfaces atomically with the backfill; keep the `# module::Name` comment text as human audit only.
- **Rationale**: single canonical machine source with no fallback; comments remain a human breadcrumb. Atomic (C-004) to avoid a half-retired state (R3).
- **Parse surfaces to retire** (file:line, code-state dossier): `_PROVENANCE_COMMENT_RE` (`test_no_dead_symbols.py:1435`); `_content_tier_entry_lines`/`_comments_by_line` (`:1440-1481`); `test_every_content_tier_entry_has_parseable_provenance_comment` (`:1484-1513`); `_comments_by_row` (`_refresh_dead_symbol_hashes.py:183-194`); `_recover_provenance` + call in `parse_allowlist_entries` (`:237-251`, `:276`); `AllowlistEntry.module_path` comment branch (`:132-141`); `Outcome.UNRECOVERABLE` comment mode (`:88-89`, `:356-360`).

## Decision 5 — Non-goal guards

- **Decision**: pin G1–G6 in `tests/unit/test_symbol_key.py`. Keystone **G6**: `dataclasses.fields(SymbolKey)[...'source_module'].compare is False`. G1/G2 equality+hash+frozenset membership invariance; G3 content-tier stays `is_content_tier`, `key_tier` unescalated; G4 `as_tuple()` excludes the field; G5 resolver-minted key has `source_module is None` and `body_hash` unaffected by a provenance peer.
- **Rationale**: makes the non-goals fail-fast against a future edit (R1/R2/R4).

## Reality-checks correcting the issue text

- Comment formats: "≥3" → **2 today** (trailing 192, preceding 146); #2853 WP01 already normalized the third away. No format-drift work needed.
- Duplicate `bare_name`s: "7" → **8 content-tier groups, only 2 genuine** (`SCHEMA_VERSION`, `register` — same name, different `body_hash`). The other 6 are harmless same-hash re-adds.
- Corpus: 363 entries (338 content-tier, 25 collision-tier).

## Related work (nothing supersedes #3552)

- #3560 (CLOSED) Finding-1: **corrected by the post-plan squad** — a non-comparing `source_module` cannot resolve a *live* same-name/same-body collision (it is invisible to `final_key in allowlist` and tier selection), and it must not (that would forfeit relocation-tolerance, C-002/G3). The Finding-1 `NEEDS_MODULE_PATH` escalation is *correct* and stays; it is resolved by a hand-authored collision-tier `module_path=` entry, orthogonal to this mission. The #3552 acceptance anchor is therefore **comment-independent recovery** (FR-005/SC-002), not collision exemption. The two #3558 Finding-1 tests stay green. #2546 (CLOSED) precursor. #2913 (OPEN) independent. #3552 parented under EPIC #1931.

## Post-plan squad correction (Option A, operator-confirmed)

- The three post-plan lenses converged: FR-005/SC-002 as originally written was unsatisfiable without forbidden auto-escalation. Operator chose **Option A (provenance-only)**: keep the non-hashing field, drop the "no `NEEDS_MODULE_PATH`" claim, re-anchor on comment-independent recovery. Also folded: merge backfill + parse-retirement into one atomic WP (E501/lineno); replace the deleted completeness gate (FR-006) and integrity cross-check (FR-007); add `test_refresh_dead_symbol_hashes.py` to the blast radius; reword (not delete) `Outcome.UNRECOVERABLE`; count allowlist-scoped, never hardcode.

## Supply-chain

- N/A — no dependency added/upgraded/removed (stdlib `dataclasses`/`ast` only).

## Adversarial evidence

- The design was hardened by the four-lens squad pre-plan; the critical risk R1 (comparing field) is closed by construction and pinned by G6. No contested finding dropped. Post-plan and post-tasks adversarial squads will run at those point-cuts.
