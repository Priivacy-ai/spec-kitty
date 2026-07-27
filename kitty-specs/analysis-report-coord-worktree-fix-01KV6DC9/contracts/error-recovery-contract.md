# Error Recovery Contract: `_require_current_analysis_report()`

This contract specifies the exact output format for each error branch in
`_require_current_analysis_report()` after the fix. Implementers must match
these formats exactly; test assertions must verify against these strings.

---

## Branch: `carrier_format_not_wrapped` (new)

**Trigger**: `analysis_freshness.reason == "carrier_format_not_wrapped"`

**Output** (to stdout via `print()`):
```
Error: analysis_report_required: /spec-kitty.analyze must be run before implementation.
  Reason: analysis-report.md is in carrier format (analysis-findings/v1) — written directly
          rather than via record-analysis. The implement gate requires the persisted
          outer-wrapper format (artifact_type: spec-kitty.analysis-report).
  Recovery: spec-kitty agent mission record-analysis --mission <mission_slug> --input-file <analysis_freshness.path>
```

**Binding rules**:
- `<mission_slug>` is the `mission_slug` parameter of `_require_current_analysis_report()`
- `<analysis_freshness.path>` is the absolute path from `AnalysisFreshness.path`
- The word `Recovery:` (not `Run:`) is used for this branch to distinguish it from the missing-report case

---

## Branch: `missing_analysis_report` (updated)

**Trigger**: `analysis_freshness.missing is True`

**Output**:
```
Error: analysis_report_required: /spec-kitty.analyze must be run before implementation.
  Missing: <analysis_freshness.path>
  Run step 1: /spec-kitty.analyze
  Run step 2: spec-kitty agent mission record-analysis --mission <mission_slug> --input-file -
```

**Binding rules**:
- `<mission_slug>` is the `mission_slug` parameter
- The two-step presentation (`step 1` / `step 2`) is required for NFR-003 (actionable without source inspection)

---

## Branch: `stale_analysis_report` (unchanged behavior, retained for completeness)

**Trigger**: `analysis_freshness.stale is True` and `reason == "stale_analysis_report"`

**Output** (existing behavior, no change):
```
Error: analysis_report_required: /spec-kitty.analyze must be run before implementation.
  Reason: stale_analysis_report
  Stale inputs:
    - <artifact_name_1>
    - <artifact_name_2>
  Run: /spec-kitty.analyze --mission <mission_slug>
```

---

## Branch: all other reasons (catch-all, unchanged behavior)

**Trigger**: any other `analysis_freshness.reason` value

**Output** (existing behavior, no change):
```
Error: analysis_report_required: /spec-kitty.analyze must be run before implementation.
  Reason: <analysis_freshness.reason>
  Run: /spec-kitty.analyze --mission <mission_slug>
```

---

## Invariant

The header line `"Error: analysis_report_required: /spec-kitty.analyze must be run before implementation."` is emitted in every branch. Existing callers and tests that assert on this string must not break.
