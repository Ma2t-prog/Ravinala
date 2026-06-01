#!/usr/bin/env python3
"""Fix the sidebar navbar in app.py"""

def fix_navbar():
    file_path = "src/app.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the line with "Pricing Center" in the options list
    in_nav_section = False
    nav_start = -1
    nav_end = -1
    
    for i, line in enumerate(lines):
        if '"🎯  Pricing Center"' in line:
            in_nav_section = True
            nav_start = i - 2  # Include the radio() line
        
        if in_nav_section and '"📚' in line and ('Learn' in line or 'Legal' in line):
            nav_end = i
            break
    
    if nav_start == -1 or nav_end == -1:
        print(f"ERROR: Could not find navbar section (start={nav_start}, end={nav_end})")
        return False
    
    print(f"Found navbar section: lines {nav_start+1} to {nav_end+1}")
    
    # Create new nav options
    new_nav_lines = [
        '    "nav",\n',
        '    options=[\n',
        '        "🏠  Home",\n',
        '        "🎯  Pricing Center",\n',
        '        "🏗️  The Sandbox",\n',
        '        "🛠️  Custom Product",\n',
        '        "🏛️  Museum of Exotics",\n',
        '        "💼  Enterprise Valuations",\n',
        '        "📊  Macro Analysis",\n',
        '        "⚠️  Risk Management",\n',
        '        "📈  Backtesting",\n',
        '        "📉  Vol Calibration",\n',
        '        "🤖  ML Pricing",\n',
        '        "🛡️  Hedging",\n',
        '        "✨  Advanced Exotics",\n',
        '        "📡  Live Market",\n',
        '        "📚  Learn",\n',
        '        "⚖️  Legal",\n',
        '    ],\n',
    ]
    
    # Build the new file content
    new_content = (
        lines[:nav_start] +
        new_nav_lines +
        lines[nav_end+1:]
    )
    
    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_content)
    
    print("✅ Navbar fixed successfully!")
    return True

if __name__ == "__main__":
    fix_navbar()
