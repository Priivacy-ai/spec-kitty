# Changelog

The canonical Spec Kitty changelog lives in this section as
[`CHANGELOG.md`](CHANGELOG.md) (Mission B, FR-009).

The repository-root `CHANGELOG.md` **persists as an alias** kept byte-for-byte
in sync with this canonical copy: release tooling (`scripts/release/`,
`pyproject.toml`, `.github/release-readiness.yml`) reads the root path and is
out of relocate scope. Root is the alias; `docs/changelog/CHANGELOG.md` is
canonical.
