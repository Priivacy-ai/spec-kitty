# Data Model — Drift-Proof Architectural Ratchet Allow-lists

The "data" here is the seed/key shapes of the ratchet allow-lists. No runtime
entities; these are test-infra value objects.

## ContentDescriptor (WS1)
The position-free seed of an allow-list entry.

| Field | Type | Notes |
|-------|------|-------|
| `rel_path` | str | repo-relative path of the guarded module |
| `qualname` | str | enclosing function/class qualname (`<module>` for module-level) |
| `token_substring` | str | matched against the **normalized** token line; unique-within-qualname OR paired with `occurrence` |
| `occurrence` | int \| None | ordinal disambiguator ONLY when ≥2 identical token lines share a qualname (a *count within a scan*, not a file line — permitted by the meta-guard) |
| `rationale` | str | why this exception is sanctioned |

**Invariants**:
- Resolves to **exactly one** live finding (0 or >1 → RED). *(D-1, NFR-005)*
- `token_substring` matches the normalized `code_tokens_by_line` output, never raw source. *(D-2)*
- Carries **no line number** in any authoritative field. *(FR-004)*

## CompositeKey (existing, reused)
`(qualname, token_line)` from `contracts/anchoring.composite_key`.
- Drift-proof against line motion **and** relocation-tolerant (not module-qualified).
- Re-anchors on enclosing rename / same-line token edit (genuine semantic change — C-003).

## RelocationProofSymbolKey (WS2, NEW module)
The dead-symbol allow-list identity.

| Field | Type | Notes |
|-------|------|-------|
| `bare_name` | str | necessary but **never sufficient alone** (D-4) |
| `disambiguator` | str | module-relative + body signal; distinguishes same-name symbols across modules (`ArtifactKind`×3) |

**Invariants**:
- Bare-name-alone is forbidden (would re-blind T004 no-false-negative). *(D-4, FR-007)*
- A behaviour-preserving relocation yields the **same** key (no allow-list edit). *(SC-001)*
- Two distinct same-named symbols in different modules yield **distinct** keys. *(T004)*

## AuthoritativeComparand vs DiagnosticLocator (meta-guard vocabulary)
| Kind | Read for membership/comparison/count? | May carry a line? |
|------|--------------------------------------|-------------------|
| Authoritative comparand (seed/key) | yes | **no** (banned by FR-004) |
| Diagnostic `line:` locator | no (navigation hint only) | yes (permitted, documented) |
| Count-floor baseline | count only, not a position | yes (integer is a count, not a line) |

## StalenessTwinGuard (per migrated gate)
Asserts each descriptor **resolves to exactly one live finding whose composite key
equals the seeded key**. Preserves shrink-only teeth: a routed-away allowance no
longer resolves → the guard reds → the entry must be deleted (even if a *different*
finding exists in the same qualname). *(D-1, FR-003)*

## StandingMetaGuard (FR-004)
Scans all `tests/architectural/` Python seeds + the two YAMLs; fails if any
authoritative comparand carries an integer line component. Enumerates the two
deferred `path::qualname` census allow-lists (FR-014). The single authority for
the DIR-041 generalization.
