# Data Model: Glossary DRG Surfaces and Charter Lint

**Mission**: glossary-drg-surfaces-and-charter-lint-01KPTY5Y

---

## New Types

### InlineNotice (WP5.3)

Ephemeral value object rendered to terminal output by the CLI observation surface. Never persisted.

| Field | Type | Description |
|-------|------|-------------|
| `term` | `str` | Canonical term name |
| `term_id` | `str` | Glossary term ID |
| `conflicting_senses` | `list[str]` | Two or more sense texts that are in conflict |
| `severity` | `Literal["high", "critical"]` | Conflict severity (only high/critical trigger inline display) |
| `suggested_action` | `str` | Short human-readable suggestion (e.g., "run `spec-kitty glossary resolve deployment-target`") |
| `conflict_type` | `str` | Conflict category from `classify_conflict()` |

**Invariants**: `severity in {"high", "critical"}` always; only emitted when there is at least one conflict.

---

### GlossaryHealthData (WP5.4, WP5.4 dashboard API)

```python
class GlossaryHealthResponse(TypedDict):
    total_terms: int
    high_severity_drift_count: int
    orphaned_term_count: int       # terms with no vocabulary edge in the DRG
    entity_pages_generated: bool   # whether compiled/glossary/ dir exists and is non-empty
    entity_pages_path: str | None  # relative path to compiled/glossary/ dir
    last_conflict_at: str | None   # ISO timestamp of most recent high-severity conflict event
```

**Source of truth**: glossary store (`src/specify_cli/glossary/store.py`) + event log at `.kittify/events/glossary/_cli.events.jsonl`.

---

### EntityPage (WP5.5)

Markdown file at `.kittify/charter/compiled/glossary/<term-id>.md`. Never committed (gitignored).

**Structure**:
```markdown
# <canonical-term-name>

**ID**: glossary:<term-id>  **Scope**: <scope>  **Status**: <active|deprecated|provisional>

## Definition

<current canonical definition>

## Provenance

First introduced by: <synthesizer-run-id> at <ISO timestamp>  
Source corpus snapshot: <snapshot-id>

## References

### Work Packages
- [WP01 — <title>](<relative-path-to-tasks/WP01.md>) — cited in <context excerpt>
- ...

### ADRs
- [ADR-3 — <title>](<relative-path-to-adrs/ADR-3.md>) — defined / invalidated / referenced

### Mission Steps
- [Step N of mission <slug>](<path>) — observed at <timestamp>

### Retrospective Findings
- <finding excerpt> — [Retro <id>](<path>)

### Charter Sections
- <section name> — introduced this term in charter interview at <timestamp>

## Conflict History

| Timestamp | Severity | Type | Senses | Resolution | Actor |
|-----------|----------|------|--------|------------|-------|
| ...       | high     | ...  | ...    | ...        | ...   |

## Related Terms

- **Sibling**: [<term>](glossary:<id>.md) — via shared parent scope
- **Generalization**: [<term>](glossary:<id>.md)
```

---

### LintFinding (WP5.6)

```python
@dataclass
class LintFinding:
    category: Literal["orphan", "contradiction", "staleness", "reference_integrity"]
    type: str          # e.g. "wp", "adr", "glossary_term", "synthesized_artifact", "procedure"
    id: str            # node ID or URN of the offending artifact
    severity: Literal["low", "medium", "high", "critical"]
    message: str       # human-readable description of the decay
    feature_id: str | None   # mission slug / feature ID if scoped, else None
    remediation_hint: str | None  # optional suggested fix
```

**JSON serialization** (for `--json` output):
```json
{
  "category": "orphan",
  "type": "adr",
  "id": "ADR-7",
  "severity": "medium",
  "message": "ADR-7 is not referenced by any WP, charter section, or other ADR in feature 042",
  "feature_id": "042-my-feature",
  "remediation_hint": "Reference ADR-7 from at least one WP or mark it as superseded"
}
```

---

### DecayReport (WP5.6)

```python
@dataclass
class DecayReport:
    findings: list[LintFinding]
    scanned_at: str           # ISO 8601 timestamp
    feature_scope: str | None # mission slug if --feature was passed, else None
    duration_seconds: float
    drg_node_count: int
    drg_edge_count: int
```

**Persisted to**: `.kittify/lint-report.json` after each run (machine-readable, keyed by `scanned_at`). The dashboard reads the most recent entry.

**JSON envelope**:
```json
{
  "findings": [...],
  "scanned_at": "2026-04-22T15:00:00Z",
  "feature_scope": null,
  "duration_seconds": 1.24,
  "drg_node_count": 312,
  "drg_edge_count": 1048
}
```

---

### DecayWatchTileResponse (WP5.6 dashboard, TypedDict)

```python
class DecayWatchTileResponse(TypedDict):
    has_data: bool
    scanned_at: str | None
    orphan_count: int
    contradiction_count: int
    staleness_count: int
    reference_integrity_count: int
    high_severity_count: int
    total_count: int
    feature_scope: str | None
```

---

## State Transitions

### Entity Page Lifecycle (WP5.5)

```
[not generated]  →  [generated]  →  [stale]  →  [regenerated]
       ↑                                               ↓
       └─────────── ensure_charter_bundle_fresh() ─────┘
```

Entity pages are regenerated atomically: write to a temp file, rename into place. A stale page is never served partially.

### Lint Report Lifecycle (WP5.6)

```
[none]  →  [current]  →  [stale (next run)]  →  [current (overwritten)]
```

Only one lint report file exists at a time. Dashboard always shows the most recent completed run.

---

## File Layout

```
.kittify/
  charter/
    compiled/
      glossary/           ← gitignored, entity pages
        <term-id>.md
        <term-id>.md
        ...
  events/
    glossary/
      _cli.events.jsonl   ← CLI invocation conflict events (WP5.3, WP5.4)
      <mission-id>.events.jsonl
  lint-report.json        ← last DecayReport JSON (WP5.6 → WP5.6 dashboard)

src/specify_cli/
  glossary/
    entity_pages.py       ← GlossaryEntityPageRenderer (WP5.5)
  charter_lint/
    __init__.py
    engine.py             ← LintEngine (WP5.6)
    findings.py           ← LintFinding, DecayReport dataclasses (WP5.6)
    checks/
      orphan.py           ← OrphanChecker (WP5.6)
      contradiction.py    ← ContradictionChecker (WP5.6)
      staleness.py        ← StalenessChecker (WP5.6)
      reference_integrity.py ← ReferenceIntegrityChecker (WP5.6)
  dashboard/
    handlers/
      glossary.py         ← GlossaryHandler (WP5.4)
      lint.py             ← LintTileHandler (WP5.6 dashboard)
    api_types.py          ← add GlossaryHealthResponse, DecayWatchTileResponse
```
