# S2083 path-injection BLOCKERs — false-positive rationale (WP03)

**Verdict: all 3 SonarCloud `pythonsecurity:S2083` BLOCKERs are false positives.** Each write sink is
contained by existing, regression-locked sanitizers that SonarCloud's taint tracker does not model as
sanitizers. No code change is warranted (adding another guard would be theatre — and, per site 3
evidence, an inline guard one line above the sink is already ignored by Sonar). **Resolution: mark each
as False Positive in the SonarCloud UI** (operator action), citing the rationale below. This is
legitimate issue triage, not an in-code suppression — the charter treats code fix and hotspot review as
separate actions.

Containment verified: `pytest tests/merge/test_bookkeeping_projection_seam.py
tests/specify_cli/skills/test_verifier.py -k "traversal or untrusted or symlink or safe_path or within
or refus"` → **7 passed**.

## Site 1 — `src/specify_cli/merge/bookkeeping_projection.py:212`

`path.write_bytes(original)` in `_restore_optional_bytes`. The target is produced by
`_assert_status_path_within_target_surface(...)`, which runs `assert_safe_path_segment(mission_slug)`
(rejects `..`, `/`, `\`, absolute, leading-dot; `core/paths.py:40`) and then
`ensure_within_any(candidate, roots=[surface_root])` (`core/utils.py:105`, raises unless the resolved
path stays under the target surface). The leaf filename is a module constant; `original` is bytes
re-read from the already-validated target. The only dynamic segment (`mission_slug`, ultimately the CLI
`--mission` handle) is validated before composition. Adversarial: `spec-kitty merge --mission
"../../etc/foo"` → `assert_safe_path_segment` raises before any write. Regression:
`tests/merge/test_bookkeeping_projection_seam.py:44` (rejects `../escape`), `:118` (untrusted surface).

## Site 2 — `src/specify_cli/merge/bookkeeping_projection.py:346`

`trusted_target_status_path.write_bytes(source_status_bytes)`. Target path: same
`_assert_status_path_within_target_surface` containment as site 1. Source path
(`_assert_status_surface_file_path_is_trusted`): SSOT classifier gate on the basename, symlink refusal,
and `ensure_within_any(files=[<events>, <status>])` allowlisting exactly two constant basenames. Both
the path and the source are contained. Regression: `test_bookkeeping_projection_seam.py:118`,
`:128` (refuses untrusted status filename).

## Site 3 — `src/specify_cli/skills/verifier.py:402`

`safe_dest.write_text(...)`. `dest` passes a four-layer guard before use: `os.path.normpath`
(`_project_managed_path`), `is_relative_to(project_path.resolve())` (`:242`), `is_external_symlink`
(twice), and `ensure_within_directory(dest, project_root)` (`:399`, resolves and raises if outside the
root). The path segment originates in the on-disk managed-skill manifest `installed_path`; the guards
specifically block escaping `project_root`. Written content is trusted registry data. Regression:
`tests/specify_cli/skills/test_verifier.py:450` ("Unsafe path"), `:463` (`repaired == 0` on traversal),
`:298` (refuses external-symlinked ancestor). **Note:** `ensure_within_directory` at `:399` is
intraprocedural — one line above the sink — yet Sonar still flags, direct evidence that Sonar does not
recognize this project's sanitizers.

## Action for the operator

Mark issues `AZ_...` for these three sinks as **False Positive** in the SonarCloud UI
(`https://sonarcloud.io/project/issues?impactSeverities=BLOCKER&id=Priivacy-ai_spec-kitty`), pasting
the matching rationale above. SC-002 (0 open BLOCKER) clears via this UI action, not via a code change.
