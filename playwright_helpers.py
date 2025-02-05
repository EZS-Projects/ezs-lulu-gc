import asyncio
import random
import logging
from playwright.async_api import async_playwright
import os

log_dir = "../log"
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("../log/playwright_helper.log"), logging.StreamHandler()],
)

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
            await page.wait_for_selector("#countrySelectorModal", state="hidden", timeout=5000)
    except Exception as e:
        logging.warning(f"未找到弹窗关闭按钮或点击失败: {e}")


async def human_like_actions(page):
    scroll_distance = random.randint(100, 1000)
    await page.mouse.wheel(0, scroll_distance)
    await asyncio.sleep(random.uniform(0.5, 2.0))


async def input_card_number_and_check(page, card_number, max_retries=8):
    retry_count = 0
    while retry_count < max_retries:
        try:
            await page.fill('//*[@id="card-number"]', "")
            await page.fill('//*[@id="card-number"]', card_number, timeout=5000)
            logging.info(f"已输入卡号: {card_number}")

            await page.click('//button[@value="check-balance"]')
            logging.info("已点击查询按钮，等待余额信息")

            selector = await page.query_selector('xpath=//p[@class="balance"]')
            await selector.is_visible()

            balance_element = await page.wait_for_selector('xpath=//p[@class="balance"]', timeout=5000)
            if balance_element:
                balance_text = await balance_element.inner_text()
                logging.info(f"查询结果: {balance_text}")
                return balance_text
        except Exception as e:
            retry_count += 1
            logging.warning(f"查询卡号 {card_number} 时失败: {e}")
            if retry_count < max_retries:
                await asyncio.sleep(random.uniform(0.5, 1.0))
            else:
                logging.error(f"卡号 {card_number} 查询失败，已达到最大重试次数")
                return "Error"


async def click_check_another_card(page):
    try:
        continue_button = await page.wait_for_selector('//button[contains(text(), "CHECK ANOTHER CARD")]', timeout=8000)
        if continue_button:
            await continue_button.click()
            logging.info("已点击 'CHECK ANOTHER CARD' 按钮")
            await page.wait_for_selector('xpath=//*[@id="card-number"]', timeout=8000)
    except Exception as e:
        logging.error(f"未找到 'CHECK ANOTHER CARD' 按钮或点击失败: {e}")
