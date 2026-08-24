---
schema_version: 1
artifact_type: spec-kitty.analysis-report
command: /spec-kitty.analyze
mission_slug: copyable-version-output-01KW6N9V
mission_id: 01KW6N9VBP46T024MXT8C368JE
generated_at: '2026-06-28T08:52:29.969622+00:00'
analyzer_agent: cursor
input_artifacts:
  spec.md:
    path: /Users/zohar/apps/spec-kitty-cli-improvements/kitty-specs/copyable-version-output-01KW6N9V/spec.md
    sha256: 7505b68e72d71e6cc5938f57779ac3c07729d9913c55115488845f1ce9fee2fd
  plan.md:
    path: /Users/zohar/apps/spec-kitty-cli-improvements/kitty-specs/copyable-version-output-01KW6N9V/plan.md
    sha256: 47af7a1c6c6f78968538b103eed7eeb3279c83fc002938261d37a0d6d131a75a
  tasks.md:
    path: /Users/zohar/apps/spec-kitty-cli-improvements/kitty-specs/copyable-version-output-01KW6N9V/tasks.md
    sha256: 84229cc3112e9f4be76edb2577d2eafe78547f83f203f02d22adbbeb407ad3fa
  charter:
    path: /Users/zohar/apps/spec-kitty-cli-improvements/.kittify/charter/charter.md
    sha256: d393b068f20eab1bb918c2f53e669d01048f049e8b0f948ff6001fc280517c08
verdict: unknown
issue_counts:
  critical:
  low:
  info:
  medium:
  high:
findings: []
---

# Analysis Report: Copyable Version Output

## Existing Surfaces

- Version output is produced by `version_callback` in `src/specify_cli/__init__.py`.
- The callback currently calls `show_banner(force=True)` before printing `spec-kitty-cli version ...`.

## Implementation Direction

Remove banner rendering from the version callback and print the copyable version line directly. Add focused tests for both `--version` and `-v` to ensure the first non-empty line is the version line and the large banner/tagline is absent.

## Risks

- Existing users may expect branding in version output, but the mission explicitly prioritizes issue-report copy/paste.

## Validation

Run the targeted version output test file in a local virtualenv.
