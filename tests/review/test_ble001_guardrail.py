from __future__ import annotations

from pathlib import Path

from specify_cli.cli.commands.review import (
    audit_auth_storage_ble001_line,
    collect_auth_storage_ble001_findings,
)


def test_scoped_ble001_with_specific_safety_reason_passes(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    path = repo_root / "src/specify_cli/auth/flows/revoke.py"
    line = (
        "except Exception as exc:  # noqa: BLE001 - "
        "storage cleanup failure is logged and local deletion continues"
    )

    finding = audit_auth_storage_ble001_line(path, 12, line, repo_root=repo_root)

    assert finding is None


def test_scoped_ble001_with_missing_reason_fails(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    path = repo_root / "src/specify_cli/auth/flows/revoke.py"
    line = "except Exception as exc:  # noqa: BLE001"

    finding = audit_auth_storage_ble001_line(path, 12, line, repo_root=repo_root)

    assert finding is not None
    assert finding.file == str(path)
    assert finding.line == 12
    assert finding.suppression == line
    assert "specific safety reason" in finding.remediation


def test_scoped_plain_broad_exception_without_noqa_fails(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    path = repo_root / "src/specify_cli/auth/http/transport.py"
    line = "except Exception as exc:"

    finding = audit_auth_storage_ble001_line(path, 19, line, repo_root=repo_root)

    assert finding is not None
    assert finding.file == str(path)
    assert finding.line == 19
    assert finding.reason == ""
    assert "specific safety reason" in finding.remediation


def test_scoped_ble001_with_generic_reason_fails(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    path = repo_root / "src/specify_cli/cli/commands/_auth_logout.py"
    line = "except Exception as exc:  # noqa: BLE001 - broad catch"

    finding = audit_auth_storage_ble001_line(path, 27, line, repo_root=repo_root)

    assert finding is not None
    assert finding.file == str(path)
    assert finding.line == 27
    assert finding.reason == "broad catch"
    assert "narrow the exception type" in finding.remediation


def test_ble001_outside_scoped_auth_storage_paths_is_ignored(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    path = repo_root / "src/specify_cli/cli/commands/sync.py"
    line = "except Exception:  # noqa: BLE001"

    finding = audit_auth_storage_ble001_line(path, 4, line, repo_root=repo_root)

    assert finding is None


def test_collect_auth_storage_ble001_findings_reports_file_line_and_text(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    bad_path = repo_root / "src/specify_cli/auth/transport.py"
    bad_path.parent.mkdir(parents=True)
    bad_path.write_text(
        "\n".join(
            [
                "def connect() -> None:",
                "    try:",
                "        pass",
                "    except Exception:  # noqa: BLE001 - ignore",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    out_of_scope = repo_root / "src/specify_cli/cli/commands/sync.py"
    out_of_scope.parent.mkdir(parents=True)
    out_of_scope.write_text("except Exception:  # noqa: BLE001\n", encoding="utf-8")

    findings = collect_auth_storage_ble001_findings(repo_root)

    assert len(findings) == 1
    assert findings[0].file == str(bad_path)
    assert findings[0].line == 4
    assert findings[0].suppression == "except Exception:  # noqa: BLE001 - ignore"
