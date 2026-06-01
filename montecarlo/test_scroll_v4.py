"""Scroll diagnostic v4 — verifie si le JS fix tourne VRAIMENT (apres 1s)."""
from playwright.sync_api import sync_playwright

URL = "http://localhost:8501"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})

    js_errors = []
    page.on("console", lambda msg: js_errors.append(f"[{msg.type}] {msg.text}") if msg.type in ("error","warning") else None)

    page.goto(URL, timeout=15000)
    page.wait_for_timeout(2000)  # wait longer than our 300ms fix

    results = page.evaluate("""() => {
        const vc = document.querySelector('[data-testid="stAppViewContainer"]');
        if (!vc) return {error: 'stAppViewContainer not found'};

        // Check computed overflow AFTER JS fix should have run
        const computed = window.getComputedStyle(vc).overflowY;
        const inlineStyle = vc.style.overflowY;
        const inlinePriority = vc.style.getPropertyPriority('overflow-y');

        // Check if any iframe exists (components.html)
        const iframes = Array.from(document.querySelectorAll('iframe'));
        const iframeCount = iframes.length;
        let iframeAccessible = false;
        try {
            if (iframes[0]) {
                const _ = iframes[0].contentDocument;
                iframeAccessible = true;
            }
        } catch(e) {}

        // Can we scroll right now without forcing?
        const scrollBefore = vc.scrollTop;
        vc.scrollTop = 100;
        const scrollAfter = vc.scrollTop;
        vc.scrollTop = scrollBefore;

        return {
            computed_overflowY_after_2s: computed,
            inline_overflowY:            inlineStyle,
            inline_priority:             inlinePriority,
            js_fix_ran:                  inlineStyle === 'auto' && inlinePriority === 'important',
            iframe_count:                iframeCount,
            iframe_accessible:           iframeAccessible,
            scroll_works_now:            scrollAfter > 0,
            scrollHeight:                vc.scrollHeight,
            clientHeight:                vc.clientHeight,
        };
    }""")

    print("\n=== DIAGNOSTIC v4 — JS FIX STATUS ===")
    for k, v in results.items():
        status = ""
        if k == "js_fix_ran":
            status = " [OK]" if v else " [FAIL] -> iframe peut pas acceder window.parent"
        if k == "computed_overflowY_after_2s":
            status = " [OK]" if v == "auto" else " [FAIL] toujours hidden"
        print(f"  {k:35s}: {v}{status}")

    print("\n=== CONSOLE ERRORS ===")
    for e in js_errors[:10]:
        print(f"  {e}")
    if not js_errors:
        print("  (aucune erreur)")

    print("\n=== VERDICT ===")
    if results.get('js_fix_ran'):
        print("  [OK] JS fix tourne correctement depuis l'iframe")
    else:
        print("  [FAIL] JS fix ne tourne PAS — iframe sandboxee ou window.parent bloque")
        print("  -> Solution: injecter le fix via st.markdown directement")

    browser.close()
