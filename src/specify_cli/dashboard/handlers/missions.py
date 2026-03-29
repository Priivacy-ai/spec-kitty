"""Mission-centric dashboard handlers."""

from __future__ import annotations

import json
import urllib.parse
from pathlib import Path

from ..scanner import (
    format_path_for_display,
    resolve_active_mission,
    resolve_mission_dir,
    scan_all_missions,
    scan_mission_kanban,
)
from .base import DashboardHandler
from specify_cli.legacy_detector import is_legacy_format
from specify_cli.mission import MissionError, get_mission_by_name

__all__ = ["MissionHandler"]


class MissionHandler(DashboardHandler):
    """Serve mission lists, kanban lanes, and artifact viewers."""

    def handle_missions_list(self) -> None:
        """Return summary data for all missions."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()

        project_path = Path(self.project_dir).resolve()
        missions = scan_all_missions(project_path)

        # Add legacy format indicator to each mission
        for mission_entry in missions:
            mission_dir = project_path / mission_entry['path']
            mission_entry['is_legacy'] = is_legacy_format(mission_dir)

        # Derive active mission from the same active-mission resolver used by CLI status.
        mission_context = {
            'name': 'No active mission',
            'domain': 'unknown',
            'version': '',
            'slug': '',
            'description': '',
            'path': '',
        }

        active_mission_entry = resolve_active_mission(project_path, missions)

        if active_mission_entry:
            mission_type_key = active_mission_entry.get('meta', {}).get('mission', 'software-dev')
            try:
                kittify_dir = project_path / ".kittify"
                mission = get_mission_by_name(mission_type_key, kittify_dir)
                mission_context = {
                    'name': mission.name,
                    'domain': mission.config.domain,
                    'version': mission.config.version,
                    'slug': mission.path.name,
                    'description': mission.config.description or '',
                    'path': format_path_for_display(str(mission.path)),
                    'mission_name': active_mission_entry.get('name', ''),
                }
            except MissionError:
                # Fallback: show mission name with unknown mission type
                mission_context = {
                    'name': f"Unknown ({mission_type_key})",
                    'domain': 'unknown',
                    'version': '',
                    'slug': mission_type_key,
                    'description': '',
                    'path': '',
                    'mission_name': active_mission_entry.get('name', ''),
                }

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

        active_worktree_display: str | None = None
        if worktrees_root_exists:
            try:
                current_path.relative_to(worktrees_root_resolved)
                active_worktree_display = format_path_for_display(str(current_path))
            except ValueError:
                active_worktree_display = None

        if not active_worktree_display and current_path != project_path:
            active_worktree_display = format_path_for_display(str(current_path))

        response = {
            'missions': missions,
            'active_mission_id': active_mission_entry.get('id') if active_mission_entry else None,
            'project_path': format_path_for_display(str(project_path)),
            'worktrees_root': worktrees_root_display,
            'active_worktree': active_worktree_display,
            'active_mission': mission_context,
        }
        self.wfile.write(json.dumps(response).encode())

    def handle_kanban(self, path: str) -> None:
        """Return kanban data for a specific mission slug."""
        parts = path.split('/')
        if len(parts) >= 4:
            mission_id = parts[3]
            project_path = Path(self.project_dir).resolve()
            kanban_data = scan_mission_kanban(project_path, mission_id)

            # Check if mission uses legacy format
            mission_dir = resolve_mission_dir(project_path, mission_id)
            is_legacy = is_legacy_format(mission_dir) if mission_dir else False

            response = {
                'lanes': kanban_data,
                'is_legacy': is_legacy,
                'upgrade_needed': is_legacy,
            }

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
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

        mission_id = parts[3]
        project_path = Path(self.project_dir)
        mission_dir = resolve_mission_dir(project_path, mission_id)

        if len(parts) == 4:
            response = {'main_file': None, 'artifacts': []}

            if mission_dir:
                research_md = mission_dir / 'research.md'
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

                research_dir = mission_dir / 'research'
                if research_dir.exists() and research_dir.is_dir():
                    for file_path in sorted(research_dir.rglob('*')):
                        if file_path.is_file():
                            relative_path = str(file_path.relative_to(mission_dir))
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

        if len(parts) >= 5 and mission_dir:
            file_path_encoded = parts[4]
            file_path_str = urllib.parse.unquote(file_path_encoded)
            artifact_file = (mission_dir / file_path_str).resolve()

            try:
                artifact_file.relative_to(mission_dir.resolve())
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
                    self.wfile.write(f'Error reading file: {exc}'.encode())
                return

        self.send_response(404)
        self.end_headers()

    def _handle_artifact_directory(self, path: str, directory_name: str, md_icon: str = '📝') -> None:
        """Generic handler for artifact directories (contracts, checklists, etc).

        Args:
            path: The request path
            directory_name: Name of the subdirectory (e.g., 'contracts', 'checklists')
            md_icon: Icon to use for .md files (default: '📝')
        """
        parts = path.split('/')
        if len(parts) < 4:
            self.send_response(404)
            self.end_headers()
            return

        mission_id = parts[3]
        project_path = Path(self.project_dir)
        mission_dir = resolve_mission_dir(project_path, mission_id)

        if len(parts) == 4:
            # Return directory listing
            response = {'files': []}

            if mission_dir:
                artifact_dir = mission_dir / directory_name
                if artifact_dir.exists() and artifact_dir.is_dir():
                    for file_path in sorted(artifact_dir.rglob('*')):
                        if file_path.is_file():
                            relative_path = str(file_path.relative_to(mission_dir))
                            icon = '📄'
                            if file_path.suffix == '.md':
                                icon = md_icon
                            elif file_path.suffix == '.json':
                                icon = '📋'
                            response['files'].append({
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

        if len(parts) >= 5 and mission_dir:
            # Serve specific file
            file_path_encoded = parts[4]
            file_path_str = urllib.parse.unquote(file_path_encoded)
            artifact_file = (mission_dir / file_path_str).resolve()

            try:
                artifact_file.relative_to(mission_dir.resolve())
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
                    self.wfile.write(f'Error reading file: {exc}'.encode())
                return

        self.send_response(404)
        self.end_headers()

    def handle_contracts(self, path: str) -> None:
        """Return contracts directory listing or serve a specific file."""
        self._handle_artifact_directory(path, 'contracts', md_icon='📝')

    def handle_checklists(self, path: str) -> None:
        """Return checklists directory listing or serve a specific file."""
        self._handle_artifact_directory(path, 'checklists', md_icon='✅')

    def handle_artifact(self, path: str) -> None:
        """Serve primary artifacts like spec.md and plan.md."""
        parts = path.split('/')
        if len(parts) < 4:
            self.send_response(404)
            self.end_headers()
            return

        mission_id = parts[3]
        artifact_name = parts[4] if len(parts) > 4 else ''

        project_path = Path(self.project_dir)
        mission_dir = resolve_mission_dir(project_path, mission_id)

        artifact_map = {
            'spec': 'spec.md',
            'plan': 'plan.md',
            'tasks': 'tasks.md',
            'research': 'research.md',
            'quickstart': 'quickstart.md',
            'data-model': 'data-model.md',
        }

        filename = artifact_map.get(artifact_name)
        if mission_dir and filename:
            artifact_file = mission_dir / filename
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
                    self.wfile.write(f'Error reading {filename}: {exc}'.encode())
                return

        self.send_response(404)
        self.end_headers()
