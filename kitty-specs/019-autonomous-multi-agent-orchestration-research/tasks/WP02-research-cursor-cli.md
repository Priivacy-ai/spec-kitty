---
work_package_id: "WP02"
subtasks:
  - "T006"
  - "T007"
  - "T008"
  - "T009"
  - "T010"
title: "Research Cursor CLI"
phase: "Phase 1 - Agent Investigation"
lane: "for_review"
assignee: ""
agent: "opencode"
shell_pid: "21385"
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-01-18T14:41:27Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – Research Cursor CLI

## Objectives & Success Criteria

**USER PRIORITY**: Specifically investigate Cursor's CLI capabilities as explicitly requested.

Cursor is a popular AI-native IDE (VS Code fork). The user believes it has a CLI tool - find it and document it.

**Success Criteria**:
- Cursor CLI documented with working invocation example OR confirmed as IDE-only
- If CLI exists: Full capability documentation (task input, completion detection, parallel support)
- If no CLI: Document any API alternatives or workarounds

## Context & Constraints

- **Priority**: User specifically requested this research
- **Challenge**: Cursor is primarily an IDE - headless operation is uncertain
- **Scope**: Headless/CLI only (not interested in IDE features)

Reference documents:
- `kitty-specs/019-autonomous-multi-agent-orchestration-research/spec.md` - RQ-6 specifically about Cursor
- `kitty-specs/019-autonomous-multi-agent-orchestration-research/plan.md` - Research template

## Subtasks & Detailed Guidance

### Subtask T006 – Search for Cursor CLI Documentation

**Purpose**: Find official documentation about Cursor's CLI capabilities.

**Steps**:
1. Visit https://cursor.com/docs (or current documentation site)
2. Search for "CLI", "command line", "terminal", "headless"
3. Check Cursor GitHub/Discord for CLI announcements
4. Search npm/pip for `cursor` or `cursor-cli` packages
5. Check Homebrew: `brew search cursor`
6. Web search: "Cursor IDE CLI tool 2026"

**Files**: Note findings in `research/04-cursor.md`

**Key Questions**:
- Is there official CLI documentation?
- Any community tools or wrappers?
- Is CLI a paid/enterprise feature?

---

### Subtask T007 – Check Cursor.app for Embedded CLI Tools

**Purpose**: Inspect Cursor application bundle for CLI binaries.

**Steps** (macOS):
1. Check if Cursor is installed: `ls /Applications/Cursor.app`
2. Explore app bundle:
   ```bash
   ls -la /Applications/Cursor.app/Contents/Resources/
   ls -la /Applications/Cursor.app/Contents/Resources/app/bin/
   ls -la /Applications/Cursor.app/Contents/MacOS/
   ```
3. Look for binaries: `cursor`, `cursor-cli`, `agent`, similar
4. Check shell integration:
   ```bash
   cat /usr/local/bin/cursor 2>/dev/null || cat ~/.local/bin/cursor 2>/dev/null
   ```
5. Check PATH for cursor command: `which cursor`

**Steps** (Linux):
1. Check common install locations
2. Look for shell commands in `/usr/bin/`, `/usr/local/bin/`

**Files**: Document findings in `research/04-cursor.md`

**Key Questions**:
- Does Cursor install a shell command like VS Code's `code` command?
- Is there an agent mode binary?

---

### Subtask T008 – Test Cursor CLI Commands

**Purpose**: If CLI exists, test its capabilities.

**Steps** (if `cursor` command found):
1. Run `cursor --help` and capture full output
2. Run `cursor --version`
3. Test opening a folder: `cursor /path/to/project`
4. Look for agent/AI subcommands: `cursor ai --help`, `cursor agent --help`
5. Check for prompt/task flags
6. Test with simple prompt if available

**If no CLI found**:
- Document as "No CLI available"
- Note any alternative approaches discovered

**Files**: Add CLI test results to `research/04-cursor.md`

---

### Subtask T009 – Document Headless Invocation Method

**Purpose**: If CLI has AI capabilities, document how to use it for automation.

**Steps** (if agent CLI exists):
1. Document exact command to invoke AI agent
2. Test task input methods:
   - Command line argument: `cursor agent "Do something"`
   - File input: `cursor agent --file task.md`
   - Stdin: `cat task.md | cursor agent`
3. Document output format (stdout, files, JSON)
4. Test exit codes (success, failure)
5. Check for workspace/project context handling
6. Document authentication requirements

**If no headless AI mode**:
- Check for API access
- Check for Extension Host CLI
- Document limitations

**Files**: Update `research/04-cursor.md` with task specification section

---

### Subtask T010 – Write Cursor Research File

**Purpose**: Complete the research file following template.

**Steps**:
1. Ensure all sections from plan.md template are filled
2. Add source links (documentation URLs, forum posts)
3. Write orchestration assessment:
   - Can participate in autonomous workflow? Yes/No/Partial
   - Limitations
   - Integration complexity
4. Provide clear verdict on Cursor CLI viability

**Files**: Complete `research/04-cursor.md`

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Cursor is IDE-only | Document clearly, note for orchestration limitations |
| CLI exists but undocumented | Test empirically, note "unofficial" status |
| CLI requires paid tier | Document tier requirements |
| Cursor changes frequently | Note version tested, date of research |

## Definition of Done Checklist

- [x] Official documentation searched
- [x] Cursor.app inspected for CLI binaries
- [x] CLI commands tested (if found)
- [x] Headless invocation method documented (or confirmed unavailable)
- [x] Research file `research/04-cursor.md` complete
- [x] Orchestration assessment completed
- [x] Source links included
- [x] Clear verdict on Cursor CLI viability provided

## Review Guidance

- Verify Cursor search was thorough (multiple sources checked)
- If CLI found, verify commands actually work
- If no CLI, confirm alternative approaches documented
- This is a user priority - ensure comprehensive investigation

## Activity Log

- 2026-01-18T14:41:27Z – system – lane=planned – Prompt created.
- 2026-01-18T15:14:22Z – claude – shell_pid=16561 – lane=doing – Started implementation via workflow command
- 2026-01-18T15:18:17Z – claude – shell_pid=16561 – lane=for_review – Cursor CLI fully documented. Found `cursor agent -p` with headless mode, JSON output, --force for edits. Known quirks: CLI can hang, stdin issues. Integration: Medium (workarounds needed).
- 2026-01-18T15:25:41Z – opencode – shell_pid=21385 – lane=doing – Started implementation via workflow command
- 2026-01-18T15:32:28Z – opencode – shell_pid=21385 – lane=for_review – Ready for review: Cursor CLI headless research documented
