"""Feature-centric dashboard handlers."""

from __future__ import annotations

import json
import urllib.parse
from pathlib import Path
from typing import Optional

from ..scanner import (
    format_path_for_display,
    resolve_feature_dir,
    scan_all_features,
    scan_feature_kanban,
)
from .base import DashboardHandler
from specify_cli.mission import MissionError, get_active_mission

__all__ = ["FeatureHandler"]


class FeatureHandler(DashboardHandler):
    """Serve feature lists, kanban lanes, and artifact viewers."""

    def handle_features_list(self) -> None:
        """Return summary data for all features."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()

        project_path = Path(self.project_dir).resolve()
        features = scan_all_features(project_path)

        mission_context = {
            'name': 'Unknown mission',
            'domain': 'unknown',
            'version': '',
            'slug': '',
            'description': '',
            'path': '',
        }
        try:
            mission = get_active_mission(project_path)
            mission_context = {
                'name': mission.name,
                'domain': mission.domain,
                'version': mission.version,
                'slug': mission.path.name,
                'description': mission.description or '',
                'path': format_path_for_display(str(mission.path)),
            }
        except MissionError:
            pass

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

        response = {
            'features': features,
            'project_path': format_path_for_display(str(project_path)),
            'worktrees_root': worktrees_root_display,
            'active_worktree': active_worktree_display,
            'active_mission': mission_context,
        }
        self.wfile.write(json.dumps(response).encode())

    def handle_kanban(self, path: str) -> None:
        """Return kanban data for a specific feature slug."""
        parts = path.split('/')
        if len(parts) >= 4:
            feature_id = parts[3]
            project_path = Path(self.project_dir).resolve()
            kanban_data = scan_feature_kanban(project_path, feature_id)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(json.dumps(kanban_data).encode())
            return

        self.send_response(404)
        self.end_headers()

    def handle_research(self, path: str) -> None:
        """Return research.md contents + artifacts, or serve a specific file."""
        parts = path.split('/')
        if len(parts) < 4:
            self.send_response(404)
            self.end_headers()
            return

        feature_id = parts[3]
        project_path = Path(self.project_dir)
        feature_dir = resolve_feature_dir(project_path, feature_id)

        if len(parts) == 4:
            response = {'main_file': None, 'artifacts': []}

            if feature_dir:
                research_md = feature_dir / 'research.md'
                if research_md.exists():
                    try:
                        response['main_file'] = research_md.read_text(encoding='utf-8')
                    except UnicodeDecodeError as err:
                        error_msg = (
                            f'⚠️ **Encoding Error in research.md**\\n\\n'
                            f'This file contains non-UTF-8 characters at position {err.start}.\\n'
                            'Please convert the file to UTF-8 encoding.\\n\\n'
                            'Attempting to read with error recovery...\\n\\n---\\n\\n'
                        )
                        response['main_file'] = error_msg + research_md.read_text(
                            encoding='utf-8', errors='replace'
                        )

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
                                'icon': icon,
                            })

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            return

        if len(parts) >= 5 and feature_dir:
            file_path_encoded = parts[4]
            file_path_str = urllib.parse.unquote(file_path_encoded)
            artifact_file = (feature_dir / file_path_str).resolve()

            try:
                artifact_file.relative_to(feature_dir.resolve())
            except ValueError:
                self.send_response(404)
                self.end_headers()
                return

            if artifact_file.exists() and artifact_file.is_file():
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.send_header('Cache-Control', 'no-cache')
                self.end_headers()
                try:
                    content = artifact_file.read_text(encoding='utf-8')
                    self.wfile.write(content.encode('utf-8'))
                except UnicodeDecodeError as err:
                    error_msg = (
                        f'⚠️ Encoding Error in {artifact_file.name}\\n\\n'
                        f'This file contains non-UTF-8 characters at position {err.start}.\\n'
                        'Please convert the file to UTF-8 encoding.\\n\\n'
                        'Attempting to read with error recovery...\\n\\n'
                    )
                    content = artifact_file.read_text(encoding='utf-8', errors='replace')
                    self.wfile.write(error_msg.encode('utf-8') + content.encode('utf-8'))
                except Exception as exc:
                    self.wfile.write(f'Error reading file: {exc}'.encode('utf-8'))
                return

        self.send_response(404)
        self.end_headers()

    def handle_artifact(self, path: str) -> None:
        """Serve primary artifacts like spec.md and plan.md."""
        parts = path.split('/')
        if len(parts) < 4:
            self.send_response(404)
            self.end_headers()
            return

        feature_id = parts[3]
        artifact_name = parts[4] if len(parts) > 4 else ''

        project_path = Path(self.project_dir)
        feature_dir = resolve_feature_dir(project_path, feature_id)

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
                except UnicodeDecodeError as err:
                    error_msg = (
                        f'⚠️ **Encoding Error in {filename}**\\n\\n'
                        f'This file contains non-UTF-8 characters at position {err.start}.\\n'
                        'Please convert the file to UTF-8 encoding.\\n\\n'
                        'Attempting to read with error recovery...\\n\\n---\\n\\n'
                    )
                    content = artifact_file.read_text(encoding='utf-8', errors='replace')
                    self.wfile.write(error_msg.encode('utf-8') + content.encode('utf-8'))
                except Exception as exc:
                    self.wfile.write(f'Error reading {filename}: {exc}'.encode('utf-8'))
                return

        self.send_response(404)
        self.end_headers()
