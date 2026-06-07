# Research: Session Presence Multi-Harness Orientation

## 1. Atomic File Writes on All Platforms (NFR-003, C-002)

**Decision**: Use `os.replace(tmp_path, target_path)` for all file writes.

**Rationale**: `os.replace()` is guaranteed atomic on POSIX (single `rename(2)` syscall) and is the closest equivalent on Windows (atomic where OS supports it; always succeeds even if the destination exists). The temp file must be created in the **same directory** as the target so the rename stays on the same filesystem. `Path.write_text()` to a temp path followed by `os.replace()` is the standard Python cross-platform pattern and avoids partial-write corruption on crash.

**Implementation**: `tmp = target.with_suffix(".tmp"); tmp.write_text(content, encoding="utf-8"); os.replace(tmp, target)`

**Alternatives considered**:
- `target.write_text()` directly — not atomic, leaves corrupt file on crash
- `tempfile.NamedTemporaryFile` — cross-directory by default, breaks same-filesystem guarantee

---

## 2. Background Version Check Subprocess (FR-006, NFR-002)

**Decision**: Primary command `uv pip index versions spec-kitty-cli --quiet 2>/dev/null` (most users will have uv); fallback to `pip index versions spec-kitty-cli -q 2>/dev/null | head -1`. Cache result at `~/.kittify/last-cli-check.json`.

**Rationale**: The issues specify both `uv pip index versions` and a curl/jq fallback. `uv` is the project's package manager (see `CLAUDE.md`: `uv sync --frozen --all-extras`), so it will be present in most user environments. Using `pip index` as fallback avoids requiring `curl` + `jq`. Both approaches produce the latest version string from PyPI. The subprocess is spawned with `subprocess.Popen(..., start_new_session=True)` to detach it from the parent process (avoids zombie processes on POSIX; silently ignored on Windows).

**Cache format**: See `contracts/version-cache.md`.

**Failure handling**: Any subprocess error is caught and suppressed. `get_available_version()` returns `None` on first run (no cache) and the last known cached value thereafter, never raising.

**Alternatives considered**:
- Direct `requests.get("https://pypi.org/pypi/spec-kitty-cli/json")` — blocks the hot path even briefly; requires network on the main thread
- `importlib.metadata.version()` for comparison — only gives installed version, not latest

---

## 3. Pattern D Harnesses — SkillsPreambleWriter Target (FR-012)

**Decision**: `SkillsPreambleWriter` defaults to AGENTS.md injection at project root for Pi, Vibe, and Letta.

**Rationale**: The research notes at `architecture/3.x/research/session-presence-harness-gaps.md` document open questions about whether Pi/Vibe/Letta prefer the skills manifest preamble or AGENTS.md. In the absence of a definitive answer, AGENTS.md is the broadest-compatible target: all three harnesses resolve context from AGENTS.md alongside their skills manifest. Using the same `MarkdownRulesWriter` section-append pattern (same markers, same idempotency) means the implementation is trivial and the fallback behavior is identical to Pattern C.

**Refinement path**: When the research notes are resolved for a specific harness, `SkillsPreambleWriter` can be subclassed or parameterized to target the skills manifest preamble instead. The `Writer` protocol makes this a non-breaking change.

**Alternatives considered**:
- Inject into `.agents/skills/spec-kitty.<command>/SKILL.md` preamble — would require knowing the exact skill file layout per harness; risks drift if skill filenames change
- Defer to NullWriter until research is resolved — leaves three harnesses without orientation; unacceptable given FR-012 target

---

## 4. settings.json Hook Merge Strategy (FR-002, C-002)

**Decision**: Read-parse-merge-write with structure preservation. Load the file as JSON (create `{"hooks": {}}` if absent or if JSON is malformed). Traverse to `hooks.SessionStart` (create as empty list if absent). Check if any entry in the list already has `{"type": "command", "command": "spec-kitty session-start"}` (exact match). If not present, append the spec-kitty hook entry. Write back atomically.

**Rationale**: The Claude Code `settings.json` may contain hooks from other tools (e.g., context-mode, sentrux). The merge must be purely additive — no existing entries removed or reordered. Using exact-match checking on the spec-kitty hook object avoids duplicate detection false negatives from shallow comparisons.

**`unregister()` strategy**: Filter out only the exact spec-kitty entry from the SessionStart list. If the list becomes empty after removal, leave `hooks.SessionStart` as an empty list rather than deleting the key (safer; avoids structure drift).

**Alternatives considered**:
- Regex-based detection of the command string — fragile against JSON formatting variations
- Overwrite the entire file — destroys user-configured hooks; unacceptable

---

## 5. `session-start` Exit-0 Guarantee (FR-005, C-003)

**Decision**: Wrap the entire `session_start()` body in a bare `try / except Exception: pass` block. Never re-raise.

**Rationale**: The SessionStart hook fires at the start of every Claude Code session. A non-zero exit or an uncaught exception would surface as an error in the user's session. The command's value is informational only — a silent failure is always preferable to a broken session. The bare `except Exception` is intentional and documented; it is not a code smell in this specific context.

**Testing**: Verify exit 0 by patching `SessionPresenceManager._build_content` to raise an arbitrary exception and asserting `result.exit_code == 0`.

---

## 6. `_find_project_root()` Implementation (FR-004)

**Decision**: Walk up from `Path.cwd()`, checking each ancestor for a `.kittify/` directory. Return the first match or `None` if the filesystem root is reached.

**Rationale**: Standard spec-kitty project detection pattern, consistent with how other commands locate the project root. Must not follow symlinks outside the filesystem tree.

**Edge cases**: Called from a non-project directory (e.g., user's home) → returns `None` → `session-start` exits 0 with no output. Called from inside a worktree → walks up past the worktree to the repo root (`.kittify/` is in the repo root, not the worktree). Both cases validated in tests.
