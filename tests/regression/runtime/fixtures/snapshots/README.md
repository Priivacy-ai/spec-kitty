# Regression Snapshots — Runtime Extraction Baseline

## Capture Metadata

| Field           | Value                           |
|-----------------|---------------------------------|
| **Captured**    | 2026-04-22                      |
| **CLI version** | spec-kitty-cli 3.2.0a4          |
| **Mission**     | `runtime-regression-reference-01KPDYGW` |
| **Purpose**     | Pre-extraction behavioral baseline for WP08 regression assertions |

## Snapshots

| File              | CLI Command                                                                             |
|-------------------|-----------------------------------------------------------------------------------------|
| `next.json`       | `spec-kitty next --agent claude --mission runtime-regression-reference-01KPDYGW --json` |
| `implement.json`  | `spec-kitty agent action implement WP01 --agent claude --mission runtime-regression-reference-01KPDYGW --json` |
| `review.json`     | `spec-kitty agent action review WP01 --agent claude --mission runtime-regression-reference-01KPDYGW --json` |
| `merge.json`      | `spec-kitty merge runtime-regression-reference-01KPDYGW --json` |

## Normalization Rules for WP08 Regression Assertions

When comparing post-extraction output against these snapshots, apply the following normalizations:

1. **Strip timestamps**: Replace any ISO 8601 timestamp values with a placeholder (e.g., `"<TIMESTAMP>"`).
   - Fields: `at`, `created_at`, `updated_at`, `started_at`, `materialized_at`
2. **Strip absolute paths**: Replace any paths containing `/home/`, `/Users/`, or `/tmp/` with `<PATH>`.
   - Fields: `workspace`, `worktree_path`, `prompt_file`, `repo_root`
3. **Strip run IDs**: Replace dynamic ULID run IDs with `<RUN_ID>`.
   - Fields: `run_id`, `decision_id`
4. **Strip version strings**: Replace CLI version strings with `<VERSION>`.

## Interpretation

Snapshots represent the **current behavior** before any code moves. They may contain error payloads (e.g., `{"error": "..."}`) if the CLI returned an error for the reference mission. This is expected — the mission fixture is minimal and does not have a full project context registered in `.kittify/`.

The key assertion is **structural stability**: after extraction, the same commands must return the same JSON keys and error codes, even if the values differ for dynamic fields (timestamps, paths).
