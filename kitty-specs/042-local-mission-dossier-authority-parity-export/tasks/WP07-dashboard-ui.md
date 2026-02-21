---
work_package_id: WP07
title: Dashboard UI Integration
lane: "done"
dependencies:
- WP06
base_branch: 042-local-mission-dossier-authority-parity-export-WP06
base_commit: 2372bcf6c66bd728f8ec61c6c89da0f2c7452344
created_at: '2026-02-21T16:02:48.023451+00:00'
subtasks:
- T034
- T035
- T036
- T037
- T038
- T039
feature_slug: 042-local-mission-dossier-authority-parity-export
shell_pid: "3863"
agent: "coordinator"
reviewed_by: "Robert Douglass"
review_status: "approved"
---

# WP07: Dashboard UI Integration

**Objective**: Render dossier overview, artifact list with filtering, and detail views in local dashboard. Uses vanilla JavaScript (no Vue framework) to fetch from WP06 API endpoints and display results with syntax highlighting hints and proper truncation for large files.

**Priority**: P1 (User-facing feature)

**Scope**:
- dossier-panel.js (vanilla JS component)
- Dashboard HTML integration (new dossier tab)
- Artifact list rendering + filtering UI
- Artifact detail modal/view
- Truncation notice for >5MB
- Media type hints (markdown, json, yaml)

**Test Criteria**:
- Dashboard renders dossier panel without errors
- Artifact list loads and displays 30+ artifacts
- Filtering works (click class=output, list updates)
- Detail view displays full text for small artifacts
- Truncation notice for large artifacts

---

## Context

WP06 provides API endpoints; WP07 consumes them with vanilla JavaScript UI. The dashboard integrates a new dossier tab alongside existing features, allowing curators to inspect artifact completeness and review content without leaving the dashboard.

**Key Requirements**:
- **FR-013**: Local dashboard UI MUST render dossier overview, artifact list/filter, detail views
- **SC-001**: Dashboard <500ms response times
- **Design**: Vanilla JS (no Vue/SPA framework, aligns with existing dashboard)

**Dashboard Context**:
- Existing dashboard: `src/specify_cli/dashboard/`
- Static JS: `src/specify_cli/dashboard/static/js/`
- Templates: `src/specify_cli/dashboard/templates/dashboard.html`

---

## Detailed Guidance

### T034: Create dossier-panel.js

**What**: Vanilla JavaScript component managing dossier UI state and interactions.

**How**:
1. Create dossier-panel.js in `src/specify_cli/dashboard/static/js/dossier-panel.js`:
   ```javascript
   class DossierPanel {
       constructor(containerId) {
           this.container = document.getElementById(containerId);
           this.apiBase = '/api/dossier';
           this.featureSlug = null;
           this.snapshot = null;
           this.artifacts = null;
           this.filters = {
               class: null,
               wp_id: null,
               step_id: null,
               required_only: false,
           };
       }

       async init(featureSlug) {
           this.featureSlug = featureSlug;
           await this.loadSnapshot();
           await this.loadArtifacts();
           this.render();
           this.attachEventListeners();
       }

       async loadSnapshot() {
           const response = await fetch(`${this.apiBase}/overview?feature=${this.featureSlug}`);
           this.snapshot = await response.json();
       }

       async loadArtifacts(filters = {}) {
           const params = new URLSearchParams({
               feature: this.featureSlug,
               ...filters,
           });
           const response = await fetch(`${this.apiBase}/artifacts?${params}`);
           this.artifacts = await response.json();
       }

       render() {
           this.renderOverview();
           this.renderArtifactList();
           this.renderFilterUI();
       }

       renderOverview() {
           const overview = this.container.querySelector('.dossier-overview');
           overview.innerHTML = `
               <div class="overview-header">
                   <h2>Dossier Overview</h2>
               </div>
               <div class="overview-grid">
                   <div class="stat">
                       <span class="label">Completeness</span>
                       <span class="value status-${this.snapshot.completeness_status}">
                           ${this.snapshot.completeness_status.toUpperCase()}
                       </span>
                   </div>
                   <div class="stat">
                       <span class="label">Total Artifacts</span>
                       <span class="value">${this.snapshot.artifact_counts.total}</span>
                   </div>
                   <div class="stat">
                       <span class="label">Required Present</span>
                       <span class="value">${this.snapshot.artifact_counts.required_present}/${this.snapshot.artifact_counts.required}</span>
                   </div>
                   <div class="stat">
                       <span class="label">Missing</span>
                       <span class="value warn">${this.snapshot.missing_required_count}</span>
                   </div>
               </div>
               <div class="parity-hash">
                   <span class="label">Parity Hash</span>
                   <code>${this.snapshot.parity_hash_sha256.substring(0, 16)}...</code>
               </div>
           `;
       }

       renderArtifactList() {
           const list = this.container.querySelector('.dossier-artifact-list');
           if (!this.artifacts || this.artifacts.artifacts.length === 0) {
               list.innerHTML = '<p>No artifacts found</p>';
               return;
           }

           const rows = this.artifacts.artifacts.map(artifact => `
               <tr data-artifact-key="${artifact.artifact_key}" class="artifact-row">
                   <td class="artifact-key">
                       <a href="#" class="artifact-link" data-key="${artifact.artifact_key}">
                           ${artifact.artifact_key}
                       </a>
                   </td>
                   <td class="artifact-class">
                       <span class="badge badge-${artifact.artifact_class}">
                           ${artifact.artifact_class}
                       </span>
                   </td>
                   <td class="artifact-path">${artifact.relative_path}</td>
                   <td class="artifact-status">
                       ${artifact.is_present ? '✓' : '✗ ' + (artifact.error_reason || 'missing')}
                   </td>
               </tr>
           `).join('');

           list.innerHTML = `
               <table class="artifact-table">
                   <thead>
                       <tr>
                           <th>Artifact Key</th>
                           <th>Class</th>
                           <th>Path</th>
                           <th>Status</th>
                       </tr>
                   </thead>
                   <tbody>
                       ${rows}
                   </tbody>
               </table>
           `;
       }

       renderFilterUI() {
           const filterContainer = this.container.querySelector('.dossier-filters');
           // Render filter buttons/checkboxes
       }

       attachEventListeners() {
           // Click artifact row to show detail
           this.container.querySelectorAll('.artifact-link').forEach(link => {
               link.addEventListener('click', (e) => {
                   e.preventDefault();
                   const key = link.dataset.key;
                   this.showArtifactDetail(key);
               });
           });

           // Filter buttons
           this.container.querySelectorAll('.filter-btn').forEach(btn => {
               btn.addEventListener('click', (e) => {
                   // Update filter, reload artifacts, re-render
               });
           });
       }

       async showArtifactDetail(artifactKey) {
           const response = await fetch(`${this.apiBase}/artifacts/${artifactKey}?feature=${this.featureSlug}`);
           const artifact = await response.json();
           this.renderArtifactDetail(artifact);
       }

       renderArtifactDetail(artifact) {
           // Render modal/side panel with artifact content
       }
   }
   ```
2. Add initialization code to dashboard.js
3. Use vanilla fetch API (no jQuery)
4. Handle loading states (spinner, disabled buttons)
5. Add error handling (404, network errors)

**Implementation Details**:
- Use Fetch API (modern, built-in)
- Handle promises with async/await
- DOM manipulation with querySelector, innerHTML
- CSS classes for styling (no inline styles)
- Error messages displayed to user

**Test Requirements**:
- Component initializes without errors
- loadSnapshot fetches overview correctly
- loadArtifacts fetches artifact list correctly
- render() populates HTML
- EventListeners attached and working

---

### T035: Add Dossier Tab to Dashboard HTML

**What**: Integrate dossier panel into dashboard.html with tab navigation.

**How**:
1. Modify dashboard.html to add dossier tab:
   ```html
   <div class="dashboard-container">
       <div class="dashboard-tabs">
           <button class="tab-btn active" data-tab="features">Features</button>
           <button class="tab-btn" data-tab="missions">Missions</button>
           <button class="tab-btn" data-tab="dossier">Dossier</button>  <!-- NEW -->
       </div>

       <div class="tab-content">
           <!-- Existing tabs... -->

           <!-- NEW: Dossier Tab -->
           <div id="dossier-tab" class="tab-pane" style="display: none;">
               <div class="dossier-panel">
                   <div class="dossier-overview"></div>
                   <div class="dossier-filters"></div>
                   <div class="dossier-artifact-list"></div>
               </div>
               <div id="dossier-detail-modal" class="modal" style="display: none;">
                   <div class="modal-content">
                       <button class="modal-close">&times;</button>
                       <div class="artifact-detail"></div>
                   </div>
               </div>
           </div>
       </div>
   </div>
   ```
2. Add CSS styling for dossier panel (new file or inline)
3. Add tab switching JavaScript
4. Ensure existing tabs still work

**HTML Structure**:
- Tab navigation buttons (Features, Missions, Dossier)
- Tab content divs (dossier-panel, detail modal)
- IDs for JavaScript targeting

**Test Requirements**:
- Dossier tab renders without errors
- Tab switching works (click Dossier tab, shows dossier panel)
- Other tabs unaffected

---

### T036: Render Artifact List + Filtering

**What**: Display filtered artifact table with checkbox filters.

**How**:
1. Create renderFilterUI() in DossierPanel:
   ```javascript
   renderFilterUI() {
       const filterContainer = this.container.querySelector('.dossier-filters');
       const classes = ['input', 'workflow', 'output', 'evidence', 'policy', 'runtime'];

       const filterHTML = `
           <div class="filters">
               <h3>Filter Artifacts</h3>
               <div class="filter-group">
                   <label>Class:</label>
                   ${classes.map(cls => `
                       <label>
                           <input type="checkbox" class="filter-class" value="${cls}">
                           ${cls}
                       </label>
                   `).join('')}
               </div>
               <div class="filter-group">
                   <label>
                       <input type="checkbox" class="filter-required" value="true">
                       Required Only
                   </label>
               </div>
               <button class="filter-reset-btn">Reset Filters</button>
           </div>
       `;
       filterContainer.innerHTML = filterHTML;

       // Attach filter event listeners
       filterContainer.querySelectorAll('.filter-class').forEach(cb => {
           cb.addEventListener('change', () => this.applyFilters());
       });
       filterContainer.querySelector('.filter-reset-btn').addEventListener('click', () => {
           this.filters = {};
           this.loadArtifacts({});
           this.render();
       });
   }

   applyFilters() {
       // Collect selected filters
       const selectedClasses = Array.from(
           this.container.querySelectorAll('.filter-class:checked')
       ).map(cb => cb.value);

       const filters = {};
       if (selectedClasses.length > 0) {
           filters.class = selectedClasses[0];  // Single class filter (or support multiple)
       }

       this.loadArtifacts(filters);
       this.renderArtifactList();
   }
   ```
2. renderArtifactList() displays table with columns: Key, Class, Path, Status
3. Support filtering by class, wp_id, step_id (UI provides checkboxes)
4. Display stable ordering (by artifact_key, verified by server)

**Filter UI Design**:
- Checkboxes for each class
- "Required Only" checkbox
- "Reset Filters" button
- Real-time filtering (update list on checkbox change)

**Test Requirements**:
- Filters appear in HTML
- Clicking checkbox triggers filter update
- Artifact list updates with filtered results
- Reset button clears filters

---

### T037: Implement Artifact Detail View

**What**: Show full artifact content in modal/side panel.

**How**:
1. Create renderArtifactDetail() in DossierPanel:
   ```javascript
   renderArtifactDetail(artifact) {
       const modal = this.container.querySelector('#dossier-detail-modal');
       const detail = modal.querySelector('.artifact-detail');

       let contentHTML = '';
       if (artifact.content) {
           contentHTML = `
               <pre class="artifact-content ${artifact.media_type_hint}"><code>
                   ${escapeHtml(artifact.content)}
               </code></pre>
           `;
       } else if (artifact.content_truncated) {
           contentHTML = `
               <div class="artifact-truncated">
                   <p>${artifact.truncation_notice}</p>
               </div>
           `;
       } else if (!artifact.is_present) {
           contentHTML = `
               <div class="artifact-missing">
                   <p>Artifact not present (${artifact.error_reason})</p>
               </div>
           `;
       }

       detail.innerHTML = `
           <div class="artifact-header">
               <h2>${artifact.artifact_key}</h2>
               <span class="badge badge-${artifact.artifact_class}">${artifact.artifact_class}</span>
           </div>
           <div class="artifact-metadata">
               <dl>
                   <dt>Path</dt><dd>${artifact.relative_path}</dd>
                   <dt>Size</dt><dd>${formatBytes(artifact.size_bytes)}</dd>
                   <dt>Status</dt><dd>${artifact.is_present ? 'Present' : 'Missing'}</dd>
                   <dt>Required</dt><dd>${artifact.required_status}</dd>
                   <dt>Hash</dt><dd><code>${artifact.content_hash_sha256?.substring(0, 16)}...</code></dd>
               </dl>
           </div>
           <div class="artifact-content-wrapper">
               ${contentHTML}
           </div>
       `;

       modal.style.display = 'flex';
       modal.querySelector('.modal-close').addEventListener('click', () => {
           modal.style.display = 'none';
       });
   }

   function escapeHtml(unsafe) {
       return unsafe
           .replace(/&/g, "&amp;")
           .replace(/</g, "&lt;")
           .replace(/>/g, "&gt;")
           .replace(/"/g, "&quot;")
           .replace(/'/g, "&#039;");
   }

   function formatBytes(bytes) {
       if (bytes < 1024) return bytes + ' B';
       if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
       return (bytes / 1024 / 1024).toFixed(1) + ' MB';
   }
   ```
2. Create modal HTML in dashboard.html
3. Show metadata (path, size, hash, status)
4. Display full content if <5MB
5. Show truncation notice if >5MB

**Test Requirements**:
- Detail modal opens on artifact click
- Metadata displays correctly
- Content shows for small artifacts
- Truncation notice shows for large artifacts

---

### T038: Add Truncation Notice for >5MB

**What**: Display user-friendly truncation message for large artifacts.

**How**:
1. In renderArtifactDetail(), check artifact.content_truncated:
   ```javascript
   if (artifact.content_truncated) {
       contentHTML = `
           <div class="artifact-truncated warning">
               <svg class="icon"><!--warning icon--></svg>
               <div class="truncation-message">
                   <h3>Content Not Available</h3>
                   <p>${artifact.truncation_notice}</p>
                   <p>File size: <strong>${formatBytes(artifact.size_bytes)}</strong></p>
                   <p>
                       <a href="${artifact.relative_path}" class="btn btn-secondary">
                           Download File
                       </a>
                   </p>
               </div>
           </div>
       `;
   }
   ```
2. Add CSS styling (.artifact-truncated class)
3. Include "Download File" link (optional enhancement)
4. Clear messaging (why content not shown)

**Test Requirements**:
- Truncation notice displays for artifacts >5MB
- Notice includes file size
- User understands why content not shown

---

### T039: Media Type Hints

**What**: Add CSS classes/icons based on artifact media type.

**How**:
1. In renderArtifactList(), add class to table row:
   ```javascript
   <tr data-artifact-key="${artifact.artifact_key}" class="artifact-row media-${artifact.media_type_hint}">
   ```
2. In renderArtifactDetail(), add class to content:
   ```javascript
   <pre class="artifact-content media-${artifact.media_type_hint}">
   ```
3. Add CSS styling per media type:
   ```css
   .artifact-content.media-markdown {
       border-left: 4px solid #0366d6;
       background-color: #f6f8fa;
   }
   .artifact-content.media-json {
       border-left: 4px solid #f97316;
       background-color: #fef3c7;
   }
   .artifact-content.media-yaml {
       border-left: 4px solid #8b5cf6;
       background-color: #f3e8ff;
   }
   ```
4. Optional: Add icon badge (MD, JSON, YAML)
5. Syntax highlighting hint (markdown=italic, json=monospace, etc.)

**Media Types**:
- markdown: Blue border, light blue bg, italic text
- json: Orange border, light orange bg, monospace
- yaml: Purple border, light purple bg, monospace
- text: Default styling

**Test Requirements**:
- Media type hints visible in artifact list
- Correct colors/styling per type
- Accessibility (not color-only)

---

## Definition of Done

- [ ] dossier-panel.js created (vanilla JS, fetch API)
- [ ] Dashboard HTML integrated with dossier tab
- [ ] Artifact list rendering working (table view)
- [ ] Filtering UI implemented (class, required_only)
- [ ] Artifact detail modal working
- [ ] Truncation notice for >5MB artifacts
- [ ] Media type hints (colors, badges)
- [ ] All interactions tested (load, filter, detail, close)
- [ ] Error handling working (404, network errors)
- [ ] SC-001 performance validated (<500ms)
- [ ] FR-013 requirement satisfied

---

## Risks & Mitigations

**Risk 1**: Vanilla JS code becomes complex
- **Mitigation**: Keep components small, use helper functions

**Risk 2**: Large artifact content crashes browser
- **Mitigation**: Truncate at 5MB (server-side check)

**Risk 3**: Filtering logic inconsistent with server
- **Mitigation**: All filtering on server (client just sends params)

**Risk 4**: HTML escaping issues (XSS)
- **Mitigation**: Use escapeHtml() helper, avoid innerHTML for user data

---

## Reviewer Guidance

When reviewing WP07:
1. Verify dossier-panel.js uses vanilla JS (no Vue)
2. Check fetch API usage (correct error handling)
3. Confirm artifact list renders correctly
4. Validate filtering works (class, required_only)
5. Check artifact detail modal opens/closes
6. Verify truncation notice displays for >5MB
7. Check media type hints (colors, badges)
8. Test user interactions (click filters, click artifacts)
9. Validate error handling (404s, network failures)
10. Confirm SC-001 performance (<500ms)

---

## Implementation Notes

- **Storage**: dossier-panel.js, modifications to dashboard.html
- **Dependencies**: WP06 (API endpoints), vanilla JS (no frameworks)
- **Estimated Lines**: ~300 (JS) + ~100 (HTML/CSS modifications)
- **Integration Point**: WP06 endpoints; dashboard main.js
- **Styling**: Reuse existing dashboard color scheme

## Activity Log

- 2026-02-21T16:02:48Z – coordinator – shell_pid=3863 – lane=doing – Assigned agent via workflow command
- 2026-02-21T16:05:55Z – coordinator – shell_pid=3863 – lane=for_review – Ready for review: Dashboard UI integration complete - dossier panel with vanilla JS, filtering, detail views, truncation handling, and media type hints. All 6 subtasks done, comprehensive tests passing.
- 2026-02-21T16:06:21Z – coordinator – shell_pid=3863 – lane=done – Code review passed: 25 tests, vanilla JS implementation verified, responsive dashboard UI validated
