---
work_package_id: WP07
work_package_title: GitHub Client and Init Command
subtitle: Extract GitHub operations and refactor init command
subtasks:
  - T060
  - T061
  - T062
  - T063
  - T064
  - T065
  - T066
  - T067
  - T068
  - T069
phases: story-based
priority: P3
lane: planned
tags:
  - github
  - init
  - complex
  - parallel
  - agent-f
history:
  - date: 2025-11-11
    status: created
    by: spec-kitty.tasks
---

# WP07: GitHub Client and Init Command

## Objective

Create a dedicated GitHub client module for API operations and refactor the complex init command into manageable pieces.

## Context

The init command is the largest and most complex command (520+ lines) with GitHub download functionality embedded. This work package extracts GitHub operations and breaks down init.

**Agent Assignment**: Agent F (Days 4-5)

## Requirements from Specification

- Clean GitHub API client
- Init command under 200 lines
- Support all init modes (local/package/remote)
- Maintain all init options

## Implementation Guidance

### T060-T063: Extract GitHub client to template/github_client.py

**T060**: Extract `download_template_from_github()`
- Lines 985-1104 from __init__.py
- Streaming download with progress
- ~120 lines

**T061**: Extract `download_and_extract_template()`
- Lines 1106-1306 from __init__.py
- ZIP extraction and flattening
- Most complex extraction logic
- ~200 lines (may need to split)

**T062**: Extract GitHub auth helpers
```python
def _github_token(cli_token: str | None = None) -> str | None:
    """Return sanitized GitHub token."""
    # Lines 71-73

def _github_auth_headers(cli_token: str | None = None) -> dict:
    """Return Authorization header dict."""
    # Lines 75-78
```

**T063**: Extract `parse_repo_slug()`
- Lines 432-436 from __init__.py
- Parse owner/repo format
- ~5 lines

### T064-T067: Refactor init command to cli/commands/init.py

The init command needs to be broken into logical sections:

**T064**: Extract init command setup
- Command decorator and parameters
- Initial validation
- ~50 lines

**T065**: Extract interactive prompts logic
- AI assistant selection
- Script type selection
- Mission selection
- ~100 lines

**T066**: Extract template mode detection
- Check for local repo
- Check for package installation
- Default to remote
- ~30 lines

**T067**: Extract main orchestration loop
- Template downloading
- Agent asset generation
- Git initialization
- Final reporting
- ~120 lines

### T068-T069: Testing

**T068**: Mock GitHub API for testing
- Mock HTTP responses
- Test download progress
- Test error handling

**T069**: Test init command with all flags
- Test interactive mode
- Test non-interactive mode
- Test all combinations of flags

## Testing Strategy

1. **GitHub client tests**: Mock API responses
2. **Init command tests**: Test all modes and options
3. **Integration tests**: Test full init flow
4. **Edge cases**: Test error handling

## Definition of Done

- [ ] GitHub client extracted and tested
- [ ] Init command refactored and under 200 lines
- [ ] All init modes work (local/package/remote)
- [ ] All init options preserved
- [ ] Tests written with mocked APIs
- [ ] No behavioral changes

## Risks and Mitigations

**Risk**: Init is the most complex command
**Mitigation**: Careful testing, keep original as reference

**Risk**: GitHub API interactions are critical
**Mitigation**: Comprehensive mocking in tests

**Risk**: Many edge cases in init
**Mitigation**: Test each mode separately

## Review Guidance

1. Verify init works in all three modes
2. Check GitHub downloads work correctly
3. Ensure all init options preserved
4. Confirm error handling robust

## Dependencies

- WP03: Needs template system modules

## Dependents

- WP08: Integration will finalize init command