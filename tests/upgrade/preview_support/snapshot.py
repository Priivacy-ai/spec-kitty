"""Independent lstat oracle. No production imports; atime alone is excluded."""

from __future__ import annotations

import hashlib
import os
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Node:
    """Raw filesystem observation, including absent roots and empty directories."""

    kind: str
    sha256: str | None = None
    target: str | None = None
    mode: int | None = None
    mtime_ns: int | None = None


Snapshot = dict[tuple[str, str], Node]


def snapshot(roots: Mapping[str, Path]) -> Snapshot:
    """Observe all nodes without following links, filtering Git or ignored files."""
    result: Snapshot = {}

    def visit(root_id: str, path: Path, relative: str) -> None:
        try:
            info = path.lstat()
        except FileNotFoundError:
            result[(root_id, relative)] = Node("absent")
            return
        mode = stat.S_IMODE(info.st_mode)
        if stat.S_ISLNK(info.st_mode):
            node = Node("symlink", target=os.readlink(path), mode=mode, mtime_ns=info.st_mtime_ns)
        elif stat.S_ISREG(info.st_mode):
            # Independent file-integrity oracle, not charter canonical hashing.
            digest = hashlib.sha256(path.read_bytes()).hexdigest()  # noqa: TID251 -- raw filesystem checksum
            node = Node("file", sha256=digest, mode=mode, mtime_ns=info.st_mtime_ns)
        elif stat.S_ISDIR(info.st_mode):
            node = Node("directory", mode=mode, mtime_ns=info.st_mtime_ns)
        else:
            node = Node("special", mode=mode, mtime_ns=info.st_mtime_ns)
        result[(root_id, relative)] = node
        if node.kind == "directory":
            for child in sorted(path.iterdir()):
                visit(root_id, child, child.name if relative == "." else f"{relative}/{child.name}")

    for root_id, path in sorted(roots.items()):
        visit(root_id, path, ".")
    return result


def assert_unchanged(before: Snapshot, after: Snapshot) -> None:
    """Enforce exact within-fixture purity, including parent mtimes."""
    changed = [key for key in sorted(before.keys() | after.keys()) if before.get(key) != after.get(key)]
    assert not changed, f"Filesystem changed: {changed}"


@dataclass(frozen=True)
class Effect:
    """Net persistent operation; raw timestamps remain in the snapshots."""

    root: str
    path: str
    action: str
    before: Node
    after: Node


def _action(before: Node, after: Node) -> str | None:
    if before.kind == "absent" and after.kind != "absent":
        return "create"
    if after.kind == "absent" and before.kind != "absent":
        return "delete"
    if before.kind != after.kind:
        return "replace"
    if before.sha256 != after.sha256:
        return "update"
    if before.target != after.target:
        return "retarget"
    if before.mode != after.mode:
        return "chmod"
    return None


def net_delta(before: Snapshot, after: Snapshot) -> tuple[Effect, ...]:
    """Derive path/kind/content/mode effects; mtime-only churn is purity evidence.

    A child's create changes parent mtime without a separate apply operation.
    Git internals remain present; callers must report their changes separately.
    No cross-copy content or timestamp-field normalization is performed here.
    """
    effects = []
    for root, path in sorted(before.keys() | after.keys()):
        old = before.get((root, path), Node("absent"))
        new = after.get((root, path), Node("absent"))
        action = _action(old, new)
        if action:
            effects.append(Effect(root, path, action, old, new))
    return tuple(effects)
