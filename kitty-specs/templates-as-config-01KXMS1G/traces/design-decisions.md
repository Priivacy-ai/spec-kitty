# Design Decision Trace

## 2026-07-16 — Doctrine artifact is the sole mapping authority

`MissionType.template_set` remains the only authored artifact-key-to-filename mapping. The resolved context exposes an exact lazy/cached projection; profile defaults and filesystem scans cannot populate it.

## 2026-07-16 — Separate filename selection from file precedence

Resolved mission configuration chooses the filename by artifact kind. The existing resolver then selects the winning permitted copy, preserving all five override tiers.

## 2026-07-16 — Known absent configuration fails closed

Null mappings, missing keys, and unresolved mapped filenames produce unavailable/actionable results identifying the mission type and artifact kind. They never inherit software-development content.

## 2026-07-16 — Legacy fallback stays isolated

This mission neither removes nor broadens the meta-less/typeless fallback. Issue #2660 owns that compatibility retirement.

## 2026-07-16 — Parity proof is temporary

The software-development before/after parity scaffold is used only during migration and must be deleted before merge. Doctrine and production-reader behavior tests are the enduring proof.

### 2026-07-16 — Enduring proof after retiring executable parity

Decision: activated readers select templates by semantic artifact keys (`spec`, `plan`) through `resolve_configured_template`; the mapped filename then enters the unchanged five-tier resolver. Neutral/null configurations fail closed with stable diagnostics. The existing typeless plan compatibility branch remains isolated and structurally guarded until its dedicated retirement; it is not available to activated missions. Migration parity is executable but transient: run exact old/new comparisons, preserve the result in traces, then delete the scaffold and retain behavior-level integration/e2e tests. The permanent regression gate uses Python AST structure to require both production readers to call the configured seam, prohibit magic specification selection, and confine the legacy plan selector to a `mission_type is None` guard. Rejected alternatives: permanent dual-path parity code (two authorities that can drift), broad text-count architecture assertions (comments can satisfy them), and synthetic-only fixtures that bypass production readers.

### 2026-07-16 — Mutation-resistant guard semantics and tier ownership

A structural gate must constrain semantics, not merely vocabulary. The typeless compatibility check now requires exactly one `ast.Is` comparison against `None`, with the legacy resolver call inside the guarded body and absent from the else body; a parametrized synthetic mutation proof accepts `is None` and rejects `is not None`. The parity residue exception is narrowed to the permanent guard source and its own same-directory compiled artifact. Other `__pycache__` entries remain scanned; a synthetic `test_template_resolution_parity_scaffold.*.pyc` is detected. Package-default integration assertions must isolate all higher precedence tiers they constrain, so the test owns an empty global home rather than relying on suite order.

### 2026-07-16 — Harden supported boundaries without inventing a security authority

The plan reader takes one strict snapshot of canonical planning metadata. Physically absent metadata retains the explicitly scoped #2660 compatibility path; malformed, non-object, or identity-less present metadata fails before template or lifecycle mutation. The canonical `mission_type` field and supported legacy `mission` field both route through activated configured-template selection. Readable metadata symlinks behave like readable files; broken or self-referential links fail rather than impersonating absence. Configured filenames must be portable safe path segments because doctrine and overlay authors control them, not because a manually constructed resolved context is considered authenticated. Review rejected activation revalidation and exotic alias/setattr mutation tests as disproportionate; live CLI behavior, mapping authority, path containment, and the exact typeless branch are the maintained contract.
