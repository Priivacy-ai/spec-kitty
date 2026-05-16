"""OrgDoctrineSource protocol and FetchResult contract.

The protocol is intentionally structural (``typing.Protocol``) so that third
parties can supply their own adapters without inheriting from a spec-kitty
base class.  The single contract method is ``fetch(target_dir)``; everything
else is implementation detail.

All implementations MUST:

* Write the doctrine pack into ``target_dir`` such that the directory contains
  at least one recognised artifact subdirectory (``directives/``, ``tactics/``,
  ``styleguides/``, ``toolguides/``, ``paradigms/``, ``procedures/``,
  ``agent_profiles/``, ``mission_step_contracts/``) on success.
* Terminate every network call before returning.  After ``fetch`` returns, the
  snapshot must be usable offline.
* Never raise for network/auth/server problems — surface them via
  ``FetchResult(ok=False, errors=[...])`` so callers can compose error UX.

See ``kitty-specs/layered-doctrine-org-layer-01KRNPEE/contracts/`` for the
pack layout and the HTTP API contract that :class:`ApiSource` implements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass
class FetchResult:
    """Outcome of a fetch operation.

    Attributes:
        ok: True when the fetch produced a valid local snapshot.
        artifacts_written: Number of artifact files (typically ``*.yaml``)
            written to the target directory.  Implementations are free to
            count distinctly (e.g. ``GitSource`` counts ``*.yaml`` files,
            ``ApiSource`` counts every artifact body it persisted).
        pack_version: Best-effort version identifier for the snapshot (e.g.
            a git tag/sha from ``git describe``, an ``ETag``, or the
            ``/version`` endpoint response).  ``None`` when no version is
            available.
        errors: List of human-readable error messages.  Empty when ``ok``.
    """

    ok: bool
    artifacts_written: int
    pack_version: str | None
    errors: list[str] = field(default_factory=list)


@runtime_checkable
class OrgDoctrineSource(Protocol):
    """Fetch-time source adapter for org doctrine packs.

    Implementations pull governance artifacts from a remote location and
    write a validated snapshot to ``target_dir``.  No network calls are made
    after this method returns.
    """

    def fetch(self, target_dir: Path) -> FetchResult:
        """Materialise a doctrine snapshot at ``target_dir``.

        Implementations MUST be idempotent: calling ``fetch`` on a populated
        ``target_dir`` should refresh the snapshot in place (or be wrapped
        by :func:`specify_cli.doctrine.snapshot.write_snapshot` for atomic
        replace semantics).
        """
        ...
