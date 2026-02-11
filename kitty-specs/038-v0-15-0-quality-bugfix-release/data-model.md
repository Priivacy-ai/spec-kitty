# Data Model: v0.15.0 Bugfix Release

**Feature**: 038-v0-15-0-quality-bugfix-release
**Created**: 2026-02-11
**Purpose**: Define entities and relationships for tracking bug fixes, tests, commits, and releases

## Entity: Bug

**Description**: Represents a GitHub issue reporting a bug that needs to be fixed in this release.

**Attributes**:
- `issue_number` (integer, required): GitHub issue number (e.g., 95, 120)
- `title` (string, required): Short bug description
- `reporter` (string, required): GitHub username who reported (e.g., @MRiabov)
- `priority` (enum, required): P1 (critical) or P2 (medium)
- `risk_level` (enum, required): LOW, MEDIUM, or HIGH
- `file_location` (string, required): Source file path + line numbers
- `fix_description` (string, required): What the fix does
- `test_count` (integer, required): Number of tests written for this bug
- `fix_order` (integer, required): Order in which bug is fixed (1-7)

**Validation Rules**:
- `issue_number` must match actual GitHub issue
- `priority` determines urgency (P1 fixed first)
- `risk_level` determines testing rigor (HIGH requires more integration tests)
- `file_location` must be accurate path in spec-kitty repo
- `test_count` must be >= 3 (minimum coverage per bug)

**States**: reported → fixing (test written) → fixed (test green) → released → closed (thank-you sent)

**Example**:
```json
{
  "issue_number": 95,
  "title": "Kebab-case validation",
  "reporter": "@MRiabov",
  "priority": "P1",
  "risk_level": "LOW",
  "file_location": "src/specify_cli/cli/commands/agent/feature.py:224-288",
  "fix_description": "Add regex validation for feature slugs before directory creation",
  "test_count": 8,
  "fix_order": 1
}
```

---

## Entity: Commit

**Description**: Represents a git commit containing a bug fix and its tests.

**Attributes**:
- `sha` (string, required): Git commit SHA (40 characters)
- `message` (string, required): Commit message following format: `fix: {description} (fixes #{number})`
- `branch` (enum, required): main or 2.x
- `bug_number` (integer, required): Which bug this commit fixes
- `files_changed` (array, required): List of file paths modified
- `lines_added` (integer): Lines added (code + tests)
- `lines_removed` (integer): Lines removed
- `test_files_included` (array, required): Test files added in this commit
- `cherry_pick_status` (enum): direct, needs_adaptation, manual_port, or not_applicable

**Relationships**:
- Commit → Bug (one-to-one: each commit fixes exactly one bug)
- Main Commit → 2.x Commit (cherry-pick link via `-x` flag)

**Validation Rules**:
- `message` must include `fixes #{number}`
- `files_changed` must include at least one source file and one test file
- For 2.x commits: if `cherry_pick_status = direct`, verify `-x` flag in commit message

**Example**:
```json
{
  "sha": "abc123...",
  "message": "fix: enforce kebab-case validation for feature slugs (fixes #95)",
  "branch": "main",
  "bug_number": 95,
  "files_changed": ["src/specify_cli/cli/commands/agent/feature.py", "tests/specify_cli/cli/commands/test_feature_slug_validation.py"],
  "lines_added": 45,
  "lines_removed": 2,
  "test_files_included": ["tests/specify_cli/cli/commands/test_feature_slug_validation.py"],
  "cherry_pick_status": "direct"
}
```

---

## Entity: Test

**Description**: Represents a test case validating a bug fix.

**Attributes**:
- `file_path` (string, required): Location in tests/ directory
- `test_name` (string, required): Function name (e.g., `test_invalid_slug_rejected`)
- `test_type` (enum, required): unit, integration, or regression
- `bug_number` (integer, required): Which bug this test validates
- `coverage_target` (string, required): Specific code path being tested
- `pass_status` (enum, required): red (failing before fix), green (passing after fix)
- `branch_compatibility` (enum, required): both, main_only, 2x_only, or needs_adaptation

**Relationships**:
- Test → Bug (many-to-one: multiple tests per bug)
- Test → Commit (embedded: created in same commit as fix)

**Validation Rules**:
- Unit tests must start with `test_`
- Integration tests must be in `tests/integration/`
- Regression tests must fail before fix, pass after fix
- Each bug must have minimum 3 tests (various edge cases)

**Example**:
```json
{
  "file_path": "tests/specify_cli/cli/commands/test_feature_slug_validation.py",
  "test_name": "test_invalid_slug_with_spaces_rejected",
  "test_type": "unit",
  "bug_number": 95,
  "coverage_target": "feature.py:create_feature() validation logic",
  "pass_status": "green",
  "branch_compatibility": "both"
}
```

---

## Entity: Release

**Description**: Represents a version release on main or 2.x branch.

**Attributes**:
- `version` (string, required): Semantic version (e.g., "0.15.0", "2.0.0a2")
- `branch` (enum, required): main or 2.x
- `release_date` (datetime, required): When release was tagged
- `bugs_fixed` (array, required): List of bug issue numbers (e.g., [95, 120, 117, 124, 119, 122, 123])
- `commits_included` (array, required): List of commit SHAs
- `tests_added` (integer, required): Total new tests in this release
- `pypi_published` (boolean, required): Whether published to PyPI
- `github_release_url` (string, optional): URL to GitHub release page

**Relationships**:
- Release → Commits (one-to-many: includes 7-9 commits)
- Release → Bugs (one-to-many: fixes 7 bugs)
- Release → Tests (one-to-many: includes 54+ tests)
- Main Release → 2.x Release (cherry-pick relationship)

**Validation Rules**:
- `version` must follow semver (main: 0.x.y, 2.x: 2.0.0aX)
- `bugs_fixed` count must match commits_included count (minus version bump commit)
- `tests_added` must be >= 54 (comprehensive coverage)
- Both main and 2.x must have corresponding releases

**Example**:
```json
{
  "version": "0.15.0",
  "branch": "main",
  "release_date": "2026-02-11T18:00:00Z",
  "bugs_fixed": [95, 120, 117, 124, 119, 122, 123],
  "commits_included": ["sha1", "sha2", "sha3", "sha4", "sha5", "sha6", "sha7", "sha8"],
  "tests_added": 54,
  "pypi_published": true,
  "github_release_url": "https://github.com/Priivacy-ai/spec-kitty/releases/tag/v0.15.0"
}
```

---

## Entity: ContributorAcknowledgment

**Description**: Represents thank-you communication to bug reporters.

**Attributes**:
- `github_username` (string, required): Reporter's GitHub handle
- `issue_numbers` (array, required): Issues they reported
- `thank_you_sent` (boolean, required): Whether thank-you message posted
- `message_timestamp` (datetime, optional): When message was posted
- `message_template_used` (enum, required): general_announcement or per_issue

**Relationships**:
- ContributorAcknowledgment → Bugs (one-to-many: contributor may have reported multiple)
- ContributorAcknowledgment → Release (many-to-one: acknowledged in release notes)

**Validation Rules**:
- All 7 bugs must have corresponding acknowledgment
- `thank_you_sent` must be true before release is considered complete
- Message must use user's voice (template provided in plan)

**Example**:
```json
{
  "github_username": "MRiabov",
  "issue_numbers": [95],
  "thank_you_sent": true,
  "message_timestamp": "2026-02-11T19:00:00Z",
  "message_template_used": "per_issue"
}
```

---

## Relationships Diagram

```
Release (0.15.0)
  ├── contains → Commit #1 (Bug #95 fix)
  │   ├── fixes → Bug #95
  │   └── includes → Test (8 tests for #95)
  ├── contains → Commit #2 (Bug #120 fix)
  │   ├── fixes → Bug #120
  │   └── includes → Test (6 tests for #120)
  ├── contains → Commit #3 (Bug #117 fix)
  │   ├── fixes → Bug #117
  │   └── includes → Test (10 tests for #117)
  ├── contains → Commit #4 (Bug #124 fix)
  │   ├── fixes → Bug #124
  │   └── includes → Test (5 tests for #124)
  ├── contains → Commit #5 (Bug #119 fix)
  │   ├── fixes → Bug #119
  │   └── includes → Test (5 tests for #119)
  ├── contains → Commit #6 (Bug #122 fix)
  │   ├── fixes → Bug #122
  │   └── includes → Test (8 tests for #122)
  ├── contains → Commit #7 (Bug #123 fix)
  │   ├── fixes → Bug #123
  │   └── includes → Test (12 tests for #123)
  └── contains → Commit #8 (Version bump)

Release (0.15.0)
  └── cherry-picked to → Release (2.0.0a2)
      ├── contains → Commit #1 (cherry-picked with -x)
      ├── contains → Commit #2 (cherry-picked with -x)
      ├── contains → Commit #3 (cherry-picked with -x)
      ├── contains → Commit #4 (cherry-picked with -x)
      ├── contains → Commit #5 (manually ported - file divergence)
      ├── contains → Commit #6 (cherry-picked with -x)
      ├── contains → Commit #7 (cherry-picked with -x)
      └── contains → Commit #8 (new version bump for 2.x)

Contributors
  ├── @brkastner → Bug #123
  ├── @umuteonder → Bug #122, #120
  ├── @MRiabov → Bug #95
  ├── @digitalanalyticsdeveloper → Bug #117
  └── @fabiodouek → Bug #119, #124
      └── acknowledged in → Release (0.15.0)
```

---

## State Transitions

### Bug Lifecycle

```
[reported] → [fixing] → [fixed] → [released] → [closed]
   ↓            ↓          ↓          ↓           ↓
Issue      Test RED   Test GREEN  PyPI pub   Thank-you
opened                                         posted
```

### Commit Lifecycle (Main)

```
[created] → [tested] → [merged] → [tagged] → [published]
    ↓          ↓          ↓          ↓           ↓
Fix code   CI green   PR merged  v0.15.0    PyPI live
+ tests
```

### Commit Lifecycle (2.x)

```
[cherry-picked] → [adapted] → [tested] → [merged] → [tagged] → [published]
       ↓             ↓           ↓          ↓          ↓           ↓
Copy from main  Fix for 2.x  CI green  PR merged  v2.0.0a2   PyPI live
                (if needed)
```

---

## Notes

**Test-First Discipline**: Each commit must include both fix and tests (atomic, one per bug)

**Cherry-Pick Audit Trail**: Use `-x` flag for traceability (appends "cherry picked from commit <sha>")

**2.x Divergence**: Only Bug #119 needs manual porting (acceptance_core.py → acceptance.py)

**Version Strategy**:
- main: Patch version bump (0.14.2 → 0.15.0)
- 2.x: Alpha increment (2.0.0a1 → 2.0.0a2)
- Reserve 0.15.1+ only for post-release regressions

**Contributor Recognition**:
- 5 unique contributors reported 7 bugs
- Personalized thank-you in user's voice
- Acknowledged by name in release notes
