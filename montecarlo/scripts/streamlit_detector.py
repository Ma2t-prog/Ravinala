#!/usr/bin/env python3
"""
Streamlit Detector
==================
Scans the ENTIRE project for any traces of Streamlit that need to be migrated
to React. Produces a migration completeness score.

Usage:
    python scripts/streamlit_detector.py [--detailed] [--output FILE]
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"
PAGES_DIR = SRC_DIR / "pages"
FRONTEND_DIR = SRC_DIR / "frontend"

# Directories to skip
SKIP_DIRS = {
    "node_modules", "__pycache__", ".git", ".venv", "venv", "env",
    ".tox", ".mypy_cache", ".pytest_cache", "dist", "build",
    "ravinala.egg-info", ".egg-info",
}

# Patterns
STREAMLIT_IMPORT_PATTERNS = [
    re.compile(r'^import\s+streamlit\b', re.MULTILINE),
    re.compile(r'^from\s+streamlit\b', re.MULTILINE),
    re.compile(r'^import\s+streamlit\s+as\s+\w+', re.MULTILINE),
]

STREAMLIT_USAGE_PATTERNS = [
    (re.compile(r'\bst\.(\w+)\s*\('), "st.{func}() call"),
    (re.compile(r'\bst\.sidebar\b'), "st.sidebar usage"),
    (re.compile(r'\bst\.session_state\b'), "st.session_state usage"),
    (re.compile(r'\bst\.cache_data\b'), "st.cache_data decorator"),
    (re.compile(r'\bst\.cache_resource\b'), "st.cache_resource decorator"),
    (re.compile(r'\bst\.experimental_\w+\b'), "st.experimental_ usage"),
    (re.compile(r'\bst\.set_page_config\b'), "st.set_page_config call"),
    (re.compile(r'\bst\.columns\b'), "st.columns layout"),
    (re.compile(r'\bst\.tabs\b'), "st.tabs layout"),
    (re.compile(r'\bst\.expander\b'), "st.expander widget"),
    (re.compile(r'\bst\.form\b'), "st.form widget"),
    (re.compile(r'\bst\.plotly_chart\b'), "st.plotly_chart (needs React chart)"),
    (re.compile(r'\bst\.dataframe\b'), "st.dataframe (needs React table)"),
    (re.compile(r'\bst\.data_editor\b'), "st.data_editor (needs React table)"),
    (re.compile(r'\bst\.metric\b'), "st.metric (needs React component)"),
    (re.compile(r'\bst\.(?:text_input|number_input|selectbox|multiselect|slider|checkbox|radio|text_area|date_input|time_input|file_uploader|color_picker)\b'),
     "st.input widget (needs React form)"),
    (re.compile(r'\bst\.(?:button|download_button|link_button)\b'), "st.button (needs React button)"),
    (re.compile(r'\bst\.(?:write|markdown|title|header|subheader|text|caption|code|latex|divider)\b'),
     "st.display (needs React component)"),
    (re.compile(r'\bst\.(?:success|error|warning|info|exception|toast)\b'),
     "st.notification (needs React toast/alert)"),
    (re.compile(r'\bst\.(?:spinner|progress|balloons|snow)\b'),
     "st.feedback (needs React equivalent)"),
    (re.compile(r'\bStreamlitAPIException\b'), "StreamlitAPIException reference"),
]

STREAMLIT_CONFIG_FILES = [
    ".streamlit/config.toml",
    ".streamlit/secrets.toml",
    ".streamlit/credentials.toml",
    "streamlit_app.py",
    "app_streamlit.py",
]

REQUIREMENTS_STREAMLIT_RE = re.compile(r'^streamlit\b', re.MULTILINE | re.IGNORECASE)


def should_skip(path: Path) -> bool:
    """Check if a path should be skipped."""
    parts = path.parts
    return any(skip in parts for skip in SKIP_DIRS)


def scan_file_for_streamlit(filepath: Path) -> dict | None:
    """Scan a single file for Streamlit traces."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    findings = {
        "file": str(filepath.relative_to(PROJECT_ROOT)),
        "has_import": False,
        "imports": [],
        "usages": [],
        "usage_count": 0,
        "line_count": content.count('\n') + 1,
        "unique_st_functions": set(),
    }

    # Check imports
    for pattern in STREAMLIT_IMPORT_PATTERNS:
        for match in pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            findings["has_import"] = True
            findings["imports"].append({
                "line": line_num,
                "text": match.group().strip(),
            })

    # Check usage patterns
    for pattern, description in STREAMLIT_USAGE_PATTERNS:
        for match in pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            line_text = content.splitlines()[line_num - 1].strip() if line_num <= len(content.splitlines()) else ""
            findings["usages"].append({
                "line": line_num,
                "type": description,
                "text": line_text[:120],
            })
            findings["usage_count"] += 1
            # Track unique st.X functions
            func_match = re.search(r'st\.(\w+)', match.group())
            if func_match:
                findings["unique_st_functions"].add(func_match.group(1))

    # Convert set to list for JSON serialization
    findings["unique_st_functions"] = sorted(findings["unique_st_functions"])

    if findings["has_import"] or findings["usages"]:
        return findings
    return None


def scan_requirements(project_root: Path) -> list[dict]:
    """Scan requirements files for Streamlit dependency."""
    results = []
    req_files = list(project_root.rglob("requirements*.txt")) + list(project_root.rglob("pyproject.toml"))

    for req_file in req_files:
        if should_skip(req_file):
            continue
        try:
            content = req_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        if REQUIREMENTS_STREAMLIT_RE.search(content) or "streamlit" in content.lower():
            lines = content.splitlines()
            for i, line in enumerate(lines, 1):
                if "streamlit" in line.lower():
                    results.append({
                        "file": str(req_file.relative_to(project_root)),
                        "line": i,
                        "text": line.strip(),
                    })
    return results


def scan_config_files(project_root: Path) -> list[dict]:
    """Find Streamlit config files."""
    results = []
    for config in STREAMLIT_CONFIG_FILES:
        config_path = project_root / config
        if config_path.exists():
            results.append({
                "file": config,
                "size_bytes": config_path.stat().st_size,
            })

    # Also check for .streamlit directory
    streamlit_dir = project_root / ".streamlit"
    if streamlit_dir.exists() and streamlit_dir.is_dir():
        for f in streamlit_dir.iterdir():
            rel = str(f.relative_to(project_root))
            if not any(r["file"] == rel for r in results):
                results.append({
                    "file": rel,
                    "size_bytes": f.stat().st_size if f.is_file() else 0,
                })

    return results


def find_python_pages(pages_dir: Path) -> list[dict]:
    """Find Python files in pages/ that should be React TSX."""
    results = []
    if not pages_dir.exists():
        return results

    for py_file in sorted(pages_dir.glob("*.py")):
        if py_file.name == "__init__.py":
            continue

        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        has_streamlit = any(p.search(content) for p in STREAMLIT_IMPORT_PATTERNS)
        st_count = sum(len(p.findall(content)) for p, _ in STREAMLIT_USAGE_PATTERNS)

        # Check if a corresponding .tsx exists
        tsx_name = py_file.stem + ".tsx"
        tsx_candidates = list(FRONTEND_DIR.rglob(tsx_name)) if FRONTEND_DIR.exists() else []
        has_tsx_equivalent = len(tsx_candidates) > 0

        results.append({
            "file": str(py_file.relative_to(PROJECT_ROOT)),
            "name": py_file.stem,
            "lines": content.count('\n') + 1,
            "has_streamlit": has_streamlit,
            "streamlit_usage_count": st_count,
            "has_tsx_equivalent": has_tsx_equivalent,
            "tsx_equivalent": str(tsx_candidates[0].relative_to(PROJECT_ROOT)) if tsx_candidates else None,
            "migration_status": "DONE" if has_tsx_equivalent else ("NEEDS_MIGRATION" if has_streamlit else "PYTHON_ONLY"),
        })

    return results


def compute_migration_score(
    streamlit_files: list[dict],
    python_pages: list[dict],
    config_files: list[dict],
    req_references: list[dict],
) -> dict:
    """Compute overall migration completeness score."""
    total_issues = 0
    resolved = 0

    # Python pages
    for page in python_pages:
        total_issues += 1
        if page["has_tsx_equivalent"]:
            resolved += 1

    # Streamlit traces in code
    total_issues += len(streamlit_files)
    # None resolved (they still exist)

    # Config files
    total_issues += len(config_files)

    # Requirements
    total_issues += len(req_references)

    if total_issues == 0:
        pct = 100.0
    else:
        pct = (resolved / total_issues) * 100

    return {
        "total_issues": total_issues,
        "resolved": resolved,
        "remaining": total_issues - resolved,
        "completion_pct": round(pct, 1),
    }


def main():
    parser = argparse.ArgumentParser(description="Streamlit Detector")
    parser.add_argument("--detailed", action="store_true", help="Show detailed per-file analysis")
    parser.add_argument("--output", type=str, help="Output JSON report to file")
    args = parser.parse_args()

    print("=" * 70)
    print("  STREAMLIT DETECTOR")
    print(f"  Project: {PROJECT_ROOT}")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # --- Scan ALL Python files ---
    print("\n--- SCANNING FOR STREAMLIT TRACES ---")
    streamlit_files = []
    total_scanned = 0

    for py_file in PROJECT_ROOT.rglob("*.py"):
        if should_skip(py_file):
            continue
        total_scanned += 1
        result = scan_file_for_streamlit(py_file)
        if result:
            streamlit_files.append(result)

    print(f"  Scanned {total_scanned} Python files")
    print(f"  Files with Streamlit traces: {len(streamlit_files)}")

    total_usages = sum(f["usage_count"] for f in streamlit_files)
    total_imports = sum(1 for f in streamlit_files if f["has_import"])
    print(f"  Files with Streamlit imports: {total_imports}")
    print(f"  Total Streamlit usages: {total_usages}")

    # Group by directory
    dir_groups = defaultdict(list)
    for f in streamlit_files:
        parts = Path(f["file"]).parts
        dir_key = parts[0] if len(parts) > 1 else "root"
        dir_groups[dir_key].append(f)

    print(f"\n  By directory:")
    for dir_name, files in sorted(dir_groups.items(), key=lambda x: -len(x[1])):
        usages = sum(f["usage_count"] for f in files)
        print(f"    {dir_name}/: {len(files)} files, {usages} usages")

    if args.detailed:
        print(f"\n--- DETAILED FILE ANALYSIS ---")
        for f in sorted(streamlit_files, key=lambda x: -x["usage_count"]):
            print(f"\n  {f['file']} ({f['line_count']} lines)")
            if f["has_import"]:
                for imp in f["imports"]:
                    print(f"    IMPORT L{imp['line']}: {imp['text']}")
            if f["unique_st_functions"]:
                print(f"    Functions: st.{', st.'.join(f['unique_st_functions'])}")
            print(f"    Total usages: {f['usage_count']}")
            if f["usages"] and args.detailed:
                for usage in f["usages"][:10]:
                    print(f"    L{usage['line']:4d} [{usage['type']}] {usage['text'][:80]}")
                if len(f["usages"]) > 10:
                    print(f"    ... and {len(f['usages']) - 10} more")

    # --- Python pages needing migration ---
    print(f"\n--- PYTHON PAGES ANALYSIS ---")
    python_pages = find_python_pages(PAGES_DIR)
    print(f"  Total Python page files: {len(python_pages)}")

    needs_migration = [p for p in python_pages if p["migration_status"] == "NEEDS_MIGRATION"]
    done = [p for p in python_pages if p["migration_status"] == "DONE"]
    python_only = [p for p in python_pages if p["migration_status"] == "PYTHON_ONLY"]

    print(f"  Already migrated (has TSX): {len(done)}")
    print(f"  Needs migration (has Streamlit): {len(needs_migration)}")
    print(f"  Python-only (no Streamlit): {len(python_only)}")

    if needs_migration:
        print(f"\n  Pages to migrate:")
        for p in sorted(needs_migration, key=lambda x: -x["streamlit_usage_count"]):
            print(f"    {p['name']:40s} {p['lines']:5d} lines, {p['streamlit_usage_count']:3d} st. calls")

    # --- Config files ---
    print(f"\n--- STREAMLIT CONFIG FILES ---")
    config_files = scan_config_files(PROJECT_ROOT)
    if config_files:
        for cf in config_files:
            print(f"  {cf['file']} ({cf['size_bytes']} bytes)")
    else:
        print("  None found. Good!")

    # --- Requirements ---
    print(f"\n--- REQUIREMENTS REFERENCES ---")
    req_references = scan_requirements(PROJECT_ROOT)
    if req_references:
        for ref in req_references:
            print(f"  {ref['file']}:{ref['line']}: {ref['text']}")
    else:
        print("  No streamlit in requirements. Good!")

    # --- Unique st.X functions used ---
    all_funcs = set()
    for f in streamlit_files:
        all_funcs.update(f["unique_st_functions"])

    if all_funcs:
        print(f"\n--- ALL UNIQUE st.X FUNCTIONS USED ({len(all_funcs)}) ---")
        # Group by category
        categories = {
            "Layout": {"columns", "tabs", "sidebar", "container", "expander", "empty"},
            "Input": {"text_input", "number_input", "selectbox", "multiselect", "slider",
                      "checkbox", "radio", "text_area", "date_input", "time_input",
                      "file_uploader", "color_picker", "button", "download_button", "form"},
            "Display": {"write", "markdown", "title", "header", "subheader", "text",
                        "caption", "code", "latex", "divider", "metric"},
            "Charts": {"plotly_chart", "altair_chart", "pyplot", "vega_lite_chart",
                       "bar_chart", "line_chart", "area_chart", "map"},
            "Data": {"dataframe", "data_editor", "table", "json"},
            "Status": {"success", "error", "warning", "info", "exception", "toast",
                       "spinner", "progress", "balloons", "snow"},
            "Config": {"set_page_config", "cache_data", "cache_resource", "session_state"},
        }

        for cat_name, cat_funcs in categories.items():
            found = sorted(all_funcs & cat_funcs)
            if found:
                print(f"  {cat_name}: {', '.join('st.' + f for f in found)}")

        uncategorized = all_funcs - set().union(*categories.values())
        if uncategorized:
            print(f"  Other: {', '.join('st.' + f for f in sorted(uncategorized))}")

    # --- Migration Score ---
    score = compute_migration_score(streamlit_files, python_pages, config_files, req_references)

    print(f"\n{'=' * 70}")
    print(f"  MIGRATION SCORE: {score['completion_pct']}% COMPLETE")
    print(f"  Total issues: {score['total_issues']}")
    print(f"  Resolved: {score['resolved']}")
    print(f"  Remaining: {score['remaining']}")

    # Visual bar
    filled = int(score['completion_pct'] / 2)
    bar = "#" * filled + "." * (50 - filled)
    print(f"  [{bar}] {score['completion_pct']}%")

    if score['remaining'] > 0:
        print(f"\n  WHAT REMAINS:")
        if needs_migration:
            print(f"    - {len(needs_migration)} Python pages to convert to TSX")
        if streamlit_files:
            print(f"    - {len(streamlit_files)} files still reference Streamlit")
        if config_files:
            print(f"    - {len(config_files)} Streamlit config files to remove")
        if req_references:
            print(f"    - {len(req_references)} requirements entries to remove")
    else:
        print(f"\n  MIGRATION COMPLETE! No Streamlit traces found.")

    print(f"{'=' * 70}")

    # JSON report
    full_report = {
        "timestamp": datetime.now().isoformat(),
        "project_root": str(PROJECT_ROOT),
        "migration_score": score,
        "summary": {
            "files_scanned": total_scanned,
            "files_with_streamlit": len(streamlit_files),
            "total_streamlit_usages": total_usages,
            "files_with_imports": total_imports,
            "python_pages_total": len(python_pages),
            "pages_needing_migration": len(needs_migration),
            "pages_migrated": len(done),
            "config_files": len(config_files),
            "requirement_references": len(req_references),
            "unique_st_functions": sorted(all_funcs),
        },
        "streamlit_files": [
            {k: v for k, v in f.items()}
            for f in streamlit_files
        ],
        "python_pages": python_pages,
        "config_files": config_files,
        "requirement_references": req_references,
    }

    report_path = Path(args.output) if args.output else PROJECT_ROOT / "tmp" / "streamlit_detector_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(full_report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  JSON report saved to: {report_path}")

    # Exit code: non-zero if Streamlit traces remain
    sys.exit(0 if score["remaining"] == 0 else 1)


if __name__ == "__main__":
    main()
