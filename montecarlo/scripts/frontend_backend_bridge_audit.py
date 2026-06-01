#!/usr/bin/env python3
"""
Frontend-Backend Bridge Audit
==============================
Verifies the connection matrix between frontend API calls and backend routes.
Detects orphan endpoints, dead calls, and type mismatches.

Usage:
    python scripts/frontend_backend_bridge_audit.py [--verbose]
"""

import argparse
import ast
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
FRONTEND_DIR = SRC_DIR / "frontend"
BACKEND_DIR = PROJECT_ROOT / "backend"
BACKEND_APP_DIR = BACKEND_DIR / "app"
BACKEND_ROUTES_DIR = BACKEND_APP_DIR / "routes"
BACKEND_SCHEMAS_DIR = BACKEND_APP_DIR / "schemas"

# Patterns for backend route detection
FASTAPI_ROUTE_RE = re.compile(
    r'@(?:router|app)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)
FASTAPI_PREFIX_RE = re.compile(
    r'(?:APIRouter|router)\s*\(\s*(?:.*?prefix\s*=\s*["\']([^"\']+)["\'])?',
    re.DOTALL,
)
INCLUDE_ROUTER_RE = re.compile(
    r'include_router\s*\(\s*(\w+)(?:.*?prefix\s*=\s*["\']([^"\']+)["\'])?',
    re.DOTALL,
)

# Patterns for frontend API call detection
FETCH_URL_RE = re.compile(
    r'(?:fetch|axios\.(?:get|post|put|delete|patch)|api\.(?:get|post|put|delete|patch)|'
    r'apiClient\.(?:get|post|put|delete|patch)|apiService\.(?:get|post|put|delete|patch))\s*\(\s*'
    r'[`"\']([^`"\']+)[`"\']',
    re.IGNORECASE,
)
TEMPLATE_URL_RE = re.compile(
    r'(?:fetch|axios\.(?:get|post|put|delete|patch)|api\.(?:get|post|put|delete|patch))\s*\(\s*'
    r'`([^`]+)`',
    re.IGNORECASE,
)
API_BASE_RE = re.compile(
    r'(?:API_BASE|BASE_URL|API_URL|baseURL|apiUrl)\s*(?:=|:)\s*["\']([^"\']+)["\']'
)

# Pydantic schema detection
PYDANTIC_MODEL_RE = re.compile(
    r'class\s+(\w+)\s*\(\s*(?:BaseModel|BaseSchema|Schema)\s*\)\s*:',
)
PYDANTIC_FIELD_RE = re.compile(
    r'(\w+)\s*:\s*([\w\[\],\s|]+)(?:\s*=)?',
)

# TypeScript interface detection
TS_INTERFACE_RE = re.compile(
    r'(?:export\s+)?interface\s+(\w+)\s*\{([^}]+)\}',
    re.DOTALL,
)
TS_TYPE_RE = re.compile(
    r'(?:export\s+)?type\s+(\w+)\s*=\s*\{([^}]+)\}',
    re.DOTALL,
)


def find_backend_routes() -> list[dict]:
    """Parse all backend route files and extract endpoints."""
    routes = []

    if not BACKEND_ROUTES_DIR.exists():
        # Try alternative locations
        alt_dirs = [
            BACKEND_APP_DIR / "api",
            BACKEND_DIR / "routes",
            BACKEND_DIR / "api",
        ]
        for alt in alt_dirs:
            if alt.exists():
                return _scan_route_dir(alt)
        return routes

    return _scan_route_dir(BACKEND_ROUTES_DIR)


def _scan_route_dir(route_dir: Path) -> list[dict]:
    """Scan a directory for FastAPI route definitions."""
    routes = []

    # First pass: find router prefixes from main.py or __init__.py
    prefix_map = {}
    for init_file in [
        BACKEND_APP_DIR / "main.py",
        route_dir / "__init__.py",
        BACKEND_DIR / "run.py",
    ]:
        if init_file.exists():
            content = init_file.read_text(encoding="utf-8", errors="replace")
            for match in INCLUDE_ROUTER_RE.finditer(content):
                router_var = match.group(1)
                prefix = match.group(2) or ""
                prefix_map[router_var] = prefix

    # Second pass: parse route files
    for py_file in sorted(route_dir.glob("*.py")):
        if py_file.name == "__init__.py":
            continue

        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        # Detect file-level prefix
        file_prefix = ""
        prefix_match = FASTAPI_PREFIX_RE.search(content)
        if prefix_match and prefix_match.group(1):
            file_prefix = prefix_match.group(1)

        # If no prefix found in file, try to infer from include_router
        if not file_prefix:
            module_name = py_file.stem
            for var_name, prefix in prefix_map.items():
                if module_name in var_name.lower() or var_name.lower() in module_name:
                    file_prefix = prefix
                    break
            if not file_prefix:
                # Default: use filename as prefix
                file_prefix = f"/api/{module_name}"

        # Extract routes
        for match in FASTAPI_ROUTE_RE.finditer(content):
            method = match.group(1).upper()
            path = match.group(2)
            full_path = file_prefix.rstrip("/") + "/" + path.lstrip("/") if path != "/" else file_prefix
            # Normalize double slashes
            full_path = re.sub(r'//+', '/', full_path)
            if not full_path.startswith("/"):
                full_path = "/" + full_path

            line_num = content[:match.start()].count('\n') + 1

            # Try to extract response model
            # Look for response_model= in the decorator
            dec_line = content[match.start():content.find('\n', match.end())]
            response_model_match = re.search(r'response_model\s*=\s*(\w+)', dec_line)
            response_model = response_model_match.group(1) if response_model_match else None

            routes.append({
                "method": method,
                "path": full_path,
                "file": str(py_file.relative_to(PROJECT_ROOT)),
                "line": line_num,
                "response_model": response_model,
            })

    return routes


def find_frontend_api_calls() -> list[dict]:
    """Scan frontend files for API calls."""
    calls = []
    search_dirs = [FRONTEND_DIR, SRC_DIR]

    # Find API base URL
    api_base = ""
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for ext in ("*.tsx", "*.jsx", "*.ts", "*.js"):
            for f in search_dir.rglob(ext):
                if "node_modules" in str(f):
                    continue
                try:
                    content = f.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                base_match = API_BASE_RE.search(content)
                if base_match:
                    api_base = base_match.group(1)
                    break

    # Scan all frontend files
    seen_files = set()
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for ext in ("*.tsx", "*.jsx", "*.ts", "*.js"):
            for f in search_dir.rglob(ext):
                if "node_modules" in str(f) or f in seen_files:
                    continue
                seen_files.add(f)
                try:
                    content = f.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue

                for match in FETCH_URL_RE.finditer(content):
                    url = match.group(1)
                    # Strip base URL if present
                    if api_base and url.startswith(api_base):
                        url = url[len(api_base):]
                    if not url.startswith("/"):
                        url = "/" + url
                    # Detect HTTP method
                    call_text = content[max(0, match.start() - 50):match.start()]
                    method = "GET"
                    for m in ("post", "put", "delete", "patch"):
                        if m in call_text.lower():
                            method = m.upper()
                            break

                    line_num = content[:match.start()].count('\n') + 1
                    calls.append({
                        "url": url,
                        "method": method,
                        "file": str(f.relative_to(PROJECT_ROOT)),
                        "line": line_num,
                    })

                # Also check template literals
                for match in TEMPLATE_URL_RE.finditer(content):
                    url = match.group(1)
                    # Normalize template variables: ${id} -> {id}
                    url = re.sub(r'\$\{[^}]+\}', '{param}', url)
                    if api_base and url.startswith(api_base):
                        url = url[len(api_base):]
                    if not url.startswith("/"):
                        url = "/" + url

                    line_num = content[:match.start()].count('\n') + 1
                    call_text = content[max(0, match.start() - 50):match.start()]
                    method = "GET"
                    for m in ("post", "put", "delete", "patch"):
                        if m in call_text.lower():
                            method = m.upper()
                            break

                    calls.append({
                        "url": url,
                        "method": method,
                        "file": str(f.relative_to(PROJECT_ROOT)),
                        "line": line_num,
                    })

    return calls


def find_pydantic_schemas() -> dict[str, list[dict]]:
    """Parse Pydantic schemas from backend."""
    schemas = {}
    search_dirs = [BACKEND_SCHEMAS_DIR, BACKEND_APP_DIR / "models.py"]

    files_to_scan = []
    if BACKEND_SCHEMAS_DIR.exists():
        files_to_scan.extend(BACKEND_SCHEMAS_DIR.rglob("*.py"))
    models_file = BACKEND_APP_DIR / "models.py"
    if models_file.exists():
        files_to_scan.append(models_file)

    for py_file in files_to_scan:
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        for match in PYDANTIC_MODEL_RE.finditer(content):
            model_name = match.group(1)
            # Extract fields (simple heuristic)
            start = match.end()
            # Find the next class or end of file
            next_class = re.search(r'\nclass\s', content[start:])
            end = start + next_class.start() if next_class else len(content)
            body = content[start:end]

            fields = []
            for field_match in PYDANTIC_FIELD_RE.finditer(body):
                fname = field_match.group(1)
                ftype = field_match.group(2).strip()
                if fname not in ("model_config", "class", "def", "self", "return"):
                    fields.append({"name": fname, "type": ftype})

            schemas[model_name] = fields

    return schemas


def find_ts_interfaces() -> dict[str, list[dict]]:
    """Parse TypeScript interfaces/types from frontend."""
    interfaces = {}
    search_dirs = [FRONTEND_DIR, SRC_DIR]

    seen = set()
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for ext in ("*.tsx", "*.ts"):
            for f in search_dir.rglob(ext):
                if "node_modules" in str(f) or f in seen:
                    continue
                seen.add(f)
                try:
                    content = f.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue

                for pattern in [TS_INTERFACE_RE, TS_TYPE_RE]:
                    for match in pattern.finditer(content):
                        name = match.group(1)
                        body = match.group(2)
                        fields = []
                        for line in body.strip().split('\n'):
                            line = line.strip().rstrip(';').rstrip(',')
                            if ':' in line and not line.startswith('//'):
                                parts = line.split(':', 1)
                                fname = parts[0].strip().rstrip('?')
                                ftype = parts[1].strip()
                                fields.append({"name": fname, "type": ftype})
                        interfaces[name] = fields

    return interfaces


def normalize_path_for_matching(path: str) -> str:
    """Normalize a URL path for matching, replacing path params with wildcards."""
    # Replace {param}, :param, {param} with *
    normalized = re.sub(r'\{[^}]+\}', '*', path)
    normalized = re.sub(r':(\w+)', '*', normalized)
    normalized = normalized.rstrip('/')
    return normalized.lower()


def match_routes(
    backend_routes: list[dict],
    frontend_calls: list[dict],
) -> dict:
    """Match frontend calls to backend routes."""
    # Normalize backend routes
    backend_normalized = {}
    for route in backend_routes:
        key = normalize_path_for_matching(route["path"])
        if key not in backend_normalized:
            backend_normalized[key] = []
        backend_normalized[key].append(route)

    # Normalize frontend calls
    frontend_normalized = {}
    for call in frontend_calls:
        key = normalize_path_for_matching(call["url"])
        if key not in frontend_normalized:
            frontend_normalized[key] = []
        frontend_normalized[key].append(call)

    # Find matches
    matched_backend = set()
    matched_frontend = set()
    matches = []

    for bkey, broutes in backend_normalized.items():
        for fkey, fcalls in frontend_normalized.items():
            # Exact match or wildcard match
            if bkey == fkey or _wildcard_match(bkey, fkey) or _wildcard_match(fkey, bkey):
                for br in broutes:
                    for fc in fcalls:
                        matches.append({
                            "backend_route": br["path"],
                            "backend_method": br["method"],
                            "backend_file": br["file"],
                            "frontend_url": fc["url"],
                            "frontend_file": fc["file"],
                            "frontend_line": fc["line"],
                        })
                matched_backend.add(bkey)
                matched_frontend.add(fkey)

    # Orphan endpoints (backend without frontend)
    orphan_endpoints = []
    for bkey, broutes in backend_normalized.items():
        if bkey not in matched_backend:
            for br in broutes:
                orphan_endpoints.append(br)

    # Dead calls (frontend without backend)
    dead_calls = []
    for fkey, fcalls in frontend_normalized.items():
        if fkey not in matched_frontend:
            for fc in fcalls:
                dead_calls.append(fc)

    return {
        "matches": matches,
        "orphan_endpoints": orphan_endpoints,
        "dead_calls": dead_calls,
    }


def _wildcard_match(pattern: str, text: str) -> bool:
    """Simple wildcard matching where * matches any path segment."""
    pattern_parts = pattern.split('/')
    text_parts = text.split('/')

    if len(pattern_parts) != len(text_parts):
        return False

    for p, t in zip(pattern_parts, text_parts):
        if p == '*' or t == '*':
            continue
        if p != t:
            return False
    return True


def compare_types(
    pydantic_schemas: dict[str, list[dict]],
    ts_interfaces: dict[str, list[dict]],
) -> list[dict]:
    """Compare Pydantic schemas with TypeScript interfaces."""
    mismatches = []

    # Map Python types to TS equivalents
    type_map = {
        "str": "string",
        "int": "number",
        "float": "number",
        "bool": "boolean",
        "list": "array",
        "dict": "object",
        "Optional": "optional",
        "datetime": "string",
        "date": "string",
        "Decimal": "number",
        "UUID": "string",
    }

    for schema_name, schema_fields in pydantic_schemas.items():
        # Try to find matching TS interface (fuzzy)
        ts_match = None
        for ts_name, ts_fields in ts_interfaces.items():
            if (
                ts_name.lower() == schema_name.lower()
                or ts_name.lower().replace("response", "") == schema_name.lower().replace("response", "")
                or ts_name.lower().replace("dto", "") == schema_name.lower().replace("schema", "")
            ):
                ts_match = (ts_name, ts_fields)
                break

        if ts_match:
            ts_name, ts_fields = ts_match
            ts_field_map = {f["name"]: f["type"] for f in ts_fields}
            py_field_map = {f["name"]: f["type"] for f in schema_fields}

            # Check missing fields
            for fname in py_field_map:
                if fname not in ts_field_map:
                    mismatches.append({
                        "type": "missing_in_ts",
                        "schema": schema_name,
                        "interface": ts_name,
                        "field": fname,
                        "python_type": py_field_map[fname],
                    })

            for fname in ts_field_map:
                if fname not in py_field_map:
                    mismatches.append({
                        "type": "missing_in_python",
                        "schema": schema_name,
                        "interface": ts_name,
                        "field": fname,
                        "ts_type": ts_field_map[fname],
                    })

    return mismatches


def main():
    parser = argparse.ArgumentParser(description="Frontend-Backend Bridge Audit")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--output", type=str, help="Output JSON report to file")
    args = parser.parse_args()

    print("=" * 70)
    print("  FRONTEND-BACKEND BRIDGE AUDIT")
    print(f"  Project: {PROJECT_ROOT}")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # --- Backend Routes ---
    print("\n--- BACKEND ROUTES ---")
    backend_routes = find_backend_routes()
    print(f"  Found {len(backend_routes)} endpoints")
    if args.verbose:
        for r in backend_routes:
            print(f"    {r['method']:6s} {r['path']:40s} ({r['file']}:{r['line']})")

    # --- Frontend API Calls ---
    print("\n--- FRONTEND API CALLS ---")
    frontend_calls = find_frontend_api_calls()
    print(f"  Found {len(frontend_calls)} API calls")
    if args.verbose:
        for c in frontend_calls:
            print(f"    {c['method']:6s} {c['url']:40s} ({c['file']}:{c['line']})")

    # --- Match Routes ---
    print("\n--- ROUTE MATCHING ---")
    result = match_routes(backend_routes, frontend_calls)

    matched = result["matches"]
    orphans = result["orphan_endpoints"]
    dead = result["dead_calls"]

    print(f"  Matched: {len(matched)}")
    print(f"  Orphan endpoints (backend only): {len(orphans)}")
    print(f"  Dead calls (frontend only): {len(dead)}")

    if orphans:
        print(f"\n--- ORPHAN ENDPOINTS ({len(orphans)}) ---")
        print("  These backend routes have no frontend caller:")
        for o in orphans:
            print(f"    {o['method']:6s} {o['path']:40s} ({o['file']}:{o['line']})")

    if dead:
        print(f"\n--- DEAD API CALLS ({len(dead)}) ---")
        print("  These frontend calls have no matching backend route:")
        for d in dead:
            print(f"    {d['method']:6s} {d['url']:40s} ({d['file']}:{d['line']})")

    # --- Type Comparison ---
    print("\n--- TYPE COMPARISON ---")
    pydantic_schemas = find_pydantic_schemas()
    ts_interfaces = find_ts_interfaces()
    print(f"  Pydantic schemas: {len(pydantic_schemas)}")
    print(f"  TypeScript interfaces: {len(ts_interfaces)}")

    type_mismatches = compare_types(pydantic_schemas, ts_interfaces)
    if type_mismatches:
        print(f"\n  Type mismatches found: {len(type_mismatches)}")
        for mm in type_mismatches:
            if mm["type"] == "missing_in_ts":
                print(f"    {mm['schema']}.{mm['field']} ({mm['python_type']}) - missing in TS interface {mm['interface']}")
            elif mm["type"] == "missing_in_python":
                print(f"    {mm['interface']}.{mm['field']} ({mm['ts_type']}) - missing in Pydantic schema {mm['schema']}")
    else:
        print("  No type mismatches detected (or no matching schema/interface pairs found)")

    # --- Coverage Matrix ---
    print(f"\n--- COVERAGE MATRIX ---")
    # Group by backend file
    route_by_file = defaultdict(list)
    for r in backend_routes:
        route_by_file[r["file"]].append(r)

    orphan_paths = {o["path"] for o in orphans}

    for bfile, routes in sorted(route_by_file.items()):
        covered = sum(1 for r in routes if r["path"] not in orphan_paths)
        total = len(routes)
        pct = (covered / total * 100) if total > 0 else 0
        bar = "#" * int(pct / 5) + "." * (20 - int(pct / 5))
        print(f"  {bfile:45s} [{bar}] {covered}/{total} ({pct:.0f}%)")

    # --- Summary ---
    total_coverage = 0
    if backend_routes:
        total_coverage = (len(backend_routes) - len(orphans)) / len(backend_routes) * 100

    print(f"\n{'=' * 70}")
    print(f"  SUMMARY")
    print(f"  Backend endpoints: {len(backend_routes)}")
    print(f"  Frontend API calls: {len(frontend_calls)}")
    print(f"  Matched connections: {len(matched)}")
    print(f"  Orphan endpoints: {len(orphans)}")
    print(f"  Dead calls: {len(dead)}")
    print(f"  Type mismatches: {len(type_mismatches)}")
    print(f"  Overall coverage: {total_coverage:.1f}%")
    status = "PASS" if len(orphans) == 0 and len(dead) == 0 else "FAIL"
    print(f"  Status: {status}")
    print(f"{'=' * 70}")

    # JSON report
    full_report = {
        "timestamp": datetime.now().isoformat(),
        "project_root": str(PROJECT_ROOT),
        "summary": {
            "backend_endpoints": len(backend_routes),
            "frontend_api_calls": len(frontend_calls),
            "matched_connections": len(matched),
            "orphan_endpoints": len(orphans),
            "dead_calls": len(dead),
            "type_mismatches": len(type_mismatches),
            "overall_coverage_pct": round(total_coverage, 1),
            "status": status,
        },
        "backend_routes": backend_routes,
        "frontend_calls": frontend_calls,
        "matches": matched,
        "orphan_endpoints": orphans,
        "dead_calls": dead,
        "type_mismatches": type_mismatches,
        "pydantic_schemas": {k: v for k, v in pydantic_schemas.items()},
        "ts_interfaces": {k: v for k, v in ts_interfaces.items()},
    }

    report_path = Path(args.output) if args.output else PROJECT_ROOT / "tmp" / "bridge_audit_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(full_report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  JSON report saved to: {report_path}")

    sys.exit(0 if status == "PASS" else 1)


if __name__ == "__main__":
    main()
