# Research Findings

## Decision: Build toolchain for PyPI artifacts
- **Rationale**: Using `python -m build` invokes the standard PyPA build frontend, producing both wheel and sdist artifacts while honoring the existing Hatchling backend declared in `pyproject.toml`. It keeps the workflow simple, widely supported, and avoids additional CLI dependencies.
- **Alternatives considered**: `hatch build` (redundant with `python -m build` and requires hatch CLI on runner), `poetry build` (would require migrating project metadata), manual `setup.py` invocation (deprecated, less reliable with modern backends).

## Decision: Publish action and credential hand-off
- **Rationale**: `pypa/gh-action-pypi-publish@release/v1` can accept a `PYPI_API_TOKEN` secret, handles uploading artifacts from the workflow, and is maintained by the PyPA team, aligning with the requirement to keep secrets out of the repository.
- **Alternatives considered**: Custom `twine upload` step (requires manual installation and more boilerplate), third-party release actions (added maintenance risk, not officially supported).

## Decision: Tag-triggering and version alignment
- **Rationale**: Requiring tags in the form `vMAJOR.MINOR.PATCH` keeps triggers deterministic, matches standard Python release conventions, and allows the workflow to derive the release version. A validation script comparing the tag, `pyproject.toml`, and `CHANGELOG.md` ensures failures surface before publishing.
- **Alternatives considered**: Publishing on every push to `main` (no manual control, increases accidental releases), manual workflow dispatch (contradicts the automation requirement), trusting maintainers to align versions without automation (risks mismatches noted in spec).

## Decision: Readiness checklist delivery
- **Rationale**: Documenting readiness steps in `docs/releases/readiness-checklist.md` keeps guidance version-controlled and accessible, while scripting shared validation (`scripts/release/validate_release.py`) gives parity between local checks and CI, addressing FR-002 and FR-003.
- **Alternatives considered**: Wiki or external docs (drifts from repo, harder to update), embedding instructions only in workflow logs (discoverability issues), relying solely on CI failures (slower feedback on feature branches).
