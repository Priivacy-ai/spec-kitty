#!/usr/bin/env python3
"""Check every behavioral profile projection and source hash, without rewriting."""

from __future__ import annotations

from pathlib import Path
import sys

from render_profile import render


def check(root: Path) -> list[str]:
    directory = root / "conformance/behavioral"
    sources = root / "packs/built-in/agent_profiles"
    manifests = sorted((directory / "profiles").glob("*.yaml"))
    errors = []
    if not manifests:
        return ["No behavioral profile manifests found"]
    expected = {p.stem for p in manifests}
    for suffix in [".md", ".md.sha256"]:
        actual = {p.name.removesuffix(suffix) for p in (directory / "projected").glob("*" + suffix)}
        if actual != expected:
            errors.append(f"Projection inventory differs for {suffix}: missing={sorted(expected - actual)}, extra={sorted(actual - expected)}")
    for manifest in manifests:
        relative = Path("packs/built-in/agent_profiles") / (manifest.stem + ".agent.yaml")
        try:
            body, digest = render(sources / relative.name)
            target = directory / "projected" / (manifest.stem + ".md")
            if target.read_text() != body:
                errors.append(f"{target.name}: rendered body drift")
            if target.with_suffix(".md.sha256").read_text() != f"{digest}  {relative.as_posix()}\n":
                errors.append(f"{target.name}: source hash/path drift")
        except (OSError, ValueError, TypeError, KeyError) as exc:
            errors.append(f"{manifest.stem}: {exc}")
    return errors


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    errors = check(root)
    for error in errors:
        print(error, file=sys.stderr)
    print(f"behavioral-projection-drift: {'FAIL' if errors else 'OK'}")
    raise SystemExit(bool(errors))
