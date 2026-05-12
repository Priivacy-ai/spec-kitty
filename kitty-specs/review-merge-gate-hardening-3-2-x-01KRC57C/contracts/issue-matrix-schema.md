# Contract: `issue-matrix.md` validator schema

**WP**: WP03 | **FRs**: FR-006, FR-028 – FR-032 | **Diagnostic codes**: `MISSION_REVIEW_ISSUE_MATRIX_*`

## Audit-derived vocabulary (closed sets)

### Mandatory columns

Exact order, case-insensitive on input, normalized to lowercase internally:

1. `issue`
2. `verdict`
3. `evidence_ref`

### Named-optional columns (closed set)

May appear in any order after the mandatory three:

- `title`
- `scope` (alias: `theme`)
- `wp` (alias: `wp_id`)
- `fr` (alias: `fr(s)`)
- `nfr` (alias: `nfr(s)`)
- `sc`
- `repo`

### Verdict allow-list (closed set)

```
fixed
verified-already-fixed
deferred-with-followup
```

## Validator rules

| Rule | Diagnostic on violation |
|------|-------------------------|
| All mandatory columns present, in order | `MISSION_REVIEW_ISSUE_MATRIX_SCHEMA_DRIFT` |
| Every column is either mandatory or named-optional | `MISSION_REVIEW_ISSUE_MATRIX_SCHEMA_DRIFT` (names unknown column) |
| Verdict cell value is in the allow-list | `MISSION_REVIEW_ISSUE_MATRIX_VERDICT_UNKNOWN` |
| Exactly one Markdown table at top level (additional prose allowed; additional tables NOT allowed) | `MISSION_REVIEW_ISSUE_MATRIX_MULTI_TABLE` |
| `evidence_ref` cell non-empty | `MISSION_REVIEW_ISSUE_MATRIX_EVIDENCE_REF_EMPTY` |
| When `verdict == deferred-with-followup`, `evidence_ref` contains a follow-up handle (regex matches `#\d+` OR contains `Follow-up:` substring) | `MISSION_REVIEW_ISSUE_MATRIX_DEFERRED_WITHOUT_HANDLE` |

## Remediation pass over existing matrices (FR-032)

When the validator runs in remediation mode over the 6 existing matrices on `main`:

- **Auto-normalize**: capitalization drift (`Issue` → `issue`), alias drift (`Evidence ref` → `evidence_ref`, `wp_id` → `wp`, `theme` → `scope`). Writes a one-line provenance note inside the file: `<!-- normalized YYYY-MM-DD: header case folded; aliases resolved -->`.
- **Surface, do not auto-fix**: structural drift (multi-table layout in `charter-golden-path-e2e-tranche-1-01KQ806X`; any unknown columns like `Surface` or `Where surfaced in code`). Operator gets a diagnostic with repair guidance and must commit the fix manually.

## Parsing contract

- Parser is line-oriented Markdown table parser; tolerates leading prose.
- Empty leading/trailing whitespace in cells is stripped.
- Backticked verdict values (`` `fixed` ``) are accepted; backticks stripped during normalization.
- Linkified issue values (`[#123](https://...)`) are accepted; the `#NNN` form is canonical for the parsed `IssueMatrixRow.issue` value.

## Output

- On success: parsed `list[IssueMatrixRow]`.
- On failure: non-zero exit + JSON diagnostic on stdout.

## Acceptance fixtures

- 6 existing matrices on `main` — each passes either after auto-normalize or surfaces a specific diagnostic per the rules above.
- A synthetic matrix with an unknown column `Severity` — fails `SCHEMA_DRIFT` naming `Severity`.
- A synthetic matrix with verdict `deferred` (no `-with-followup`) — fails `VERDICT_UNKNOWN`.
- A synthetic matrix with `deferred-with-followup` verdict but `evidence_ref` of `TBD` — fails `DEFERRED_WITHOUT_HANDLE`.
