"""Test minimal — injecte un script dans l'iframe via Playwright et verifie l'execution."""
from playwright.sync_api import sync_playwright

URL = "http://localhost:8502"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.goto(URL, timeout=15000)
    page.wait_for_timeout(1500)

    # Execute directly from iframe frame
    frames = page.frames
    print(f"Frames: {len(frames)}")

    for i, frame in enumerate(frames):
        if frame == page.main_frame:
            continue
        try:
            # Try running the exact same code as our script
            res = frame.evaluate("""() => {
                var errors = [];
                try {
                    var doc = window.parent.document;
                    var vc = doc.querySelector('[data-testid="stAppViewContainer"]');
                    if (!vc) { errors.push('vc not found'); }
                    else {
                        vc.style.setProperty('overflow-y', 'scroll', 'important');
                        window.parent.__rvn_fix_count = (window.parent.__rvn_fix_count || 0) + 1;
                    }
                    return {ok: true, errors: errors, fixCount: window.parent.__rvn_fix_count};
                } catch(e) {
                    return {ok: false, error: e.toString()};
                }
            }""")
            print(f"  Frame[{i}] manual exec: {res}")
        except Exception as e:
            print(f"  Frame[{i}] error: {e}")

    # Now check if it stuck
    main = page.evaluate("""() => {
        const vc = document.querySelector('[data-testid="stAppViewContainer"]');
        return {
            fix_count: window.__rvn_fix_count || 0,
            overflowY_computed: vc ? getComputedStyle(vc).overflowY : 'N/A',
            overflowY_inline:   vc ? vc.style.overflowY : 'N/A',
        };
    }""")
    print(f"\n  Main page after manual frame exec: {main}")

    # Wait 2s and check if Streamlit reset it
    page.wait_for_timeout(2000)
    main2 = page.evaluate("""() => {
        const vc = document.querySelector('[data-testid="stAppViewContainer"]');
        return {
            overflowY_computed: vc ? getComputedStyle(vc).overflowY : 'N/A',
            overflowY_inline:   vc ? vc.style.overflowY : 'N/A',
        };
    }""")
    print(f"  Main page 2s later: {main2}")
    if main2.get('overflowY_computed') in ('auto', 'scroll'):
        print("  [OK] Fix persists after 2s — Streamlit does NOT reset inline styles")
    else:
        print("  [FAIL] Fix was reset by Streamlit after 2s")

    browser.close()
