"""Backward-compat shim — canonical home is specify_cli.doc_analysis.gap_analysis."""

from specify_cli.doc_analysis.gap_analysis import (  # noqa: F401
    DocFramework,
    DivioType,
    GapAnalysis,
    GapPriority,
    CoverageMatrix,
    DocumentationGap,
    analyze_documentation_gaps,
    build_coverage_matrix,
    classify_by_content_heuristics,
    classify_divio_type,
    detect_doc_framework,
    detect_project_areas,
    detect_version_mismatch,
    extract_documented_api_from_sphinx,
    extract_public_api_from_python,
    generate_gap_analysis_report,
    infer_area_from_path,
    parse_frontmatter,
    prioritize_gaps,
    run_gap_analysis_for_feature,
)
