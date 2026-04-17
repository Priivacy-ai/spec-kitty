# Phase 1 Data Model — Charter Ownership Consolidation and Neutrality Hardening

**Mission**: `01KPD880` · **Phase**: 1 (Design & Contracts)

This mission introduces no runtime persistence, no database schema, and no on-disk bundle layout change (C-001). The "data model" here is the small set of **configuration artifacts, runtime value types, and metadata records** that the neutrality lint and shim deprecation machinery rely on.

Each entity below has: purpose, shape, validation rules, and the spec requirement(s) it satisfies.

---

## Entity 1 — `BannedTerm`

**Purpose**: Describes a single pattern the neutrality lint rejects in generic-scoped doctrine artifacts.

**Shape** (YAML entry under `src/charter/neutrality/banned_terms.yaml:terms`):

```yaml
- id: PY-001                      # unique, stable, human-readable; prefix indicates language family
  kind: literal                   # "literal" | "regex"
  pattern: "pytest"               # literal string or regex source
  rationale: "Primary offender pre-3.1.5; Python test framework name."
  added_in: "3.2.0"               # release when term was added; informational only
```

**Validation rules**:

- `id` MUST be unique within the file.
- `kind` MUST be one of `literal` or `regex`.
- If `kind == "regex"`, `pattern` MUST compile under `re.compile(pattern, re.MULTILINE)` at lint startup; a compile failure fails the test run with a clear error naming the offending `id`.
- `rationale` MUST be a non-empty string (forces contributors to justify new bans).
- `added_in` is informational; not validated beyond being a string.

**Initial population**: Four Python-scoped terms (PY-001 through PY-004) — see `research.md` R-003. The initial list is deliberately narrow: filenames like `pyproject.toml`, `conftest.py`, and `.py` suffixes appear in multi-ecosystem enumerations in generic templates (e.g., alongside `package.json`, `go.mod`, `Cargo.toml`) and were excluded to avoid false positives. Expansion requires a deliberate add with rationale.

**Requirements covered**: FR-008 (banned-term enforcement), FR-014 (single-file maintenance).

---

## Entity 2 — `LanguageScopedPath`

**Purpose**: Declares a doctrine artifact path (or path prefix) as intentionally language-scoped, exempting it from the banned-terms lint.

**Shape** (YAML entry under `src/charter/neutrality/language_scoped_allowlist.yaml:paths`):

```yaml
- path: "src/charter/profiles/python/README.md"
  scope: python
  owner: "charter team"
  reason: "Canonical Python profile guidance; references pytest intentionally."
  added_in: "3.2.0"
```

**Validation rules**:

- `path` MUST be a repo-relative path with forward slashes; MUST resolve to an existing file at lint time, otherwise the test fails with a clear message (prevents silent stale allowlist entries).
- `scope` MUST be a non-empty string; convention: lowercase language family (`python`, `node`, `ruby`, `go`, …).
- `owner` and `reason` MUST be non-empty strings.
- `added_in` is informational.
- The allowlist MAY use glob-style `path` patterns (e.g., `src/charter/profiles/python/**/*.md`); the lint implementation resolves globs via `pathlib.Path.glob`. If a glob matches zero files at lint time, the test fails (stale entry).

**Initial population**: **Four entries**, not empty. Baseline audit of `src/doctrine/` found shipped artifacts that are intentionally Python-scoped and would otherwise fail the lint:

```yaml
paths:
  - path: "src/doctrine/agent_profiles/shipped/python-implementer.agent.yaml"
    scope: python
    owner: "charter team"
    reason: "Shipped Python implementer agent profile; references pytest/pip intentionally."
    added_in: "3.2.0"
  - path: "src/doctrine/styleguides/shipped/python-conventions.styleguide.yaml"
    scope: python
    owner: "charter team"
    reason: "Canonical Python conventions styleguide; Python vocabulary is the subject."
    added_in: "3.2.0"
  - path: "src/doctrine/toolguides/shipped/python-review-checks.toolguide.yaml"
    scope: python
    owner: "charter team"
    reason: "Python review-check toolguide; tool names (pytest, mypy) are the subject."
    added_in: "3.2.0"
  - path: "src/doctrine/toolguides/shipped/PYTHON_REVIEW_CHECKS.md"
    scope: python
    owner: "charter team"
    reason: "Human-readable companion to python-review-checks.toolguide.yaml."
    added_in: "3.2.0"
```

The earlier draft assumption that the allowlist ships empty was incorrect — it was based on the absence of a `src/charter/profiles/python/` tree, overlooking `src/doctrine/`, which is the actual bias surface. Shipping with an empty allowlist would cause the lint to fail on its first run against the real repo.

**Requirements covered**: FR-009 (allowlist existence), FR-013 (Python guidance confined to allowlisted paths).

---

## Entity 3 — `NeutralityLintResult`

**Purpose**: In-memory value type produced by the lint scanner; consumed by the pytest assertion to produce actionable diagnostics.

**Shape** (Python dataclass, `src/charter/neutrality/lint.py`):

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class BannedTermHit:
    file: Path            # repo-relative
    line: int             # 1-indexed
    column: int           # 1-indexed
    term_id: str          # e.g., "PY-001"
    match: str            # the actual matched text (for error message)

@dataclass(frozen=True)
class NeutralityLintResult:
    hits: tuple[BannedTermHit, ...]
    stale_allowlist_entries: tuple[str, ...]      # paths that matched zero files
    scanned_file_count: int
    banned_term_count: int
    allowlisted_path_count: int

    @property
    def passed(self) -> bool:
        return not self.hits and not self.stale_allowlist_entries
```

**Validation rules**: immutable dataclass (`frozen=True`); construction is the only write path.

**Requirements covered**: FR-010 (regression test mechanics), FR-011 (actionable error messages — the hit record carries everything needed to print file:line, the term id, and the remediation hint).

---

## Entity 4 — `ShimDeprecationRecord`

**Purpose**: Metadata attached to the legacy **package** (`specify_cli.charter`) so the DeprecationWarning message is consistent and the removal release is discoverable from Python introspection (not just a changelog entry). Submodule shims (`compiler.py`, `interview.py`, `resolver.py`) intentionally do not carry warning-emitting code, because Python loads the parent package's `__init__.py` on the way to resolving any submodule — emitting per-submodule would double-warn on every `from specify_cli.charter.X import Y` (see C-2, shim-deprecation-contract.md).

**Shape** (module-level constants on the package `__init__.py` only):

```python
# src/specify_cli/charter/__init__.py
import warnings

__deprecated__ = True
__canonical_import__ = "charter"              # the package path callers should use instead
__removal_release__ = "3.3.0"                 # target version for shim removal
__deprecation_message__ = (
    "specify_cli.charter is deprecated; import from 'charter' instead. "
    "Scheduled removal: 3.3.0."
)

warnings.warn(__deprecation_message__, DeprecationWarning, stacklevel=2)
```

Submodule shims (`compiler.py`, `interview.py`, `resolver.py`) MAY carry informational `__deprecated__ = True` and `__canonical_import__ = "charter.<submod>"` attributes for reader clarity, but they MUST NOT call `warnings.warn` or declare `__deprecation_message__` / `__removal_release__`. Those live on the package alone.

**Validation rules**:

- The package `__init__.py` MUST declare all four attributes; the `test_shim_deprecation.py` test enforces via `importlib` + `getattr`.
- `__canonical_import__` MUST be a dotted Python path that resolves successfully at test time (validates the replacement import actually works).
- `__removal_release__` MUST match the release string recorded in `CHANGELOG.md` for this mission's removal-target entry (cross-validated by the deprecation test reading both).
- `__deprecation_message__` MUST include both the canonical path and the removal release.
- Submodule shims MUST NOT emit `DeprecationWarning`; the test's `len(ours) == 1` assertion (see C-2) catches any regression that reintroduces per-submodule warnings.

**Requirements covered**: FR-005 (catchable DeprecationWarning with canonical path + removal release), FR-015 (sunset plan recorded in contributor-facing location), SC-006 (docstring + changelog consistency).

---

## Entity 5 — `CharterOwnershipInvariant`

**Purpose**: Executable invariant — there is exactly one definition of `build_charter_context` and exactly one definition of `ensure_charter_bundle_fresh` anywhere under `src/`.

**Shape** (implemented as a pytest case using `ast`, not stored data):

```python
# tests/charter/test_charter_ownership_invariant.py — executable spec of the invariant
CANONICAL_OWNERS: dict[str, str] = {
    "build_charter_context": "src/charter/context.py",
    "ensure_charter_bundle_fresh": "src/charter/sync.py",
}
```

**Validation rules**:

- Each name in `CANONICAL_OWNERS` MUST appear as exactly one `FunctionDef` across all Python files under `src/`.
- The canonical file path MUST be the file containing that sole definition.
- A failure produces an error message naming every file containing a `FunctionDef` with a tracked name, guiding the contributor to the canonical location.

**Requirements covered**: FR-001, FR-002 (ownership invariants); SC-001 (automated test confirms the invariant).

---

## Cross-entity relationships

```
BannedTerm  ──(applied to files NOT in)──▶  LanguageScopedPath
                              │
                              ▼
                      NeutralityLintResult  ─────▶  (pytest assertion → pass/fail)

ShimDeprecationRecord  ─────▶  (import-time DeprecationWarning)
                              │
                              ▼
                  (test asserts warning + canonical-import resolves)

CharterOwnershipInvariant ─────▶  (ast scan)  ─────▶  (pytest assertion → pass/fail)
```

No foreign-key style relationship exists; the entities are independent and live in disjoint files. The lint scanner joins `BannedTerm` × `LanguageScopedPath` at test time to produce `NeutralityLintResult`.

---

## State transitions

None. All entities are configuration-at-rest or transient in-memory values. No runtime mutation, no persistence layer.

---

## Versioning & migration

- `banned_terms.yaml` and `language_scoped_allowlist.yaml` ship an implicit v1 schema in this mission. Adding new top-level fields is a non-breaking change; removing fields is breaking and requires a separate mission.
- `ShimDeprecationRecord` attribute set is the v1 contract; if a future mission needs richer metadata, new optional attributes can be added without breaking the invariant.

---

## Out-of-scope entities

Intentionally **not** modelled in this mission (per spec Out of Scope + Constraints):

- A doctrine artifact `scope:` field (would require schema redesign — C-003).
- A multi-language styleguide/toolguide registry (deferred to Phase 4 / #466 — C-002).
- A provenance / telemetry record of lint invocations (not required by any FR).
- On-disk charter bundle entities (frozen by C-001).
