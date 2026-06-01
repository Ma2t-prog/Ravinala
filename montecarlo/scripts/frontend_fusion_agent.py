#!/usr/bin/env python3
"""
Frontend Fusion Agent
=====================
Helps merge multiple React pages into a single tabbed page.
Analyzes common imports, duplicate code, and generates a fusion skeleton.

Usage:
    python scripts/frontend_fusion_agent.py \\
        --sources "Page1.tsx,Page2.tsx" \\
        --target "MergedPage.tsx" \\
        --tabs "Tab1,Tab2"
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from textwrap import dedent, indent

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"
FRONTEND_DIR = SRC_DIR / "frontend"

# Patterns
IMPORT_RE = re.compile(
    r'^import\s+(?:(?:\{[^}]+\}|\w+|\*\s+as\s+\w+)(?:\s*,\s*(?:\{[^}]+\}|\w+))*)\s+from\s+["\']([^"\']+)["\'];?\s*$',
    re.MULTILINE,
)
NAMED_IMPORT_RE = re.compile(
    r'^import\s+\{([^}]+)\}\s+from\s+["\']([^"\']+)["\'];?\s*$',
    re.MULTILINE,
)
DEFAULT_IMPORT_RE = re.compile(
    r'^import\s+(\w+)\s+from\s+["\']([^"\']+)["\'];?\s*$',
    re.MULTILINE,
)
FUNCTION_DEF_RE = re.compile(
    r'(?:export\s+)?(?:const|function)\s+(\w+)\s*(?:=\s*(?:async\s*)?\([^)]*\)\s*(?::\s*\w+(?:<[^>]+>)?)?\s*=>|(?:\s*\([^)]*\)))',
    re.MULTILINE,
)
STATE_HOOK_RE = re.compile(r'const\s+\[(\w+),\s*set\w+\]\s*=\s*useState')
EFFECT_HOOK_RE = re.compile(r'useEffect\s*\(')
TYPE_INTERFACE_RE = re.compile(
    r'(?:export\s+)?(?:interface|type)\s+(\w+)\s*(?:=|{)',
    re.MULTILINE,
)


def find_source_file(name: str) -> Path | None:
    """Find a source file by name in the project."""
    # Try exact path first
    exact = PROJECT_ROOT / name
    if exact.exists():
        return exact

    # Search in common locations
    for search_dir in [FRONTEND_DIR, SRC_DIR / "pages", SRC_DIR, PROJECT_ROOT]:
        if not search_dir.exists():
            continue
        # Direct match
        candidate = search_dir / name
        if candidate.exists():
            return candidate
        # Recursive search
        matches = list(search_dir.rglob(name))
        if matches:
            return matches[0]

    return None


def parse_imports(content: str) -> dict:
    """Parse all imports from a file."""
    imports = {
        "named": defaultdict(set),    # source -> {names}
        "default": {},                 # source -> default_name
        "all_sources": set(),
    }

    for match in NAMED_IMPORT_RE.finditer(content):
        names = [n.strip().split(" as ")[0].strip() for n in match.group(1).split(",")]
        source = match.group(2)
        imports["named"][source].update(names)
        imports["all_sources"].add(source)

    for match in DEFAULT_IMPORT_RE.finditer(content):
        default_name = match.group(1)
        source = match.group(2)
        imports["default"][source] = default_name
        imports["all_sources"].add(source)

    return imports


def parse_functions(content: str) -> list[dict]:
    """Extract function definitions."""
    functions = []
    for match in FUNCTION_DEF_RE.finditer(content):
        name = match.group(1)
        line_num = content[:match.start()].count('\n') + 1
        # Get the function body (approximate by finding the next function or end)
        start = match.start()
        # Simple heuristic: count braces
        depth = 0
        end = start
        in_body = False
        for i, ch in enumerate(content[start:], start):
            if ch == '{':
                depth += 1
                in_body = True
            elif ch == '}':
                depth -= 1
                if in_body and depth == 0:
                    end = i + 1
                    break
        body = content[start:end]
        lines = body.count('\n') + 1
        functions.append({
            "name": name,
            "line": line_num,
            "size_lines": lines,
            "body_preview": body[:200].replace('\n', ' ').strip(),
        })
    return functions


def parse_state_hooks(content: str) -> list[str]:
    """Extract useState variable names."""
    return STATE_HOOK_RE.findall(content)


def parse_types(content: str) -> list[str]:
    """Extract type/interface definitions."""
    return TYPE_INTERFACE_RE.findall(content)


def analyze_file(filepath: Path) -> dict:
    """Full analysis of a source file."""
    content = filepath.read_text(encoding="utf-8", errors="replace")
    return {
        "path": filepath,
        "content": content,
        "lines": content.count('\n') + 1,
        "imports": parse_imports(content),
        "functions": parse_functions(content),
        "state_hooks": parse_state_hooks(content),
        "types": parse_types(content),
        "has_effects": len(EFFECT_HOOK_RE.findall(content)),
    }


def find_common_imports(analyses: list[dict]) -> dict:
    """Find imports shared across files."""
    source_counts = Counter()
    for a in analyses:
        for src in a["imports"]["all_sources"]:
            source_counts[src] += 1

    common = {}
    for src, count in source_counts.items():
        if count >= 2:
            # Merge named imports
            merged_names = set()
            for a in analyses:
                merged_names.update(a["imports"]["named"].get(src, set()))
            common[src] = {
                "used_by": count,
                "total_files": len(analyses),
                "named_imports": sorted(merged_names),
            }
    return common


def find_duplicate_functions(analyses: list[dict]) -> list[dict]:
    """Find functions with the same name across files."""
    func_map = defaultdict(list)
    for a in analyses:
        for func in a["functions"]:
            func_map[func["name"]].append({
                "file": str(a["path"].name),
                "line": func["line"],
                "size": func["size_lines"],
            })

    return [
        {"name": name, "locations": locs}
        for name, locs in func_map.items()
        if len(locs) >= 2
    ]


def generate_skeleton(
    target_name: str,
    tab_names: list[str],
    analyses: list[dict],
    common_imports: dict,
) -> str:
    """Generate the skeleton TSX for the merged page."""
    # Collect all unique imports
    all_named: dict[str, set] = defaultdict(set)
    all_defaults: dict[str, str] = {}
    for a in analyses:
        for src, names in a["imports"]["named"].items():
            all_named[src].update(names)
        for src, default in a["imports"]["default"].items():
            if src not in all_defaults:
                all_defaults[src] = default

    # Build import block
    import_lines = []
    # React first
    react_imports = all_named.pop("react", set())
    react_imports.add("useState")
    import_lines.append(f'import React, {{ {", ".join(sorted(react_imports))} }} from "react";')

    # Sort remaining imports
    for src in sorted(set(list(all_named.keys()) + list(all_defaults.keys()))):
        parts = []
        if src in all_defaults:
            parts.append(all_defaults[src])
        if src in all_named and all_named[src]:
            parts.append("{ " + ", ".join(sorted(all_named[src])) + " }")
        if parts:
            import_lines.append(f'import {", ".join(parts)} from "{src}";')

    imports_block = "\n".join(import_lines)

    # Collect all types
    all_types = []
    for a in analyses:
        for t in a["types"]:
            all_types.append(t)
    types_block = "\n".join(f"// TODO: Merge type '{t}' from source files" for t in sorted(set(all_types)))

    # Collect all state hooks
    all_state = []
    for a in analyses:
        for s in a["state_hooks"]:
            all_state.append(s)

    state_block = "\n".join(
        f'  const [{s}, set{s[0].upper()}{s[1:]}] = useState<any>(null); // TODO: type properly'
        for s in sorted(set(all_state))
    )

    # Build tab content sections
    tab_sections = []
    for i, (tab_name, analysis) in enumerate(zip(tab_names, analyses)):
        funcs = ", ".join(f["name"] for f in analysis["functions"][:5])
        tab_sections.append(f"""
    // --- TAB: {tab_name} ---
    // Source: {analysis['path'].name}
    // Functions to integrate: {funcs or 'none detected'}
    // Lines in source: {analysis['lines']}""")

    component_name = target_name.replace(".tsx", "").replace(".jsx", "")

    # Generate tab rendering
    tab_panels = []
    for i, tab_name in enumerate(tab_names):
        tab_panels.append(f"""        {{activeTab === {i} && (
          <div className="tab-panel">
            {{/* TODO: Integrate {tab_name} content from {analyses[i]['path'].name if i < len(analyses) else 'source'} */}}
            <p>Content for {tab_name}</p>
          </div>
        )}}""")

    tab_buttons = []
    for i, tab_name in enumerate(tab_names):
        tab_buttons.append(
            f'          <button\n'
            f'            className={{`tab-button ${{activeTab === {i} ? "active" : ""}}`}}\n'
            f'            onClick={{() => setActiveTab({i})}}\n'
            f'          >\n'
            f'            {tab_name}\n'
            f'          </button>'
        )

    skeleton = f"""{imports_block}

{types_block}

/**
 * {component_name}
 *
 * Merged page combining:
{chr(10).join(f" *   - {a['path'].name} -> Tab '{t}'" for a, t in zip(analyses, tab_names))}
 *
 * Generated by frontend_fusion_agent.py on {datetime.now().strftime('%Y-%m-%d %H:%M')}
 */
{"".join(tab_sections)}

const {component_name}: React.FC = () => {{
  const [activeTab, setActiveTab] = useState<number>(0);
{state_block}

  return (
    <div className="{component_name.lower()}-page">
      <h1>{component_name.replace('Page', ' Page').replace('_', ' ')}</h1>

      <div className="tabs">
        <div className="tab-list">
{chr(10).join(tab_buttons)}
        </div>

{chr(10).join(tab_panels)}
      </div>
    </div>
  );
}};

export default {component_name};
"""
    return skeleton


def generate_fusion_report(
    sources: list[str],
    target: str,
    tabs: list[str],
    analyses: list[dict],
    common_imports: dict,
    duplicates: list[dict],
) -> dict:
    """Generate a comprehensive fusion report."""
    return {
        "timestamp": datetime.now().isoformat(),
        "fusion": {
            "sources": sources,
            "target": target,
            "tabs": tabs,
        },
        "analysis": {
            "total_lines": sum(a["lines"] for a in analyses),
            "total_functions": sum(len(a["functions"]) for a in analyses),
            "total_state_hooks": sum(len(a["state_hooks"]) for a in analyses),
            "total_types": sum(len(a["types"]) for a in analyses),
        },
        "common_imports": {
            src: {
                "used_by": info["used_by"],
                "named": info["named_imports"],
            }
            for src, info in common_imports.items()
        },
        "duplicate_functions": duplicates,
        "per_file": [
            {
                "file": str(a["path"].name),
                "lines": a["lines"],
                "functions": [f["name"] for f in a["functions"]],
                "state_hooks": a["state_hooks"],
                "types": a["types"],
            }
            for a in analyses
        ],
        "post_fusion_checklist": [
            f"Update App.tsx: remove old routes, add route for {target}",
            "Update sidebar/navigation to reference the new merged page",
            f"Delete source files: {', '.join(sources)}",
            "Run: python scripts/frontend_audit_agent.py",
            "Run: python scripts/frontend_backend_bridge_audit.py",
            "Verify all API endpoints are still called",
            "Test tab switching and data loading",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="Frontend Fusion Agent")
    parser.add_argument(
        "--sources", required=True,
        help="Comma-separated list of source page files to merge"
    )
    parser.add_argument(
        "--target", required=True,
        help="Name of the target merged page file"
    )
    parser.add_argument(
        "--tabs", required=True,
        help="Comma-separated tab names for the merged page"
    )
    parser.add_argument("--output-dir", type=str, help="Output directory for generated files")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--dry-run", action="store_true", help="Don't write files, just show report")
    args = parser.parse_args()

    sources = [s.strip() for s in args.sources.split(",")]
    tabs = [t.strip() for t in args.tabs.split(",")]
    target = args.target.strip()

    print("=" * 70)
    print("  FRONTEND FUSION AGENT")
    print(f"  Merging: {', '.join(sources)}")
    print(f"  Into: {target}")
    print(f"  Tabs: {', '.join(tabs)}")
    print("=" * 70)

    if len(sources) != len(tabs):
        print(f"\n[ERROR] Number of sources ({len(sources)}) must match number of tabs ({len(tabs)})")
        sys.exit(1)

    # Find and analyze source files
    analyses = []
    for src in sources:
        filepath = find_source_file(src)
        if filepath is None:
            print(f"\n[ERROR] Source file not found: {src}")
            print(f"  Searched in: {FRONTEND_DIR}, {SRC_DIR / 'pages'}, {SRC_DIR}, {PROJECT_ROOT}")
            sys.exit(1)
        print(f"\n  Analyzing: {filepath.relative_to(PROJECT_ROOT)}")
        analysis = analyze_file(filepath)
        analyses.append(analysis)
        print(f"    Lines: {analysis['lines']}")
        print(f"    Functions: {len(analysis['functions'])}")
        print(f"    State hooks: {len(analysis['state_hooks'])}")
        print(f"    Types: {len(analysis['types'])}")

    # Find commonalities
    common_imports = find_common_imports(analyses)
    duplicates = find_duplicate_functions(analyses)

    print(f"\n--- COMMON IMPORTS ({len(common_imports)}) ---")
    for src, info in common_imports.items():
        print(f"  {src}: used by {info['used_by']}/{len(analyses)} files")
        if info["named_imports"]:
            print(f"    Named: {', '.join(info['named_imports'])}")

    if duplicates:
        print(f"\n--- DUPLICATE FUNCTIONS ({len(duplicates)}) ---")
        for dup in duplicates:
            locs = ", ".join(f"{l['file']}:{l['line']}" for l in dup["locations"])
            print(f"  {dup['name']}() -> {locs}")
        print("  NOTE: These should be unified in the merged file.")

    # Features per source
    print(f"\n--- FEATURES PER SOURCE ---")
    for analysis, tab_name in zip(analyses, tabs):
        print(f"\n  {analysis['path'].name} -> Tab '{tab_name}':")
        for func in analysis["functions"]:
            print(f"    - {func['name']}() ({func['size_lines']} lines)")
        if analysis["state_hooks"]:
            print(f"    State: {', '.join(analysis['state_hooks'])}")

    # Generate skeleton
    skeleton = generate_skeleton(target, tabs, analyses, common_imports)

    # Generate report
    report = generate_fusion_report(sources, target, tabs, analyses, common_imports, duplicates)

    # Output
    output_dir = Path(args.output_dir) if args.output_dir else PROJECT_ROOT / "tmp"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not args.dry_run:
        # Write skeleton
        skeleton_path = output_dir / target
        skeleton_path.write_text(skeleton, encoding="utf-8")
        print(f"\n  Skeleton written to: {skeleton_path}")

        # Write report
        report_path = output_dir / f"fusion_report_{target.replace('.tsx', '')}.json"
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  Report written to: {report_path}")
    else:
        print(f"\n--- GENERATED SKELETON (dry-run) ---")
        print(skeleton[:2000])
        if len(skeleton) > 2000:
            print(f"  ... ({len(skeleton)} chars total)")

    # Checklist
    print(f"\n--- POST-FUSION CHECKLIST ---")
    for item in report["post_fusion_checklist"]:
        print(f"  [ ] {item}")

    print(f"\n{'=' * 70}")
    print(f"  Fusion analysis complete.")
    print(f"  Total lines to merge: {sum(a['lines'] for a in analyses)}")
    print(f"  Estimated target size: ~{sum(a['lines'] for a in analyses) * 0.7:.0f} lines (after dedup)")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
