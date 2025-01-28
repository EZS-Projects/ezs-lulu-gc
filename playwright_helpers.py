import asyncio
import random
from playwright.async_api import async_playwright

async def init_driver(
    headless: bool = True,
    use_proxy: bool = False,
    proxy_server: str = "http://127.0.0.1:1080",
    locale: str = "en-AU",
    timezone: str = "Australia/Sydney",
):
    playwright = await async_playwright().start()

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
    ]
    user_agent = random.choice(user_agents)

    launch_args = {"headless": headless}
    if use_proxy:
        launch_args["proxy"] = {"server": proxy_server}

    browser = await playwright.chromium.launch(**launch_args)

    context_args = {
        "user_agent": user_agent,
        "viewport": {"width": 1280, "height": 720},
        "locale": locale,
        "timezone_id": timezone,
        "permissions": [],
    }

    context = await browser.new_context(**context_args)
    page = await context.new_page()

    return playwright, browser, context, page

async def close_popup(page):
    try:
        popup_button = await page.query_selector('xpath=//*[@id="countrySelectorModal"]/div/div/div[1]/button')
        if popup_button:
            await popup_button.click()
    except Exception:
        pass

async def human_like_actions(page):
    scroll_distance = random.randint(100, 1000)
    await page.mouse.wheel(0, scroll_distance)
    await asyncio.sleep(random.uniform(0.5, 2.0))
