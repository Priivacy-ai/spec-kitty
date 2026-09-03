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

**Update — RESOLVED by operator ruling (tasks phase R4, `reviews/tasks.ruling.md`), not escalated further**:
the operator ruled from precedent (`charter-authority-flip-01M14RB3`, cited directly in
`tests/architectural/test_archive_root_byte_identical.py`'s own module docstring — "the correction belongs
in the live mission dossier, not the archive") that this is not a genuine tension needing a case-by-case
operator pick each time it recurs: the two frozen contract docs
(`kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/activation.md`,
`.../charter-context.md`) stay byte-identical, never edited. The FR-009 correction they would have carried
is instead written to a NEW file under this mission's own live dossier —
`kitty-specs/spdd-reasons-activation-split-brain-01M1K6VN/contracts-activation-authority-update.md` — an
ADD relative to `_MISSION_BASE_REV`, so the gate never fires against WP05's own edits. WP05's prompt file
(`tasks/WP05-docs-activation-authority.md`) was rewritten this round (R4) to reflect this: it no longer
instructs editing either frozen file, and its Definition of Done requires
`pytest tests/architectural/test_archive_root_byte_identical.py -q` to pass CLEAN before WP05's work is
committed, not to be reported as an expected red. Re-run live during this R4 fix round: 2 passed, zero
changes under `kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/`.

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
