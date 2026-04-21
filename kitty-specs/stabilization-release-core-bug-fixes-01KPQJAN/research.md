# Research: Stabilization Release: Core Bug Fixes

**Phase 0 output** — technical design decisions per work package  
**Date**: 2026-04-21  
**Mission ID**: 01KPQJAN4P2V4MTHRFGS7VW17M

---

## WP01: Merge Post-Merge Invariant

### Finding: Porcelain v1 status code semantics

Git `--porcelain` (v1) format: two-character status code + space + path. The first character is the index status, the second is the working-tree status. `??` means the file is untracked (not in index, not in HEAD). It does not represent divergence from the last commit.

Only the following codes indicate that tracked files diverge from HEAD and should trigger the invariant:
- Index changes: `M`, `A`, `D`, `R`, `C`, `U` in position 1
- Working-tree changes: `M`, `D`, `U` in position 2

Any other unexpected code (not in `expected_paths` and not `??`) should still abort, but with a generic "unexpected working-tree state" message rather than the sparse-checkout message.

**Decision**: Parse the two-character prefix of every porcelain line. Skip lines where both characters form `??`. Collect all other unexpected codes as genuine divergence. Bifurcate the abort message based on whether the offending codes look like sparse-checkout artifacts (e.g., tracked files missing) vs. an unknown state.

**Alternative considered**: Whitelist only specific "safe" codes to skip. Rejected — too brittle. Instead, the fix blacklists only `??` (the one known-safe untracked marker) and leaves all other unexpected codes as abort triggers.

---

### Finding: Error message accuracy

The current message unconditionally says `spec-kitty doctor sparse-checkout --fix`. Sparse-checkout issues manifest as unexpected deletions or modifications of tracked paths, not as `??` untracked entries. Untracked entries in `.claude/`, `.agents/`, etc. are agent tooling that appears after a `spec-kitty upgrade` or fresh agent setup.

**Decision**: The error message dispatches on the nature of the offending lines:
- If offending lines include tracked-file modifications or deletions → retain sparse-checkout guidance
- Otherwise → emit a general "unexpected working-tree state" message pointing the user to `git status` for investigation

---

## WP02: Shim Generation Format

### Finding: Gemini command file format

Gemini CLI (`gemini` CLI / Project IDX) reads commands from `.gemini/commands/*.toml` files. The TOML schema is:

```toml
[[commands]]
name = "spec-kitty.implement"
description = "Execute a work package implementation"
command = "spec-kitty agent action implement {{args}} --agent gemini"
```

Key differences from the Markdown format:
- No YAML frontmatter
- TOML array-of-tables `[[commands]]` structure
- Argument placeholder is `{{args}}` (Mustache-style), not `$ARGUMENTS`
- File extension is `.toml`

**Decision**: Add `generate_shim_content_toml(command, agent_name, arg_placeholder)` alongside the existing `generate_shim_content()`. The TOML generator uses the `[[commands]]` schema above.

**Alternative considered**: A single generator with a format parameter. Rejected — the two formats are structurally different enough that a branch inside one function would be harder to read and test than two separate functions.

---

### Finding: Qwen command file format

Qwen Code (Qwen Coder CLI) reads commands from `.qwen/commands/*.md` files using the same Markdown + YAML frontmatter format as Claude Code, but with `{{args}}` as the argument placeholder (not `$ARGUMENTS`).

**Decision**: Qwen stays with `.md` format but switches to `{{args}}` placeholder. `AGENT_ARG_PLACEHOLDERS["qwen"] = "{{args}}"` is the only change for Qwen. No new generator function needed.

**Note**: This is the implementation-time conclusion from inspecting the Qwen CLI spec. If Qwen behavior differs, the implementation must update this research note and the plan.

---

### Finding: AGENT_SHIM_FORMATS dispatch

The cleanest change is:
1. Add `AGENT_SHIM_FORMATS: dict[str, str] = {"gemini": "toml"}` — agents in this dict use the alternate generator; all others use the Markdown generator.
2. In `generate_all_shims()`, check `AGENT_SHIM_FORMATS.get(agent_key, "md")` and dispatch accordingly, using the correct file extension.
3. `AGENT_ARG_PLACEHOLDERS` gains `"gemini": "{{args}}"` and `"qwen": "{{args}}"`.

---

## WP03: Review Lane Semantics

### Finding: IN_REVIEW lane exists in the transition matrix

The 9-lane state machine includes `in_review` as a distinct lane between `for_review` and `approved`/`rejected`. The transition matrix in `src/specify_cli/status/transitions.py` already allows `for_review → in_review`. The review-claim code bypassed this by using `force=True` with `in_progress` — an illegal transition that was silently accepted because of the force flag.

**Decision**: Use `to_lane=Lane.IN_REVIEW` and remove `force=True`. The legal transition `for_review → in_review` does not need forcing.

---

### Finding: Legacy backward compatibility strategy

Historical event logs contain `{"to_lane": "in_progress", "review_ref": "action-review-claim"}` entries. These are valid historical records. The fix must:

1. Keep the `is_review_claimed` detection logic working for both old and new shapes.
2. Not retroactively rewrite or reinterpret historical events in the snapshot — the snapshot for an old log will show `in_progress` for a legacy review-claimed WP, which is the historically accurate state.
3. Approval/rejection paths that read `current_lane` must accept both `Lane.IN_REVIEW` (new) and the legacy `Lane.IN_PROGRESS` + `review_ref=action-review-claim` shape as valid "under review" states.

**Decision**: Update `is_review_claimed` to OR the two conditions:
```python
is_review_claimed = bool(
    latest_event is not None
    and (
        latest_event.to_lane == Lane.IN_REVIEW
        or (
            latest_event.to_lane == Lane.IN_PROGRESS
            and latest_event.review_ref == "action-review-claim"
        )
    )
)
```
The guard that checks current_lane must also accept `Lane.IN_REVIEW` as a valid state for review operations.

---

### Finding: Downstream lane references

A search of `workflow.py` for `Lane.IN_PROGRESS` in the review workflow confirms these are the only sites that need updating:
- Line ~1344: `is_review_claimed` check (update to OR both shapes)
- Lines ~1362: `current_lane not in {Lane.FOR_REVIEW, Lane.IN_PROGRESS}` guard (add `Lane.IN_REVIEW` as accepted entry)
- Lines ~1418–1426: The emit itself (change `to_lane` to `Lane.IN_REVIEW`, remove `force=True`)

Approval and rejection handling downstream operate on `current_lane` at the time of approval/rejection, not on the lane at claim time. Since new claims will produce `in_review`, and the transition matrix allows `in_review → approved`/`in_review → for_review` (rejected), no downstream changes are needed for the happy path.

---

## WP04: Intake Hardening Cluster

### Finding: Atomic write — temp-file strategy

Python's `pathlib.Path.replace()` is atomic on POSIX (it calls `os.rename()` under the hood). The safest pattern for two related files is:

```python
import tempfile, os

tmp_brief = kittify / f".tmp-brief-{os.getpid()}.md"
tmp_source = kittify / f".tmp-source-{os.getpid()}.yaml"
try:
    tmp_brief.write_text(brief_text, encoding="utf-8")
    tmp_source.write_text(yaml.safe_dump(...), encoding="utf-8")
    tmp_brief.replace(brief_path)
    tmp_source.replace(source_path)
except Exception:
    tmp_brief.unlink(missing_ok=True)
    tmp_source.unlink(missing_ok=True)
    raise
```

Both files are fully written before either replace is called. If the process crashes between the two replaces, at worst only one file is updated — but since the brief and sidecar are read as a pair, any inconsistency is detectable at read time (brief_hash check). The risk window is extremely small (two atomic syscalls).

**Alternative considered**: Write both to a single temp dir and rename the dir. Rejected — adds complexity; the PID-namespaced temp files are simpler and sufficient.

**Decision**: PID-namespaced temp files in the same directory (`kittify/`), both written before either replace.

---

### Finding: File size cap value and placement

5 MB (`5 * 1024 * 1024` bytes) is a reasonable upper bound for a mission brief. Mission briefs are human-written or LLM-generated planning documents; even a very detailed brief should not exceed a few hundred KB. 5 MB provides a 10–50× safety margin.

The constant `MAX_BRIEF_FILE_SIZE_BYTES` belongs in `src/specify_cli/cli/commands/intake.py` at module level. It is also useful in `mission_brief.py` for the same guard. The simplest approach: define it in `intake.py` and import it in `mission_brief.py` (or define a shared constant in a shared location). Given the constraint to not introduce new modules, define it in `intake.py` and reference it from the `_write_brief_from_candidate` path.

**Decision**: `MAX_BRIEF_FILE_SIZE_BYTES = 5 * 1024 * 1024` in `intake.py`. Check `file.stat().st_size > MAX_BRIEF_FILE_SIZE_BYTES` before any `read_text()` call on a brief candidate file. Error message: `"File is too large to ingest ({size:.1f} MB). Maximum allowed size is {MAX_BRIEF_FILE_SIZE_BYTES / 1024 / 1024:.0f} MB."`.

---

### Finding: Path containment check

Python 3.9+ provides `Path.is_relative_to()`. The project requires Python 3.11+, so this is available.

```python
resolved = abs_path.resolve()
repo_resolved = cwd.resolve()
if not resolved.is_relative_to(repo_resolved):
    continue  # silently skip, same as PermissionError
```

This check must be applied:
1. Before the `abs_path.is_file()` branch (direct file case)
2. Inside the directory expansion loop, to each `child` after resolving it

**Alternative considered**: Check `rel_path.parts` for `..` before joining. Rejected — doesn't handle absolute paths or complex traversals. `resolve()` + `is_relative_to()` is the authoritative check.

---

### Finding: Symlink exclusion

`child.is_symlink()` does not follow the link; it returns `True` if `child` itself is a symlink. `child.is_file()` follows links. The fix is to check `is_symlink()` first:

```python
if child.is_symlink():
    continue  # never follow symlinks out of the tree
if child.is_file() and child.suffix == ".md":
    ...
```

No need to also check `child.resolve().is_relative_to(...)` when symlinks are excluded entirely — simpler and more predictable.

**Decision**: Exclude all symlinks in directory expansion. If a future use case requires in-repo symlinks, a separate opt-in can be added.
