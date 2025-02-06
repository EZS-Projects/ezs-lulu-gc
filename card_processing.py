import asyncio
import logging
from playwright_helpers import close_popup, human_like_actions, input_card_number_and_check, open_check_dialogue, click_check_another_card
from playwright_init import init_driver

def split_card_numbers(card_numbers, num_batches):
    k, m = divmod(len(card_numbers), num_batches)
    return [
        card_numbers[i * k + min(i, m): (i + 1) * k + min(i + 1, m)]
        for i in range(num_batches)
    ]

async def process_card_batch(batch_id, card_numbers):
    logging.info(f"Batch {batch_id} started processing {len(card_numbers)} cards")
    results = []
    try:
        playwright, browser, context, page = await init_driver(headless=False)
        print("===浏览器已经初始化 准备跳转===")
        await page.goto("https://www.lululemon.com.au/en-au/content/gift-cards/gift-cards.html")
        print("===窗口页面已经跳转完毕===")
        await close_popup(page)
        print("===已经关闭/跳过了popup的窗口====")
        await open_check_dialogue(page)
        print("===已经打开查询的窗口====")
        
        for idx, card_number in enumerate(card_numbers, start=1):
            logging.info(f"Batch {batch_id} => Checking card {idx}/{len(card_numbers)}: {card_number}")
            logging.info(f"开始查询卡号: {card_number}")
            balance = await input_card_number_and_check(page, card_number)
            results.append({"card_number": card_number, "balance": balance})

            if balance != "Error":
                try:
                    await human_like_actions(page)
                    await click_check_another_card(page)
                except Exception as e:
                    logging.error(f"Batch {batch_id} failed to return to input page: {e}")

    except Exception as e:
        logging.critical(f"Batch {batch_id} encountered a fatal error: {e}")
    finally:
        await browser.close()
        await playwright.stop()
        logging.info(f"Batch {batch_id} browser closed")
    
    return results

async def process_card_batches(card_numbers, max_threads):
    batches = split_card_numbers(card_numbers, max_threads)
    logging.info(f"Divided into {len(batches)} batches")

    tasks = [process_card_batch(batch_id + 1, batch) for batch_id, batch in enumerate(batches)]
    all_results = await asyncio.gather(*tasks)

    final_results = [item for batch in all_results for item in batch]
    return final_results
