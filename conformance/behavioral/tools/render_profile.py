#!/usr/bin/env python3
"""Deterministic projector: ``*.agent.yaml`` -> Claude Code named-agent body.

Mission: doctrine-behavioral-suite-01KYW5XK (M4), WP01, FR-009.

Given one ``*.agent.yaml`` source path, produce, on stdout, the exact
``.claude/agents/<id>.md`` body ``ClaudeCodeProfileRenderer.render()`` would
emit -- deterministically, with zero dependency on any other checkout's tree
state. Mirrors mission M7's ``conformance/tools/profile2soul.py`` pattern
(same RED/GREEN discipline, same hazard class), but never fabricates a
single field: everything this script emits comes straight from
``ClaudeCodeProfileRenderer.render()``, unmodified.

Import-shadowing guard (Finding 5 / the single highest-value correctness
risk in this WP)
-----------------------------------------------------------------------
This checkout's own ``specify_cli`` package is ``pip``-editable-installed
pointing at a *different* checkout
(``python3 -c "import specify_cli, os; print(os.path.dirname(specify_cli.__file__))"``
resolves outside this repository entirely). A bare
``from specify_cli import ...`` -- or any import of ``specify_cli``/
``charter``/``doctrine`` before ``sys.path`` is adjusted -- would silently
read that *other* checkout's renderer/profile code, not this one's. The two
checkouts happen to be byte-identical today, which is exactly why this is a
silent-failure-prone hazard rather than a merely theoretical one: nothing
would visibly break until the checkouts drift, at which point this script
would keep producing plausible-looking, wrong output. The fix is to prepend
*this checkout's own* ``src/`` to ``sys.path`` before any such import, so the
interpreter finds this repository's packages first regardless of whatever
happens to be the current editable-install target.

Profile-loading guard
----------------------
The source profile is parsed directly via
``charter.profiles.AgentProfile.model_validate(...)`` (Pydantic), never via
``AgentProfileRepository``'s directory-scanning default. None of this WP's 5
target profiles declare ``specializes_from``, so direct construction from
the one parsed source file is sufficient, and it avoids the identical
directory-shadowing risk on the profile-*data* side (a directory scan could
just as easily pick up a stale or foreign profile tree).

Determinism contract (FR-009): running this script twice against the same,
unchanged source profile must produce byte-identical stdout. No wall-clock
timestamps anywhere in the output path; the only "generated" fact this
script computes -- the source file's content hash -- is a pure function of
that file's bytes, written to stderr, never stdout, so it never perturbs the
committed rendered body (T002 redirects stdout to the committed file).
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

# Prepend this checkout's own src/ to sys.path *before* any specify_cli/
# charter/doctrine import (see module docstring's import-shadowing guard).
# conformance/behavioral/tools/render_profile.py -> tools -> behavioral ->
# conformance -> <repo root>, so parents[3] is the repo root.
_THIS_FILE = Path(__file__).resolve()
_REPO_SRC = _THIS_FILE.parents[3] / "src"
sys.path.insert(0, str(_REPO_SRC))

from pydantic import ValidationError  # noqa: E402
from ruamel.yaml import YAML  # noqa: E402
from ruamel.yaml.error import YAMLError  # noqa: E402

from charter.profiles import AgentProfile  # noqa: E402
from specify_cli.tool_surface.profiles.renderers import (  # noqa: E402
    ClaudeCodeProfileRenderer,
)


def _load_profile(source_path: Path) -> AgentProfile:
    """Parse ``source_path`` and construct an ``AgentProfile`` directly.

    Raises ``ValueError``/``YAMLError``/``ValidationError`` on a malformed or
    incomplete source file -- callers convert these to a stable exit code
    rather than letting a raw traceback escape.
    """
    yaml = YAML(typ="safe")
    with source_path.open("r", encoding="utf-8") as handle:
        data = yaml.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{source_path}: expected a YAML mapping at the top level")
    return AgentProfile.model_validate(data)


def _content_hash(source_path: Path) -> str:
    """Return a stable ``sha256:<hex>`` digest of the source file's raw bytes.

    Pure function of file content, never of wall-clock time or of the
    rendered output -- C-003 requires manifests to cite this hash (of the
    *source* ``.agent.yaml``, not the projected body) alongside the
    projected file path.
    """
    # noqa justification (TID251): file-integrity check over a raw source
    # profile file (drift detection), not a reimplementation of
    # src/charter/hasher.py's charter-content hashing (different input
    # shape, different package boundary this standalone conformance tool
    # should not reach into) -- same exemption profile2soul.py documents.
    digest = hashlib.sha256(source_path.read_bytes()).hexdigest()  # noqa: TID251
    return f"sha256:{digest}"


def render(source_path: Path) -> tuple[str, str]:
    """Render ``source_path`` and return ``(body, source_hash)``.

    Deterministic: calling this twice with the same, unchanged
    ``source_path`` returns byte-identical results both times.
    """
    profile = _load_profile(source_path)
    body = ClaudeCodeProfileRenderer().render(profile)
    source_hash = _content_hash(source_path)
    return body, source_hash


def main(argv: list[str]) -> int:
    """CLI entry point: ``render_profile.py <path-to-agent.yaml>``.

    Writes the rendered body to stdout and ``<source_hash>  <source_path>``
    to stderr. Returns a process exit code: ``0`` on success, ``2`` on a
    usage error or an unreadable/nonexistent source path, ``1`` on a
    malformed/incomplete source profile.
    """
    if len(argv) != 2:
        print(f"usage: {argv[0]} <path-to-agent.yaml>", file=sys.stderr)
        return 2

    source_path = Path(argv[1])
    if not source_path.is_file():
        print(f"error: {source_path} is not a file", file=sys.stderr)
        return 2

    try:
        body, source_hash = render(source_path)
    except (KeyError, TypeError, ValueError, YAMLError, ValidationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    sys.stdout.write(body)
    print(f"{source_hash}  {source_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
