# Phase 0 Research: Pack-Path Portability & Language-Scope Authority

All findings below come from the pre-spec investigation squad (4 profile-loaded lenses, read-only, live-evidence-grounded against this checkout) rather than fresh research — no [NEEDS CLARIFICATION] markers remain after the Decision Moment Protocol resolved the three open product decisions during `/spec-kitty.specify`.

## WP1 — Pack-path env-var indirection

**Decision**: Expand `${VAR}`/`$VAR` tokens via `os.path.expandvars`, composed with the existing `os.path.expanduser` tilde-expansion, at `effective_root()` resolution time — not inside the `mode="before"` `_expand_tilde` field validator that mutates the stored model value.

**Rationale**: `_pack_to_yaml_dict` (`org_pack_config.py:342-355`) re-serializes `str(pack.local_path)` on every `save_pack_registry` call. If expansion happens at construction (inside the validator), the stored field becomes the machine-local absolute path, and the very next save freezes that absolute path back into `.kittify/config.yaml` — destroying the portability the fix exists to add. This was independently confirmed by two squad lenses (architect-alphonso via static trace of the round-trip; debugger-debbie via live reproduction) and is the single highest-severity finding from the investigation.

**Alternatives considered**:
- *Expand inside `_expand_tilde` at construction* (debugger-debbie's initial framing, before her own live reproduction surfaced the round-trip contradiction) — rejected: corrupts config on save, as above.
- *Expand only in the CLI layer before constructing `OrgPackConfig`* — rejected: would require every one of the ~9 `resolve_org_roots` call sites (`charter.*` and `specify_cli.*`) to remember to pre-expand, reintroducing a split-brain (violates DIRECTIVE_044 single-seam requirement); the shared model's own `effective_root()` is the correct single seam because both import surfaces already funnel through it.

**Decision**: Env-var name is `SPEC_KITTY_PACK_HOME` (locked via decision `01KWY7B134NS9KEC9SWAJ8M0CH`).

**Rationale**: Matches the existing `SPEC_KITTY_HOME` / `SPEC_KITTY_TEMPLATE_ROOT` naming convention already documented in `docs/api/environment-variables.md`; the upstream issue explicitly deferred this choice ("happy to defer to whatever's most consistent with existing env vars/config keys").

**Alternatives considered**: `PACK_INSTALLATION_BASE` (the issue's own example) — rejected as inconsistent with the `SPEC_KITTY_*` namespace convention used everywhere else in the project.

**Decision**: Unset/empty referenced variables fail closed with a named error (locked via decision `01KWY7B9DFRWNM7WV0GK1XG6K1`).

**Rationale**: `os.path.expandvars`'s stdlib default (silent literal passthrough of `${UNSET}`) would reintroduce exactly the "looks fixed but isn't" failure mode the debugger lens flagged — a config with an unset var would silently resolve to a nonsense path rather than surfacing an actionable error. The existing `OrgPackMissingError` pattern (`specify_cli/doctrine/config.py:30-39`, surfaced via `assert_pack_local_paths_exist`) is the established fail-closed idiom for this exact class of "pack path doesn't resolve" problem — doctrine-daphne confirmed this is the pattern to extend, not invent a new one.

**Alternatives considered**: Literal passthrough (stdlib default) and warn-and-literal — both rejected for silently degrading the org DRG layer (doctrine-daphne's finding: `effective_root()` feeds `load_org_drg()` and `charter activate`/`cascade`; a silently-wrong root would silently drop org directives/profiles from activation with no operator-visible signal).

**Decision**: Env-var expansion scope is `local_path` only; `subdir` is unaffected.

**Rationale**: `_validate_subdir` (`org_pack_config.py:76-115`) validates the subdir string as stored — raw, pre-expansion — rejecting `..` and absolute forms. Debugger-debbie's live reproduction confirmed `subdir` is stored literally unexpanded today; expanding it would validate the wrong (pre-expansion) string while resolving the wrong (post-expansion) path, opening an escape window around the existing containment guard (`effective_root()` lines 144-155).

## WP2 — Language-scope authority

**Decision**: Persist a structured, machine-readable language set on the compiled charter at compile time (`charter generate`/`charter sync`), and have runtime resolution (`infer_repo_languages` or its replacement) read that structured value as the canonical source. Interview-transcript extraction remains only as a creation-time-only fallback for the narrow pre-compile window (locked via decision `01KWY7BHZDKJ8PKZBPY2C6BXHS`, selecting deep unification over a minimal precedence flip).

**Rationale**: doctrine-daphne's lens identified that `extract_declared_languages()` is already invoked canonically at compile time (`src/charter/compiler.py:99`, over interview answers) — `infer_repo_languages`'s runtime re-invocation of the same extractor over the raw transcript is a textbook DIRECTIVE_044 split-brain (Rule 2: unification, not parity-preserving branch reordering). A minimal branch-flip (charter-first, interview-fallback, both still re-running regex extraction at runtime) would fix the reported drift but leave the split-brain in place — the next similar bug (e.g. a third caller adding its own precedence logic) remains possible. Persisting a structured field removes the runtime re-derivation entirely.

**Alternatives considered**: Minimal precedence flip inside `infer_repo_languages` (the issue's own "not prescriptive" suggested direction, and architect-alphonso's and debugger-debbie's baseline recommendation) — viable and lower-risk, but explicitly superseded by the operator's decision to take the deeper, doctrine-correct unification given this is a full mission with room for the more durable fix.

**Backward compatibility**: Charters compiled before this change lack the structured field. Runtime resolution falls back to interview-transcript extraction only when no structured value is present (FR-010) — this preserves current behavior for un-recompiled projects without requiring a forced migration step.

**Regression test correction**: `tests/charter/test_language_scope.py::test_infer_repo_languages_prefers_interview_answers` (lines 21-36) asserts today's buggy precedence as its contract. Per DIRECTIVE_034/041 (tests as scaffold, not friction — and the standing test-remediation/red-first discipline), this test must be run and observed red against the corrected implementation first (confirming it currently encodes the bug), then inverted to assert charter-authoritative resolution on disagreement — not deleted or weakened.

## Open items

None. `spec-kitty agent decision verify --mission pack-path-env-indirection-01KWY79W` returned `status: clean` with zero deferred/marker findings.
