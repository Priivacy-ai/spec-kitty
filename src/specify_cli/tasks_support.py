"""Backward-compat shim — canonical home is specify_cli.task_utils.

All symbols re-exported here are now in specify_cli.task_utils.support.
Update imports to: from specify_cli.task_utils import <symbol>
"""

from specify_cli.task_utils.support import (  # noqa: F401
    LANE_ALIASES,
    LANES,
    TIMESTAMP_FORMAT,
    TaskCliError,
    WorkPackage,
    activity_entries,
    append_activity_log,
    build_document,
    detect_conflicting_wp_status,
    ensure_lane,
    extract_scalar,
    find_repo_root,
    get_lane_from_frontmatter,
    git_status_lines,
    is_legacy_format,
    load_meta,
    locate_work_package,
    match_frontmatter_line,
    normalize_note,
    now_utc,
    run_git,
    set_scalar,
    split_frontmatter,
)
