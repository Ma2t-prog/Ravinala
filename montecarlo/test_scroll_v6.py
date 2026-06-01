"""Test v6 — execute JS directement depuis l'iframe pour voir si ca peut modifier window.parent."""
from playwright.sync_api import sync_playwright

URL = "http://localhost:8501"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.goto(URL, timeout=15000)
    page.wait_for_timeout(2000)

    # Get the iframe element
    frames = page.frames
    print(f"\n=== FRAMES ({len(frames)}) ===")
    for i, f in enumerate(frames):
        print(f"  [{i}] url={f.url} name={f.name}")

    # Try executing fix from inside the iframe context
    result = {"executed": False, "error": ""}
    for i, frame in enumerate(frames):
        if frame == page.main_frame:
            continue
        try:
            res = frame.evaluate("""() => {
                try {
                    var doc = window.parent.document;
                    var vc = doc.querySelector('[data-testid="stAppViewContainer"]');
                    if (!vc) return {ok: false, reason: 'vc not found', parentAccessible: true};
                    vc.style.setProperty('overflow-y', 'auto', 'important');
                    var computed = window.parent.getComputedStyle(vc).overflowY;
                    var inline = vc.style.overflowY;
                    return {ok: true, computed: computed, inline: inline, parentAccessible: true};
                } catch(e) {
                    return {ok: false, reason: e.message, parentAccessible: false};
                }
            }""")
            print(f"\n=== IFRAME [{i}] JS RESULT ===")
            for k, v in res.items():
                print(f"  {k}: {v}")
            result = res
        except Exception as e:
            print(f"  Frame [{i}] error: {e}")

    # Now check main page state
    main_state = page.evaluate("""() => {
        const vc = document.querySelector('[data-testid="stAppViewContainer"]');
        return {
            overflowY_computed: vc ? getComputedStyle(vc).overflowY : 'N/A',
            overflowY_inline:   vc ? vc.style.overflowY : 'N/A',
        };
    }""")
    print("\n=== MAIN PAGE STATE AFTER IFRAME FIX ===")
    for k, v in main_state.items():
        print(f"  {k}: {v}")

    browser.close()
