---
work_package_id: "WP05"
subtasks: ["T070", "T071", "T072", "T073", "T074", "T075", "T076", "T077", "T078", "T079", "T080", "T081", "T082", "T083", "T084", "T085", "T086", "T087", "T088", "T089", "T090", "T091"]
title: "Release Packaging Commands"
phase: "Phase 5 - Release Commands (Stream D)"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-17T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 – Release Packaging Commands

## Objectives & Success Criteria

**Goal**: Migrate GitHub Actions CI bash scripts to Python for testability and reliability.

**Success Criteria**:
- `spec-kitty agent build-release --dry-run --json` executes full workflow
- Version alignment validation (git tag, pyproject.toml, CHANGELOG.md)
- All 6 GitHub Actions bash scripts eliminated
- Works in CI/CD environment (GitHub Actions)
- 90%+ test coverage for `release.py`

---

## Context & Constraints

**Prerequisites**: WP01 complete ✅
**Stream Assignment**: Stream D (Agent Delta) - Parallel with WP02, WP03, WP04
**Files Owned**: 
- `src/specify_cli/cli/commands/agent/release.py`
- `src/specify_cli/core/release.py`
- `.github/workflows/release.yml` (update to call Python commands)

**Bash scripts to replace** (6 scripts in `.github/workflows/scripts/`):
- `get-next-version.sh`
- `update-version.sh`
- `generate-release-notes.sh`
- `create-release-packages.sh`
- `create-github-release.sh`
- `validate-version-alignment.sh`

---

## Subtasks & Detailed Guidance

### T070-T075 – Create release.py module with utilities

**T070**: Create `src/specify_cli/core/release.py` module

**Validation Step**: Before implementing release utilities, verify `.github/workflows/scripts/` directory exists:
```bash
ls .github/workflows/scripts/ 2>/dev/null || echo "Directory not found - will skip in T101"
```
If directory doesn't exist, document in release.py that GitHub Actions migration (T091) may not have bash scripts to replace.

**T071**: Implement `get_next_version(repo_root)`:
```python
def get_next_version(repo_root: Path) -> str:
    """Determine next semantic version from git tags."""
    # Run: git tag -l "v*" --sort=-version:refname
    result = subprocess.run(
        ["git", "tag", "-l", "v*", "--sort=-version:refname"],
        capture_output=True,
        text=True,
        cwd=repo_root
    )
    tags = result.stdout.strip().split("\n")
    if not tags or tags[0] == "":
        return "0.1.0"
    
    latest = tags[0].lstrip("v")
    # Parse semantic version, increment patch
    major, minor, patch = map(int, latest.split("."))
    return f"{major}.{minor}.{patch + 1}"
```

**T072**: Implement `update_version(repo_root, version)`:
- Update `pyproject.toml` version field
- Use `toml` or `tomli` library for parsing

**T073**: Implement `generate_release_notes(repo_root, version)`:
- Parse `CHANGELOG.md` for version section
- Or generate from git log: `git log --oneline v1.0.0..HEAD`

**T074**: Implement `create_release_packages(repo_root, version)`:
- Run build commands: `python -m build`
- Verify dist/ artifacts created

**T075**: Implement `create_github_release(version, notes)`:
- Use `gh` CLI: `gh release create v{version} --notes "{notes}"`
- Or use GitHub API via `httpx` library

---

### T076-T081 – Implement build-release command

**T076**: Create command in `src/specify_cli/cli/commands/agent/release.py`:
```python
@app.command(name="build-release")
def build_release(
    version: Annotated[Optional[str], typer.Option("--version")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Execute full release workflow (build, package, publish)."""
    try:
        repo_root = locate_project_root()
        
        # Auto-detect version if not provided
        if version is None:
            version = get_next_version(repo_root)
        
        # Validate version alignment
        validate_version_alignment(repo_root, version)
        
        # Update version in files
        if not dry_run:
            update_version(repo_root, version)
        
        # Generate release notes
        notes = generate_release_notes(repo_root, version)
        
        # Create packages
        if not dry_run:
            create_release_packages(repo_root, version)
        
        # Create GitHub release
        if not dry_run:
            create_github_release(version, notes)
        
        if json_output:
            print(json.dumps({
                "result": "success",
                "version": version,
                "dry_run": dry_run
            }))
        else:
            if dry_run:
                console.print(f"[yellow]Dry run:[/yellow] Would release v{version}")
            else:
                console.print(f"[green]✓[/green] Released v{version}")
    except Exception as e:
        # Error handling...
```

**T077-T081**: Add flags, validation, dual output

---

### T082-T091 – Testing and CI integration

**T082-T087**: Unit tests:
- Test version detection with various tag patterns
- Test pyproject.toml manipulation
- Test release notes generation
- Test package creation (mocked)
- Test GitHub release creation (mocked API)
- Test command with all flags

**T088-T089**: Integration tests:
- Full release workflow in dry-run mode
- Release command from CI environment (GitHub Actions)

**T090**: Verify 90%+ coverage

**T091**: Update `.github/workflows/release.yml`:
```yaml
- name: Build Release
  run: spec-kitty agent build-release --json
```

---

## Risks & Mitigations

**Risk**: GitHub API rate limits in CI/CD
**Mitigation**: Use `gh` CLI (respects auth tokens), implement retry with exponential backoff

**Risk**: Version alignment validation complexity
**Mitigation**: Check git tag == pyproject.toml == CHANGELOG.md, fail early with clear error

---

## Definition of Done Checklist

- [ ] All utilities implemented (T070-T075)
- [ ] build-release command implemented (T076-T081)
- [ ] Unit tests passing (T082-T087)
- [ ] Integration tests passing (T088-T089)
- [ ] 90%+ coverage achieved (T090)
- [ ] GitHub Actions workflow updated (T091)
- [ ] Dry-run mode validated (no side effects)

---

## Activity Log

- 2025-12-17T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
