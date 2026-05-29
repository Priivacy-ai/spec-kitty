module.exports = {
  defaultIgnores: true,
  // spec-kitty auto-generates mission lifecycle commits that don't use
  // conventional-commit format. Ignore them rather than requiring every
  // planning command to produce a typed subject line.
  ignores: [
    (commit) =>
      /^(Add|Update) (meta|spec|tasks|plan) for (feature|mission) /.test(
        commit
      ),
  ],
  rules: {
    "type-enum": [
      2,
      "always",
      [
        "build",
        "chore",
        "ci",
        "docs",
        "feat",
        "fix",
        "lint",
        "perf",
        "plan",
        "refactor",
        "revert",
        "spec",
        "style",
        "test",
      ],
    ],
    "type-case": [2, "always", "lower-case"],
    "type-empty": [2, "never"],
    "subject-empty": [2, "never"],
  },
};
