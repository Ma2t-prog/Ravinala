"""Check what's in the DOM — iframes, script tags, etc."""
from playwright.sync_api import sync_playwright

URL = "http://localhost:8502"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.goto(URL, timeout=15000)
    page.wait_for_timeout(2000)

    info = page.evaluate("""() => {
        // All iframes
        const iframes = Array.from(document.querySelectorAll('iframe'));

        // Any rvn elements
        const rvnEls = document.querySelectorAll('[class*="rvn"], [id*="rvn"]');

        // Check if our scroll fix iframe appeared
        const allIframesInfo = iframes.map(f => ({
            src: f.src || '',
            srcdocLen: (f.getAttribute('srcdoc') || '').length,
            style: f.getAttribute('style') || '',
            sandbox: f.getAttribute('sandbox') || 'none',
            display: getComputedStyle(f).display,
        }));

        return {
            iframeCount: iframes.length,
            iframes: allIframesInfo,
            rvnElCount: rvnEls.length,
            fix_count: window.__rvn_fix_count || 0,
        };
    }""")

    print("=== DOM INSPECTION ===")
    print(f"  iframe count: {info['iframeCount']}")
    print(f"  rvn elements: {info['rvnElCount']}")
    print(f"  fix_count: {info['fix_count']}")
    for i, f in enumerate(info['iframes']):
        print(f"  iframe[{i}]: srcdocLen={f['srcdocLen']} sandbox='{f['sandbox']}' style='{f['style']}'")

    # Check all frames
    print(f"\n  Playwright frames: {len(page.frames)}")
    for i, frame in enumerate(page.frames):
        print(f"    [{i}] url={frame.url[:60]}")

    browser.close()
