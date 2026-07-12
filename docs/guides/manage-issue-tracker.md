---
title: Managing the Issue Tracker
description: 'Conventions for the Spec Kitty issue tracker: functional epics versus meta-trackers, native sub-issue parenting, and blocked_by dependencies.'
doc_status: active
updated: '2026-07-12'
related:
- docs/guides/contributing.md
- docs/guides/keep-main-clean.md
- docs/guides/pr-landing.md
---

# Managing the Issue Tracker

This guide describes how Spec Kitty structures its GitHub issue tracker so the
work graph stays honest, machine-navigable, and free of the drift that
hand-maintained checklists cause. It is aimed at maintainers and agents doing
tracker hygiene — parenting issues, wiring dependencies, and pruning stale
rollups.

The rules exist because a misleading work graph is expensive: a real defect
parented under a release rollup is hidden when that rollup is closed, and a
dependency captured only as prose is invisible to every tool that reads the
tracker.

## Functional epics versus meta-trackers

The tracker has two distinct kinds of parent issue. Telling them apart is the
first decision in any hygiene pass.

- A **functional epic** is a real domain or slice of work. It owns
  **native GitHub sub-issue children**, carries the `epic` label, and has a
  body that describes the work (see [Epic bodies](#epic-bodies-describe-work-not-children)).
- A **meta-tracker** is a convenience rollup — a release go/no-go list, a
  stabilization checklist, or a dashboard view. It carries the `meta-tracker`
  label, its body is a checklist that *references* issues owned elsewhere, and
  it has **no native children of its own**.

**The distinguishing test is native children, not the title.** An issue titled
`Umbrella: …` that owns native sub-issues is a functional epic; an issue that
holds only a body checklist of items homed under other epics is a
meta-tracker. Judge by the sub-issue graph, never by the name.

Parent functional issues under functional epics only. Never parent a real
work item under a meta-tracker.

## Parent and child are native sub-issue links

Express the parent/child relationship as a **native GitHub sub-issue link**, not
as a `## Children` checklist in the parent's body. Body checklists duplicate the
relationship and silently drift out of sync.

Create a link (REST — `sub_issue_id` is the child's numeric **database** id, not
its issue number):

```bash
CID=$(gh api repos/OWNER/REPO/issues/<CHILD> --jq .id)
gh api --method POST repos/OWNER/REPO/issues/<PARENT>/sub_issues -F sub_issue_id="$CID"
```

Or via GraphQL (node ids, not numbers):

```bash
PID=$(gh api repos/OWNER/REPO/issues/<PARENT> --jq .node_id)
CID=$(gh api repos/OWNER/REPO/issues/<CHILD> --jq .node_id)
gh api graphql -f query='mutation($p:ID!,$c:ID!){addSubIssue(input:{issueId:$p,subIssueId:$c}){issue{number}}}' -f p="$PID" -f c="$CID"
```

List a parent's children with `gh api repos/OWNER/REPO/issues/<PARENT>/sub_issues`.

**Single-parent constraint.** GitHub allows an issue only one parent; a second
link attempt returns HTTP 422. To **reparent**, remove the old link first, then
add the new one:

```bash
gh api graphql -f query='mutation($p:ID!,$c:ID!){removeSubIssue(input:{issueId:$p,subIssueId:$c}){issue{number}}}' -f p="$OLD_PARENT_NODE" -f c="$CHILD_NODE"
gh api graphql -f query='mutation($p:ID!,$c:ID!){addSubIssue(input:{issueId:$p,subIssueId:$c}){issue{number}}}' -f p="$NEW_PARENT_NODE" -f c="$CHILD_NODE"
```

## Execution order is blocked_by, not prose

Encode sequencing as native `blocks` / `blocked_by` dependencies **between
children**, not as a `#A → #B → #C` sequence in the epic body. An epic body
should carry no ordering prose that a tool cannot read.

```bash
# REST — issue_id is the BLOCKING issue's numeric database id
gh api --method POST repos/OWNER/REPO/issues/<BLOCKED>/dependencies/blocked_by -F issue_id=<BLOCKER_DB_ID>

# GraphQL — issueId is the BLOCKED issue's node id
gh api graphql -f query='mutation($b:ID!,$k:ID!){addBlockedBy(input:{issueId:$b,blockingIssueId:$k}){issue{number}}}' -f b="$BLOCKED_NODE" -f k="$BLOCKER_NODE"
```

For a strangler sequence of children, wire each step `blocked_by` its
predecessor so the ready-to-start item is always unambiguous.

## Epic bodies describe work, not children

An epic body is a functional description, not a child enumeration. Every epic
body must convey:

- **Why** — the problem or motivation.
- **For whom** — which users or roles benefit.
- **Intended effect** — the outcome once the epic is done.

Preserve substantive rationale; drop mechanical checklists (the sub-issue graph
already records the children).

## Meta-tracker lifecycle

- Label a meta-tracker `meta-tracker`, never `epic`.
- Its body checklist is by design. Do **not** audit a meta-tracker for
  "no in-body children" and do **not** native-link its checklist entries — the
  real issues live under their own epics.
- **Close a meta-tracker once it holds zero native sub-issues.** Its purpose is
  spent when the work it references is tracked under proper epics. Close it with
  an audit comment, and explicitly note any residual free-text checklist items
  so nothing silently vanishes.

## Filing children from an epic

When you decompose an epic into issues:

- **Match the epic's own stated breakdown** — file exactly the slices the body
  names, in the order it names them. Do not invent scope the epic did not
  specify; flag anything too vague to file cleanly instead of guessing.
- **Ground each slice in the real code first.** If a named slice already shipped,
  record that with evidence rather than filing a phantom "to-do" ticket that
  misrepresents completed work as pending.

## See also

- [Contributing to Spec Kitty](contributing.md) — pull-request and maintainer workflow.
- [Keep main clean](keep-main-clean.md) — branch and merge discipline.
- [PR landing](pr-landing.md) — the fork-PR landing runbook.
