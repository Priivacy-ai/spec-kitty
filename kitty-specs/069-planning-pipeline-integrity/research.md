# Research: Planning Pipeline Integrity and Runtime Reliability

**Feature**: 069-planning-pipeline-integrity
**Date**: 2026-04-07
**Method**: Direct code review of affected modules

---

## Problem 1: Status dirty-git (#524)

### Confirmed root cause

`src/specify_cli/status/reducer.py` — two loci:

1. **`reduce()` at line 157**: `materialized_at=_now_utc()` — wall-clock timestamp makes JSON output non-deterministic even when events are identical. Every call produces a different string.

2. **`materialize()` at lines 184–203**: Always writes `status.json` unconditionally via `tmp_path.write_text` + `os.replace`. No read-before-write comparison.

`src/specify_cli/status/views.py` — one additional locus:

3. **`materialize_if_stale()` at line 154**: Has a correct stale check for `.kittify/derived/` files (lines 139–151), but then calls `materialize(feature_dir)` unconditionally as its return value. This second call always writes `kitty-specs/<feature>/status.json` regardless of stale status.

### Decision: Combined approach A+B

- **A (deterministic `materialized_at`)**: Change `sorted_events[-1].at` as the `materialized_at` value. Same event sequence → identical JSON → no false diffs.
- **B (skip-write if unchanged)**: In `materialize()`, after computing `json_str`, read existing `out_path` content (if it exists); skip `os.replace` if content is byte-identical.
- **`materialize_if_stale()` fix**: Replace the final `return materialize(feature_dir)` (line 154) with `return reduce(read_events(feature_dir))` — returns the snapshot without writing.

**Rationale**: A alone makes the output reproducible; B adds the idempotency guard so concurrent calls from multiple agents never race to write. Together they are belt-and-suspenders. `.gitignore`-based approach rejected: breaks CI workflows that commit `status.json` and is harder to revert.

**Empty event case**: The `reduce()` empty-events guard (line 119–128) also calls `_now_utc()`. Fix: use `""` (empty string) as the `materialized_at` for the empty case — it is semantically correct (no events → no last-event timestamp).

### Callers of `materialize()` (full map)

| Call site | File | Safe after fix? |
|-----------|------|----------------|
| `materialize(feature_dir)` | `status/bootstrap.py:153` | ✅ write only on first bootstrap |
| `_reducer.materialize(feature_dir)` | `status/emit.py:377` | ✅ emitting a new event always changes last_event_id |
| `materialize(feature_dir)` | `status/progress.py:177` | ✅ skip-write guard covers this |
| `materialize(feature_dir)` | `status/views.py:65` | ✅ called from `write_derived_views()` after new event |
| `materialize(feature_dir)` | `status/views.py:154` | ⚠️ **fix to `reduce(read_events(feature_dir))`** |

---

## Problem 2: Dependency parser (#525)

### Confirmed root cause

`src/specify_cli/core/dependency_parser.py` — `_split_wp_sections()` (lines 39–58):

```python
end = matches[idx + 1].start() if idx + 1 < len(matches) else len(tasks_content)
```

The last WP section runs from its header to `len(tasks_content)` — EOF. Any prose appended after the last WP header (Dependency Graph sections, MVP notes, coverage summaries) is included in the last WP's section body and scanned for dependency patterns. This is the confirmed source of the WP05-ghost-dependency bug in mission 068.

Second defect confirmed: `finalize-tasks` in `mission.py` at lines 1278–1282:
```python
if tasks_md.exists():
    tasks_content = tasks_md.read_text(encoding="utf-8")
    wp_dependencies = _shared_parse_deps(tasks_content)
```
There is no check for explicit `dependencies` in WP frontmatter before the prose parser runs — the prose parser result always wins for the `wp_dependencies` dict.

### Decision: wps.yaml as tier 0 in finalize-tasks

New 3-tier resolution in `finalize-tasks`:
- **Tier 0 (new)**: `wps.yaml` manifest → WP dependencies read directly from structured YAML; prose parser entirely bypassed
- **Tier 1 (existing)**: WP frontmatter (`parse_requirement_refs_from_wp_files`) — requirement refs
- **Tier 2 (existing fallback)**: `tasks.md` prose parser — only used when `wps.yaml` absent

**tasks.md generation**: `finalize-tasks` generates `tasks.md` from `wps.yaml` after processing when the manifest is present. The generated format follows the existing tasks-template.md conventions (sections, dependency lines, subtask lists) so human readability is preserved.

### wps.yaml validation library

`jsonschema` (Draft 2020-12) is already used in `src/specify_cli/mission_v1/schema.py`. Use the same pattern for wps.yaml validation. Pydantic 2.0 is available and used in `dossier/` — use it for the internal data model, and export the JSON Schema via `model.model_json_schema()`.

### Template changes scope

`/spec-kitty.tasks-outline` (source: `src/specify_cli/missions/software-dev/command-templates/tasks-outline.md`):
- Currently instructs LLM to write `tasks.md` (prose outline)
- **Change**: instruct LLM to write `wps.yaml` instead; note that `tasks.md` is generated by the system

`/spec-kitty.tasks-packages` (source: `src/specify_cli/missions/software-dev/command-templates/tasks-packages.md`):
- Currently reads `tasks.md` and generates WP prompt files
- **Change**: read from `wps.yaml`; update `wps.yaml` with per-WP fields (owned_files, requirement_refs, subtasks, prompt_file); still generate WP prompt files

**A new migration is required.** `m_2_1_3_restore_prompt_commands` uses `_is_thin_shim()` as its activation gate — it skips files that are already full prompts (≥ 10 non-empty lines without the shim marker). Existing installations have full prompt files and will be skipped. Migration `m_3_2_0_update_planning_templates.py` must detect content-stale full prompts by checking for the string `"Create \`tasks.md\`"` (present in the old tasks-outline, absent in the new version) and overwrite them from the updated source templates.

---

## Problem 3: next DAG advancement safety (#526)

### Confirmed root cause

`src/specify_cli/cli/commands/next_cmd.py` line 25:
```python
result: Annotated[str, typer.Option(...)] = "success",
```
Default `"success"` causes every bare `spec-kitty next` call to pass `result="success"` to `decide_next()`, which advances the state machine.

### Decision: query mode at CLI layer

Query mode implemented entirely in `next_cmd.py` + `runtime_bridge.py`. No changes to `spec-kitty-runtime` package (external).

**Flow for `result is None`**:
1. Call `get_or_start_run()` (idempotent — starts run only if none exists)
2. Call `_read_snapshot()` from `spec_kitty_runtime.engine` (same call that `decide_next_via_runtime` uses at line 478)
3. Return a `Decision` with `kind=DecisionKind.query` and current step info
4. Do NOT call `next_step()` from the runtime engine
5. Do NOT emit `MissionNextInvoked` event

New `DecisionKind.query = "query"` constant added to `decision.py`. The `_print_human()` function already prints `[{kind.upper()}]` at the top — so `kind="query"` produces `[QUERY]` automatically.

JSON output adds `"is_query": true` field so programmatic consumers can detect query mode without parsing the reason string.

**`_handle_answer()` flow**: Unchanged. The `--answer` flag still works; answers are processed before the result-mode check.

---

## Problem 4: Slug validator mismatch (#527)

### Confirmed root cause

`src/specify_cli/core/mission_creation.py` line 47:
```python
KEBAB_CASE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
```
Requires the first character to be a lowercase letter. Spec-kitty's own `NNN-*` slug convention starts with three digits.

Single validation call site at line 200.

### Decision: minimal regex change

```python
KEBAB_CASE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9]*(-[a-z0-9]+)*$")
```

This accepts:
- `068-feature-name` ✓ (digit-prefixed)
- `user-auth` ✓ (letter-prefixed, existing valid slugs unaffected)
- `UPPER` ✗ (still rejected — uppercase)
- `_under` ✗ (still rejected — underscore)
- `123` ✓ (technically accepted, harmless — `create` always prefixes the mission number, so a bare-digit slug becomes `069-123`; worth a comment in the code documenting the intentional permissiveness)

Error message at lines 202–211: remove the "starts with number" invalid example; add `068-fix-name` as a valid example.

Docstring at line 179: update "Bare slug such as `user-auth`" to include `068-fix-name`.

---

## Alternatives Considered and Rejected

| Option | Rejected because |
|--------|-----------------|
| Exclude `status.json` from git tracking (.gitignore) | Breaks existing CI workflows that commit it; hard to roll back if consumers depend on presence |
| Three-tier dependency with WP frontmatter (not wps.yaml) as tier 0 | Frontmatter `dependencies` is written by the pipeline, not by the planner — it cannot be the authoritative source |
| New `--query` flag for `next` | Worse ergonomics; punishes orientation use case with a required flag |
| Modify `spec-kitty-runtime` for query mode | External package boundary; query mode is a CLI-layer concern |
| Global slug validator refactor (multiple validators) | Audit found only one validation call site; refactor is unnecessary complexity |
