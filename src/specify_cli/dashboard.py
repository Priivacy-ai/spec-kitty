#!/usr/bin/env python3
"""
Zero-footprint dashboard server for Spec Kitty projects.
Serves a kanban board visualization of task progress.
"""

import json
import os
import socket
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, List, Any
import re


def find_free_port(start_port: int = 9237, max_attempts: int = 100) -> int:
    """
    Find an available port starting from start_port.

    Default port 9237 is chosen to avoid common conflicts:
    - 8080-8090: Common dev servers (npm, python -m http.server, etc.)
    - 3000-3010: React, Next.js, etc.
    - 5000-5010: Flask, Rails, etc.
    - 9237: Uncommon, unlikely to conflict

    Uses dual check: bind test AND connection test to detect existing servers.

    Args:
        start_port: First port to try (default: 9237)
        max_attempts: Maximum number of ports to try (default: 100)

    Returns:
        First available port number

    Raises:
        RuntimeError: If no free port found in the range
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
            # Port in use, try next one
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

            # Handle arrays
            if key == 'subtasks':
                # Simple array parsing for subtasks: ["T001", "T002"]
                if value.startswith('['):
                    value = [s.strip().strip('"\'') for s in value.strip('[]').split(',') if s.strip()]

            frontmatter[key] = value

    return frontmatter


def scan_tasks(project_dir: Path) -> Dict[str, Any]:
    """
    Scan the tasks directory and return kanban state grouped by feature.

    Returns:
        {
            'features': [
                {
                    'id': '001-feature-name',
                    'name': '001-feature-name',
                    'lanes': {'planned': [...], 'doing': [...], 'for_review': [...], 'done': [...]}
                },
                ...
            ]
        }
    """
    specs_dir = project_dir / 'specs'
    features = []

    if not specs_dir.exists():
        return {'features': []}

    # Find all feature directories (must match pattern XXX-name)
    feature_dirs = []
    for feature_dir in specs_dir.iterdir():
        if not feature_dir.is_dir():
            continue

        # Safeguard: Only process directories that look like feature directories
        # Pattern: starts with digits (001, 002, etc.) or has a tasks subdirectory
        if not (re.match(r'^\d+', feature_dir.name) or (feature_dir / 'tasks').exists()):
            continue

        tasks_dir = feature_dir / 'tasks'
        if not tasks_dir.exists():
            continue

        feature_dirs.append(feature_dir)

    # Sort features by name (most recent = highest number first)
    feature_dirs.sort(key=lambda d: d.name, reverse=True)

    # Scan each feature
    for feature_dir in feature_dirs:
        feature_name = feature_dir.name
        tasks_dir = feature_dir / 'tasks'
        lanes = {'planned': [], 'doing': [], 'for_review': [], 'done': []}

        # Scan each lane
        for lane in lanes.keys():
            lane_dir = tasks_dir / lane
            if not lane_dir.exists():
                continue

            # Find all prompt files (including in phase subdirectories)
            # Safeguard: Only files matching WP*.md pattern
            for prompt_file in lane_dir.rglob('WP*.md'):
                try:
                    content = prompt_file.read_text()
                    fm = parse_frontmatter(content)

                    # Safeguard: Skip files without work_package_id in frontmatter
                    if 'work_package_id' not in fm:
                        continue

                    # Extract title from first heading
                    title_match = re.search(r'^#\s+Work Package Prompt:\s+(.+)$', content, re.MULTILINE)
                    title = title_match.group(1) if title_match else prompt_file.stem

                    task_data = {
                        'id': fm.get('work_package_id', prompt_file.stem),
                        'title': title,
                        'feature': feature_name,
                        'lane': fm.get('lane', lane),
                        'subtasks': fm.get('subtasks', []),
                        'agent': fm.get('agent', ''),
                        'assignee': fm.get('assignee', ''),
                        'phase': fm.get('phase', ''),
                        'path': str(prompt_file.relative_to(project_dir))
                    }

                    lanes[lane].append(task_data)
                except Exception as e:
                    # Safeguard: Skip files that can't be parsed
                    print(f"Skipping {prompt_file}: {e}")
                    continue

        features.append({
            'id': feature_name,
            'name': feature_name,
            'lanes': lanes
        })

    return {'features': features}


def get_dashboard_html() -> str:
    """Generate the dashboard HTML with embedded CSS and JavaScript."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Spec Kitty Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .header {
            text-align: center;
            color: white;
            margin-bottom: 20px;
        }

        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }

        .header .subtitle {
            font-size: 1.1em;
            opacity: 0.9;
        }

        .tabs-container {
            max-width: 1800px;
            margin: 0 auto 20px auto;
        }

        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
            justify-content: center;
        }

        .tab {
            background: rgba(255, 255, 255, 0.2);
            color: white;
            padding: 12px 24px;
            border-radius: 8px 8px 0 0;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: 500;
            border: 2px solid transparent;
        }

        .tab:hover {
            background: rgba(255, 255, 255, 0.3);
        }

        .tab.active {
            background: rgba(255, 255, 255, 0.95);
            color: #667eea;
            border-bottom: 2px solid rgba(255, 255, 255, 0.95);
            font-weight: 600;
        }

        .feature-board {
            display: none;
        }

        .feature-board.active {
            display: block;
        }

        .last-update {
            color: white;
            text-align: center;
            margin-bottom: 20px;
            opacity: 0.8;
            font-size: 0.9em;
        }

        .no-features {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 12px;
            padding: 60px 40px;
            text-align: center;
            max-width: 600px;
            margin: 40px auto;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .no-features h2 {
            color: #6b7280;
            margin-bottom: 15px;
        }

        .no-features p {
            color: #9ca3af;
            line-height: 1.6;
        }

        .status-summary {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 12px;
            padding: 20px;
            margin: 0 auto 25px auto;
            max-width: 1800px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }

        .status-card {
            background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid;
        }

        .status-card.total { border-left-color: #6366f1; }
        .status-card.progress { border-left-color: #f59e0b; }
        .status-card.review { border-left-color: #8b5cf6; }
        .status-card.completed { border-left-color: #10b981; }
        .status-card.agents { border-left-color: #ec4899; }

        .status-label {
            font-size: 0.85em;
            color: #6b7280;
            font-weight: 500;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .status-value {
            font-size: 2em;
            font-weight: 700;
            color: #1f2937;
            line-height: 1;
        }

        .status-detail {
            font-size: 0.8em;
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
            background: linear-gradient(90deg, #10b981 0%, #059669 100%);
            transition: width 0.3s ease;
        }

        .kanban-board {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            max-width: 1800px;
            margin: 0 auto;
        }

        .lane {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            min-height: 400px;
        }

        .lane-header {
            font-size: 1.3em;
            font-weight: 600;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 3px solid;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .lane-header .count {
            font-size: 0.8em;
            background: rgba(0,0,0,0.1);
            padding: 4px 10px;
            border-radius: 12px;
        }

        .lane.planned .lane-header { border-color: #3b82f6; color: #3b82f6; }
        .lane.doing .lane-header { border-color: #f59e0b; color: #f59e0b; }
        .lane.for_review .lane-header { border-color: #8b5cf6; color: #8b5cf6; }
        .lane.done .lane-header { border-color: #10b981; color: #10b981; }

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
        }

        .lane.planned .card { border-left-color: #3b82f6; }
        .lane.doing .card { border-left-color: #f59e0b; }
        .lane.for_review .card { border-left-color: #8b5cf6; }
        .lane.done .card { border-left-color: #10b981; }

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

        .badge.feature {
            background: #dbeafe;
            color: #1e40af;
        }

        .badge.agent {
            background: #fef3c7;
            color: #92400e;
        }

        .badge.subtasks {
            background: #e0e7ff;
            color: #3730a3;
        }

        .empty-state {
            text-align: center;
            color: #9ca3af;
            padding: 40px 20px;
            font-style: italic;
        }

        @media (max-width: 1400px) {
            .kanban-board {
                grid-template-columns: repeat(2, 1fr);
            }
        }

        @media (max-width: 768px) {
            .kanban-board {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🌱 Spec Kitty Dashboard</h1>
        <div class="subtitle">Real-time Kanban Board</div>
    </div>

    <div class="last-update">Last updated: <span id="last-update">Loading...</span></div>

    <div class="tabs-container">
        <div class="tabs" id="feature-tabs"></div>
    </div>

    <div id="feature-boards"></div>

    <div id="no-features" class="no-features" style="display: none;">
        <h2>No Features Found</h2>
        <p>Create your first feature specification using <code>/speckitty.specify</code></p>
    </div>

    <script>
        let currentFeature = null;

        function createCard(task) {
            const subtasksText = task.subtasks && task.subtasks.length > 0
                ? `<span class="badge subtasks">${task.subtasks.length} subtask${task.subtasks.length !== 1 ? 's' : ''}</span>`
                : '';

            const agentText = task.agent
                ? `<span class="badge agent">${task.agent}</span>`
                : '';

            return `
                <div class="card">
                    <div class="card-id">${task.id}</div>
                    <div class="card-title">${task.title}</div>
                    <div class="card-meta">
                        ${agentText}
                        ${subtasksText}
                    </div>
                </div>
            `;
        }

        function switchToFeature(featureId) {
            currentFeature = featureId;

            // Update tab active states
            document.querySelectorAll('.tab').forEach(tab => {
                if (tab.dataset.featureId === featureId) {
                    tab.classList.add('active');
                } else {
                    tab.classList.remove('active');
                }
            });

            // Update board visibility
            document.querySelectorAll('.feature-board').forEach(board => {
                if (board.dataset.featureId === featureId) {
                    board.classList.add('active');
                } else {
                    board.classList.remove('active');
                }
            });
        }

        function updateDashboard(data) {
            const features = data.features || [];
            const tabsContainer = document.getElementById('feature-tabs');
            const boardsContainer = document.getElementById('feature-boards');
            const noFeatures = document.getElementById('no-features');

            if (features.length === 0) {
                tabsContainer.innerHTML = '';
                boardsContainer.innerHTML = '';
                noFeatures.style.display = 'block';
                return;
            }

            noFeatures.style.display = 'none';

            // Build tabs
            const tabsHTML = features.map(feature =>
                `<div class="tab" data-feature-id="${feature.id}" onclick="switchToFeature('${feature.id}')">
                    ${feature.name}
                </div>`
            ).join('');
            tabsContainer.innerHTML = tabsHTML;

            // Build boards
            const boardsHTML = features.map(feature => {
                const lanes = feature.lanes;
                const total = lanes.planned.length + lanes.doing.length + lanes.for_review.length + lanes.done.length;
                const inProgress = lanes.doing.length;
                const review = lanes.for_review.length;
                const completed = lanes.done.length;
                const completionRate = total > 0 ? Math.round((completed / total) * 100) : 0;

                // Collect unique agents
                const agents = new Set();
                Object.values(lanes).forEach(tasks => {
                    tasks.forEach(task => {
                        if (task.agent && task.agent !== 'system') {
                            agents.add(task.agent);
                        }
                    });
                });

                return `
                    <div class="feature-board" data-feature-id="${feature.id}">
                        <div class="status-summary">
                            <div class="status-grid">
                                <div class="status-card total">
                                    <div class="status-label">Total Work Packages</div>
                                    <div class="status-value">${total}</div>
                                    <div class="status-detail">${lanes.planned.length} planned</div>
                                </div>
                                <div class="status-card progress">
                                    <div class="status-label">In Progress</div>
                                    <div class="status-value">${inProgress}</div>
                                    <div class="status-detail">actively working</div>
                                </div>
                                <div class="status-card review">
                                    <div class="status-label">Awaiting Review</div>
                                    <div class="status-value">${review}</div>
                                    <div class="status-detail">needs approval</div>
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
                            </div>
                        </div>
                        <div class="kanban-board">
                            <div class="lane planned">
                                <div class="lane-header">
                                    <span>📋 Planned</span>
                                    <span class="count">${lanes.planned.length}</span>
                                </div>
                                <div>
                                    ${lanes.planned.length === 0
                                        ? '<div class="empty-state">No tasks</div>'
                                        : lanes.planned.map(createCard).join('')}
                                </div>
                            </div>

                            <div class="lane doing">
                                <div class="lane-header">
                                    <span>🚀 Doing</span>
                                    <span class="count">${lanes.doing.length}</span>
                                </div>
                                <div>
                                    ${lanes.doing.length === 0
                                        ? '<div class="empty-state">No tasks</div>'
                                        : lanes.doing.map(createCard).join('')}
                                </div>
                            </div>

                            <div class="lane for_review">
                                <div class="lane-header">
                                    <span>👀 For Review</span>
                                    <span class="count">${lanes.for_review.length}</span>
                                </div>
                                <div>
                                    ${lanes.for_review.length === 0
                                        ? '<div class="empty-state">No tasks</div>'
                                        : lanes.for_review.map(createCard).join('')}
                                </div>
                            </div>

                            <div class="lane done">
                                <div class="lane-header">
                                    <span>✅ Done</span>
                                    <span class="count">${lanes.done.length}</span>
                                </div>
                                <div>
                                    ${lanes.done.length === 0
                                        ? '<div class="empty-state">No tasks</div>'
                                        : lanes.done.map(createCard).join('')}
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
            boardsContainer.innerHTML = boardsHTML;

            // Switch to current feature or default to first (most recent)
            if (!currentFeature || !features.find(f => f.id === currentFeature)) {
                currentFeature = features[0].id;
            }
            switchToFeature(currentFeature);
        }

        function updateTimestamp() {
            const now = new Date();
            const timeStr = now.toLocaleTimeString();
            document.getElementById('last-update').textContent = timeStr;
        }

        function fetchData() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    updateDashboard(data);
                    updateTimestamp();
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

    project_dir = None  # Will be set when server is created

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

        elif self.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()

            data = scan_tasks(Path(self.project_dir))
            self.wfile.write(json.dumps(data).encode())

        else:
            self.send_response(404)
            self.end_headers()


def start_dashboard(project_dir: Path, port: int = None) -> tuple[int, threading.Thread]:
    """
    Start the dashboard server in a background thread.

    Returns:
        Tuple of (port, thread) where thread is the server thread
    """
    if port is None:
        port = find_free_port()

    # Create handler class with project_dir bound
    handler_class = type('DashboardHandler', (DashboardHandler,), {
        'project_dir': str(project_dir)
    })

    server = HTTPServer(('127.0.0.1', port), handler_class)

    def serve():
        server.serve_forever()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()

    return port, thread
