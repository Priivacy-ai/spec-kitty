# Author and read charter policy in an owned checkout

Charter commands normally resolve the repository's primary checkout. When working
in a linked worktree, explicitly select that checkout to author and read its
policy:

```sh
spec-kitty charter new directive PROJECT_RELEASE_EVIDENCE --owned-checkout "$PWD"
# Author complete rules and validate the scaffold before activation.
spec-kitty charter activate directive PROJECT_RELEASE_EVIDENCE --repo-root "$PWD"
spec-kitty charter context --owned-checkout "$PWD" --action implement --json --no-mark-loaded
```

Run these commands from within the same repository. The path must name the Git
checkout root; an absolute path also works when the current directory is nested
inside that checkout. `spec-kitty doctrine new` accepts the same selection flag.
Selection does not activate new artifacts automatically: register the artifact
in the project's charter and use the normal activation workflow.

Ownership validation rejects missing directories, nested directories passed as
checkout roots, and checkouts from another repository. Doctrine output must stay
within the selected checkout, including when using a pack or symlinked path.
Text, JSON, and `--include` context use the same selected charter. Selection lasts
for one command and does not change repository identity or later default calls.

Without `--owned-checkout`, existing primary-checkout behavior remains unchanged.
These commands provide source-authority evidence; they do not establish that a
deployed service or a different installed CLI has consumed the policy.
