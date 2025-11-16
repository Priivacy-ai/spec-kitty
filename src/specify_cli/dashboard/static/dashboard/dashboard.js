let currentFeature = null;
let currentPage = 'overview';
let allFeatures = [];
let isConstitutionView = false;
let lastNonConstitutionPage = 'overview';
let projectPathDisplay = 'Loading…';
let activeWorktreeDisplay = 'detecting…';
let featureWorktreeDisplay = 'select a feature';
let featureSelectActive = false;
let featureSelectIdleTimer = null;
let activeMission = {
    name: 'Loading…',
    domain: '',
    version: '',
    slug: '',
    path: '',
    description: ''
};

if (typeof window !== 'undefined' && window.__INITIAL_MISSION__) {
    activeMission = window.__INITIAL_MISSION__;
}

function updateMissionDisplay(mission) {
    const nameEl = document.getElementById('mission-name');
    if (!nameEl) return;

    if (mission) {
        activeMission = mission;
    }

    nameEl.textContent = activeMission.name || 'Unknown mission';
}

// Cookie-based state persistence
function restoreState() {
    const cookies = document.cookie.split(';').reduce((acc, cookie) => {
        const parts = cookie.trim().split('=');
        if (parts.length === 2) {
            acc[parts[0]] = decodeURIComponent(parts[1]);
        }
        return acc;
    }, {});

    return {
        feature: cookies.lastFeature || null,
        page: cookies.lastPage || 'overview'
    };
}

function saveState(feature, page) {
    const expires = new Date();
    expires.setFullYear(expires.getFullYear() + 1); // 1 year

    if (feature) {
        document.cookie = `lastFeature=${encodeURIComponent(feature)}; expires=${expires.toUTCString()}; path=/; SameSite=Strict`;
    }
    if (page) {
        document.cookie = `lastPage=${encodeURIComponent(page)}; expires=${expires.toUTCString()}; path=/; SameSite=Strict`;
    }
}

function setFeatureSelectActive(isActive) {
    if (isActive) {
        featureSelectActive = true;
        if (featureSelectIdleTimer) {
            clearTimeout(featureSelectIdleTimer);
        }
        featureSelectIdleTimer = setTimeout(() => {
            featureSelectActive = false;
            featureSelectIdleTimer = null;
        }, 5000);
    } else {
        featureSelectActive = false;
        if (featureSelectIdleTimer) {
            clearTimeout(featureSelectIdleTimer);
            featureSelectIdleTimer = null;
        }
    }
}

function updateTreeInfo() {
    const treeElement = document.getElementById('tree-info');
    if (!treeElement) {
        return;
    }
    const lines = [`└─ ${projectPathDisplay}`];
    if (activeWorktreeDisplay) {
        lines.push(`   ├─ Active worktree: ${activeWorktreeDisplay}`);
        lines.push(`   └─ Feature worktree: ${featureWorktreeDisplay}`);
    } else {
        lines.push(`   └─ Feature worktree: ${featureWorktreeDisplay}`);
    }
    treeElement.textContent = lines.join('\n');
}

function computeFeatureWorktreeStatus(feature) {
    if (!feature) {
        featureWorktreeDisplay = allFeatures.length === 0 ? 'none yet' : 'select a feature';
        return;
    }
    const worktree = feature.worktree;
    if (worktree && worktree.path) {
        featureWorktreeDisplay = worktree.exists ? worktree.path : `${worktree.path} (missing)`;
    } else {
        featureWorktreeDisplay = 'unavailable';
    }
}

function switchFeature(featureId) {
    const isSameFeature = featureId === currentFeature;
    if (isConstitutionView) {
        if (isSameFeature) {
            return;
        }
        isConstitutionView = false;
        if (lastNonConstitutionPage && lastNonConstitutionPage !== 'constitution') {
            currentPage = lastNonConstitutionPage;
        } else {
            currentPage = 'overview';
        }
        document.querySelectorAll('.page').forEach(page => page.classList.remove('active'));
        const currentPageEl = document.getElementById(`page-${currentPage}`);
        if (currentPageEl) {
            currentPageEl.classList.add('active');
        }
        document.querySelectorAll('.sidebar-item').forEach(item => {
            if (item.dataset.page === currentPage) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
    }
    currentFeature = featureId;
    saveState(currentFeature, currentPage);
    loadCurrentPage();
    updateSidebarState();
    const feature = allFeatures.find(f => f.id === currentFeature);
    computeFeatureWorktreeStatus(feature);
    updateTreeInfo();
}

function switchPage(pageName) {
    if (pageName === 'constitution') {
        showConstitution();
        return;
    }
    if (pageName === 'diagnostics') {
        showDiagnostics();
        return;
    }
    isConstitutionView = false;
    currentPage = pageName;
    lastNonConstitutionPage = pageName;
    saveState(currentFeature, currentPage);

    // Update sidebar
    document.querySelectorAll('.sidebar-item').forEach(item => {
        if (item.dataset.page === pageName) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });

    // Update pages
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    const activePageEl = document.getElementById(`page-${pageName}`);
    if (activePageEl) {
        activePageEl.classList.add('active');
    }

    loadCurrentPage();
}

function updateSidebarState() {
    const feature = allFeatures.find(f => f.id === currentFeature);
    if (!feature) return;

    const artifacts = feature.artifacts;

    document.querySelectorAll('.sidebar-item').forEach(item => {
        const page = item.dataset.page;
        // System pages (constitution, diagnostics) should never be disabled
        if (!page || page === 'constitution' || page === 'diagnostics') {
            item.classList.remove('disabled');
            return;
        }

        const hasArtifact = page === 'overview' || artifacts[page.replace('-', '_')]?.exists;

        if (hasArtifact) {
            item.classList.remove('disabled');
        } else {
            item.classList.add('disabled');
        }
    });
}

function loadCurrentPage() {
    if (isConstitutionView || currentPage === 'constitution') {
        return;
    }
    if (!currentFeature) return;

    if (currentPage === 'overview') {
        loadOverview();
    } else if (currentPage === 'kanban') {
        loadKanban();
    } else if (currentPage === 'contracts') {
        loadContracts();
    } else if (currentPage === 'research') {
        loadResearch();
    } else {
        loadArtifact(currentPage);
    }
}

function loadOverview() {
    const feature = allFeatures.find(f => f.id === currentFeature);
    if (!feature) return;

    const mergeBadge = (() => {
const meta = feature.meta || {};
const mergedAt = meta.merged_at || meta.merge_at;
const mergedInto = meta.merged_into || meta.merge_into || meta.merged_target;
if (!mergedAt || !mergedInto) {
    return '';
}
const date = new Date(mergedAt);
const dateStr = isNaN(date.valueOf()) ? mergedAt : date.toLocaleDateString();
return `
    <span class="merge-badge" title="Merged into ${escapeHtml(mergedInto)} on ${escapeHtml(dateStr)}">
        <span class="icon">✅</span>
        <span>merged → ${escapeHtml(mergedInto)}</span>
    </span>
`;
    })();

    const stats = feature.kanban_stats;
    const total = stats.total;
    const completed = stats.done;
    const completionRate = total > 0 ? Math.round((completed / total) * 100) : 0;

    const artifacts = feature.artifacts;
    const artifactList = [
        {name: 'Constitution', key: 'constitution', icon: '⚖️'},
        {name: 'Specification', key: 'spec', icon: '📄'},
        {name: 'Plan', key: 'plan', icon: '🏗️'},
        {name: 'Tasks', key: 'tasks', icon: '📋'},
        {name: 'Kanban Board', key: 'kanban', icon: '🎯'},
        {name: 'Research', key: 'research', icon: '🔬'},
        {name: 'Quickstart', key: 'quickstart', icon: '🚀'},
        {name: 'Data Model', key: 'data_model', icon: '💾'},
        {name: 'Contracts', key: 'contracts', icon: '📜'},
        {name: 'Checklists', key: 'checklists', icon: '✅'},
    ].map(a => `
        <div style="padding: 10px; background: ${artifacts[a.key]?.exists ? '#ecfdf5' : '#fef2f2'};
             border-radius: 6px; border-left: 3px solid ${artifacts[a.key]?.exists ? '#10b981' : '#ef4444'};">
            ${a.icon} ${a.name}: ${artifacts[a.key]?.exists ? '✅ Available' : '❌ Not created'}
        </div>
    `).join('');

    document.getElementById('overview-content').innerHTML = `
<div style="margin-bottom: 30px;">
    <h3>Feature: ${feature.name} ${mergeBadge}</h3>
    <p style="color: #6b7280;">View and track all artifacts for this feature</p>
</div>

<div class="status-summary">
    <div class="status-card total">
                <div class="status-label">Total Tasks</div>
                <div class="status-value">${total}</div>
                <div class="status-detail">${stats.planned} planned</div>
            </div>
            <div class="status-card progress">
                <div class="status-label">In Progress</div>
                <div class="status-value">${stats.doing}</div>
            </div>
            <div class="status-card review">
                <div class="status-label">Review</div>
                <div class="status-value">${stats.for_review}</div>
            </div>
            <div class="status-card completed">
                <div class="status-label">Completed</div>
                <div class="status-value">${completed}</div>
                <div class="status-detail">${completionRate}% done</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${completionRate}%"></div>
                </div>
            </div>
        </div>

        <h3 style="margin-top: 30px; margin-bottom: 15px; color: #1f2937;">Available Artifacts</h3>
        <div style="display: grid; gap: 10px;">
            ${artifactList}
        </div>
    `;
}

function loadKanban() {
    fetch(`/api/kanban/${currentFeature}`)
        .then(response => response.json())
        .then(data => {
            renderKanban(data);
        })
        .catch(error => {
            document.getElementById('kanban-board').innerHTML =
                '<div class="empty-state">Error loading kanban board</div>';
        });
}

function renderKanban(lanes) {
    const total = lanes.planned.length + lanes.doing.length + lanes.for_review.length + lanes.done.length;
    const completed = lanes.done.length;
    const completionRate = total > 0 ? Math.round((completed / total) * 100) : 0;

    const agents = new Set();
    Object.values(lanes).forEach(tasks => {
        tasks.forEach(task => {
            if (task.agent && task.agent !== 'system') agents.add(task.agent);
        });
    });

    document.getElementById('kanban-status').innerHTML = `
        <div class="status-card total">
            <div class="status-label">Total Work Packages</div>
            <div class="status-value">${total}</div>
            <div class="status-detail">${lanes.planned.length} planned</div>
        </div>
        <div class="status-card progress">
            <div class="status-label">In Progress</div>
            <div class="status-value">${lanes.doing.length}</div>
        </div>
        <div class="status-card review">
            <div class="status-label">Review</div>
            <div class="status-value">${lanes.for_review.length}</div>
        </div>
        <div class="status-card completed">
            <div class="status-label">Completed</div>
            <div class="status-value">${completed}</div>
            <div class="status-detail">${completionRate}% done</div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${completionRate}%"></div>
            </div>
        </div>
        <div class="status-card agents">
            <div class="status-label">Active Agents</div>
            <div class="status-value">${agents.size}</div>
            <div class="status-detail">${agents.size > 0 ? Array.from(agents).join(', ') : 'none'}</div>
        </div>
    `;

    const createCard = (task) => `
        <div class="card" role="button">
            <div class="card-id">${task.id}</div>
            <div class="card-title">${task.title}</div>
            <div class="card-meta">
                ${task.agent ? `<span class="badge agent">${task.agent}</span>` : ''}
                ${task.subtasks && task.subtasks.length > 0 ?
                  `<span class="badge subtasks">${task.subtasks.length} subtask${task.subtasks.length !== 1 ? 's' : ''}</span>` : ''}
            </div>
        </div>
    `;

    document.getElementById('kanban-board').innerHTML = `
        <div class="lane planned">
            <div class="lane-header">
                <span>📋 Planned</span>
                <span class="count">${lanes.planned.length}</span>
            </div>
            <div>${lanes.planned.length === 0 ? '<div class="empty-state">No tasks</div>' : lanes.planned.map(createCard).join('')}</div>
        </div>
        <div class="lane doing">
            <div class="lane-header">
                <span>🚀 Doing</span>
                <span class="count">${lanes.doing.length}</span>
            </div>
            <div>${lanes.doing.length === 0 ? '<div class="empty-state">No tasks</div>' : lanes.doing.map(createCard).join('')}</div>
        </div>
        <div class="lane for_review">
            <div class="lane-header">
                <span>👀 For Review</span>
                <span class="count">${lanes.for_review.length}</span>
            </div>
            <div>${lanes.for_review.length === 0 ? '<div class="empty-state">No tasks</div>' : lanes.for_review.map(createCard).join('')}</div>
        </div>
        <div class="lane done">
            <div class="lane-header">
                <span>✅ Done</span>
                <span class="count">${lanes.done.length}</span>
            </div>
            <div>${lanes.done.length === 0 ? '<div class="empty-state">No tasks</div>' : lanes.done.map(createCard).join('')}</div>
        </div>
    `;

    ['planned', 'doing', 'for_review', 'done'].forEach(laneName => {
        const laneCards = document.querySelectorAll(`.lane.${laneName} .card`);
        laneCards.forEach((card, index) => {
            const task = lanes[laneName][index];
            if (!task) return;
            if (!card.hasAttribute('tabindex')) {
                card.setAttribute('tabindex', '0');
            }
            card.addEventListener('click', () => showPromptModal(task));
            card.addEventListener('keydown', (event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    showPromptModal(task);
                }
            });
        });
    });
}

function formatLaneName(lane) {
    if (!lane) return '';
    return lane.split('_').map(part => part.charAt(0).toUpperCase() + part.slice(1)).join(' ');
}

function showPromptModal(task) {
    const modal = document.getElementById('prompt-modal');
    if (!modal) return;

    const titleEl = document.getElementById('modal-title');
    const subtitleEl = document.getElementById('modal-subtitle');
    const metaEl = document.getElementById('modal-prompt-meta');
    const contentEl = document.getElementById('modal-prompt-content');
    const modalBody = document.getElementById('modal-body');

    if (titleEl) {
        titleEl.textContent = task.title || 'Work Package Prompt';
    }
    if (subtitleEl) {
        if (task.id) {
            subtitleEl.textContent = task.id;
            subtitleEl.style.display = 'block';
        } else {
            subtitleEl.textContent = '';
            subtitleEl.style.display = 'none';
        }
    }

    if (metaEl) {
        const metaItems = [];
        if (task.lane) metaItems.push(`<span>Lane: ${escapeHtml(formatLaneName(task.lane))}</span>`);
        if (task.agent) metaItems.push(`<span>Agent: ${escapeHtml(task.agent)}</span>`);
        if (task.subtasks && task.subtasks.length) {
            metaItems.push(`<span>${task.subtasks.length} subtask${task.subtasks.length !== 1 ? 's' : ''}</span>`);
        }
        if (task.phase) metaItems.push(`<span>Phase: ${escapeHtml(task.phase)}</span>`);
        if (task.prompt_path) metaItems.push(`<span>Source: ${escapeHtml(task.prompt_path)}</span>`);

        if (metaItems.length > 0) {
            metaEl.innerHTML = metaItems.join('');
            metaEl.style.display = 'flex';
        } else {
            metaEl.innerHTML = '';
            metaEl.style.display = 'none';
        }
    }

    if (contentEl) {
        if (task.prompt_markdown) {
            contentEl.innerHTML = marked.parse(task.prompt_markdown);
        } else {
            contentEl.innerHTML = '<div class="empty-state">Prompt content unavailable.</div>';
        }
    }

    if (modalBody) {
        modalBody.scrollTop = 0;
    }

    modal.classList.remove('hidden');
    modal.classList.add('show');
    modal.setAttribute('aria-hidden', 'false');
    document.body.classList.add('modal-open');
}

function hidePromptModal() {
    const modal = document.getElementById('prompt-modal');
    if (!modal) return;

    modal.classList.remove('show');
    modal.classList.add('hidden');
    modal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('modal-open');
}

const modalOverlay = document.querySelector('#prompt-modal .modal-overlay');
if (modalOverlay) {
    modalOverlay.addEventListener('click', hidePromptModal);
}
const modalCloseButton = document.getElementById('modal-close-btn');
if (modalCloseButton) {
    modalCloseButton.addEventListener('click', hidePromptModal);
}
document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
        const modal = document.getElementById('prompt-modal');
        if (modal && modal.classList.contains('show')) {
            hidePromptModal();
        }
    }
});

function loadArtifact(artifactName) {
    const artifactKey = artifactName.replace('-', '_');
    fetch(`/api/artifact/${currentFeature}/${artifactName}`)
        .then(response => response.ok ? response.text() : Promise.reject('Not found'))
        .then(content => {
            // Render markdown to HTML
            const htmlContent = marked.parse(content);
            document.getElementById(`${artifactName}-content`).innerHTML = htmlContent;
        })
        .catch(error => {
            document.getElementById(`${artifactName}-content`).innerHTML =
                '<div class="empty-state">Artifact not available</div>';
        });
}

function loadContracts() {
    fetch(`/api/contracts/${currentFeature}`)
        .then(response => response.ok ? response.json() : Promise.reject('Not found'))
        .then(data => {
            if (data.files && data.files.length > 0) {
                renderContractsList(data.files);
            } else {
                document.getElementById('contracts-content').innerHTML =
                    '<div class="empty-state">No contracts available. Run /spec-kitty.plan to generate contracts.</div>';
            }
        })
        .catch(error => {
            document.getElementById('contracts-content').innerHTML =
                '<div class="empty-state">Contracts directory not found</div>';
        });
}

function renderContractsList(files) {
    const contractsHtml = files.map((file, idx) => {
        const fileNameEscaped = escapeHtml(file.name);
        return `
            <div style="margin-bottom: 20px; padding: 15px; background: white; border-radius: 8px; border-left: 4px solid var(--lavender); cursor: pointer;"
                 data-filename="${fileNameEscaped}" class="contract-item">
                <div style="font-weight: 600; color: var(--dark-text); margin-bottom: 5px;">
                    ${file.icon} ${fileNameEscaped}
                </div>
                <div style="font-size: 0.85em; color: var(--medium-text);">
                    Click to view contract
                </div>
            </div>
        `;
    }).join('');

    document.getElementById('contracts-content').innerHTML = `
        <p style="margin-bottom: 20px; color: var(--medium-text);">
            API specifications and interface definitions for this feature.
        </p>
        ${contractsHtml}
    `;

    // Add click handlers
    document.querySelectorAll('.contract-item').forEach(item => {
        item.addEventListener('click', () => {
            loadContractFile(item.dataset.filename);
        });
    });
}

function loadContractFile(fileName) {
    fetch(`/api/contracts/${currentFeature}/${fileName}`)
        .then(response => response.ok ? response.text() : Promise.reject('Not found'))
        .then(content => {
            let htmlContent;

            // Format JSON files nicely
            if (fileName.endsWith('.json')) {
                try {
                    const jsonData = JSON.parse(content);
                    const prettyJson = JSON.stringify(jsonData, null, 2);
                    htmlContent = `<pre style="background: #f8f9fa; padding: 20px; border-radius: 8px; overflow-x: auto; border: 1px solid #dee2e6;"><code style="font-family: 'Monaco', 'Menlo', monospace; font-size: 0.9em; line-height: 1.5; color: #212529;">${escapeHtml(prettyJson)}</code></pre>`;
                } catch (e) {
                    // If JSON parsing fails, show as plain text
                    htmlContent = `<pre style="background: #f8f9fa; padding: 20px; border-radius: 8px; overflow-x: auto;"><code>${escapeHtml(content)}</code></pre>`;
                }
            } else if (fileName.endsWith('.md')) {
                // Render markdown files with proper styling
                const renderedMarkdown = marked.parse(content);
                htmlContent = `<div class="markdown-content" style="line-height: 1.6; font-size: 0.95em;">${renderedMarkdown}</div>`;
            } else if (fileName.endsWith('.csv')) {
                // Render CSV as a table
                htmlContent = renderCSV(content);
            } else if (fileName.endsWith('.yml') || fileName.endsWith('.yaml')) {
                // Show YAML files as code blocks
                htmlContent = `<pre style="background: #f8f9fa; padding: 20px; border-radius: 8px; overflow-x: auto; border: 1px solid #dee2e6;"><code style="font-family: 'Monaco', 'Menlo', monospace; font-size: 0.9em; line-height: 1.5;">${escapeHtml(content)}</code></pre>`;
            } else {
                // Default: show as code block
                htmlContent = `<pre style="background: #f8f9fa; padding: 20px; border-radius: 8px; overflow-x: auto;"><code>${escapeHtml(content)}</code></pre>`;
            }

            document.getElementById('contracts-content').innerHTML = `
                <div style="margin-bottom: 20px;">
                    <button onclick="loadContracts()"
                            style="padding: 8px 16px; background: var(--baby-blue); border: none; border-radius: 6px; cursor: pointer; color: var(--dark-text); font-weight: 500;">
                        ← Back to Contracts List
                    </button>
                </div>
                <h3 style="color: var(--grassy-green); margin-bottom: 15px;">${escapeHtml(fileName)}</h3>
                ${htmlContent}
            `;
        })
        .catch(error => {
            document.getElementById('contracts-content').innerHTML =
                '<div class="empty-state">Error loading contract file</div>';
        });
}

function loadResearch() {
    fetch(`/api/research/${currentFeature}`)
        .then(response => response.ok ? response.json() : Promise.reject('Not found'))
        .then(data => {
            if (data.main_file || (data.artifacts && data.artifacts.length > 0)) {
                renderResearchContent(data);
            } else {
                document.getElementById('research-content').innerHTML =
                    '<div class="empty-state">No research artifacts available. Run /spec-kitty.research to create them.</div>';
            }
        })
        .catch(error => {
            document.getElementById('research-content').innerHTML =
                '<div class="empty-state">Research artifacts not found</div>';
        });
}

function renderResearchContent(data) {
    let mainContent = '';
    if (data.main_file) {
        mainContent = `
            <h3 style="color: var(--grassy-green); margin-bottom: 15px;">research.md</h3>
            ${marked.parse(data.main_file)}
        `;
    }

    let artifactsHtml = '';
    if (data.artifacts && data.artifacts.length > 0) {
        const artifactItems = data.artifacts.map(file => {
            const nameEscaped = escapeHtml(file.name);
            const pathEscaped = escapeHtml(file.path);
            return `
                <div style="padding: 12px; background: white; border-radius: 8px; border-left: 4px solid var(--soft-peach); cursor: pointer;"
                     data-filepath="${pathEscaped}" data-filename="${nameEscaped}" class="research-artifact-item">
                    <div style="font-weight: 600; color: var(--dark-text); margin-bottom: 3px;">
                        ${file.icon} ${nameEscaped}
                    </div>
                    <div style="font-size: 0.75em; color: var(--medium-text); font-family: monospace;">
                        ${pathEscaped}
                    </div>
                </div>
            `;
        }).join('');

        artifactsHtml = `
            <h3 style="color: var(--grassy-green); margin-top: 30px; margin-bottom: 15px;">
                Research Artifacts
            </h3>
            <div style="display: grid; gap: 10px;">
                ${artifactItems}
            </div>
        `;
    }

    document.getElementById('research-content').innerHTML = mainContent + artifactsHtml;

    // Add click handlers
    document.querySelectorAll('.research-artifact-item').forEach(item => {
        item.addEventListener('click', () => {
            loadResearchFile(item.dataset.filepath, item.dataset.filename);
        });
    });
}

function loadResearchFile(filePath, fileName) {
    fetch(`/api/research/${currentFeature}/${encodeURIComponent(filePath)}`)
        .then(response => response.ok ? response.text() : Promise.reject('Not found'))
        .then(content => {
            let htmlContent;

            if (filePath.endsWith('.md')) {
                // Render markdown files with proper styling
                const renderedMarkdown = marked.parse(content);
                htmlContent = `<div class="markdown-content" style="line-height: 1.6; font-size: 0.95em;">${renderedMarkdown}</div>`;
            } else if (filePath.endsWith('.csv')) {
                // Render CSV as a table
                htmlContent = renderCSV(content);
            } else if (filePath.endsWith('.json')) {
                // Format JSON files nicely
                try {
                    const jsonData = JSON.parse(content);
                    const prettyJson = JSON.stringify(jsonData, null, 2);
                    htmlContent = `<pre style="background: #f8f9fa; padding: 20px; border-radius: 8px; overflow-x: auto; border: 1px solid #dee2e6;"><code style="font-family: 'Monaco', 'Menlo', monospace; font-size: 0.9em; line-height: 1.5; color: #212529;">${escapeHtml(prettyJson)}</code></pre>`;
                } catch (e) {
                    // If JSON parsing fails, show as plain text
                    htmlContent = `<pre style="background: #f8f9fa; padding: 20px; border-radius: 8px; overflow-x: auto;"><code>${escapeHtml(content)}</code></pre>`;
                }
            } else {
                // Default: show as code block
                htmlContent = `<pre style="background: white; padding: 20px; border-radius: 8px; overflow-x: auto;">${escapeHtml(content)}</pre>`;
            }

            document.getElementById('research-content').innerHTML = `
                <div style="margin-bottom: 20px;">
                    <button onclick="loadResearch()"
                            style="padding: 8px 16px; background: var(--baby-blue); border: none; border-radius: 6px; cursor: pointer; color: var(--dark-text); font-weight: 500;">
                        ← Back to Research
                    </button>
                </div>
                <h3 style="color: var(--grassy-green); margin-bottom: 15px;">${escapeHtml(fileName)}</h3>
                ${htmlContent}
            `;
        })
        .catch(error => {
            document.getElementById('research-content').innerHTML =
                '<div class="empty-state">Error loading research file</div>';
        });
}

function renderCSV(csvContent) {
    const lines = csvContent.trim().split('\n');
    if (lines.length === 0) return '<div class="empty-state">Empty CSV file</div>';

    const rows = lines.map(line => {
        // Improved CSV parsing that handles quoted fields
        const cells = [];
        let current = '';
        let inQuotes = false;

        for (let i = 0; i < line.length; i++) {
            const char = line[i];
            const nextChar = line[i + 1];

            if (char === '"') {
                if (inQuotes && nextChar === '"') {
                    // Escaped quote
                    current += '"';
                    i++; // Skip next quote
                } else {
                    // Toggle quote mode
                    inQuotes = !inQuotes;
                }
            } else if (char === ',' && !inQuotes) {
                // End of field
                cells.push(current.trim());
                current = '';
            } else {
                current += char;
            }
        }
        // Don't forget the last field
        cells.push(current.trim());

        return cells;
    });

    const headerRow = rows[0];
    const dataRows = rows.slice(1);

    return `
        <div style="overflow-x: auto; margin: 20px 0;">
            <table style="width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <thead>
                    <tr style="background: var(--baby-blue);">
                        ${headerRow.map(header => `<th style="padding: 12px; text-align: left; font-weight: 600; color: var(--dark-text); border-bottom: 2px solid var(--lavender);">${escapeHtml(header)}</th>`).join('')}
                    </tr>
                </thead>
                <tbody>
                    ${dataRows.map((row, idx) => `
                        <tr style="border-top: 1px solid #e5e7eb; ${idx % 2 === 0 ? 'background: #fafbfc;' : 'background: white;'} transition: background 0.2s;"
                            onmouseover="this.style.background='#f0f4f8'"
                            onmouseout="this.style.background='${idx % 2 === 0 ? '#fafbfc' : 'white'}'">
                            ${row.map(cell => `<td style="padding: 10px; color: var(--medium-text);">${escapeHtml(cell)}</td>`).join('')}
                        </tr>
                    `).join('')}
                </tbody>
            </table>
            ${dataRows.length === 0 ? '<div style="text-align: center; padding: 20px; color: var(--medium-text);">No data rows in CSV</div>' : ''}
        </div>
    `;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showConstitution() {
    if (!isConstitutionView && currentPage !== 'constitution') {
        lastNonConstitutionPage = currentPage;
    }
    // Switch to constitution page
    currentPage = 'constitution';
    isConstitutionView = true;
    saveState(currentFeature, 'constitution');
    document.querySelectorAll('.sidebar-item').forEach(item => item.classList.remove('active'));
    const constitutionItem = document.querySelector('.sidebar-item[data-page="constitution"]');
    if (constitutionItem) {
        constitutionItem.classList.remove('disabled');
        constitutionItem.classList.add('active');
    }
    document.querySelectorAll('.page').forEach(page => page.classList.remove('active'));
    document.getElementById('page-constitution').classList.add('active');

    // Load constitution
    fetch('/api/constitution')
        .then(response => response.ok ? response.text() : Promise.reject('Not found'))
        .then(content => {
            const htmlContent = marked.parse(content);
            document.getElementById('constitution-content').innerHTML = htmlContent;
        })
        .catch(error => {
            document.getElementById('constitution-content').innerHTML =
                '<div class="empty-state">Constitution not found. Run /spec-kitty.constitution to create it.</div>';
        });
}

function updateWorkflowIcons(workflow) {
    const iconMap = {
        'complete': '✅',
        'in_progress': '🔄',
        'pending': '⏳'
    };

    document.getElementById('icon-specify').textContent = iconMap[workflow.specify] || '⏳';
    document.getElementById('icon-plan').textContent = iconMap[workflow.plan] || '⏳';
    document.getElementById('icon-tasks').textContent = iconMap[workflow.tasks] || '⏳';
    document.getElementById('icon-implement').textContent = iconMap[workflow.implement] || '⏳';
}

function updateFeatureList(features) {
    allFeatures = features;
    const selectContainer = document.getElementById('feature-selector-container');
    const select = document.getElementById('feature-select');
    const singleFeatureName = document.getElementById('single-feature-name');
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');

    // Restore saved state from cookies on initial load
    const savedState = restoreState();

    if (select && !select.dataset.pauseHandlersAttached) {
        const activate = () => setFeatureSelectActive(true);
        const deactivate = () => setFeatureSelectActive(false);
        ['focus', 'mousedown', 'keydown', 'click', 'input'].forEach(evt => {
            select.addEventListener(evt, activate);
        });
        ['change', 'blur'].forEach(evt => {
            select.addEventListener(evt, deactivate);
        });
        select.dataset.pauseHandlersAttached = 'true';
    }

    // Handle 0 features - show welcome page
    if (features.length === 0) {
        selectContainer.style.display = 'none';
        singleFeatureName.style.display = 'none';
        sidebar.style.display = 'block';
        mainContent.style.display = 'block';
        isConstitutionView = false;
        currentFeature = null;
        computeFeatureWorktreeStatus(null);
        setFeatureSelectActive(false);

        // Show welcome page
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.getElementById('page-welcome').classList.add('active');
        currentPage = 'welcome';

        // Disable all sidebar items except constitution link
        document.querySelectorAll('.sidebar-item').forEach(item => {
            if (item.dataset.page === 'constitution') {
                item.classList.remove('disabled');
            } else {
                item.classList.add('disabled');
            }
        });
        return;
    }

    // Handle 1 feature - show name directly (no dropdown)
    if (features.length === 1) {
        selectContainer.style.display = 'none';
        singleFeatureName.style.display = 'block';
        singleFeatureName.textContent = `Feature: ${features[0].name}`;
        currentFeature = features[0].id;
        setFeatureSelectActive(false);
    } else {
        // Handle multiple features - show dropdown
        selectContainer.style.display = 'block';
        singleFeatureName.style.display = 'none';

        // Try to restore saved feature, fall back to first feature
        const savedFeatureExists = savedState.feature && features.find(f => f.id === savedState.feature);
        if (!currentFeature || !features.find(f => f.id === currentFeature)) {
            currentFeature = savedFeatureExists ? savedState.feature : features[0].id;
        }

        select.innerHTML = features.map(f =>
            `<option value="${f.id}" ${f.id === currentFeature ? 'selected' : ''}>${f.name}</option>`
        ).join('');
        select.value = currentFeature;
    }

    // Restore saved page if it's valid for the current feature
    const feature = features.find(f => f.id === currentFeature);
    if (savedState.page && savedState.page !== 'overview') {
        if (savedState.page === 'constitution') {
            // Will be handled by showConstitution() call below
            currentPage = savedState.page;
        } else if (savedState.page === 'kanban' && feature && feature.artifacts && feature.artifacts.kanban?.exists) {
            currentPage = savedState.page;
        } else if (feature && feature.artifacts) {
            const artifactKey = savedState.page.replace('-', '_');
            if (feature.artifacts[artifactKey]?.exists || savedState.page === 'overview') {
                currentPage = savedState.page;
            }
        }
    }

    sidebar.style.display = 'block';
    mainContent.style.display = 'block';

    // Update workflow icons based on current feature
    if (feature && feature.workflow) {
        updateWorkflowIcons(feature.workflow);
        computeFeatureWorktreeStatus(feature);
    } else {
        computeFeatureWorktreeStatus(null);
    }

    updateSidebarState();

    // Restore the page view
    if (currentPage === 'constitution') {
        showConstitution();
    } else {
        isConstitutionView = false;
        // Update sidebar highlighting
        document.querySelectorAll('.sidebar-item').forEach(item => {
            if (item.dataset.page === currentPage) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
        // Update page visibility
        document.querySelectorAll('.page').forEach(page => page.classList.remove('active'));
        const activePageEl = document.getElementById(`page-${currentPage}`);
        if (activePageEl) {
            activePageEl.classList.add('active');
        }
        loadCurrentPage();
    }
}

function updateFeatureListSilent(features) {
    // Same as updateFeatureList but doesn't reload the current page
    // Used during polling to avoid resetting user's view
    const oldFeature = allFeatures.find(f => f.id === currentFeature);
    allFeatures = features;
    const feature = features.find(f => f.id === currentFeature);

    if (feature && feature.workflow) {
        updateWorkflowIcons(feature.workflow);
        computeFeatureWorktreeStatus(feature);
    } else {
        computeFeatureWorktreeStatus(null);
    }
    updateSidebarState();

    // Detect artifact changes and reload overview if artifacts changed
    if (currentPage === 'overview' && oldFeature && feature) {
        const oldArtifacts = JSON.stringify(oldFeature.artifacts);
        const newArtifacts = JSON.stringify(feature.artifacts);
        if (oldArtifacts !== newArtifacts) {
            loadOverview();
        }
    }
}

function fetchData(isInitialLoad = false) {
    if (featureSelectActive && !isInitialLoad) {
        return;
    }
    fetch('/api/features')
        .then(response => response.json())
        .then(data => {
            // Use full update on initial load, silent update on polls
            if (isInitialLoad) {
                updateFeatureList(data.features);
            } else {
                updateFeatureListSilent(data.features);

                // Refresh kanban board if currently viewing it
                if (currentPage === 'kanban' && !isConstitutionView && currentFeature) {
                    loadKanban();
                }
            }

            document.getElementById('last-update').textContent = new Date().toLocaleTimeString();

            if (data.project_path) {
                projectPathDisplay = data.project_path;
            }

            if (data.active_worktree) {
                activeWorktreeDisplay = data.active_worktree;
            } else {
                activeWorktreeDisplay = '';
            }

            if (data.active_mission) {
                updateMissionDisplay(data.active_mission);
            }

            const currentFeatureObj = allFeatures.find(f => f.id === currentFeature);
            computeFeatureWorktreeStatus(currentFeatureObj || null);
            updateTreeInfo();
        })
        .catch(error => console.error('Error fetching data:', error));
}

// Initial fetch
// Diagnostics functions
function showDiagnostics() {
    if (!isConstitutionView && currentPage !== 'diagnostics') {
        lastNonConstitutionPage = currentPage;
    }
    // Switch to diagnostics page
    currentPage = 'diagnostics';
    isConstitutionView = false;
    saveState(currentFeature, 'diagnostics');

    // Update sidebar - consistent with other pages
    document.querySelectorAll('.sidebar-item').forEach(item => {
        if (item.dataset.page === 'diagnostics') {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });

    // Update pages
    document.querySelectorAll('.page').forEach(page => page.classList.remove('active'));
    const diagnosticsPage = document.getElementById('page-diagnostics');
    if (diagnosticsPage) {
        diagnosticsPage.classList.add('active');
    }

    loadDiagnostics();
}

function loadDiagnostics() {
    // Show loading state
    document.getElementById('diagnostics-loading').style.display = 'block';
    document.getElementById('diagnostics-content').style.display = 'none';
    document.getElementById('diagnostics-error').style.display = 'none';

    fetch('/api/diagnostics')
        .then(response => response.json())
        .then(data => {
            displayDiagnostics(data);
        })
        .catch(error => {
            document.getElementById('diagnostics-loading').style.display = 'none';
            document.getElementById('diagnostics-error').style.display = 'block';
            document.getElementById('diagnostics-error-message').textContent = error.toString();
        });
}

function displayDiagnostics(data) {
    document.getElementById('diagnostics-loading').style.display = 'none';
    document.getElementById('diagnostics-content').style.display = 'block';

    // Display environment status
    const statusHtml = `
        <h3>Environment</h3>
        <div><strong>Working Directory:</strong> ${data.current_working_directory}</div>
        <div><strong>Repository Root:</strong> ${data.project_path}</div>
        <div><strong>Git Branch:</strong> ${data.git_branch || 'Not detected'}</div>
        <div><strong>In Worktree:</strong> ${data.in_worktree ? '✅ Yes' : '❌ No'}</div>
        <div><strong>Active Mission:</strong> ${data.active_mission || 'software-dev'}</div>
    `;
    document.getElementById('diagnostics-status').innerHTML = statusHtml;

    // Display file integrity
    if (data.file_integrity) {
        const integrityHtml = `
            <h3>Mission File Integrity</h3>
            <div><strong>Expected Files:</strong> ${data.file_integrity.total_expected}</div>
            <div><strong>Present Files:</strong> ${data.file_integrity.total_present}</div>
            <div><strong>Missing Files:</strong> ${data.file_integrity.total_missing}</div>
            ${data.file_integrity.missing_files && data.file_integrity.missing_files.length > 0 ?
                `<div style="margin-top: 10px;"><strong>Missing:</strong><br>${data.file_integrity.missing_files.slice(0, 5).map(f => `• ${f}`).join('<br>')}</div>` : ''}
        `;
        const integrityDiv = document.createElement('div');
        integrityDiv.innerHTML = integrityHtml;
        integrityDiv.style.marginTop = '20px';
        document.getElementById('diagnostics-status').appendChild(integrityDiv);
    }

    // Display worktree overview
    if (data.worktree_overview) {
        const overviewHtml = `
            <h3>Worktree Overview</h3>
            <div><strong>Total Features:</strong> ${data.worktree_overview.total_features}</div>
            <div><strong>Active Worktrees:</strong> ${data.worktree_overview.active_worktrees}</div>
            <div><strong>Merged Features:</strong> ${data.worktree_overview.merged_features}</div>
            <div><strong>In Development:</strong> ${data.worktree_overview.in_development}</div>
            <div><strong>Not Started:</strong> ${data.worktree_overview.not_started}</div>
        `;
        const overviewDiv = document.createElement('div');
        overviewDiv.innerHTML = overviewHtml;
        overviewDiv.style.marginTop = '20px';
        document.getElementById('diagnostics-status').appendChild(overviewDiv);
    }

    // Display current feature
    if (data.current_feature && data.current_feature.detected) {
        const stateMap = {
            'merged': '✅ MERGED',
            'in_development': '🔄 IN DEVELOPMENT',
            'ready_to_merge': '🔵 READY TO MERGE',
            'not_started': '⏳ NOT STARTED',
            'unknown': '❓ UNKNOWN'
        };
        const currentHtml = `
            <h3>Current Feature</h3>
            <div><strong>Feature:</strong> ${data.current_feature.name}</div>
            <div><strong>State:</strong> ${stateMap[data.current_feature.state] || data.current_feature.state}</div>
            <div><strong>Branch Exists:</strong> ${data.current_feature.branch_exists ? '✅' : '❌'}</div>
            <div><strong>Worktree Exists:</strong> ${data.current_feature.worktree_exists ? '✅' : '❌'}</div>
            ${data.current_feature.worktree_path ? `<div><strong>Worktree Path:</strong> ${data.current_feature.worktree_path}</div>` : ''}
            ${data.current_feature.artifacts_in_main && data.current_feature.artifacts_in_main.length > 0 ?
                `<div><strong>Artifacts in Main:</strong> ${data.current_feature.artifacts_in_main.join(', ')}</div>` : ''}
            ${data.current_feature.artifacts_in_worktree && data.current_feature.artifacts_in_worktree.length > 0 ?
                `<div><strong>Artifacts in Worktree:</strong> ${data.current_feature.artifacts_in_worktree.join(', ')}</div>` : ''}
        `;
        const currentDiv = document.createElement('div');
        currentDiv.innerHTML = currentHtml;
        currentDiv.style.marginTop = '20px';
        document.getElementById('diagnostics-status').appendChild(currentDiv);
    }

    // Display all features table
    if (data.all_features && data.all_features.length > 0) {
        const tableHtml = `
            <h3>All Features Status</h3>
            <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
                <thead>
                    <tr style="background: #f0f0f0;">
                        <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Feature</th>
                        <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">State</th>
                        <th style="padding: 8px; text-align: center; border: 1px solid #ddd;">Branch</th>
                        <th style="padding: 8px; text-align: center; border: 1px solid #ddd;">Worktree</th>
                        <th style="padding: 8px; text-align: center; border: 1px solid #ddd;">Artifacts</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.all_features.slice(0, 10).map(feature => {
                        const stateDisplay = {
                            'merged': '<span style="color: green;">MERGED</span>',
                            'in_development': '<span style="color: orange;">ACTIVE</span>',
                            'ready_to_merge': '<span style="color: blue;">READY</span>',
                            'not_started': '<span style="color: gray;">NOT STARTED</span>',
                            'unknown': '<span style="color: gray;">?</span>'
                        }[feature.state] || feature.state;

                        const branchDisplay = feature.branch_merged ? 'merged' : (feature.branch_exists ? '✓' : '-');
                        const worktreeDisplay = feature.worktree_exists ? '✓' : '-';
                        const artifactCount = (feature.artifacts_in_main || []).length + (feature.artifacts_in_worktree || []).length;
                        const artifactsDisplay = artifactCount > 0 ? artifactCount : '-';

                        return `
                            <tr>
                                <td style="padding: 8px; border: 1px solid #ddd;">${feature.name}</td>
                                <td style="padding: 8px; border: 1px solid #ddd;">${stateDisplay}</td>
                                <td style="padding: 8px; text-align: center; border: 1px solid #ddd;">${branchDisplay}</td>
                                <td style="padding: 8px; text-align: center; border: 1px solid #ddd;">${worktreeDisplay}</td>
                                <td style="padding: 8px; text-align: center; border: 1px solid #ddd;">${artifactsDisplay}</td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
            ${data.all_features.length > 10 ? `<div style="margin-top: 10px; color: #666;">... and ${data.all_features.length - 10} more features</div>` : ''}
        `;
        const tableDiv = document.createElement('div');
        tableDiv.innerHTML = tableHtml;
        tableDiv.style.marginTop = '20px';
        document.getElementById('diagnostics-status').appendChild(tableDiv);
    }

    // Display observations (not prescriptive recommendations)
    if (data.observations && data.observations.length > 0) {
        document.getElementById('diagnostics-issues').style.display = 'block';
        document.querySelector('#diagnostics-issues h3').textContent = 'Observations';
        const obsHtml = data.observations.map(obs => `<div>• ${obs}</div>`).join('');
        document.getElementById('diagnostics-issues-content').innerHTML = obsHtml;
    } else {
        document.getElementById('diagnostics-issues').style.display = 'none';
    }

    // Hide recommendations section since we're being observational
    const recsSection = document.getElementById('diagnostics-recommendations');
    if (recsSection) {
        recsSection.style.display = 'none';
    }
}

function refreshDiagnostics() {
    loadDiagnostics();
}

updateMissionDisplay();
updateTreeInfo();
fetchData(true);  // Pass true for initial load

// Poll every second
setInterval(fetchData, 1000);
