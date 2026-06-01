#!/usr/bin/env python3
"""Integrate ETF Explorer into app.py"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

APPFILE = "montecarlo/src/app.py"

with open(APPFILE, "r", encoding="utf-8") as f:
    content = f.read()

changes = 0

# ── 1. Add "layers" icon to IC dict ─────────────────────────────────────────
old_icon = '        "gavel":    _ic(\'<path d="M14 13l3 3-9.9 9.9a2.12 2.12 0 01-3-3L14 13z"/><path d="M3.5 11.5l10-10 3 3-10 10-3-3z"/>\')'
new_icon = old_icon + """
        "layers":   _ic('<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>'),"""

if old_icon in content:
    content = content.replace(old_icon, new_icon, 1)
    changes += 1
    print("✅ Step 1: Added layers icon")
else:
    print("⚠️ Step 1: Could not find gavel icon anchor")

# ── 2. Add ETF Explorer to CATEGORIES (inside DATA & COMPLIANCE) ─────────────
old_cat = '''        ("DATA & COMPLIANCE", [
            ("🌱  ESG & Green Lab",      "ESG & Green Lab",      IC["leaf"]),
            ("🏛️  Regulatory Capital",   "Regulatory Capital",   IC["columns"]),
            ("📡  Alt Data & Sentiment", "Alt Data & Sentiment", IC["database"]),
            ("⚖️  Portfolio Optimizer",  "Portfolio Optimizer",  IC["piechart"]),
        ]),'''

new_cat = '''        ("DATA & COMPLIANCE", [
            ("🌱  ESG & Green Lab",      "ESG & Green Lab",      IC["leaf"]),
            ("🏛️  Regulatory Capital",   "Regulatory Capital",   IC["columns"]),
            ("📡  Alt Data & Sentiment", "Alt Data & Sentiment", IC["database"]),
            ("⚖️  Portfolio Optimizer",  "Portfolio Optimizer",  IC["piechart"]),
            ("🔍  ETF Explorer",         "ETF Explorer",         IC["layers"]),
        ]),'''

if old_cat in content:
    content = content.replace(old_cat, new_cat, 1)
    changes += 1
    print("✅ Step 2: Added ETF Explorer to CATEGORIES")
else:
    print("⚠️ Step 2: Could not find DATA & COMPLIANCE block")

# ── 3. Add ETF Explorer to radio options ─────────────────────────────────────
old_opts = '        "⚖️  Portfolio Optimizer",\n        "🎓  Quantum Academy",'
new_opts = '        "⚖️  Portfolio Optimizer",\n        "🔍  ETF Explorer",\n        "🎓  Quantum Academy",'

if old_opts in content:
    content = content.replace(old_opts, new_opts, 1)
    changes += 1
    print("✅ Step 3: Added ETF Explorer to radio options")
else:
    print("⚠️ Step 3: Could not find radio options anchor")

# ── 4. Append ETF Explorer handler at end of file ───────────────────────────
etf_handler = '''

# ==================== TAB: UCITS ETF EXPLORER ====================
if selected == "🔍  ETF Explorer":
    from etf_explorer import render_etf_explorer
    render_etf_explorer()
'''

if 'render_etf_explorer' not in content:
    content += etf_handler
    changes += 1
    print("✅ Step 4: Appended ETF Explorer handler")
else:
    print("ℹ️ Step 4: Handler already present, skipped")

# ── Save ──────────────────────────────────────────────────────────────────────
with open(APPFILE, "w", encoding="utf-8") as f:
    f.write(content)

print(f"\n{'✅ All done!' if changes >= 4 else '⚠️ Some steps may have failed'} ({changes}/4 changes applied)")
