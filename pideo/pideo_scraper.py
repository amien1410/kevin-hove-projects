import asyncio
import json
from playwright.async_api import async_playwright

import sys

sys.stdout.reconfigure(encoding='utf-8')

START_URL = "https://xn--pido-dpa.fr/filtre-climatisation/"

# ---------- SAFE HELPERS ----------
async def safe_text(locator):
    try:
        if await locator.count() > 0:
            return (await locator.first.inner_text()).strip()
    except:
        pass
    return ""

async def safe_attr(locator, attr):
    try:
        if await locator.count() > 0:
            return await locator.first.get_attribute(attr)
    except:
        pass
    return ""


# ---------- SCRAPER ----------
async def scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        results = []
        current_url = START_URL

        while True:
            print(f"➡️ Scraping: {current_url}")
            await page.goto(current_url, timeout=60000)

            # wait products
            await page.wait_for_selector(".ty-grid-list__item")

            products = page.locator(".ty-grid-list__item")
            count = await products.count()

            print(f"   Found {count} products")

            for i in range(count):
                item = products.nth(i)

                name = await safe_text(item.locator("a.product-title"))
                url = await safe_attr(item.locator("a.product-title"), "href")

                # price is split (€ + number)
                price_value = await safe_text(item.locator(".ty-price-num").nth(1))
                price = f"€{price_value}" if price_value else ""

                results.append({
                    "name": name,
                    "url": url,
                    "price": price
                })

            # ---------- NEXT PAGE ----------
            next_btn = page.locator("a.ty-pagination__next")

            if await next_btn.count() == 0:
                print("✅ No more pages")
                break

            next_url = await next_btn.get_attribute("href")

            if not next_url:
                print("✅ Last page reached")
                break

            current_url = next_url

        # ---------- SAVE ----------
        with open("products_pido.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\n✅ DONE: {len(results)} products saved")

        await browser.close()


# ---------- RUN ----------
asyncio.run(scrape())
