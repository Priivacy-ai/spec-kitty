"""CLI distribution identity and upgrade-source resolvers for packager hooks.

Stock Spec Kitty registers nothing under these entry-point groups. Absence of
registrations preserves public-PyPI / ``spec-kitty-cli`` behaviour.
"""

from __future__ import annotations

from specify_cli.distribution.installed_version import (
    resolve_installed_distribution_version,
)
from specify_cli.distribution.package_name import (
    CLI_PACKAGE_GROUP,
    DEFAULT_CLI_PACKAGE_NAME,
    clear_cli_package_name_cache,
    resolve_cli_package_name,
)
from specify_cli.distribution.profile import (
    DISTRIBUTION_PROFILE_GROUP,
    DistributionProfile,
    clear_distribution_profile_cache,
    resolve_distribution_profile,
    stock_distribution_profile,
)
from specify_cli.distribution.upgrade_provider import (
    PROVIDER_SELECT_ENV_VAR,
    UPGRADE_PROVIDER_GROUP,
    clear_upgrade_provider_cache,
    resolve_upgrade_provider,
)

__all__ = [
    "CLI_PACKAGE_GROUP",
    "DEFAULT_CLI_PACKAGE_NAME",
    "DISTRIBUTION_PROFILE_GROUP",
    "DistributionProfile",
    "PROVIDER_SELECT_ENV_VAR",
    "UPGRADE_PROVIDER_GROUP",
    "clear_cli_package_name_cache",
    "clear_distribution_profile_cache",
    "clear_upgrade_provider_cache",
    "resolve_cli_package_name",
    "resolve_distribution_profile",
    "resolve_installed_distribution_version",
    "resolve_upgrade_provider",
    "stock_distribution_profile",
]
