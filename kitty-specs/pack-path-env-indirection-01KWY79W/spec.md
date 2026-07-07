# Feature Specification: Pack-Path Portability & Language-Scope Authority

**Mission**: `pack-path-env-indirection-01KWY79W`
**Mission Type**: software-dev
**Target Branch**: `issue/2437-env-var-pack-paths`
**Upstream**: [Priivacy-ai/spec-kitty#2437](https://github.com/Priivacy-ai/spec-kitty/issues/2437) (anchor) + [Priivacy-ai/spec-kitty#2395](https://github.com/Priivacy-ai/spec-kitty/issues/2395) (folded in)
**Created**: 2026-07-07

## Purpose TLDR

Make org doctrine pack paths portable across machines/CI via env-var indirection, and make doctrine language-scope filtering read from the compiled charter instead of a stale interview snapshot.

## Purpose Context

Two independent, upstream-confirmed correctness/portability defects live in the same domain (charter/doctrine config resolution) but touch disjoint code, tests, and authority chains. A pre-spec investigation squad (architect, debugger, doctrine-integrity, and planning lenses, each profile-loaded against the live codebase) confirmed both defects by direct reproduction and recommended folding them into one mission as two independent work packages. This spec captures that grounded scope so implementation does not need to re-derive it.

## Intent Summary

- **Primary actor (WP1)**: An operator/team configuring `doctrine.org.packs[].local_path` in `.kittify/config.yaml` who needs the path to resolve identically across different developer machines and CI runners so the config file is safe to commit.
- **Primary actor (WP2)**: An operator who edits `.kittify/charter/charter.md` after initial charter creation (adding/removing a governed language) without re-running the discovery interview, and expects doctrine language-scope filtering to reflect the current charter, not the stale interview transcript.
- **Rule that must always hold (WP1)**: The stored `local_path` config value is never mutated by resolution — expansion happens read-side at `effective_root()`, so a template like `${SPEC_KITTY_PACK_HOME}/org-pack` survives a load → save → load round-trip unchanged. An unset referenced variable fails closed with a named, operator-actionable error; it never silently resolves to a passthrough literal.
- **Rule that must always hold (WP2)**: Runtime language-scope inference for doctrine artefact filtering reads a single canonical source (the compiled charter), not a re-derivation from the raw creation-time interview transcript. The interview transcript is creation-time input only.
- **Explicit assumptions**: No org pack is configured in the primary spec-kitty repo itself; both fixes are exercised via unit/integration tests with fixture repos, not a live org-pack dependency. `#2213` (a distinct seam-disagreement bug about *who calls* `infer_repo_languages`, not precedence) is explicitly out of scope.

## Domain Language

| Term | Definition | Avoid |
|---|---|---|
| Pack path | The resolved filesystem root of a configured org doctrine pack (`OrgPackConfig.effective_root()`) | "pack location" (ambiguous with pack identity) |
| Env-var indirection | Runtime expansion of `${VAR}` / `$VAR` tokens inside a configured path, resolved against the process environment at read time | "variable substitution" (too generic) |
| Compiled charter | The current, generated `.kittify/charter/charter.md` (and its structured artefacts) reflecting the latest `charter generate`/`charter sync` | "the charter file" (ambiguous with the interview) |
| Interview answers | The creation-time snapshot at `.kittify/charter/interview/answers.yaml`, captured once at charter generation and not re-synced on later charter edits | "charter answers" (confusable with compiled charter) |
| Active languages | The resolved set of languages used to filter language-scoped doctrine artefacts (`active_languages` on `DoctrineService`) | "project languages" (undefined elsewhere in doctrine) |

## User Scenarios & Testing

### WP1 — Pack-path env-var indirection

**Primary scenario**: An operator writes `doctrine.org.packs[].local_path: "${SPEC_KITTY_PACK_HOME}/acme-doctrine"` in `.kittify/config.yaml` and commits it. Teammates and CI, each with their own `SPEC_KITTY_PACK_HOME` set in their environment, run `spec-kitty doctrine fetch` / `spec-kitty doctor doctrine` and the pack resolves correctly against their own machine-local path — with no edits to the committed config.

**Exception path**: `SPEC_KITTY_PACK_HOME` is unset (or empty) in the operator's environment. Resolution fails closed with a named error identifying the missing variable and the configured pack name — consistent with the existing `OrgPackMissingError` pattern — rather than silently treating `${SPEC_KITTY_PACK_HOME}` as a literal directory name or silently producing an empty org layer.

**Round-trip scenario**: The registry is loaded, another field is mutated (e.g. via `spec-kitty agent config add`), and `save_pack_registry` writes the config back to disk. The `local_path` value on disk after the save is still the literal `${SPEC_KITTY_PACK_HOME}/acme-doctrine` template — not the machine-local absolute path that the current process resolved it to.

**Regression scenarios**: A literal absolute path (no `${...}`) resolves unchanged. A `~`-prefixed path still tilde-expands as it does today. The legacy `organisation_packs[].path` shape also expands env vars (same underlying `OrgPackConfig`).

**Security boundary scenario**: A `subdir` value is never subject to env-var expansion; it continues to be validated as a literal relative path with no `..` and no absolute form, before and after this change.

### WP2 — Language-scope authority (charter-first)

**Primary scenario**: An operator initially runs the discovery interview declaring Python as the governed language, generates the charter, then later edits `charter.md` directly to add TypeScript (without re-running the interview). The next `spec-kitty charter context` (or any doctrine operation consuming `active_languages`) reflects both Python and TypeScript, sourced from the current compiled charter — not from the stale interview transcript.

**Exception / disagreement scenario**: The interview transcript and the compiled charter name different languages (interview says Python only; charter.md has since been edited to say TypeScript only). The compiled charter wins. This is the exact scenario the current code gets wrong and that regression coverage must prove.

**Fallback scenario**: No compiled charter exists yet (fresh project, interview completed but charter not yet generated). Interview answers remain a legitimate creation-time-only fallback input in that narrow window.

**Out of scope**: `#2213` (seam-disagreement over which caller invokes `infer_repo_languages`) is not addressed by this mission.

## Functional Requirements

| ID | Description | Status |
|---|---|---|
| FR-001 | `OrgPackConfig` resolution MUST expand `${VAR}` and `$VAR` environment-variable tokens inside `local_path` at read/resolution time (`effective_root()`), while the stored/serialized `local_path` value remains the literal, unexpanded template. | Draft |
| FR-002 | Env-var expansion MUST be applied identically to the canonical `doctrine.org.packs[].local_path` shape and the legacy `organisation_packs[].path` shape, since both parse into the same `OrgPackConfig` model. | Draft |
| FR-003 | If a referenced environment variable is unset (or empty) at resolution time, resolution MUST fail closed with a named, operator-actionable error identifying the missing variable and the configured pack name, consistent with the existing `OrgPackMissingError` pattern. It MUST NOT silently pass through the literal token or silently produce an empty org layer. | Draft |
| FR-004 | Tilde (`~`) expansion MUST continue to work exactly as today, composed correctly with env-var expansion (both applied before the `is_absolute()` classification in `effective_root()`). | Draft |
| FR-005 | A literal absolute path with no `${...}`/`~` tokens MUST resolve unchanged (no regression). | Draft |
| FR-006 | Env-var expansion MUST be scoped to `local_path` only. The `subdir` field's existing validation (relative-only, no `..`, no absolute form) MUST NOT be weakened or bypassed by this change. | Draft |
| FR-007 | The symlink-escape containment check in `effective_root()` MUST still correctly fence the resolved `subdir` candidate against the resolved (post-expansion) `local_path` root — expansion order must not create an escape window. | Draft |
| FR-008 | `infer_repo_languages` (or its replacement) MUST resolve the governed language set from the compiled charter as the canonical runtime source, per DIRECTIVE_044 unification, rather than re-deriving from the raw interview transcript at runtime. | Draft |
| FR-009 | The compiled charter MUST persist a structured, machine-readable language set at compile time (`charter generate`/`charter sync`), so runtime consumers read a resolved value instead of re-running free-text regex extraction against `charter.md` prose. | Draft |
| FR-010 | When the compiled charter has no structured language set yet (pre-existing projects, or the narrow window between interview completion and first charter generation), resolution MUST fall back to the interview transcript as a creation-time-only input — never as a competing runtime authority once a compiled value exists. | Draft |
| FR-011 | All existing callers of `infer_repo_languages` (`src/charter/context.py`, `src/charter/compact.py`) MUST consume the corrected resolution without requiring per-caller precedence logic (single canonical seam). | Draft |
| FR-012 | The existing test that pins interview-preferred precedence (`tests/charter/test_language_scope.py::test_infer_repo_languages_prefers_interview_answers`) MUST be corrected to assert charter-authoritative behavior on disagreement, not deleted. | Draft |

## Non-Functional Requirements

| ID | Description | Status |
|---|---|---|
| NFR-001 | Env-var and tilde expansion for pack paths MUST add no measurable latency to `doctrine fetch`/`doctor doctrine` (pure string/path operations, no I/O beyond existing filesystem checks). | Draft |
| NFR-002 | The charter-first language resolution MUST NOT require re-running the discovery interview for existing projects to pick up the corrected precedence on their next charter compile. | Draft |

## Constraints

| ID | Description | Status |
|---|---|---|
| C-001 | WP1 and WP2 MUST be implemented, tested, and reviewable as independent, parallelizable work packages — zero shared code, test fixtures, or files between them. | Draft |
| C-002 | `#2213` is explicitly out of scope for this mission. | Draft |
| C-003 | The chosen env-var name is `SPEC_KITTY_PACK_HOME`, matching the existing `SPEC_KITTY_HOME` / `SPEC_KITTY_TEMPLATE_ROOT` naming convention (locked via decision `01KWY7B134NS9KEC9SWAJ8M0CH`). | Draft |
| C-004 | Unset-variable behavior is fail-closed (locked via decision `01KWY7B9DFRWNM7WV0GK1XG6K1`). | Draft |
| C-005 | The language-scope fix depth is the deeper DIRECTIVE_044 unification (persist a structured language set at compile time), not a minimal precedence branch-flip (locked via decision `01KWY7BHZDKJ8PKZBPY2C6BXHS`). | Draft |

## Success Criteria

- SC-001: An operator can commit a `.kittify/config.yaml` containing an env-var-templated `local_path` and have it resolve correctly on any machine or CI runner with `SPEC_KITTY_PACK_HOME` set, with zero manual per-machine edits to the committed file.
- SC-002: An operator who edits their charter's declared languages after initial creation sees doctrine language-scope filtering reflect the change immediately on the next charter compile, without re-running the discovery interview.
- SC-003: Both fixes ship with regression tests proving the previously-buggy scenario (env-var passthrough; interview-over-charter precedence) now resolves correctly, and existing tests that encoded the old (buggy) behavior are corrected rather than removed.

## Key Entities

- **OrgPackConfig** (`src/doctrine/drg/org_pack_config.py`): pydantic value object for a configured org doctrine pack; owns `local_path`, `subdir`, and `effective_root()` resolution.
- **Compiled Charter** (`.kittify/charter/charter.md` + structured artefacts): the canonical, current governance document; source of truth for active languages once compiled.
- **Interview Answers** (`.kittify/charter/interview/answers.yaml`): creation-time-only snapshot; not a competing runtime authority once a compiled language set exists.

## Assumptions

- No org pack is configured in this repository today; both WPs are proven via fixture-based tests, not a live dependency on an actual org pack.
- The compiled-charter structured language field (FR-009) is a new, additive field — it does not require a schema-breaking change to existing `charter.md` files that lack it (FR-010 fallback covers that case).
