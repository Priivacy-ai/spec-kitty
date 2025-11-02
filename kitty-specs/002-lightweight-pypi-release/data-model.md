# Data Model

## FeatureBranch
- **Responsibility**: Tracks release candidate work prior to merging into `main`.
- **Key Fields**:
  - `name` — short-lived branch name prefixed with issue/feature id (string).
  - `version_bump` — enum `{major, minor, patch}` selected for the upcoming release.
  - `checklist_status` — enum `{pending, ready, blocked}` summarising readiness checks.
  - `changelog_entry_ref` — path to the pending changelog section for the release.
  - `test_results` — link to CI job run verifying unit/integration coverage.
- **Validations**:
  - `version_bump` MUST be present before merge.
  - `checklist_status` MUST equal `ready` to merge into `main`.
- **State Transitions**:
  - `pending → blocked` when readiness script detects failures.
  - `blocked → ready` after maintainer resolves issues and reruns validation.
- **Relationships**:
  - Owns exactly one `ReleaseTag` once merged.
  - References latest `ManagedSecret` definition for credential guidance.

## ReleaseTag
- **Responsibility**: Semantic version tag that triggers the publish workflow.
- **Key Fields**:
  - `name` — string matching regex `^v\d+\.\d+\.\d+$`.
  - `git_commit_sha` — commit identifier the tag annotates.
  - `derived_version` — semantic version extracted from `pyproject.toml`.
  - `release_notes_ref` — pointer to changelog section for this version.
- **Validations**:
  - `name` MUST equal `derived_version` prefixed with `v`.
  - Tag MUST point to a commit on `main`.
  - Changelog entry for `release_notes_ref` MUST exist.
- **Relationships**:
  - Generated from a single `FeatureBranch` merge.
  - Produces one `PyPIArtifact` bundle.

## PyPIArtifact
- **Responsibility**: Wheel and sdist published to PyPI.
- **Key Fields**:
  - `artifact_type` — enum `{wheel, sdist}`.
  - `filename` — generated distribution filename.
  - `sha256` — checksum for distribution integrity.
  - `upload_time` — timestamp recorded by PyPI.
  - `repository_url` — https://pypi.org/project/spec-kitty-cli/.
- **Validations**:
  - Built artifacts MUST derive from the tagged commit.
  - Metadata MUST include changelog URL and project description.
- **Relationships**:
  - Created by the publish job associated with a `ReleaseTag`.
  - Depends on `ManagedSecret` to authenticate upload.

## ManagedSecret
- **Responsibility**: Secure storage reference for credentials.
- **Key Fields**:
  - `provider` — GitHub Actions.
  - `name` — `PYPI_API_TOKEN`.
  - `rotation_policy` — recommended rotation cadence (e.g., 90 days).
  - `creation_steps` — documented manual steps for token generation.
  - `last_rotated` — optional field maintained by maintainer.
- **Validations**:
  - Secret MUST NOT be committed to the repository.
  - Workflows MUST access credentials via secrets context.
- **Relationships**:
  - Referenced by release workflow job and readiness documentation.
