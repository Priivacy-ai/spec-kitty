# Gate-Conversion Contract — refactor-stable-gate-substrate-01KWK3FY

Binding rules for IC-01 (and the identity halves of IC-02/03). Deviations require a
recorded design-decision entry.

1. **Design-P only**: the stored comparand is the tool-derived
   `(rel_path, qualname, token)`; the live side re-derives and checks membership.
   Seed re-derivation at load (Design-S) is FORBIDDEN for new conversions (empirically
   fails both NFR-001 halves — research.md D1).
2. **Freeze provenance**: tokens enter the allowlist/inventory only via the fail-closed
   converter (or the gate's own emit-on-miss output) — never typed by hand. The
   converter aborts loudly on: module-scope resolution, empty token, unparseable file.
3. **Line demotion**: `line:` fields survive as non-authoritative locators; NO
   comparison, set-membership, or count logic may read them. Violation messages may
   print them.
4. **Theater triad mandatory** (per data-model.md): drift-green / content-red /
   new-offender-red, all driving the CI entry points. A missing leg is a review reject.
5. **Same-WP completeness**: type changes propagate to every constructor (incl. the
   ~6 int-line test constructors and `derive_live_key` unit tests) in the same WP —
   `mypy --strict` on the file must be clean at every commit.
6. **Staleness semantics**: a frozen key with no live match = gate FAILURE with
   "evict or re-approve" guidance (never auto-eviction, never silent).
7. **Refactor-stable conformance** (C-001): the conversion introduces no positive
   literal-presence scans and no size checks; the gate's negative invariant (the
   forbidden-call scan) is unchanged in meaning.
