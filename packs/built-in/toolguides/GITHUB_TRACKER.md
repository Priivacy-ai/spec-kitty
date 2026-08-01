# GitHub Issue-Tracker Operations — `gh` CLI + GraphQL

**⚠️ READ THIS before bulk tracker work** (re-parenting, type/priority audits,
dedup sweeps). These are the mechanics and the gotchas that silently waste hours.

This guide covers driving the GitHub issue tracker from the CLI: native
sub-issues (the parent/child source of truth), issue types, walking the parent
chain, auth, and the rate-limit and id-confusion traps. It is the operational
companion to the **Planning & Tracking Styleguide**.

---

## Auth

- **`unset GITHUB_TOKEN` before `gh` calls on org repos.** The ambient
  `GITHUB_TOKEN` often has limited scopes (`Missing required token scopes`).
  Unsetting it falls back to the keyring `gho_*` token with full `repo` scope.
- **Background shells lack keyring auth.** `gh` invoked in a backgrounded shell
  returns empty or fails silently — the keyring is not available there. Run
  `gh` loops in the foreground.

---

## Sub-issues — the native parent/child source of truth

Native sub-issues, not body checklists, are the authoritative parent/child
graph. Body checklists are invisible to tooling — backfill native links.

- **Add a child (REST):** `POST /repos/{owner}/{repo}/issues/{parent}/sub_issues`
  (note the **plural** `sub_issues`).
- **Remove a child (REST):** `DELETE /repos/{owner}/{repo}/issues/{parent}/sub_issue`
  (note the **singular** `sub_issue`).
- **`sub_issue_id` must be the integer database `id`, NOT the issue number.**
  Pass it with **`-F sub_issue_id=<id>`** (capital `F` = typed/number). `-f`
  sends a string and fails with `422 "not of type integer"`.
- **Get the database id:** `gh api repos/{owner}/{repo}/issues/{n} --jq '.id'`.
- **Single-parent constraint.** An issue may have only one parent. To move it,
  `DELETE` from the old parent *then* `POST` to the new. Re-adding without
  removing fails with `422 "Sub issue may only have one parent"` /
  `"duplicate sub-issues"`.
- **Reading children:**
  `gh api repos/{owner}/{repo}/issues/{n}/sub_issues --paginate --jq '.[].number'`.
  **`--paginate` is mandatory** — the default page size is 30; epics with more
  children silently truncate without it (a frequent cause of a false
  "not linked" reading).
- **Nesting is allowed** (epic -> sub-epic -> leaf) — useful for tiered
  hierarchies.

---

## Reading the parent / walking the chain

- **`.parent` is reliable only via GraphQL, not REST.** REST `issue.parent`
  returns `null` even when a parent exists. The authoritative reads are the
  `sub_issues` listing (downward) and GraphQL `parent` (upward).
- **Walk upward** with nested `parent`, then take the last non-null as the root:

  ```graphql
  issue(number: $n) {
    parent { number parent { number parent { number } } }
  }
  ```

---

## Issue types (Task / Bug / Feature)

> Note: "Feature" below is the **GitHub issue-type** value — the tracker's own
> classification vocabulary — not the Spec Kitty Mission domain object.

- Type ids are **per-repo**; fetch them:
  `{ repository { issueTypes(first: 20) { nodes { id name } } } }`.
- **Set a type** via GraphQL mutation, using the **GraphQL node id** (`I_…`):

  ```graphql
  mutation {
    updateIssue(input: { id: "<node_id>", issueTypeId: "<type_id>" }) {
      issue { number }
    }
  }
  ```

- **Search by type works:**
  `gh search issues 'type:Bug' --repo <owner>/<repo> --state open` — useful for
  type/label consistency audits.

### ⚠️ Two different `.id`s — the trap that bites repeatedly

- REST `gh api repos/{owner}/{repo}/issues/{n} --jq '.id'` returns the
  **database id** (a big integer, e.g. `4607444833`) — that is what
  `sub_issue_id` wants.
- `updateIssue` needs the **GraphQL node id** (`I_kwDO…`). Passing the REST
  `.id` to `updateIssue` fails with
  `NOT_FOUND "Could not resolve to a node with the global id"`.
- Get the node id from GraphQL (`issue(number: $n) { id }`) or from REST
  **`.node_id`** (not `.id`).

---

## GraphQL query gotchas (the big time-sinks)

- **Shell double-quote interpolation breaks queries.** Building
  `-f query="…issue(number:$n)…"` with escaped `\"` inside double quotes
  produces parser errors (`Expected NAME, actual: INT`). **Use GraphQL
  variables** — single-quote the query and pass the number typed:

  ```bash
  Q='query($n:Int!){repository(owner:"O",name:"R"){issue(number:$n){number parent{number}}}}'
  gh api graphql -F n=$n -f query="$Q"
  ```

- **Batched aliases starting with a digit fail.** `i$n:issue(...)` across many
  tickets throws parser errors; per-ticket variable queries are more robust than
  hand-built alias batches.
- **Do not interpolate `$n` into the `--jq` string.** Emit the number from the
  query result (`.number`) and let `jq` read it, avoiding nested-quote breakage.

---

## Rate-limiting and loops (critical for bulk work)

- **Rapid per-ticket loops trip GitHub *secondary* rate limits.** Those errors
  are hidden by `2>/dev/null`, so the loop produces **0 results silently** while
  an isolated single call still works moments later.
- **Mitigations:**
  - Throttle: `sleep 0.25`–`0.5` between calls; keep loops short.
  - Prefer **one REST `gh issue list --json …`** (a single call returning
    labels and dates) over N GraphQL calls when you only need list-level fields.
  - Reserve per-ticket GraphQL for the few tickets that genuinely need `parent`
    or `issueType`.
  - **Batched parent lookup:** scope a whole orphan-set in one aliased query
    rather than one call per ticket.
- **Do not trust an empty loop result** — verify with a single call before
  concluding "0" or "not linked".

### --paginate applies to all gh list surfaces

`--paginate` is not specific to sub-issue reads. Any `gh` command that returns a
paginated list (issues, labels, search results, API list endpoints) silently
truncates at the default page size (30 for most; 100 for `gh search issues`).
Always add `--paginate` when the full result set matters:

```bash
# All forms that need --paginate:
gh api repos/{owner}/{repo}/issues/{n}/sub_issues --paginate --jq '.[].number'
gh issue list --repo {owner}/{repo} --state open --paginate --json number,title,labels
gh label list --repo {owner}/{repo} --paginate --json name,description
gh api repos/{owner}/{repo}/labels --paginate --jq '.[].name'
```

Exception: `gh search issues` returns up to 100 items per call with `--limit` but
has a separate cap; verify with `--jq 'length'` when a known large set is expected.

---

## Handy one-call queries

- List + labels + dates in one shot:
  `gh issue list --repo <owner>/<repo> --state open --search "created:>=YYYY-MM-DD" --json number,title,createdAt,labels`.
- **Author association** (for community-precedence dedup): not available in
  `gh issue view --json` (the field is rejected). Use REST:
  `gh api repos/{owner}/{repo}/issues/{n} --jq '.author_association'`
  (`NONE` = community; `COLLABORATOR`/`CONTRIBUTOR` = core team).
- Labels: `gh label list --json name,description`;
  `gh label create <name> --color <hex> --description …`;
  `gh label delete <name> --yes` (deletion is **global** — removes the label
  from every issue, open and closed).
- Edit an issue:
  `gh issue edit <n> --add-label X --remove-label Y --title "…" --body-file path`.
- Close as superseded:
  `gh issue close <n> --reason "not planned" --comment "…"`.

---

## Pitfall quick-table

| Symptom | Cause | Fix |
|---|---|---|
| `422 not of type integer` on sub_issue | used `-f` / passed issue number | `-F sub_issue_id=<DB id>` |
| `422 may only have one parent` | re-add without remove | `DELETE` old parent first |
| Loop returns 0, single call works | secondary rate limit (errors hidden) | throttle; verify with a single call |
| Background `gh` empty / fails | no keyring auth in background shell | run in the foreground |
| `Expected NAME, actual INT` | shell-interpolated GraphQL query | GraphQL variables + single-quoted query |
| Epic "missing" a child | no `--paginate` (30-item page) | add `--paginate` |
| REST `.parent` null but child exists | REST parent is unreliable | use GraphQL `parent` |
| `updateIssue` -> `NOT_FOUND … global id` | passed REST `.id` (database id) | use GraphQL node id (`I_…`) / REST `.node_id` |
