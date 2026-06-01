#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('montecarlo/src/app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find sidebar section
in_sidebar = False
sidebar_options = []

for i, line in enumerate(lines):
    if 'options=[' in line:
        in_sidebar = True
    if in_sidebar:
        if '"],' in line and 'label_visibility' in lines[i+1]:
            break
        # Extract quoted strings
        if '"' in line and line.strip().startswith('"'):
            opt = line.strip().strip('",')
            if opt:
                sidebar_options.append(opt)

print("SIDEBAR OPTIONS:")
for i, opt in enumerate(sidebar_options, 1):
    print(f"{i:2d}. {opt}")
