# Contract: Exhaustive Current-Tree Occurrence Inventory

**Produces**: `inventory-hits.tsv` (ephemeral, untracked), `inventory.md` (committed)
**Consumes**: WP01 `implementation-baseline.json`, accepted ADR
**Terminal use**: M6 exact zero audit
**Fixed exclusion roots (four)**: `kitty-specs/`, `.kittify/migrations/mission-state/quarantine/`,
`kitty-ops/`, `.kittify/missions/` — the immutable historical-record set
(`DM-01M0NMS9WPH33EPFCJQRTQVNSA`, amended by `DM-01M0P6C8C7Q6SPBT412V39RPN0` to add the three record
roots alongside the archive). Each is an operator-fixed audit boundary applied identically in both modes
via its own `:(top,exclude)<root>` pathspec / ls-tree prefix drop — never a class, allowlist, baseline, or
X value, and never an allowlist mechanism (four independent exclude pathspecs, not an include list). No
wave renames a slug/directory or edits/renames a pre-existing path under any of the four; runtime may keep
appending new records to them. Omitting any of the four, or adding any other, is an audit error.

## Frozen base

Before WP01's first edit, WP01 fetches `origin/main`, requires that exact tip is incorporated, and
atomically writes `target_ref`, 40-character `target_tip`, `implementation_base`, capture commands,
timestamp, actor, and `wp_id=WP01` to `implementation-baseline.json`. WP02–WP05 use that immutable target
tip and never refetch/repoint it. Incorporating another target invalidates evidence and requires the
documented fresh-branch, planning-commit replay, WP01 restart.

## Canonical audits

Both audits run as one Python process using `subprocess.run(..., stdout=PIPE, stderr=PIPE)`; a shell
pipeline is forbidden. The process constructs the token as
`bytes((100,111,99,116,114,105,110,101))` and accepts `base_commit` plus
`mode in {inventory,terminal}`. **It runs at the repository toplevel only**: it first runs
`git rev-parse --show-prefix` and treats any non-empty output (a subdirectory cwd) as an audit error — never
as zero — and records the resolved toplevel, `git --version`, and the resolved lowercase commit OID
(`git rev-parse --verify <base_commit>^{commit}`) in the audit record. (Squad finding, 2026-08-23: a
cwd-relative pathspec reports zero from any token-free subdirectory; the `:(top)` anchoring and
`--full-tree` below close that hole; the frozen-base WP02 run was executed at the toplevel and is unaffected.)

The content subprocess executes exactly:

```python
["git", "grep", "-a", "-i", "-n", "-o", "--column", "--full-name", "-z",
 "-e", token.decode("ascii"), base_commit, "--", ":(top)",
 ":(top,exclude)kitty-specs/",
 ":(top,exclude).kittify/migrations/mission-state/quarantine/",
 ":(top,exclude)kitty-ops/",
 ":(top,exclude).kittify/missions/"]
```

(`:(top)` anchors the pathspec at the repository root regardless of cwd; the four
`:(top,exclude)<root>` pathspecs are the fixed exclusion roots. Verified live: identical record counts
from the toplevel and from a subdirectory; the former `-- . ':(exclude)kitty-specs/'` single-root form is
retired for the terminal gate — the WP02 frozen-base inventory used it at the toplevel, where the two
forms are equivalent for that single root.)

It writes captured stderr through unchanged. Return code `0` is valid only with non-empty stdout and means
hits; return code `1` is valid only with empty stdout and means no hits; return code `>1`, signal failure,
or either return-code/stdout inconsistency is an audit error. Inventory mode emits stdout and succeeds for
valid rc 0 or 1. Terminal mode emits hits and returns failure for rc 0, succeeds only for rc 1, and returns
a distinct audit-error failure for rc >1/inconsistency. Thus expected no-match rc 1 is never confused with
an execution error. For rc 0, parse raw bytes **structurally**: each record is
`tree-prefixed-path NUL decimal-line NUL decimal-column NUL exact-match LF`; locate the trailing
`NUL digits NUL digits NUL match LF` suffix and take every byte before it as the path, so a pathname that
itself contains LF (or NUL-unsafe bytes) is parsed, never rejected. Require the first field to begin with
exactly `base_commit.encode() + b":"`, strip only that prefix, require positive ASCII line/column and
`exact_match.lower() == token`, and reject truncation, extra bytes, or malformed fields. Never split on
colon: path bytes may contain colon, tab, newline, or non-UTF-8 bytes. Percent-encode every path byte
outside ASCII unreserved `[A-Za-z0-9._~-]` (and `%`) using uppercase hex before TSV output. `ordinal` is
the 1-based count for the exact decoded `(path,line,column)` coordinate in raw-record order (for this token
`-o --column` yields distinct columns, so `ordinal` is structurally always 1; it stays contractual). Resolve
the tree with a checked `git rev-parse --verify <base_commit>^{tree}` and preserve its validated lowercase
ASCII hex OID (40 characters for SHA-1 or 64 for SHA-256).

The pathname subprocess executes exactly:

```python
["git", "ls-tree", "-r", "-z", "--full-tree", "--name-only", base_commit]
```

(`--full-tree` lists the whole tree regardless of cwd.) It checks return code before inspecting stdout; any
nonzero return code, signal failure, or missing NUL record framing (non-empty output must end in NUL; empty
output is valid) is an audit error. Only after rc 0 does it split bytes on NUL, drop every path whose raw
bytes start with `b"kitty-specs/"`, `b".kittify/migrations/mission-state/quarantine/"`, `b"kitty-ops/"`, or
`b".kittify/missions/"` (the four fixed exclusion roots; each counted separately as orientation), compare
`token in path.lower()` on the remainder without decoding, and emit matching paths NUL-delimited. Inventory
mode succeeds after emitting matches; terminal mode fails when the match list is non-empty and succeeds only
when empty.

Two further checked steps close escape classes that `git grep` does not see: (1) **symlink targets** — for
every `120000` entry of `git ls-tree -r -z --full-tree <base_commit>` outside the root, read the blob with
`git cat-file blob <oid>` and apply the token test to the target bytes (`test_symlink_target_audited`);
(2) **format-character/homoglyph evasion** — over every text blob outside the root, NFKC-normalise and strip
Unicode category `Cf`, soft hyphen and zero-width characters, then apply the token test
(`test_no_homoglyph_or_format_char_evasion`). Both must be zero in terminal mode; both are reported in
inventory mode. The audit record stores mode, toplevel, git version, argv, raw git rc, stdout/stderr
SHA-256, excluded-root content/pathname counts, commit/tree OIDs, and final result. Orientation counts
(including excluded-root counts) are never contractual.

## `inventory-hits.tsv`

Fixed UTF-8/LF header:

`hit_id	kind	path	line	column	ordinal	match_sha256	occurrence_class_id	surface_category	compatibility_registry_id`

- content coordinates include every match ordinal, including repeated matches on one line;
- pathname coordinates have empty line/column/ordinal and preserve path bytes using uppercase percent
  encoding for non-unreserved bytes so tabs/newlines/NUL-unsafe names remain one TSV field;
- `occurrence_class_id` is exactly one `OC-##`; `surface_category` is exactly S1–S10;
- `compatibility_registry_id` is empty or one `CR-##`; it annotates temporary compatibility and never
  excludes/duplicates the row;
- X1/X2/X3, ignored, historical, internal, intentional, generated, and exempt values are invalid.

### Deterministic `match_sha256`

For both row kinds, build this exact preimage and store lowercase
`hashlib.sha256(preimage).hexdigest()`:

```text
domain_tag || LP(kind) || LP(tree_oid) || LP(raw_path) || LP(line) ||
LP(column) || LP(ordinal) || LP(match)
```

- `domain_tag` is the 37 exact ASCII bytes `spec-kitty.terminology-hit.sha256.v1\0` and is not LP-framed.
- `LP(x)` is `len(x)` encoded as an unsigned 64-bit big-endian integer (`struct.pack(">Q", len(x))`),
  followed by the exact bytes `x`; lengths greater than `2^64-1` fail.
- `kind` is exactly ASCII `content` or `pathname`.
- `tree_oid` is the validated lowercase ASCII hex tree OID, never raw digest bytes or a commit/ref name.
- `raw_path` is the tree-relative undecoded pathname bytes after validated revision-prefix removal.
- For content, `line`, `column`, and `ordinal` are each their positive value encoded as an unsigned
  64-bit big-endian payload (`struct.pack(">Q", value)`), and `match` is the exact case-preserving matched
  bytes emitted by grep. Values outside `1..2^64-1` fail.
- For pathname, `line`, `column`, `ordinal`, and `match` are each the empty byte string, producing four
  consecutive zero-length LP fields. A pathname has one row regardless of repeated token substrings.

No decimal text, native-endian integer, normalized/case-folded match, percent-encoded path, commit OID,
or omitted empty field enters this digest. `test_inventory_match_sha256_byte_identical_reproduction` runs
two independent inventory processes over the same tree, including colon/tab/newline/non-UTF-8 path
fixtures and mixed-case/repeated content matches, and requires byte-identical TSV plus independently
recomputed content and pathname hashes.

Rows sort by `kind,path,line,column,ordinal`; IDs derive from order. Manifest rows must be set-equal to
both audit outputs. Duplicate/omitted/sampled/synthetic coordinates fail.

The TSV is ephemeral evidence (`DM-01M0NMSD60JYG7K7V5MJCKJ3P8`): WP02 writes it to the mission directory,
where the mission-local `.gitignore` keeps it untracked; it may be attached to the PR as an artifact.
`inventory.md` pins its SHA-256 and row count, and set equality is proven by regenerating it from the frozen
base with the recorded command and matching those values byte-for-byte (WP05 does this independently).

## `inventory.md`

It records:

1. frozen base, exact argv, raw git rc, stdout/stderr SHA-256, the TSV SHA-256 and row count, and the
   exact reproduction command;
2. manifest-derived totals by kind, S1–S10, and OC, plus per-excluded-root (`kitty-specs/`,
   `.kittify/migrations/mission-state/quarantine/`, `kitty-ops/`, `.kittify/missions/`) content and
   pathname counts as non-contractual orientation;
3. each OC's member set (= all TSV rows carrying that `occurrence_class_id`; the ID span is orientation
   only — spans interleave) and semantic seam;
4. CR candidates with disjoint source hit IDs, planned introduction, fixed/M2-map target, M6 removal,
   budget, control record, and named tests; source coordinates keep their introduction-wave OC owner,
   while later-created product/control coordinates are distinct M6-removal work;
5. scope statement: every internal code, history, test, fixture, metadata, generated-asset, ADR/docs
   archive and matching pathname hit outside the four fixed exclusion roots is work, never an exclusion;
   `kitty-specs/`, `.kittify/migrations/mission-state/quarantine/`, `kitty-ops/`, and `.kittify/missions/`
   are the four fixed exclusion roots and no pre-existing path under any of them is edited or renamed;
6. assignment-readiness statement: classes split wherever M1–M6 ownership would differ.

Assignment is authored only in `stacked-plan.md`, but its disjoint union must equal every manifest hit.
Current-repository hits cannot be externally deferred.

## Per-wave and terminal contract

Each M1–M6 mission freezes a fresh wave-local base, reruns the same audits, and owns an exact occurrence
map. M1–M5 may maintain temporary shrink-only fingerprints and registered CRs; they are transition proof,
not terminal exceptions. M6 deletes compatibility controls/baselines/allowlists and reruns against `HEAD`
with the same four fixed exclusion roots. Terminal content git subprocess must have empty stdout/raw
rc 1 and its wrapper must exit 0; pathname git subprocess must have raw rc 0 and yield zero paths after the
drop. Any hit, omitted or additional exclusion, git failure, malformed output, or wrapper that masks an
upstream return code blocks I6.

M6 uses `scripts/audit_retired_term_zero.py` with required check marker
`terminology-zero-current-tree`; command identity is
`python scripts/audit_retired_term_zero.py --commit <final-commit-oid> --mode terminal --json -`; exit `0`
= both audits zero, `1` = hits, `2` = audit/input/git error (including a non-toplevel cwd; usage errors are
not exit 2 — they use a distinct code). It executes exactly the argv/drop/symlink/normalised checks above; a
pathspec that differs from this contract fails. Its stdout-only external JSON attestation stores object
format, the resolved toplevel, `git --version`, resolved lowercase **commit** and tree OIDs, argv, raw
return codes, stdout/stderr hashes, counts, and result. Any tree mutation makes evidence stale; CI/release
merge/publish gates rerun terminal mode against the final result tree; **no earlier working-tree or
parent-commit zero result authorizes merge or publication.** The entrypoint never writes to the audited
repository.

Named tests: `test_content_audit_accepts_rc1_empty_only`, `test_content_audit_rejects_git_rc_gt1`,
`test_path_audit_propagates_ls_tree_failure`, `test_symlink_target_audited`,
`test_no_homoglyph_or_format_char_evasion`. Required mutations: `mutation_git_audit_failure_cannot_pass_zero`
substitutes a failing git executable and an invalid commit for each subprocess;
`mutation_subdir_cwd_cannot_pass_zero` runs both modes from a token-free subdirectory of a tree that has
hits; inventory and terminal modes must fail before any zero count/result is recorded. The hostile-path
fixture of `test_inventory_match_sha256_byte_identical_reproduction` includes a pathname containing LF.
