# Contract: the verdict-recording seam — MOVED

**This file is no longer the census.** It is a pointer, kept so that references in
`plan.md` and earlier revisions resolve to an explanation rather than to stale
scaffolding.

The census lives at **`tests/architectural/verdict_seam_census.yaml`**, folded there
by WP16 from per-concern fragments at `tests/architectural/census/verdict_seam_IC0N.yaml`
written by WP01, WP04 and WP08.

## Why it moved

`finalize-tasks` rejects any `owned_files` entry under `kitty-specs/`, with no
`planning_artifact` exemption. A census no work package can own is a census nothing
maintains.

The move is an improvement rather than a workaround. FR-020 requires the contract to
be the architectural check's **expected-set fixture** — its stated failure mode is
*"a prose file nothing consults would discharge this FR while going stale
immediately."* A markdown table in a spec directory was exactly that file. A YAML
fixture beside the check that loads it cannot go stale without reddening CI.

An earlier revision of this file also recorded "commits outside it with
retry-on-contention" as a settled decision for NFR-006. That mechanism was
subsequently **refuted** — `CommitRouterResult.status` is a closed four-value
`Literal` and an `index.lock` collision carries no distinguishable signal, so the
buildable form uses the existing `status.views.git_operation_in_progress()` probe.
See `plan.md`'s IC-05a risks and WP10.
