import asyncio
import csv
import logging
import random
import re
import sys
from dataclasses import dataclass, fields, asdict
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, Page, BrowserContext, TimeoutError as PWTimeout

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

BASE_URL      = "https://www.semboutique.com"
OUTPUT_FILE   = "semboutique_products.csv"
PAGE_SIZE     = 20          # products per paginated page
MAX_RETRIES   = 3           # retry count on transient errors
RETRY_DELAY   = 2.0         # seconds between retries
CONCURRENCY   = 2           # simultaneous category workers (be polite)
HEADLESS      = True        # set False to debug visually

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/537.36 Chrome/123 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/122 Safari/537.36",
]

CATEGORIES = [
    {
        "category": "ACCESSOIRE CLIMATISATION",
        "url": f"{BASE_URL}/14211-entretien-maison/13698-climatiseurs/14255-accessoire-climatisation",
    },
    {
        "category": "CARTE ELECTRONIQUE CLIMATISATION",
        "url": f"{BASE_URL}/14211-entretien-maison/13698-climatiseurs/14250-carte-electronique-climatisation",
    },
    {
        "category": "HELICE CLIMATISATION",
        "url": f"{BASE_URL}/14211-entretien-maison/13698-climatiseurs/14252-helice-climatisation",
    },
    {
        "category": "MOTEUR DE CLIMATISATION",
        "url": f"{BASE_URL}/14211-entretien-maison/13698-climatiseurs/14251-moteur-de-climatisation",
    },
    {
        "category": "PIECES DIVERSES CLIMATISATION",
        "url": f"{BASE_URL}/14211-entretien-maison/13698-climatiseurs/14254-pieces-diverses-climatisation",
    },
    {
        "category": "SONDE CTN CLIMATISATION",
        "url": f"{BASE_URL}/14211-entretien-maison/13698-climatiseurs/14253-sonde-ctn-climatisation",
    },
]


# ─────────────────────────────────────────────
# DATA MODEL
# ─────────────────────────────────────────────
@dataclass
class Product:
    name:        Optional[str]
    brand:       Optional[str]
    price:       Optional[str]
    product_url: Optional[str]
    reference:   Optional[str]
    source:      str
    category:    str

    @property
    def is_valid(self) -> bool:
        """At least one identifying field must be non-empty."""
        return any([self.name, self.brand, self.price, self.product_url, self.reference])


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
_PRICE_RE = re.compile(r"\d+€\d+")

def clean_price(raw: str) -> Optional[str]:
    """Normalise price strings, removing duplicated segments."""
    if not raw:
        return None
    raw = raw.strip()
    matches = _PRICE_RE.findall(raw)
    if matches:
        suffix = " ttc" if "ttc" in raw.lower() else ""
        return matches[0] + suffix
    return raw


# ─────────────────────────────────────────────
# PAGE SCRAPER  (single URL)
# ─────────────────────────────────────────────
async def scrape_page(page: Page, url: str, category_name: str) -> tuple[list[Product], bool]:
    """
    Returns (products_on_page, is_last_page).
    Raises on unrecoverable errors so the caller can retry.
    """
    await page.goto(url, timeout=60_000, wait_until="domcontentloaded")
    await page.wait_for_selector("section.fsproducts", timeout=30_000)

    product_els = await page.query_selector_all("div.fs-product")
    results: list[Product] = []

    for el in product_els:
        # ── name + URL ──────────────────────────────
        name_el = await el.query_selector("h3.fs-name a")
        name        = (await name_el.inner_text()).strip() if name_el else None
        href        = await name_el.get_attribute("href") if name_el else None
        product_url = (BASE_URL + href) if href else None

        # ── reference ───────────────────────────────
        ref_el    = await el.query_selector("h4.fs-ref span")
        reference = (await ref_el.inner_text()).strip() if ref_el else None

        # ── brand ────────────────────────────────────
        brand_el = await el.query_selector("div.pb-1 img")
        brand    = await brand_el.get_attribute("title") if brand_el else None

        # ── price ────────────────────────────────────
        price_whole_el   = await el.query_selector(".fsprice-amount")
        price_decimal_el = await el.query_selector(".price-centime")

        if price_whole_el:
            whole   = (await price_whole_el.inner_text()).strip().split()[0]
            decimal = (await price_decimal_el.inner_text()).strip() if price_decimal_el else ""
            price   = clean_price(f"{whole}{decimal}".replace("\n", ""))
        else:
            price = None

        product = Product(
            name=name,
            brand=brand,
            price=price,
            product_url=product_url,
            reference=reference,
            source=BASE_URL,
            category=category_name,
        )
        if product.is_valid:
            results.append(product)

    # ── pagination sentinel ──────────────────────
    next_disabled = await page.query_selector(
        "li.disabled.page-item span.page-link span.fa-angle-right"
    )
    is_last_page = next_disabled is not None

    return results, is_last_page


# ─────────────────────────────────────────────
# CATEGORY SCRAPER  (all pages, with retry)
# ─────────────────────────────────────────────
async def scrape_category(context: BrowserContext, cat: dict) -> list[Product]:
    category_name = cat["category"]
    base_url      = cat["url"]

    page = await context.new_page()
    all_products: list[Product] = []
    start = 0

    try:
        while True:
            url = f"{base_url}?start={start}"
            log.info("  %-42s  offset=%d", category_name, start)

            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    products, is_last = await scrape_page(page, url, category_name)
                    all_products.extend(products)
                    log.info("    → %d products (last=%s)", len(products), is_last)
                    break
                except (PWTimeout, Exception) as exc:
                    if attempt == MAX_RETRIES:
                        log.error("    Giving up after %d attempts: %s", MAX_RETRIES, exc)
                        is_last = True          # skip to next category
                        break
                    log.warning("    Attempt %d failed (%s). Retrying…", attempt, exc)
                    await asyncio.sleep(RETRY_DELAY * attempt)

            if is_last:
                break

            start += PAGE_SIZE
            # polite delay between pages
            await asyncio.sleep(random.uniform(0.8, 1.8))

    finally:
        await page.close()

    log.info("✓ %-42s  total=%d", category_name, len(all_products))
    return all_products


# ─────────────────────────────────────────────
# MAIN ORCHESTRATOR
# ─────────────────────────────────────────────
async def scrape() -> list[Product]:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=HEADLESS,
            args=["--disable-blink-features=AutomationControlled"],
        )

        context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1280, "height": 900},
        )

        # Mask the webdriver flag
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
        )

        # ── controlled concurrency with semaphore ────
        sem = asyncio.Semaphore(CONCURRENCY)

        async def bounded_scrape(cat):
            async with sem:
                return await scrape_category(context, cat)

        tasks   = [bounded_scrape(cat) for cat in CATEGORIES]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_products: list[Product] = []
        for cat, result in zip(CATEGORIES, results):
            if isinstance(result, Exception):
                log.error("Category '%s' failed: %s", cat["category"], result)
            else:
                all_products.extend(result)

        await browser.close()

    return all_products


# ─────────────────────────────────────────────
# CSV EXPORT
# ─────────────────────────────────────────────
def save_to_csv(products: list[Product], filepath: str = OUTPUT_FILE) -> None:
    if not products:
        log.warning("No products to save.")
        return

    fieldnames = [f.name for f in fields(Product)]
    path = Path(filepath)

    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(asdict(p) for p in products)

    log.info("Saved %d products → %s", len(products), path.resolve())


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    log.info("Starting scrape of %d categories…", len(CATEGORIES))
    data = asyncio.run(scrape())
    save_to_csv(data)
    log.info("Done. Total products: %d", len(data))
