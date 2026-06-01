"""Full app audit - Unicode safe, tests all pages for runtime errors."""
import asyncio
import sys
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:8509"

# Exact sidebar link text (ASCII-safe versions)
ALL_PAGES = [
    'Home',
    'Live Market',
    'Market News',
    'Macro Analysis',
    'Alt Data',
    'Intelligence',
    'Financial Analysis',
    'Pricing Center',
    'Structuring Suite',
    'Custom Product',
    'Advanced Exotics',
    'Museum of Exotics',
    'The Sandbox',
    'Enterprise Val.',
    'Equity Research',
    'Fixed Income',
    'Asset Explorer',
    'Company Analyzer',
    'ETF Explorer',
    'Risk Management',
    'Greeks & Sensitivity',
    'Vol Calibration',
    'Backtesting',
    'ML Pricing',
    'Hedging',
    'Portfolio Optimizer',
    'Strategy Lab',
    'Scenario Matrix',
    'P&L Attribution',
    'Position Book',
    'TAX LAB',
    'Universe Search',
    'Advanced Screener',
    'Instrument Analysis',
    'Portfolio Omega',
    'Risk Engine',
    'ML Engine',
    'Advanced Analysis',
    'Market Intelligence',
    'Portfolio Monitor',
    'Signal Intelligence',
    'Data Layer',
    'Physics Lab',
    'ESG & Green Lab',
    'Regulatory Capital',
    'Report Generator',
    'Legal & Compliance',
    'Quantum Academy',
    'Probability Bible',
    'Learning Hub',
    'Trade Book',
    'Admin Panel',
]

async def test_page(page, link_text):
    """Navigate to page, wait for load, check for errors."""
    try:
        # Find link in sidebar by partial text
        links = await page.locator('[data-testid="stSidebarNav"] a').all()
        matched = []
        for link in links:
            text = await link.inner_text()
            if link_text.lower() in text.lower():
                matched.append(link)

        if not matched:
            return 'SKIP', f'Link not found: {link_text}'

        await matched[0].click()
        await page.wait_for_timeout(3000)

        # Check for error elements
        errors = await page.locator('[data-testid="stException"]').all()
        if errors:
            err_text = await errors[0].inner_text()
            return 'ERROR', err_text[:300].replace('\n', ' ')

        return 'OK', ''

    except Exception as e:
        return 'CRASH', str(e)[:200]


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        page.on('console', lambda _: None)

        print(f"Navigating to {BASE_URL}...")
        await page.goto(BASE_URL, wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(2000)

        # Expand sidebar if collapsed
        try:
            toggle = page.locator('[data-testid="collapsedControl"]')
            if await toggle.is_visible():
                await toggle.click()
                await page.wait_for_timeout(500)
        except Exception:
            pass

        ok = skip = errors_count = 0
        failed_pages = []

        for page_name in ALL_PAGES:
            status, msg = await test_page(page, page_name)

            safe_name = page_name.encode('ascii', 'replace').decode('ascii')

            if status == 'OK':
                ok += 1
                print(f"  [OK]    {safe_name}")
            elif status == 'SKIP':
                skip += 1
                print(f"  [SKIP]  {safe_name}")
            else:
                errors_count += 1
                safe_msg = msg.encode('ascii', 'replace').decode('ascii')
                print(f"  [FAIL]  {safe_name}: {safe_msg}")
                failed_pages.append(safe_name)

        print(f"\n--- SUMMARY ---")
        print(f"OK: {ok}  SKIP: {skip}  FAIL: {errors_count}  TOTAL: {len(ALL_PAGES)}")
        if failed_pages:
            print(f"Failed: {failed_pages}")

        await browser.close()

        if errors_count > 0:
            sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
