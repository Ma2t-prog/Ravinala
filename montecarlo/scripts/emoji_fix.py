#!/usr/bin/env python3
"""
Emoji cleanup script for montecarlo Python files.
Replaces emoji characters with plain-text alternatives or removes them.
"""
import re
import sys

# Map from Unicode codepoint to replacement string
# Empty string means "remove"
EMOJI_MAP = {
    # Status indicators
    0x2705: '[OK]',       # ✅
    0x274C: '[ERR]',      # ❌
    0x2715: 'x',          # ✗
    0x2713: 'v',          # ✓ (checkmark)
    0x2717: 'x',          # ✗ (ballot x)
    0x26A0: '[WARN]',     # ⚠
    0x2753: '?',          # ❓
    # Color circles
    0x1F7E2: '[OK]',      # 🟢 green circle
    0x1F7E1: '[WARN]',    # 🟡 yellow circle
    0x1F534: '[ERR]',     # 🔴 red circle
    0x1F535: '[INFO]',    # 🔵 blue circle
    0x26AA: '[--]',       # ⚪ white circle
    # Charts/finance
    0x1F4CA: '',          # 📊 bar chart
    0x1F4C8: '',          # 📈 chart up
    0x1F4C9: '',          # 📉 chart down
    0x1F4B0: '',          # 💰 money bag
    0x1F4B1: '',          # 💱 currency exchange
    0x1F4B5: '',          # 💵 dollar banknote
    0x1F4B9: '',          # 💹 chart with yen
    0x1F48E: '',          # 💎 gem
    # Navigation/arrows
    0x27A1: '->',         # ➡
    0x2795: '+',          # ➕
    0x2B06: '^',          # ⬆
    0x2B07: 'v',          # ⬇
    # Tech/tools
    0x1F680: '',          # 🚀
    0x26A1: '',           # ⚡
    0x1F4A5: '',          # 💥
    0x1F504: '',          # 🔄
    0x1F514: '',          # 🔔
    0x1F52E: '',          # 🔮
    0x1F50D: '',          # 🔍
    0x1F52C: '',          # 🔬
    0x1F9EA: '',          # 🧪
    0x1F9E0: '',          # 🧠
    0x1F916: '',          # 🤖
    0x1F4A1: '',          # 💡
    # Documents
    0x1F4CB: '',          # 📋
    0x1F4C4: '',          # 📄
    0x1F4C5: '',          # 📅
    0x1F4DA: '',          # 📚
    0x1F4D0: '',          # 📐
    0x1F4D2: '',          # 📒
    0x1F4D5: '',          # 📕
    0x1F4D6: '',          # 📖
    0x1F4D7: '',          # 📗
    0x1F4D8: '',          # 📘
    0x1F4E1: '',          # 📡
    0x1F4E2: '',          # 📢
    0x1F4E5: '',          # 📥
    0x1F4E7: '',          # 📧
    0x1F4F0: '',          # 📰
    0x1F5C4: '',          # 🗄
    0x1F5D1: '',          # 🗑
    # People/places
    0x1F464: '',          # 👤
    0x1F468: '',          # 👨
    0x1F91D: '',          # 🤝
    0x1F3E0: '',          # 🏠
    0x1F3DB: '',          # 🏛
    0x1F5FD: '',          # 🗽
    0x1F30D: '',          # 🌍
    0x1F30A: '',          # 🌊
    # Nature
    0x1F331: '',          # 🌱
    0x1F333: '',          # 🌳
    0x1F334: '',          # 🌴
    0x1F49A: '',          # 💚
    # Activities/games
    0x1F3B2: '',          # 🎲
    0x1F3AF: '',          # 🎯
    0x1F393: '',          # 🎓
    0x1F3D4: '',          # 🏔
    # Other misc
    0x1F321: '',          # 🌡
    0x1F441: '',          # 👁
    0x1F4AC: '',          # 💬
    0x1F4BC: '',          # 💼
    0x1F500: '',          # 🔀
    0x1F50B: '',          # 🔋
    0x1F517: '',          # 🔗
    0x1F522: '',          # 🔢
    0x1F578: '',          # 🕸
    0x1F6E1: '',          # 🛡
    0x1F9A0: '',          # 🦠
    0x1F9F9: '',          # 🧹
    0x23F0: '',           # ⏰
    0x23F3: '',           # ⏳
    0x23F8: '',           # ⏸
    0x2696: '',           # ⚖
    0x2699: '',           # ⚙
    0x2726: '',           # ✦
    0x1F4BC: '',          # 💼
    # Variation selector (should be removed when preceding emoji is gone)
    0xFE0F: '',           # variation selector-16
    # Flag components (regional indicators)
    # 0x1F1EC + 0x1F1E7 = 🇬🇧  etc — handled by range below
}

# Also handle regional indicator symbols (flag emojis)
# U+1F1E0 to U+1F1FF
REGIONAL_INDICATOR_RANGE = (0x1F1E0, 0x1F1FF)


def replace_emojis(content):
    result = []
    i = 0
    while i < len(content):
        ch = content[i]
        cp = ord(ch)

        # Check regional indicators (flag emojis)
        if REGIONAL_INDICATOR_RANGE[0] <= cp <= REGIONAL_INDICATOR_RANGE[1]:
            # Skip this character (and potentially next if it's also a regional indicator)
            if (i + 1 < len(content) and
                    REGIONAL_INDICATOR_RANGE[0] <= ord(content[i+1]) <= REGIONAL_INDICATOR_RANGE[1]):
                i += 2  # skip both chars of a flag pair
            else:
                i += 1
            continue

        if cp in EMOJI_MAP:
            replacement = EMOJI_MAP[cp]
            result.append(replacement)
            i += 1
            continue

        result.append(ch)
        i += 1

    return ''.join(result)


FILES = [
    'C:/Users/Matthias/Project/montecarlo/src/app.py',
    'C:/Users/Matthias/Project/montecarlo/src/financial_analysis_suite.py',
    'C:/Users/Matthias/Project/montecarlo/src/gui.py',
    'C:/Users/Matthias/Project/montecarlo/src/home_page.py',
    'C:/Users/Matthias/Project/montecarlo/src/home_page_v3.py',
    'C:/Users/Matthias/Project/montecarlo/src/new_pages.py',
    'C:/Users/Matthias/Project/montecarlo/src/analysis/intermarket.py',
    'C:/Users/Matthias/Project/montecarlo/src/analysis/relative_strength.py',
    'C:/Users/Matthias/Project/montecarlo/src/analysis/screener.py',
    'C:/Users/Matthias/Project/montecarlo/src/analysis/suite_ui.py',
    'C:/Users/Matthias/Project/montecarlo/src/genesix/omega_database.py',
    'C:/Users/Matthias/Project/montecarlo/src/genesix/dashboard/intelligence.py',
    'C:/Users/Matthias/Project/montecarlo/src/genesix/dashboard/components/scenario.py',
    'C:/Users/Matthias/Project/montecarlo/src/genesix/data/macro_fetcher.py',
    'C:/Users/Matthias/Project/montecarlo/src/genesix/utils/config.py',
    'C:/Users/Matthias/Project/montecarlo/src/genesix/utils/formatters.py',
    'C:/Users/Matthias/Project/montecarlo/src/pages/documentation.py',
    'C:/Users/Matthias/Project/montecarlo/src/pages/enterprise_valuations.py',
    'C:/Users/Matthias/Project/montecarlo/src/pages/genesix_advanced_analysis.py',
    'C:/Users/Matthias/Project/montecarlo/src/pages/genesix_data_layer.py',
    'C:/Users/Matthias/Project/montecarlo/src/pages/genesix_home.py',
    'C:/Users/Matthias/Project/montecarlo/src/pages/genesix_intelligence.py',
    'C:/Users/Matthias/Project/montecarlo/src/pages/genesix_market_intelligence.py',
    'C:/Users/Matthias/Project/montecarlo/src/pages/genesix_ml_engine.py',
    'C:/Users/Matthias/Project/montecarlo/src/pages/genesix_portfolio_monitor.py',
    'C:/Users/Matthias/Project/montecarlo/src/pages/genesix_risk_engine.py',
    'C:/Users/Matthias/Project/montecarlo/src/pages/intelligence_center.py',
    'C:/Users/Matthias/Project/montecarlo/src/pages/physics_demo.py',
    'C:/Users/Matthias/Project/montecarlo/src/pages/strategy_lab.py',
]


def main():
    total_changed = 0
    for filepath in FILES:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                original = f.read()
        except FileNotFoundError:
            print(f'SKIP (not found): {filepath}')
            continue

        cleaned = replace_emojis(original)

        if cleaned != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(cleaned)
            # Count emojis removed
            diff_count = sum(1 for a, b in zip(original, cleaned) if a != b)
            print(f'CLEANED: {filepath.split("/")[-1]}')
            total_changed += 1
        else:
            print(f'no change: {filepath.split("/")[-1]}')

    print(f'\nDone. {total_changed} files modified.')


if __name__ == '__main__':
    main()
