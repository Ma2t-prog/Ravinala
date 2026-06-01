"""Test v8 — check iframe content + inject script flag to verify execution."""
from playwright.sync_api import sync_playwright

URL = "http://localhost:8501"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.goto(URL, timeout=15000)
    page.wait_for_timeout(3000)

    # 1. Check iframe details from main page
    info = page.evaluate("""() => {
        const iframes = document.querySelectorAll('iframe');
        return Array.from(iframes).map((f, i) => ({
            index: i,
            sandbox: f.getAttribute('sandbox') || 'none',
            height: f.getAttribute('height'),
            width: f.getAttribute('width'),
            srcdocLen: (f.getAttribute('srcdoc') || '').length,
            srcdocSnippet: (f.getAttribute('srcdoc') || '').substring(0, 200),
            contentDocState: f.contentDocument ? f.contentDocument.readyState : 'no access',
        }));
    }""")

    print("=== IFRAME INFO ===")
    for frame in info:
        for k, v in frame.items():
            print(f"  {k}: {v}")
    print()

    # 2. Check if our script set the debug flag
    frames = page.frames
    print(f"=== FRAMES: {len(frames)} ===")
    for i, f in enumerate(frames):
        if f == page.main_frame:
            continue
        try:
            state = f.evaluate("""() => ({
                scriptIife: typeof window.__rvn_scroll_fix_ran !== 'undefined',
                parentOk: (function(){ try { return !!window.parent.document; } catch(e){ return false; } })(),
                vcExists: (function(){ try { return !!window.parent.document.querySelector('[data-testid="stAppViewContainer"]'); } catch(e){ return false; } })(),
            })""")
            print(f"  Frame[{i}]: {state}")
        except Exception as e:
            print(f"  Frame[{i}] error: {e}")

    # 3. What CSS classes does stAppViewContainer have?
    classes = page.evaluate("""() => {
        const vc = document.querySelector('[data-testid="stAppViewContainer"]');
        if (!vc) return 'not found';
        return {
            className: vc.className,
            computedOverflow: getComputedStyle(vc).overflow,
            computedOverflowY: getComputedStyle(vc).overflowY,
        };
    }""")
    print(f"\n=== stAppViewContainer CLASSES ===")
    for k, v in classes.items():
        print(f"  {k}: {v}")

    browser.close()
