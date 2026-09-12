---
work_package_id: WP03
title: Path-injection security hotspots (S2083 x3)
dependencies: []
requirement_refs:
- C-001
- FR-001
- NFR-001
- NFR-002
planning_base_branch: fix/sonar-bug-blocker-remediation
merge_target_branch: fix/sonar-bug-blocker-remediation
branch_strategy: Planning artifacts for this mission were generated on fix/sonar-bug-blocker-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/sonar-bug-blocker-remediation unless the human explicitly redirects the landing branch.
created_at: '2026-08-10T15:05:00+00:00'
subtasks:
- T007
- T008
phase: Investigate stream - security
history:
- at: '2026-08-10T15:05:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/merge/bookkeeping_projection.py
- src/specify_cli/skills/verifier.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its
guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

---

## Objective

Resolve the 3 SonarCloud **S2083** BLOCKER security issues ("Change this code to not construct the path
from user-controlled data"). Each is a filesystem path built (partly) from a value Sonar's taint
analysis traces to an external/user-influenced source — a path-traversal exposure if the value can
contain `..` or an absolute path.

This is an **investigate** WP: the fix is not uniform. First classify each site, then apply the
matching remedy. **Never** silence with a suppression.

## Per-site method

1. **Trace the taint source.** Follow the flagged path component back to where it enters the process.
   Classify it:
   - **External/user-controlled** (CLI arg, env var, tracker/API payload, file contents parsed from an
     untrusted source, a mission handle a user typed) → **contain it** (FR-001).
   - **Trusted repo/mission-internal** (a value derived from the resolved repo root, a validated
     `mission_id`/`mid8`, a constant, an already-validated lane id) → **trusted-local exemption**
     (C-001): keep the semantics, add a short comment + PR rationale explaining why the source is
     trusted. Do NOT add sanitization theatre.
2. **Containment pattern** (for the external case):
   - Reject or reduce traversal: forbid `..` segments and absolute components; normalize with
     `os.path.normpath` / `Path` and assert the resolved path stays under the intended base
     (`resolved.is_relative_to(base)` on 3.11+), raising a clear error otherwise.
   - Prefer an allowlist (known set of names) over blocklisting characters when the value space is
     small (e.g. a known WP id / lane id shape).
3. **Test the remedy** (C-002): add a focused test — a traversal input (`../../etc/x`, an absolute
   path) is rejected/anchored; a legitimate input still resolves correctly.

## Subtasks

### T007 — bookkeeping_projection path construction (2 sites)

- `src/specify_cli/merge/bookkeeping_projection.py:212`
- `src/specify_cli/merge/bookkeeping_projection.py:346`

These build paths during merge bookkeeping projection. Trace what feeds the path segment at each line
(likely a mission/WP/lane identifier or a feature-dir name). If it is an already-validated internal
identifier, apply the C-001 exemption with rationale; if any part is user-supplied and unvalidated,
anchor the path under the intended base and reject traversal, with a test.

### T008 — skills/verifier path construction (1 site)

- `src/specify_cli/skills/verifier.py:402`

The skills verifier builds a path (likely to a skill/command artifact). Trace the segment source;
contain-or-exempt per the method above, with a test for the contained case.

## Squad findings (AUTHORITATIVE — a pre-implementation security squad traced every site; operator decision applied)

**All 3 S2083 sites are VERIFIED FALSE POSITIVES.** A taint trace confirmed each sink is contained by
existing, regression-locked sanitizers that Sonar's tracker does not model. The 7 containment tests
already pass (`tests/merge/test_bookkeeping_projection_seam.py` + `tests/specify_cli/skills/test_verifier.py`,
traversal/untrusted/symlink cases). **Operator decision: DOCUMENT the rationale + operator marks each
False Positive in the SonarCloud UI. NO code change — do not add sanitization (it would be theatre and,
per `verifier.py:399`, an inline guard one line above the sink is already ignored by Sonar).**

This WP therefore produces **no source edit**. Its deliverable is a written rationale artifact + the
regression-test confirmation. Do NOT modify `bookkeeping_projection.py` or `verifier.py`.

Per-site rationale to record (verbatim basis for the PR body + SonarCloud FP comment):

1. **`merge/bookkeeping_projection.py:212`** (`path.write_bytes(original)` in `_restore_optional_bytes`).
   Target is `_assert_status_path_within_target_surface(...)` → `assert_safe_path_segment(mission_slug)`
   (rejects `..`/`/`/`\`/absolute) + `ensure_within_any(roots=[surface_root])`; leaf is a module
   constant; `original` is re-read from the validated target. Adversarial: `--mission "../../etc/foo"`
   → `assert_safe_path_segment` raises before any write (test_bookkeeping_projection_seam.py:44,118).
2. **`merge/bookkeeping_projection.py:346`** (`trusted_target_status_path.write_bytes(source_status_bytes)`).
   Target path: same `_assert_status_path_within_target_surface` containment. Source path:
   `_assert_status_surface_file_path_is_trusted` (SSOT classifier gate + symlink refusal +
   `ensure_within_any(files=[events, status])` allowlist of two constant basenames). Tests: :118, :128.
3. **`skills/verifier.py:402`** (`safe_dest.write_text(...)`). `dest` passes a 4-layer guard:
   `os.path.normpath` → `is_relative_to(project_root)` (`:242`) → `is_external_symlink` ×2 →
   `ensure_within_directory(dest, project_root)` (`:399`). Written content is trusted registry data.
   Tests: test_verifier.py:450 (Unsafe path), :463 (repaired==0), :298 (external symlink refused).

## Subtasks (revised per squad + operator decision)

### T007 / T008 — verify containment + author false-positive rationale (NO code change)

1. Re-run the 7 containment tests and confirm green:
   `pytest tests/merge/test_bookkeeping_projection_seam.py tests/specify_cli/skills/test_verifier.py -k "traversal or untrusted or symlink or safe_path or within or refus"`.
2. Write the per-site rationale above into a mission artifact:
   `kitty-specs/sonar-bug-blocker-remediation-01KZP2P2/research/s2083-false-positive-rationale.md`
   (this is the WP's owned deliverable — update `owned_files`/`create_intent` accordingly).
3. The PR body must state the 3 S2083 BLOCKERs are false positives requiring SonarCloud UI
   False-Positive resolution by the operator (code fix and hotspot review are separate actions, per the
   charter) — so a later agent does not "fix" safe code, and SC-002 is understood to clear via the UI.

## Branch Strategy

Planning base and final merge target are both `fix/sonar-bug-blocker-remediation`. Consume the
workspace `spec-kitty implement` resolves from `lanes.json`.

## Definition of Done

- All 3 S2083 sites resolved: each is either contained (with a traversal-rejection test) or exempted as
  trusted-local (with a written rationale in code + PR body). No suppression.
- `ruff`/`mypy` clean on changed src; scoped tests green.
- The PR body records, per site, the classification (contained vs trusted-local) and why — Sonar
  hotspot review is a separate UI action; call out any residual needing UI sign-off (per charter).
- `move-task --to for_review` pre-review gate passes.

## Risks / reviewer guidance

- **Misclassification is the risk**: exempting a genuinely-external source as "trusted-local" leaves a
  real vulnerability. The reviewer must independently verify the taint trace for each exemption.
- Loopback/local-only guidance (charter): do not over-engineer sanitization onto a provably trusted
  internal identifier — but the burden of proof is on the trace, recorded in the PR.
