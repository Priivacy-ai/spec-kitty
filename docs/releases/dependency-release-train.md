# Dependency Release Train

This release train prevents CLI releases from shipping with unlicensed or non-reproducible dependency pins.

## Order

1. Release `spec-kitty-events` with clear MIT metadata on PyPI.
2. Release `spec-kitty-runtime` with clear MIT metadata on PyPI (if used by CLI).
3. Release `spec-kitty-tracker` with clear MIT metadata on PyPI (if used by CLI).
4. Release `spec-kitty-cli` with exact `==` pins to the versions above.

## Required Checks

- `scripts/release/validate_dependency_matrix.py`
- `scripts/release/validate_dependency_policy.py`
- `scripts/release/validate_distribution_metadata.py`

## Compatibility Matrix Maintenance

Update [dependency-compatibility-matrix.toml](dependency-compatibility-matrix.toml) in every release PR:

- Add a new `[cli."X.Y.Z".dependencies]` section.
- Add a new `[cli."X.Y.Z".train]` section and set all release-train libraries:
  - `spec-kitty-events`
  - `spec-kitty-runtime` (`not-used` when not bundled)
  - `spec-kitty-tracker` (use concrete version even when embedded)
- Record every `spec-kitty-*` dependency used by CLI.
- Keep `release_train.order` unchanged unless release ownership changes.

## Exception Policy

Non-PyPI direct references and prerelease dependency pins are blocked by default.
They are only allowed for a specific release when an explicit CI approval secret is set.
