"""Unreachability control for the inline-meta-read gate (SC-005 / NFR-004).

Scanner-invisible bypass shape, reproduced from research control ``C3``
(``kitty-specs/meta-fail-closed-3162-01KZ7FSQ/research/3162-census.md:300``): the
``meta.json`` bytes arrive from ``git show HEAD:<path>`` stdout, **not** from a
``read_text``/``open``/``read_bytes`` call, so clause 2 of the scanner predicate
(``test_inline_meta_read_gate._read_source_base``) cannot resolve the parsed
argument to a path expression at all. Expected census over this file alone:
**sites: 0**.

Two shapes are present on purpose:

* :func:`_inlined_git_show_read` — ``C3`` verbatim, the parse fully inlined.
* :func:`_delegated_git_show_read` — the **post-widening repeat**. WP06's
  one-hop anchor *does* follow a private, same-module, single-parameter parse
  helper (:func:`_parse_meta_object`) back to its call sites, so it reaches this
  call site and *then* rejects it at clause 2. The widening deliberately does
  not make the ``git show`` class reachable; covering it needs a genuinely new
  argument-shape detector, which is out of scope (FR-007 deferral).

The companion module ``unreachability_control_twin.py`` carries the positive
control (**sites: 1**), so this ``0`` is falsifiable rather than the signature of
a broken scanner (``architectural-gate-non-vacuity``).

**Never move this module (or its twin) under ``src/``.**
``scan_inline_meta_reads`` walks ``SRC_ROOT``; the twin's fully-inlined read
placed there would raise the live inline census and red
``test_inline_meta_read_floor`` — the very floor these controls exist to prove.
This is scratch scanner input: never imported, never executed. The
leading-underscore package directory keeps pytest from collecting it.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def _parse_meta_object(text: str) -> dict[str, object] | None:
    """Private, same-module, single-parameter parse helper — the anchor-hop shape."""
    parsed: object = json.loads(text)
    return parsed if isinstance(parsed, dict) else None


def _git_show(worktree: Path, path: str) -> subprocess.CompletedProcess[str]:
    """Read the committed blob at ``HEAD:<path>`` — the bytes never touch the filesystem."""
    return subprocess.run(
        ["git", "show", f"HEAD:{path}"],
        cwd=worktree,
        capture_output=True,
        text=True,
        check=False,
    )


def _inlined_git_show_read(worktree: Path, path: str) -> object:
    """``C3`` verbatim: parse inlined, argument traced to subprocess stdout -> invisible."""
    meta_path = worktree / path
    result = _git_show(meta_path.parent, path)
    parsed: object = json.loads(result.stdout)
    return parsed


def _delegated_git_show_read(worktree: Path, path: str) -> dict[str, object] | None:
    """Post-widening repeat: the anchor hop reaches this call site and still rejects."""
    meta_path = worktree / path
    result = _git_show(meta_path.parent, path)
    return _parse_meta_object(result.stdout)
