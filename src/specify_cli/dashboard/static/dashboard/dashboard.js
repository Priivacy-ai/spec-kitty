let currentMission = null;
let currentPage = 'overview';
let allMissions = [];
let isConstitutionView = false;
let lastNonConstitutionPage = 'overview';
let projectPathDisplay = 'Loading…';
let activeWorktreeDisplay = 'detecting…';
let missionSelectActive = false;
let missionSelectIdleTimer = null;
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

/**
 * Intercept clicks on links within rendered markdown content.
 * Routes artifact links (spec.md, plan.md, etc.) through the dashboard API
 * instead of navigating to broken URLs.
 *
 * @param {HTMLElement} container - The container element with rendered markdown
 * @param {string} basePath - Base path for relative links (e.g., 'research/' for research artifacts)
 */
function interceptMarkdownLinks(container, basePath = '') {
    if (!container) return;

    // Map of artifact names to their dashboard page keys
    const artifactMap = {
        'spec.md': 'spec',
        'plan.md': 'plan',
        'tasks.md': 'tasks',
        'research.md': 'research',
        'quickstart.md': 'quickstart',
        'data-model.md': 'data_model',
        'data_model.md': 'data_model',
    };

    container.querySelectorAll('a').forEach(link => {
        const href = link.getAttribute('href');
        if (!href) return;

        // Skip external links and anchor links
        if (href.startsWith('http://') || href.startsWith('https://') || href.startsWith('#')) {
            return;
        }

        // Normalize the path (remove leading ./ or /)
        let normalizedPath = href.replace(/^\.?\//, '');

        // Check if it's a known artifact (top-level .md file)
        if (artifactMap[normalizedPath]) {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                switchPage(artifactMap[normalizedPath]);
            });
            link.style.cursor = 'pointer';
            link.title = `View ${normalizedPath} in dashboard`;
            return;
        }

        // Check if it's a research/, contracts/, or checklists/ subdirectory file
        if (normalizedPath.startsWith('research/') || normalizedPath.startsWith('contracts/') || normalizedPath.startsWith('checklists/')) {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const fileName = normalizedPath.split('/').pop();
                if (normalizedPath.startsWith('research/')) {
                    loadResearchFile(normalizedPath, fileName);
                } else if (normalizedPath.startsWith('contracts/')) {
                    loadContractFile(normalizedPath, fileName);
                } else if (normalizedPath.startsWith('checklists/')) {
                    loadChecklistFile(normalizedPath, fileName);
                }
            });
            link.style.cursor = 'pointer';
            link.title = `View ${normalizedPath} in dashboard`;
            return;
        }

        // Handle relative paths within the current context (e.g., evidence-log.csv from research.md)
        if (basePath && !normalizedPath.includes('/')) {
            const fullPath = basePath + normalizedPath;
            link.addEventListener('click', (e) => {
                e.preventDefault();
                if (basePath === 'research/') {
                    loadResearchFile(fullPath, normalizedPath);
                } else if (basePath === 'contracts/') {
                    loadContractFile(fullPath, normalizedPath);
                } else if (basePath === 'checklists/') {
                    loadChecklistFile(fullPath, normalizedPath);
                }
            });
            link.style.cursor = 'pointer';
            link.title = `View ${fullPath} in dashboard`;
        }
    });
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
        mission: cookies.lastMission || null,
        page: cookies.lastPage || 'overview'
    };
}

function saveState(mission, page) {
    const expires = new Date();
    expires.setFullYear(expires.getFullYear() + 1); // 1 year

    if (mission) {
        document.cookie = `lastMission=${encodeURIComponent(mission)}; expires=${expires.toUTCString()}; path=/; SameSite=Strict`;
    }
    if (page) {
        document.cookie = `lastPage=${encodeURIComponent(page)}; expires=${expires.toUTCString()}; path=/; SameSite=Strict`;
    }
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const toggle = document.getElementById('sidebar-toggle');
    const collapsed = sidebar.classList.toggle('collapsed');
    toggle.textContent = collapsed ? '›' : '‹';
    const expires = new Date();
    expires.setFullYear(expires.getFullYear() + 1);
    document.cookie = `sidebarCollapsed=${collapsed}; expires=${expires.toUTCString()}; path=/; SameSite=Strict`;
}

function restoreSidebarState() {
    const match = document.cookie.match(/sidebarCollapsed=(\w+)/);
    if (match && match[1] === 'true') {
        const sidebar = document.getElementById('sidebar');
        const toggle = document.getElementById('sidebar-toggle');
        sidebar.classList.add('collapsed');
        toggle.textContent = '›';
    }
}

restoreSidebarState();

function setMissionSelectActive(isActive) {
    if (isActive) {
        missionSelectActive = true;
        if (missionSelectIdleTimer) {
            clearTimeout(missionSelectIdleTimer);
        }
        missionSelectIdleTimer = setTimeout(() => {
            missionSelectActive = false;
            missionSelectIdleTimer = null;
        }, 5000);
    } else {
        missionSelectActive = false;
        if (missionSelectIdleTimer) {
            clearTimeout(missionSelectIdleTimer);
            missionSelectIdleTimer = null;
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
        lines.push(`   └─ Active worktree: ${activeWorktreeDisplay}`);
    }
    // Note: In 0.11.0+, worktrees are per-WP, not per-mission
    // Mission-level worktree display removed (obsolete 0.10.x concept)
    treeElement.textContent = lines.join('\n');
}

function computeMissionWorktreeStatus(mission) {
    // No-op: Mission-level worktrees are obsolete in 0.11.0+
    // In workspace-per-WP model, worktrees are per-WP, not per-mission
    // This function is kept for compatibility but does nothing
}

function switchMission(missionId) {
    const isSameMission = missionId === currentMission;
    if (isConstitutionView) {
        if (isSameMission) {
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
    currentMission = missionId;
    saveState(currentMission, currentPage);
    loadCurrentPage();
    updateSidebarState();
    const mission = allMissions.find(f => f.id === currentMission);
    computeMissionWorktreeStatus(mission);
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
    saveState(currentMission, currentPage);

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
    const mission = allMissions.find(f => f.id === currentMission);
    if (!mission) return;

    const artifacts = mission.artifacts;

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
    if (!currentMission) return;

    if (currentPage === 'overview') {
        loadOverview();
    } else if (currentPage === 'kanban') {
        loadKanban();
    } else if (currentPage === 'contracts') {
        loadContracts();
    } else if (currentPage === 'checklists') {
        loadChecklists();
    } else if (currentPage === 'research') {
        loadResearch();
    } else {
        loadArtifact(currentPage);
    }
}

function loadOverview() {
    const mission = allMissions.find(f => f.id === currentMission);
    if (!mission) return;

    const mergeBadge = (() => {
const meta = mission.meta || {};
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

    const stats = mission.kanban_stats;
    const total = stats.total;
    const completed = stats.done;
    const completionRate = total > 0 ? Math.round((completed / total) * 100) : 0;

    const artifacts = mission.artifacts;
    const artifactList = [
        {name: 'Project Constitution', key: 'constitution', icon: '⚖️'},
        {name: 'Specification', key: 'spec', icon: '📄'},
        {name: 'Plan', key: 'plan', icon: '🏗️'},
        {name: 'Tasks', key: 'tasks', icon: '📋'},
        {name: 'Kanban Board', key: 'kanban', icon: '🎯'},
        {name: 'Research', key: 'research', icon: '🔬'},
        {name: 'Quickstart', key: 'quickstart', icon: '🚀'},
        {name: 'Data Model', key: 'data_model', icon: '💾'},
        {name: 'Contracts', key: 'contracts', icon: '📜'},
        {name: 'Checklists', key: 'checklists', icon: '✅'},
    ].map(a => {
        const isAvailable = artifacts[a.key]?.exists;
        return `
        <div style="padding: 10px; background: ${isAvailable ? '#ecfdf5' : '#fef2f2'};
             border-radius: 6px; border-left: 3px solid ${isAvailable ? '#10b981' : '#ef4444'};">
            ${a.icon} ${a.name}: ${isAvailable ? '✅ Available' : '❌ Not created'}
        </div>
    `}).join('');

    document.getElementById('overview-content').innerHTML = `
<div style="margin-bottom: 30px;">
    <h3>Mission: ${mission.name} ${mergeBadge}</h3>
    <p style="color: #6b7280;">View and track all artifacts for this mission</p>
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
            <div class="status-card approved">
                <div class="status-label">Approved</div>
                <div class="status-value">${stats.approved || 0}</div>
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
    fetch(`/api/kanban/${currentMission}`)
        .then(response => response.json())
        .then(data => {
            renderKanban(data && data.lanes ? data.lanes : data);
        })
        .catch(error => {
            document.getElementById('kanban-board').innerHTML =
                '<div class="empty-state">Error loading kanban board</div>';
        });
}

function renderKanban(lanes) {
    const total = lanes.planned.length + lanes.doing.length + lanes.for_review.length + (lanes.in_review || []).length + (lanes.approved || []).length + lanes.done.length;
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
            <div class="status-label">For Review</div>
            <div class="status-value">${lanes.for_review.length}</div>
        </div>
        <div class="status-card in-review">
            <div class="status-label">In Review</div>
            <div class="status-value">${(lanes.in_review || []).length}</div>
        </div>
        <div class="status-card approved">
            <div class="status-label">Approved</div>
            <div class="status-value">${(lanes.approved || []).length}</div>
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
                ${task.role ? `<span class="badge role">${task.role}</span>` : ''}
                ${task.agent_profile ? `<span class="badge profile">${task.agent_profile}</span>` : ''}
                ${task.task_type ? `<span class="badge task-type">${task.task_type}</span>` : ''}
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
        <div class="lane in_review">
            <div class="lane-header">
                <span>🔍 In Review</span>
                <span class="count">${(lanes.in_review || []).length}</span>
            </div>
            <div>${(lanes.in_review || []).length === 0 ? '<div class="empty-state">No tasks</div>' : (lanes.in_review || []).map(createCard).join('')}</div>
        </div>
        <div class="lane approved">
            <div class="lane-header">
                <span>👍 Approved</span>
                <span class="count">${(lanes.approved || []).length}</span>
            </div>
            <div>${(lanes.approved || []).length === 0 ? '<div class="empty-state">No tasks</div>' : (lanes.approved || []).map(createCard).join('')}</div>
        </div>
        <div class="lane done">
            <div class="lane-header">
                <span>✅ Done</span>
                <span class="count">${lanes.done.length}</span>
            </div>
            <div>${lanes.done.length === 0 ? '<div class="empty-state">No tasks</div>' : lanes.done.map(createCard).join('')}</div>
        </div>
    `;

    ['planned', 'doing', 'for_review', 'in_review', 'approved', 'done'].forEach(laneName => {
        const laneCards = document.querySelectorAll(`.lane.${laneName} .card`);
        laneCards.forEach((card, index) => {
            const task = (lanes[laneName] || [])[index];
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
        if (task.role) metaItems.push(`<span>Role: ${escapeHtml(task.role)}</span>`);
        if (task.agent_profile) metaItems.push(`<span>Profile: ${escapeHtml(task.agent_profile)}</span>`);
        if (task.task_type) metaItems.push(`<span>Type: ${escapeHtml(task.task_type)}</span>`);
        if (task.subtasks && task.subtasks.length) {
            metaItems.push(`<span>${task.subtasks.length} subtask${task.subtasks.length !== 1 ? 's' : ''}</span>`);
        }
        if (task.phase) metaItems.push(`<span>Phase: ${escapeHtml(task.phase)}</span>`);
        if (task.approved_by) metaItems.push(`<span>Approved By: ${escapeHtml(task.approved_by)}</span>`);
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
    fetch(`/api/artifact/${currentMission}/${artifactName}`)
        .then(response => response.ok ? response.text() : Promise.reject('Not found'))
        .then(content => {
            // Render markdown to HTML
            const htmlContent = marked.parse(content);
            const container = document.getElementById(`${artifactName}-content`);
            container.innerHTML = htmlContent;
            // Intercept markdown links to route through dashboard
            interceptMarkdownLinks(container);
        })
        .catch(error => {
            document.getElementById(`${artifactName}-content`).innerHTML =
                '<div class="empty-state">Artifact not available</div>';
        });
}

function loadContracts() {
    fetch(`/api/contracts/${currentMission}`)
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
        const filePathEscaped = escapeHtml(file.path);
        return `
            <div style="margin-bottom: 20px; padding: 15px; background: white; border-radius: 8px; border-left: 4px solid var(--lavender); cursor: pointer;"
                 data-filepath="${filePathEscaped}" data-filename="${fileNameEscaped}" class="contract-item">
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
            API specifications and interface definitions for this mission.
        </p>
        ${contractsHtml}
    `;

    // Add click handlers
    document.querySelectorAll('.contract-item').forEach(item => {
        item.addEventListener('click', () => {
            loadContractFile(item.dataset.filepath, item.dataset.filename);
        });
    });
}

function loadContractFile(filePath, fileName) {
    fetch(`/api/contracts/${currentMission}/${encodeURIComponent(filePath)}`)
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

            const container = document.getElementById('contracts-content');
            container.innerHTML = `
                <div style="margin-bottom: 20px;">
                    <button onclick="loadContracts()"
                            style="padding: 8px 16px; background: var(--baby-blue); border: none; border-radius: 6px; cursor: pointer; color: var(--dark-text); font-weight: 500;">
                        ← Back to Contracts List
                    </button>
                </div>
                <h3 style="color: var(--grassy-green); margin-bottom: 15px;">${escapeHtml(fileName)}</h3>
                ${htmlContent}
            `;
            // Intercept markdown links to route through dashboard
            interceptMarkdownLinks(container, 'contracts/');
        })
        .catch(error => {
            document.getElementById('contracts-content').innerHTML =
                '<div class="empty-state">Error loading contract file</div>';
        });
}

function loadChecklists() {
    fetch(`/api/checklists/${currentMission}`)
        .then(response => response.ok ? response.json() : Promise.reject('Not found'))
        .then(data => {
            if (data.files && data.files.length > 0) {
                renderChecklistsList(data.files);
            } else {
                document.getElementById('checklists-content').innerHTML =
                    '<div class="empty-state">No checklists available.</div>';
            }
        })
        .catch(error => {
            document.getElementById('checklists-content').innerHTML =
                '<div class="empty-state">Checklists directory not found</div>';
        });
}

function renderChecklistsList(files) {
    const checklistsHtml = files.map((file, idx) => {
        const fileNameEscaped = escapeHtml(file.name);
        const filePathEscaped = escapeHtml(file.path);
        return `
            <div style="margin-bottom: 20px; padding: 15px; background: white; border-radius: 8px; border-left: 4px solid var(--lavender); cursor: pointer;"
                 data-filepath="${filePathEscaped}" data-filename="${fileNameEscaped}" class="checklist-item">
                <div style="font-weight: 600; color: var(--dark-text); margin-bottom: 5px;">
                    ${file.icon} ${fileNameEscaped}
                </div>
                <div style="font-size: 0.85em; color: var(--medium-text);">
                    Click to view checklist
                </div>
            </div>
        `;
    }).join('');

    document.getElementById('checklists-content').innerHTML = `
        <p style="margin-bottom: 20px; color: var(--medium-text);">
            Quality control and validation checklists for this mission.
        </p>
        ${checklistsHtml}
    `;

    // Add click handlers
    document.querySelectorAll('.checklist-item').forEach(item => {
        item.addEventListener('click', () => {
            loadChecklistFile(item.dataset.filepath, item.dataset.filename);
        });
    });
}

function loadChecklistFile(filePath, fileName) {
    fetch(`/api/checklists/${currentMission}/${encodeURIComponent(filePath)}`)
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

            const container = document.getElementById('checklists-content');
            container.innerHTML = `
                <div style="margin-bottom: 20px;">
                    <button onclick="loadChecklists()"
                            style="padding: 8px 16px; background: var(--baby-blue); border: none; border-radius: 6px; cursor: pointer; color: var(--dark-text); font-weight: 500;">
                        ← Back to Checklists List
                    </button>
                </div>
                <h3 style="color: var(--grassy-green); margin-bottom: 15px;">${escapeHtml(fileName)}</h3>
                ${htmlContent}
            `;
            // Intercept markdown links to route through dashboard
            interceptMarkdownLinks(container, 'checklists/');
        })
        .catch(error => {
            document.getElementById('checklists-content').innerHTML =
                '<div class="empty-state">Error loading checklist file</div>';
        });
}

function loadResearch() {
    fetch(`/api/research/${currentMission}`)
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

    // Intercept markdown links to route through dashboard
    interceptMarkdownLinks(document.getElementById('research-content'));

    // Add click handlers
    document.querySelectorAll('.research-artifact-item').forEach(item => {
        item.addEventListener('click', () => {
            loadResearchFile(item.dataset.filepath, item.dataset.filename);
        });
    });
}

function loadResearchFile(filePath, fileName) {
    fetch(`/api/research/${currentMission}/${encodeURIComponent(filePath)}`)
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

            const container = document.getElementById('research-content');
            container.innerHTML = `
                <div style="margin-bottom: 20px;">
                    <button onclick="loadResearch()"
                            style="padding: 8px 16px; background: var(--baby-blue); border: none; border-radius: 6px; cursor: pointer; color: var(--dark-text); font-weight: 500;">
                        ← Back to Research
                    </button>
                </div>
                <h3 style="color: var(--grassy-green); margin-bottom: 15px;">${escapeHtml(fileName)}</h3>
                ${htmlContent}
            `;
            // Intercept markdown links to route through dashboard
            interceptMarkdownLinks(container, 'research/');
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
    saveState(currentMission, 'constitution');
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
            const container = document.getElementById('constitution-content');
            container.innerHTML = htmlContent;
            // Intercept markdown links to route through dashboard
            interceptMarkdownLinks(container);
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

function getMissionDisplayName(mission) {
    if (!mission) {
        return 'Unknown mission';
    }

    return mission.display_name || mission.name || mission.id || 'Unknown mission';
}

function updateMissionList(missions, activeMissionId = null) {
    allMissions = missions;
    const selectContainer = document.getElementById('mission-selector-container');
    const select = document.getElementById('mission-select');
    const singleMissionName = document.getElementById('single-mission-name');
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');

    // Restore saved state from cookies on initial load
    const savedState = restoreState();

    if (select && !select.dataset.pauseHandlersAttached) {
        const activate = () => setMissionSelectActive(true);
        const deactivate = () => setMissionSelectActive(false);
        ['focus', 'mousedown', 'keydown', 'click', 'input'].forEach(evt => {
            select.addEventListener(evt, activate);
        });
        ['change', 'blur'].forEach(evt => {
            select.addEventListener(evt, deactivate);
        });
        select.dataset.pauseHandlersAttached = 'true';
    }

    // Handle 0 missions - show welcome page
    if (missions.length === 0) {
        selectContainer.style.display = 'none';
        singleMissionName.style.display = 'none';
        sidebar.style.display = 'block';
        mainContent.style.display = 'block';
        isConstitutionView = false;
        currentMission = null;
        computeMissionWorktreeStatus(null);
        setMissionSelectActive(false);

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

    // Handle 1 mission - show name directly (no dropdown)
    if (missions.length === 1) {
        selectContainer.style.display = 'none';
        singleMissionName.style.display = 'block';
        singleMissionName.textContent = `Mission: ${getMissionDisplayName(missions[0])}`;
        currentMission = activeMissionId || missions[0].id;
        setMissionSelectActive(false);
    } else {
        // Handle multiple missions - show dropdown
        selectContainer.style.display = 'block';
        singleMissionName.style.display = 'none';

        const activeMissionExists = activeMissionId && missions.find(f => f.id === activeMissionId);
        // Try to restore saved mission, fall back to first mission
        const savedMissionExists = savedState.mission && missions.find(f => f.id === savedState.mission);
        if (activeMissionExists) {
            currentMission = activeMissionId;
        } else if (!currentMission || !missions.find(f => f.id === currentMission)) {
            currentMission = savedMissionExists ? savedState.mission : missions[0].id;
        }

        select.innerHTML = missions.map(f =>
            `<option value="${f.id}" ${f.id === currentMission ? 'selected' : ''}>${escapeHtml(getMissionDisplayName(f))}</option>`
        ).join('');
        select.value = currentMission;
    }

    // Restore saved page if it's valid for the current mission
    const mission = missions.find(f => f.id === currentMission);
    if (savedState.page && savedState.page !== 'overview') {
        if (savedState.page === 'constitution') {
            // Will be handled by showConstitution() call below
            currentPage = savedState.page;
        } else if (savedState.page === 'kanban' && mission && mission.artifacts && mission.artifacts.kanban?.exists) {
            currentPage = savedState.page;
        } else if (mission && mission.artifacts) {
            const artifactKey = savedState.page.replace('-', '_');
            if (mission.artifacts[artifactKey]?.exists || savedState.page === 'overview') {
                currentPage = savedState.page;
            }
        }
    }

    sidebar.style.display = 'block';
    mainContent.style.display = 'block';

    // Update workflow icons based on current mission
    if (mission && mission.workflow) {
        updateWorkflowIcons(mission.workflow);
        computeMissionWorktreeStatus(mission);
    } else {
        computeMissionWorktreeStatus(null);
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

function updateMissionListSilent(missions) {
    // Same as updateMissionList but doesn't reload the current page
    // Used during polling to avoid resetting user's view
    const oldMission = allMissions.find(f => f.id === currentMission);
    allMissions = missions;
    const mission = missions.find(f => f.id === currentMission);

    if (mission && mission.workflow) {
        updateWorkflowIcons(mission.workflow);
        computeMissionWorktreeStatus(mission);
    } else {
        computeMissionWorktreeStatus(null);
    }
    updateSidebarState();

    // Detect artifact changes and reload overview if artifacts changed
    if (currentPage === 'overview' && oldMission && mission) {
        const oldArtifacts = JSON.stringify(oldMission.artifacts);
        const newArtifacts = JSON.stringify(mission.artifacts);
        if (oldArtifacts !== newArtifacts) {
            loadOverview();
        }
    }
}

function fetchData(isInitialLoad = false) {
    if (missionSelectActive && !isInitialLoad) {
        return;
    }
    fetch('/api/missions')
        .then(response => response.json())
        .then(data => {
            // Use full update on initial load, silent update on polls
            if (isInitialLoad) {
                updateMissionList(data.missions, data.active_mission_id || null);
            } else {
                updateMissionListSilent(data.missions);

                // Refresh kanban board if currently viewing it
                if (currentPage === 'kanban' && !isConstitutionView && currentMission) {
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

            const currentMissionObj = allMissions.find(f => f.id === currentMission);
            computeMissionWorktreeStatus(currentMissionObj || null);
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
    saveState(currentMission, 'diagnostics');

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
        <div><strong>Working Directory:</strong> ${data.current_working_directory || '(not available)'}</div>
        <div><strong>Repository Root:</strong> ${data.project_path || '(not available)'}</div>
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
            <div><strong>Total Missions:</strong> ${data.worktree_overview.total_missions}</div>
            <div><strong>Active Worktrees:</strong> ${data.worktree_overview.active_worktrees}</div>
            <div><strong>Merged Missions:</strong> ${data.worktree_overview.merged_missions}</div>
            <div><strong>In Development:</strong> ${data.worktree_overview.in_development}</div>
            <div><strong>Not Started:</strong> ${data.worktree_overview.not_started}</div>
        `;
        const overviewDiv = document.createElement('div');
        overviewDiv.innerHTML = overviewHtml;
        overviewDiv.style.marginTop = '20px';
        document.getElementById('diagnostics-status').appendChild(overviewDiv);
    }

    // Display current mission
    if (data.current_mission && data.current_mission.detected) {
        const stateMap = {
            'merged': '✅ MERGED',
            'in_development': '🔄 IN DEVELOPMENT',
            'ready_to_merge': '🔵 READY TO MERGE',
            'not_started': '⏳ NOT STARTED',
            'unknown': '❓ UNKNOWN'
        };
        const currentHtml = `
            <h3>Current Mission</h3>
            <div><strong>Mission:</strong> ${data.current_mission.name}</div>
            <div><strong>State:</strong> ${stateMap[data.current_mission.state] || data.current_mission.state}</div>
            <div><strong>Branch Exists:</strong> ${data.current_mission.branch_exists ? '✅' : '❌'}</div>
            <div><strong>Worktree Exists:</strong> ${data.current_mission.worktree_exists ? '✅' : '❌'}</div>
            ${data.current_mission.worktree_path ? `<div><strong>Worktree Path:</strong> ${data.current_mission.worktree_path}</div>` : ''}
            ${data.current_mission.artifacts_in_main && data.current_mission.artifacts_in_main.length > 0 ?
                `<div><strong>Artifacts in Main:</strong> ${data.current_mission.artifacts_in_main.join(', ')}</div>` : ''}
            ${data.current_mission.artifacts_in_worktree && data.current_mission.artifacts_in_worktree.length > 0 ?
                `<div><strong>Artifacts in Worktree:</strong> ${data.current_mission.artifacts_in_worktree.join(', ')}</div>` : ''}
        `;
        const currentDiv = document.createElement('div');
        currentDiv.innerHTML = currentHtml;
        currentDiv.style.marginTop = '20px';
        document.getElementById('diagnostics-status').appendChild(currentDiv);
    }

    // Display all missions table
    if (data.all_missions && data.all_missions.length > 0) {
        const tableHtml = `
            <h3>All Missions Status</h3>
            <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
                <thead>
                    <tr style="background: #f0f0f0;">
                        <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Mission</th>
                        <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">State</th>
                        <th style="padding: 8px; text-align: center; border: 1px solid #ddd;">Branch</th>
                        <th style="padding: 8px; text-align: center; border: 1px solid #ddd;">Worktree</th>
                        <th style="padding: 8px; text-align: center; border: 1px solid #ddd;">Artifacts</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.all_missions.slice(0, 10).map(missionItem => {
                        const stateDisplay = {
                            'merged': '<span style="color: green;">MERGED</span>',
                            'in_development': '<span style="color: orange;">ACTIVE</span>',
                            'ready_to_merge': '<span style="color: blue;">READY</span>',
                            'not_started': '<span style="color: gray;">NOT STARTED</span>',
                            'unknown': '<span style="color: gray;">?</span>'
                        }[missionItem.state] || missionItem.state;

                        const branchDisplay = missionItem.branch_merged ? 'merged' : (missionItem.branch_exists ? '✓' : '-');
                        const worktreeDisplay = missionItem.worktree_exists ? '✓' : '-';
                        const artifactCount = (missionItem.artifacts_in_main || []).length + (missionItem.artifacts_in_worktree || []).length;
                        const artifactsDisplay = artifactCount > 0 ? artifactCount : '-';

                        return `
                            <tr>
                                <td style="padding: 8px; border: 1px solid #ddd;">${missionItem.name}</td>
                                <td style="padding: 8px; border: 1px solid #ddd;">${stateDisplay}</td>
                                <td style="padding: 8px; text-align: center; border: 1px solid #ddd;">${branchDisplay}</td>
                                <td style="padding: 8px; text-align: center; border: 1px solid #ddd;">${worktreeDisplay}</td>
                                <td style="padding: 8px; text-align: center; border: 1px solid #ddd;">${artifactsDisplay}</td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
            ${data.all_missions.length > 10 ? `<div style="margin-top: 10px; color: #666;">... and ${data.all_missions.length - 10} more missions</div>` : ''}
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
