# Data Model — Review/Merge Gate Hardening (3.2.x)

**Mission**: `review-merge-gate-hardening-3-2-x-01KRC57C` | **Date**: 2026-05-12

Defines the new typed entities, enums, and dataclass shapes introduced by this mission. Implementation modules implement these; tests assert against them; the cross-surface fixture harness (#992 Phase 0) consumes them.

---

## 1. WP03 — Mission-review domain

### `MissionReviewMode` (StrEnum)

```python
class MissionReviewMode(StrEnum):
    """Mode of a `spec-kitty review` invocation.

    Resolution order (highest precedence first):
      1. --mode CLI flag, if present
      2. POST_MERGE if meta.json.baseline_merge_commit is set
      3. LIGHTWEIGHT otherwise

    See: src/specify_cli/cli/commands/review/ERROR_CODES.md
    """
    LIGHTWEIGHT = "lightweight"
    POST_MERGE = "post-merge"
```

### `IssueMatrixVerdict` (StrEnum)

```python
class IssueMatrixVerdict(StrEnum):
    """Closed-set verdict allow-list for issue-matrix.md rows.

    Derived from audit of 6 existing matrices (2026-05-12); no drift observed.

    See: src/specify_cli/cli/commands/review/ERROR_CODES.md
    """
    FIXED = "fixed"
    VERIFIED_ALREADY_FIXED = "verified-already-fixed"
    DEFERRED_WITH_FOLLOWUP = "deferred-with-followup"
```

### `IssueMatrixRow` (dataclass)

```python
@dataclass(frozen=True)
class IssueMatrixRow:
    # Mandatory canonical fields (lowercase normalized)
    issue: str                      # GitHub issue identifier, may include #-prefix or link
    verdict: IssueMatrixVerdict
    evidence_ref: str               # non-empty; for DEFERRED_WITH_FOLLOWUP must contain a follow-up handle

    # Named-optional canonical fields (None when absent)
    title: str | None = None
    scope: str | None = None        # alias accepted: theme
    wp: str | None = None           # alias accepted: wp_id
    fr: str | None = None           # alias accepted: fr(s)
    nfr: str | None = None          # alias accepted: nfr(s)
    sc: str | None = None
    repo: str | None = None         # multi-repo scope (e.g., spec-kitty-saas)
```

### `IssueMatrixSchema` (typed validator vocabulary, NFR-007 single source)

```python
# Encoded once in src/specify_cli/cli/commands/review/_issue_matrix.py
MANDATORY_COLUMNS: tuple[str, ...] = ("issue", "verdict", "evidence_ref")
NAMED_OPTIONAL_COLUMNS: tuple[str, ...] = ("title", "scope", "wp", "fr", "nfr", "sc", "repo")
COLUMN_ALIASES: dict[str, str] = {
    "evidence ref": "evidence_ref",
    "wp_id": "wp",
    "fr(s)": "fr",
    "nfr(s)": "nfr",
    "theme": "scope",
}
```

### `MissionReviewDiagnostic` (StrEnum)

```python
class MissionReviewDiagnostic(StrEnum):
    """JSON-stable diagnostic codes emitted by `spec-kitty review`.

    Per-code remediation guidance is documented in
    src/specify_cli/cli/commands/review/ERROR_CODES.md
    """
    MODE_MISMATCH = "MISSION_REVIEW_MODE_MISMATCH"
    ISSUE_MATRIX_MISSING = "MISSION_REVIEW_ISSUE_MATRIX_MISSING"
    ISSUE_MATRIX_SCHEMA_DRIFT = "MISSION_REVIEW_ISSUE_MATRIX_SCHEMA_DRIFT"
    ISSUE_MATRIX_VERDICT_UNKNOWN = "MISSION_REVIEW_ISSUE_MATRIX_VERDICT_UNKNOWN"
    ISSUE_MATRIX_MULTI_TABLE = "MISSION_REVIEW_ISSUE_MATRIX_MULTI_TABLE"
    ISSUE_MATRIX_EVIDENCE_REF_EMPTY = "MISSION_REVIEW_ISSUE_MATRIX_EVIDENCE_REF_EMPTY"
    ISSUE_MATRIX_DEFERRED_WITHOUT_HANDLE = "MISSION_REVIEW_ISSUE_MATRIX_DEFERRED_WITHOUT_HANDLE"
    GATE_RECORD_MISSING = "MISSION_REVIEW_GATE_RECORD_MISSING"
    MISSION_EXCEPTION_INVALID = "MISSION_REVIEW_MISSION_EXCEPTION_INVALID"
    TEST_EXTRA_MISSING = "MISSION_REVIEW_TEST_EXTRA_MISSING"
```

### `MissionReviewReport` (frontmatter shape, FR-005, FR-007)

```python
@dataclass(frozen=True)
class MissionReviewReport:
    verdict: Literal["pass", "pass_with_notes", "fail"]
    mode: MissionReviewMode
    reviewed_at: str                # ISO-8601 UTC
    findings: int
    gates_recorded: list[GateRecord]
    issue_matrix_present: bool | Literal["not_applicable"]
    mission_exception_present: bool | Literal["not_applicable"]


@dataclass(frozen=True)
class GateRecord:
    id: Literal["gate_1", "gate_2", "gate_3", "gate_4"]
    name: str                       # e.g., "wp_lane_check"
    command: str                    # the exact CLI command executed
    exit_code: int
    result: Literal["pass", "fail", "skip"]
```

---

## 2. WP04 — Merge-state idempotency

### `MergeState` field addition

```python
# Extends existing src/specify_cli/merge/state.py MergeState dataclass:
@dataclass
class MergeState:
    # ... existing fields ...
    mission_number_baked: bool = False     # NEW (WP04)
```

Persistence: included in the existing `save_state()` / `load_state()` JSON serializer.

---

## 3. WP06 — Charter encoding chokepoint

### `CharterContent` (dataclass, FR-016, FR-017)

```python
@dataclass(frozen=True)
class CharterContent:
    text: str                       # always normalized UTF-8
    source_encoding: str            # detected, e.g. "utf-8", "cp1252", "utf-8-sig"
    confidence: float               # 0.0-1.0
    source_path: Path | None        # None for inline ingest via load_charter_bytes()
    normalization_applied: bool     # True if re-encoded from non-UTF-8
```

### `CharterEncodingDiagnostic` (StrEnum)

```python
class CharterEncodingDiagnostic(StrEnum):
    """JSON-stable diagnostic codes emitted by src/charter/_io.py.

    Per-code remediation guidance is documented in src/charter/ERROR_CODES.md
    """
    AMBIGUOUS = "CHARTER_ENCODING_AMBIGUOUS"
    NOT_NORMALIZED = "CHARTER_ENCODING_NOT_NORMALIZED"
```

### `EncodingProvenanceRecord` (JSONL record schema, FR-022)

```python
@dataclass(frozen=True)
class EncodingProvenanceRecord:
    event_id: str                   # ULID
    at: str                         # ISO-8601 UTC
    file_path: str                  # repo-relative path
    source_encoding: str
    confidence: float
    normalization_applied: bool
    bypass_used: bool               # True iff --unsafe override was used
    actor: str                      # invoker identification (e.g., "spec-kitty charter compile")
    mission_id: str | None          # ULID for per-mission events; None for centralized log
```

**Routing rule**: if `file_path` starts with `kitty-specs/<mission>/`, the record goes to `kitty-specs/<mission>/.encoding-provenance.jsonl` and `mission_id` is set; otherwise to `.kittify/encoding-provenance/global.jsonl` with `mission_id = None`. **Same record schema in both files; no duplication; same JSONL format**.

---

## 4. WP05 — Status read resolution

No new types. WP05 modifies behavior of existing functions:

- `get_main_repo_root()` retains current semantics for write paths.
- A new helper `get_status_read_root()` is added in `src/specify_cli/git/` (or wherever the existing resolvers live) which returns the **current worktree root** preferentially, falling back to `get_main_repo_root()` only when explicitly requested. Read-only status commands switch to this resolver.

---

## 5. Cross-cutting — ERROR_CODES.md schema (FR-033, NFR-008)

Each `ERROR_CODES.md` follows this Markdown layout:

```markdown
# <Subsystem> Error & Warning Codes

> **Source of truth**: `<module>/_diagnostics.py` (StrEnum class `<ClassName>`).
> This file is a hand-maintained mirror. Until #645's code-to-docs flow exists,
> the StrEnum members and this file's section count must match per NFR-008.

## <CODE_NAME>

**When it fires**: <one-sentence summary>

**JSON stability**: this code string is stable across minor releases; consumers may match it as an opaque identifier.

**Remediation**:
1. <option 1>
2. <option 2>
3. <option 3 if applicable>

**Body example**:

```text
<one-liner of the diagnostic body text the operator sees>
```
```

The StrEnum class docstring includes the literal line `See: <path-to-ERROR_CODES.md>`.

---

## 6. Glossary entries to add (FR-034)

Each new canonical term added to `.kittify/glossaries/spec_kitty_core.yaml`:

| Surface | Brief definition | Confidence | Status | Added by WP |
|---------|------------------|-----------|--------|-------------|
| lightweight mode | `spec-kitty review` invocation that performs consistency checks but is explicitly NOT a release gate. Skips dead-code and BLE001 audits; reports state with that limitation. | 0.95 | active | WP03 |
| post-merge mode | `spec-kitty review` invocation that enforces the full mission-review release-gate contract; requires `issue-matrix.md`, Gate 1–4 records, and `mission-exception.md` when applicable. | 0.95 | active | WP03 |
| mode mismatch | Diagnostic class fired when an operator explicitly requests `--mode post-merge` against a mission whose `baseline_merge_commit` is absent. | 0.95 | active | WP03 |
| issue-matrix schema drift | Diagnostic class fired when an `issue-matrix.md` file uses columns outside the canonical mandatory + named-optional vocabulary. | 0.95 | active | WP03 |
| encoding chokepoint | The single ingestion boundary at which charter content's source encoding is detected and recorded as provenance before downstream consumers see it. | 0.95 | active | WP06 |
| encoding provenance | The persisted audit trail (JSONL) of every encoding decision the chokepoint made, including detected encoding, confidence, normalization action, and bypass usage. | 0.95 | active | WP06 |
| unsafe bypass | An operator-chosen override of the encoding chokepoint's hard-fail behavior; uses the highest-confidence decode candidate and records `bypass_used: true` in provenance. | 0.95 | active | WP06 |
| review.py package | The post-WP07 layout of `src/specify_cli/cli/commands/review/` as a package of sibling files; was a single file pre-WP07. | 0.9 | active | WP07 |
| charter-content migration | The WP08 scan + normalize-or-fail-loud flow that brings existing missions' charter content into compliance with the WP06 chokepoint contract. | 0.95 | active | WP08 |

(Glossary entries may be refined during implementation; WP-level done criteria enforce presence per FR-034.)
