"""Release preparation package for spec-kitty.

This package builds release artifacts (changelog draft, version bump, structured inputs)
from local filesystem artifacts only. No network calls are made (FR-014).

Public API:
  - version.propose_version(current, channel) -> str
  - changelog.build_changelog_block(repo_root, since_tag) -> tuple[str, list[str]]
  - payload.build_release_prep_payload(channel, repo_root) -> ReleasePrepPayload
  - payload.ReleasePrepPayload (dataclass)
"""

from .payload import ReleasePrepPayload, build_release_prep_payload
from .version import ReleaseChannel, propose_version

__all__ = [
    "ReleaseChannel",
    "ReleasePrepPayload",
    "build_release_prep_payload",
    "propose_version",
]
