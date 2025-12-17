---
work_package_id: "WP03"
subtasks:
  - "T012"
  - "T013"
  - "T014"
  - "T015"
  - "T016"
title: "Status Command & Dashboard"
phase: "Phase 1 - Core Implementation"
lane: "for_review"
assignee: ""
agent: "claude"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-17T13:15:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
  - timestamp: "2025-12-17T16:30:00Z"
    lane: "for_review"
    agent: "claude"
    shell_pid: ""
    action: "Implementation complete - scanner and acceptance updated"
activity_log: |
  - 2025-12-17T13:15:00Z – system – lane=planned – Prompt created
  - 2025-12-17T16:30:00Z – claude – lane=for_review – Implementation complete
---

# Work Package Prompt: WP03 – Status Command & Dashboard

## Objectives & Success Criteria

Enhance the status command and update dashboard scanner to read lanes from frontmatter:
1. Status command shows WPs grouped by `lane:` frontmatter value
2. Auto-detect current feature from worktree/branch when argument omitted
3. Dashboard scanner reads lane from frontmatter, not directory

**Success Criteria** (from spec FR-006 to FR-008, SC-003, SC-006):
- `tasks_cli.py status 007-feature` shows all WPs grouped by lane
- `tasks_cli.py status` (no arg) auto-detects feature from worktree
- Status returns within 1 second for features with 50 WPs
- Dashboard displays WPs in correct lane columns based on frontmatter

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/007-frontmatter-only-lane/spec.md` (User Stories 2 & 5)
- Research: `kitty-specs/007-frontmatter-only-lane/research.md`

**Key Files**:
- `scripts/tasks/tasks_cli.py` - status command
- `src/specify_cli/dashboard/scanner.py` - `scan_feature_kanban()`, `scan_all_features()`
- `src/specify_cli/acceptance.py` - lane collection for acceptance checks

**Dependencies**: WP01 (lane utilities)

**Can run in parallel with**: WP02, WP04

## Subtasks & Detailed Guidance

### Subtask T012 – Enhance status command with lane grouping

**Purpose**: Provide clear visibility of WP lane distribution.

**Steps**:
1. Open `scripts/tasks/tasks_cli.py`
2. Find or create `status_command()` function
3. Implement formatted output:
   ```python
   @app.command("status")
   def status_command(
       feature: Optional[str] = typer.Argument(None, help="Feature name (auto-detected if omitted)")
   ):
       """Show work package status grouped by lane."""
       repo_root = find_repo_root()

       # Auto-detect feature if not provided (T013)
       if feature is None:
           feature = detect_feature_from_context(repo_root)
           if feature is None:
               console.print("[red]Error: Could not detect feature. Please specify feature name.[/red]")
               raise typer.Exit(1)

       tasks_dir = repo_root / "kitty-specs" / feature / "tasks"
       if not tasks_dir.exists():
           console.print(f"[red]Error: tasks/ directory not found for feature '{feature}'[/red]")
           raise typer.Exit(1)

       # Group WPs by lane
       wps_by_lane = {lane: [] for lane in LANES}
       for wp_file in tasks_dir.glob("WP*.md"):
           content = wp_file.read_text()
           frontmatter, _ = split_frontmatter(content)
           lane = get_lane_from_frontmatter(wp_file)
           wp_id = frontmatter.get("work_package_id", "???")
           title = frontmatter.get("title", wp_file.stem)
           wps_by_lane[lane].append((wp_id, title))

       # Display
       console.print(f"\n[bold]Feature: {feature}[/bold]\n")
       for lane in LANES:
           count = len(wps_by_lane[lane])
           console.print(f"[bold]{lane.upper()}[/bold] ({count})")
           if wps_by_lane[lane]:
               for wp_id, title in sorted(wps_by_lane[lane]):
                   console.print(f"  {wp_id}  {title}")
           else:
               console.print("  [dim](none)[/dim]")
           console.print()
   ```

**Files**: `scripts/tasks/tasks_cli.py` (MODIFY)

**Parallel?**: No, core implementation

### Subtask T013 – Add auto-detect feature from worktree

**Purpose**: Convenience for users working in feature worktrees.

**Steps**:
1. Create helper function:
   ```python
   def detect_feature_from_context(repo_root: Path) -> Optional[str]:
       """Detect feature name from current branch or worktree path.

       Detection priority:
       1. Parse from current git branch (e.g., "007-frontmatter-only-lane")
       2. Parse from worktree path (e.g., ".worktrees/007-feature-name")
       """
       # Try git branch
       try:
           result = subprocess.run(
               ["git", "branch", "--show-current"],
               cwd=repo_root,
               capture_output=True,
               text=True,
               check=True
           )
           branch = result.stdout.strip()
           if branch and branch != "main":
               # Verify this feature exists
               feature_path = repo_root / "kitty-specs" / branch
               if feature_path.exists():
                   return branch
       except subprocess.CalledProcessError:
           pass

       # Try worktree path detection
       cwd = Path.cwd()
       if ".worktrees" in str(cwd):
           # Extract feature name from path
           parts = str(cwd).split(".worktrees/")
           if len(parts) > 1:
               feature_part = parts[1].split("/")[0]
               feature_path = repo_root / "kitty-specs" / feature_part
               if feature_path.exists():
                   return feature_part

       return None
   ```
2. Integrate with status_command (done in T012)

**Files**: `scripts/tasks/tasks_cli.py` (MODIFY)

**Parallel?**: Yes, utility function

### Subtask T014 – Update scan_feature_kanban() for frontmatter

**Purpose**: Dashboard kanban view reads lane from frontmatter.

**Steps**:
1. Open `src/specify_cli/dashboard/scanner.py`
2. Find `scan_feature_kanban()` function (around line 293-370)
3. Replace directory-based logic:
   ```python
   # OLD (around line 310-315):
   for lane in lanes.keys():
       lane_dir = tasks_dir / lane
       if lane_dir.exists():
           for prompt_file in lane_dir.rglob("WP*.md"):
               ...

   # NEW:
   def scan_feature_kanban(feature_dir: Path) -> Dict[str, List[Dict]]:
       """Scan feature for kanban board data, reading lanes from frontmatter."""
       tasks_dir = feature_dir / "tasks"
       lanes = {lane: [] for lane in ["planned", "doing", "for_review", "done"]}

       if not tasks_dir.exists():
           return lanes

       # Scan flat tasks/ directory
       for wp_file in tasks_dir.glob("WP*.md"):
           content = wp_file.read_text()
           frontmatter = parse_frontmatter(content)

           # Get lane from frontmatter, default to "planned"
           lane = frontmatter.get("lane", "planned")
           if lane not in lanes:
               lane = "planned"  # Fallback for invalid lanes

           lanes[lane].append({
               "id": frontmatter.get("work_package_id", wp_file.stem),
               "title": frontmatter.get("title", "Untitled"),
               "file": wp_file.name,
               "assignee": frontmatter.get("assignee", ""),
               "lane": lane,
               # ... other fields as needed
           })

       return lanes
   ```

**Files**: `src/specify_cli/dashboard/scanner.py` (MODIFY)

**Parallel?**: No, core dashboard change

### Subtask T015 – Update scan_all_features() for frontmatter

**Purpose**: Feature list view counts WPs by frontmatter lane.

**Steps**:
1. Find `scan_all_features()` function (around line 235-290)
2. Update lane counting logic:
   ```python
   # OLD (around line 259-267):
   for lane in ["planned", "doing", "for_review", "done"]:
       lane_dir = tasks_dir / lane
       if lane_dir.exists():
           count = len(list(lane_dir.rglob("WP*.md")))

   # NEW:
   def count_wps_by_lane(tasks_dir: Path) -> Dict[str, int]:
       """Count work packages by lane from frontmatter."""
       counts = {lane: 0 for lane in ["planned", "doing", "for_review", "done"]}

       if not tasks_dir.exists():
           return counts

       for wp_file in tasks_dir.glob("WP*.md"):
           content = wp_file.read_text()
           frontmatter = parse_frontmatter(content)
           lane = frontmatter.get("lane", "planned")
           if lane in counts:
               counts[lane] += 1

       return counts
   ```
3. Integrate into `scan_all_features()` where lane counts are needed

**Files**: `src/specify_cli/dashboard/scanner.py` (MODIFY)

**Parallel?**: Yes, can be done alongside T014

### Subtask T016 – Update acceptance.py lane collection

**Purpose**: Acceptance checks must read lanes from frontmatter.

**Steps**:
1. Open `src/specify_cli/acceptance.py`
2. Find where `lanes` dict is populated (look for `AcceptanceSummary`)
3. Update to read from frontmatter:
   ```python
   def collect_wp_lanes(feature_dir: Path) -> Dict[str, List[str]]:
       """Collect work package IDs grouped by lane from frontmatter."""
       tasks_dir = feature_dir / "tasks"
       lanes = {lane: [] for lane in ["planned", "doing", "for_review", "done"]}

       if not tasks_dir.exists():
           return lanes

       for wp_file in tasks_dir.glob("WP*.md"):
           content = wp_file.read_text()
           frontmatter = parse_frontmatter(content)
           lane = frontmatter.get("lane", "planned")
           wp_id = frontmatter.get("work_package_id", wp_file.stem)

           if lane in lanes:
               lanes[lane].append(wp_id)

       return lanes
   ```
4. Update `AcceptanceSummary` initialization to use this function

**Files**: `src/specify_cli/acceptance.py` (MODIFY)

**Parallel?**: Yes, independent of scanner changes

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Performance degradation | Test with 50 WPs; frontmatter parsing should be fast |
| Dashboard breaking | Test dashboard after changes; verify all views work |
| Auto-detect fails silently | Clear error message when detection fails |

## Definition of Done Checklist

- [ ] `status` command shows WPs grouped by frontmatter lane
- [ ] Auto-detect feature from worktree/branch works
- [ ] `scan_feature_kanban()` reads lane from frontmatter
- [ ] `scan_all_features()` counts WPs by frontmatter lane
- [ ] `acceptance.py` collects lanes from frontmatter
- [ ] Status command returns in <1 second for 50 WPs
- [ ] Dashboard correctly displays WPs in lane columns

## Review Guidance

- Test `tasks_cli.py status` from worktree (should auto-detect)
- Test `tasks_cli.py status 007-feature` explicitly
- Verify dashboard kanban view shows correct lane assignments
- Check performance with multiple WP files
