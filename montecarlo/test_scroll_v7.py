"""Test v7 — verifie le contenu de l'iframe et si le script s'execute."""
from playwright.sync_api import sync_playwright

URL = "http://localhost:8501"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})

    console_msgs = []
    page.on("console", lambda m: console_msgs.append(f"[{m.type}][{m.frame.url[:40]}] {m.text[:120]}"))

    page.goto(URL, timeout=15000)
    page.wait_for_timeout(3000)

    # Check iframe content
    iframe_info = page.evaluate("""() => {
        const iframes = document.querySelectorAll('iframe');
        return Array.from(iframes).map((f, i) => ({
            index: i,
            src: f.src || f.srcdoc?.substring(0,200) || 'no src',
            width: f.width,
            height: f.height,
            sandbox: f.sandbox?.value || 'none',
            hasContentDoc: !!f.contentDocument,
            contentDocReady: f.contentDocument?.readyState || 'N/A',
            bodyHTML: f.contentDocument?.body?.innerHTML?.substring(0,300) || 'N/A',
        }));
    }""")

    print("\n=== IFRAMES ===")
    for info in iframe_info:
        for k, v in info.items():
            print(f"  {k}: {v}")
        print()

    print("=== CONSOLE MESSAGES (all frames) ===")
    for msg in console_msgs:
        if 'warning' not in msg.lower() or 'sandbox' in msg.lower() or 'feature' not in msg.lower():
            print(f"  {msg}")

    print("\n=== CHECKING: does injecting script directly work? ===")
    # Try injecting a script tag into the page via iframe
    for i, frame in enumerate(page.frames):
        if frame == page.main_frame:
            continue
        result = frame.evaluate("""() => {
            // Check if window.parent is accessible
            try {
                const doc = window.parent.document;
                const vc = doc.querySelector('[data-testid="stAppViewContainer"]');
                return {
                    parentAccessible: true,
                    vcExists: !!vc,
                    vcOverflow: vc ? window.parent.getComputedStyle(vc).overflowY : 'N/A',
                    scriptRanFlag: window.__rvn_scroll_fix_ran || false,
                };
            } catch(e) {
                return {parentAccessible: false, error: e.message};
            }
        }""")
        print(f"  Frame [{i}] state: {result}")

    browser.close()
