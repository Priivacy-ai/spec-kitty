#!/usr/bin/env python3
"""AST lint rule against hand-rolled event dicts.

This script enforces the canonical-producer non-negotiable (C-007 in
`spec-kitty-mission-workflow.md`): all lifecycle event payloads must be
constructed through the canonical `spec_kitty_events` pydantic models, not
assembled by hand as `dict[str, Any]` shapes.

The rule operationalizes the post-rc14->rc22 drift-class intervention
(Priivacy-ai/spec-kitty#1248, part of the regression-prevention plan in
Priivacy-ai/spec-kitty#1247 and drift-class epic #1198). Reviewer attention
alone failed seven times in eight releases; CI enforcement closes that gap.

Violation classes
-----------------

CP001  ast.Dict literal whose keys include both string literal "event_type"
       and "payload", when the literal is NOT the argument to a call against
       a known-canonical constructor (suffixes: Payload, Envelope, Event;
       names: StatusEvent, EventEnvelope, LifecycleEvent).

CP002  ast.FunctionDef / AsyncFunctionDef whose annotated return type is
       `dict[str, Any]` (or `Dict[str, Any]`) AND whose body assembles a
       dict literal containing "event_type" or "payload".

CP003  `payload=` keyword argument in a call to any identifier matching
       `^emit_`, `^enqueue_`, or named `send_event`, when the value is an
       inline `ast.Dict` literal (not a pydantic model instance,
       not a `.model_dump()` call, not a name bound to a canonical model).

CP900  Exemption comment present but tracker reference missing or malformed.

CP901  ``canonical-event-exempt`` comment present but the category is missing
       / not one of the allowed categories, or the reason is empty.

Exemption mechanisms
--------------------

There are two ways to silence a violation. Pick the one that matches *why*
the hand-rolled shape is legitimate.

1. Production wire-envelope sites (tracker-backed)
   ------------------------------------------------

   For documented local-only wire-envelope assembly in production code, use
   an inline comment of the form:

       # canonical-producer-exempt: <tracker-ref> -- <one-line reason>

   placed on the violating line OR on the line immediately above it. The
   tracker reference is enforced by regex (default: `(<repo>)?#\\d+`) so every
   exemption is auditable and has a path to closure. Missing or malformed
   tracker still fails the lint (with CP900).

2. Legitimate test fixtures (category-backed)
   -------------------------------------------

   A *test* that hand-rolls an event must EITHER be refactored to build the
   event via the canonical emit/model path (``emit_*`` + ``read_*`` round
   trip), OR be explicitly annotated as one of two legitimate categories:

       # canonical-event-exempt(comparison): <reason>
       # canonical-event-exempt(exception-flow): <reason>

   placed on the violating line OR on the line immediately above it.

   * ``comparison``     -- the test's scope is specifically to compare a
                           creation function's output against an expected
                           hand-rolled dict (``assert emit_*(...) == {...}``).
                           The expected dict MUST be hand-rolled or the test
                           would be tautological.
   * ``exception-flow`` -- the test feeds a deliberately non-canonical /
                           malformed / legacy event shape into a defensive or
                           exception code path. A ``spec_kitty_events.*Payload``
                           model cannot represent the shape (that's the point),
                           so a raw fixture is the correct unit-under-test
                           input.

   The category is required and must be one of the two above; the reason is
   required and is surfaced in lint output so reviewers see WHY. A missing /
   unknown category or empty reason fails the lint with CP901.

   Un-annotated hand-rolled event creation in a test is a violation: either
   refactor it to the canonical path or annotate it with the right category.

Usage
-----

    python scripts/lint_canonical_producers.py --paths src/ scripts/ tests/

Baseline (ratchet) mode:

    # Capture today's violations into a baseline file so the rule blocks NEW
    # additions while existing sites are exempted-by-baseline until they can
    # be refactored individually:
    python scripts/lint_canonical_producers.py \\
        --paths src/ scripts/ tests/ \\
        --update-baseline scripts/canonical_producer_lint_baseline.txt

    # In CI, pass --baseline so today's known violations are silenced and
    # only NEW ones fail the build:
    python scripts/lint_canonical_producers.py \\
        --paths src/ scripts/ tests/ \\
        --baseline scripts/canonical_producer_lint_baseline.txt

The baseline is a hashed-violation file (one finding key per line). It is a
strict ratchet -- the lint refuses to silently allow new violations even if
they appear on a previously-baselined line. Each entry corresponds to one
specific (path, code, dict-shape-fingerprint) triple. When a baselined
violation disappears (because the site was refactored), the lint warns and
suggests re-running --update-baseline to keep the file lean.

Exit codes:
    0 -- no violations (or all violations covered by baseline; no stale
         baseline entries)
    1 -- at least one violation not covered by baseline
    2 -- usage error

Operating constraints
---------------------

* stdlib only (`ast`, `tokenize`, `pathlib`, `re`, `argparse`, `sys`).
  No new pip deps. The script must run on every CI runner unchanged.
* The rule lives here, in spec-kitty. spec-kitty-saas and
  spec-kitty-end-to-end-testing CI clone spec-kitty at a pinned SHA and
  invoke this script. There is exactly one source of truth.
"""

from __future__ import annotations

import argparse
import ast
import io
import re
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Iterable

# --------------------------------------------------------------------------- #
# Configuration                                                                #
# --------------------------------------------------------------------------- #

# A canonical constructor is recognised either by name (exact match in
# _CANONICAL_NAMES) or by suffix (the trailing segment of the call target
# ends in one of these strings).
_CANONICAL_NAMES: frozenset[str] = frozenset(
    {"StatusEvent", "EventEnvelope", "LifecycleEvent"}
)
_CANONICAL_SUFFIXES: tuple[str, ...] = ("Payload", "Envelope")

# Emit-site names that activate CP003.
_EMIT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^emit_"),
    re.compile(r"^enqueue_"),
    re.compile(r"^send_event$"),
)

# Event-shape keys that mark a dict as a candidate for CP001 / CP002.
_EVENT_KEYS_REQUIRED: frozenset[str] = frozenset({"event_type", "payload"})

# Tracker-ref regex. Permits bare `#1248` and `repo#1248` /
# `Priivacy-ai/spec-kitty#1248` forms.
_TRACKER_REF_PATTERN: re.Pattern[str] = re.compile(
    r"(?:[A-Za-z0-9._/-]+)?#\d+"
)

_EXEMPT_PREFIX = "canonical-producer-exempt:"

# Category-backed exemption for legitimate test fixtures.
#   # canonical-event-exempt(<category>): <reason>
_EVENT_EXEMPT_PATTERN: re.Pattern[str] = re.compile(
    r"^canonical-event-exempt\((?P<category>[^)]*)\)\s*:\s*(?P<reason>.*)$"
)
_EVENT_EXEMPT_CATEGORIES: frozenset[str] = frozenset({"comparison", "exception-flow"})


# --------------------------------------------------------------------------- #
# Data structures                                                              #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Finding:
    """A single lint finding."""

    path: Path
    line: int
    col: int
    code: str  # CP001 / CP002 / CP003 / CP900
    message: str

    def format(self) -> str:
        # Format matches the ruff convention: `<path>:<line>:<col>: <code> <message>`
        return f"{self.path}:{self.line}:{self.col}: {self.code} {self.message}"


@dataclass(frozen=True)
class ExemptionToken:
    """A parsed exemption comment."""

    line: int  # line number where the comment appears
    tracker_ref: str | None  # parsed tracker reference (None if malformed)
    raw: str  # raw comment text (for diagnostics)


@dataclass(frozen=True)
class EventExemptionToken:
    """A parsed ``canonical-event-exempt(<category>): <reason>`` comment.

    Used by *test* fixtures that legitimately hand-roll an event. ``category``
    is ``None`` when missing / not one of the allowed categories, and
    ``reason`` is ``None`` when empty -- either condition is malformed and
    surfaces as CP901.
    """

    line: int  # line number where the comment appears
    category: str | None  # comparison | exception-flow (None if malformed)
    reason: str | None  # one-line reason (None if empty/missing)
    raw: str  # raw comment text (for diagnostics)

    @property
    def is_valid(self) -> bool:
        return self.category is not None and self.reason is not None


# --------------------------------------------------------------------------- #
# Exemption parsing                                                            #
# --------------------------------------------------------------------------- #


def _parse_exemptions(source: str) -> dict[int, ExemptionToken]:
    """Parse all canonical-producer-exempt comments from a source string.

    Returns a mapping from comment line number to the parsed exemption.
    """
    exemptions: dict[int, ExemptionToken] = {}
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        for tok in tokens:
            if tok.type != tokenize.COMMENT:
                continue
            text = tok.string.lstrip("#").strip()
            if not text.startswith(_EXEMPT_PREFIX):
                continue
            payload = text[len(_EXEMPT_PREFIX):].strip()
            # Capture the FIRST whitespace-separated token before the em-dash /
            # double-dash / colon as the tracker ref candidate. We deliberately
            # scan the entire payload (not just the first token) so reasons
            # that quote issue numbers don't accidentally validate the
            # exemption -- the tracker must be the first thing after the
            # prefix.
            first_segment = payload.split(maxsplit=1)[0] if payload else ""
            # Strip any trailing punctuation like "," before validation.
            first_segment = first_segment.rstrip(",;")
            if _TRACKER_REF_PATTERN.fullmatch(first_segment):
                exemptions[tok.start[0]] = ExemptionToken(
                    line=tok.start[0],
                    tracker_ref=first_segment,
                    raw=tok.string,
                )
            else:
                exemptions[tok.start[0]] = ExemptionToken(
                    line=tok.start[0],
                    tracker_ref=None,
                    raw=tok.string,
                )
    except tokenize.TokenizeError:
        # If the file can't even be tokenized we let _lint_one_file surface
        # the AST parse error separately.
        return {}
    return exemptions


def _is_exempt(node_line: int, exemptions: dict[int, ExemptionToken]) -> ExemptionToken | None:
    """Return the exemption applicable to a finding at `node_line`, if any.

    An exemption applies if its comment is on the same line as the finding
    or on the line immediately above.
    """
    for candidate_line in (node_line, node_line - 1):
        if candidate_line in exemptions:
            return exemptions[candidate_line]
    return None


def _parse_event_exemptions(source: str) -> dict[int, EventExemptionToken]:
    """Parse all ``canonical-event-exempt(<category>): <reason>`` comments.

    Returns a mapping from comment line number to the parsed exemption.
    """
    exemptions: dict[int, EventExemptionToken] = {}
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        for tok in tokens:
            if tok.type != tokenize.COMMENT:
                continue
            text = tok.string.lstrip("#").strip()
            match = _EVENT_EXEMPT_PATTERN.match(text)
            if match is None:
                continue
            raw_category = match.group("category").strip()
            reason = match.group("reason").strip()
            category = raw_category if raw_category in _EVENT_EXEMPT_CATEGORIES else None
            exemptions[tok.start[0]] = EventExemptionToken(
                line=tok.start[0],
                category=category,
                reason=reason or None,
                raw=tok.string,
            )
    except tokenize.TokenizeError:
        return {}
    return exemptions


def _event_exempt_for(
    node_line: int, exemptions: dict[int, EventExemptionToken]
) -> EventExemptionToken | None:
    """Return the event-exemption applicable to a finding at `node_line`.

    Applies if the comment is on the same line as the finding or the line
    immediately above.
    """
    for candidate_line in (node_line, node_line - 1):
        if candidate_line in exemptions:
            return exemptions[candidate_line]
    return None


# --------------------------------------------------------------------------- #
# AST helpers                                                                  #
# --------------------------------------------------------------------------- #


def _is_canonical_call(node: ast.AST) -> bool:
    """True if `node` is a Call whose target is a canonical constructor."""
    if not isinstance(node, ast.Call):
        return False
    name = _call_target_name(node.func)
    if name is None:
        return False
    if name in _CANONICAL_NAMES:
        return True
    return any(name.endswith(suffix) for suffix in _CANONICAL_SUFFIXES)


def _call_target_name(func: ast.AST) -> str | None:
    """Return the trailing identifier of a Call's `func`, if simple enough."""
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _is_emit_call(node: ast.Call) -> bool:
    """True if `node.func` matches one of the emit-site name patterns."""
    name = _call_target_name(node.func)
    if name is None:
        return False
    return any(pattern.match(name) for pattern in _EMIT_PATTERNS)


def _dict_has_event_keys(node: ast.Dict) -> bool:
    """True if a dict literal has both `event_type` and `payload` as string keys."""
    string_keys: set[str] = set()
    for key in node.keys:
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            string_keys.add(key.value)
    return _EVENT_KEYS_REQUIRED.issubset(string_keys)


def _dict_has_any_event_key(node: ast.Dict) -> bool:
    """True if a dict literal has `event_type` or `payload` as a string key."""
    return any(isinstance(key, ast.Constant) and isinstance(key.value, str) and key.value in _EVENT_KEYS_REQUIRED for key in node.keys)


def _annotation_is_dict_str_any(annotation: ast.AST | None) -> bool:
    """True if the annotation is `dict[str, Any]` or `Dict[str, Any]`."""
    if annotation is None:
        return False
    if not isinstance(annotation, ast.Subscript):
        return False
    value = annotation.value
    if isinstance(value, ast.Name) and value.id not in {"dict", "Dict"}:
        return False
    if isinstance(value, ast.Attribute) and value.attr not in {"dict", "Dict"}:
        return False
    slice_node = annotation.slice
    if not isinstance(slice_node, ast.Tuple) or len(slice_node.elts) != 2:
        return False
    first, second = slice_node.elts
    if not (isinstance(first, ast.Name) and first.id == "str"):
        return False
    # second may be `Any`, `typing.Any`, or `object`. Accept any of these
    # because they all reflect a hand-rolled return shape.
    if isinstance(second, ast.Name) and second.id in {"Any", "object"}:
        return True
    return bool(isinstance(second, ast.Attribute) and second.attr == "Any")


# --------------------------------------------------------------------------- #
# Visitor                                                                      #
# --------------------------------------------------------------------------- #


class _ParentTagger(ast.NodeTransformer):
    """Annotate every node with its parent so the visitor can ask
    `is this dict literal an argument to a Call?`."""

    def visit(self, node: ast.AST) -> ast.AST:  # type: ignore[override]
        for child in ast.iter_child_nodes(node):
            child._cp_parent = node
            self.visit(child)
        return node


class _CanonicalProducerVisitor(ast.NodeVisitor):
    def __init__(
        self,
        path: Path,
        exemptions: dict[int, ExemptionToken],
        event_exemptions: dict[int, EventExemptionToken] | None = None,
    ) -> None:
        self.path = path
        self.exemptions = exemptions
        self.event_exemptions = event_exemptions or {}
        self.findings: list[Finding] = []
        # Track which exemption-comment lines have been "consumed" by a
        # finding-or-suppression decision so we can detect unused/invalid
        # exemptions and emit CP900.
        self._exemption_decisions: dict[int, bool] = {}
        # Track which event-exemption comment lines were consumed so a dangling
        # malformed canonical-event-exempt surfaces as CP901 in finalize().
        self._event_exemption_decisions: dict[int, bool] = {}

    # ------------------------------------------------------------------ CP001
    def visit_Dict(self, node: ast.Dict) -> None:
        if _dict_has_event_keys(node):
            parent = getattr(node, "_cp_parent", None)
            inside_canonical = False
            # Walk up two levels to handle `Canonical(payload={...})`:
            # the dict's parent may be a keyword node, whose parent is the
            # Call. That's still canonical.
            cursor: ast.AST | None = parent
            for _ in range(3):
                if cursor is None:
                    break
                if _is_canonical_call(cursor):
                    inside_canonical = True
                    break
                cursor = getattr(cursor, "_cp_parent", None)
            if not inside_canonical:
                self._maybe_report(
                    line=node.lineno,
                    col=node.col_offset,
                    code="CP001",
                    message=(
                        "hand-rolled event dict (keys event_type+payload) "
                        "outside a canonical model call -- construct via "
                        "spec_kitty_events.lifecycle.*Payload or another "
                        "canonical model"
                    ),
                )
        self.generic_visit(node)

    # ------------------------------------------------------------------ CP002
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_function(node)
        self.generic_visit(node)

    def _check_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        if not _annotation_is_dict_str_any(node.returns):
            return
        # Walk the body looking for `return <Dict>` or assignments of a
        # dict that is then returned. Simple shape -- explicit return of a
        # dict literal -- is the documented hand-rolled case from rc14->rc22.
        for child in ast.walk(node):
            if isinstance(child, ast.Return) and isinstance(child.value, ast.Dict) and _dict_has_any_event_key(child.value):
                self._maybe_report(
                    line=child.value.lineno,
                    col=child.value.col_offset,
                    code="CP002",
                    message=(
                        "function declared dict[str, Any] return builds "
                        "event-shaped dict in body -- declare the "
                        "canonical pydantic model as the return type and "
                        "construct via that model"
                    ),
                )

    # ------------------------------------------------------------------ CP003
    def visit_Call(self, node: ast.Call) -> None:
        if _is_emit_call(node):
            for kw in node.keywords:
                if kw.arg != "payload":
                    continue
                if isinstance(kw.value, ast.Dict):
                    self._maybe_report(
                        line=kw.value.lineno,
                        col=kw.value.col_offset,
                        code="CP003",
                        message=(
                            "inline dict literal passed as payload= to "
                            "emit_*/enqueue_*/send_event -- construct via a "
                            "canonical pydantic model and pass its "
                            ".model_dump() or the model instance"
                        ),
                    )
        self.generic_visit(node)

    # ------------------------------------------------------------------ shared
    def _maybe_report(self, *, line: int, col: int, code: str, message: str) -> None:
        # Category-backed test-fixture exemption takes precedence: a test that
        # legitimately hand-rolls an event annotates it as comparison /
        # exception-flow. A malformed annotation surfaces CP901 instead.
        event_exempt = _event_exempt_for(line, self.event_exemptions)
        if event_exempt is not None:
            self._event_exemption_decisions[event_exempt.line] = True
            if event_exempt.is_valid:
                # Legitimate, categorized fixture -- suppressed (reason is
                # surfaced via the comment itself; nothing to report).
                return
            self.findings.append(
                Finding(
                    path=self.path,
                    line=event_exempt.line,
                    col=0,
                    code="CP901",
                    message=(
                        "canonical-event-exempt has a missing/unknown category "
                        "or empty reason -- required form: "
                        "'# canonical-event-exempt(comparison|exception-flow): "
                        "<reason>'"
                    ),
                )
            )
            return

        exempt = _is_exempt(line, self.exemptions)
        if exempt is None:
            self.findings.append(
                Finding(path=self.path, line=line, col=col, code=code, message=message)
            )
            return
        # Mark this exemption as consumed.
        self._exemption_decisions[exempt.line] = True
        if exempt.tracker_ref is None:
            # CP900 is reported at the exemption comment's own line so the
            # operator sees it where the problem is.
            self.findings.append(
                Finding(
                    path=self.path,
                    line=exempt.line,
                    col=0,
                    code="CP900",
                    message=(
                        "exemption comment is missing or has a malformed "
                        "tracker reference -- required form: "
                        "'# canonical-producer-exempt: <repo>?#<num> -- <reason>'"
                    ),
                )
            )

    def finalize(self) -> None:
        """Emit CP900 for any exemption with a missing tracker that did NOT
        attach to a finding (so operators can't leave dangling malformed
        exemptions around)."""
        for line, exempt in self.exemptions.items():
            if exempt.tracker_ref is None and line not in self._exemption_decisions:
                self.findings.append(
                    Finding(
                        path=self.path,
                        line=line,
                        col=0,
                        code="CP900",
                        message=(
                            "exemption comment is missing or has a malformed "
                            "tracker reference (and does not attach to any "
                            "violation) -- remove it or fix the tracker ref"
                        ),
                    )
                )
        # CP901: a malformed canonical-event-exempt that did NOT attach to any
        # violation is still flagged so dead/broken annotations don't pile up.
        for line, event_exempt in self.event_exemptions.items():
            if not event_exempt.is_valid and line not in self._event_exemption_decisions:
                self.findings.append(
                    Finding(
                        path=self.path,
                        line=line,
                        col=0,
                        code="CP901",
                        message=(
                            "canonical-event-exempt has a missing/unknown "
                            "category or empty reason (and does not attach to "
                            "any violation) -- remove it or fix the annotation: "
                            "'# canonical-event-exempt(comparison|exception-flow)"
                            ": <reason>'"
                        ),
                    )
                )


# --------------------------------------------------------------------------- #
# File / tree iteration                                                        #
# --------------------------------------------------------------------------- #


def _iter_python_files(roots: Iterable[Path]) -> Iterable[Path]:
    """Yield all .py files under the given roots, ignoring common junk dirs."""
    skip_dirs = {
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        "node_modules",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "build",
        "dist",
        ".worktrees",
    }
    for root in roots:
        if root.is_file() and root.suffix == ".py":
            yield root
            continue
        if not root.is_dir():
            continue
        for path in root.rglob("*.py"):
            # Skip junk dirs anywhere in the path.
            if any(part in skip_dirs for part in path.parts):
                continue
            yield path


def _lint_one_file(path: Path) -> list[Finding]:
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        # Bad syntax is a different problem; the project's other lints will
        # catch it. We refuse to emit canonical-producer findings on a tree
        # we can't parse.
        return []
    _ParentTagger().visit(tree)
    exemptions = _parse_exemptions(source)
    event_exemptions = _parse_event_exemptions(source)
    visitor = _CanonicalProducerVisitor(
        path=path, exemptions=exemptions, event_exemptions=event_exemptions
    )
    visitor.visit(tree)
    visitor.finalize()
    return visitor.findings


def lint_paths(paths: Iterable[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for file_path in _iter_python_files(paths):
        findings.extend(_lint_one_file(file_path))
    findings.sort(key=lambda f: (str(f.path), f.line, f.col, f.code))
    return findings


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #


def _finding_key(f: Finding) -> str:
    """Return the baseline key for a finding.

    Format: `<path>::<code>` -- intentionally line-number-agnostic so a small
    edit that shifts line numbers does not invalidate the baseline. The
    trade-off is that adding a NEW violation in a file that already has
    same-code violations will not be detected; that's an acceptable false
    negative in baseline mode because the goal is to ratchet down the
    aggregate count, not to catch every line. CI without --baseline catches
    everything; --baseline mode is the migration on-ramp.
    """
    return f"{f.path}::{f.code}"


def _read_baseline(path: Path) -> set[str]:
    if not path.exists():
        return set()
    out: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.add(line)
    return out


def _write_baseline(path: Path, findings: list[Finding]) -> None:
    keys = sorted({_finding_key(f) for f in findings})
    header = (
        "# Canonical-producer-lint baseline.\n"
        "# Generated by scripts/lint_canonical_producers.py --update-baseline.\n"
        "# Each line is `<path>::<code>` for a known violation site that\n"
        "# pre-dates the lint. Refactor sites individually; re-run\n"
        "# --update-baseline to keep this file lean. See issue #1248.\n"
    )
    path.write_text(header + "\n".join(keys) + ("\n" if keys else ""), encoding="utf-8")


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="lint_canonical_producers",
        description=(
            "AST lint rule against hand-rolled event dicts. "
            "Enforces the canonical-producer non-negotiable from "
            "spec-kitty-mission-workflow.md C-007."
        ),
    )
    p.add_argument(
        "--paths",
        nargs="+",
        required=True,
        help="One or more files or directories to lint.",
    )
    p.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help=(
            "Path to a baseline file. Known violations in the baseline are "
            "silenced (CI passes). New violations not in the baseline still "
            "fail. Use --update-baseline to refresh."
        ),
    )
    p.add_argument(
        "--update-baseline",
        type=Path,
        default=None,
        help=(
            "Path at which to write a fresh baseline file capturing every "
            "current violation. Run this after a refactor sweep to shrink "
            "the baseline."
        ),
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # argparse exits with 2 on usage error; preserve that.
        return int(exc.code) if exc.code is not None else 2

    roots = [Path(p) for p in args.paths]
    missing = [p for p in roots if not p.exists()]
    if missing:
        for p in missing:
            print(f"error: path does not exist: {p}", file=sys.stderr)
        return 2

    findings = lint_paths(roots)

    if args.update_baseline is not None:
        _write_baseline(args.update_baseline, findings)
        print(
            f"wrote {len({_finding_key(f) for f in findings})} baseline "
            f"entries to {args.update_baseline}",
            file=sys.stderr,
        )
        return 0

    baseline = _read_baseline(args.baseline) if args.baseline else set()
    new_findings = [f for f in findings if _finding_key(f) not in baseline]
    silenced_count = len(findings) - len(new_findings)

    for f in new_findings:
        print(f.format())

    # Detect stale baseline entries (entries that no longer correspond to a
    # current violation). Warn but do not fail -- if the refactor cleared
    # the site, that's good; the operator just needs to refresh.
    if baseline:
        present_keys = {_finding_key(f) for f in findings}
        stale = sorted(baseline - present_keys)
        if stale:
            print(
                f"warning: {len(stale)} baseline entr"
                f"{'y' if len(stale) == 1 else 'ies'} no longer correspond "
                "to a current violation -- refresh with --update-baseline:",
                file=sys.stderr,
            )
            for key in stale:
                print(f"  - {key}", file=sys.stderr)

    if new_findings:
        msg = (
            f"\n{len(new_findings)} new canonical-producer violation(s)"
        )
        if silenced_count:
            msg += f" ({silenced_count} silenced by baseline)"
        msg += (
            ". See https://github.com/Priivacy-ai/spec-kitty/issues/1248 "
            "and spec-kitty-mission-workflow.md C-007."
        )
        print(msg, file=sys.stderr)
        return 1

    if silenced_count and not args.baseline:
        # This branch is unreachable -- silenced_count is only nonzero when
        # a baseline was loaded -- but guarded for safety.
        pass
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
