/**
 * Dossier Panel - Vanilla JavaScript component for rendering dossier UI
 *
 * Manages dossier state, artifact rendering, filtering, and detail views
 * without external framework dependencies (no Vue, React, etc.)
 */

class DossierPanel {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error(`DossierPanel: Container with id '${containerId}' not found`);
            return;
        }

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
        this.currentDetailKey = null;
    }

    /**
     * Initialize dossier panel with feature slug
     * @param {string} featureSlug - The feature identifier
     */
    async init(featureSlug) {
        if (!this.container) return;

        this.featureSlug = featureSlug;

        try {
            await this.loadSnapshot();
            await this.loadArtifacts();
            this.render();
            this.attachEventListeners();
        } catch (error) {
            console.error('Error initializing DossierPanel:', error);
            this.renderError(error.message);
        }
    }

    /**
     * Load snapshot overview from API
     */
    async loadSnapshot() {
        const response = await fetch(`${this.apiBase}/overview?feature=${this.featureSlug}`);
        if (!response.ok) {
            throw new Error(`Failed to load snapshot: ${response.status}`);
        }
        this.snapshot = await response.json();
    }

    /**
     * Load artifacts list with current filters applied
     */
    async loadArtifacts(filters = {}) {
        const params = new URLSearchParams({
            feature: this.featureSlug,
            ...filters,
        });

        const response = await fetch(`${this.apiBase}/artifacts?${params}`);
        if (!response.ok) {
            throw new Error(`Failed to load artifacts: ${response.status}`);
        }
        this.artifacts = await response.json();
    }

    /**
     * Render all UI components (overview, filters, artifact list)
     */
    render() {
        if (!this.container) return;

        this.renderOverview();
        this.renderFilterUI();
        this.renderArtifactList();
    }

    /**
     * Render dossier overview card with summary statistics
     */
    renderOverview() {
        const overview = this.container.querySelector('.dossier-overview');
        if (!overview || !this.snapshot) return;

        const completenessClass = `status-${this.snapshot.completeness_status.toLowerCase()}`;

        overview.innerHTML = `
            <div class="overview-header">
                <h2>Dossier Overview</h2>
            </div>
            <div class="overview-grid">
                <div class="stat">
                    <span class="label">Completeness</span>
                    <span class="value ${completenessClass}">
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
                    <span class="value ${this.snapshot.missing_required_count > 0 ? 'warn' : ''}">
                        ${this.snapshot.missing_required_count}
                    </span>
                </div>
            </div>
            <div class="parity-hash">
                <span class="label">Parity Hash</span>
                <code>${this.escapeHtml(this.snapshot.parity_hash_sha256.substring(0, 16))}...</code>
            </div>
        `;
    }

    /**
     * Render filter UI with checkboxes for artifact class and required_only
     */
    renderFilterUI() {
        const filterContainer = this.container.querySelector('.dossier-filters');
        if (!filterContainer) return;

        const classes = ['input', 'workflow', 'output', 'evidence', 'policy', 'runtime'];

        const filterHTML = `
            <div class="filters">
                <h3>Filter Artifacts</h3>
                <div class="filter-group">
                    <label class="filter-group-label">Class:</label>
                    <div class="filter-options">
                        ${classes.map(cls => `
                            <label class="filter-checkbox">
                                <input type="checkbox" class="filter-class" value="${cls}">
                                <span>${cls}</span>
                            </label>
                        `).join('')}
                    </div>
                </div>
                <div class="filter-group">
                    <label class="filter-checkbox">
                        <input type="checkbox" class="filter-required">
                        <span>Required Only</span>
                    </label>
                </div>
                <button class="filter-reset-btn">Reset Filters</button>
            </div>
        `;
        filterContainer.innerHTML = filterHTML;
    }

    /**
     * Render artifact list table with all artifacts
     */
    renderArtifactList() {
        const list = this.container.querySelector('.dossier-artifact-list');
        if (!list || !this.artifacts) return;

        if (!this.artifacts.artifacts || this.artifacts.artifacts.length === 0) {
            list.innerHTML = '<p class="no-artifacts">No artifacts found</p>';
            return;
        }

        const rows = this.artifacts.artifacts.map(artifact => `
            <tr data-artifact-key="${this.escapeHtml(artifact.artifact_key)}" class="artifact-row media-${artifact.media_type_hint || 'text'}">
                <td class="artifact-key">
                    <a href="#" class="artifact-link" data-key="${this.escapeHtml(artifact.artifact_key)}">
                        ${this.escapeHtml(artifact.artifact_key)}
                    </a>
                </td>
                <td class="artifact-class">
                    <span class="badge badge-${artifact.artifact_class}">
                        ${this.escapeHtml(artifact.artifact_class)}
                    </span>
                </td>
                <td class="artifact-path">${this.escapeHtml(artifact.relative_path)}</td>
                <td class="artifact-status">
                    ${artifact.is_present ? '<span class="status-present">✓ Present</span>' : '<span class="status-missing">✗ ' + this.escapeHtml(artifact.error_reason || 'Missing') + '</span>'}
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

    /**
     * Attach all event listeners (filter changes, artifact clicks, etc.)
     */
    attachEventListeners() {
        if (!this.container) return;

        // Artifact detail view on row click
        this.container.querySelectorAll('.artifact-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const key = link.dataset.key;
                this.showArtifactDetail(key);
            });
        });

        // Filter changes
        this.container.querySelectorAll('.filter-class').forEach(checkbox => {
            checkbox.addEventListener('change', () => this.applyFilters());
        });

        this.container.querySelector('.filter-required')?.addEventListener('change', () => {
            this.applyFilters();
        });

        // Reset filters button
        this.container.querySelector('.filter-reset-btn')?.addEventListener('click', () => {
            this.filters = {
                class: null,
                wp_id: null,
                step_id: null,
                required_only: false,
            };
            // Reset all checkboxes
            this.container.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                cb.checked = false;
            });
            this.loadArtifacts({}).then(() => {
                this.renderArtifactList();
                this.attachEventListeners();
            });
        });

        // Modal close button
        const modal = this.container.querySelector('#dossier-detail-modal');
        if (modal) {
            modal.querySelector('.modal-close')?.addEventListener('click', () => {
                modal.style.display = 'none';
                this.currentDetailKey = null;
            });

            // Close modal on background click
            modal.querySelector('.modal-overlay')?.addEventListener('click', () => {
                modal.style.display = 'none';
                this.currentDetailKey = null;
            });
        }
    }

    /**
     * Apply current filter selections and reload artifact list
     */
    async applyFilters() {
        const selectedClasses = Array.from(
            this.container.querySelectorAll('.filter-class:checked')
        ).map(cb => cb.value);

        const requiredOnly = this.container.querySelector('.filter-required')?.checked || false;

        const filters = {};
        if (selectedClasses.length > 0) {
            filters.class = selectedClasses[0]; // Single filter support for now
        }
        if (requiredOnly) {
            filters.required_only = 'true';
        }

        this.filters = filters;

        try {
            await this.loadArtifacts(filters);
            this.renderArtifactList();
            this.attachEventListeners();
        } catch (error) {
            console.error('Error applying filters:', error);
            this.renderError('Failed to apply filters');
        }
    }

    /**
     * Fetch and display artifact detail in modal
     * @param {string} artifactKey - The artifact key to display
     */
    async showArtifactDetail(artifactKey) {
        this.currentDetailKey = artifactKey;

        try {
            const response = await fetch(
                `${this.apiBase}/artifacts/${encodeURIComponent(artifactKey)}?feature=${this.featureSlug}`
            );

            if (!response.ok) {
                throw new Error(`Artifact not found: ${response.status}`);
            }

            const artifact = await response.json();
            this.renderArtifactDetail(artifact);
        } catch (error) {
            console.error('Error loading artifact detail:', error);
            this.renderArtifactDetailError(artifactKey, error.message);
        }
    }

    /**
     * Render artifact detail view in modal
     * @param {object} artifact - The artifact data
     */
    renderArtifactDetail(artifact) {
        const modal = this.container.querySelector('#dossier-detail-modal');
        if (!modal) return;

        const detail = modal.querySelector('.artifact-detail');
        if (!detail) return;

        let contentHTML = '';

        if (!artifact.is_present) {
            contentHTML = `
                <div class="artifact-missing">
                    <p>Artifact not present</p>
                    <p class="error-reason">${this.escapeHtml(artifact.error_reason || 'Unknown reason')}</p>
                </div>
            `;
        } else if (artifact.content_truncated) {
            contentHTML = `
                <div class="artifact-truncated warning">
                    <h4>⚠️ Content Not Available</h4>
                    <p>${this.escapeHtml(artifact.truncation_notice || 'File is too large to display')}</p>
                    <p class="file-size">File size: <strong>${this.formatBytes(artifact.size_bytes)}</strong></p>
                    <p>
                        <a href="${this.escapeHtml(artifact.relative_path)}" class="btn btn-secondary" download>
                            Download File
                        </a>
                    </p>
                </div>
            `;
        } else if (artifact.content) {
            const mediaClass = artifact.media_type_hint ? `media-${artifact.media_type_hint}` : '';
            contentHTML = `
                <pre class="artifact-content ${mediaClass}"><code>${this.escapeHtml(artifact.content)}</code></pre>
            `;
        } else {
            contentHTML = `<div class="artifact-empty"><p>No content available</p></div>`;
        }

        detail.innerHTML = `
            <div class="artifact-header">
                <h2>${this.escapeHtml(artifact.artifact_key)}</h2>
                <span class="badge badge-${artifact.artifact_class}">
                    ${this.escapeHtml(artifact.artifact_class)}
                </span>
            </div>
            <div class="artifact-metadata">
                <dl>
                    <dt>Path</dt>
                    <dd>${this.escapeHtml(artifact.relative_path)}</dd>
                    <dt>Size</dt>
                    <dd>${this.formatBytes(artifact.size_bytes)}</dd>
                    <dt>Status</dt>
                    <dd>${artifact.is_present ? 'Present' : 'Missing'}</dd>
                    <dt>Required</dt>
                    <dd>${this.escapeHtml(artifact.required_status || 'Unknown')}</dd>
                    <dt>Hash</dt>
                    <dd><code>${this.escapeHtml(artifact.content_hash_sha256?.substring(0, 16) || 'N/A')}...</code></dd>
                </dl>
            </div>
            <div class="artifact-content-wrapper">
                ${contentHTML}
            </div>
        `;

        modal.style.display = 'flex';
    }

    /**
     * Render error in artifact detail modal
     * @param {string} artifactKey - The artifact key that failed to load
     * @param {string} errorMessage - The error message
     */
    renderArtifactDetailError(artifactKey, errorMessage) {
        const modal = this.container.querySelector('#dossier-detail-modal');
        if (!modal) return;

        const detail = modal.querySelector('.artifact-detail');
        if (!detail) return;

        detail.innerHTML = `
            <div class="artifact-error">
                <h2>${this.escapeHtml(artifactKey)}</h2>
                <div class="error-message">
                    <p>Error loading artifact:</p>
                    <p><strong>${this.escapeHtml(errorMessage)}</strong></p>
                </div>
            </div>
        `;

        modal.style.display = 'flex';
    }

    /**
     * Render error message in main container
     * @param {string} message - Error message to display
     */
    renderError(message) {
        const content = this.container.querySelector('.dossier-content');
        if (!content) {
            this.container.innerHTML = `<div class="dossier-error"><p>${this.escapeHtml(message)}</p></div>`;
        } else {
            content.innerHTML = `<div class="dossier-error"><p>${this.escapeHtml(message)}</p></div>`;
        }
    }

    /**
     * HTML escape helper to prevent XSS attacks
     * @param {string} unsafe - Unsafe string
     * @returns {string} Escaped string safe for HTML
     */
    escapeHtml(unsafe) {
        if (typeof unsafe !== 'string') return String(unsafe);
        return unsafe
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    /**
     * Format bytes to human-readable size string
     * @param {number} bytes - Number of bytes
     * @returns {string} Formatted size (e.g., "1.5 MB")
     */
    formatBytes(bytes) {
        if (typeof bytes !== 'number' || bytes < 0) return 'Unknown';
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        if (bytes < 1024 * 1024 * 1024) return (bytes / 1024 / 1024).toFixed(1) + ' MB';
        return (bytes / 1024 / 1024 / 1024).toFixed(1) + ' GB';
    }
}

// Export for testing and external use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DossierPanel;
}
