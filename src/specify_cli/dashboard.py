#!/usr/bin/env python3
"""
Zero-footprint dashboard v2 with sidebar navigation and feature dropdown.
"""

import json
import os
import socket
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, List, Any
import re
import urllib.parse


def find_free_port(start_port: int = 9237, max_attempts: int = 100) -> int:
    """
    Find an available port starting from start_port.

    Default port 9237 is chosen to avoid common conflicts:
    - 8080-8090: Common dev servers (npm, python -m http.server, etc.)
    - 3000-3010: React, Next.js, etc.
    - 5000-5010: Flask, Rails, etc.
    - 9237: Uncommon, unlikely to conflict

    Uses dual check: bind test AND connection test to detect existing servers.
    """
    for port in range(start_port, start_port + max_attempts):
        # Check 1: Try to connect (detects existing server)
        try:
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.settimeout(0.1)
            result = test_sock.connect_ex(('127.0.0.1', port))
            test_sock.close()
            if result == 0:
                # Port is in use (something is listening)
                continue
        except:
            pass

        # Check 2: Try to bind (ensures we can actually use it)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue

    raise RuntimeError(f"Could not find free port in range {start_port}-{start_port + max_attempts}")


def parse_frontmatter(content: str) -> Dict[str, Any]:
    """Extract YAML frontmatter from markdown file."""
    if not content.startswith('---'):
        return {}

    parts = content.split('---', 2)
    if len(parts) < 3:
        return {}

    frontmatter = {}
    for line in parts[1].strip().split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip().strip('"\'')

            if key == 'subtasks' and value.startswith('['):
                value = [s.strip().strip('"\'') for s in value.strip('[]').split(',') if s.strip()]

            frontmatter[key] = value

    return frontmatter


def get_feature_artifacts(feature_dir: Path) -> Dict[str, Any]:
    """Get list of available artifacts for a feature."""
    artifacts = {
        'spec': (feature_dir / 'spec.md').exists(),
        'plan': (feature_dir / 'plan.md').exists(),
        'tasks': (feature_dir / 'tasks.md').exists(),
        'research': (feature_dir / 'research.md').exists(),
        'quickstart': (feature_dir / 'quickstart.md').exists(),
        'data_model': (feature_dir / 'data-model.md').exists(),
        'contracts': (feature_dir / 'contracts').exists(),
        'checklists': (feature_dir / 'checklists').exists(),
        'kanban': (feature_dir / 'tasks').exists(),
    }
    return artifacts


def scan_all_features(project_dir: Path) -> List[Dict[str, Any]]:
    """Scan all features and return metadata."""
    specs_dir = project_dir / 'specs'
    features = []

    if not specs_dir.exists():
        return []

    for feature_dir in specs_dir.iterdir():
        if not feature_dir.is_dir():
            continue

        # Only process numbered features or those with tasks
        if not (re.match(r'^\d+', feature_dir.name) or (feature_dir / 'tasks').exists()):
            continue

        # Get artifacts
        artifacts = get_feature_artifacts(feature_dir)

        # Calculate kanban stats if available
        kanban_stats = {'total': 0, 'planned': 0, 'doing': 0, 'for_review': 0, 'done': 0}
        if artifacts['kanban']:
            tasks_dir = feature_dir / 'tasks'
            for lane in ['planned', 'doing', 'for_review', 'done']:
                lane_dir = tasks_dir / lane
                if lane_dir.exists():
                    count = len(list(lane_dir.rglob('WP*.md')))
                    kanban_stats[lane] = count
                    kanban_stats['total'] += count

        features.append({
            'id': feature_dir.name,
            'name': feature_dir.name,
            'path': str(feature_dir.relative_to(project_dir)),
            'artifacts': artifacts,
            'kanban_stats': kanban_stats
        })

    # Sort by name (most recent first)
    features.sort(key=lambda f: f['name'], reverse=True)

    return features


def scan_feature_kanban(project_dir: Path, feature_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """Scan kanban board for a specific feature."""
    feature_dir = project_dir / 'specs' / feature_id
    lanes = {'planned': [], 'doing': [], 'for_review': [], 'done': []}

    if not feature_dir.exists():
        return lanes

    tasks_dir = feature_dir / 'tasks'
    if not tasks_dir.exists():
        return lanes

    # Scan each lane
    for lane in lanes.keys():
        lane_dir = tasks_dir / lane
        if not lane_dir.exists():
            continue

        for prompt_file in lane_dir.rglob('WP*.md'):
            try:
                content = prompt_file.read_text()
                fm = parse_frontmatter(content)

                if 'work_package_id' not in fm:
                    continue

                title_match = re.search(r'^#\s+Work Package Prompt:\s+(.+)$', content, re.MULTILINE)
                title = title_match.group(1) if title_match else prompt_file.stem

                task_data = {
                    'id': fm.get('work_package_id', prompt_file.stem),
                    'title': title,
                    'lane': fm.get('lane', lane),
                    'subtasks': fm.get('subtasks', []),
                    'agent': fm.get('agent', ''),
                    'assignee': fm.get('assignee', ''),
                    'phase': fm.get('phase', ''),
                }

                lanes[lane].append(task_data)
            except Exception as e:
                continue

    return lanes


def get_dashboard_html() -> str:
    """Generate the dashboard HTML with sidebar and dropdown."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Spec Kitty Dashboard</title>
    <style>
        :root {
            --baby-blue: #A7C7E7;
            --grassy-green: #7BB661;
            --lavender: #C9A0DC;
            --sunny-yellow: #FFF275;
            --soft-peach: #FFD8B1;
            --light-gray: #E8E8E8;
            --creamy-white: #FFFDF7;
            --dark-text: #2c3e50;
            --medium-text: #546e7a;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: var(--baby-blue);
            color: var(--dark-text);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        .header {
            background: var(--creamy-white);
            padding: 20px 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 3px solid var(--sunny-yellow);
        }

        .header-left {
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .header h1 {
            font-size: 1.8em;
            color: var(--grassy-green);
            margin: 0;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
        }

        .feature-selector {
            min-width: 300px;
        }

        .feature-selector label {
            display: block;
            font-size: 0.85em;
            color: #6b7280;
            margin-bottom: 5px;
            font-weight: 500;
        }

        .feature-selector select {
            width: 100%;
            padding: 10px 15px;
            border: 2px solid var(--lavender);
            border-radius: 8px;
            font-size: 1em;
            background: var(--creamy-white);
            color: var(--dark-text);
            cursor: pointer;
            transition: all 0.2s;
        }

        .feature-selector select:hover {
            border-color: var(--grassy-green);
            background: white;
        }

        .feature-selector select:focus {
            outline: none;
            border-color: var(--grassy-green);
            box-shadow: 0 0 0 3px rgba(123, 182, 97, 0.2);
        }

        .last-update {
            font-size: 0.85em;
            color: var(--medium-text);
        }

        .container {
            display: flex;
            flex: 1;
            overflow: hidden;
        }

        .sidebar {
            width: 250px;
            background: var(--creamy-white);
            padding: 20px 0;
            box-shadow: 2px 0 10px rgba(0,0,0,0.1);
            overflow-y: auto;
            border-right: 2px solid var(--light-gray);
        }

        .sidebar-item {
            padding: 12px 30px;
            cursor: pointer;
            transition: all 0.2s;
            border-left: 4px solid transparent;
            display: flex;
            align-items: center;
            gap: 10px;
            color: var(--dark-text);
        }

        .sidebar-item:hover {
            background: rgba(201, 160, 220, 0.15);
            color: var(--grassy-green);
        }

        .sidebar-item.active {
            background: rgba(123, 182, 97, 0.1);
            border-left-color: var(--grassy-green);
            color: var(--grassy-green);
            font-weight: 600;
        }

        .sidebar-item.disabled {
            opacity: 0.4;
            cursor: not-allowed;
        }

        .sidebar-item.disabled:hover {
            background: transparent;
            color: #4b5563;
        }

        .main-content {
            flex: 1;
            padding: 30px;
            overflow-y: auto;
        }

        .page {
            display: none;
        }

        .page.active {
            display: block;
        }

        .content-card {
            background: var(--creamy-white);
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            border-top: 3px solid var(--sunny-yellow);
        }

        .content-card h2 {
            color: var(--grassy-green);
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid var(--soft-peach);
        }

        .markdown-content {
            line-height: 1.6;
            color: #374151;
        }

        .markdown-content h1, .markdown-content h2, .markdown-content h3 {
            margin-top: 24px;
            margin-bottom: 12px;
            color: #1f2937;
        }

        .markdown-content p {
            margin-bottom: 12px;
        }

        .markdown-content code {
            background: #f3f4f6;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.9em;
        }

        .markdown-content pre {
            background: #1f2937;
            color: #f3f4f6;
            padding: 16px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 16px 0;
        }

        .markdown-content ul, .markdown-content ol {
            margin-left: 24px;
            margin-bottom: 12px;
        }

        /* Status summary styles */
        .status-summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }

        .status-card {
            background: linear-gradient(135deg, var(--creamy-white) 0%, #fafaf8 100%);
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid;
        }

        .status-card.total { border-left-color: var(--baby-blue); }
        .status-card.progress { border-left-color: var(--sunny-yellow); }
        .status-card.review { border-left-color: var(--lavender); }
        .status-card.completed { border-left-color: var(--grassy-green); }
        .status-card.agents { border-left-color: var(--soft-peach); }

        .status-label {
            font-size: 0.85em;
            color: #6b7280;
            font-weight: 500;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .status-value {
            font-size: 2.5em;
            font-weight: 700;
            color: #1f2937;
            line-height: 1;
        }

        .status-detail {
            font-size: 0.85em;
            color: #9ca3af;
            margin-top: 6px;
        }

        .progress-bar {
            width: 100%;
            height: 6px;
            background: #e5e7eb;
            border-radius: 3px;
            margin-top: 10px;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--grassy-green) 0%, #5a9647 100%);
            transition: width 0.3s ease;
        }

        /* Kanban board styles */
        .kanban-board {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
        }

        .lane {
            background: var(--creamy-white);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            min-height: 400px;
            border-top: 3px solid;
        }

        .lane-header {
            font-size: 1.2em;
            font-weight: 600;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .lane-header .count {
            font-size: 0.8em;
            background: rgba(0,0,0,0.08);
            padding: 4px 10px;
            border-radius: 12px;
        }

        .lane.planned { border-top-color: var(--baby-blue); }
        .lane.planned .lane-header { border-color: var(--baby-blue); color: var(--baby-blue); }

        .lane.doing { border-top-color: var(--sunny-yellow); }
        .lane.doing .lane-header { border-color: var(--sunny-yellow); color: #d4a800; }

        .lane.for_review { border-top-color: var(--lavender); }
        .lane.for_review .lane-header { border-color: var(--lavender); color: var(--lavender); }

        .lane.done { border-top-color: var(--grassy-green); }
        .lane.done .lane-header { border-color: var(--grassy-green); color: var(--grassy-green); }

        .card {
            background: white;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.08);
            border-left: 4px solid;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            background: var(--creamy-white);
        }

        .lane.planned .card { border-left-color: var(--baby-blue); }
        .lane.doing .card { border-left-color: var(--sunny-yellow); }
        .lane.for_review .card { border-left-color: var(--lavender); }
        .lane.done .card { border-left-color: var(--grassy-green); }

        .card-id {
            font-weight: 600;
            color: #6b7280;
            font-size: 0.85em;
            margin-bottom: 5px;
        }

        .card-title {
            font-size: 1.05em;
            font-weight: 500;
            margin-bottom: 8px;
            color: #1f2937;
            line-height: 1.4;
        }

        .card-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 10px;
        }

        .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.75em;
            font-weight: 500;
        }

        .badge.agent {
            background: var(--soft-peach);
            color: #8b5a00;
        }

        .badge.subtasks {
            background: var(--lavender);
            color: #5a3a6e;
        }

        .empty-state {
            text-align: center;
            color: #9ca3af;
            padding: 40px 20px;
            font-style: italic;
        }

        .no-features {
            text-align: center;
            padding: 60px 40px;
        }

        .no-features h2 {
            color: white;
            margin-bottom: 15px;
        }

        .no-features p {
            color: rgba(255, 255, 255, 0.8);
            line-height: 1.6;
        }

        @media (max-width: 1400px) {
            .kanban-board {
                grid-template-columns: repeat(2, 1fr);
            }
        }

        @media (max-width: 768px) {
            .container {
                flex-direction: column;
            }
            .sidebar {
                width: 100%;
            }
            .kanban-board {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-left">
            <h1>🌱 Spec Kitty</h1>
            <div class="feature-selector">
                <label>Feature:</label>
                <select id="feature-select" onchange="switchFeature(this.value)">
                    <option value="">Loading...</option>
                </select>
            </div>
        </div>
        <div class="last-update">Last updated: <span id="last-update">Loading...</span></div>
    </div>

    <div class="container">
        <div class="sidebar">
            <div class="sidebar-item active" data-page="overview" onclick="switchPage('overview')">
                📊 Overview
            </div>
            <div class="sidebar-item" data-page="spec" onclick="switchPage('spec')">
                📄 Spec
            </div>
            <div class="sidebar-item" data-page="plan" onclick="switchPage('plan')">
                🏗️ Plan
            </div>
            <div class="sidebar-item" data-page="tasks" onclick="switchPage('tasks')">
                📋 Tasks
            </div>
            <div class="sidebar-item" data-page="kanban" onclick="switchPage('kanban')">
                🎯 Kanban
            </div>
            <div class="sidebar-item" data-page="research" onclick="switchPage('research')">
                🔬 Research
            </div>
            <div class="sidebar-item" data-page="quickstart" onclick="switchPage('quickstart')">
                🚀 Quickstart
            </div>
            <div class="sidebar-item" data-page="data-model" onclick="switchPage('data-model')">
                💾 Data Model
            </div>
        </div>

        <div class="main-content">
            <div id="page-overview" class="page active">
                <div class="content-card">
                    <h2>Feature Overview</h2>
                    <div id="overview-content"></div>
                </div>
            </div>

            <div id="page-spec" class="page">
                <div class="content-card">
                    <h2>Specification</h2>
                    <div id="spec-content" class="markdown-content"></div>
                </div>
            </div>

            <div id="page-plan" class="page">
                <div class="content-card">
                    <h2>Implementation Plan</h2>
                    <div id="plan-content" class="markdown-content"></div>
                </div>
            </div>

            <div id="page-tasks" class="page">
                <div class="content-card">
                    <h2>Task List</h2>
                    <div id="tasks-content" class="markdown-content"></div>
                </div>
            </div>

            <div id="page-kanban" class="page">
                <div class="content-card">
                    <h2>Kanban Board</h2>
                    <div id="kanban-status" class="status-summary"></div>
                    <div id="kanban-board" class="kanban-board"></div>
                </div>
            </div>

            <div id="page-research" class="page">
                <div class="content-card">
                    <h2>Research</h2>
                    <div id="research-content" class="markdown-content"></div>
                </div>
            </div>

            <div id="page-quickstart" class="page">
                <div class="content-card">
                    <h2>Quickstart Guide</h2>
                    <div id="quickstart-content" class="markdown-content"></div>
                </div>
            </div>

            <div id="page-data-model" class="page">
                <div class="content-card">
                    <h2>Data Model</h2>
                    <div id="data-model-content" class="markdown-content"></div>
                </div>
            </div>

            <div id="no-features-message" class="no-features" style="display: none;">
                <h2>No Features Found</h2>
                <p>Create your first feature using <code>/speckitty.specify</code></p>
            </div>
        </div>
    </div>

    <script>
        let currentFeature = null;
        let currentPage = 'overview';
        let allFeatures = [];

        function switchFeature(featureId) {
            currentFeature = featureId;
            loadCurrentPage();
            updateSidebarState();
        }

        function switchPage(pageName) {
            currentPage = pageName;

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
            document.getElementById(`page-${pageName}`)?.classList.add('active');

            loadCurrentPage();
        }

        function updateSidebarState() {
            const feature = allFeatures.find(f => f.id === currentFeature);
            if (!feature) return;

            const artifacts = feature.artifacts;

            document.querySelectorAll('.sidebar-item').forEach(item => {
                const page = item.dataset.page;
                const hasArtifact = page === 'overview' || artifacts[page.replace('-', '_')];

                if (hasArtifact) {
                    item.classList.remove('disabled');
                } else {
                    item.classList.add('disabled');
                }
            });
        }

        function loadCurrentPage() {
            if (!currentFeature) return;

            if (currentPage === 'overview') {
                loadOverview();
            } else if (currentPage === 'kanban') {
                loadKanban();
            } else {
                loadArtifact(currentPage);
            }
        }

        function loadOverview() {
            const feature = allFeatures.find(f => f.id === currentFeature);
            if (!feature) return;

            const stats = feature.kanban_stats;
            const total = stats.total;
            const completed = stats.done;
            const completionRate = total > 0 ? Math.round((completed / total) * 100) : 0;

            const artifacts = feature.artifacts;
            const artifactList = [
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
                <div style="padding: 10px; background: ${artifacts[a.key] ? '#ecfdf5' : '#fef2f2'};
                     border-radius: 6px; border-left: 3px solid ${artifacts[a.key] ? '#10b981' : '#ef4444'};">
                    ${a.icon} ${a.name}: ${artifacts[a.key] ? '✅ Available' : '❌ Not created'}
                </div>
            `).join('');

            document.getElementById('overview-content').innerHTML = `
                <div style="margin-bottom: 30px;">
                    <h3>Feature: ${feature.name}</h3>
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
                <div class="card">
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
        }

        function loadArtifact(artifactName) {
            const artifactKey = artifactName.replace('-', '_');
            fetch(`/api/artifact/${currentFeature}/${artifactName}`)
                .then(response => response.ok ? response.text() : Promise.reject('Not found'))
                .then(content => {
                    document.getElementById(`${artifactName}-content`).innerHTML =
                        `<pre style="white-space: pre-wrap; font-family: inherit;">${escapeHtml(content)}</pre>`;
                })
                .catch(error => {
                    document.getElementById(`${artifactName}-content`).innerHTML =
                        '<div class="empty-state">Artifact not available</div>';
                });
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function updateFeatureList(features) {
            allFeatures = features;
            const select = document.getElementById('feature-select');

            if (features.length === 0) {
                select.innerHTML = '<option value="">No features</option>';
                document.getElementById('no-features-message').style.display = 'block';
                document.querySelector('.sidebar').style.display = 'none';
                document.querySelector('.main-content').style.display = 'none';
                return;
            }

            document.getElementById('no-features-message').style.display = 'none';
            document.querySelector('.sidebar').style.display = 'block';
            document.querySelector('.main-content').style.display = 'block';

            select.innerHTML = features.map(f =>
                `<option value="${f.id}" ${f.id === currentFeature ? 'selected' : ''}>${f.name}</option>`
            ).join('');

            if (!currentFeature || !features.find(f => f.id === currentFeature)) {
                currentFeature = features[0].id;
                select.value = currentFeature;
            }

            updateSidebarState();
            loadCurrentPage();
        }

        function fetchData() {
            fetch('/api/features')
                .then(response => response.json())
                .then(data => {
                    updateFeatureList(data.features);
                    document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
                })
                .catch(error => console.error('Error fetching data:', error));
        }

        // Initial fetch
        fetchData();

        // Poll every second
        setInterval(fetchData, 1000);
    </script>
</body>
</html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the dashboard."""

    project_dir = None

    def log_message(self, format, *args):
        """Suppress request logging."""
        pass

    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(get_dashboard_html().encode())

        elif self.path == '/api/features':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()

            features = scan_all_features(Path(self.project_dir))
            self.wfile.write(json.dumps({'features': features}).encode())

        elif self.path.startswith('/api/kanban/'):
            feature_id = self.path.split('/')[-1]
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()

            lanes = scan_feature_kanban(Path(self.project_dir), feature_id)
            self.wfile.write(json.dumps(lanes).encode())

        elif self.path.startswith('/api/artifact/'):
            parts = self.path.split('/')
            if len(parts) >= 4:
                feature_id = parts[3]
                artifact_name = parts[4] if len(parts) > 4 else ''

                project_path = Path(self.project_dir)
                feature_dir = project_path / 'specs' / feature_id

                # Map artifact names to files
                artifact_map = {
                    'spec': 'spec.md',
                    'plan': 'plan.md',
                    'tasks': 'tasks.md',
                    'research': 'research.md',
                    'quickstart': 'quickstart.md',
                    'data-model': 'data-model.md',
                }

                filename = artifact_map.get(artifact_name)
                if filename:
                    artifact_file = feature_dir / filename
                    if artifact_file.exists():
                        self.send_response(200)
                        self.send_header('Content-type', 'text/plain')
                        self.send_header('Cache-Control', 'no-cache')
                        self.end_headers()
                        self.wfile.write(artifact_file.read_text().encode())
                        return

            self.send_response(404)
            self.end_headers()

        else:
            self.send_response(404)
            self.end_headers()


def start_dashboard(project_dir: Path, port: int = None, background_process: bool = False) -> tuple[int, threading.Thread]:
    """
    Start the dashboard server.

    Args:
        project_dir: Project directory to serve
        port: Port to use (None = auto-find)
        background_process: If True, fork a detached background process that survives parent exit

    Returns:
        Tuple of (port, thread)
    """
    if port is None:
        port = find_free_port()

    if background_process:
        # Fork a detached background process that survives parent exit
        import subprocess
        import sys

        # Write a small Python script to run the server
        script = f"""
import sys
from pathlib import Path
sys.path.insert(0, '{Path(__file__).parent}')
from dashboard import DashboardHandler, HTTPServer

handler_class = type('DashboardHandler', (DashboardHandler,), {{
    'project_dir': '{project_dir}'
}})

server = HTTPServer(('127.0.0.1', {port}), handler_class)
server.serve_forever()
"""

        # Start detached process (survives parent exit)
        process = subprocess.Popen(
            [sys.executable, '-c', script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True  # Detach from parent
        )

        # Return dummy thread (process is independent)
        return port, None
    else:
        # Original threaded approach (for compatibility)
        handler_class = type('DashboardHandler', (DashboardHandler,), {
            'project_dir': str(project_dir)
        })

        server = HTTPServer(('127.0.0.1', port), handler_class)

        def serve():
            server.serve_forever()

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()

        return port, thread
