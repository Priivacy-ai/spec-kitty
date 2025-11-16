---
work_package_id: "WP09"
subtasks:
  - "T062"
  - "T063"
  - "T064"
  - "T065"
  - "T066"
  - "T067"
title: "Dashboard Mission Display"
phase: "Phase 5 - Polish"
lane: "done"
review_status: ""
reviewed_by: "codex"
assignee: "codex"
agent: "codex"
shell_pid: "37165"
history:
  - timestamp: "2025-01-16T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

## Review Feedback

**Status**: ✅ **Approved**

**Key Checks**:
1. `APIHandler.handle_root()` now loads the active mission (via `get_active_mission`) and passes it to `get_dashboard_html(mission_context=...)`, so the initial HTML payload seeds `window.__INITIAL_MISSION__` before any dashboard JavaScript runs. This satisfies T062 and the R3 hybrid decision (server render + manual refresh) because the mission badge renders immediately, even if `/api/features` is slow or offline.
2. `dashboard.js` reads `window.__INITIAL_MISSION__` into `activeMission` before the first `updateMissionDisplay()` call, and the refresh button simply reloads the page, so the mission display remains consistent with the `/api/features` payload on subsequent refreshes.

**Validation**:
- `python3 - <<'PY' ... src/specify_cli/dashboard/templates/__init__.py` (see review log) confirmed `get_dashboard_html()` now embeds the mission JSON inline, proving the placeholder replacement works outside the HTTP server.

# Work Package Prompt: WP09 – Dashboard Mission Display

## Objectives & Success Criteria

**Goal**: Add active mission display to spec-kitty dashboard header, making it visible which domain mode is active without running CLI commands.

**Success Criteria**:
- Dashboard displays active mission name prominently (header or sidebar)
- Mission display updates when mission switched (after page refresh)
- Optional: Refresh button for manual update
- Design is prominent but not obtrusive (per user guidance: "resist complication")
- Works with both software-dev and research missions
- No mission-specific UI changes (dashboard remains generic)
- All 6 subtasks (T062-T067) completed

## Context & Constraints

**Problem Statement**: Users can't see active mission when viewing dashboard:
- Must run `spec-kitty mission current` in terminal
- Risk of confusion when switching between research and software work
- No visual confirmation of current mode

**User Story** (Spec User Story 7):
> "I want to see the currently active mission displayed prominently, so I know which domain mode my current work is using without running CLI commands."

**Supporting Documents**:
- Spec: `kitty-specs/005-refactor-mission-system/spec.md` (User Story 7, FR-027 through FR-029)
- Research: `kitty-specs/005-refactor-mission-system/research.md` (R3: Dashboard integration - Hybrid approach selected)

**Design Decision from Research**:
- **Approach**: Hybrid (server-side rendering + manual refresh button)
- **Rationale**: Aligns with "resist complication" guidance, mission switching is infrequent
- **Implementation**: Add mission to template context on page load, optional refresh button

**User Guidance Constraints**:
> "If there are clear cases where the dashboard should adapt, it should adapt, but we should resist the urge to complicate the dashboard unless necessary."

**Dashboard Technology Stack** (current):
- Backend: FastAPI or similar Python web framework
- Templates: Jinja2 or similar templating
- Frontend: HTML/CSS/JavaScript (minimal)
- Real-time updates: WebSocket for feature status (existing)

**Existing Dashboard Features**:
- Project name displayed
- Feature overview (kanban lanes)
- Work package status
- Real-time updates via WebSocket

**Location**: `src/specify_cli/dashboard/server.py` and associated templates

## Subtasks & Detailed Guidance

### Subtask T062 – Update server.py with mission context

**Purpose**: Add active mission to dashboard server context.

**Steps**:
1. Locate dashboard server file: `src/specify_cli/dashboard/server.py`
2. Find main route handler (likely `/` or `/index`)
3. Add mission to template context:
   ```python
   from specify_cli.mission import get_active_mission, MissionError

   @app.get("/")
   async def index(request: Request):
       """Dashboard index page."""
       project_root = get_project_root()  # Existing function

       # Load active mission
       try:
           mission = get_active_mission(project_root)
           mission_context = {
               "name": mission.name,
               "domain": mission.domain,
               "version": mission.version,
               "path": str(mission.path)
           }
       except MissionError:
           # Fallback if mission can't be loaded
           mission_context = {
               "name": "Unknown",
               "domain": "unknown",
               "version": "0.0.0",
               "path": ""
           }

       # Add to existing template context
       context = {
           "request": request,
           "project_name": project_root.name,
           "active_mission": mission_context,  # NEW
           # ... other existing context
       }

       return templates.TemplateResponse("index.html", context)
   ```

4. Test server starts: `spec-kitty dashboard`
5. Verify mission in template context: Add debug print temporarily

**Files**: `src/specify_cli/dashboard/server.py`

**Parallel?**: No (backend foundation for frontend changes)

**Notes**: Follow existing pattern for context loading. Don't break existing functionality.

---

### Subtask T063 – Update dashboard HTML template

**Purpose**: Display mission name in dashboard UI.

**Steps**:
1. Locate dashboard template (likely `templates/index.html` or `dashboard/templates/`)
2. Find header section (top of page)
3. Add mission display:
   ```html
   <header class="dashboard-header">
     <div class="header-left">
       <h1>Spec Kitty Dashboard</h1>
       <span class="project-name">{{ project_name }}</span>
     </div>

     <div class="header-right">
       <!-- NEW: Mission display -->
       <div class="mission-display">
         <span class="mission-label">Mission:</span>
         <span class="mission-name">{{ active_mission.name }}</span>
         <span class="mission-domain">({{ active_mission.domain }})</span>
         <!-- Refresh button added in T064 -->
       </div>
     </div>
   </header>
   ```

4. Verify template variable accessible: `{{ active_mission.name }}`

**Files**: Dashboard HTML template file

**Parallel?**: Yes (can work on while T064 works on refresh button)

**Notes**: Exact file location may vary - search for main dashboard template.

---

### Subtask T064 – Add refresh button (optional enhancement)

**Purpose**: Allow manual dashboard refresh to see mission updates.

**Steps**:
1. Add refresh button to mission display (in template):
   ```html
   <div class="mission-display">
     <span class="mission-label">Mission:</span>
     <span class="mission-name">{{ active_mission.name }}</span>
     <span class="mission-domain">({{ active_mission.domain }})</span>
     <button class="refresh-button" onclick="location.reload()">
       ↻ Refresh
     </button>
   </div>
   ```

2. Alternative with JavaScript reload:
   ```html
   <button class="refresh-button" onclick="refreshDashboard()">
     ↻ Refresh
   </button>

   <script>
   function refreshDashboard() {
     location.reload();
   }
   </script>
   ```

3. Test button functionality

**Files**: Dashboard HTML template

**Parallel?**: Yes (independent from T063)

**Notes**: Keep it simple - just page reload. No AJAX complexity needed.

---

### Subtask T065 – Style mission display

**Purpose**: Make mission display prominent but not obtrusive.

**Steps**:
1. Locate dashboard CSS file (likely `static/style.css` or inline styles)
2. Add CSS for mission display:
   ```css
   .mission-display {
     display: flex;
     align-items: center;
     gap: 8px;
     padding: 8px 16px;
     background: #f0f9ff;  /* Light blue background */
     border-radius: 6px;
     font-size: 14px;
   }

   .mission-label {
     color: #64748b;  /* Muted gray */
     font-weight: 500;
   }

   .mission-name {
     color: #0f172a;  /* Dark text */
     font-weight: 600;
   }

   .mission-domain {
     color: #64748b;  /* Muted gray */
     font-style: italic;
     font-size: 12px;
   }

   .refresh-button {
     margin-left: 8px;
     padding: 4px 8px;
     background: #e0f2fe;
     border: 1px solid #bae6fd;
     border-radius: 4px;
     cursor: pointer;
     font-size: 12px;
   }

   .refresh-button:hover {
     background: #bae6fd;
   }
   ```

3. Adjust colors to match existing dashboard theme
4. Test on different screen sizes (responsive)
5. Verify not obtrusive - shouldn't dominate interface

**Files**: Dashboard CSS file

**Parallel?**: Yes (can style while HTML is being updated)

**Notes**: Follow existing dashboard design language. Prominent but subtle.

---

### Subtask T066 – Test with software-dev mission

**Purpose**: Verify dashboard works with default software-dev mission.

**Steps**:
1. Ensure project using software-dev mission:
   ```bash
   spec-kitty mission current
   # Should show: Software Dev Kitty
   ```

2. Start dashboard:
   ```bash
   spec-kitty dashboard
   ```

3. Open in browser: http://localhost:8000 (or configured port)
4. Verify mission displayed in header:
   - Should show: "Mission: Software Dev Kitty (software)"
   - Should be styled correctly
   - Should not be obtrusive

5. Test refresh button (if implemented):
   - Click button → page reloads → mission still shown

6. Screenshot for documentation

**Files**: Manual testing

**Parallel?**: No (requires T062-T065 complete)

**Notes**: First manual testing checkpoint. Verify basic functionality works.

---

### Subtask T067 – Test with research mission

**Purpose**: Verify dashboard updates after mission switch.

**Steps**:
1. Switch to research mission:
   ```bash
   spec-kitty mission switch research
   ```

2. Refresh dashboard (click refresh button or reload page)
3. Verify mission updated:
   - Should now show: "Mission: Deep Research Kitty (research)"
   - Styling should be same (generic)
   - No research-specific UI changes (per constraint)

4. Test mission switch back:
   ```bash
   spec-kitty mission switch software-dev
   ```

5. Refresh dashboard again
6. Verify shows "Software Dev Kitty" again

7. Test without refresh:
   - Switch mission
   - Don't refresh dashboard
   - Should still show old mission (expected - manual refresh required)
   - Document this behavior

**Files**: Manual testing

**Parallel?**: No (final validation)

**Notes**: Verify dashboard doesn't break with mission switching. Refresh requirement is acceptable per design decision.

---

## Test Strategy

**Manual Testing Workflow**:

1. **Initial State**:
   ```bash
   # Start with software-dev mission
   spec-kitty mission current  # Verify: Software Dev Kitty
   spec-kitty dashboard
   # Open http://localhost:8000
   # Screenshot: software-dev mission display
   ```

2. **Mission Switch Test**:
   ```bash
   # Switch to research
   spec-kitty mission switch research

   # Dashboard still shows old mission (no auto-update)
   # Click refresh button or reload page
   # Screenshot: research mission display
   ```

3. **Switch Back Test**:
   ```bash
   # Switch back to software-dev
   spec-kitty mission switch software-dev

   # Refresh dashboard
   # Verify shows software-dev again
   ```

4. **Styling Validation**:
   - Check on laptop screen (1440p)
   - Check on smaller screen (1080p)
   - Verify colors match dashboard theme
   - Verify text is readable
   - Verify doesn't overflow or wrap awkwardly

5. **Error State Test**:
   - Break active-mission symlink
   - Start dashboard
   - Should show "Unknown" or fallback gracefully

**Automated Testing** (optional):
- Could add Playwright test for dashboard rendering
- Not critical for this feature (manual testing sufficient)

---

## Risks & Mitigations

**Risk 1**: Dashboard becomes cluttered
- **Mitigation**: Minimal design, header placement, no large visual changes

**Risk 2**: Mission display breaks dashboard layout
- **Mitigation**: Test responsive design, use flexbox for adaptive layout

**Risk 3**: Users expect auto-update without refresh
- **Mitigation**: Document refresh requirement, make button obvious

**Risk 4**: Dashboard WebSocket updates break
- **Mitigation**: Don't modify WebSocket logic, only add template context

**Risk 5**: Backend changes break existing dashboard
- **Mitigation**: Test all dashboard features after changes, not just mission display

---

## Definition of Done Checklist

- [ ] server.py updated with mission context
- [ ] Dashboard template updated with mission display
- [ ] Refresh button added (or documented as skipped)
- [ ] CSS styling added and matches dashboard theme
- [ ] Tested with software-dev mission
- [ ] Tested with research mission
- [ ] Tested mission switch → refresh → updated display
- [ ] Display is prominent but not obtrusive
- [ ] No regressions in existing dashboard functionality
- [ ] Works on different screen sizes

**Visual Verification**:
- [ ] Screenshot with software-dev mission
- [ ] Screenshot with research mission
- [ ] Mission text readable and well-styled
- [ ] Refresh button functional (if implemented)

---

## Review Guidance

**Critical Checkpoints**:
1. Mission display must be visible but not dominating
2. Refresh mechanism must work (button or manual reload)
3. No breaking changes to existing dashboard features
4. Styling must match existing design language
5. Works with all missions (generic, not mission-specific)

**What Reviewers Should Verify**:
- Start dashboard with software-dev → verify mission shown
- Switch to research, refresh → verify mission updated
- Check layout on different screen sizes → no overflow
- Test existing dashboard features → everything still works
- Verify no mission-specific UI complications added

**Acceptance Criteria from Spec**:
- User Story 7, Scenarios 1-4 satisfied
- FR-027 through FR-029 implemented
- SC-016, SC-017 achieved (visible without CLI, updates within 5 seconds of refresh)

---

## Activity Log

- 2025-01-16T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2025-11-16T13:25:04Z – codex – shell_pid=4035 – lane=doing – Started implementation
- 2025-11-16T13:29:56Z – codex – shell_pid=4035 – lane=doing – Completed implementation
- 2025-11-16T13:30:15Z – codex – shell_pid=4035 – lane=for_review – Ready for review
- 2025-11-16T14:02:45Z – codex – shell_pid=15588 – lane=planned – Review feedback: Server still missing mission context injection
- 2025-11-16T14:03:33Z – codex – shell_pid=15588 – lane=planned – Code review complete: needs mission context injection
- 2025-11-16T14:06:03Z – codex – shell_pid=60030 – lane=doing – Started implementation
- 2025-11-16T14:10:16Z – codex – shell_pid=60030 – lane=doing – Addressed feedback: Added mission context to dashboard root rendering
- 2025-11-16T14:10:30Z – codex – shell_pid=60030 – lane=doing – Addressed feedback: Seeded dashboard client with inline mission data
- 2025-11-16T14:11:48Z – codex – shell_pid=60030 – lane=for_review – Ready for review
- 2025-11-16T14:15:01Z – codex – shell_pid=37165 – lane=done – Approved without changes
