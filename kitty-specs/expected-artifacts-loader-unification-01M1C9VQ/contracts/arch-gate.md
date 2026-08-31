# Contract — bare-construction arch-gate (FR-011)

Close the "mirror loader regrows" defect class by construction (DIRECTIVE_043).

## What is forbidden

In production code (`src/`, excluding the canonical helper and the model's own
tests), NEITHER of these may appear:

- `ExpectedArtifactManifest.model_validate(`
- `ExpectedArtifactManifest(` (direct construction — because `from_yaml_file`
  proved `cls(**data)` bypasses a `model_validate`-only gate; FR-013 deletes that
  path and this gate keeps it dead).

## Allowlist (the ONLY permitted call sites)

- `charter/activation/manifest_loader.py` — the canonical loader (its org + built-in
  `model_validate` calls).
- The model's own definition module (`expected_artifact_manifest.py`) for
  internal construction if any.
- Test modules that deliberately construct the model directly
  (`tests/**` — direct-construction characterization), explicitly exempted.

## Non-vacuity requirements (charter DIRECTIVE_043)

1. **Concrete floor**: the gate asserts the allowlist has exactly the expected
   entries — not "0 or more".
2. **Self-mutation test**: a test that injects a forbidden call into a temp
   fixture and asserts the gate FAILS (proves the gate is not theater).
3. **Refactor-stable**: expressed as an AST/call-site allowlist keyed by module,
   not a brittle line-number match, so relocating the loader in a later refactor
   does not falsely trip it.
4. **Shrink-only**: the allowlist may only shrink in future missions (frozen
   baseline), never silently grow.

## Sequencing (hard constraint)

The gate's allowlist points at `charter/activation/manifest_loader.py`. It is
authored/enabled ONLY AFTER:
- FR-001 moves the canonical `model_validate` calls into charter, AND
- FR-004/FR-005/FR-006 delete the mirror `model_validate` calls, AND
- FR-013 deletes `from_yaml_file`.

Enabling it earlier trips on surviving mirrors or on the pre-relocation location.
