import asyncio
import random
import time
import logging
from pathlib import Path

import pandas as pd
from tqdm.asyncio import tqdm
from playwright.async_api import async_playwright

try:
    from playwright_stealth import stealth_async
    USE_STEALTH = True
except ImportError:
    USE_STEALTH = False

# ========== 配置日志 ==========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("../log/card_query.log"), logging.StreamHandler()],
)

def random_delay(min_seconds=1.0, max_seconds=3.0):
    return random.uniform(min_seconds, max_seconds)

# ========== 模拟简单的人为操作 ==========
async def human_like_actions(page):
    delay = random_delay(0.5, 2.0)
    await asyncio.sleep(delay)

    scroll_distance = random.randint(100, 1000)
    await page.mouse.wheel(0, scroll_distance)

    await asyncio.sleep(random_delay(0.5, 2.0))

    page_width = page.viewport_size["width"]
    page_height = page.viewport_size["height"]
    x = random.randint(0, page_width)
    y = random.randint(0, page_height)
    await page.mouse.move(x, y, steps=random.randint(5, 15))

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

    launch_args = {
        "headless": headless,
    }
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

    # ========== 深度反检测配置 ==========
    await page.add_init_script(
        """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});

        window.chrome = { runtime: {} };

        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) { return 'Intel Inc.'; }
            if (parameter === 37446) { return 'Intel Iris OpenGL Engine'; }
            return getParameter(parameter);
        };

        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) =>
            parameters.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : originalQuery(parameters);

        Object.defineProperty(screen, 'width', { get: () => 1920 });
        Object.defineProperty(screen, 'height', { get: () => 1080 });
    """
    )

    # 图片请求拦截
    await page.route(
        "**/*",
        lambda route: (
            route.abort()
            if route.request.resource_type == "image"
            else route.continue_()
        ),
    )

    if USE_STEALTH:
        await stealth_async(page)

    return playwright, browser, context, page

async def close_popup(page):
    try:
        popup_button = await page.query_selector('xpath=//*[@id="countrySelectorModal"]/div/div/div[1]/button')
        if not popup_button:
            logging.info("未找到弹窗关闭按钮，跳过关闭弹窗步骤")
            return

        await page.click(
            'xpath=//*[@id="countrySelectorModal"]/div/div/div[1]/button', timeout=8000
        )
        logging.info("弹窗已成功关闭")
        await page.wait_for_selector(
            "#countrySelectorModal", state="hidden", timeout=5000
        )
        logging.info("弹窗已隐藏")
    except Exception as e:
        logging.warning(f"未找到关闭弹窗按钮或点击失败: {e}")
        await page.screenshot(path="../log/close_popup_error.png")
        logging.info("已保存截图 'close_popup_error.png' 以供调试")

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
        await page.screenshot(path="open_check_dialogue_error.png")
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

            balance_element = await page.wait_for_selector(
                'xpath=//p[@class="balance"]', timeout=5000
            )

            if balance_element:
                balance_text = await balance_element.inner_text()
                logging.info(f"查询结果: {balance_text}")
                return balance_text
        except Exception as e:
            retry_count += 1
            logging.warning(f"查询卡号 {card_number} 时失败: {e}")
            if retry_count < max_retries:
                sleep_time = random.uniform(0.5, 1.0)
                logging.info(
                    f"等待 {sleep_time:.2f} 秒后重试 (重试次数: {retry_count}/{max_retries})"
                )
                await asyncio.sleep(sleep_time)
            else:
                logging.error(f"卡号 {card_number} 查询失败，已达到最大重试次数")
                return "Error"

async def click_check_another_card(page):
    try:
        continue_button = await page.wait_for_selector(
            '//button[contains(text(), "CHECK ANOTHER CARD")]', timeout=8000
        )
        if continue_button:
            await continue_button.click()
            logging.info("已点击 'CHECK ANOTHER CARD' 按钮")

            await page.wait_for_selector('xpath=//*[@id="card-number"]', timeout=8000)
            logging.info("输入框已可用")
    except Exception as e:
        logging.error(f"未找到 'CHECK ANOTHER CARD' 按钮或点击失败: {e}")
        await page.screenshot(path="../log/click_check_another_card_error.png")
        raise e

async def process_card_batch(batch_id, card_numbers, progress_bar, progress_lock):
    logging.info(f"线程 {batch_id} 开始处理 {len(card_numbers)} 张卡号")
    results = []

    playwright, browser, context, page = None, None, None, None
    try:
        playwright, browser, context, page = await init_driver(use_proxy=False)

        url = "https://www.lululemon.com.au/en-au/content/gift-cards/gift-cards.html"
        await page.goto(url)
        logging.info(f"线程 {batch_id} 页面已加载: {url}")

        await close_popup(page)
        await open_check_dialogue(page)

        for idx, card_number in enumerate(card_numbers, start=1):
            logging.info(
                f"线程 {batch_id} => 查询第 {idx}/{len(card_numbers)} 张卡号: {card_number}"
            )

            balance = await input_card_number_and_check(page, card_number)
            results.append((card_number, balance))

            if balance != "Error":
                try:
                    await human_like_actions(page)
                    logging.info(
                        f"线程 {batch_id} 等待 0 秒后继续下一张查询"
                    )
                    await click_check_another_card(page)
                except Exception as e:
                    logging.error(f"线程 {batch_id} 无法返回查询页面: {e}")
            else:
                logging.warning(
                    f"线程 {batch_id} 卡号 {card_number} 查询失败，跳过点击 'CHECK ANOTHER CARD'"
                )

            async with progress_lock:
                progress_bar.update(1)

    except Exception as e:
        logging.critical(f"线程 {batch_id} 运行出现严重错误: {e}")
    finally:
        if browser:
            try:
                await browser.close()
                await playwright.stop()
                logging.info(f"线程 {batch_id} 浏览器已关闭")
            except Exception as e:
                logging.error(f"线程 {batch_id} 关闭浏览器时出错: {e}")

    return results

def split_card_numbers(card_numbers, num_batches):
    k, m = divmod(len(card_numbers), num_batches)
    return [
        card_numbers[i * k + min(i, m) : (i + 1) * k + min(i + 1, m)]
        for i in range(num_batches)
    ]

async def main():
    input_file = "../files/data.csv"
    output_file = "../files/price.csv"

    MAX_THREADS = 1

    try:
        df = pd.read_csv(input_file)
        card_numbers = df.iloc[:, 0].astype(str).tolist()
        logging.info(f"总共 {len(card_numbers)} 张卡需要查询")

        batches = split_card_numbers(card_numbers, MAX_THREADS)
        logging.info(
            f"划分为 {len(batches)} 个批次，平均每批次约 {len(batches[0])} 张卡"
        )

        progress_bar = tqdm(
            total=len(card_numbers), desc="Processing cards", unit="card"
        )
        progress_lock = asyncio.Lock()

        tasks = [
            process_card_batch(batch_id + 1, batch, progress_bar, progress_lock)
            for batch_id, batch in enumerate(batches)
        ]

        all_results = []
        for task in asyncio.as_completed(tasks):
            batch_res = await task
            all_results.extend(batch_res)

        progress_bar.close()

        result_df = pd.DataFrame(all_results, columns=["Card Number", "Price"])
        result_df.to_csv(output_file, index=False)
        logging.info(f"查询结果已保存到 {output_file}")

    except Exception as e:
        logging.critical(f"主函数运行出错: {e}")

if __name__ == "__main__":
    asyncio.run(main())
