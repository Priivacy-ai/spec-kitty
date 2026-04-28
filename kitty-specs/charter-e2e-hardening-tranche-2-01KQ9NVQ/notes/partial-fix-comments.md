# Partial-fix comment drafts

**Status: NO PARTIAL FIXES.**

All six issues closed by this PR (`#839`, `#840`, `#841`, `#842`, `#843`, `#844`) are fully resolved by their respective work packages (WP02..WP07) and locked into the strict E2E by WP08. None require a partial-close comment.

Cross-check basis (per WP09 T043):

- WP02 (`#840`): `spec-kitty init` stamps both `schema_version` (positive int) and `schema_capabilities` in `.kittify/metadata.yaml`. Strict E2E asserts both keys post-init. Approved on lane-a.
- WP03 (`#839`): fixture synthesis under `SPEC_KITTY_FIXTURE_AUTO_STUB=1` writes canonical doctrine artifacts; strict E2E asserts `doctrine_path.is_dir()` and a non-empty file inventory. Approved on lane-a.
- WP04 (`#841`): `charter generate --json` envelope contains `next_step.action ∈ {git_add, no_action_required}`; on `git_add` the paths list is non-empty. Strict E2E asserts the contract and stages the listed paths. Approved on lane-a.
- WP05 (`#842`): `mark_invocation_succeeded` suppresses atexit diagnostic prints on success paths; every `--json` stdout in the E2E now parses with `json.loads(stdout)` on the full stream. Approved on lane-a.
- WP06 (`#844` / `#336` regression lock): `kind=step` envelopes always carry a non-empty resolvable `prompt_file` (`os.path.exists` asserted); `kind=blocked` carries a non-empty reason; `SKILL.md` workaround text removed; migration `m_3_2_5_fix_prompt_file_workaround.py` rewrites legacy per-agent copies at upgrade-time. Approved on lane-a.
- WP07 (`#843`): composed actions issued by `next` write paired started/completed profile-invocation records keyed by `invocation_id`; outcome on completed records is in canonical `{done, failed, abandoned}`. Strict E2E asserts pairing and outcome enum. Approved on lane-a.

No deviations were flagged in the lane-a implementer notes that escalate scope or partially close any of the six issues. If any reviewer of the upstream PR identifies a behavioral gap that justifies a partial-close, replace this note with a precise per-issue comment stating: which FR/aspect was fixed, which is deferred, the deferral reason, and the follow-up issue number.
