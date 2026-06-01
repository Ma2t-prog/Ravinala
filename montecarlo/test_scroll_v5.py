"""Scroll diagnostic v5 — trouve la regle CSS gagnante + teste injection depuis iframe."""
from playwright.sync_api import sync_playwright

URL = "http://localhost:8501"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.goto(URL, timeout=15000)
    page.wait_for_timeout(2000)

    results = page.evaluate("""() => {
        const vc = document.querySelector('[data-testid="stAppViewContainer"]');
        if (!vc) return {error: 'not found'};

        // Find ALL CSS rules that set overflow on stAppViewContainer
        const winningRules = [];
        for (const ss of document.styleSheets) {
            try {
                for (const rule of ss.cssRules || []) {
                    if (!rule.selectorText) continue;
                    const sel = rule.selectorText;
                    if (sel.includes('stAppViewContainer') || sel === '*') {
                        const overflow = rule.style.overflow || rule.style.overflowY || rule.style.overflowX;
                        if (overflow) {
                            const priority = rule.style.getPropertyPriority('overflow') ||
                                             rule.style.getPropertyPriority('overflow-y');
                            winningRules.push({
                                selector: sel,
                                overflow: overflow,
                                overflowY: rule.style.overflowY,
                                priority: priority,
                                href: ss.href || 'inline'
                            });
                        }
                    }
                }
            } catch(e) {}
        }

        // Also check stApp parent
        const app = document.querySelector('[data-testid="stApp"]');
        const appStyle = app ? window.getComputedStyle(app) : null;

        // Check if iframe can be accessed and its window.parent works
        const iframe = document.querySelector('iframe');
        let iframeParentTest = 'no iframe';
        if (iframe) {
            try {
                const iDoc = iframe.contentDocument;
                const iWin = iframe.contentWindow;
                iframeParentTest = iWin && iWin.parent === window ? 'window.parent==top OK' : 'window.parent != top';
            } catch(e) { iframeParentTest = 'error: ' + e.message; }
        }

        return {
            vc_computed_overflowY: window.getComputedStyle(vc).overflowY,
            vc_inline_overflowY: vc.style.overflowY,
            app_computed_overflow: appStyle ? appStyle.overflow : 'N/A',
            app_computed_overflowY: appStyle ? appStyle.overflowY : 'N/A',
            matching_rules_count: winningRules.length,
            winning_rules: winningRules,
            iframe_parent_test: iframeParentTest,
        };
    }""")

    print("\n=== CSS RULES ANALYSIS ===")
    print(f"  vc computed overflow-y : {results['vc_computed_overflowY']}")
    print(f"  vc inline overflow-y   : '{results['vc_inline_overflowY']}'")
    print(f"  stApp overflow         : {results['app_computed_overflow']}")
    print(f"  stApp overflow-y       : {results['app_computed_overflowY']}")
    print(f"  iframe->window.parent  : {results['iframe_parent_test']}")
    print(f"\n  Rules targeting stAppViewContainer ({results['matching_rules_count']}):")
    for r in results.get('winning_rules', []):
        print(f"    [{r['priority'] or 'normal':9s}] {r['selector']}")
        print(f"             overflow:{r['overflow']} overflow-y:{r['overflowY']}")
        href = r['href']
        if len(href) > 80:
            href = '...' + href[-60:]
        print(f"             source: {href}")

    browser.close()
