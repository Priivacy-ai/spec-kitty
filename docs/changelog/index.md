---
title: Changelog
description: 'Changelog landing page: points to the canonical docs/changelog/CHANGELOG.md and explains the root CHANGELOG.md symlink that release tooling reads.'
doc_status: active
updated: '2026-07-04'
related:
- docs/changelog/CHANGELOG.md
- docs/plans/3-2-x-milestone-roadmap.md
- docs/release-goals/index.md
---
# Changelog

The canonical Spec Kitty changelog lives in this section as
[`CHANGELOG.md`](CHANGELOG.md) (Mission B, FR-009).

The repository-root `CHANGELOG.md` is a **symlink to this canonical copy**:
release tooling (`scripts/release/`, `pyproject.toml`,
`.github/release-readiness.yml`) reads the root path and is out of relocate
scope. Root is the symlink; `docs/changelog/CHANGELOG.md` is canonical.

For where the project is going next, see the
[release goals](../release-goals/index.md) and the
[3.2.x milestone roadmap](../plans/3-2-x-milestone-roadmap.md) (a plans/
working document under the distil-then-retire lifecycle).
