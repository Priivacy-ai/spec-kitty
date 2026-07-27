# Data Model: Analysis Report Coord-Worktree Fix

No new persistent data entities are introduced. The fix modifies behavior of
existing functions and adds one named constant. This document captures the
reason-code taxonomy as the only "data" boundary added by this mission.

---

## Reason-Code Taxonomy for `AnalysisFreshness.reason`

`check_analysis_report_current()` returns an `AnalysisFreshness` dataclass with
a `reason: str | None` field. After this fix, the complete set of stable reason
values is:

| Reason value | When emitted | Recovery action |
|---|---|---|
| `None` | Report is current and valid | None — proceed |
| `"missing_analysis_report"` | `analysis-report.md` does not exist | Run `/spec-kitty.analyze`, then `record-analysis` |
| `"invalid_analysis_report_frontmatter"` | File has unparseable frontmatter | Delete and re-generate |
| `"carrier_format_not_wrapped"` | **NEW** — frontmatter has `schema: analysis-findings/v1` but not outer-wrapper `artifact_type` | `record-analysis --input-file <path>` |
| `"invalid_analysis_report_artifact_type"` | Frontmatter parsed successfully, neither outer-wrapper nor carrier format | Delete and re-generate |
| `"missing_input_artifacts"` | `input_artifacts` key absent from frontmatter | Re-run `record-analysis` |
| `"stale_analysis_report"` | One or more input artifact hashes differ from current | Re-run `/spec-kitty.analyze` + `record-analysis` |

**Invariant**: `carrier_format_not_wrapped` is checked before `invalid_analysis_report_artifact_type`.
A file cannot match both: a carrier file has `schema: analysis-findings/v1`
(not `artifact_type`), so it will return `carrier_format_not_wrapped` and never
reach the generic check.

**Constant definition** (in `src/specify_cli/analysis_report.py`):
```
ANALYSIS_REPORT_REASON_CARRIER_FORMAT = "carrier_format_not_wrapped"
```
This constant must be used in both `check_analysis_report_current()` (where it
is set) and `_require_current_analysis_report()` (where it is matched), so it
belongs in `analysis_report.py` which is already imported by the workflow module.

---

## `AnalysisFreshness` Dataclass (unchanged shape)

```
AnalysisFreshness:
  ok: bool
  path: Path
  stale: bool
  missing: bool
  reason: str | None
  mismatches: dict[str, dict[str, str | None]]
```

The `carrier_format_not_wrapped` reason sets `stale=True` and `missing=False`,
consistent with how other "file exists but is wrong format" reasons are encoded.
No dataclass field additions are needed.
