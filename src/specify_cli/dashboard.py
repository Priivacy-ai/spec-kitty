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


def find_free_port(start_port: int = 8080, max_attempts: int = 100) -> int:
    """
    Find an available port starting from start_port.

    Automatically scans through ports to find one that's not in use.
    For example, if 8080-8082 are occupied, it will return 8083.

    Args:
        start_port: First port to try (default: 8080)
        max_attempts: Maximum number of ports to try (default: 100)

    Returns:
        First available port number

    Raises:
        RuntimeError: If no free port found in the range
    """
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
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


def scan_tasks(project_dir: Path) -> Dict[str, List[Dict[str, Any]]]:
    """Scan the tasks directory and return kanban state."""
    specs_dir = project_dir / 'specs'
    lanes = {'planned': [], 'doing': [], 'for_review': [], 'done': []}

    if not specs_dir.exists():
        return lanes

    # Find all feature directories
    for feature_dir in specs_dir.iterdir():
        if not feature_dir.is_dir():
            continue

        tasks_dir = feature_dir / 'tasks'
        if not tasks_dir.exists():
            continue

        feature_name = feature_dir.name

        # Scan each lane
        for lane in lanes.keys():
            lane_dir = tasks_dir / lane
            if not lane_dir.exists():
                continue

            # Find all prompt files (including in phase subdirectories)
            for prompt_file in lane_dir.rglob('WP*.md'):
                try:
                    content = prompt_file.read_text()
                    fm = parse_frontmatter(content)

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
                    print(f"Error parsing {prompt_file}: {e}")
                    continue

    return lanes


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
            margin-bottom: 30px;
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

        .last-update {
            color: white;
            text-align: center;
            margin-bottom: 20px;
            opacity: 0.8;
            font-size: 0.9em;
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

    <div class="kanban-board">
        <div class="lane planned">
            <div class="lane-header">
                <span>📋 Planned</span>
                <span class="count" id="count-planned">0</span>
            </div>
            <div id="lane-planned"></div>
        </div>

        <div class="lane doing">
            <div class="lane-header">
                <span>🚀 Doing</span>
                <span class="count" id="count-doing">0</span>
            </div>
            <div id="lane-doing"></div>
        </div>

        <div class="lane for_review">
            <div class="lane-header">
                <span>👀 For Review</span>
                <span class="count" id="count-for_review">0</span>
            </div>
            <div id="lane-for_review"></div>
        </div>

        <div class="lane done">
            <div class="lane-header">
                <span>✅ Done</span>
                <span class="count" id="count-done">0</span>
            </div>
            <div id="lane-done"></div>
        </div>
    </div>

    <script>
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
                        <span class="badge feature">${task.feature}</span>
                        ${agentText}
                        ${subtasksText}
                    </div>
                </div>
            `;
        }

        function updateDashboard(data) {
            const lanes = ['planned', 'doing', 'for_review', 'done'];

            lanes.forEach(lane => {
                const container = document.getElementById(`lane-${lane}`);
                const count = document.getElementById(`count-${lane}`);
                const tasks = data[lane] || [];

                count.textContent = tasks.length;

                if (tasks.length === 0) {
                    container.innerHTML = '<div class="empty-state">No tasks</div>';
                } else {
                    container.innerHTML = tasks.map(createCard).join('');
                }
            });

            document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
        }

        function fetchData() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => updateDashboard(data))
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
