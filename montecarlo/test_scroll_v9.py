"""Test v9 — verifie que le fix tourne (fix_count > 0) + etat final."""
from playwright.sync_api import sync_playwright

URL = "http://localhost:8502"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.goto(URL, timeout=15000)
    page.wait_for_timeout(2000)

    results = page.evaluate("""() => {
        const vc = document.querySelector('[data-testid="stAppViewContainer"]');
        return {
            fix_count:           window.__rvn_fix_count || 0,
            computed_overflowY:  vc ? getComputedStyle(vc).overflowY : 'N/A',
            inline_overflowY:    vc ? vc.style.overflowY : 'N/A',
            inline_priority:     vc ? vc.style.getPropertyPriority('overflow-y') : 'N/A',
            scrollHeight:        vc ? vc.scrollHeight : 0,
            clientHeight:        vc ? vc.clientHeight : 0,
        };
    }""")

    print("\n=== SCROLL FIX STATUS ===")
    for k, v in results.items():
        print(f"  {k}: {v}")

    print("\n=== VERDICT ===")
    fc = results.get('fix_count', 0)
    oy = results.get('computed_overflowY')
    if fc > 0:
        print(f"  [OK] Fix ran {fc} times")
    else:
        print("  [FAIL] Fix never ran — script not executing in iframe")
    if oy in ('auto', 'scroll'):
        print(f"  [OK] overflow-y = {oy} — page IS scrollable")
    else:
        print(f"  [FAIL] overflow-y = {oy} — still hidden")

    browser.close()
