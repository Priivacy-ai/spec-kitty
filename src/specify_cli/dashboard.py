#!/usr/bin/env python3
"""
Zero-footprint dashboard v2 with sidebar navigation and feature dropdown.
"""

import json
import os
import socket
import threading
import time
import secrets
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import re
import urllib.parse
import urllib.request
import urllib.error
import mimetypes

STATIC_URL_PREFIX = '/static/'
STATIC_DIR = (Path(__file__).parent / 'static').resolve()


def format_path_for_display(path_str: Optional[str]) -> Optional[str]:
    """Return a human-readable path that shortens the user's home directory."""
    if not path_str:
        return path_str

    try:
        path = Path(path_str).expanduser()
    except (TypeError, ValueError):
        return path_str

    try:
        resolved = path.resolve()
    except Exception:
        resolved = path

    try:
        home = Path.home().resolve()
    except Exception:
        home = Path.home()

    try:
        relative = resolved.relative_to(home)
    except ValueError:
        return str(resolved)

    relative_str = str(relative)
    if relative_str in ('', '.'):
        return '~'

    return f"~{os.sep}{relative_str}"


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


def work_package_sort_key(task: Dict[str, Any]) -> tuple:
    """Provide a natural sort key for work package identifiers."""
    work_id = str(task.get('id', '')).strip()
    if not work_id:
        return ((), '')

    number_parts = [
        int(part.lstrip('0') or '0')
        for part in re.findall(r'\d+', work_id)
    ]
    return (tuple(number_parts), work_id.lower())


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


def get_workflow_status(artifacts: Dict[str, bool]) -> Dict[str, str]:
    """
    Determine workflow progression status.

    Returns dict with step names and status ('complete', 'in_progress', 'pending')
    """
    has_spec = artifacts.get('spec', False)
    has_plan = artifacts.get('plan', False)
    has_tasks = artifacts.get('tasks', False)
    has_kanban = artifacts.get('kanban', False)

    # Workflow: specify → plan → tasks → implement
    workflow = {}

    if has_spec:
        workflow['specify'] = 'complete'
    else:
        workflow['specify'] = 'pending'
        workflow['plan'] = 'pending'
        workflow['tasks'] = 'pending'
        workflow['implement'] = 'pending'
        return workflow

    if has_plan:
        workflow['plan'] = 'complete'
    else:
        workflow['plan'] = 'pending'
        workflow['tasks'] = 'pending'
        workflow['implement'] = 'pending'
        return workflow

    if has_tasks:
        workflow['tasks'] = 'complete'
    else:
        workflow['tasks'] = 'pending'
        workflow['implement'] = 'pending'
        return workflow

    if has_kanban:
        workflow['implement'] = 'in_progress'
    else:
        workflow['implement'] = 'pending'

    return workflow


def gather_feature_paths(project_dir: Path) -> Dict[str, Path]:
    """Collect candidate feature directories from root and worktrees."""
    feature_paths: Dict[str, Path] = {}

    # Root-level specs (legacy / non-worktree workflows)
    root_specs = project_dir / 'kitty-specs'
    if root_specs.exists():
        for feature_dir in root_specs.iterdir():
            if feature_dir.is_dir():
                feature_paths[feature_dir.name] = feature_dir

    # Worktree-hosted specs (preferred in worktree workflow)
    worktrees_root = project_dir / '.worktrees'
    if worktrees_root.exists():
        for worktree_dir in worktrees_root.iterdir():
            if not worktree_dir.is_dir():
                continue
            wt_specs = worktree_dir / 'kitty-specs'
            if not wt_specs.exists():
                continue
            for feature_dir in wt_specs.iterdir():
                if feature_dir.is_dir():
                    # Favor worktree copy (overwrites root entry if present)
                    feature_paths[feature_dir.name] = feature_dir

    return feature_paths


def run_diagnostics(project_dir: Path) -> Dict[str, Any]:
    """Run comprehensive diagnostics on the project setup."""
    import subprocess

    diagnostics = {
        'project_path': str(project_dir),
        'current_working_directory': str(Path.cwd()),
        'git_branch': None,
        'in_worktree': False,
        'worktrees_exist': False,
        'features': [],
        'recommendations': [],
        'issues': []
    }

    # Check git branch
    try:
        result = subprocess.run(
            ['git', 'branch', '--show-current'],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=True
        )
        diagnostics['git_branch'] = result.stdout.strip()
    except subprocess.CalledProcessError:
        diagnostics['issues'].append('Could not detect git branch')

    # Check if current directory is in a worktree
    cwd_str = str(Path.cwd())
    diagnostics['in_worktree'] = '.worktrees' in cwd_str

    # Check if worktrees directory exists
    worktrees_dir = project_dir / '.worktrees'
    diagnostics['worktrees_exist'] = worktrees_dir.exists()

    # Analyze each feature
    all_features = set()

    # Collect features from root
    root_specs = project_dir / 'kitty-specs'
    if root_specs.exists():
        for feature_dir in root_specs.iterdir():
            if feature_dir.is_dir() and re.match(r'^\d{3}-', feature_dir.name):
                all_features.add(feature_dir.name)

    # Collect features from worktrees
    if worktrees_dir.exists():
        for worktree_dir in worktrees_dir.iterdir():
            if worktree_dir.is_dir():
                all_features.add(worktree_dir.name)

    # Analyze each feature
    for feature_name in sorted(all_features):
        feature_info = {
            'name': feature_name,
            'worktree_exists': False,
            'worktree_path': str(worktrees_dir / feature_name),
            'root_artifacts': [],
            'worktree_artifacts': [],
            'dashboard_expects': None,
            'cli_will_create': None,
            'location_mismatch': False,
            'recommendations': []
        }

        # Check worktree existence
        worktree_path = worktrees_dir / feature_name
        feature_info['worktree_exists'] = worktree_path.exists()

        # Check root artifacts
        root_feature_dir = root_specs / feature_name
        if root_feature_dir.exists():
            for artifact_file in ['spec.md', 'plan.md', 'tasks.md', 'research.md', 'data-model.md']:
                if (root_feature_dir / artifact_file).exists():
                    feature_info['root_artifacts'].append(artifact_file)

        # Check worktree artifacts
        worktree_feature_dir = worktree_path / 'kitty-specs' / feature_name
        if worktree_feature_dir.exists():
            for artifact_file in ['spec.md', 'plan.md', 'tasks.md', 'research.md', 'data-model.md']:
                if (worktree_feature_dir / artifact_file).exists():
                    feature_info['worktree_artifacts'].append(artifact_file)

        # Determine where dashboard expects artifacts
        if feature_info['worktree_exists']:
            feature_info['dashboard_expects'] = str(worktree_feature_dir)
        else:
            feature_info['dashboard_expects'] = str(root_feature_dir)

        # Determine where CLI will create artifacts (simplified logic)
        if diagnostics['in_worktree'] and feature_name in cwd_str:
            feature_info['cli_will_create'] = str(worktree_feature_dir)
        elif feature_info['worktree_exists']:
            feature_info['cli_will_create'] = str(worktree_feature_dir)
        else:
            feature_info['cli_will_create'] = str(root_feature_dir)

        # Check for location mismatch
        feature_info['location_mismatch'] = feature_info['cli_will_create'] != feature_info['dashboard_expects']

        # Generate recommendations
        if feature_info['location_mismatch']:
            feature_info['recommendations'].append(f"Location mismatch! Run commands from {worktree_path}")

        if feature_info['worktree_exists'] and not diagnostics['in_worktree']:
            feature_info['recommendations'].append(f"Navigate to worktree: cd {worktree_path}")

        if not feature_info['worktree_exists']:
            feature_info['recommendations'].append(f"Create worktree: git worktree add .worktrees/{feature_name} {feature_name}")

        # Check for orphaned artifacts
        if feature_info['root_artifacts'] and feature_info['worktree_artifacts']:
            feature_info['recommendations'].append("Artifacts exist in both locations - consider consolidating")

        diagnostics['features'].append(feature_info)

    # Generate overall recommendations
    if diagnostics['git_branch'] == 'main':
        diagnostics['issues'].append('On main branch - commands will fail!')
        diagnostics['recommendations'].append('Navigate to a feature worktree')

    if not diagnostics['worktrees_exist']:
        diagnostics['recommendations'].append('No worktrees found - create with: spec-kitty specify')

    if not diagnostics['in_worktree'] and diagnostics['worktrees_exist']:
        diagnostics['recommendations'].append('You are not in a worktree - navigate to .worktrees/<feature>')

    return diagnostics


def resolve_feature_dir(project_dir: Path, feature_id: str) -> Optional[Path]:
    """Resolve the on-disk directory for the requested feature."""
    feature_paths = gather_feature_paths(project_dir)
    feature_dir = feature_paths.get(feature_id)
    return feature_dir


def scan_all_features(project_dir: Path) -> List[Dict[str, Any]]:
    """Scan all features and return metadata."""
    features = []
    feature_paths = gather_feature_paths(project_dir)

    for feature_id, feature_dir in feature_paths.items():
        # Only process numbered features or those with tasks
        if not (re.match(r'^\d+', feature_dir.name) or (feature_dir / 'tasks').exists()):
            continue

        friendly_name = feature_dir.name
        meta_data: Dict[str, Any] | None = None
        meta_path = feature_dir / 'meta.json'
        if meta_path.exists():
            try:
                meta_data = json.loads(meta_path.read_text(encoding="utf-8"))
                potential_name = meta_data.get("friendly_name")
                if isinstance(potential_name, str) and potential_name.strip():
                    friendly_name = potential_name.strip()
            except json.JSONDecodeError:
                meta_data = None

        # Get artifacts
        artifacts = get_feature_artifacts(feature_dir)

        # Get workflow status
        workflow = get_workflow_status(artifacts)

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

        worktree_root = project_dir / '.worktrees'
        worktree_path = worktree_root / feature_dir.name
        worktree_exists = worktree_path.exists()

        features.append({
            'id': feature_id,
            'name': friendly_name,
            'path': str(feature_dir.relative_to(project_dir)),
            'artifacts': artifacts,
            'workflow': workflow,
            'kanban_stats': kanban_stats,
            'meta': meta_data or {},
            'worktree': {
                'path': format_path_for_display(str(worktree_path)),
                'exists': worktree_exists
            }
        })

    # Sort by feature id (ensures newest e.g., 010-... first)
    features.sort(key=lambda f: f['id'], reverse=True)

    return features


def scan_feature_kanban(project_dir: Path, feature_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """Scan kanban board for a specific feature."""
    feature_dir = resolve_feature_dir(project_dir, feature_id)
    lanes = {'planned': [], 'doing': [], 'for_review': [], 'done': []}

    if feature_dir is None or not feature_dir.exists():
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

                # Extract prompt markdown without frontmatter so we can show it in the UI
                prompt_body = content
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        prompt_body = parts[2].strip()

                task_data = {
                    'id': fm.get('work_package_id', prompt_file.stem),
                    'title': title,
                    'lane': fm.get('lane', lane),
                    'subtasks': fm.get('subtasks', []),
                    'agent': fm.get('agent', ''),
                    'assignee': fm.get('assignee', ''),
                    'phase': fm.get('phase', ''),
                    'prompt_markdown': prompt_body,
                    'prompt_path': str(prompt_file.relative_to(project_dir)) if prompt_file.is_relative_to(project_dir) else str(prompt_file),
                }

                lanes[lane].append(task_data)
            except Exception as e:
                continue

        lanes[lane].sort(key=work_package_sort_key)

    return lanes


def get_dashboard_html() -> str:
    """Generate the dashboard HTML with sidebar and dropdown."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Spec Kitty Dashboard</title>
    <link rel="icon" type="image/png" href="/static/spec-kitty.png">
    <script src="https://cdn.jsdelivr.net/npm/marked@11.1.1/marked.min.js"></script>
    <link rel="stylesheet" href="/static/dashboard/dashboard.css">
    <!-- OLD INLINE CSS BELOW - KEPT FOR REFERENCE, NOT LOADED -->
    <style type="text/template" id="old-inline-css" style="display: none;">
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

        .header-logo-wrapper {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 60px;
            height: 60px;
            background: white;
            border-radius: 14px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.12);
            border: 2px solid rgba(123, 182, 97, 0.25);
            overflow: hidden;
        }

        .header-logo {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }

        .header h1 {
            font-size: 1.8em;
            color: var(--grassy-green);
            margin: 0;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
        }

        .header-info {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .tree-view {
            font-size: 0.75em;
            color: var(--medium-text);
            font-family: 'Monaco', 'Menlo', monospace;
            background: rgba(0,0,0,0.05);
            padding: 6px 10px;
            border-radius: 6px;
            white-space: pre;
            line-height: 1.4;
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

        .sidebar-last-update {
            margin: 6px 30px 20px;
            display: block;
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
            background: #ffffff;
            color: #111827;
            padding: 16px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 16px 0;
        }

        .markdown-content pre code {
            background: transparent;
            color: inherit;
            padding: 0;
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

        .merge-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            border-radius: 999px;
            font-size: 0.85em;
            font-weight: 600;
            color: #065f46;
            background: #d1fae5;
            border: 1px solid #34d399;
            margin-left: 12px;
            white-space: nowrap;
        }

        .merge-badge .icon {
            font-size: 1em;
        }

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

        body.modal-open {
            overflow: hidden;
        }

        .modal {
            position: fixed;
            inset: 0;
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }

        .modal.show {
            display: flex;
        }

        .modal.hidden {
            display: none;
        }

        .modal-overlay {
            position: absolute;
            inset: 0;
            background: rgba(17, 24, 39, 0.65);
            backdrop-filter: blur(2px);
        }

        .modal-content {
            position: relative;
            background: white;
            border-radius: 12px;
            padding: 24px;
            max-width: 900px;
            width: min(90%, 900px);
            max-height: 80vh;
            display: flex;
            flex-direction: column;
            gap: 16px;
            box-shadow: 0 20px 40px rgba(15, 23, 42, 0.35);
            overflow: hidden;
        }

        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 16px;
        }

        .modal-title {
            font-size: 1.35em;
            font-weight: 600;
            color: #1f2937;
        }

        .modal-subtitle {
            font-size: 0.9em;
            color: #6b7280;
            margin-top: 4px;
        }

        .modal-close {
            border: none;
            background: transparent;
            color: #6b7280;
            font-size: 1.2em;
            cursor: pointer;
            transition: color 0.2s ease;
        }

        .modal-close:hover,
        .modal-close:focus {
            color: #1f2937;
        }

        .modal-body {
            position: relative;
            overflow-y: auto;
            padding-right: 4px;
        }

        .modal-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 12px;
        }

        .modal-meta span {
            background: #f3f4f6;
            border-radius: 12px;
            padding: 4px 12px;
            font-size: 0.85em;
            color: #4b5563;
        }

        .modal-content .markdown-content {
            padding: 0;
        }

        .modal-content .markdown-content pre {
            background: #ffffff;
            color: #111827;
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
            <div class="header-logo-wrapper">
                <img src="/static/spec-kitty.png" alt="Spec Kitty logo" class="header-logo">
            </div>
            <div class="header-info">
                <h1>Spec Kitty</h1>
                <pre class="tree-view" id="tree-info">Loading…</pre>
            </div>
            <div class="feature-selector" id="feature-selector-container">
                <label>Feature:</label>
                <select id="feature-select" onchange="switchFeature(this.value)">
                    <option value="">Loading...</option>
                </select>
            </div>
            <div id="single-feature-name" style="display: none; font-size: 1.2em; color: var(--grassy-green); font-weight: 600;"></div>
        </div>
    </div>

    <div class="container">
        <div class="sidebar">
            <div class="sidebar-item" data-page="constitution" onclick="switchPage('constitution')">
                📜 Constitution
            </div>
            <div class="last-update sidebar-last-update">Last updated: <span id="last-update">Loading...</span></div>
            <div style="padding: 15px 30px; font-size: 0.75em; color: #9ca3af; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">
                Workflow
            </div>
            <div class="sidebar-item active" data-page="overview" data-step="overview" onclick="switchPage('overview')">
                <span id="icon-overview">📊</span> Overview
            </div>
            <div class="sidebar-item" data-page="spec" data-step="specify" onclick="switchPage('spec')">
                <span id="icon-specify">⏳</span> Specify
            </div>
            <div class="sidebar-item" data-page="plan" data-step="plan" onclick="switchPage('plan')">
                <span id="icon-plan">⏳</span> Plan
            </div>
            <div class="sidebar-item" data-page="tasks" data-step="tasks" onclick="switchPage('tasks')">
                <span id="icon-tasks">⏳</span> Tasks
            </div>
            <div class="sidebar-item" data-page="kanban" data-step="implement" onclick="switchPage('kanban')">
                <span id="icon-implement">⏳</span> Implement
            </div>
            <div style="padding: 15px 30px; margin-top: 20px; font-size: 0.75em; color: #9ca3af; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">
                Artifacts
            </div>
            <div class="sidebar-item" data-page="research" onclick="switchPage('research')">
                🔬 Research
            </div>
            <div class="sidebar-item" data-page="contracts" onclick="switchPage('contracts')">
                📜 Contracts
            </div>
            <div class="sidebar-item" data-page="quickstart" onclick="switchPage('quickstart')">
                🚀 Quickstart
            </div>
            <div class="sidebar-item" data-page="data-model" onclick="switchPage('data-model')">
                💾 Data Model
            </div>
            <div style="padding: 15px 30px; margin-top: 20px; font-size: 0.75em; color: #9ca3af; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">
                System
            </div>
            <div class="sidebar-item" data-page="diagnostics" onclick="switchPage('diagnostics')">
                🔍 Diagnostics
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

            <div id="page-contracts" class="page">
                <div class="content-card">
                    <h2>Contracts</h2>
                    <div id="contracts-content" class="markdown-content"></div>
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

            <div id="page-constitution" class="page">
                <div class="content-card">
                    <h2>📜 Project Constitution</h2>
                    <div id="constitution-content" class="markdown-content"></div>
                </div>
            </div>

            <div id="page-diagnostics" class="page">
                <div class="content-card">
                    <h2>🔍 Environment Diagnostics</h2>
                    <div id="diagnostics-loading" style="padding: 20px; text-align: center;">
                        <div style="font-size: 1.2em; color: var(--medium-text);">Loading diagnostics...</div>
                    </div>
                    <div id="diagnostics-content" style="display: none;">
                        <!-- Current Status -->
                        <div style="margin-bottom: 30px;">
                            <h3 style="color: var(--grassy-green); margin-bottom: 15px;">Current Status</h3>
                            <div id="diagnostics-status" style="background: var(--light-gray); padding: 15px; border-radius: 8px; font-family: monospace; font-size: 0.9em;"></div>
                        </div>

                        <!-- Issues & Recommendations -->
                        <div id="diagnostics-issues" style="margin-bottom: 30px; display: none;">
                            <h3 style="color: #ef4444; margin-bottom: 15px;">⚠️ Issues Detected</h3>
                            <div id="diagnostics-issues-content" style="background: #fef2f2; border-left: 4px solid #ef4444; padding: 15px; border-radius: 4px;"></div>
                        </div>

                        <div id="diagnostics-recommendations" style="margin-bottom: 30px; display: none;">
                            <h3 style="color: #f59e0b; margin-bottom: 15px;">💡 Recommendations</h3>
                            <div id="diagnostics-recommendations-content" style="background: #fffbeb; border-left: 4px solid #f59e0b; padding: 15px; border-radius: 4px;"></div>
                        </div>

                        <!-- Feature Analysis -->
                        <div style="margin-bottom: 30px;">
                            <h3 style="color: var(--grassy-green); margin-bottom: 15px;">Feature Analysis</h3>
                            <div id="diagnostics-features" style="display: flex; flex-direction: column; gap: 15px;"></div>
                        </div>

                        <!-- Actions -->
                        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid var(--light-gray);">
                            <button onclick="refreshDiagnostics()" style="background: var(--grassy-green); color: white; padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-size: 1em;">
                                🔄 Refresh Diagnostics
                            </button>
                        </div>
                    </div>
                    <div id="diagnostics-error" style="display: none; padding: 20px; background: #fef2f2; border-left: 4px solid #ef4444; border-radius: 4px;">
                        <strong>Error loading diagnostics:</strong> <span id="diagnostics-error-message"></span>
                    </div>
                </div>
            </div>

            <div id="page-welcome" class="page">
                <div class="content-card">
                    <h2>Welcome to Spec Kitty!</h2>
                    <div style="padding: 40px 20px; text-align: center;">
                        <p style="font-size: 1.2em; margin-bottom: 30px; color: var(--medium-text);">
                            Your project is initialized and the dashboard is ready.
                        </p>
                        <div style="background: var(--baby-blue); padding: 30px; border-radius: 12px; max-width: 600px; margin: 0 auto;">
                            <h3 style="color: var(--grassy-green); margin-bottom: 20px;">Get Started</h3>
                            <ol style="text-align: left; line-height: 2; color: var(--dark-text);">
                                <li>Run <code style="background: white; padding: 4px 8px; border-radius: 4px;">/spec-kitty.specify</code> to create your first feature</li>
                                <li>Then <code style="background: white; padding: 4px 8px; border-radius: 4px;">/spec-kitty.plan</code> to create the implementation plan</li>
                                <li>Then <code style="background: white; padding: 4px 8px; border-radius: 4px;">/spec-kitty.tasks</code> to generate the task breakdown</li>
                                <li>Watch the dashboard update in real-time as you work!</li>
                            </ol>
                        </div>
                    </div>
                </div>
            </div>

            <div id="no-features-message" class="no-features" style="display: none;">
                <h2>No Features Found</h2>
                <p>Create your first feature using <code>/spec-kitty.specify</code></p>
            </div>
        </div>
    </div>

    <div id="prompt-modal" class="modal hidden" aria-hidden="true">
        <div class="modal-overlay"></div>
        <div class="modal-content" role="dialog" aria-modal="true" aria-labelledby="modal-title">
            <div class="modal-header">
                <div>
                    <div class="modal-title" id="modal-title">Work Package Prompt</div>
                    <div class="modal-subtitle" id="modal-subtitle"></div>
                </div>
                <button type="button" class="modal-close" id="modal-close-btn" aria-label="Close prompt viewer">✕</button>
            </div>
            <div class="modal-body" id="modal-body">
                <div class="modal-meta" id="modal-prompt-meta"></div>
                <div id="modal-prompt-content" class="markdown-content"></div>
            </div>
        </div>
    </div>

    <script src="/static/dashboard/dashboard.js"></script>
    <!-- OLD INLINE CODE BELOW - KEPT FOR REFERENCE, NOT EXECUTED -->
    <script type="text/template" id="old-inline-js"  style="display: none;">
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
            treeElement.textContent = lines.join('\\n');
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
                if (!page || page === 'constitution') {
                    item.classList.remove('disabled');
                    return;
                }

                const hasArtifact = page === 'overview' || artifacts[page.replace('-', '_')];

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
                    const htmlContent = marked.parse(content);
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
                    // Try to render as markdown, fallback to plain text
                    let htmlContent;
                    if (filePath.endsWith('.md')) {
                        htmlContent = marked.parse(content);
                    } else if (filePath.endsWith('.csv')) {
                        // Render CSV as a table
                        htmlContent = renderCSV(content);
                    } else {
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
                // Simple CSV parsing (doesn't handle quoted commas)
                return line.split(',').map(cell => cell.trim());
            });

            const headerRow = rows[0];
            const dataRows = rows.slice(1);

            return `
                <div style="overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden;">
                        <thead>
                            <tr style="background: var(--baby-blue);">
                                ${headerRow.map(header => `<th style="padding: 12px; text-align: left; font-weight: 600; color: var(--dark-text);">${escapeHtml(header)}</th>`).join('')}
                            </tr>
                        </thead>
                        <tbody>
                            ${dataRows.map((row, idx) => `
                                <tr style="border-top: 1px solid var(--light-gray); ${idx % 2 === 0 ? 'background: #fafaf8;' : ''}">
                                    ${row.map(cell => `<td style="padding: 10px;">${escapeHtml(cell)}</td>`).join('')}
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
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

        function showDiagnostics() {
            // Switch to diagnostics page
            currentPage = 'diagnostics';
            isConstitutionView = false;
            document.querySelectorAll('.sidebar-item').forEach(item => item.classList.remove('active'));
            const diagnosticsItem = document.querySelector('.sidebar-item[data-page="diagnostics"]');
            if (diagnosticsItem) {
                diagnosticsItem.classList.remove('disabled');
                diagnosticsItem.classList.add('active');
            }
            document.querySelectorAll('.page').forEach(page => page.classList.remove('active'));
            document.getElementById('page-diagnostics').classList.add('active');

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

            // Display current status
            const statusHtml = `
                <div><strong>Project Path:</strong> ${data.project_path}</div>
                <div><strong>Current Directory:</strong> ${data.current_working_directory}</div>
                <div><strong>Git Branch:</strong> ${data.git_branch || 'Not detected'}</div>
                <div><strong>In Worktree:</strong> ${data.in_worktree ? '✅ Yes' : '❌ No'}</div>
                <div><strong>Worktrees Exist:</strong> ${data.worktrees_exist ? '✅ Yes' : '❌ No'}</div>
            `;
            document.getElementById('diagnostics-status').innerHTML = statusHtml;

            // Display issues
            if (data.issues && data.issues.length > 0) {
                document.getElementById('diagnostics-issues').style.display = 'block';
                const issuesHtml = data.issues.map(issue => `<div>• ${issue}</div>`).join('');
                document.getElementById('diagnostics-issues-content').innerHTML = issuesHtml;
            } else {
                document.getElementById('diagnostics-issues').style.display = 'none';
            }

            // Display recommendations
            if (data.recommendations && data.recommendations.length > 0) {
                document.getElementById('diagnostics-recommendations').style.display = 'block';
                const recsHtml = data.recommendations.map(rec => `<div>• ${rec}</div>`).join('');
                document.getElementById('diagnostics-recommendations-content').innerHTML = recsHtml;
            } else {
                document.getElementById('diagnostics-recommendations').style.display = 'none';
            }

            // Display feature analysis
            const featuresContainer = document.getElementById('diagnostics-features');
            if (data.features && data.features.length > 0) {
                const featuresHtml = data.features.map(feature => {
                    const statusColor = feature.location_mismatch ? '#ef4444' : '#10b981';
                    const statusText = feature.location_mismatch ? '❌ Location Mismatch' : '✅ Locations Match';

                    let artifactsInfo = '';
                    if (feature.root_artifacts.length > 0) {
                        artifactsInfo += `<div><strong>Root artifacts:</strong> ${feature.root_artifacts.join(', ')}</div>`;
                    }
                    if (feature.worktree_artifacts.length > 0) {
                        artifactsInfo += `<div><strong>Worktree artifacts:</strong> ${feature.worktree_artifacts.join(', ')}</div>`;
                    }

                    let recommendations = '';
                    if (feature.recommendations.length > 0) {
                        recommendations = '<div style="margin-top: 10px; padding: 10px; background: #fffbeb; border-radius: 4px;">' +
                            '<strong>Recommendations:</strong><br>' +
                            feature.recommendations.map(r => `• ${r}`).join('<br>') +
                            '</div>';
                    }

                    return `
                        <div style="background: white; border: 1px solid var(--light-gray); border-radius: 8px; padding: 15px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                <h4 style="margin: 0; color: var(--grassy-green);">${feature.name}</h4>
                                <span style="color: ${statusColor}; font-weight: bold;">${statusText}</span>
                            </div>
                            <div style="font-size: 0.9em; color: var(--medium-text);">
                                <div><strong>Worktree exists:</strong> ${feature.worktree_exists ? '✅ Yes' : '❌ No'}</div>
                                ${artifactsInfo}
                                <div style="margin-top: 8px; padding: 8px; background: var(--light-gray); border-radius: 4px; font-family: monospace; font-size: 0.85em;">
                                    <div><strong>Dashboard expects:</strong><br>${feature.dashboard_expects}</div>
                                    <div style="margin-top: 5px;"><strong>CLI will create:</strong><br>${feature.cli_will_create}</div>
                                </div>
                                ${recommendations}
                            </div>
                        </div>
                    `;
                }).join('');
                featuresContainer.innerHTML = featuresHtml;
            } else {
                featuresContainer.innerHTML = '<div style="text-align: center; color: var(--medium-text);">No features found</div>';
            }
        }

        function refreshDiagnostics() {
            loadDiagnostics();
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

                select.innerHTML = features.map(f =>
                    `<option value="${f.id}" ${f.id === currentFeature ? 'selected' : ''}>${f.name}</option>`
                ).join('');

                if (!currentFeature || !features.find(f => f.id === currentFeature)) {
                    currentFeature = features[0].id;
                    select.value = currentFeature;
                }
            }

            sidebar.style.display = 'block';
            mainContent.style.display = 'block';

            // Update workflow icons based on current feature
            const feature = features.find(f => f.id === currentFeature);
            if (feature && feature.workflow) {
                updateWorkflowIcons(feature.workflow);
                computeFeatureWorktreeStatus(feature);
            } else {
                computeFeatureWorktreeStatus(null);
            }

            updateSidebarState();
            if (!isConstitutionView) {
                loadCurrentPage();
            }
        }

        function fetchData() {
            if (featureSelectActive) {
                return;
            }
            fetch('/api/features')
                .then(response => response.json())
                .then(data => {
                    updateFeatureList(data.features);
                    document.getElementById('last-update').textContent = new Date().toLocaleTimeString();

                    if (data.project_path) {
                        projectPathDisplay = data.project_path;
                    }

                    if (data.active_worktree) {
                        activeWorktreeDisplay = data.active_worktree;
                    } else {
                        activeWorktreeDisplay = '';
                    }

                    const currentFeatureObj = allFeatures.find(f => f.id === currentFeature);
                    computeFeatureWorktreeStatus(currentFeatureObj || null);
                    updateTreeInfo();
                })
                .catch(error => console.error('Error fetching data:', error));
        }

        // Initial fetch
        updateTreeInfo();
        fetchData();

        // Poll every second
        setInterval(fetchData, 1000);
    </script>
</body>
</html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the dashboard."""

    project_dir = None
    project_token = None

    def log_message(self, format, *args):
        """Suppress request logging."""
        pass

    def _send_json(self, status_code: int, payload: Dict[str, Any]) -> None:
        """Return JSON response with standard headers."""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def _handle_shutdown(self) -> None:
        """Handle shutdown requests."""
        expected_token = getattr(self, 'project_token', None)

        token = None
        if self.command == 'POST':
            content_length = int(self.headers.get('Content-Length') or 0)
            body = self.rfile.read(content_length) if content_length else b''
            if body:
                try:
                    payload = json.loads(body.decode('utf-8'))
                    token = payload.get('token')
                except (UnicodeDecodeError, json.JSONDecodeError):
                    self._send_json(400, {'error': 'invalid_payload'})
                    return
        else:
            parsed_path = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed_path.query)
            token_values = params.get('token')
            if token_values:
                token = token_values[0]

        if expected_token and token != expected_token:
            self._send_json(403, {'error': 'invalid_token'})
            return

        self._send_json(200, {'status': 'stopping'})

        def shutdown_server(server):
            # Delay slightly to allow response to flush before shutdown
            time.sleep(0.05)
            server.shutdown()

        threading.Thread(target=shutdown_server, args=(self.server,), daemon=True).start()

    def do_POST(self):
        """Handle POST requests."""
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        if path == '/api/shutdown':
            self._handle_shutdown()
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        if path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(get_dashboard_html().encode())

        elif path == '/api/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()

            try:
                project_path = str(Path(self.project_dir).resolve())
            except Exception:
                project_path = str(self.project_dir)

            response_data = {
                'status': 'ok',
                'project_path': project_path,
            }

            token = getattr(self, 'project_token', None)
            if token:
                response_data['token'] = token

            self.wfile.write(json.dumps(response_data).encode())

        elif path == '/api/shutdown':
            self._handle_shutdown()

        elif path == '/api/features':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()

            project_path = Path(self.project_dir).resolve()
            features = scan_all_features(project_path)

            worktrees_root_path = project_path / '.worktrees'
            try:
                worktrees_root_resolved = worktrees_root_path.resolve()
            except Exception:
                worktrees_root_resolved = worktrees_root_path

            try:
                current_path = Path.cwd().resolve()
            except Exception:
                current_path = Path.cwd()

            worktrees_root_exists = worktrees_root_path.exists()
            worktrees_root_display = (
                format_path_for_display(str(worktrees_root_resolved))
                if worktrees_root_exists
                else None
            )

            active_worktree_display: Optional[str] = None
            if worktrees_root_exists:
                try:
                    current_path.relative_to(worktrees_root_resolved)
                    active_worktree_display = format_path_for_display(str(current_path))
                except ValueError:
                    active_worktree_display = None

            if not active_worktree_display and current_path != project_path:
                active_worktree_display = format_path_for_display(str(current_path))

            response_data = {
                'features': features,
                'project_path': format_path_for_display(str(project_path)),
                'worktrees_root': worktrees_root_display,
                'active_worktree': active_worktree_display,
            }
            self.wfile.write(json.dumps(response_data).encode())

        elif path.startswith('/api/kanban/'):
            feature_id = path.split('/')[-1]
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()

            lanes = scan_feature_kanban(Path(self.project_dir), feature_id)
            self.wfile.write(json.dumps(lanes).encode())

        elif path == '/api/constitution':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()

            constitution_file = Path(self.project_dir) / '.kittify' / 'memory' / 'constitution.md'
            if constitution_file.exists():
                try:
                    content = constitution_file.read_text(encoding='utf-8')
                    self.wfile.write(content.encode('utf-8'))
                except UnicodeDecodeError as e:
                    error_msg = f'⚠️ Encoding Error: File contains non-UTF-8 characters at position {e.start}. Please convert to UTF-8.\n\nAttempting to read with error recovery...\n\n'
                    try:
                        content = constitution_file.read_text(encoding='utf-8', errors='replace')
                        self.wfile.write(error_msg.encode('utf-8') + content.encode('utf-8'))
                    except Exception as fallback_err:
                        self.wfile.write(f'Error reading file: {fallback_err}'.encode('utf-8'))
                except Exception as e:
                    print(f"Error reading constitution: {e}")
                    self.wfile.write(f'Error reading constitution: {e}'.encode('utf-8'))
            else:
                self.wfile.write(b'Constitution not yet created. Run /spec-kitty.constitution to create it.')

        elif path.startswith('/api/contracts/'):
            parts = path.split('/')
            if len(parts) >= 4:
                feature_id = parts[3]
                project_path = Path(self.project_dir)
                feature_dir = resolve_feature_dir(project_path, feature_id)

                if len(parts) == 4:
                    # List all contract files
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Cache-Control', 'no-cache')
                    self.end_headers()

                    if feature_dir:
                        contracts_dir = feature_dir / 'contracts'
                        if contracts_dir.exists() and contracts_dir.is_dir():
                            files = []
                            for file_path in sorted(contracts_dir.iterdir()):
                                if file_path.is_file():
                                    icon = '📄'
                                    if file_path.suffix in ['.yml', '.yaml']:
                                        icon = '⚙️'
                                    elif file_path.suffix == '.json':
                                        icon = '📋'
                                    elif file_path.suffix == '.md':
                                        icon = '📝'
                                    files.append({
                                        'name': file_path.name,
                                        'icon': icon
                                    })
                            self.wfile.write(json.dumps({'files': files}).encode())
                        else:
                            self.wfile.write(json.dumps({'files': []}).encode())
                    else:
                        self.wfile.write(json.dumps({'files': []}).encode())

                elif len(parts) >= 5:
                    # Get specific contract file
                    file_name = parts[4]
                    if feature_dir:
                        contracts_dir = feature_dir / 'contracts'
                        contract_file = contracts_dir / file_name

                        # Security check: ensure file is within contracts directory
                        try:
                            contract_file = contract_file.resolve()
                            contract_file.relative_to(contracts_dir.resolve())

                            if contract_file.exists() and contract_file.is_file():
                                self.send_response(200)
                                self.send_header('Content-type', 'text/plain')
                                self.send_header('Cache-Control', 'no-cache')
                                self.end_headers()

                                try:
                                    content = contract_file.read_text(encoding='utf-8')
                                    self.wfile.write(content.encode('utf-8'))
                                except UnicodeDecodeError as e:
                                    error_msg = f'⚠️ Encoding Error in {file_name}\n\nThis file contains non-UTF-8 characters at position {e.start}.\nPlease convert the file to UTF-8 encoding.\n\nAttempting to read with error recovery...\n\n'
                                    print(f"Encoding error in {contract_file}: {e}")
                                    try:
                                        content = contract_file.read_text(encoding='utf-8', errors='replace')
                                        self.wfile.write(error_msg.encode('utf-8') + content.encode('utf-8'))
                                    except Exception as fallback_err:
                                        self.wfile.write(f'Error reading file: {fallback_err}'.encode('utf-8'))
                                except Exception as e:
                                    print(f"Error reading contract {file_name}: {e}")
                                    self.wfile.write(f'Error reading file: {e}'.encode('utf-8'))
                                return
                        except ValueError:
                            # Path traversal attempt
                            pass
                        except Exception as e:
                            print(f"Error accessing contract file: {e}")

                    self.send_response(404)
                    self.end_headers()
            else:
                self.send_response(404)
                self.end_headers()

        elif path.startswith('/api/research/'):
            parts = path.split('/')
            if len(parts) >= 4:
                feature_id = parts[3]
                project_path = Path(self.project_dir)
                feature_dir = resolve_feature_dir(project_path, feature_id)

                if len(parts) == 4:
                    # Get research.md and list all artifacts
                    response = {'main_file': None, 'artifacts': []}

                    try:
                        if feature_dir:
                            # Get research.md content
                            research_md = feature_dir / 'research.md'
                            if research_md.exists():
                                try:
                                    response['main_file'] = research_md.read_text(encoding='utf-8')
                                except UnicodeDecodeError as e:
                                    error_msg = f'⚠️ **Encoding Error in research.md**\n\nThis file contains non-UTF-8 characters at position {e.start}.\nPlease convert the file to UTF-8 encoding.\n\nAttempting to read with error recovery...\n\n---\n\n'
                                    print(f"Encoding error in {research_md}: {e}")
                                    try:
                                        content = research_md.read_text(encoding='utf-8', errors='replace')
                                        response['main_file'] = error_msg + content
                                    except Exception as fallback_err:
                                        response['main_file'] = f'Error reading research.md: {fallback_err}'

                            # List research artifacts
                            research_dir = feature_dir / 'research'
                            if research_dir.exists() and research_dir.is_dir():
                                for file_path in sorted(research_dir.rglob('*')):
                                    if file_path.is_file():
                                        relative_path = str(file_path.relative_to(feature_dir))
                                        icon = '📄'
                                        if file_path.suffix == '.csv':
                                            icon = '📊'
                                        elif file_path.suffix == '.md':
                                            icon = '📝'
                                        elif file_path.suffix in ['.xlsx', '.xls']:
                                            icon = '📈'
                                        elif file_path.suffix == '.json':
                                            icon = '📋'
                                        response['artifacts'].append({
                                            'name': file_path.name,
                                            'path': relative_path,
                                            'icon': icon
                                        })
                    except Exception as e:
                        # Log error but still return valid JSON
                        print(f"Error loading research artifacts: {e}")
                        import traceback
                        traceback.print_exc()

                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Cache-Control', 'no-cache')
                    self.end_headers()
                    self.wfile.write(json.dumps(response).encode())

                elif len(parts) >= 5:
                    # Get specific research artifact
                    file_path_encoded = parts[4]
                    file_path_str = urllib.parse.unquote(file_path_encoded)

                    if feature_dir:
                        artifact_file = feature_dir / file_path_str

                        # Security check: ensure file is within feature directory
                        try:
                            artifact_file = artifact_file.resolve()
                            artifact_file.relative_to(feature_dir.resolve())

                            if artifact_file.exists() and artifact_file.is_file():
                                self.send_response(200)
                                self.send_header('Content-type', 'text/plain')
                                self.send_header('Cache-Control', 'no-cache')
                                self.end_headers()

                                try:
                                    content = artifact_file.read_text(encoding='utf-8')
                                    self.wfile.write(content.encode('utf-8'))
                                except UnicodeDecodeError as e:
                                    error_msg = f'⚠️ Encoding Error in {artifact_file.name}\n\nThis file contains non-UTF-8 characters at position {e.start}.\nPlease convert the file to UTF-8 encoding.\n\nAttempting to read with error recovery...\n\n'
                                    print(f"Encoding error in {artifact_file}: {e}")
                                    try:
                                        content = artifact_file.read_text(encoding='utf-8', errors='replace')
                                        self.wfile.write(error_msg.encode('utf-8') + content.encode('utf-8'))
                                    except Exception as fallback_err:
                                        self.wfile.write(f'Error reading file: {fallback_err}'.encode('utf-8'))
                                except Exception as e:
                                    print(f"Error reading research artifact {file_path_str}: {e}")
                                    self.wfile.write(f'Error reading file: {e}'.encode('utf-8'))
                                return
                        except ValueError:
                            # Path traversal attempt
                            pass
                        except Exception as e:
                            print(f"Error accessing research artifact: {e}")

                    self.send_response(404)
                    self.end_headers()
            else:
                self.send_response(404)
                self.end_headers()

        elif path.startswith(STATIC_URL_PREFIX):
            relative_path = path[len(STATIC_URL_PREFIX):]
            static_root = STATIC_DIR
            try:
                safe_path = (STATIC_DIR / relative_path).resolve()
            except (RuntimeError, ValueError):
                safe_path = None

            if not relative_path or not safe_path:
                self.send_response(404)
                self.end_headers()
                return

            try:
                safe_path.relative_to(static_root)
            except ValueError:
                self.send_response(404)
                self.end_headers()
                return

            if not safe_path.is_file():
                self.send_response(404)
                self.end_headers()
                return

            mime_type, _ = mimetypes.guess_type(safe_path.name)
            self.send_response(200)
            self.send_header('Content-type', mime_type or 'application/octet-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            with safe_path.open('rb') as static_file:
                self.wfile.write(static_file.read())
            return

        elif path.startswith('/api/artifact/'):
            parts = path.split('/')
            if len(parts) >= 4:
                feature_id = parts[3]
                artifact_name = parts[4] if len(parts) > 4 else ''

                project_path = Path(self.project_dir)
                feature_dir = resolve_feature_dir(project_path, feature_id)

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
                if feature_dir and filename:
                    artifact_file = feature_dir / filename
                    if artifact_file.exists():
                        self.send_response(200)
                        self.send_header('Content-type', 'text/plain')
                        self.send_header('Cache-Control', 'no-cache')
                        self.end_headers()

                        try:
                            content = artifact_file.read_text(encoding='utf-8')
                            self.wfile.write(content.encode('utf-8'))
                        except UnicodeDecodeError as e:
                            error_msg = f'⚠️ **Encoding Error in {filename}**\n\nThis file contains non-UTF-8 characters at position {e.start}.\nPlease convert the file to UTF-8 encoding.\n\nAttempting to read with error recovery...\n\n---\n\n'
                            print(f"Encoding error in {artifact_file}: {e}")
                            import traceback
                            traceback.print_exc()
                            try:
                                content = artifact_file.read_text(encoding='utf-8', errors='replace')
                                self.wfile.write(error_msg.encode('utf-8') + content.encode('utf-8'))
                            except Exception as fallback_err:
                                self.wfile.write(f'Error reading file: {fallback_err}'.encode('utf-8'))
                        except Exception as e:
                            print(f"Error reading artifact {artifact_name}: {e}")
                            import traceback
                            traceback.print_exc()
                            self.wfile.write(f'Error reading {filename}: {e}'.encode('utf-8'))
                        return

            self.send_response(404)
            self.end_headers()

        elif path == '/api/diagnostics':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()

            diagnostics = run_diagnostics(Path(self.project_dir))
            self.wfile.write(json.dumps(diagnostics).encode())

        else:
            self.send_response(404)
            self.end_headers()


def start_dashboard(project_dir: Path, port: int = None, background_process: bool = False, project_token: Optional[str] = None) -> tuple[int, Optional[threading.Thread]]:
    """
    Start the dashboard server.

    Args:
        project_dir: Project directory to serve
        port: Port to use (None = auto-find)
        background_process: If True, fork a detached background process that survives parent exit
        project_token: Optional token identifying the project instance

    Returns:
        Tuple of (port, thread)
    """
    if port is None:
        port = find_free_port()

    # Resolve to absolute path
    project_dir_abs = project_dir.resolve()

    if background_process:
        # Fork a detached background process that survives parent exit
        import subprocess
        import sys

        # Write a small Python script to run the server
        script = f"""
import sys
sys.path.insert(0, {repr(str(Path(__file__).parent))})
from dashboard import DashboardHandler, HTTPServer

handler_class = type(
    'DashboardHandler',
    (DashboardHandler,),
    {{
        'project_dir': {repr(str(project_dir_abs))},
        'project_token': {repr(project_token)}
    }}
)

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
            'project_dir': str(project_dir_abs),
            'project_token': project_token,
        })

        server = HTTPServer(('127.0.0.1', port), handler_class)

        def serve():
            server.serve_forever()

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()

        return port, thread


def _parse_dashboard_file(dashboard_file: Path) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    """Read dashboard metadata from disk."""
    try:
        content = dashboard_file.read_text(encoding='utf-8')
    except Exception:
        return None, None, None

    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        return None, None, None

    url = lines[0] if lines else None
    port = None
    token = None

    if len(lines) >= 2:
        try:
            port = int(lines[1])
        except ValueError:
            port = None

    if len(lines) >= 3:
        token = lines[2] or None

    return url, port, token


def _write_dashboard_file(dashboard_file: Path, url: str, port: int, token: Optional[str]) -> None:
    """Persist dashboard metadata to disk."""
    dashboard_file.parent.mkdir(parents=True, exist_ok=True)
    lines = [url, str(port)]
    if token:
        lines.append(token)
    dashboard_file.write_text("\n".join(lines) + "\n", encoding='utf-8')


def _check_dashboard_health(port: int, project_dir: Path, expected_token: Optional[str], timeout: float = 0.5) -> bool:
    """Verify that the dashboard on the port belongs to the provided project."""
    health_url = f"http://127.0.0.1:{port}/api/health"
    try:
        with urllib.request.urlopen(health_url, timeout=timeout) as response:
            if response.status != 200:
                return False
            payload = response.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ConnectionError, socket.error):
        return False
    except Exception:
        return False

    try:
        data = json.loads(payload.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False

    remote_path = data.get('project_path')
    if not remote_path:
        return False

    try:
        remote_resolved = str(Path(remote_path).resolve())
    except Exception:
        remote_resolved = str(remote_path)

    try:
        expected_path = str(project_dir.resolve())
    except Exception:
        expected_path = str(project_dir)

    if remote_resolved != expected_path:
        return False

    remote_token = data.get('token')
    if expected_token:
        return remote_token == expected_token

    return True


def ensure_dashboard_running(project_dir: Path, preferred_port: Optional[int] = None, background_process: bool = True) -> Tuple[str, int, bool]:
    """
    Ensure a dashboard server is running for the provided project directory.

    Returns:
        Tuple of (url, port, started) where started is True when a new server was launched.
    """
    project_dir_resolved = project_dir.resolve()
    dashboard_file = project_dir_resolved / '.kittify' / '.dashboard'

    existing_url = None
    existing_port = None
    existing_token = None

    if dashboard_file.exists():
        existing_url, existing_port, existing_token = _parse_dashboard_file(dashboard_file)
        if existing_port is not None and _check_dashboard_health(existing_port, project_dir_resolved, existing_token):
            url = existing_url or f"http://127.0.0.1:{existing_port}"
            return url, existing_port, False

    if preferred_port is not None:
        try:
            port_to_use = find_free_port(preferred_port, max_attempts=1)
        except RuntimeError:
            port_to_use = None
    else:
        port_to_use = None

    token = secrets.token_hex(16)
    port, _ = start_dashboard(project_dir_resolved, port=port_to_use, background_process=background_process, project_token=token)
    url = f"http://127.0.0.1:{port}"

    for _ in range(40):
        if _check_dashboard_health(port, project_dir_resolved, token):
            _write_dashboard_file(dashboard_file, url, port, token)
            return url, port, True
        time.sleep(0.25)

    raise RuntimeError(f"Dashboard failed to start on port {port} for project {project_dir_resolved}")


def stop_dashboard(project_dir: Path, timeout: float = 5.0) -> Tuple[bool, str]:
    """
    Attempt to stop the dashboard server for the provided project directory.

    Returns:
        Tuple[bool, str]: (stopped, message)
    """
    project_dir_resolved = project_dir.resolve()
    dashboard_file = project_dir_resolved / '.kittify' / '.dashboard'

    if not dashboard_file.exists():
        return False, "No dashboard metadata found."

    url, port, token = _parse_dashboard_file(dashboard_file)
    if port is None:
        dashboard_file.unlink(missing_ok=True)
        return False, "Dashboard metadata was invalid and has been cleared."

    if not _check_dashboard_health(port, project_dir_resolved, token):
        dashboard_file.unlink(missing_ok=True)
        return False, "Dashboard was already stopped. Metadata has been cleared."

    shutdown_url = f"http://127.0.0.1:{port}/api/shutdown"

    def _attempt_get() -> Tuple[bool, Optional[str]]:
        params = {}
        if token:
            params['token'] = token
        query = urllib.parse.urlencode(params)
        url = f"{shutdown_url}?{query}" if query else shutdown_url
        try:
            urllib.request.urlopen(url, timeout=1)
            return True, None
        except urllib.error.HTTPError as exc:
            if exc.code == 403:
                return False, "Dashboard refused shutdown (token mismatch)."
            if exc.code in (404, 405, 501):
                return False, None  # Try POST fallback
            return False, f"Dashboard shutdown failed with HTTP {exc.code}."
        except (urllib.error.URLError, TimeoutError, ConnectionError, socket.error) as exc:
            return False, f"Dashboard shutdown request failed: {exc}"
        except Exception as exc:
            return False, f"Unexpected error during shutdown: {exc}"

    def _attempt_post() -> Tuple[bool, Optional[str]]:
        payload = json.dumps({'token': token}).encode('utf-8')
        request = urllib.request.Request(
            shutdown_url,
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        try:
            urllib.request.urlopen(request, timeout=1)
            return True, None
        except urllib.error.HTTPError as exc:
            if exc.code == 403:
                return False, "Dashboard refused shutdown (token mismatch)."
            if exc.code == 501:
                return False, "Dashboard does not support remote shutdown (upgrade required)."
            return False, f"Dashboard shutdown failed with HTTP {exc.code}."
        except (urllib.error.URLError, TimeoutError, ConnectionError, socket.error) as exc:
            return False, f"Dashboard shutdown request failed: {exc}"
        except Exception as exc:
            return False, f"Unexpected error during shutdown: {exc}"

    ok, error_message = _attempt_get()
    if not ok and error_message is None:
        ok, error_message = _attempt_post()
    if not ok:
        return False, error_message or "Dashboard shutdown failed."

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _check_dashboard_health(port, project_dir_resolved, token):
            dashboard_file.unlink(missing_ok=True)
            return True, f"Dashboard stopped and metadata cleared (port {port})."
        time.sleep(0.1)

    return False, f"Dashboard did not stop within {timeout} seconds."
