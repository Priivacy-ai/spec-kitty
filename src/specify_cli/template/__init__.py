"""Template management for spec-kitty."""

from .manager import (
    copy_package_tree,
    copy_specify_base_from_local,
    copy_specify_base_from_package,
    get_local_repo_root,
)
from .renderer import (
    DEFAULT_PATH_PATTERNS,
    parse_frontmatter,
    render_template,
    rewrite_paths,
)
from .asset_generator import (
    generate_agent_assets,
    render_command_template,
)
from .github_client import (
    GitHubClientError,
    SSL_CONTEXT,
    build_http_client,
    download_and_extract_template,
    download_template_from_github,
    parse_repo_slug,
)

__all__ = [
    "GitHubClientError",
    "SSL_CONTEXT",
    "build_http_client",
    "copy_package_tree",
    "copy_specify_base_from_local",
    "copy_specify_base_from_package",
    "DEFAULT_PATH_PATTERNS",
    "download_and_extract_template",
    "download_template_from_github",
    "generate_agent_assets",
    "get_local_repo_root",
    "parse_frontmatter",
    "parse_repo_slug",
    "render_command_template",
    "render_template",
    "rewrite_paths",
]
