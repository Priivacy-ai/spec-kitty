"""GitHub template download and extraction helpers."""

from __future__ import annotations

import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Tuple

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

import ssl
import truststore

from specify_cli.cli import StepTracker


class GitHubClientError(RuntimeError):
    """Raised when GitHub template operations fail."""


SSL_CONTEXT = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
DEFAULT_CONSOLE = Console()


def build_http_client(*, skip_tls: bool = False) -> httpx.Client:
    """Create a default httpx client honoring TLS verification flags."""
    verify = SSL_CONTEXT if not skip_tls else False
    return httpx.Client(verify=verify)


def _github_token(cli_token: str | None = None) -> str | None:
    """Return sanitized GitHub token (CLI argument takes precedence)."""
    token = (cli_token or os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN") or "").strip()
    return token or None


def _github_auth_headers(cli_token: str | None = None) -> dict[str, str]:
    """Return Authorization header dict only when a non-empty token exists."""
    token = _github_token(cli_token)
    return {"Authorization": f"Bearer {token}"} if token else {}


def parse_repo_slug(slug: str) -> tuple[str, str]:
    """Return (owner, repo) tuple for strings like 'owner/name'."""
    parts = slug.strip().split("/")
    if len(parts) != 2 or not all(parts):
        raise ValueError(f"Invalid GitHub repo slug '{slug}'. Expected format owner/name")
    return parts[0], parts[1]


def download_template_from_github(
    repo_owner: str,
    repo_name: str,
    ai_assistant: str,
    download_dir: Path,
    *,
    script_type: str = "sh",
    verbose: bool = True,
    show_progress: bool = True,
    client: httpx.Client | None = None,
    debug: bool = False,
    github_token: str | None = None,
    console: Console | None = None,
) -> Tuple[Path, dict]:
    """Download the release asset for the requested AI assistant."""
    console = console or DEFAULT_CONSOLE
    client = client or build_http_client()

    if verbose:
        console.print("[cyan]Fetching latest release information...[/cyan]")
    api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"

    try:
        response = client.get(
            api_url,
            timeout=30,
            follow_redirects=True,
            headers=_github_auth_headers(github_token),
        )
        status = response.status_code
        if status != 200:
            msg = f"GitHub API returned {status} for {api_url}"
            if debug:
                msg += f"\nResponse headers: {response.headers}\nBody (truncated 500): {response.text[:500]}"
            raise GitHubClientError(msg)
        try:
            release_data = response.json()
        except ValueError as exc:
            raise GitHubClientError(
                f"Failed to parse release JSON: {exc}\nRaw (truncated 400): {response.text[:400]}"
            ) from exc
    except GitHubClientError:
        raise
    except Exception as exc:
        console.print("[red]Error fetching release information[/red]")
        console.print(Panel(str(exc), title="Fetch Error", border_style="red"))
        raise GitHubClientError(str(exc)) from exc

    assets = release_data.get("assets", [])
    pattern = f"spec-kitty-template-{ai_assistant}-{script_type}"
    matching_assets = [
        asset for asset in assets if pattern in asset.get("name", "") and asset.get("name", "").endswith(".zip")
    ]
    asset = matching_assets[0] if matching_assets else None
    if asset is None:
        asset_names = [a.get("name", "?") for a in assets]
        console.print(
            f"[red]No matching release asset found[/red] for [bold]{ai_assistant}[/bold] "
            f"(expected pattern: [bold]{pattern}[/bold])"
        )
        console.print(Panel("\n".join(asset_names) or "(no assets)", title="Available Assets", border_style="yellow"))
        raise GitHubClientError("No matching release asset found")

    download_url = asset["browser_download_url"]
    filename = asset["name"]
    file_size = asset["size"]

    if verbose:
        console.print(f"[cyan]Found template:[/cyan] {filename}")
        console.print(f"[cyan]Size:[/cyan] {file_size:,} bytes")
        console.print(f"[cyan]Release:[/cyan] {release_data['tag_name']}")

    zip_path = download_dir / filename
    if verbose:
        console.print("[cyan]Downloading template...[/cyan]")

    try:
        with client.stream(
            "GET",
            download_url,
            timeout=60,
            follow_redirects=True,
            headers=_github_auth_headers(github_token),
        ) as response:
            if response.status_code != 200:
                body_sample = response.text[:400]
                raise GitHubClientError(
                    f"Download failed with {response.status_code}\\nHeaders: {response.headers}\\nBody (truncated): {body_sample}"
                )
            total_size = int(response.headers.get("content-length", 0))
            with open(zip_path, "wb") as fh:
                if total_size == 0 or not show_progress:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        fh.write(chunk)
                else:
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                        console=console,
                    ) as progress:
                        task = progress.add_task("Downloading...", total=total_size)
                        downloaded = 0
                        for chunk in response.iter_bytes(chunk_size=8192):
                            fh.write(chunk)
                            downloaded += len(chunk)
                            progress.update(task, completed=downloaded)
    except GitHubClientError:
        if zip_path.exists():
            zip_path.unlink()
        raise
    except Exception as exc:
        if zip_path.exists():
            zip_path.unlink()
        console.print("[red]Error downloading template[/red]")
        console.print(Panel(str(exc), title="Download Error", border_style="red"))
        raise GitHubClientError(str(exc)) from exc

    if verbose:
        console.print(f"Downloaded: {filename}")
    metadata = {
        "filename": filename,
        "size": file_size,
        "release": release_data["tag_name"],
        "asset_url": download_url,
    }
    return zip_path, metadata


def download_and_extract_template(
    project_path: Path,
    ai_assistant: str,
    script_type: str,
    is_current_dir: bool = False,
    *,
    verbose: bool = True,
    tracker: StepTracker | None = None,
    tracker_prefix: str | None = None,
    allow_existing: bool = False,
    client: httpx.Client | None = None,
    debug: bool = False,
    github_token: str | None = None,
    repo_owner: str = "spec-kitty",
    repo_name: str = "spec-kitty",
    console: Console | None = None,
) -> Path:
    """Download the latest release and extract it to create a new project."""
    console = console or DEFAULT_CONSOLE
    current_dir = Path.cwd()

    def tk(step: str) -> str:
        return f"{tracker_prefix}-{step}" if tracker_prefix else step

    if tracker:
        tracker.start(tk("fetch"), "contacting GitHub API")
    try:
        zip_path, meta = download_template_from_github(
            repo_owner,
            repo_name,
            ai_assistant,
            current_dir,
            script_type=script_type,
            verbose=verbose and tracker is None,
            show_progress=(tracker is None),
            client=client,
            debug=debug,
            github_token=github_token,
            console=console,
        )
        if tracker:
            tracker.complete(tk("fetch"), f"release {meta['release']} ({meta['size']:,} bytes)")
            tracker.add(tk("download"), "Download template")
            tracker.complete(tk("download"), meta["filename"])
    except GitHubClientError:
        if tracker:
            tracker.error(tk("fetch"), "failed")
        raise

    if tracker:
        tracker.add(tk("extract"), "Extract template")
        tracker.start(tk("extract"))
    elif verbose:
        console.print("Extracting template...")

    temp_dir: Path | None = None
    try:
        if not is_current_dir:
            project_path.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            names = zip_ref.namelist()
            if tracker:
                tracker.start(tk("zip-list"))
                tracker.complete(tk("zip-list"), f"{len(names)} entries")
            elif verbose:
                console.print(f"[cyan]ZIP contains {len(names)} items[/cyan]")

            temp_dir = Path(tempfile.mkdtemp())
            zip_ref.extractall(temp_dir)

            extracted_items = list(temp_dir.iterdir())
            if tracker:
                tracker.start(tk("extracted-summary"))
                tracker.complete(tk("extracted-summary"), f"temp {len(extracted_items)} items")
            elif verbose:
                console.print(f"[cyan]Extracted {len(extracted_items)} items to temp location[/cyan]")

            source_dir = extracted_items[0] if len(extracted_items) == 1 and extracted_items[0].is_dir() else temp_dir
            if source_dir is not temp_dir:
                if tracker:
                    tracker.add(tk("flatten"), "Flatten nested directory")
                    tracker.complete(tk("flatten"))
                elif verbose:
                    console.print("[cyan]Found nested directory structure[/cyan]")

            if is_current_dir or allow_existing:
                _merge_tree(source_dir, project_path, console, verbose and not tracker)
            else:
                # For new project directories, we need to move the contents not the directory itself
                # Create the project_path first if it doesn't exist
                project_path.mkdir(parents=True, exist_ok=True)
                # Move each item from source_dir into project_path
                for item in source_dir.iterdir():
                    dest_item = project_path / item.name
                    shutil.move(str(item), str(dest_item))
    except Exception as exc:
        if tracker:
            tracker.error(tk("extract"), str(exc))
        else:
            console.print("[red]Error extracting template[/red]")
            console.print(Panel(str(exc), title="Extraction Error", border_style="red"))
        if not is_current_dir and project_path.exists():
            shutil.rmtree(project_path)
        raise GitHubClientError(str(exc)) from exc
    finally:
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        if tracker:
            tracker.add(tk("cleanup"), "Remove temporary archive")
        if zip_path.exists():
            zip_path.unlink()
            if tracker:
                tracker.complete(tk("cleanup"), meta["filename"])
            elif verbose:
                console.print(f"Cleaned up: {zip_path.name}")
        elif tracker:
            tracker.complete(tk("cleanup"), "skipped")

    if tracker:
        tracker.complete(tk("extract"), "done")
    elif verbose:
        console.print(f"[cyan]Template files {'merged' if is_current_dir else 'extracted'}[/cyan]")

    return project_path



def _merge_tree(source_dir: Path, dest_dir: Path, console: Console, verbose: bool) -> None:
    """Merge directory contents from source into destination."""
    for item in source_dir.iterdir():
        dest_path = dest_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dest_path, dirs_exist_ok=True)
        else:
            if dest_path.exists() and verbose:
                console.print(f"[yellow]Overwriting file:[/yellow] {item.name}")
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest_path)


__all__ = [
    "GitHubClientError",
    "SSL_CONTEXT",
    "build_http_client",
    "download_and_extract_template",
    "download_template_from_github",
    "parse_repo_slug",
]
