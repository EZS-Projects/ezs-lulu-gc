import asyncio
import random
import logging
import os
from pathlib import Path
from playwright.async_api import async_playwright

try:
    from playwright_stealth import stealth_async
    USE_STEALTH = True
except ImportError:
    USE_STEALTH = False

log_dir = "../log"
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("../log/playwright_helper.log"), logging.StreamHandler()],
)

async def close_popup(page):
    popup_button = await page.query_selector('xpath=//*[@id="countrySelectorModal"]/div/div/div[1]/button')
    if popup_button:
        await popup_button.click()

        # 使用 wait_for_function 检查弹窗是否隐藏
        try:
            await page.wait_for_function(
                '''() => {
                    const modal = document.querySelector("#countrySelectorModal");
                    return modal === null || modal.getAttribute("aria-hidden") === "true" || modal.style.display === "none";
                }''',
                timeout=5000
            )
            logging.info("已关闭弹出的欢迎对话框")
        except Exception as e:
            logging.error(f"等待弹窗隐藏时发生错误: {e}")


async def human_like_actions(page):
    # delay = random_delay(0.5, 2.0)
    # await asyncio.sleep(delay)

    scroll_distance = random.randint(100, 1000)
    await page.mouse.wheel(0, scroll_distance)

    # await asyncio.sleep(random_delay(0.5, 2.0))

    page_width = page.viewport_size["width"]
    page_height = page.viewport_size["height"]
    x = random.randint(0, page_width)
    y = random.randint(0, page_height)
    await page.mouse.move(x, y, steps=random.randint(5, 15))

async def open_check_dialogue(page):
    try:
        specific_option = await page.wait_for_selector(
            "xpath=/html/body/div[1]/div[3]/div[2]/a", timeout=10000
        )
        if specific_option:
            await specific_option.click()
            logging.info("成功点击指定选项")
            await page.wait_for_timeout(500)  # 等待页面稳定
    except Exception as e:
        logging.warning(f"未找到指定选项或点击失败: {e}")
        logging.info("已保存截图 'open_check_dialogue_error.png' 以供调试")

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
