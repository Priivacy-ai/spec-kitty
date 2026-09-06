"""Retained global runtime asset batches, including owner inventory and locks.

This is private to the three global asset owners. It is not a project installer,
filesystem overlay, rollback service or serialized apply interface. Catalog and
format decisions stay in bootstrap, agent_commands and agent_skills.
"""

from __future__ import annotations

from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from collections.abc import Iterator
from dataclasses import asdict, dataclass, replace
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

from specify_cli.runtime.generated_writer import generated_temporary_path, write_generated_file
from specify_cli.tool_surface.operations import (
    ApplyConsent,
    Diagnostic,
    Disposition,
    FileState,
    InputObservation,
    OperationRoot,
    OwnerApplyResult,
    OwnerAssessment,
    OwnershipProof,
    PhysicalEffect,
)


def digest(data: bytes) -> str:
    """Hash exact asset bytes, without text or timestamp normalization."""
    return hashlib.sha256(data).hexdigest()  # noqa: TID251 -- raw asset integrity, not charter hashing


def node_state(path: Path) -> FileState:
    """Read one node without following its final link."""
    try:
        info = path.lstat()
    except FileNotFoundError:
        return FileState("absent")
    mode = stat.S_IMODE(info.st_mode)
    if stat.S_ISLNK(info.st_mode):
        return FileState("symlink", target=os.readlink(path), mode=mode, mtime_ns=info.st_mtime_ns)
    if stat.S_ISDIR(info.st_mode):
        return FileState("directory", mode=mode, mtime_ns=info.st_mtime_ns)
    if not stat.S_ISREG(info.st_mode):
        raise ValueError(f"Unsupported asset node: {path}")
    return FileState("file", sha256=digest(path.read_bytes()), mode=mode, mtime_ns=info.st_mtime_ns)


def _action(before: FileState, after: FileState) -> str | None:
    if before.kind == "absent":
        return "create" if after.kind != "absent" else None
    if after.kind == "absent":
        return "delete"
    if before.kind != after.kind:
        return "replace"
    if before.sha256 != after.sha256:
        return "update"
    if before.target != after.target:
        return "retarget"
    return "chmod" if before.mode != after.mode else None


@dataclass(frozen=True)
class AssetWrite:
    """Exact prepared content and its owner-produced effect."""

    effect: PhysicalEffect
    content: bytes | None


@dataclass(frozen=True)
class AssetObservation:
    """Exact node plus directory membership, including ignored children."""

    path: Path
    state: FileState
    children: tuple[str, ...] | None = None
    identity: tuple[int, int] | None = None


@dataclass(frozen=True)
class PreparedAssets:
    """Immutable output of one global owner; never a replay token."""

    writes: tuple[AssetWrite, ...]
    observations: tuple[AssetObservation, ...]
    environment: tuple[tuple[str, str | None], ...]
    lock_path: Path
    anchor: Path
    temporary_paths: tuple[Path, ...] = ()


_SOURCE_ENV = (
    "HOME",
    "USERPROFILE",
    "SPEC_KITTY_HOME",
    "SPEC_KITTY_TEMPLATE_ROOT",
    "SPEC_KITTY_PACKS_ROOT",
    "XDG_CONFIG_HOME",
    "OPENCODE_CONFIG_DIR",
    "LOCALAPPDATA",
)
_HELD_LOCKS: ContextVar[frozenset[Path]] = ContextVar("global_asset_locks", default=frozenset())


def global_asset_root(owner: str, paths: tuple[Path, ...]) -> OperationRoot:
    """Choose a stable reporting anchor covering resolved global destinations."""
    anchor = Path(os.path.commonpath((Path.home(), *paths))).parent
    return OperationRoot(owner, "global", anchor)


def _observation(path: Path, state: FileState, children: tuple[str, ...] | None = None) -> AssetObservation:
    if state.kind == "directory":
        info = path.lstat()
        return AssetObservation(path, replace(state, mtime_ns=None), children, (info.st_dev, info.st_ino))
    return AssetObservation(path, state, children)


class AssetPreparation:
    """Collect one runtime owner's canonical assets before any write.

    The private inventory records only canonically equal or successfully
    generated nodes. Unknown bytes never become ownership by hashing them.
    Entries are committed last, so partial installation cannot certify work.
    """

    def __init__(self, owner: str, root: OperationRoot, cache: Path, lock_name: str, consent: ApplyConsent) -> None:
        self.owner, self.root, self.consent = owner, root, consent
        self.lock_path = cache / lock_name
        self.inventory = cache / f"{owner}-assets.json"
        self.observed: dict[Path, AssetObservation] = {}
        self.writes: dict[Path, AssetWrite] = {}
        self.dispositions: list[Disposition] = []
        self.entries: dict[str, dict[str, object]] = {}
        self.previous: dict[str, dict[str, object]] = {}
        self.selected: set[Path] = set()
        self.temporary_paths: set[Path] = set()
        self.environment = tuple((name, os.environ.get(name)) for name in _SOURCE_ENV)
        state = self.observe(self.inventory)
        if state.kind == "file":
            payload = json.loads(self.inventory.read_bytes())
            if not isinstance(payload, dict) or payload.get("schema_version") != 1 or not isinstance(payload.get("entries"), dict):
                raise ValueError(f"Invalid global asset inventory: {self.inventory}")
            for relative, record in payload["entries"].items():
                if not isinstance(relative, str) or not isinstance(record, dict):
                    raise ValueError("Invalid global asset inventory entry")
                # PhysicalEffect validates this same confined relative spelling.
                if Path(relative).is_absolute() or "\\" in relative or ":" in relative or any(p in {"", "..", "."} for p in relative.split("/")):
                    raise ValueError("Unconfined global asset inventory entry")
                try:
                    FileState(**record)
                except TypeError as exc:
                    raise ValueError("Invalid global asset inventory state") from exc
            self.previous = payload["entries"]
            self.entries = dict(self.previous)
        elif state.kind != "absent":
            raise ValueError(f"Global inventory is not a regular file: {self.inventory}")

    def observe(self, path: Path, *, members: bool = False) -> FileState:
        """Observe ancestry before opening a node; reject escaping parents."""
        for parent in reversed(path.parents):
            if parent != Path(parent.anchor):
                state = node_state(parent)
                system_alias = (
                    sys.platform == "darwin" and parent in {Path("/var"), Path("/tmp")} and state.kind == "symlink" and state.target == f"private/{parent.name}"  # noqa: S108 -- validate macOS system aliases, not a temporary file
                )
                if state.kind not in {"absent", "directory"} and not system_alias:
                    raise ValueError(f"Asset parent is not a directory: {parent}")
                self.observed.setdefault(parent, _observation(parent, state))
        state = node_state(path)
        children = tuple(sorted(p.name for p in path.iterdir())) if members and state.kind == "directory" else None
        previous = self.observed.get(path)
        current = _observation(path, state, children if children is not None else previous.children if previous else None)
        if previous is not None and (previous.state, previous.identity) != (current.state, current.identity):
            raise ValueError(f"Asset changed during preparation: {path}")
        self.observed[path] = current
        return state

    def source(self, path: Path) -> bytes:
        """Read a required regular source, retaining its exact observations."""
        if self.observe(path).kind != "file":
            raise ValueError(f"Required asset source is not a regular file: {path}")
        return path.read_bytes()

    def preserve(self, path: Path, reason: str, *, drift: bool = False) -> None:
        self.dispositions.append(
            Disposition(
                self.owner,
                self.root.root_id,
                path.relative_to(self.root.path).as_posix(),
                "consent_required" if drift else "preserve",
                reason,
            )
        )

    def _effect(self, path: Path, after: FileState, content: bytes | None, proof: OwnershipProof) -> None:
        before = self.observe(path)
        action = _action(before, after)
        relative = path.relative_to(self.root.path).as_posix()
        if action is None:
            self.dispositions.append(Disposition(self.owner, self.root.root_id, relative, "unchanged", "Asset already matches"))
            return
        if after.kind == "file" and action != "chmod" and path != self.lock_path:
            temporary = generated_temporary_path(path)
            if self.observe(temporary).kind != "absent":
                raise ValueError(f"Unproven atomic writer artifact must be preserved: {temporary}")
            self.temporary_paths.add(temporary)
        effect = PhysicalEffect(
            self.owner, "global_bootstrap", self.root, relative, action, before, after, "Refresh canonical global asset", (proof,), (self.owner,)
        )
        previous = self.writes.get(path)
        if previous is not None and previous.effect.after != after:
            raise ValueError(f"Conflicting global asset outputs: {path}")
        self.writes[path] = AssetWrite(effect, content)

    def parents(self, path: Path) -> None:
        for parent in reversed(path.parents):
            if parent == self.root.path or self.root.path not in parent.parents:
                continue
            state = self.observe(parent)
            if state.kind == "absent":
                self._effect(parent, FileState("directory", mode=0o755), None, OwnershipProof("managed_path", f"{self.owner}:required-parent"))

    def asset(self, path: Path, content: bytes | None, mode: int, *, managed_tree: bool = False, canonical_predecessor: bool = False) -> None:
        """Compare canonical output; preserve drift and unknown links/content."""
        before = self.observe(path)
        self.selected.add(path)
        relative = path.relative_to(self.root.path).as_posix()
        desired = FileState("directory", mode=mode) if content is None else FileState("file", sha256=digest(content), mode=mode)
        old = self.previous.get(relative)
        owned = old is not None and before.kind == old.get("kind") and before.sha256 == old.get("sha256") and before.target == old.get("target")
        equal = before.kind == desired.kind and before.sha256 == desired.sha256
        allowed_drift = old is not None and relative in self.consent.overwrite_paths
        if before.kind != "absent" and not (owned or equal or allowed_drift or canonical_predecessor or (managed_tree and before.kind != "symlink")):
            self.preserve(path, "Changed managed asset" if old else "Unproven existing asset", drift=old is not None)
            return
        if allowed_drift and not owned and not equal:
            self.backup(path, before, desired)
        if before.kind == "directory" and desired.kind != "directory":
            self.preserve(path, "Directory replacement requires enumerated ownership", drift=True)
            return
        self.parents(path)
        proof = OwnershipProof("manifest", f"{self.inventory.name}:{relative}") if owned else OwnershipProof("managed_path", f"{self.owner}:{relative}")
        if canonical_predecessor:
            proof = OwnershipProof("canonical_content", f"{self.owner}:{relative}:version-only-change")
        self._effect(path, desired, content, proof)
        self.entries[relative] = asdict(desired)

    def backup(self, path: Path, before: FileState, after: FileState) -> None:
        """Allocate a retained state-derived backup; collisions are never reused."""
        relative = path.relative_to(self.root.path).as_posix()
        identity = json.dumps((relative, asdict(replace(before, mtime_ns=None)), asdict(after)), sort_keys=True).encode()
        base = self.inventory.parent / "backups" / ("state-" + digest(identity))
        candidate = base
        suffix = 0
        while self.observe(candidate).kind != "absent":
            suffix += 1
            candidate = base.with_name(f"{base.name}-{suffix}")
        target = candidate / relative
        self.parents(target)
        data = self.source(path) if before.kind == "file" else None
        self._effect(target, replace(before, mtime_ns=None), data, OwnershipProof("manifest", f"{self.inventory.name}:{relative}"))

    def retire(self, path: Path) -> bool:
        """Remove only exact inventory-owned unchanged nodes; retain drift."""
        before = self.observe(path, members=True)
        if before.kind == "absent":
            return True
        relative = path.relative_to(self.root.path).as_posix()
        old = self.previous.get(relative)
        if old is None or (before.kind, before.sha256, before.target) != (old.get("kind"), old.get("sha256"), old.get("target")):
            self.preserve(path, "Unproven or edited retired asset", drift=old is not None)
            return False
        if before.kind == "directory":
            removable = [self.retire(child) for child in sorted(path.iterdir())]
            if not all(removable):
                self.preserve(path, "Retired directory contains preserved content")
                return False
        self._effect(path, FileState("absent"), None, OwnershipProof("manifest", f"{self.inventory.name}:{relative}"))
        self.entries.pop(relative, None)
        return True

    def prune_missing(self, destination: Path) -> None:
        """Inspect recorded descendants absent from this complete source tree."""
        candidates = sorted((self.root.path / p for p in self.previous), key=lambda p: len(p.parts))
        retired: list[Path] = []
        for path in candidates:
            if destination not in path.parents or path in self.selected or any(parent in retired for parent in path.parents):
                continue
            self.retire(path)
            retired.append(path)

    def tree(self, source: Path, destination: Path, *, readonly: bool = False, managed_tree: bool = False) -> None:
        """Prepare all source descendants, retaining empty dirs and executable bits."""
        source_state = self.observe(source, members=True)
        if source_state.kind != "directory":
            raise ValueError(f"Required asset tree unavailable: {source}")
        dest_state = self.observe(destination)
        if dest_state.kind not in {"directory", "absent"}:
            self.preserve(destination, "Unproven asset tree replacement")
            return
        self.asset(destination, None, source_state.mode or 0o755, managed_tree=managed_tree)
        for child in sorted(source.iterdir()):
            state = self.observe(child)
            target = destination / child.name
            if state.kind == "directory":
                self.tree(child, target, readonly=readonly, managed_tree=managed_tree)
            elif state.kind == "file":
                mode = state.mode or 0o644
                self.asset(target, self.source(child), mode & ~0o222 if readonly else mode, managed_tree=managed_tree)
            else:
                raise ValueError(f"Unsupported source asset kind: {child}")

    def finish(self, version_path: Path | None, version: str) -> OwnerAssessment:
        """Retain supporting inventory/stamp bytes; never refresh equal content."""
        if self.entries != self.previous:
            data = (json.dumps({"schema_version": 1, "entries": self.entries}, sort_keys=True, indent=2) + "\n").encode()
            self.parents(self.inventory)
            self._effect(self.inventory, FileState("file", sha256=digest(data), mode=0o644), data, OwnershipProof("managed_path", f"{self.owner}:inventory"))
        if version_path is not None:
            self.parents(version_path)
            data = version.encode()
            self._effect(version_path, FileState("file", sha256=digest(data), mode=0o644), data, OwnershipProof("managed_path", f"{self.owner}:version-stamp"))
        if self.writes:
            self.parents(self.lock_path)
            lock = self.observe(self.lock_path)
            if lock.kind == "absent":
                self._effect(
                    self.lock_path, FileState("file", sha256=digest(b""), mode=0o644), b"", OwnershipProof("managed_path", f"{self.owner}:persistent-lock")
                )
            elif lock.kind != "file":
                raise ValueError("Global owner lock is not a regular file")
        writes = tuple(self.writes.values())
        prepared = PreparedAssets(writes, tuple(self.observed.values()), self.environment, self.lock_path, self.root.path, tuple(sorted(self.temporary_paths)))
        return OwnerAssessment(
            self.owner,
            self.root,
            tuple(w.effect for w in writes),
            tuple(self.dispositions),
            inputs_fingerprint=(InputObservation("assets", prepared.observations),),
            prepared=prepared,
            consent=self.consent,
        )


def incomplete(owner: str, root: OperationRoot, error: Exception) -> OwnerAssessment:
    """A source/config failure never becomes a complete empty assessment."""
    return OwnerAssessment(owner, root, complete=False, diagnostics=(Diagnostic("global_assets_unavailable", owner, "error", str(error)),))


def check_assets(assessment: OwnerAssessment) -> tuple[Diagnostic, ...]:
    """Compare the entire batch before opening any write-capable handle."""
    prepared = assessment.prepared
    if not isinstance(prepared, PreparedAssets):
        return (Diagnostic("invalid_preparation", assessment.owner_key, "error", "Expected retained global asset data"),)
    try:
        for name, value in prepared.environment:
            if os.environ.get(name) != value:
                raise ValueError(f"Global asset environment changed: {name}")
        # Ancestors precede child file reads, including parents outside the root.
        for observation in sorted(prepared.observations, key=lambda item: len(item.path.parts)):
            current = _observation(observation.path, node_state(observation.path))
            if (current.state, current.identity) != (observation.state, observation.identity):
                raise ValueError(f"Global asset input changed: {observation.path}")
            if observation.children is not None and tuple(sorted(p.name for p in observation.path.iterdir())) != observation.children:
                raise ValueError(f"Global asset inventory changed: {observation.path}")
    except (OSError, ValueError) as exc:
        return (Diagnostic("precondition_changed", assessment.owner_key, "error", str(exc)),)
    return ()


@contextmanager
def recheck_assets(assessment: OwnerAssessment) -> Iterator[tuple[Diagnostic, ...]]:
    """Hold an existing owner lock without truncation throughout recheck/apply.

    Cold lock creation is itself an assessed effect in apply. Recheck always
    runs before that creation; exclusive creation detects a racing cold owner.
    """
    from specify_cli.runtime.bootstrap import _lock_exclusive

    diagnostics = check_assets(assessment)
    prepared = assessment.prepared
    if diagnostics or not assessment.effects or not isinstance(prepared, PreparedAssets):
        yield diagnostics
        return
    if prepared.lock_path in _HELD_LOCKS.get():
        yield diagnostics
        return
    with ExitStack() as stack:
        if prepared.lock_path.exists():
            stream = stack.enter_context(prepared.lock_path.open("r"))
            _lock_exclusive(stream)
        elif os.name != "nt":
            # POSIX directories support flock without creating a lock artifact.
            # Serialize cold installers on the stable reporting anchor until
            # apply creates and acquires the existing owner-specific lock.
            descriptor = os.open(prepared.anchor, os.O_RDONLY)
            stack.callback(os.close, descriptor)
            _lock_exclusive(descriptor)
        token = _HELD_LOCKS.set(_HELD_LOCKS.get() | {prepared.lock_path})
        try:
            yield check_assets(assessment)
        finally:
            _HELD_LOCKS.reset(token)


def _write_asset(write: AssetWrite) -> None:
    effect, content = write.effect, write.content
    path = effect.destination
    if effect.action == "delete":
        if effect.before.kind == "directory":
            path.rmdir()
        else:
            path.unlink()
    elif effect.action == "chmod":
        path.chmod(effect.after.mode or 0o444)
    elif effect.after.kind == "directory":
        path.mkdir(mode=effect.after.mode or 0o755)
        path.chmod(effect.after.mode or 0o755)
    elif effect.after.kind == "symlink":
        if effect.after.target is None:
            raise ValueError("Missing retained link target")
        path.symlink_to(effect.after.target)
    else:
        if content is None:
            raise ValueError("Missing prepared file bytes")
        if effect.before.kind == "symlink":
            path.unlink()
        write_generated_file(path, content, read_only=False)
        path.chmod(effect.after.mode or 0o444)


def apply_assets(assessment: OwnerAssessment, consent: ApplyConsent) -> OwnerApplyResult:
    """Write retained bytes, report actual IDs, and never certify a failed batch."""
    ids = tuple(effect.id for effect in assessment.effects)
    if not assessment.complete or consent.overwrite_paths != assessment.consent.overwrite_paths:
        return OwnerApplyResult(assessment.owner_key, skipped=ids, outcome="failed", diagnostics=assessment.diagnostics)
    if not consent.automatic or not ids:
        return OwnerApplyResult(assessment.owner_key, skipped=ids, outcome="skipped")
    with recheck_assets(assessment) as diagnostics:
        if diagnostics:
            return OwnerApplyResult(assessment.owner_key, skipped=ids, outcome="precondition_changed", diagnostics=diagnostics)
        if assessment.owner_key == "runtime_bootstrap":
            from specify_cli.runtime.bootstrap import populate_from_package

            prepared = assessment.prepared
            if not isinstance(prepared, PreparedAssets):
                raise TypeError("Expected retained package assets")
            result = populate_from_package(prepared.lock_path.parent.parent, assessment=assessment, consent=consent)
            if result is None:
                raise TypeError("Runtime package writer omitted its apply result")
            return result
        return _apply_retained_assets(assessment)


def _write_order(write: AssetWrite) -> tuple[int, int, str]:
    effect = write.effect
    name = effect.destination.name
    stage = 3
    if effect.after.kind == "directory" and effect.action == "create":
        stage = 0
    elif name.startswith(".") and name.endswith(".lock"):
        stage = 1
    elif "/backups/state-" in effect.path:
        stage = 2
    elif name.endswith("-assets.json"):
        stage = 5
    elif name.endswith(".lock"):
        stage = 6
    elif effect.action == "delete":
        stage = 4
    depth = -len(effect.destination.parts) if effect.action == "delete" else len(effect.destination.parts)
    return stage, depth, effect.path


def _apply_retained_assets(assessment: OwnerAssessment) -> OwnerApplyResult:
    from specify_cli.runtime.bootstrap import _lock_exclusive

    prepared = assessment.prepared
    if not isinstance(prepared, PreparedAssets):
        raise TypeError("Expected prepared global assets")
    # Parent creates first; inventory and version stamps last. A failed content
    # write must never stamp or certify the unattempted remainder.
    ordered = sorted(prepared.writes, key=_write_order)
    succeeded: list[str] = []
    with ExitStack() as locks:
        for index, write in enumerate(ordered):
            try:
                if write.effect.destination == prepared.lock_path and write.effect.action == "create":
                    stream = locks.enter_context(prepared.lock_path.open("x"))
                    prepared.lock_path.chmod(write.effect.after.mode or 0o644)
                    _lock_exclusive(stream)
                else:
                    _write_asset(write)
            except (OSError, ValueError, UnicodeError) as exc:
                return OwnerApplyResult(
                    assessment.owner_key,
                    tuple(succeeded),
                    (write.effect.id,),
                    tuple(w.effect.id for w in ordered[index + 1 :]),
                    (Diagnostic("global_asset_write_failed", assessment.owner_key, "error", str(exc)),),
                    "partial" if succeeded else "failed",
                )
            succeeded.append(write.effect.id)
    return OwnerApplyResult(assessment.owner_key, tuple(succeeded))
