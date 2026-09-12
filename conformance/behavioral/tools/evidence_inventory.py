"""Resolve the shared suite catalog into exact expected evidence identities."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def manifest_paths(root: Path) -> tuple[list[str], list[str]]:
    catalog = json.loads((root / "conformance/behavioral/suite.json").read_text())
    profiles = sorted(p.relative_to(root).as_posix() for p in root.glob(catalog["profileGlob"]))
    if len(profiles) < catalog["minimumProfiles"] or not profiles:
        raise ValueError("Behavioral profile inventory below canonical suite floor")
    doctrine = catalog["doctrineManifests"]
    if not doctrine or len(set(profiles + doctrine)) != len(profiles + doctrine):
        raise ValueError("Empty or duplicate suite inventory")
    if any(not (root / path).is_file() for path in profiles + doctrine):
        raise ValueError("Suite manifest is missing")
    return profiles, doctrine


def inventory(root: Path) -> dict[str, object]:
    from ruamel.yaml import YAML

    yaml = YAML(typ="safe")
    profiles, doctrine = manifest_paths(root)

    def rules(path: str) -> list[str]:
        ids = [rule["ruleId"] for rule in yaml.load((root / path).read_text())["rules"]]
        if not ids or any(not isinstance(item, str) or not item for item in ids) or len(set(ids)) != len(ids):
            raise ValueError(f"Empty or duplicate rule inventory: {path}")
        return ids

    expected_profiles = {}
    for path in profiles:
        profile = Path(path).stem
        axes = []
        for rule in rules(path):
            suffix = "-" + profile
            if not rule.endswith(suffix):
                raise ValueError(f"Rule does not belong to profile: {rule}")
            parts = rule[: -len(suffix)].lower().split("-")
            axes.append(parts[0] + "".join(part.capitalize() for part in parts[1:]))
        if len(set(axes)) != len(axes):
            raise ValueError(f"Colliding profile axes: {profile}")
        expected_profiles[profile] = axes
    return {"perProfile": expected_profiles, "doctrineManifests": {path: rules(path) for path in doctrine}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paths", action="store_true", help="List runner inputs without requiring YAML dependencies")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    if args.paths:
        profile_paths, doctrine_paths = manifest_paths(root)
        print("\n".join(profile_paths + doctrine_paths))
    else:
        print(json.dumps(inventory(root)))
