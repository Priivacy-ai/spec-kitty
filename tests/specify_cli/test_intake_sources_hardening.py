"""Regression tests for WP04 T022/T023: path containment and symlink exclusion."""

from __future__ import annotations

from specify_cli.intake_sources import scan_for_plans


def test_scan_excludes_out_of_bounds_path(tmp_path, monkeypatch):
    """Paths resolving outside cwd are silently excluded."""
    # Create in-bounds file
    inbound = tmp_path / ".opencode" / "plans" / "brief.md"
    inbound.parent.mkdir(parents=True)
    inbound.write_text("# real brief", encoding="utf-8")

    # Create out-of-bounds file
    escape_dir = tmp_path.parent / f"escape_{tmp_path.name}"
    escape_dir.mkdir(exist_ok=True)
    escape_file = escape_dir / "plan.md"
    escape_file.write_text("# escape", encoding="utf-8")

    # Patch HARNESS_PLAN_SOURCES to include relative escape path
    patched = [
        ("opencode", "opencode", [".opencode/plans"]),
        ("escape_test", None, ["../escape_" + tmp_path.name + "/plan.md"]),
    ]
    monkeypatch.setattr("specify_cli.intake_sources.HARNESS_PLAN_SOURCES", patched)

    results = scan_for_plans(tmp_path)
    found_paths = {r[0].resolve() for r in results}
    assert inbound.resolve() in found_paths, "in-bounds file should be included"
    assert escape_file.resolve() not in found_paths, "escape file should be excluded"


def test_scan_excludes_symlink_in_directory(tmp_path):
    """Symlinks inside plan directories are not followed."""
    plans_dir = tmp_path / ".opencode" / "plans"
    plans_dir.mkdir(parents=True)

    regular = plans_dir / "brief.md"
    regular.write_text("# real brief", encoding="utf-8")

    outside = tmp_path.parent / f"outside_{tmp_path.name}.md"
    outside.write_text("# outside", encoding="utf-8")
    symlink = plans_dir / "linked.md"
    symlink.symlink_to(outside)

    results = scan_for_plans(tmp_path)
    found_paths = {r[0] for r in results}
    found_resolved = {p.resolve() for p in found_paths}
    assert regular.resolve() in found_resolved, "regular file should be included"
    assert symlink not in found_paths, "symlink should be excluded"
    assert outside.resolve() not in found_resolved, "symlink target excluded"


def test_scan_includes_valid_inbounds_file(tmp_path):
    """Normal in-bounds markdown files are still returned after hardening."""
    brief = tmp_path / ".opencode" / "plans" / "brief.md"
    brief.parent.mkdir(parents=True)
    brief.write_text("# brief", encoding="utf-8")
    results = scan_for_plans(tmp_path)
    found = {r[0].resolve() for r in results}
    assert brief.resolve() in found
