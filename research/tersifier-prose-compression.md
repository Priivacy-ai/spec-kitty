# Tersifier: token-compressed delivery of prose templates (research)

**Status: research prototype. Default-off behind `SPEC_KITTY_TERSIFY`. Not intended for merge.**

## Idea

Templates, skills, and prompts stay authored in full prose. At the three
LLM-delivery choke points — slash-command rendering
(`template/asset_generator.py`), Agent-Skills rendering
(`skills/command_renderer.py`), and `spec-kitty next` prompt assembly
(`runtime/next/prompt_builder.py`) — `specify_cli.tersify.tersify_for_llm()`
serves a reduced version, with a legend for any non-obvious shorthand.

Two layers:

1. **Hand-tersified cache** — a whole-file terse rewrite stored at
   `<dir>/terse/<name>.terse.md`, keyed by the SHA-256 of the prose source.
   Stale hash → automatic fallback, so an outdated terse copy is never served.
   Scaffold with `PYTHONPATH=src python scripts/tersify_report.py --scaffold <file>`.
2. **Dictionary pass** — deterministic multi-word phrase collapses and filler
   deletions, every entry vetted with a real tokenizer (o200k_base) and kept
   only at ≥ +1 token per application. Character shorthand ("meeting"→"mtg")
   measured at 0 or **negative** savings and is deliberately absent.

Protected byte-for-byte in both layers (enforced by
`tests/specify_cli/test_tersify.py` over the whole bundled corpus): code
fences and inline code, indented code blocks, tables, YAML frontmatter,
`{SCRIPT}`/`{{jinja}}`/`$ARGUMENTS`/`__AGENT__`/`<handle>` placeholders, HTML
comments (SPDD + version markers), headings, and `spec-kitty`/`uv run`/`python`
invocation lines.

## Measurements (o200k_base tokens, `scripts/tersify_report.py`)

- Dictionary pass over the real corpus (12 mission-step prompts, 14 doctrine
  skills, 57 doctrine templates): **0.0–0.4% saved**. Spec-kitty templates are
  already terse, imperative technical writing — the generic-filler dictionary
  barely fires.
- Hand-tersified demo (`accept/prompt.md`): **19.1% saved** (614 → 497). Below
  the ~40–50% seen on conversational prose because most of the file is
  protected structure (fences, headings, commands) — the incompressible-payload
  ceiling.

## Conclusions so far

The dictionary layer is not worth running on this corpus; its value is the
audit methodology (token-delta vetting) and the protection machinery. If this
direction is pursued, the leverage is the hand layer applied to the largest
prompts (`specify` ≈ 7.6k tokens, `tasks` ≈ 7.4k) — at ~19%, roughly 1.4k
tokens per delivery per file — multiplied by every configured agent and every
`next` invocation. Whether ~15–20% is worth a second artifact to maintain per
template (even hash-guarded and CI-verified) is the open question.
