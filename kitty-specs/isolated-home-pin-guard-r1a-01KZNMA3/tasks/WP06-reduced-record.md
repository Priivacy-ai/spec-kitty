---
work_package_id: WP06
title: 'The reduced record: the imported halt-path ADR, #3121, and the residuals R1a is honest about'
dependencies:
- WP05
requirement_refs:
- FR-008
- C-006
- C-008
- C-009
- C-010
- C-013
planning_base_branch: feat/isolated-home-pin-guard
merge_target_branch: feat/isolated-home-pin-guard
branch_strategy: Planning artifacts for this mission were generated on feat/isolated-home-pin-guard. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/isolated-home-pin-guard unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
- T029
- T030
history: []
agent_profile: curator-carla
authoritative_surface: docs/adr/3.x/
create_intent:
- docs/adr/3.x/2026-08-07-1-a-mission-halting-instrument-is-worth-its-cost.md
execution_mode: planning_artifact
owned_files:
- docs/adr/3.x/2026-08-07-1-a-mission-halting-instrument-is-worth-its-cost.md
role: curator
tags: []
task_type: curation
tracker_refs: []
---

# Work Package Prompt: WP06 (alias WP-d) – The reduced record: the imported halt-path ADR, #3121, and the residuals R1a is honest about

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `curator-carla`
- **Role**: `curator`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Import the halt-path ADR **verbatim** from the spike branch (never author a second record of one halt),
compose and post the #3121 update carrying **every** FR-008 item unconditionally, and write `record.md` —
the place where R1a states what it did **not** prove.

## Context

- **Plan concern**: IC-07 (the reduced record and the two corrections).
- **This WP writes the honest half of the Mission.** Every item in T030 is a claim R1a would otherwise be read
  as having proved. A missing residual is a false claim by omission.
- **C-013 is the binding constraint of this package**: **nothing is merged, no branch integration of any
  kind, no PR un-drafted, and `gh issue create` is FORBIDDEN.** `#2991`, `#3170`, `#3226` and `#2642` are
  **already filed** — **cite them by number, never re-file them**.
- **`spike/isolated-home-3121` is read-only and is left untouched.** Extraction is by `git show` only.
- **D-1 and D-2 are deferred to R1b** with the reason: both target files exist only on
  `spike/isolated-home-3121` and C-013 bars merging, so there is **no in-scope path** to either.

---

### Subtask T027: Import the halt-path ADR verbatim — do not author a second record of one halt

**Purpose**: One halt, one record. An imported artefact the importing Mission edits **stops being external
evidence**.

**Steps**:

1. **Verify the precondition**: the file **EXISTS** on `spike/isolated-home-3121` and is **ABSENT** on HEAD.
2. Extract by **`git show` only**:
   ```bash
   git show spike/isolated-home-3121:docs/adr/3.x/2026-08-07-1-a-mission-halting-instrument-is-worth-its-cost.md \
       > docs/adr/3.x/2026-08-07-1-a-mission-halting-instrument-is-worth-its-cost.md
   ```
   **No merge, no rebase, no cherry-pick, no branch integration of any kind (C-013).** The spike branch is
   **left untouched**.
3. Assert the landed file is **BYTE-IDENTICAL** to `git show spike/isolated-home-3121:<the same path>`.
4. **Record BOTH `sha256` values in the commit body**, following the pattern the M4 evidence import already
   set.
5. Confirm `spec.md`'s header citation **resolves after this subtask**.

**Files**: `docs/adr/3.x/2026-08-07-1-a-mission-halting-instrument-is-worth-its-cost.md` (imported, unmodified).

**Validation**: **Authoring a new ADR produces a different `sha256`**, and C-006 separately lists "the
halt-path ADR" as something R1a writes — so **without the byte-identity assertion R1a lands a second,
divergent record of one halt**.

**What this cannot see**: whether the ADR is still the right record.

---

### Subtask T028: Compose the #3121 update — every FR-008 item, unconditionally

**Purpose**: SC-009's item list. **A comment missing one item fails it.**

**Steps** — compose **one** comment body carrying **all** of:

1. The **THREE separately labelled reach figures** — **40/40 sites, 36/36 files, 40/191 of all pin sites** —
   **never one merged ratio**.
2. An explicit **RETRACTION of the struck 26.06%**.
3. The **census-is-not-a-manifest distinction** and its **reviewer test**, stated over **anything that makes a
   definition acceptable to the guard**, not over census rows alone.
4. **§0.3's provenance correction**, including the **authored-versus-committed distinction** and the
   **explicit refusal to state a growth rate**.
5. The statement that **R1a adjudicates NOTHING**.
6. And — **UNCONDITIONALLY, not only in the degraded band** — **`r`, `|R|`, `|R_f|`, both window SHAs, EVERY
   attempted window INCLUDING the VOID result at `709a59534` (`|R| = 3`), and the machine-readable band
   verdict**.
7. It also states plainly that **the window MOVED** and whether §0.3's `28 -> 30` figure is **RE-DERIVED** or
   **SUPERSEDED**, **in those words**.

**Files**: comment body drafted into `record.md` before posting (no new file).

**Validation**: **The first revision made the degraded band's publication obligation invisible by enumerating
four items that did not include `r`.** The DoD **is** the item list, and a comment missing any one of them
fails it.

**What this cannot see**: whether a reader will read it.

---

### Subtask T029: Post it, and make the posting recoverable

**Purpose**: A comment composed but not posted leaves no URL.

**Steps**:

1. Post with **`gh issue comment 3121`** — **NEVER `gh issue create`**, which C-013 bars and which would mint
   the very `owed_to` ambiguity OD-001 decided against.
2. **Record the returned comment URL in `record.md`**, so the publication is recoverable **from the Mission
   record** rather than only from GitHub.
3. **Nothing is merged, no PR is un-drafted, no `gh pr merge`.**

**Files**: `record.md` (append the comment URL).

**Validation**: The URL is in `record.md`.

**What this cannot see**: whether #3121 is the right issue for 40 distinct adjudications. **OD-001 decided
`#3121` and recorded the decision as reversible at zero cost**, because re-pointing `owed_to` is a
regeneration and the baseline hash is over the key set.

---

### Subtask T030: Record what R1a proved, what it did not, and what it hands to R1b

**Purpose**: `record.md` is where the Mission states **what it did not prove**. Every item below is a claim R1a
would otherwise be read as having proved.

**Steps** — state each as a **labelled item a reader can find without reading the spec**:

1. **C-014 limb (iii) remains VACUOUS** and is R1a's recorded residual, stated over **adopters R1a does not
   have**.
2. **SC-011 is PURE SHAPE** and **SC-012 carries the entire behavioural load alone**.
3. **SC-012 limb 2 is vacuous as specified**, and what makes it bite is **the negative control in WP03/T013b**.
4. **THE GATE'S POWER TO HALT THIS MISSION WAS SPENT WHEN `r` LEAKED** — say so **in those terms**, name the
   leaked values (**`r = 100%` at `|R| = 9, 33, 34` around ~300 / ~600 / ~2000 first-parent commits back**),
   and state that **what survives is a published measurement under a pre-committed rule whose stopping
   criterion never reads `r`**.
5. **THE VERDICT RESIDUAL IN ITS NARROWED HONEST FORM** — a collected test proves internal consistency, the
   band, **AND** that every **surviving end-SHA key recomputes to real content in this tree**; **only the
   START-SHA operands remain unprovable without git**.
6. **The named escapes with their measured populations**, and the **explicit statement that the enumeration is
   NOT claimed complete**.
7. **C-008** — `|P| = 5` is **not used, not inherited, not cited**, and **R1b MUST RE-RUN WP01 over the
   current class**, which is now **40 under a different predicate**.
8. **C-010** — **PR #3285 is R1b's coordination dependency, not an R1a blocker.**
9. **D-1 and D-2 deferred to R1b with the reason**: both target files exist only on
   `spike/isolated-home-3121` and **C-013 bars merging**.
10. **TG-1 through TG-4 for the operator to route, with NO issue created.**
11. **WP01's OWN FINDINGS, carried forward here because they live only in docstrings inside
    `_home_pin_scan.py`** — `record.md` is **this WP's owned file**, so WP01 could not write them and
    **nothing else owns carrying them**. A finding that lives only in a docstring is a finding the record does
    not have. Each as a labelled item:
    - the **`key_member` / `Attribution` contract deviation**;
    - **C-012(5)'s member-level substitution**, whose literal form **raises on 11 of 40** — verified
      independently in review;
    - the **`NEEDLE_BYTES` derivation** and the reason for it;
    - **`OWNER_PARAM_NAMES`'s PROVISIONAL status** until WP03/T012 binds the owner contract's declared fixture
      name to it — and whether that binding landed;
    - the **`_corpus` `lru_cache` staleness caveat**.
12. **The four framework defects met in planning, CITED NOT RE-FILED**: **`#2991`** (SC-\* refs dropped at the
    tasks-packages boundary), **`#3170`** (the requirement scraper reading prose), **`#3226`** / **`#2642`**
    (the tasks_outline exit guard masking a real failure).
12. **THE STANDING OBLIGATION THAT WP01/T004's REGISTRY TEST PARSES FR-007's TABLE OUT OF THIS MISSION's
    `spec.md`**, so **flattening or archiving the mission directory re-points a collected, always-on test**.
13. **THE RESIDUAL IN THE HALT ENFORCEMENT** — the lane machine blocks downstream WPs **only if an implementer
    performs two transitions correctly** (leave WP-0b at `for_review`, move WP03..WP06 to `blocked`) **at the
    moment they have just learned the Mission is halting**, and **marking WP-0b `approved` out of habit opens
    the gate**; **the collected verdict test is the defence-in-depth behind that, not the enforcement**.
14. **Every pre-existing red met during implementation** with its **command, failure summary and merge-base
    evidence**, **ROUTED TO THE OPERATOR as a TG-item** (**C-009** — pre-existing reds are not this Mission's
    to fix) **because DIR-013's GitHub issue is the operator's to open and C-013 forbids the implementer
    opening it**.
15. **OD-003's measured runner figure with the contention headroom stated rather than assumed.**

Also carry forward into `record.md`: **the ordering evidence from WP03/T010**, **the pytest version from
WP03/T012**, and **the SC-002b figures from WP04/T020**.

**Files**: `record.md` (mission-directory artefact assigned to this WP, ~200 lines).

**Validation**: **Every item is a claim R1a would otherwise be read as having proved.**

**What this cannot see**: the residuals nobody wrote down.

---

## Definition of Done

Per-subtask completion is a `spec-kitty agent tasks mark-status <Txxx> --status done` event.

1. **The ADR is byte-identical to the spike-branch original**, with **both `sha256` values in the commit body**.
2. **#3121 carries every FR-008 item unconditionally, including the VOID window**, and **the comment URL is in
   `record.md`**.
3. **`record.md` states each residual as a labelled item**, including **the two vacuous criteria, the leak, and
   the narrowed verdict residual**; and **carries the ordering evidence from WP03/T010, the pytest version from
   WP03/T012, and the SC-002b figures from WP04/T020**.
4. **No issue was created; nothing was merged; no PR was un-drafted; the four framework defects are CITED by
   number, never re-filed.**

## Not Done If

- **A new halt-path ADR was authored instead of imported.**
- **The gate's outputs are published only in the degraded band**, or **the VOID window is omitted**.
- **The record still describes the gate as R1a's own stopping mechanism.**
- **`gh issue create` was run**, or **any branch integration occurred**.

## Risks

| Risk | Mitigation |
|---|---|
| The ADR gets "improved" during import. | Byte-identity assertion plus both `sha256` values in the commit body. **An imported artefact the importing Mission edits stops being external evidence.** |
| The #3121 comment quietly drops `r` because the band is not degraded. | **FR-008 is unconditional.** The DoD is the item list; check all seven items of T028 individually. |
| `gh issue create` looks like the right way to file TG-1..TG-4. | **C-013 forbids it.** TG items are routed to the **operator**, who opens anything that needs opening. |
| A residual is left unwritten because it is embarrassing. | The leak, the two vacuous criteria and the procedural halt enforcement are the **three most embarrassing** items and are the three most explicitly required. |
| The spike branch is touched. | `git show` only. No merge, no rebase, no cherry-pick. |

## Reviewer Guidance

- **Diff the ADR against `git show spike/isolated-home-3121:<path>` yourself.** A one-character "tidy" makes it
  a second record.
- **Count T028's items: seven.** The historically-dropped one is `r`.
- **Read `record.md` for the three items a Mission is least likely to write down**: the leak (item 4), the two
  vacuous criteria (items 1-3), and the **procedural** halt enforcement (item 13).
- Confirm the four framework defect numbers appear as **citations**, and that no issue was created.

## Implementation

```bash
spec-kitty agent action implement WP06 --agent <name>
```
