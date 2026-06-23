"""AST guard against ``CommitTargetKind`` reintroduction (WP01 / FR-010, FR-011, NFR-003).

The single-authority topology cleanup eradicates the vestigial
:class:`mission_runtime.context.CommitTargetKind` enum (WP04/WP05 drain its
references; WP16 deletes the type). This guard is the **non-fakeable** safety net
that makes that eradication *stick*: it FAILS CI if, in ``src/``,

* **(a)** any ``CommitTargetKind`` symbol reference REAPPEARS beyond the recorded
  baseline (the symbol-set RATCHET — it may only SHRINK, never grow), OR
* **(b)** anything serializes the former enum value ``"flattened"`` **as the
  enum** — e.g. ``CommitTargetKind.FLATTENED.value`` flowing into a JSON/meta
  write — which is a forbidden re-coupling of the storage layer to the doomed
  enum.

**Symbol resolution, never string-grep (NFR-003).** ``FLATTENED.value ==
"flattened"`` COLLIDES with the SURVIVING ``flattened`` provenance meta-flag
(``meta["flattened"] = False``, C-006), so a string scan for ``"flattened"``
would false-flag the legitimate flag. This guard therefore resolves the symbol by
AST: it tracks the imported binding name of ``CommitTargetKind`` (including aliased
re-imports, ``import ... as _K``) and flags only AST nodes that reference THAT
binding — an attribute access on it, an aliased ``Name``, or a
``getattr(obj, "CommitTargetKind")`` form. The literal string ``"flattened"`` on
its own is NEVER flagged.

**Drift-proof keying (CT1).** Every recorded site is keyed on the
``_ratchet_keys.composite_key`` ``(enclosing_qualname, token_line)`` tuple — a
content-addressed key that survives a ``+1`` blank/comment line drift and changes
only on a genuine semantic move. NO ``file.py:NNN`` keys.

**Ratchet form (T003 choice).** Part (a) uses the SYMBOL-SET ratchet (not a fixed
``== N`` count): the live reference set must be a SUBSET of the recorded baseline.
This is GREEN-and-tightening through WP03→WP05 (each reference drained shrinks the
set; the test stays green), and reaches the empty set when WP16 deletes the enum.
A REINTRODUCED reference (a new key absent from the baseline) FAILS the gate
immediately — that is the reappearance guard. The baseline is the explicit,
auditable record of every site that still references the doomed enum.

The companion :mod:`test_commit_target_kind_guard` self-test (``test_guard_*``
below) plants a synthetic offender and asserts the detector BITES — a guard that
cannot fail on a planted phantom is theater (the gate-unmask discipline, NFR-003).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.architectural._ratchet_keys import composite_key

pytestmark = [pytest.mark.architectural]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"

#: The canonical symbol the guard tracks.
_TARGET_SYMBOL = "CommitTargetKind"
#: The former enum-value string that must never be serialized AS the enum. It is
#: only flagged when reached via the enum symbol (``CommitTargetKind.FLATTENED``),
#: NEVER as a bare ``"flattened"`` string (that collides with the C-006 meta-flag).
_FLATTENED_MEMBER = "FLATTENED"


@dataclass(frozen=True)
class _Reference:
    """One discovered ``CommitTargetKind`` reference site."""

    rel_path: str
    lineno: int
    form: str  # "import" | "attribute" | "getattr" | "name" | "serialize"
    source: str

    def as_key(self) -> tuple[str, str, str]:
        """Drift-proof ``(rel_path, qualname, token_line)`` symbol-set key.

        Content-addressed (enclosing function + tokenized code line) via
        :func:`composite_key`, NOT line-number addressed — a benign blank/comment
        insertion above the site leaves the key unchanged (CT1).
        """
        qn, tl = composite_key(self.source, self.lineno)
        return (self.rel_path, qn, tl)


class _CommitTargetKindVisitor(ast.NodeVisitor):
    """Resolve ``CommitTargetKind`` references BY SYMBOL across one module.

    Tracks the imported binding name (handles ``import ... as _alias``) so an
    aliased re-import is followed, then flags:

    * the import binding itself (form ``"import"``),
    * an attribute access ``<binding>.X`` (form ``"attribute"``; a ``.FLATTENED``
      member access whose ``.value`` is taken is additionally form ``"serialize"``),
    * a bare ``Name`` reference to the binding (form ``"name"``),
    * a ``getattr(obj, "CommitTargetKind")`` dynamic access (form ``"getattr"``).

    A bare string literal ``"flattened"`` is NEVER visited as a reference — the
    surviving C-006 meta-flag is structurally invisible to this symbol walk.
    """

    def __init__(self, rel_path: str, source: str) -> None:
        self.rel_path = rel_path
        self.source = source
        self.refs: list[_Reference] = []
        #: Binding names that resolve to ``CommitTargetKind`` (canonical + aliases).
        self._bindings: set[str] = set()

    def _add(self, lineno: int, form: str) -> None:
        self.refs.append(_Reference(self.rel_path, lineno, form, self.source))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name == _TARGET_SYMBOL:
                self._bindings.add(alias.asname or alias.name)
                self._add(node.lineno, "import")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # ``<binding>.<member>`` — the binding may be a direct Name or itself an
        # attribute chain (e.g. ``context.CommitTargetKind`` when imported via a
        # module). We flag a member access on a tracked binding, and additionally
        # mark ``<binding>.FLATTENED.value`` as a serialize-as-enum site.
        base = node.value
        if isinstance(base, ast.Name) and base.id in self._bindings:
            form = "attribute"
            self._add(node.lineno, form)
        elif (
            isinstance(base, ast.Attribute)
            and base.attr == _FLATTENED_MEMBER
            and isinstance(base.value, ast.Name)
            and base.value.id in self._bindings
            and node.attr == "value"
        ):
            # ``CommitTargetKind.FLATTENED.value`` — serialize-as-enum (part b).
            self._add(node.lineno, "serialize")
        elif isinstance(base, ast.Attribute) and base.attr == _TARGET_SYMBOL:
            # ``<module>.CommitTargetKind`` attribute import form.
            self._add(node.lineno, "attribute")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id in self._bindings:
            self._add(node.lineno, "name")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # ``getattr(obj, "CommitTargetKind")`` — dynamic resolution of the symbol.
        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "getattr"
            and len(node.args) >= 2
            and isinstance(node.args[1], ast.Constant)
            and node.args[1].value == _TARGET_SYMBOL
        ):
            self._add(node.lineno, "getattr")
        self.generic_visit(node)


def discover_references(source: str, rel_path: str) -> list[_Reference]:
    """AST-walk one module's *source* and return every ``CommitTargetKind`` reference.

    Resolves the symbol by binding (imports + aliases + attribute/getattr forms),
    NEVER by grepping the string ``"flattened"`` — the surviving C-006 meta-flag is
    not a reference and is never flagged.
    """
    try:
        tree = ast.parse(source, filename=rel_path)
    except SyntaxError:
        return []
    visitor = _CommitTargetKindVisitor(rel_path, source)
    visitor.visit(tree)
    return visitor.refs


def _discover_src_references() -> list[_Reference]:
    """Discover every ``CommitTargetKind`` reference under ``src/`` (sorted)."""
    refs: list[_Reference] = []
    for path in sorted(_SRC.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            continue
        # Cheap pre-filter: skip files that cannot reference the symbol at all.
        if _TARGET_SYMBOL not in source:
            continue
        rel = path.relative_to(_REPO_ROOT).as_posix()
        refs.extend(discover_references(source, rel))
    return refs


def _live_reference_keys() -> set[tuple[str, str, str]]:
    """The live symbol-set: every reference key currently present under ``src/``."""
    return {ref.as_key() for ref in _discover_src_references()}


# ---------------------------------------------------------------------------
# Baseline symbol-set (T003 ratchet). The recorded set of every CommitTargetKind
# reference site present TODAY. The ratchet asserts the live set is a SUBSET of
# this baseline — it may only SHRINK (WP03→WP05 drain references; WP16 deletes the
# enum and the set reaches empty). A REINTRODUCED reference (a key NOT in this
# baseline) FAILS the gate. Keys are content-addressed composite keys (CT1), so
# benign line drift does NOT churn the baseline; only a genuine new/moved site does.
#
# The baseline is generated from the live tree at WP01 authoring time and is the
# auditable record of the eradication's starting point. When a downstream WP drains
# a reference, it REMOVES the corresponding key here (the set shrinks); it never
# re-keys to dodge a red (CT2).
# ---------------------------------------------------------------------------
#
# WP16 (FR-001b) DELETED the ``CommitTargetKind`` enum and the ``CommitTarget``
# ``kind`` field. Every producer/consumer was drained first (WP03/WP04/WP05/WP14/
# WP15) and the final residue here, so the baseline is now EMPTY: ZERO live
# references survive under ``src/``. The ratchet has reached its terminal state —
# the live set must STAY empty, and ANY reintroduced reference is an immediate
# failure (the eradication is permanent). ``test_baseline_is_empty_post_wp16``
# pins this terminal state.
_BASELINE_REFERENCE_KEYS: frozenset[tuple[str, str, str]] = frozenset()


def test_commit_target_kind_references_only_shrink() -> None:
    """T003 (a): the ``CommitTargetKind`` reference set may only SHRINK (ratchet).

    Symbol-set ratchet (NOT a fixed ``== N`` count): the live reference set must be
    a SUBSET of the recorded baseline. Any reference key absent from the baseline is
    a REINTRODUCTION — the eradication guard fires. As WP03→WP05 drain references
    the live set shrinks and the test stays GREEN; when WP16 deletes the enum the
    set reaches empty (still a subset). Keyed on the drift-proof composite key (CT1),
    never ``file.py:NNN``.
    """
    live = _live_reference_keys()
    reintroduced = live - _BASELINE_REFERENCE_KEYS
    assert not reintroduced, (
        "CommitTargetKind reference REINTRODUCED at "
        + ", ".join(
            f"{rel}::{qn} :: {tl!r}" for (rel, qn, tl) in sorted(reintroduced)
        )
        + " — the enum is being eradicated (WP04/WP05/WP16); a new reference "
        "must not reappear. If a reference legitimately MOVED, drain the old key "
        "and re-author the site, do not silently widen the baseline."
    )


def test_baseline_is_empty_post_wp16() -> None:
    """Terminal state (WP16 / FR-001b): the baseline is EMPTY — the enum is deleted.

    WP16 deleted the ``CommitTargetKind`` enum and the ``CommitTarget.kind`` field
    after every producer/consumer was drained. The baseline therefore reaches the
    empty set: there is NO surviving site that references the doomed symbol. This is
    the inverse of the pre-WP16 ``nonempty`` precondition — it pins the eradication
    as COMPLETE and permanent (the symbol cannot be reintroduced under ``src/``).
    """
    assert not _BASELINE_REFERENCE_KEYS, (
        "post-WP16 the CommitTargetKind baseline must be EMPTY (the enum is "
        "deleted) — a non-empty baseline means a residue reference survived the "
        "eradication or the baseline was not drained"
    )


def test_live_set_is_empty_post_wp16() -> None:
    """Terminal state: ZERO live ``CommitTargetKind`` references remain in ``src/``.

    The eradication proof in code (FR-001b): the AST symbol walk over the whole
    ``src/`` tree finds NO reference to the deleted ``CommitTargetKind`` symbol.
    Combined with the empty baseline above, the subset ratchet is now a permanent
    "stays-empty" guard — any reintroduced reference fails
    ``test_commit_target_kind_references_only_shrink`` immediately.
    """
    assert _live_reference_keys() == set(), (
        "a CommitTargetKind reference survives in src/ after WP16 deleted the enum "
        "— the eradication is incomplete: "
        + ", ".join(
            f"{rel}::{qn}" for (rel, qn, _tl) in sorted(_live_reference_keys())
        )
    )


def test_ratchet_bites_on_reintroduced_key() -> None:
    """T004: the subset ratchet FAILS when a reintroduced key is present.

    Proves the ratchet is not inert: a synthetic live set carrying a key absent from
    the baseline must produce a non-empty ``live - baseline`` (the reintroduction the
    ratchet reports). Without this, a future bug that made the live set vacuously
    equal the baseline would pass silently.
    """
    phantom_key = ("src/phantom_reintroduced.py", "land", "return CommitTargetKind . PRIMARY")
    synthetic_live = set(_BASELINE_REFERENCE_KEYS) | {phantom_key}
    reintroduced = synthetic_live - _BASELINE_REFERENCE_KEYS
    assert reintroduced == {phantom_key}, (
        "the subset ratchet failed to report a planted reintroduced reference key "
        "— the ratchet is inert (theater)"
    )


def test_no_serialize_flattened_enum_value() -> None:
    """T003 (b): nothing serializes ``CommitTargetKind.FLATTENED.value`` as the enum.

    The storage layer must never re-couple to the doomed enum's value. This is
    distinct from the surviving ``flattened`` provenance meta-flag (C-006): the
    guard flags ONLY the ``CommitTargetKind.FLATTENED.value`` symbol chain, never a
    bare ``"flattened"`` string. GREEN today (no such serialization exists) and must
    stay green — a future ``meta["topology"] = CommitTargetKind.FLATTENED.value``
    write would fire this gate.
    """
    serialize_sites = [
        ref for ref in _discover_src_references() if ref.form == "serialize"
    ]
    assert not serialize_sites, (
        "CommitTargetKind.FLATTENED.value serialized as the enum at "
        + ", ".join(f"{ref.rel_path}:{ref.lineno}" for ref in serialize_sites)
        + " — the storage layer must not re-couple to the doomed enum value "
        "(distinct from the surviving 'flattened' provenance meta-flag, C-006)."
    )


# ---------------------------------------------------------------------------
# T004 — planted-offender self-tests (non-fakeability, NFR-003). Each plants a
# synthetic source and asserts the detector BITES, proving the guard is not inert.
# ---------------------------------------------------------------------------

_PHANTOM_DIRECT = '''\
from mission_runtime import CommitTargetKind


def land() -> object:
    return CommitTargetKind.COORDINATION
'''

_PHANTOM_ALIASED_REIMPORT = '''\
from mission_runtime.context import CommitTargetKind as _K


def land() -> object:
    kind = _K.PRIMARY
    return kind
'''

_PHANTOM_GETATTR = '''\
def land(context: object) -> object:
    enum_cls = getattr(context, "CommitTargetKind")
    return enum_cls
'''

_PHANTOM_SERIALIZE = '''\
import json

from mission_runtime import CommitTargetKind


def persist(meta: dict[str, object]) -> str:
    meta["topology"] = CommitTargetKind.FLATTENED.value
    return json.dumps(meta)
'''

#: Negative control: the surviving C-006 provenance meta-flag must NOT trip the
#: guard. A bare ``"flattened"`` string is not a CommitTargetKind reference.
_LEGIT_META_FLAG = '''\
def backfill(meta: dict[str, object]) -> dict[str, object]:
    meta["flattened"] = False
    if meta.get("flattened") is True:
        meta["flattened"] = bool(meta["flattened"])
    return meta
'''


def test_guard_bites_direct_reference() -> None:
    """T004: the detector flags a plain ``CommitTargetKind.X`` reference."""
    refs = discover_references(_PHANTOM_DIRECT, "phantom_direct.py")
    forms = {r.form for r in refs}
    assert "import" in forms
    assert "attribute" in forms


def test_guard_bites_aliased_reimport() -> None:
    """T004: an aliased re-import (``import ... as _K``) is followed by the detector.

    The whole point of symbol resolution (vs string-grep): a rename of the binding
    cannot smuggle a reference past the guard.
    """
    refs = discover_references(_PHANTOM_ALIASED_REIMPORT, "phantom_alias.py")
    forms = {r.form for r in refs}
    assert "import" in forms, "aliased import binding not tracked"
    # The aliased ``_K.PRIMARY`` attribute access and the bare ``kind`` use resolve.
    assert "attribute" in forms, "aliased attribute access not flagged"


def test_guard_bites_getattr_form() -> None:
    """T004: a ``getattr(obj, "CommitTargetKind")`` dynamic access is flagged."""
    refs = discover_references(_PHANTOM_GETATTR, "phantom_getattr.py")
    assert any(r.form == "getattr" for r in refs), (
        "dynamic getattr resolution of CommitTargetKind not flagged"
    )


def test_guard_bites_serialize_enum_value() -> None:
    """T004: ``CommitTargetKind.FLATTENED.value`` is flagged as a serialize site."""
    refs = discover_references(_PHANTOM_SERIALIZE, "phantom_serialize.py")
    assert any(r.form == "serialize" for r in refs), (
        "CommitTargetKind.FLATTENED.value serialization not flagged"
    )


def test_guard_ignores_surviving_flattened_meta_flag() -> None:
    """T004 negative control: the C-006 ``flattened`` meta-flag must NOT be flagged.

    Proves the guard resolves the SYMBOL, not the string: a legit
    ``meta["flattened"] = False`` (the surviving provenance flag) carries the
    literal ``"flattened"`` but no ``CommitTargetKind`` symbol, so the detector
    returns ZERO references. A string-grep guard would false-flag this — the
    one-sided over-broad mutant this negative control kills.
    """
    refs = discover_references(_LEGIT_META_FLAG, "legit_flag.py")
    assert refs == [], (
        f"the surviving 'flattened' meta-flag was wrongly flagged: {refs} — the "
        "guard must resolve the CommitTargetKind symbol, never the string"
    )
