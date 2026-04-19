"""Regression gate: generic-scoped doctrine artifacts contain no banned terms.

Contract: kitty-specs/charter-ownership-consolidation-and-neutrality-hardening-01KPD880/
         contracts/neutrality-lint-contract.md (C-3)

This module is the CI gate: it runs :func:`charter.neutrality.run_neutrality_lint`
against the shipped doctrine artifacts and fails if any banned term re-appears or
any allowlist entry becomes stale. It also contains a fault-injection test
(SC-005) that proves the scanner catches regressions, and a runtime budget test
(NFR-001).
"""

from __future__ import annotations

import time
from pathlib import Path

from charter.neutrality import NeutralityLintResult, run_neutrality_lint


def _format_failure(result: NeutralityLintResult) -> str:
    """Render a reviewer-actionable failure message per contract C-3.

    The message MUST include, per the contract:
      - one line per hit with ``file:line:column``, ``term_id``, and matched text;
      - a remediation block naming both options (remove term OR allowlist path);
      - a separate remediation note for stale allowlist entries.
    """
    lines: list[str] = ["Neutrality lint failed.", "", "HITS:"]
    for hit in result.hits:
        lines.append(f"  {hit.file}:{hit.line}:{hit.column} — term_id={hit.term_id} matched={hit.match!r}")
    if result.stale_allowlist_entries:
        lines.append("")
        lines.append("STALE ALLOWLIST ENTRIES:")
        for path in result.stale_allowlist_entries:
            lines.append(f"  {path}  (no file resolves this path)")
    lines += [
        "",
        "Remediation for each HIT:",
        "  (a) Remove the banned term from the file, OR",
        "  (b) Add the file's path to src/charter/neutrality/language_scoped_allowlist.yaml",
        "      if the file is INTENTIONALLY language-scoped.",
        "",
        "Remediation for STALE entries:",
        "  Delete the stale path from language_scoped_allowlist.yaml, or restore the expected file.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# T010 — Baseline regression gate
# ---------------------------------------------------------------------------


def test_generic_artifacts_are_neutral() -> None:
    """Baseline: the shipped repo must produce zero hits and zero stale entries."""
    result = run_neutrality_lint()
    assert result.passed, _format_failure(result)


# ---------------------------------------------------------------------------
# T011 — Fault-injection test (SC-005)
# ---------------------------------------------------------------------------


def test_fault_injection_catches_regression(tmp_path: Path) -> None:
    """Prove the lint would catch a regression.

    We create a synthetic "generic" artifact that contains a banned term and
    point the scanner at the tmp tree only, with no allowlist coverage. The
    scanner must fail and must record a PY-001 ("pytest") hit.
    """
    fake_root = tmp_path / "src" / "doctrine" / "fake"
    fake_root.mkdir(parents=True)
    (fake_root / "generic.md").write_text(
        "To run tests, invoke pytest on the command line.\n",
        encoding="utf-8",
    )

    # Write a minimal allowlist YAML with zero paths so the scanner has an
    # allowlist file to load but no entries that could mask our injection.
    empty_allowlist = tmp_path / "empty_allowlist.yaml"
    empty_allowlist.write_text(
        "schema_version: '1'\npaths: []\n",
        encoding="utf-8",
    )

    result = run_neutrality_lint(
        repo_root=tmp_path,
        scan_roots=[tmp_path / "src" / "doctrine"],
        allowlist_path=empty_allowlist,
    )
    assert not result.passed
    assert any(hit.term_id == "PY-001" for hit in result.hits), f"Expected PY-001 ('pytest') hit; got hits={result.hits}"


def test_default_scan_roots_include_mission_templates(tmp_path: Path) -> None:
    """Mission ``templates/`` directories must be scanned by default.

    The current repo ships many generic mission prompt files under
    ``src/specify_cli/missions/*/templates/`` rather than only under
    ``command-templates/``. A banned term appearing there must therefore be
    caught by the default repo scan.
    """
    mission_templates = tmp_path / "src" / "specify_cli" / "missions" / "research" / "templates"
    mission_templates.mkdir(parents=True)
    (mission_templates / "plan-template.md").write_text(
        "Generic mission guidance that accidentally tells the user to run pytest.\n",
        encoding="utf-8",
    )

    empty_allowlist = tmp_path / "allow.yaml"
    empty_allowlist.write_text("schema_version: '1'\npaths: []\n", encoding="utf-8")

    result = run_neutrality_lint(
        repo_root=tmp_path,
        allowlist_path=empty_allowlist,
    )
    assert not result.passed
    assert any(hit.term_id == "PY-001" for hit in result.hits), f"Expected PY-001 ('pytest') hit from mission templates; got hits={result.hits}"


def test_default_scan_roots_include_both_mission_template_dirs(tmp_path: Path) -> None:
    """Both ``command-templates/`` and ``templates/`` are scanned when they coexist.

    A mission directory may ship both directories at the same time.  A refactor
    that makes the two branches mutually exclusive would produce a false-negative
    in either direction — this test locks in that both are live.
    """
    mission_dir = tmp_path / "src" / "specify_cli" / "missions" / "research"
    command_templates = mission_dir / "command-templates"
    templates = mission_dir / "templates"
    command_templates.mkdir(parents=True)
    templates.mkdir(parents=True)

    (command_templates / "cmd.md").write_text("Run pytest to validate.\n", encoding="utf-8")
    (templates / "tpl.md").write_text("Generic guidance: invoke pytest here.\n", encoding="utf-8")

    empty_allowlist = tmp_path / "allow.yaml"
    empty_allowlist.write_text("schema_version: '1'\npaths: []\n", encoding="utf-8")

    result = run_neutrality_lint(repo_root=tmp_path, allowlist_path=empty_allowlist)
    assert not result.passed
    hit_files = {str(h.file) for h in result.hits}
    assert any("command-templates" in f for f in hit_files), f"Expected a PY-001 hit from command-templates/; got hit_files={hit_files}"
    assert any("command-templates" not in f and "templates" in f for f in hit_files), f"Expected a PY-001 hit from templates/; got hit_files={hit_files}"


def test_default_scan_roots_include_mission_templates(tmp_path: Path) -> None:
    """Mission ``templates/`` directories must be scanned by default.

    The current repo ships many generic mission prompt files under
    ``src/specify_cli/missions/*/templates/`` rather than only under
    ``command-templates/``. A banned term appearing there must therefore be
    caught by the default repo scan.
    """
    mission_templates = tmp_path / "src" / "specify_cli" / "missions" / "research" / "templates"
    mission_templates.mkdir(parents=True)
    (mission_templates / "plan-template.md").write_text(
        "Generic mission guidance that accidentally tells the user to run pytest.\n",
        encoding="utf-8",
    )

    empty_allowlist = tmp_path / "allow.yaml"
    empty_allowlist.write_text("schema_version: '1'\npaths: []\n", encoding="utf-8")

    result = run_neutrality_lint(
        repo_root=tmp_path,
        allowlist_path=empty_allowlist,
    )
    assert not result.passed
    assert any(hit.term_id == "PY-001" for hit in result.hits), f"Expected PY-001 ('pytest') hit from mission templates; got hits={result.hits}"


def test_default_scan_roots_include_both_mission_template_dirs(tmp_path: Path) -> None:
    """Both ``command-templates/`` and ``templates/`` are scanned when they coexist.

    A mission directory may ship both directories at the same time.  A refactor
    that makes the two branches mutually exclusive would produce a false-negative
    in either direction — this test locks in that both are live.
    """
    mission_dir = tmp_path / "src" / "specify_cli" / "missions" / "research"
    command_templates = mission_dir / "command-templates"
    templates = mission_dir / "templates"
    command_templates.mkdir(parents=True)
    templates.mkdir(parents=True)

    (command_templates / "cmd.md").write_text("Run pytest to validate.\n", encoding="utf-8")
    (templates / "tpl.md").write_text("Generic guidance: invoke pytest here.\n", encoding="utf-8")

    empty_allowlist = tmp_path / "allow.yaml"
    empty_allowlist.write_text("schema_version: '1'\npaths: []\n", encoding="utf-8")

    result = run_neutrality_lint(repo_root=tmp_path, allowlist_path=empty_allowlist)
    assert not result.passed
    hit_files = {str(h.file) for h in result.hits}
    assert any("command-templates" in f for f in hit_files), f"Expected a PY-001 hit from command-templates/; got hit_files={hit_files}"
    assert any("command-templates" not in f and "templates" in f for f in hit_files), f"Expected a PY-001 hit from templates/; got hit_files={hit_files}"


def test_fault_injection_respects_allowlist(tmp_path: Path) -> None:
    """An allowlisted file must NOT produce a hit even when it contains a banned term.

    This covers the allowlist short-circuit branch in the scanner and doubles
    as evidence that a language-scoped file can legitimately ship with
    language-specific terminology.
    """
    fake_root = tmp_path / "src" / "doctrine" / "python-scoped"
    fake_root.mkdir(parents=True)
    fake_file = fake_root / "py-guide.md"
    fake_file.write_text(
        "This file is python-scoped; it is allowed to mention pytest.\n",
        encoding="utf-8",
    )

    allowlist = tmp_path / "allow.yaml"
    allowlist.write_text(
        "schema_version: '1'\n"
        "paths:\n"
        "  - path: src/doctrine/python-scoped/py-guide.md\n"
        "    rationale: Intentionally scoped to Python for this test.\n"
        "    added_in: '3.2.0'\n",
        encoding="utf-8",
    )

    result = run_neutrality_lint(
        repo_root=tmp_path,
        scan_roots=[tmp_path / "src" / "doctrine"],
        allowlist_path=allowlist,
    )
    # No hits because the one offending file is allowlisted.
    assert not result.hits
    # No stale entries because the allowlisted path resolves to a real file.
    assert not result.stale_allowlist_entries
    assert result.passed


def test_stale_allowlist_entry_is_reported(tmp_path: Path) -> None:
    """An allowlist entry that resolves to zero files must be flagged as stale."""
    (tmp_path / "src" / "doctrine").mkdir(parents=True)

    allowlist = tmp_path / "allow.yaml"
    allowlist.write_text(
        "schema_version: '1'\npaths:\n  - path: src/doctrine/does-not-exist.md\n    rationale: Intentionally stale for test.\n    added_in: '3.2.0'\n",
        encoding="utf-8",
    )

    result = run_neutrality_lint(
        repo_root=tmp_path,
        scan_roots=[tmp_path / "src" / "doctrine"],
        allowlist_path=allowlist,
    )
    assert not result.passed
    assert "src/doctrine/does-not-exist.md" in result.stale_allowlist_entries


def test_glob_allowlist_matches_files(tmp_path: Path) -> None:
    """Glob allowlist entries must suppress hits in matching files AND not be flagged stale."""
    scoped_dir = tmp_path / "src" / "doctrine" / "python-scoped"
    scoped_dir.mkdir(parents=True)
    (scoped_dir / "one.md").write_text("run pytest here\n", encoding="utf-8")
    (scoped_dir / "two.md").write_text("also pytest here\n", encoding="utf-8")

    allowlist = tmp_path / "allow.yaml"
    allowlist.write_text(
        "schema_version: '1'\npaths:\n  - path: src/doctrine/python-scoped/*.md\n    rationale: Glob-scoped to a python directory.\n    added_in: '3.2.0'\n",
        encoding="utf-8",
    )

    result = run_neutrality_lint(
        repo_root=tmp_path,
        scan_roots=[tmp_path / "src" / "doctrine"],
        allowlist_path=allowlist,
    )
    assert result.passed, f"Expected glob allowlist to suppress all hits; got hits={result.hits} stale={result.stale_allowlist_entries}"


def test_regex_term_reports_accurate_column(tmp_path: Path) -> None:
    """A regex-kind banned term must report file:line:column that points at the match."""
    scan_root = tmp_path / "src" / "doctrine"
    scan_root.mkdir(parents=True)
    # "pip install" is a regex term (PY-003). Place it at a non-zero column.
    target = scan_root / "regex-hit.md"
    target.write_text("   pip install foo\n", encoding="utf-8")

    empty_allowlist = tmp_path / "allow.yaml"
    empty_allowlist.write_text("schema_version: '1'\npaths: []\n", encoding="utf-8")

    result = run_neutrality_lint(
        repo_root=tmp_path,
        scan_roots=[scan_root],
        allowlist_path=empty_allowlist,
    )
    py003_hits = [h for h in result.hits if h.term_id == "PY-003"]
    assert py003_hits, f"Expected PY-003 regex hit; got hits={result.hits}"
    hit = py003_hits[0]
    assert hit.line == 1
    # 1-indexed column of "pip install" starts at index 3 -> column 4
    assert hit.column == 4, f"Expected column 4, got {hit.column}"
    assert hit.match == "pip install"


# ---------------------------------------------------------------------------
# T012 — Runtime budget (NFR-001)
# ---------------------------------------------------------------------------


def test_runtime_budget() -> None:
    """The full baseline lint must complete in under 5 seconds."""
    start = time.perf_counter()
    run_neutrality_lint()
    elapsed = time.perf_counter() - start
    assert elapsed < 5.0, f"Neutrality lint took {elapsed:.2f}s, budget is 5s"
