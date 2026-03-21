import asyncio
import json
from playwright.async_api import async_playwright
import sys

sys.stdout.reconfigure(encoding='utf-8')

EMAIL = ""
PASSWORD = ""
LOGIN_URL = "https://app.repturn.com/login"
SUCCESS_URL = "https://app.repturn.com"

async def login_and_save_cookies():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=300)  # set True if needed
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
        )
        page = await context.new_page()

        print("➡️ Opening login page...")
        try:
            await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)

            # Ensure page really loaded
            await page.wait_for_selector("#email", timeout=20000)
            
        except:
            print("⚠️ Retrying with networkidle...")
            await page.goto(LOGIN_URL, wait_until="networkidle", timeout=60000)

        # --- Step 1: Fill Email ---
        await page.wait_for_selector("#email", timeout=15000)
        await page.fill("#email", EMAIL)

        print("➡️ Clicking Continue (email)...")
        # Click the button that contains the email text
        await page.locator("button:has-text('Continue'), button:has-text('{}')".format(EMAIL)).first.click()

        # --- Step 2: Wait for Password Field ---
        print("⏳ Waiting for password field...")
        await page.wait_for_selector("input[type='password']", timeout=15000)

        # --- Step 3: Fill Password ---
        await page.fill("input[type='password']", PASSWORD)

        print("➡️ Clicking Login...")
        await page.locator("button:has-text('Log in')").click()

        # --- Step 4: Wait for redirect ---
        print("⏳ Waiting for successful login redirect...")
        await page.wait_for_url("**app.repturn.com**", timeout=20000)

        # --- Step 5: Save Cookies ---
        cookies = await context.cookies()
        with open("cookies.json", "w") as f:
            json.dump(cookies, f, indent=2)

        print("✅ Login successful, cookies saved to cookies.json")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(login_and_save_cookies())
