"""Scroll diagnostic v3 — simule le JS fix (setProperty) et verifie que le scroll fonctionne."""
from playwright.sync_api import sync_playwright

URL = "http://localhost:8501"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.goto(URL, timeout=15000)
    page.wait_for_timeout(4000)

    results = page.evaluate("""() => {
        const vc = document.querySelector('[data-testid="stAppViewContainer"]');
        if (!vc) return {error: 'stAppViewContainer not found'};

        const before = window.getComputedStyle(vc).overflowY;
        const scrollBefore = vc.scrollTop;

        // Apply the fix (same as what attachWheelFix does)
        vc.style.setProperty('overflow-y', 'auto', 'important');
        vc.style.setProperty('overflow-x', 'hidden', 'important');

        const after = window.getComputedStyle(vc).overflowY;

        // Try scrolling
        vc.scrollTop = 300;
        const scrollAfter = vc.scrollTop;

        return {
            overflow_before_fix: before,
            overflow_after_fix:  after,
            scroll_moved_to:     scrollAfter,
            scroll_worked:       scrollAfter > 0,
            scrollHeight:        vc.scrollHeight,
            clientHeight:        vc.clientHeight,
            has_scrollable_content: vc.scrollHeight > vc.clientHeight,
        };
    }""")

    print("\n=== SCROLL FIX SIMULATION ===")
    for k, v in results.items():
        print(f"  {k:25s}: {v}")

    print("\n=== VERDICT ===")
    if results.get('scroll_worked'):
        print("  [OK] FIX WORKS — setProperty forces overflow:auto, scrollTop moves")
        print(f"  [OK] Page has {results['scrollHeight']}px content in {results['clientHeight']}px viewport")
        print("  -> attachWheelFix (300ms delay) will apply this fix on every page load")
    else:
        print("  [FAIL] Scroll still broken after fix")
        print(f"  overflow before: {results.get('overflow_before_fix')}")
        print(f"  overflow after:  {results.get('overflow_after_fix')}")

    browser.close()
