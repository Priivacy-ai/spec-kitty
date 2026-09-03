# Tooling friction — tasks-outline / tasks-packages phase

Recorded during `wps.yaml` + WP authoring (spec-kitty CLI 3.2.6rc4), per Standing Order #3. Both items
below are genuine tooling/process tensions, not silently resolved — see the mission report for how each
was actually handled in this pass.

## 1. `test_archive_root_byte_identical.py` conflicts with FR-009's contract-doc edits (confirmed, unresolved)

`tests/architectural/test_archive_root_byte_identical.py` freezes every file that existed under
`kitty-specs/` (among three other roots) at a FIXED historical commit (`_MISSION_BASE_REV = "fc4acaa897"`,
from an unrelated mission, `charter-authority-flip-01M14RB3`) — any Modify of a pre-existing file under that
root fails the gate; only ADDs of new paths are allowed (plus one unrelated, explicitly named exception
file).

**Confirmed live** (`git show fc4acaa897:<path>` for both files, run during tasks authoring): both
`kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/activation.md` and
`kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/charter-context.md` ALREADY EXISTED at that base
revision, and neither is in the test's `_APPEND_ONLY_SPINE_EXCEPTIONS` whitelist.

**Consequence**: FR-009 (this mission's spec, P2) requires editing both files. This test — while not one of
the two named architectural gates this mission's own NFR-005/plan.md section (f) scopes local verification
to — runs unconditionally in CI's always-on architectural pole on every PR regardless of path, per its own
header comment. **WP05's edits to these two files will trip this gate.**

**Not resolved by this session**: no code, test, or exception-list change was made to work around this. WP05's
prompt file (`tasks/WP05-docs-activation-authority.md`) instructs the implementing agent to make the FR-009
edits as specified, record this same finding, and state explicitly in the PR description that this specific
test is an expected, known red for this reason — an operator decision (extend the exception list? move the
contract docs to a non-frozen location? accept a permanent narrow exception?) is needed, not a unilateral
pick by an implementing agent.

## 2. `tasks.md` has zero freeform-prose capacity — several mission-brief-required statements had to live in WP prompt bodies instead

`generate_tasks_md_from_manifest` (`src/specify_cli/core/wps_manifest.py`) generates `tasks.md` **entirely
mechanically** from `wps.yaml`'s per-WP fields (title, dependencies, requirement_refs, plan_concern_refs,
owned_files, subtasks, prompt_file) — there is no notes/description/freeform field on `WorkPackageEntry`,
and the generator emits a fixed template with no prose-injection point.

**Consequence**: this mission's authoring brief asked for several mission-wide statements to be recorded
"in tasks.md" — whether the one-PR shape stays reviewable or should split; the plan.md section (a)
cross-WP chokepoint (WP01/WP02/WP03 all encode the same `None`-means-"all built-ins" semantic contract and
must not be reviewed for that question in isolation from each other); the plan.md section (f) gate table;
the plan.md section (g) baseline-capture prerequisite. None of these can literally live in the generated
`tasks.md` given the current generator.

**Handled by**: placing the equivalent content directly in the relevant WP prompt files instead (the actual
place a human/agent implementing or reviewing a WP will read it) — the one-PR-shape statement and baseline
capture appear in WP01/WP02/WP03's Context sections; the cross-WP chokepoint note is stated identically in
all three of WP01/WP02/WP03's Context sections so it surfaces regardless of which WP a reader opens first;
the gate table's load-bearing pieces (scoped pytest commands, marker discipline, TID251/Bandit awareness)
are folded into each test-adding WP's own Context section rather than reproduced as a single table anywhere.
This is a workable substitute, not a full equivalent — a reader who only skims `tasks.md` (never opening a
WP file) will not see any of this content. Flagged here in case a future mission wants `wps.yaml`/`tasks.md`
to gain an actual freeform per-WP or mission-level notes field.
