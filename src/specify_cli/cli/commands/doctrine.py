"""``spec-kitty doctrine`` command group.

Surface area:

* ``spec-kitty doctrine fetch [--pack <name>] [--dry-run]`` — fetch one or
  all configured org doctrine packs into their local snapshot directories.
* ``spec-kitty doctrine regenerate-graph [--check] [--json]`` — deterministically
  regenerate the shipped DRG ``graph.yaml`` from the built-in doctrine tree
  (FR-009 / WP09). ``--check`` compares without writing and exits non-zero when
  the committed graph is stale.
* ``spec-kitty doctrine pack validate <pack-path> [--json]`` — validate a
  doctrine pack against the artifact / DRG / org-charter contracts.
* ``spec-kitty doctrine pack assemble <out> <inputs...> [--force]
  [--conflicts-out FILE] [--json]`` — assemble multiple input packs into a
  single distributable output pack.
* ``spec-kitty doctrine new <kind> <id> [--pack <path>]`` — scaffold a stub
  project-layer (or pack-layer) artifact YAML pre-filled with the canonical
  schema's required fields (FR-016).
* ``spec-kitty doctrine validate <path>`` — validate a single project-layer
  artifact file or a doctrine tree against the artifact schemas (FR-017).
* ``spec-kitty doctrine org init <path> [--force] [--template …]
  [--org-name …] [--local-path …] [--branch …]`` — scaffold a minimal org
  doctrine pack, or render a full tree from a local/git template for operators
  creating their own doctrine (FR-006 / WP08 + template render).
* ``spec-kitty doctrine org validate <path>`` — validate an org doctrine pack
  using the WP06 loader and schema checks; exits non-zero on errors (FR-006 /
  WP08).
* ``spec-kitty doctrine mission-type list [--json]`` — list all mission types
  visible in the doctrine layer (built-in + org + project) regardless of
  activation state (FR-013 / WP13).

Both ``pack validate`` and ``pack assemble`` are implemented by WP06; their
heavy lifting lives in :mod:`specify_cli.doctrine.pack_validator` and
:mod:`specify_cli.doctrine.pack_assembler` so this module only handles
argument parsing and exit-code mapping. ``new`` and ``validate`` are owned
by WP09 (Mission B) and reuse the same schema registry from
:mod:`specify_cli.doctrine.pack_validator`.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from charter.drg import ArtifactKind
from specify_cli.cli.console import console
from rich.table import Table

__all__ = ["app"]

_JSON_OPTION_HELP = "Emit machine-readable JSON instead of rich text."

app = typer.Typer(
    name="doctrine",
    help="Manage org-layer doctrine packs (fetch, validate, assemble).",
    no_args_is_help=True,
)

pack_app = typer.Typer(
    name="pack",
    help="Validate or assemble doctrine packs.",
    no_args_is_help=True,
)
app.add_typer(pack_app, name="pack")

org_app = typer.Typer(
    name="org",
    help="Manage org-layer doctrine pack authoring (init, validate).",
    no_args_is_help=True,
)
app.add_typer(org_app, name="org")

mission_type_app = typer.Typer(
    name="mission-type",
    help="Mission type commands.",
    no_args_is_help=True,
)
app.add_typer(mission_type_app, name="mission-type")



# ----------------------------------------------------------------------
# fetch
# ----------------------------------------------------------------------
@app.command(name="fetch")
def fetch(
    pack_name: str | None = typer.Option(
        None,
        "--pack",
        help="Fetch only the named pack (default: fetch all configured packs).",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be fetched without contacting any remote.",
    ),
) -> None:
    """Fetch org doctrine pack(s) from their configured remote sources."""
    from specify_cli.core.paths import locate_project_root
    from specify_cli.doctrine.config import load_pack_registry
    from specify_cli.doctrine.snapshot import fetch_pack

    repo_root = locate_project_root()
    if repo_root is None:
        console.print(
            "[red]Could not locate spec-kitty project root.[/red] "
            "Run from inside a project containing .kittify/."
        )
        raise typer.Exit(1)

    registry = load_pack_registry(repo_root)
    if not registry.packs:
        console.print("[red]No org doctrine packs configured.[/red]")
        console.print(
            "Add a [bold]doctrine.org.packs[/bold] block to "
            ".kittify/config.yaml. See the contract at "
            "kitty-specs/layered-doctrine-org-layer-*/contracts/config-schema.yaml."
        )
        raise typer.Exit(1)

    target_packs = list(registry.packs)
    if pack_name is not None:
        target_packs = [p for p in registry.packs if p.name == pack_name]
        if not target_packs:
            names = ", ".join(registry.names()) or "(none)"
            console.print(
                f"[red]Pack '{pack_name}' not found.[/red] "
                f"Configured packs: {names}"
            )
            raise typer.Exit(1)

    if dry_run:
        from doctrine.drg.org_pack_config import OrgPackEnvVarUnsetError

        for pack in target_packs:
            origin = pack.url or str(pack.local_path)
            try:
                target = pack.local_path_root(repo_root)
            except OrgPackEnvVarUnsetError as exc:
                console.print(
                    f"Would fetch pack '[bold]{pack.name}[/bold]' from {origin} "
                    f"— [red]cannot resolve target: {exc}[/red]"
                )
                continue
            console.print(
                f"Would fetch pack '[bold]{pack.name}[/bold]' from {origin} "
                f"into {target}"
            )
        return

    any_failed = False
    for pack in target_packs:
        result = fetch_pack(pack, repo_root)
        if result.ok:
            console.print(
                f"[green]Pack '{pack.name}': {result.artifacts_written} "
                "artifacts[/green]"
            )
            if result.pack_version:
                console.print(f"  Version: {result.pack_version}")
        else:
            console.print(f"[red]Pack '{pack.name}' failed:[/red]")
            for err in result.errors:
                console.print(f"  {err}")
            any_failed = True

    if any_failed:
        raise typer.Exit(1)


# ----------------------------------------------------------------------
# regenerate-graph — deterministic DRG regeneration (FR-009 / WP09 T026)
# ----------------------------------------------------------------------
def _doctrine_root() -> Path:
    """Return the built-in doctrine root that owns the shipped ``graph.yaml``.

    The extractor walks ``<doctrine_root>/directives/built-in`` etc. and writes
    ``<doctrine_root>/graph.yaml``. Regeneration must target the *working-tree*
    source (``src/doctrine``) when invoked from inside a spec-kitty checkout —
    that is the file the freshness gate reads and that a developer commits.

    Resolution order:
      1. Walk up from CWD for a ``src/doctrine`` dir carrying built-in
         artifacts (``directives/built-in``) and a committed ``graph.yaml``.
      2. Fall back to the installed :mod:`doctrine` package directory (e.g. a
         consumer project running the CLI from a non-editable install).
    """
    cwd = Path.cwd().resolve()
    for candidate in [cwd, *cwd.parents]:
        src_doctrine = candidate / "src" / "doctrine"
        if (src_doctrine / "directives" / "built-in").is_dir():
            return src_doctrine

    import doctrine

    return Path(doctrine.__file__).resolve().parent


@app.command(name="regenerate-graph")
def regenerate_graph(
    check: bool = typer.Option(
        False,
        "--check",
        help=(
            "Do not write; regenerate into a temp file and compare against the "
            "committed graph.yaml. Exit 1 when stale (operator-runnable freshness "
            "gate). Exit 0 when fresh."
        ),
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help=_JSON_OPTION_HELP,
    ),
) -> None:
    """Regenerate the shipped DRG ``graph.yaml`` deterministically (FR-009).

    Composes the DRG extractor + calibrator into ``src/doctrine/graph.yaml``.
    Running twice on unchanged inputs yields byte-identical output. With
    ``--check`` the command never writes: it regenerates into a temp file and
    compares against the committed graph, exiting non-zero when stale — the
    operator-facing twin of the ``test_shipped_graph_yaml_is_fresh`` gate.
    """
    import tempfile

    from doctrine.drg.migration.extractor import generate_graph
    from doctrine.drg.validator import DRGValidationError

    doctrine_root = _doctrine_root()
    committed = doctrine_root / "graph.yaml"

    if check:
        with tempfile.TemporaryDirectory() as tmp:
            generated = Path(tmp) / "graph.yaml"
            try:
                generate_graph(doctrine_root, generated)
            except DRGValidationError as exc:
                _emit_regen_result(
                    status="invalid",
                    path=committed,
                    json_output=json_output,
                    detail="; ".join(exc.errors),
                )
                raise typer.Exit(1) from exc
            fresh = generated.read_text(encoding="utf-8") == committed.read_text(
                encoding="utf-8"
            )
        _emit_regen_result(
            status="fresh" if fresh else "stale",
            path=committed,
            json_output=json_output,
        )
        raise typer.Exit(0 if fresh else 1)

    try:
        generate_graph(doctrine_root, committed)
    except DRGValidationError as exc:
        _emit_regen_result(
            status="invalid",
            path=committed,
            json_output=json_output,
            detail="; ".join(exc.errors),
        )
        raise typer.Exit(1) from exc

    _emit_regen_result(status="written", path=committed, json_output=json_output)
    raise typer.Exit(0)


def _emit_regen_result(
    *,
    status: str,
    path: Path,
    json_output: bool,
    detail: str | None = None,
) -> None:
    """Render the regenerate-graph outcome as JSON or rich text."""
    if json_output:
        payload: dict[str, object] = {"status": status, "path": str(path)}
        if detail is not None:
            payload["detail"] = detail
        console.print_json(json.dumps(payload))
        return

    if status == "written":
        console.print(f"[green]Regenerated DRG graph:[/green] {path}")
    elif status == "fresh":
        console.print(f"[green]DRG graph is fresh:[/green] {path}")
    elif status == "stale":
        console.print(
            f"[red]DRG graph is stale:[/red] {path}\n"
            "Run [bold]spec-kitty doctrine regenerate-graph[/bold] and commit the result."
        )
    elif status == "invalid":
        console.print(
            f"[red]DRG graph failed validation:[/red] {detail or '(no detail)'}"
        )


# ----------------------------------------------------------------------
# pack validate
# ----------------------------------------------------------------------
@pack_app.command(name="validate")
def pack_validate(
    pack_path: Path = typer.Argument(
        ...,
        help="Path to the doctrine pack directory to validate.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help=_JSON_OPTION_HELP,
    ),
) -> None:
    """Validate a doctrine pack against schema and DRG constraints.

    Exits 0 when the pack passes validation (advisories do not affect the
    exit code) and 1 when at least one error is reported.
    """
    from specify_cli.doctrine.pack_validator import (
        render_validation_result,
        validate_pack,
    )

    result = validate_pack(pack_path)
    render_validation_result(result, json_output=json_output)
    raise typer.Exit(0 if result.ok else 1)


# ----------------------------------------------------------------------
# pack assemble
# ----------------------------------------------------------------------
@pack_app.command(name="assemble")
def pack_assemble(
    output_path: Path = typer.Argument(
        ...,
        help="Output directory for the assembled distributable pack.",
    ),
    input_packs: list[Path] = typer.Argument(
        ...,
        help="One or more input pack directories to assemble.",
    ),
    conflicts_out: Path | None = typer.Option(
        None,
        "--conflicts-out",
        help="Write the conflict report to this path (JSON).",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help=(
            "Resolve artifact-id conflicts by last-pack-wins and drop "
            "duplicate DRG edges silently."
        ),
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help=_JSON_OPTION_HELP,
    ),
) -> None:
    """Assemble multiple doctrine packs into a single distributable.

    Exits 0 on success and 1 when conflicts block the merge or when the
    assembled output fails validation.
    """
    from specify_cli.doctrine.pack_assembler import (
        assemble_pack,
        render_assembly_result,
    )

    result = assemble_pack(
        input_packs=list(input_packs),
        output_dir=output_path,
        force=force,
        conflicts_out=conflicts_out,
    )
    render_assembly_result(
        result,
        output_dir=output_path,
        input_packs=list(input_packs),
        json_output=json_output,
    )
    raise typer.Exit(0 if result.ok else 1)


# ----------------------------------------------------------------------
# new — scaffold a stub artifact (FR-016 / WP09 T048)
# ----------------------------------------------------------------------

#: Canonical artifact kinds the scaffolder supports. The plural form names the
#: pack-mode directory (``directives/``, ``styleguides/``, …); project mode uses
#: the singular project overlay directories for the runtime-managed kinds. The
#: singular form becomes the YAML filename suffix
#: (``foo.directive.yaml``).  Order is the canonical listing order from
#: the pack contract; consumed by ``--help`` rendering.
_CANONICAL_KIND_SINGULAR_TO_PLURAL: dict[str, str] = {
    "directive": "directives",
    "tactic": "tactics",
    "styleguide": "styleguides",
    "toolguide": "toolguides",
    "paradigm": "paradigms",
    "procedure": "procedures",
    "agent_profile": "agent_profiles",
    "mission_step_contract": "mission_step_contracts",
}

_PROJECT_KIND_DIRS: dict[str, str] = {
    "directive": "directive",
    "tactic": "tactic",
    "styleguide": "styleguide",
    "procedure": "procedure",
}

#: Per-kind stub bodies.  Each stub is the *minimum* YAML payload that
#: passes the corresponding Pydantic schema in ``src/doctrine/*/models.py``
#: when ``<ID>`` is substituted in.  The scaffolder validates the rendered
#: stub against the schema before writing — if a future schema change
#: tightens a required field, the next ``doctrine new`` invocation will
#: surface the mismatch immediately rather than silently scaffolding an
#: invalid file.
def _artifact_filename(kind_singular: str, artifact_id: str) -> str:
    """Return the canonical filename for a doctrine artifact."""
    glob_pattern = ArtifactKind(kind_singular).glob_pattern
    if not glob_pattern.startswith("*"):
        raise ValueError(f"Unsupported artifact kind: {kind_singular}")
    return f"{artifact_id}{glob_pattern.removeprefix('*')}"


def _stub_template(kind_singular: str, artifact_id: str) -> str:
    """Return the canonical YAML stub for ``kind_singular`` populated with ``artifact_id``."""
    if kind_singular == "directive":
        # Directive: id must match [A-Z][A-Z0-9_-]*; intent + title required.
        return (
            f'schema_version: "1.0"\n'
            f"id: {artifact_id}\n"
            f"title: TODO short title\n"
            f"intent: TODO why this directive exists\n"
            f"enforcement: advisory\n"
        )
    if kind_singular == "tactic":
        # Tactic: needs at least one step.
        return (
            f'schema_version: "1.0"\n'
            f"id: {artifact_id}\n"
            f"name: TODO short name\n"
            f"purpose: TODO when to apply this tactic\n"
            f"steps:\n"
            f"  - title: TODO first step\n"
            f"    description: TODO what the step does\n"
        )
    if kind_singular == "styleguide":
        # Styleguide: needs at least one principle (min_length=1).
        return (
            f'schema_version: "1.0"\n'
            f"id: {artifact_id}\n"
            f"title: TODO short title\n"
            f"scope: code\n"
            f"principles:\n"
            f"  - TODO first principle\n"
            f"applies_to_languages: []\n"
        )
    if kind_singular == "toolguide":
        # Toolguide: guide_path must match ^src/doctrine/.+\.md$.
        return (
            f'schema_version: "1.0"\n'
            f"id: {artifact_id}\n"
            f"tool: TODO tool name\n"
            f"title: TODO short title\n"
            f"guide_path: src/doctrine/toolguides/{artifact_id}.md\n"
            f"summary: TODO one-line summary\n"
        )
    if kind_singular == "paradigm":
        return (
            f'schema_version: "1.0"\n'
            f"id: {artifact_id}\n"
            f"name: TODO short name\n"
            f"summary: TODO one-line summary of the paradigm\n"
        )
    if kind_singular == "procedure":
        # Procedure: name + purpose + entry/exit + min 1 step.
        return (
            f'schema_version: "1.0"\n'
            f"id: {artifact_id}\n"
            f"name: TODO short name\n"
            f"purpose: TODO why this procedure exists\n"
            f"entry_condition: TODO when to enter\n"
            f"exit_condition: TODO when complete\n"
            f"steps:\n"
            f"  - title: TODO first step\n"
        )
    if kind_singular == "agent_profile":
        # AgentProfile uses hyphenated YAML aliases (profile-id, schema-version,
        # specialization → {primary-focus, ...}). The model requires roles
        # (min_length=1), purpose, and a Specialization with primary-focus.
        # Reviewers will fill in the full 6-section structure; this stub
        # carries only the schema's hard-required fields.
        return (
            f'schema-version: "1.0"\n'
            f"profile-id: {artifact_id}\n"
            f"name: TODO agent display name\n"
            f"roles: [implementer]\n"
            f"purpose: TODO one-line purpose statement\n"
            f"specialization:\n"
            f"  primary-focus: TODO primary focus area\n"
        )
    if kind_singular == "mission_step_contract":
        return (
            f"id: {artifact_id}\n"
            f'schema_version: "1.0"\n'
            f"action: TODO action verb\n"
            f"mission: TODO mission slug\n"
            f"steps:\n"
            f"  - id: step-1\n"
            f"    description: TODO step description\n"
        )
    # Unreachable — caller validated kind first.
    raise ValueError(f"Unsupported artifact kind: {kind_singular}")


def _resolve_scaffold_root(
    repo_root: Path | None,
    pack: Path | None,
) -> Path:
    """Return the doctrine root that scaffolded files should land under.

    Project-layer scaffolding (no ``--pack``) writes under
    ``<repo_root>/.kittify/doctrine/``. Pack-mode scaffolding writes to the
    user-supplied pack root verbatim.
    """
    if pack is not None:
        return pack
    if repo_root is None:
        raise typer.BadParameter(
            "Could not locate spec-kitty project root. Run from inside a project "
            "containing .kittify/ or pass --pack to target an explicit pack directory."
        )
    return repo_root / ".kittify" / "doctrine"


@app.command(name="new")
def new(
    kind: str = typer.Argument(
        ...,
        help=(
            "Artifact kind (singular): one of "
            + ", ".join(sorted(_CANONICAL_KIND_SINGULAR_TO_PLURAL))
            + "."
        ),
    ),
    artifact_id: str = typer.Argument(
        ...,
        metavar="ID",
        help="Artifact identifier (kebab-case for most kinds; SCREAMING_SNAKE for directives).",
    ),
    pack: Path | None = typer.Option(
        None,
        "--pack",
        help=(
            "Scaffold inside a doctrine pack directory instead of the project layer. "
            "When omitted, the stub lands under .kittify/doctrine/."
        ),
    ),
) -> None:
    """Scaffold a stub doctrine artifact YAML (FR-016).

    The scaffolder pre-fills the canonical schema's required fields with
    ``TODO …`` placeholders so the file passes ``doctrine validate`` on
    first emit.  Refuses to overwrite an existing file.
    """
    kind_singular = kind.strip().lower()
    if kind_singular not in _CANONICAL_KIND_SINGULAR_TO_PLURAL:
        valid = ", ".join(sorted(_CANONICAL_KIND_SINGULAR_TO_PLURAL))
        console.print(
            f"[red]Unknown artifact kind '{kind}'.[/red] "
            f"Expected one of: {valid}."
        )
        raise typer.Exit(2)

    plural = _CANONICAL_KIND_SINGULAR_TO_PLURAL[kind_singular]

    from specify_cli.core.paths import locate_project_root

    repo_root = locate_project_root()
    try:
        doctrine_root = _resolve_scaffold_root(repo_root, pack)
    except typer.BadParameter as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    target_dir_name = (
        plural if pack is not None else _PROJECT_KIND_DIRS.get(kind_singular, plural)
    )
    target_dir = doctrine_root / target_dir_name
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / _artifact_filename(kind_singular, artifact_id)

    if target_path.exists():
        console.print(
            f"[red]Refusing to overwrite existing file:[/red] {target_path}"
        )
        raise typer.Exit(1)

    stub_text = _stub_template(kind_singular, artifact_id)

    # Sanity-check the stub against the schema before writing so a future
    # schema tightening can't silently regress the scaffolder.  The
    # registry in pack_validator is the canonical source of truth.
    from ruamel.yaml import YAML

    from specify_cli.doctrine.pack_validator import _artifact_schema_registry

    schema_cls = _artifact_schema_registry()[plural][1]
    parsed = YAML(typ="safe").load(stub_text)
    try:
        schema_cls.model_validate(parsed)
    except Exception as exc:  # noqa: BLE001 — surface to operator verbatim
        console.print(
            f"[red]Internal error:[/red] stub for kind '{kind_singular}' failed "
            f"schema validation: {exc}"
        )
        raise typer.Exit(1) from exc

    target_path.write_text(stub_text, encoding="utf-8")
    console.print(
        f"[green]Created stub artifact:[/green] {target_path}\n"
        f"Run [bold]spec-kitty doctrine validate {target_path}[/bold] to confirm."
    )


# ----------------------------------------------------------------------
# validate — project-layer artifact / tree validation (FR-017 / WP09 T049)
# ----------------------------------------------------------------------

#: Map filename suffix → ``(plural_dir_name, kind_singular)`` for the
#: ``validate`` command to detect a single file's artifact kind without
#: requiring the operator to pass it explicitly.  Mirrors the suffixes
#: declared in :func:`_artifact_schema_registry`.
_SUFFIX_TO_KIND: dict[str, tuple[str, str]] = {
    ".directive.yaml": ("directives", "directive"),
    ".tactic.yaml": ("tactics", "tactic"),
    ".styleguide.yaml": ("styleguides", "styleguide"),
    ".toolguide.yaml": ("toolguides", "toolguide"),
    ".paradigm.yaml": ("paradigms", "paradigm"),
    ".procedure.yaml": ("procedures", "procedure"),
    ".agent.yaml": ("agent_profiles", "agent_profile"),
    ".step-contract.yaml": ("mission_step_contracts", "mission_step_contract"),
    ".asset.yaml": ("assets", "asset"),
}


def _detect_artifact_kind(path: Path) -> tuple[str, str] | None:
    """Return ``(plural, singular)`` for *path* based on its filename suffix."""
    name = path.name.lower()
    for suffix, kinds in _SUFFIX_TO_KIND.items():
        if name.endswith(suffix):
            return kinds
    return None


#: Sentinel strings that authors mistakenly put in ``applies_to_languages``
#: to mean "applies to all languages".  These are NOT valid language tokens;
#: omitting the field entirely is the correct way to express always-applicable.
_APPLIES_TO_LANGUAGES_SENTINELS: frozenset[str] = frozenset({"any", "all"})


def _check_applies_to_languages(data: dict[str, object]) -> str | None:
    """Return an error message if ``applies_to_languages`` contains a sentinel.

    Checks the raw YAML dict (before Pydantic) so the guard fires regardless
    of artifact kind and gives authors an actionable message instead of a
    generic schema error.
    """
    raw = data.get("applies_to_languages")
    if not isinstance(raw, list):
        return None
    bad = [
        str(token)
        for token in raw
        if isinstance(token, str)
        and token.strip().lower() in _APPLIES_TO_LANGUAGES_SENTINELS
    ]
    if not bad:
        return None
    quoted = ", ".join(f"'{t}'" for t in bad)
    return (
        f"`any`/`all` are not language tokens — "
        f"omit `applies_to_languages` to mean always-applicable "
        f"(found: {quoted})"
    )


def _validate_single_artifact(
    path: Path,
) -> tuple[bool, str | None]:
    """Validate a single artifact YAML file.

    Returns ``(ok, error_message)``.  ``error_message`` is ``None`` on
    success and a human-readable string on failure.
    """
    from ruamel.yaml import YAML
    from ruamel.yaml.error import YAMLError

    from specify_cli.doctrine.pack_validator import _artifact_schema_registry

    detected = _detect_artifact_kind(path)
    if detected is None:
        return False, (
            f"unrecognised artifact filename suffix (expected one of "
            f"{', '.join(sorted(_SUFFIX_TO_KIND))})"
        )
    plural, _singular = detected
    try:
        data = YAML(typ="safe").load(path.read_text(encoding="utf-8"))
    except (YAMLError, OSError) as exc:
        return False, f"YAML parse error: {exc}"
    if data is None:
        return False, "empty YAML document"
    if not isinstance(data, dict):
        return False, "expected a YAML mapping at top level"
    lang_err = _check_applies_to_languages(data)
    if lang_err is not None:
        return False, lang_err
    schema_cls = _artifact_schema_registry()[plural][1]
    try:
        schema_cls.model_validate(data)
    except Exception as exc:  # noqa: BLE001 — schema errors → operator text
        return False, f"schema validation failed: {exc}"
    return True, None


@app.command(name="validate")
def validate(
    path: Path = typer.Argument(
        ...,
        help=(
            "Artifact YAML file or a directory containing project-layer "
            "doctrine artifacts (recurses into per-kind subdirectories)."
        ),
    ),
) -> None:
    """Validate project-layer doctrine artifacts against their schemas (FR-017).

    When *path* is a single file, validates that file.  When *path* is a
    directory, walks the tree for ``*.yaml`` files whose filename suffix
    matches a canonical artifact kind and validates each one.

    Exit code: ``0`` if every artifact validates; ``1`` if any artifact
    fails.  A per-file error report is printed for failures.
    """
    if not path.exists():
        console.print(f"[red]Path not found:[/red] {path}")
        raise typer.Exit(2)

    targets: list[Path] = (
        [path]
        if path.is_file()
        else sorted(p for p in path.rglob("*.yaml") if _detect_artifact_kind(p))
    )

    if not targets:
        console.print(
            f"[yellow]No doctrine artifact files found under {path}.[/yellow]"
        )
        raise typer.Exit(0)

    failures: list[tuple[Path, str]] = []
    for target in targets:
        ok, err = _validate_single_artifact(target)
        if ok:
            console.print(f"[green]OK[/green] {target}")
        else:
            failures.append((target, err or "(no error message)"))
            console.print(f"[red]FAIL[/red] {target}: {err}")

    if failures:
        console.print(
            f"\n[red]{len(failures)} of {len(targets)} artifact(s) failed validation.[/red]"
        )
        raise typer.Exit(1)
    console.print(
        f"\n[green]{len(targets)} artifact(s) passed validation.[/green]"
    )
    raise typer.Exit(0)


# ----------------------------------------------------------------------
# org init — scaffold a minimal org doctrine pack skeleton (FR-006 / WP08)
# ----------------------------------------------------------------------

#: Minimal ``org-charter.yaml`` body.  All fields are optional in
#: :class:`specify_cli.doctrine.org_charter.OrgCharterPolicy`; the stub
#: carries the schema_version sentinel and a TODO org_name as a
#: quickstart hint.
_ORG_CHARTER_STUB = """\
schema_version: "1"
org_name: TODO replace with your organisation name
required_directives: []
required_tactics: []
required_paradigms: []
required_styleguides: []
required_toolguides: []
required_procedures: []
required_agent_profiles: []
required_mission_step_contracts: []
governance_policies: []
activations: []
"""

#: Minimal ``drg/fragment.yaml`` stub.  Carries ``# pydantic_model:`` and
#: ``# expect: valid`` frontmatter so the FR-140 contract round-trip gate
#: exercises it automatically.  The ``source_ref`` placeholder is
#: intentionally ``TODO`` — operators replace it with the pack's real path.
_DRG_FRAGMENT_STUB = """\
# pydantic_model: charter.drg.OrgDRGFragment
# expect: valid
pack_name: TODO replace with your pack name
source_kind: local_path
source_ref: .
layer_index: 1
provenance_marker: org
nodes: []
edges: []
"""

#: Minimal ``README.md`` stub.
_ORG_PACK_README_STUB = """\
# Org Doctrine Pack

> Scaffolded by `spec-kitty doctrine org init`.

## Contents

- `org-charter.yaml` — organisation-level governance policy
- `drg/fragment.yaml` — DRG extension fragment declaring org-tier nodes
- Additional artifact subdirectories (e.g. `directives/`, `tactics/`) may
  be added alongside the `org-charter.yaml`.

## Validation

```bash
spec-kitty doctrine org validate .
```
"""


@org_app.command(name="init")
def org_init(
    pack_path: Path = typer.Argument(
        ...,
        help="Destination directory for the scaffold or rendered doctrine tree.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite an existing pack directory.",
    ),
    template: str | None = typer.Option(
        None,
        "--template",
        help=(
            "Local template directory or git URL (HTTPS/SSH; optional #branch). "
            "When omitted, scaffolds the minimal three-file pack."
        ),
    ),
    org_name: str | None = typer.Option(
        None,
        "--org-name",
        help="Validated org/pack identity for {{ORG_NAME}} (required with --template).",
    ),
    local_path: str | None = typer.Option(
        None,
        "--local-path",
        help="Value for {{LOCAL_PATH}} (default: pack). Distinct from PACK_PATH.",
    ),
    branch: str | None = typer.Option(
        None,
        "--branch",
        help="Git ref when --template is a git URL (may also be encoded in TEMPLATE).",
    ),
) -> None:
    """Scaffold a minimal org pack or render from a template.

    Without ``--template``, creates three files under *pack-path*::

        org-charter.yaml   — governance policy stub
        drg/fragment.yaml  — DRG extension stub (with pydantic_model: frontmatter)
        README.md          — authoring quickstart

    With ``--template``, copies the full template tree (minus ``.templateignore``),
    substitutes ``{{ORG_NAME}}`` / ``{{LOCAL_PATH}}``, and writes under *pack-path*.

    Refuses to overwrite an existing directory unless ``--force`` is passed.
    """
    if template is not None:
        _run_template_render(
            pack_path=pack_path,
            template=template,
            org_name=org_name,
            local_path=local_path,
            branch=branch,
            force=force,
        )
        return
    _run_minimal_scaffold(pack_path, force=force)


def _run_minimal_scaffold(pack_path: Path, *, force: bool) -> None:
    """Write the legacy three-file org pack skeleton."""
    if pack_path.exists() and not force:
        console.print(
            f"[red]Target directory already exists:[/red] {pack_path}\n"
            "Pass [bold]--force[/bold] to overwrite."
        )
        raise typer.Exit(1)

    pack_path.mkdir(parents=True, exist_ok=True)
    (pack_path / "drg").mkdir(parents=True, exist_ok=True)

    (pack_path / "org-charter.yaml").write_text(_ORG_CHARTER_STUB, encoding="utf-8")
    (pack_path / "drg" / "fragment.yaml").write_text(_DRG_FRAGMENT_STUB, encoding="utf-8")
    (pack_path / "README.md").write_text(_ORG_PACK_README_STUB, encoding="utf-8")

    console.print(f"[green]Org pack scaffolded at:[/green] {pack_path}")
    console.print("  org-charter.yaml")
    console.print("  drg/fragment.yaml")
    console.print("  README.md")
    console.print(
        f"\nRun [bold]spec-kitty doctrine org validate {pack_path}[/bold] to confirm."
    )


def _run_template_render(
    *,
    pack_path: Path,
    template: str,
    org_name: str | None,
    local_path: str | None,
    branch: str | None,
    force: bool,
) -> None:
    """Dispatch template render via ``template_render.pipeline``."""
    from specify_cli.doctrine.template_render import RenderRequest
    from specify_cli.doctrine.template_render.pipeline import render_org_pack

    if not org_name:
        console.print(
            "[red]ORG_NAME is required when --template is set[/red] "
            "(org_name.required)."
        )
        raise typer.Exit(1)

    err = render_org_pack(
        RenderRequest(
            pack_path=pack_path,
            template=template,
            org_name=org_name,
            local_path=local_path,
            branch=branch,
            force=force,
        )
    )
    if err is not None:
        console.print(f"[red]{err.message}[/red]")
        raise typer.Exit(1)

    console.print(f"[green]Org doctrine rendered at:[/green] {pack_path}")
    console.print(
        "  Full template tree written (minus .templateignore); "
        "ORG_NAME / LOCAL_PATH tokens substituted."
    )
    console.print(
        f"\nRun [bold]spec-kitty doctrine org validate {pack_path}/pack[/bold] "
        "or your template's quality-check if applicable."
    )


# ----------------------------------------------------------------------
# org validate — validate an org pack against WP06 schema (FR-006 / WP08)
# ----------------------------------------------------------------------


@org_app.command(name="validate")
def org_validate(
    pack_path: Path = typer.Argument(
        ...,
        help="Path to the org doctrine pack directory to validate.",
    ),
) -> None:
    """Validate an org doctrine pack using schema and DRG checks (FR-006).

    Calls the WP06 :func:`specify_cli.doctrine.pack_validator.validate_pack`
    loader.  Prints per-file findings with file paths.  Exits non-zero when
    at least one error is found.
    """
    from specify_cli.doctrine.pack_validator import (
        render_validation_result,
        validate_pack,
    )

    result = validate_pack(pack_path)

    # Additionally validate drg/fragment.yaml against OrgDRGFragment schema
    # (pack_validator covers DRG edge/node cross-refs; this catches
    # kind-constraint violations that pack_validator defers to advisory).
    fragment_path = pack_path / "drg" / "fragment.yaml"
    if fragment_path.exists():
        from ruamel.yaml import YAML
        from ruamel.yaml.error import YAMLError

        try:
            raw = fragment_path.read_text(encoding="utf-8")
            # Strip pydantic_model / expect frontmatter comment lines.
            payload_lines = [
                line for line in raw.splitlines()
                if not line.strip().startswith("#")
            ]
            frag_data = YAML(typ="safe").load("\n".join(payload_lines))
            if frag_data is not None and isinstance(frag_data, dict):
                from charter.drg import OrgDRGFragment
                from pydantic import ValidationError as PydanticValidationError

                try:
                    OrgDRGFragment.model_validate(frag_data)
                except PydanticValidationError as exc:
                    from specify_cli.doctrine.pack_validator import ValidationIssue, ValidationResult

                    extra_error = ValidationIssue(
                        severity="error",
                        artifact_type="drg",
                        artifact_id=frag_data.get("pack_name"),
                        file=str(fragment_path),
                        message=f"OrgDRGFragment schema validation failed: {exc.errors()[0].get('msg', exc)}",
                    )
                    result = ValidationResult(
                        ok=False,
                        errors=[*result.errors, extra_error],
                        advisories=result.advisories,
                    )
        except (YAMLError, OSError):
            pass  # pack_validator already reported YAML parse errors

    render_validation_result(result, json_output=False)
    raise typer.Exit(0 if result.ok else 1)


# ----------------------------------------------------------------------
# mission-type list — enumerate all doctrine-layer mission types (FR-013)
# ----------------------------------------------------------------------

#: Dataclass-free record type for a mission-type row.
class _MissionTypeRow:
    """Lightweight row value object for mission-type list output."""

    __slots__ = ("id", "source_layer", "display_name")

    def __init__(self, id: str, source_layer: str, display_name: str) -> None:  # noqa: A002
        self.id = id
        self.source_layer = source_layer
        self.display_name = display_name


def _collect_built_in_mission_types() -> list[_MissionTypeRow]:
    """Return mission types from the built-in doctrine layer.

    Uses :class:`doctrine.missions.mission_type_repository.MissionTypeRepository`
    to load all built-in mission types.  The display name is taken directly
    from :attr:`~doctrine.missions.models.MissionType.display_name`.
    """
    from doctrine.missions.mission_type_repository import MissionTypeRepository  # noqa: PLC0415

    repo = MissionTypeRepository.default()
    return [
        _MissionTypeRow(
            id=mt.id,
            source_layer="built-in",
            display_name=mt.display_name,
        )
        for mt in repo.load_all()
    ]


@mission_type_app.command("list")
def mission_type_list(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON.",
    ),
) -> None:
    """List all mission types in the doctrine layer (FR-013).

    Enumerates built-in, org, and project mission types regardless of
    activation state.  The DRG resolution chain applies: built-in →
    org → project.  An org type with the same id shadows the built-in
    type; a project type shadows the org type.

    Use ``spec-kitty charter mission-type list`` to see only types that
    are currently activated for this project.
    """
    # Collect built-in types.
    rows: list[_MissionTypeRow] = _collect_built_in_mission_types()

    # Sort: built-in first (already the case), then by id within each layer.
    rows.sort(key=lambda r: (r.source_layer != "built-in", r.id))

    if json_output:
        data = [
            {"id": r.id, "source_layer": r.source_layer, "display_name": r.display_name}
            for r in rows
        ]
        console.print_json(json.dumps(data))
        return

    if not rows:
        console.print("[yellow]No mission types found.[/yellow]")
        raise typer.Exit(0)

    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", style="cyan")
    table.add_column("SOURCE", style="green")
    table.add_column("DISPLAY NAME")

    for row in rows:
        table.add_row(row.id, row.source_layer, row.display_name)

    console.print(table)
    raise typer.Exit(0)
