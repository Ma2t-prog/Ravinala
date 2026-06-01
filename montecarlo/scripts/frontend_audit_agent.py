#!/usr/bin/env python3
"""
Frontend Audit Agent
====================
Audits the entire React frontend for migration quality, code health,
and backend connectivity.

Usage:
    python scripts/frontend_audit_agent.py [--fix-hints] [--verbose] [--page NomPage]
"""

import argparse
import ast
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Project paths (auto-detected relative to this script)
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"
FRONTEND_DIR = SRC_DIR / "frontend"
PAGES_DIR = SRC_DIR / "pages"
BACKEND_ROUTES_DIR = PROJECT_ROOT / "backend" / "app" / "routes"

# Patterns
STREAMLIT_IMPORT_RE = re.compile(r'\b(?:import\s+streamlit|from\s+streamlit|import\s+streamlit\s+as\s+st)\b')
STREAMLIT_USAGE_RE = re.compile(r'\bst\.\w+')
FETCH_CALL_RE = re.compile(r'\b(?:fetch|axios|api\.|apiClient|useQuery|useMutation|apiService)\s*[\.(]')
HARDCODED_DATA_RE = re.compile(
    r'(?:const|let|var)\s+\w+\s*(?::\s*\w+(?:\[\])?\s*)?=\s*\[(?:\s*\{[^}]{30,}\})',
    re.DOTALL
)
HTML_RAW_RE = re.compile(r'<(?:div|span|table|tr|td|th|form|input|button|select|h[1-6])\b[^>]*>')
CONSOLE_LOG_RE = re.compile(r'\bconsole\.\w+\s*\(')
ANY_TYPE_RE = re.compile(r':\s*any\b|<any>|as\s+any\b')
ROUTE_DEF_RE = re.compile(r'<Route\s+[^>]*path\s*=\s*["\']([^"\']+)["\']')
COMPONENT_IMPORT_RE = re.compile(r'import\s+(?:\{[^}]+\}|\w+)\s+from\s+["\']([^"\']+)["\']')


def find_tsx_jsx_files(root: Path) -> list[Path]:
    """Find all .tsx and .jsx files recursively."""
    files = []
    for ext in ("*.tsx", "*.jsx"):
        files.extend(root.rglob(ext))
    return sorted(files)


def find_py_pages(pages_dir: Path) -> list[Path]:
    """Find .py files in the pages directory that should be .tsx."""
    if not pages_dir.exists():
        return []
    return sorted(p for p in pages_dir.glob("*.py") if p.name != "__init__.py")


def check_streamlit_in_tsx(content: str) -> list[str]:
    """Detect leftover Streamlit references in TSX/JSX files."""
    issues = []
    for i, line in enumerate(content.splitlines(), 1):
        if STREAMLIT_IMPORT_RE.search(line):
            issues.append(f"Line {i}: Streamlit import detected: {line.strip()}")
        if STREAMLIT_USAGE_RE.search(line):
            issues.append(f"Line {i}: Streamlit usage detected: {line.strip()}")
    return issues


def check_backend_connection(content: str) -> dict:
    """Check if a page connects to the backend."""
    matches = FETCH_CALL_RE.findall(content)
    has_loading = bool(re.search(r'\b(?:loading|isLoading|pending|isFetching)\b', content))
    has_error_handling = bool(re.search(r'\b(?:catch|error|isError|onError|Error)\b', content))
    return {
        "has_api_calls": len(matches) > 0,
        "api_call_count": len(matches),
        "has_loading_state": has_loading,
        "has_error_handling": has_error_handling,
    }


def check_common_components(content: str) -> dict:
    """Check usage of common React components vs raw HTML."""
    raw_html_count = len(HTML_RAW_RE.findall(content))
    imports = COMPONENT_IMPORT_RE.findall(content)
    uses_common_components = any(
        imp for imp in imports
        if any(kw in imp for kw in ("components", "common", "shared", "ui", "layout"))
    )
    has_tabs = bool(re.search(r'\b(?:Tabs|TabPanel|TabList|Tab)\b', content))
    has_breadcrumb = bool(re.search(r'\b(?:Breadcrumb|breadcrumb)\b', content, re.IGNORECASE))
    has_title = bool(re.search(r'<(?:h1|Title|PageTitle|PageHeader)\b', content))
    return {
        "raw_html_elements": raw_html_count,
        "uses_common_components": uses_common_components,
        "has_tabs": has_tabs,
        "has_breadcrumb": has_breadcrumb,
        "has_page_title": has_title,
    }


def check_code_quality(content: str) -> dict:
    """Check TypeScript quality issues."""
    any_types = ANY_TYPE_RE.findall(content)
    console_logs = CONSOLE_LOG_RE.findall(content)
    return {
        "any_type_count": len(any_types),
        "console_log_count": len(console_logs),
    }


def check_hardcoded_data(content: str) -> list[str]:
    """Detect hardcoded data arrays/objects that should come from API."""
    issues = []
    matches = HARDCODED_DATA_RE.finditer(content)
    for m in matches:
        line_num = content[:m.start()].count('\n') + 1
        snippet = m.group()[:80].replace('\n', ' ')
        issues.append(f"Line {line_num}: Possible hardcoded data: {snippet}...")
    return issues


def extract_routes_from_app_tsx(project_root: Path) -> dict[str, str]:
    """Parse App.tsx to find defined routes."""
    routes = {}
    # Search for App.tsx in multiple possible locations
    candidates = list(project_root.rglob("App.tsx")) + list(project_root.rglob("app.tsx"))
    for app_file in candidates:
        if "node_modules" in str(app_file):
            continue
        content = app_file.read_text(encoding="utf-8", errors="replace")
        for match in ROUTE_DEF_RE.finditer(content):
            path = match.group(1)
            # Try to find the component name nearby
            line_start = content.rfind('\n', 0, match.start()) + 1
            line_end = content.find('\n', match.end())
            line = content[line_start:line_end]
            comp_match = re.search(r'(?:component|element)\s*=\s*\{?\s*<?(\w+)', line)
            comp_name = comp_match.group(1) if comp_match else "Unknown"
            routes[path] = comp_name
    return routes


def detect_duplicate_functions(files: list[Path], threshold: int = 5) -> list[dict]:
    """Find functions with similar signatures across files."""
    func_map: dict[str, list[tuple[Path, int]]] = defaultdict(list)
    func_pattern = re.compile(
        r'(?:export\s+)?(?:const|function)\s+(\w+)\s*(?:=\s*(?:async\s*)?\([^)]*\)|(?:\([^)]*\)))'
    )
    for fpath in files:
        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for match in func_pattern.finditer(content):
            fname = match.group(1)
            line_num = content[:match.start()].count('\n') + 1
            func_map[fname].append((fpath, line_num))

    duplicates = []
    for fname, locations in func_map.items():
        if len(locations) >= 2:
            duplicates.append({
                "function": fname,
                "locations": [
                    {"file": str(loc[0].relative_to(project_root)), "line": loc[1]}
                    for loc in locations
                ],
            })
    return duplicates


def score_page(audit: dict) -> int:
    """Score a page 0-10 based on audit results."""
    score = 10

    # Streamlit remnants: -3
    if audit.get("streamlit_issues"):
        score -= 3

    # No API calls: -2
    backend = audit.get("backend_connection", {})
    if not backend.get("has_api_calls"):
        score -= 2

    # No loading/error handling: -1 each
    if backend.get("has_api_calls"):
        if not backend.get("has_loading_state"):
            score -= 1
        if not backend.get("has_error_handling"):
            score -= 1

    # Raw HTML heavy (>20 raw elements): -1
    components = audit.get("common_components", {})
    if components.get("raw_html_elements", 0) > 20:
        score -= 1

    # No common components: -1
    if not components.get("uses_common_components"):
        score -= 1

    # No title/breadcrumb: -0.5 each
    if not components.get("has_page_title"):
        score -= 0.5
    if not components.get("has_breadcrumb"):
        score -= 0.5

    # Code quality
    quality = audit.get("code_quality", {})
    if quality.get("any_type_count", 0) > 3:
        score -= 1
    if quality.get("console_log_count", 0) > 2:
        score -= 0.5

    # Hardcoded data: -1
    if audit.get("hardcoded_data_issues"):
        score -= 1

    return max(0, min(10, round(score)))


def generate_fix_hints(audit: dict) -> list[str]:
    """Generate actionable fix hints."""
    hints = []

    if audit.get("streamlit_issues"):
        hints.append("CRITICAL: Remove all Streamlit imports and replace with React equivalents.")

    backend = audit.get("backend_connection", {})
    if not backend.get("has_api_calls"):
        hints.append("Add API calls to fetch data from the backend instead of using hardcoded data.")
    if backend.get("has_api_calls") and not backend.get("has_loading_state"):
        hints.append("Add loading state (e.g., isLoading) for API calls.")
    if backend.get("has_api_calls") and not backend.get("has_error_handling"):
        hints.append("Add error handling (try/catch or error state) for API calls.")

    components = audit.get("common_components", {})
    if not components.get("uses_common_components"):
        hints.append("Use shared/common components instead of building everything from scratch.")
    if not components.get("has_page_title"):
        hints.append("Add a page title (<h1> or <PageTitle> component).")
    if not components.get("has_breadcrumb"):
        hints.append("Add breadcrumb navigation for user orientation.")

    quality = audit.get("code_quality", {})
    if quality.get("any_type_count", 0) > 0:
        hints.append(f"Replace {quality['any_type_count']} 'any' types with proper TypeScript types.")
    if quality.get("console_log_count", 0) > 0:
        hints.append(f"Remove {quality['console_log_count']} console.log statements for production.")

    if audit.get("hardcoded_data_issues"):
        hints.append("Replace hardcoded data arrays with API calls.")

    return hints


# Make project_root available at module level for detect_duplicate_functions
project_root = PROJECT_ROOT


def audit_page(filepath: Path, verbose: bool = False, fix_hints: bool = False) -> dict:
    """Run full audit on a single page file."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return {"file": str(filepath), "error": str(e), "score": 0}

    rel_path = str(filepath.relative_to(PROJECT_ROOT))
    audit = {
        "file": rel_path,
        "lines": content.count('\n') + 1,
        "streamlit_issues": check_streamlit_in_tsx(content),
        "backend_connection": check_backend_connection(content),
        "common_components": check_common_components(content),
        "code_quality": check_code_quality(content),
        "hardcoded_data_issues": check_hardcoded_data(content),
    }
    audit["score"] = score_page(audit)

    if fix_hints:
        audit["fix_hints"] = generate_fix_hints(audit)

    return audit


def main():
    parser = argparse.ArgumentParser(description="Frontend Audit Agent")
    parser.add_argument("--fix-hints", action="store_true", help="Include fix hints in report")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--page", type=str, help="Audit a specific page by name")
    parser.add_argument("--output", type=str, help="Output JSON report to file")
    args = parser.parse_args()

    print("=" * 70)
    print("  FRONTEND AUDIT AGENT")
    print(f"  Project: {PROJECT_ROOT}")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Collect all TSX/JSX files
    tsx_files = []
    for search_dir in [FRONTEND_DIR, SRC_DIR]:
        if search_dir.exists():
            tsx_files.extend(find_tsx_jsx_files(search_dir))
    # Deduplicate
    tsx_files = sorted(set(tsx_files))

    # Filter by page name if requested
    if args.page:
        tsx_files = [f for f in tsx_files if args.page.lower() in f.stem.lower()]
        if not tsx_files:
            print(f"\n[!] No TSX/JSX file found matching '{args.page}'")

    # Find Python pages that should be TSX
    py_pages = find_py_pages(PAGES_DIR)

    # Route consistency
    defined_routes = extract_routes_from_app_tsx(PROJECT_ROOT)

    print(f"\n--- SCAN SUMMARY ---")
    print(f"  TSX/JSX files found: {len(tsx_files)}")
    print(f"  Python pages (should be TSX): {len(py_pages)}")
    print(f"  Routes defined in App.tsx: {len(defined_routes)}")

    # Audit each TSX/JSX file
    page_reports = []
    for fpath in tsx_files:
        report = audit_page(fpath, verbose=args.verbose, fix_hints=args.fix_hints)
        page_reports.append(report)

    # Detect duplicates
    duplicates = detect_duplicate_functions(tsx_files)

    # --- Python pages still needing migration ---
    print(f"\n--- PYTHON PAGES NEEDING MIGRATION ({len(py_pages)}) ---")
    if py_pages:
        for p in py_pages:
            rel = p.relative_to(PROJECT_ROOT)
            # Check if it has streamlit
            try:
                content = p.read_text(encoding="utf-8", errors="replace")
                has_st = bool(STREAMLIT_IMPORT_RE.search(content) or STREAMLIT_USAGE_RE.search(content))
            except Exception:
                has_st = False
            status = " [STREAMLIT]" if has_st else " [PYTHON]"
            print(f"  - {rel}{status}")
    else:
        print("  None found. Good!")

    # --- Page Scores ---
    print(f"\n--- PAGE SCORES ---")
    total_score = 0
    for report in sorted(page_reports, key=lambda r: r.get("score", 0)):
        score = report.get("score", 0)
        total_score += score
        icon = "OK" if score >= 7 else "WARN" if score >= 4 else "FAIL"
        print(f"  [{icon}] {report['file']}: {score}/10")

        if args.verbose:
            if report.get("streamlit_issues"):
                for issue in report["streamlit_issues"]:
                    print(f"        STREAMLIT: {issue}")
            bc = report.get("backend_connection", {})
            if not bc.get("has_api_calls"):
                print(f"        NO API CALLS")
            hd = report.get("hardcoded_data_issues", [])
            for issue in hd:
                print(f"        HARDCODED: {issue}")

        if args.fix_hints and report.get("fix_hints"):
            for hint in report["fix_hints"]:
                print(f"        FIX: {hint}")

    avg_score = total_score / len(page_reports) if page_reports else 0
    print(f"\n  Average score: {avg_score:.1f}/10")

    # --- Duplicates ---
    if duplicates:
        print(f"\n--- DUPLICATE FUNCTIONS ({len(duplicates)}) ---")
        for dup in duplicates[:20]:  # limit output
            locs = ", ".join(f"{l['file']}:{l['line']}" for l in dup["locations"])
            print(f"  {dup['function']}() -> {locs}")

    # --- Route Consistency ---
    if defined_routes:
        print(f"\n--- ROUTE CONSISTENCY ---")
        for path, comp in defined_routes.items():
            # Check if the component file exists
            matches = [f for f in tsx_files if comp.lower() in f.stem.lower()]
            status = "OK" if matches else "MISSING FILE"
            print(f"  {path} -> {comp} [{status}]")

    # --- Final Summary ---
    failing = [r for r in page_reports if r.get("score", 0) < 7]
    print(f"\n{'=' * 70}")
    print(f"  FINAL SUMMARY")
    print(f"  Total pages audited: {len(page_reports)}")
    print(f"  Pages passing (>=7): {len(page_reports) - len(failing)}")
    print(f"  Pages failing (<7):  {len(failing)}")
    print(f"  Python pages to migrate: {len(py_pages)}")
    print(f"  Average score: {avg_score:.1f}/10")
    print(f"{'=' * 70}")

    # JSON output
    full_report = {
        "timestamp": datetime.now().isoformat(),
        "project_root": str(PROJECT_ROOT),
        "summary": {
            "tsx_files_count": len(tsx_files),
            "py_pages_to_migrate": len(py_pages),
            "average_score": round(avg_score, 1),
            "passing_pages": len(page_reports) - len(failing),
            "failing_pages": len(failing),
            "routes_defined": len(defined_routes),
        },
        "pages": page_reports,
        "py_pages_needing_migration": [
            str(p.relative_to(PROJECT_ROOT)) for p in py_pages
        ],
        "duplicate_functions": duplicates,
        "routes": defined_routes,
    }

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(json.dumps(full_report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n  JSON report saved to: {out_path}")
    else:
        # Save to default location
        report_path = PROJECT_ROOT / "tmp" / "frontend_audit_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(full_report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n  JSON report saved to: {report_path}")

    # Exit code: non-zero if any page fails
    sys.exit(1 if failing else 0)


if __name__ == "__main__":
    main()
