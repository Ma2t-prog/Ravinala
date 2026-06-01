"""Scroll diagnostic v2 — vérifie inline style, teste le fix direct."""
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

        const st = window.getComputedStyle(vc);
        const inlineOY = vc.style.overflowY;
        const inlineO  = vc.style.overflow;

        // Is our CSS in the page?
        const styles = Array.from(document.styleSheets);
        let ourCssFound = false;
        for (const ss of styles) {
            try {
                const rules = Array.from(ss.cssRules || []);
                for (const r of rules) {
                    if (r.cssText && r.cssText.includes('stAppViewContainer') &&
                        r.cssText.includes('overflow')) {
                        ourCssFound = true;
                    }
                }
            } catch(e) {}
        }

        // Test: can we force overflow via setProperty important?
        const before = st.overflowY;
        vc.style.setProperty('overflow-y', 'auto', 'important');
        const after = window.getComputedStyle(vc).overflowY;

        // Does scrollTop move when we set it?
        const scrollBefore = vc.scrollTop;
        vc.scrollTop = 300;
        const scrollAfter = vc.scrollTop;

        // Reset
        vc.style.removeProperty('overflow-y');

        return {
            computed_overflowY: before,
            inline_overflowY:   inlineOY,
            inline_overflow:    inlineO,
            ourCssFound:        ourCssFound,
            after_setProperty:  after,
            scrollHeight:       vc.scrollHeight,
            clientHeight:       vc.clientHeight,
            scrollMovedTo:      scrollAfter,
            scrollWorked:       scrollAfter > 0,
        };
    }""")

    print("\n=== DIAGNOSTIC RESULTS ===")
    for k, v in results.items():
        print(f"  {k:25s}: {v}")

    print("\n=== CONCLUSION ===")
    r = results
    if r.get('computed_overflowY') == 'hidden':
        if r.get('inline_overflow') or r.get('inline_overflowY'):
            print("  CAUSE: Streamlit sets overflow via INLINE STYLE (React)")
            print("  FIX:   Use style.setProperty(..., 'important') in JS")
        else:
            print("  CAUSE: External CSS (index.CwxM5zkf.css) sets overflow:hidden")
            print("  FIX:   Our CSS !important should win — check injection")
    if r.get('after_setProperty') == 'auto':
        print("  GOOD: setProperty('overflow-y','auto','important') WORKS")
        print("  -> Just need to call this from components.html JS")
    if r.get('scrollWorked'):
        print(f"  GOOD: scrollTop moves ({r['scrollMovedTo']}px) when overflow is auto")
        print("  -> Content IS there, just clipped by overflow:hidden")
    if not r.get('ourCssFound'):
        print("  WARN: Our CSS rule for stAppViewContainer not found in stylesheets")

    browser.close()
