"""Mission-review command package.

Public entry: review_mission()
Internal modules:
  _diagnostics.py   — MissionReviewDiagnostic StrEnum (WP03)
  _mode.py          — MissionReviewMode + resolve_mode() (WP03)
  _issue_matrix.py  — issue-matrix validator (WP03)
  _lane_gate.py     — Gate 1: WP lane consistency check
  _dead_code.py     — Gate 2: dead-code scan
  _ble001_audit.py  — Gate 3: BLE001 broad-except audit
  _report.py        — Gate 4: report writer

See: src/specify_cli/cli/commands/review/ERROR_CODES.md (authored by WP03)
"""

from __future__ import annotations

import json
import shlex
import subprocess  # noqa: F401  (monkeypatched in tests)
import sys
import tomllib
from pathlib import Path
from typing import Annotated, Literal

import typer

from specify_cli.cli.commands._test_env_check import (  # noqa: F401
    TestExtraMissing,
    assert_pytest_available,
)
from specify_cli.compat._detect.install_method import (  # noqa: F401
    InstallMethod,
    detect_install_method,
)
from specify_cli.cli.selector_resolution import resolve_mission_handle  # noqa: F401
from specify_cli.task_utils import TaskCliError, find_repo_root  # noqa: F401
from specify_cli.version_utils import get_version  # noqa: F401

from ._ble001_audit import (  # noqa: F401
    Ble001SuppressionFinding,
    audit_auth_storage_ble001_line,
    collect_auth_storage_ble001_findings,
)
from ._dead_code import scan_dead_code  # noqa: F401
from ._diagnostics import MissionReviewDiagnostic  # noqa: F401
from ._issue_matrix import validate_issue_matrix  # noqa: F401
from ._lane_gate import check_wp_lanes  # noqa: F401
from ._mode import MissionReviewMode, ModeMismatchError, resolve_mode  # noqa: F401
from ._report import GateRecord, write_review_report  # noqa: F401


_PACKAGE_NAME = "spec-kitty-cli"
_PYTEST_NAME = "pytest"


def _fail_missing_test_extra(console: object) -> None:
    import sys

    diagnostic_code = MissionReviewDiagnostic.TEST_EXTRA_MISSING
    remediation = _missing_test_extra_remediation()
    diagnostic = {
        "diagnostic_code": str(diagnostic_code),
        "message": (
            "pytest is not importable from the active Python interpreter. "
            f"Run `{remediation}` to install pytest into that interpreter, then retry."
        ),
        "remediation": remediation,
    }
    console.print(  # type: ignore[attr-defined]
        f"[red]Error:[/red] {diagnostic_code}: {diagnostic['message']}"
    )
    sys.stdout.write(json.dumps(diagnostic) + "\n")
    raise typer.Exit(1)


def _missing_test_extra_remediation() -> str:
    try:
        install_method = detect_install_method()
    except Exception:  # noqa: BLE001
        install_method = InstallMethod.UNKNOWN

    if install_method == InstallMethod.UV_TOOL:
        return _uv_tool_reinstall_command() or _fallback_uv_tool_reinstall_command()

    return "uv sync --extra test"


def _versioned_package() -> str:
    version = get_version()
    package = "spec-kitty-cli"
    if version and version != "0.0.0-dev":
        package = f"{package}=={version}"
    return package


def _fallback_uv_tool_reinstall_command() -> str:
    return f"{_uv_tool_env_prefix()}uv tool install --force --with pytest {_versioned_package()}"


def _uv_tool_reinstall_command() -> str | None:
    try:
        receipt = _active_uv_tool_receipt()
        if receipt is None:
            return None

        requirements = receipt.get("tool", {}).get("requirements", [])
        if not isinstance(requirements, list):
            return None

        tool_requirement = _find_uv_tool_requirement(requirements)
        if tool_requirement is None:
            return None

        args = ["uv", "tool", "install", "--force"]
        args.extend(_uv_tool_with_args(requirements))
        args.extend(_uv_tool_package_args(tool_requirement))
        return f"{_uv_tool_env_prefix()}{' '.join(shlex.quote(arg) for arg in args)}"
    except Exception:  # noqa: BLE001
        return None


def _active_uv_tool_receipt() -> dict[str, object] | None:
    try:
        executable_parent = Path(sys.executable).parent
        if executable_parent.name.lower() not in {"bin", "scripts"}:
            return None

        receipt_path = executable_parent.parent / "uv-receipt.toml"
        receipt = tomllib.loads(receipt_path.read_text(encoding="utf-8"))
        if isinstance(receipt, dict):
            return receipt
    except Exception:  # noqa: BLE001
        return None
    return None


def _find_uv_tool_requirement(requirements: list[object]) -> dict[str, object] | None:
    for requirement in requirements:
        if isinstance(requirement, dict) and requirement.get("name") == _PACKAGE_NAME:
            return requirement
    return None


def _uv_tool_with_args(requirements: list[object]) -> list[str]:
    args: list[str] = []
    has_pytest = False
    for requirement in requirements:
        if not isinstance(requirement, dict):
            continue
        if requirement.get("name") == _PACKAGE_NAME:
            continue
        if requirement.get("name") == _PYTEST_NAME:
            has_pytest = True
        requirement_arg = _uv_tool_requirement_arg(requirement)
        if requirement_arg is not None:
            args.extend(["--with", requirement_arg])
    if not has_pytest:
        args.extend(["--with", _PYTEST_NAME])
    return args


def _uv_tool_requirement_arg(requirement: dict[str, object]) -> str | None:
    directory = _nonempty_str(requirement.get("directory"))
    if directory is not None:
        return directory

    path = _nonempty_str(requirement.get("path"))
    if path is not None:
        return path

    git = _nonempty_str(requirement.get("git"))
    if git is not None:
        return _uv_git_source(git)

    name = _nonempty_str(requirement.get("name"))
    if name is None:
        return None
    specifier = _nonempty_str(requirement.get("specifier"))
    return f"{name}{specifier or ''}"


def _uv_tool_package_args(requirement: dict[str, object]) -> list[str]:
    directory = _nonempty_str(requirement.get("directory"))
    if directory is not None:
        return [directory]

    editable = _nonempty_str(requirement.get("editable"))
    if editable is not None:
        return ["--editable", editable]

    path = _nonempty_str(requirement.get("path"))
    if path is not None:
        return [path]

    git = _nonempty_str(requirement.get("git"))
    if git is not None:
        return [_PACKAGE_NAME, "--from", _uv_git_source(git)]

    specifier = _nonempty_str(requirement.get("specifier"))
    if specifier is not None:
        return [f"{_PACKAGE_NAME}{specifier}"]

    return [_PACKAGE_NAME]


def _uv_git_source(git: str) -> str:
    return git if git.startswith("git+") else f"git+{git}"


def _nonempty_str(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


def _uv_tool_env_prefix() -> str:
    prefixes = [_uv_tool_dir_env_prefix(), _uv_tool_bin_dir_env_prefix()]
    return "".join(prefix for prefix in prefixes if prefix)


def _uv_tool_dir_env_prefix() -> str:
    tool_dir = _active_uv_tool_dir()
    if tool_dir is None or _same_path(tool_dir, Path.home() / ".local" / "share" / "uv" / "tools"):
        return ""
    return f"UV_TOOL_DIR={shlex.quote(str(tool_dir))} "


def _uv_tool_bin_dir_env_prefix() -> str:
    bin_dir = _active_uv_tool_bin_dir()
    if bin_dir is None or _same_path(bin_dir, Path.home() / ".local" / "bin"):
        return ""
    return f"UV_TOOL_BIN_DIR={shlex.quote(str(bin_dir))} "


def _active_uv_tool_dir() -> Path | None:
    try:
        executable_parent = Path(sys.executable).parent
        if executable_parent.name.lower() not in {"bin", "scripts"}:
            return None
        tool_env = executable_parent.parent
        if not (tool_env / "uv-receipt.toml").exists():
            return None
        return tool_env.parent
    except Exception:  # noqa: BLE001
        return None


def _active_uv_tool_bin_dir() -> Path | None:
    try:
        receipt = _active_uv_tool_receipt()
        if receipt is None:
            return None
        entrypoints = receipt.get("tool", {}).get("entrypoints", [])
        if not isinstance(entrypoints, list):
            return None
        for entrypoint in entrypoints:
            if not isinstance(entrypoint, dict) or entrypoint.get("name") != "spec-kitty":
                continue
            install_path = _nonempty_str(entrypoint.get("install-path"))
            if install_path is not None:
                return Path(install_path).parent
    except Exception:  # noqa: BLE001
        return None
    return None


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except Exception:  # noqa: BLE001
        return left == right


def _resolve_repo_root(console: object) -> Path:
    try:
        return find_repo_root()
    except TaskCliError as exc:
        console.print(f"[red]Error:[/red] {exc}")  # type: ignore[attr-defined]
        raise typer.Exit(2) from exc


def _require_mission_handle(mission: str, console: object) -> str:
    handle = mission.strip()
    if not handle:
        console.print("[red]Error:[/red] --mission is required.")  # type: ignore[attr-defined]
        raise typer.Exit(2)
    return handle


def _load_meta(feature_dir: Path) -> dict[str, object]:
    meta_path = feature_dir / "meta.json"
    if not meta_path.exists():
        return {}
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _resolve_mode_or_exit(
    *,
    console: object,
    cli_mode: str | None,
    baseline_merge_commit: str | None,
) -> tuple[MissionReviewMode, bool]:
    try:
        return resolve_mode(
            cli_flag=cli_mode,
            baseline_merge_commit=baseline_merge_commit,
        )
    except ModeMismatchError as exc:
        diagnostic = {
            "diagnostic_code": str(exc.diagnostic_code),
            "message": exc.message,
        }
        console.print(f"[red]Error:[/red] {exc.diagnostic_code}")  # type: ignore[attr-defined]
        console.print(exc.message)  # type: ignore[attr-defined]
        import sys

        sys.stdout.write(json.dumps(diagnostic) + "\n")
        raise typer.Exit(1) from exc


def _record_gate(
    gates_recorded: list[GateRecord],
    *,
    gate_id: str,
    name: str,
    result: Literal["pass", "fail"],
) -> None:
    gates_recorded.append(
        GateRecord(
            id=gate_id,
            name=name,
            command=f"spec-kitty review (internal {gate_id.replace('_', ' ')})",
            exit_code=1 if result == "fail" else 0,
            result=result,
        )
    )


def _run_lane_gate(
    feature_dir: Path,
    repo_root: Path,
    console: object,
    findings: list[dict[str, str]],
    gates_recorded: list[GateRecord],
) -> None:
    findings_before = len(findings)
    check_wp_lanes(feature_dir, repo_root, console, findings)  # type: ignore[arg-type]
    result: Literal["pass", "fail"] = "fail" if len(findings) > findings_before else "pass"
    _record_gate(gates_recorded, gate_id="gate_1", name="wp_lane_check", result=result)


def _run_dead_code_gate(
    *,
    baseline_merge_commit: str | None,
    repo_root: Path,
    console: object,
    findings: list[dict[str, str]],
    mission_id: str | None,
    mission_slug: str,
    gates_recorded: list[GateRecord],
) -> None:
    findings_before = len(findings)
    scan_dead_code(
        baseline_merge_commit,
        repo_root,
        console,  # type: ignore[arg-type]
        findings,
        mission_id=mission_id,
        mission_slug=mission_slug,
    )
    result: Literal["pass", "fail"] = "fail" if len(findings) > findings_before else "pass"
    _record_gate(gates_recorded, gate_id="gate_2", name="dead_code_scan", result=result)


def _run_ble001_gate(
    repo_root: Path,
    console: object,
    findings: list[dict[str, str]],
    gates_recorded: list[GateRecord],
) -> None:
    ble001_findings = collect_auth_storage_ble001_findings(repo_root)
    for finding in ble001_findings:
        findings.append(
            {
                "type": "ble001_suppression",
                "file": finding.file,
                "line": str(finding.line),
                "content": finding.suppression,
                "remediation": finding.remediation,
            }
        )

    if ble001_findings:
        console.print(  # type: ignore[attr-defined]
            f"  [red]✗[/red]  BLE001 audit: {len(ble001_findings)} unjustified suppression(s)"
        )
        for finding in ble001_findings:
            console.print(f"       {finding.file}:{finding.line}")  # type: ignore[attr-defined]
            console.print(f"       suppression: {finding.suppression}")  # type: ignore[attr-defined]
            console.print(f"       remediation: {finding.remediation}")  # type: ignore[attr-defined]
        result: Literal["pass", "fail"] = "fail"
    else:
        console.print("  [green]✓[/green]  BLE001 audit: 0 unjustified suppressions")  # type: ignore[attr-defined]
        result = "pass"

    _record_gate(gates_recorded, gate_id="gate_3", name="ble001_audit", result=result)


def _evaluate_issue_matrix(
    *,
    feature_dir: Path,
    review_mode: MissionReviewMode,
    console: object,
    findings: list[dict[str, str]],
) -> bool | Literal["not_applicable"]:
    if review_mode is not MissionReviewMode.POST_MERGE:
        return "not_applicable"

    issue_matrix_path = feature_dir / "issue-matrix.md"
    if not issue_matrix_path.exists():
        console.print(  # type: ignore[attr-defined]
            f"  [red]✗[/red]  Issue matrix: "
            f"{MissionReviewDiagnostic.ISSUE_MATRIX_MISSING}: "
            "issue-matrix.md not found (required in post-merge mode)"
        )
        findings.append(
            {
                "type": "issue_matrix_violation",
                "diagnostic_code": str(MissionReviewDiagnostic.ISSUE_MATRIX_MISSING),
                "message": "issue-matrix.md is required in post-merge mode",
            }
        )
        return False

    matrix_result = validate_issue_matrix(issue_matrix_path)
    if not matrix_result.passed:
        for diag in matrix_result.diagnostics:
            console.print(  # type: ignore[attr-defined]
                f"  [red]✗[/red]  Issue matrix: {diag['diagnostic_code']}: {diag['message']}"
            )
            findings.append(
                {
                    "type": "issue_matrix_violation",
                    "diagnostic_code": diag["diagnostic_code"],
                    "message": diag["message"],
                }
            )
    else:
        console.print(  # type: ignore[attr-defined]
            f"  [green]✓[/green]  Issue matrix: "
            f"{len(matrix_result.rows)} row(s) validated"
        )
    return True


def review_mission(
    mission: Annotated[
        str,
        typer.Option("--mission", help="Mission handle (id, mid8, or slug)."),
    ] = "",
    mode: Annotated[
        str | None,
        typer.Option(
            "--mode",
            help=(
                "Review mode: 'lightweight' (consistency check only) or "
                "'post-merge' (full release-gate contract). "
                "Auto-detected from meta.json.baseline_merge_commit when omitted."
            ),
            show_default=False,
        ),
    ] = None,
) -> None:
    """Validate a merged mission: WP lane check, dead-code scan, BLE001 audit.

    Writes kitty-specs/<slug>/mission-review-report.md with a machine-readable
    verdict.  See module docstring for known false-positive scenarios in the
    dead-code scan step.
    """
    from rich.console import Console

    console = Console()
    repo_root = _resolve_repo_root(console)
    try:
        assert_pytest_available(repo_root)
    except TestExtraMissing:
        _fail_missing_test_extra(console)

    handle = _require_mission_handle(mission, console)
    resolved = resolve_mission_handle(handle, repo_root)
    feature_dir = resolved.feature_dir
    mission_slug = resolved.mission_slug
    meta = _load_meta(feature_dir)
    friendly_name: str = str(meta.get("friendly_name") or mission_slug)
    _bmc_raw = meta.get("baseline_merge_commit")
    baseline_merge_commit: str | None = str(_bmc_raw) if _bmc_raw else None
    review_mode, auto_detected = _resolve_mode_or_exit(
        console=console,
        cli_mode=mode,
        baseline_merge_commit=baseline_merge_commit,
    )
    mode_label = f"{review_mode.value} ({'auto-detected' if auto_detected else 'explicit'})"
    console.print(f"\nReviewing mission: {friendly_name} ({mission_slug})")
    console.print(f"Mode: {mode_label}\n")

    findings: list[dict[str, str]] = []
    gates_recorded: list[GateRecord] = []
    _mission_id_raw = meta.get("mission_id")
    _mission_id: str | None = str(_mission_id_raw) if _mission_id_raw else None
    _run_lane_gate(feature_dir, repo_root, console, findings, gates_recorded)
    _run_dead_code_gate(
        baseline_merge_commit=baseline_merge_commit,
        repo_root=repo_root,
        console=console,
        findings=findings,
        mission_id=_mission_id,
        mission_slug=mission_slug,
        gates_recorded=gates_recorded,
    )
    _run_ble001_gate(repo_root, console, findings, gates_recorded)
    issue_matrix_present = _evaluate_issue_matrix(
        feature_dir=feature_dir,
        review_mode=review_mode,
        console=console,
        findings=findings,
    )
    mission_exception_present: bool | Literal["not_applicable"] = (
        (feature_dir / "mission-exception.md").exists()
        if review_mode is MissionReviewMode.POST_MERGE
        else "not_applicable"
    )
    write_review_report(
        feature_dir,
        repo_root,
        findings,
        console,
        mode=review_mode.value,
        gates_recorded=gates_recorded,
        issue_matrix_present=issue_matrix_present,
        mission_exception_present=mission_exception_present,
    )
    _record_gate(gates_recorded, gate_id="gate_4", name="report_writer", result="pass")


__all__ = [
    "Ble001SuppressionFinding",
    "GateRecord",
    "MissionReviewDiagnostic",
    "MissionReviewMode",
    "ModeMismatchError",
    "TestExtraMissing",
    "assert_pytest_available",
    "audit_auth_storage_ble001_line",
    "collect_auth_storage_ble001_findings",
    "resolve_mode",
    "review_mission",
    "validate_issue_matrix",
]
