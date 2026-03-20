# Semboutique Scraper

A Python web scraper that extracts air-conditioning spare parts from [semboutique.com](https://www.semboutique.com) and exports them to a CSV file. It uses **Playwright** for browser automation and **asyncio** for concurrent category scraping.

---

## Scraped Categories

| Category |
|---|
| ACCESSOIRE CLIMATISATION |
| CARTE ELECTRONIQUE CLIMATISATION |
| HELICE CLIMATISATION |
| MOTEUR DE CLIMATISATION |
| PIECES DIVERSES CLIMATISATION |
| SONDE CTN CLIMATISATION |

---

## Output

A file named `semboutique_products.csv` is created in the same directory you run the script from.

| Column | Description |
|---|---|
| `name` | Product name |
| `brand` | Brand (from image title attribute) |
| `price` | Cleaned price string (e.g. `12€50 ttc`) |
| `product_url` | Full URL to the product page |
| `reference` | Product reference code |
| `source` | Always `https://www.semboutique.com` |
| `category` | Category name the product belongs to |

---

## Requirements

- **Python 3.10 or higher** (uses `tuple[...]` type hints and `match` syntax)
- **pip** (comes with Python)
- Internet connection

---

## Setup — Step by Step

### 1. Install Python

Download and install Python from [https://www.python.org/downloads/](https://www.python.org/downloads/).

During installation on Windows, check **"Add Python to PATH"**.

Verify it works:

```bash
python --version
# Expected: Python 3.10.x or higher
```

---

### 2. Create a Virtual Environment (recommended)

A virtual environment keeps dependencies isolated from your system Python.

```bash
# Create the environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate

# On macOS / Linux:
source venv/bin/activate
```

Your terminal prompt will change to show `(venv)` when it is active.

---

### 3. Install Python Dependencies

```bash
pip install playwright
```

---

### 4. Install Playwright Browsers

Playwright manages its own browser binaries. Install the Chromium browser with:

```bash
playwright install chromium
```

> This downloads ~150 MB. Only needs to be done once per machine.

---

### 5. Place the Script

Put `semboutique_scraper.py` in any folder you like, for example:

```
my-scraper/
└── semboutique_scraper.py
```

---

### 6. Run the Script

Make sure your virtual environment is active, then run:

```bash
python semboutique_scraper.py
```

The script will log its progress in the terminal:

```
10:42:01 [INFO] Starting scrape of 6 categories…
10:42:05 [INFO]   ACCESSOIRE CLIMATISATION            offset=0
10:42:07 [INFO]     → 20 products (last=False)
10:42:09 [INFO]     → 20 products (last=False)
...
10:43:22 [INFO] ✓ SONDE CTN CLIMATISATION             total=14
10:43:22 [INFO] Saved 187 products → /your/path/semboutique_products.csv
10:43:22 [INFO] Done. Total products: 187
```

When it finishes, `semboutique_products.csv` will appear in the same folder.

---

## Configuration

All tunable settings are at the top of the script under the `# CONFIG` section:

| Constant | Default | Description |
|---|---|---|
| `OUTPUT_FILE` | `"semboutique_products.csv"` | Output filename / path |
| `HEADLESS` | `True` | Set to `False` to watch the browser while it scrapes |
| `CONCURRENCY` | `2` | Number of categories scraped in parallel |
| `MAX_RETRIES` | `3` | Retry attempts per page on failure |
| `RETRY_DELAY` | `2.0` | Base delay (seconds) between retries |
| `PAGE_SIZE` | `20` | Products per page (matches the site's pagination) |

Example — to watch the browser open and scrape in real time, change:

```python
HEADLESS = False
```

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'playwright'`**
→ Run `pip install playwright` and make sure your virtual environment is active.

**`playwright: command not found`** (after `pip install playwright`)
→ Use `python -m playwright install chromium` instead.

**Scraper stops mid-run or skips a category**
→ The site may have been slow or blocked the request. The script retries up to 3 times automatically. Try running again — it will re-scrape all categories from the start.

**`UnicodeEncodeError` on Windows**
→ The script already calls `sys.stdout.reconfigure(encoding="utf-8")`. If you still see errors, run the script with: `set PYTHONIOENCODING=utf-8 && python semboutique_scraper.py`

**Empty CSV**
→ The site's HTML structure may have changed. Open the script and verify the CSS selectors (`h3.fs-name a`, `.fsprice-amount`, etc.) still match the live page using browser DevTools.

---

## Project Structure

```
my-scraper/
├── semboutique_scraper.py   # Main script
├── semboutique_products.csv # Output (created after first run)
└── README.md                # This file
```

---

## Legal Notice

This scraper is intended for personal and research use only. Always check a website's `robots.txt` and Terms of Service before scraping. The built-in random delays and concurrency limits are designed to be respectful of the target server.
