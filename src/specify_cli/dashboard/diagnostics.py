"""Project diagnostics helpers for the dashboard."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

__all__ = ["run_diagnostics"]


def _ensure_specify_cli_on_path() -> None:
    """Ensure the repository root (src directory) is on sys.path for fallback imports."""
    candidate = Path(__file__).resolve().parents[2]  # .../src
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))


def run_diagnostics(project_dir: Path) -> Dict[str, Any]:
    """Run comprehensive diagnostics on the project setup using enhanced verification."""
    try:
        from ..manifest import FileManifest, WorktreeStatus  # type: ignore
        from ..acceptance import detect_feature_slug, AcceptanceError
    except (ImportError, ValueError):
        try:
            from specify_cli.manifest import FileManifest, WorktreeStatus  # type: ignore
            from specify_cli.acceptance import detect_feature_slug, AcceptanceError
        except ImportError:
            _ensure_specify_cli_on_path()
            from specify_cli.manifest import FileManifest, WorktreeStatus  # type: ignore
            from specify_cli.acceptance import detect_feature_slug, AcceptanceError

    kittify_dir = project_dir / ".kittify"
    repo_root = project_dir

    diagnostics: Dict[str, Any] = {
        'project_path': str(project_dir),
        'current_working_directory': str(Path.cwd()),
        'git_branch': None,
        'in_worktree': False,
        'worktrees_exist': False,
        'active_mission': None,
        'file_integrity': {},
        'worktree_overview': {},
        'current_feature': {},
        'all_features': [],
        'dashboard_health': {},
        'observations': [],
        'issues': [],
    }

    manifest = FileManifest(kittify_dir)
    worktree_status = WorktreeStatus(repo_root)

    try:
        result = subprocess.run(
            ['git', 'branch', '--show-current'],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        diagnostics['git_branch'] = result.stdout.strip()
    except subprocess.CalledProcessError:
        diagnostics['issues'].append('Could not detect git branch')

    diagnostics['in_worktree'] = '.worktrees' in str(Path.cwd())
    worktrees_dir = project_dir / '.worktrees'
    diagnostics['worktrees_exist'] = worktrees_dir.exists()
    diagnostics['active_mission'] = manifest.active_mission

    file_check = manifest.check_files()
    expected_files = manifest.get_expected_files()

    total_expected = sum(len(files) for files in expected_files.values())
    total_present = len(file_check["present"])
    total_missing = len(file_check["missing"])

    diagnostics['file_integrity'] = {
        "total_expected": total_expected,
        "total_present": total_present,
        "total_missing": total_missing,
        "missing_files": list(file_check["missing"].keys()) if file_check["missing"] else [],
    }

    worktree_summary = worktree_status.get_worktree_summary()
    diagnostics['worktree_overview'] = worktree_summary

    diagnostics['all_features'] = []
    for feature_slug in worktree_status.get_all_features():
        feature_status = worktree_status.get_feature_status(feature_slug)
        diagnostics['all_features'].append({
            'name': feature_slug,
            'state': feature_status['state'],
            'branch_exists': feature_status['branch_exists'],
            'branch_merged': feature_status['branch_merged'],
            'worktree_exists': feature_status['worktree_exists'],
            'worktree_path': feature_status['worktree_path'],
            'artifacts_in_main': feature_status['artifacts_in_main'],
            'artifacts_in_worktree': feature_status['artifacts_in_worktree'],
        })

    try:
        feature_slug = detect_feature_slug(repo_root, cwd=Path.cwd())
        if feature_slug:
            feature_status = worktree_status.get_feature_status(feature_slug.strip())
            diagnostics['current_feature'] = {
                'detected': True,
                'name': feature_slug.strip(),
                'state': feature_status['state'],
                'branch_exists': feature_status['branch_exists'],
                'branch_merged': feature_status['branch_merged'],
                'worktree_exists': feature_status['worktree_exists'],
                'worktree_path': feature_status['worktree_path'],
                'artifacts_in_main': feature_status['artifacts_in_main'],
                'artifacts_in_worktree': feature_status['artifacts_in_worktree'],
            }
    except (AcceptanceError, Exception) as exc:  # type: ignore[misc]
        diagnostics['current_feature'] = {
            'detected': False,
            'error': str(exc),
        }

    observations = []

    if diagnostics['git_branch'] == 'main' and diagnostics['in_worktree']:
        observations.append("Unusual: In worktree but on main branch")

    current_feature = diagnostics.get('current_feature') or {}
    if current_feature.get('detected') and current_feature.get('state') == 'in_development':
        if not current_feature.get('worktree_exists'):
            observations.append(
                f"Feature {current_feature.get('name')} has no worktree but has development artifacts"
            )

    if total_missing > 0:
        observations.append(f"Mission integrity: {total_missing} expected files not found")

    if worktree_summary.get('active_worktrees', 0) > 5:
        observations.append(f"Multiple worktrees active: {worktree_summary['active_worktrees']}")

    # Check dashboard health
    dashboard_file = kittify_dir / '.dashboard'
    dashboard_health = {
        'metadata_exists': dashboard_file.exists(),
        'can_start': None,
        'startup_test': None,
    }

    if dashboard_file.exists():
        try:
            from ..dashboard.lifecycle import _parse_dashboard_file, _check_dashboard_health
            url, port, token, pid = _parse_dashboard_file(dashboard_file)
            dashboard_health['url'] = url
            dashboard_health['port'] = port
            dashboard_health['pid'] = pid
            dashboard_health['has_pid'] = pid is not None

            if port:
                is_healthy = _check_dashboard_health(port, project_dir, token)
                dashboard_health['responding'] = is_healthy
                if not is_healthy:
                    diagnostics['issues'].append(f'Dashboard metadata exists but not responding on port {port}')
                    if pid:
                        # Check if process is alive
                        try:
                            from ..dashboard.lifecycle import _is_process_alive
                            if _is_process_alive(pid):
                                diagnostics['issues'].append(f'Dashboard process (PID {pid}) is alive but not responding')
                            else:
                                diagnostics['issues'].append(f'Dashboard process (PID {pid}) is dead - stale metadata file')
                        except Exception:
                            pass
        except Exception as e:
            dashboard_health['parse_error'] = str(e)
            diagnostics['issues'].append(f'Dashboard metadata file corrupted: {e}')
    else:
        # No dashboard running - try to start one and see what happens
        try:
            from ..dashboard.lifecycle import ensure_dashboard_running
            url, port, started = ensure_dashboard_running(project_dir, background_process=False)
            dashboard_health['can_start'] = True
            dashboard_health['startup_test'] = 'SUCCESS'
            dashboard_health['test_url'] = url
            dashboard_health['test_port'] = port

            # Stop the test dashboard
            try:
                from ..dashboard.lifecycle import stop_dashboard
                stop_dashboard(project_dir)
            except Exception:
                pass
        except Exception as e:
            dashboard_health['can_start'] = False
            dashboard_health['startup_test'] = 'FAILED'
            dashboard_health['startup_error'] = str(e)
            diagnostics['issues'].append(f'Dashboard cannot start: {e}')

    diagnostics['dashboard_health'] = dashboard_health
    diagnostics['observations'] = observations

    return diagnostics
