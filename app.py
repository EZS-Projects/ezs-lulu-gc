from flask import Flask, request, jsonify
import asyncio
import pandas as pd
import logging
from tqdm.asyncio import tqdm
from playwright_helpers import init_driver, close_popup, human_like_actions, input_card_number_and_check, click_check_another_card
from card_processing import process_card_batches

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("../log/api_requests.log"), logging.StreamHandler()],
)

MAX_THREADS = 1  # 增加并发线程数

@app.route('/')
def hello_world():
    return 'Hello, World!'

@app.route('/check_gift_card_values', methods=['POST'])
async def check_gift_card_values():
    data = request.json
    if not isinstance(data, list):
        return jsonify({"error": "Invalid data format. Expected a list of objects."}), 400

    for item in data:
        if not all(key in item for key in ["card_type", "card_number", "card_issue_country", "calling_time"]):
            return jsonify({"error": "Each object must contain 'card_type', 'card_number', 'card_issue_country', and 'calling_time' fields."}), 400

    print("==== data ====")
    print(data)

    df = pd.DataFrame(data)

    lulu_cards = df[df['card_type'] == 'Lululemon-GC']
    print("==== luluCards ====")
    print(lulu_cards)

    lulu_gc_numbers = lulu_cards['card_number'].tolist()
    print("==== card_numbers ====")
    print(lulu_gc_numbers)

    print("===== 拿到了 GCNumber 继续处理 ====")

    logging.info(f"Total Lululemon cards to check: {len(lulu_gc_numbers)}")

    final_results = await process_card_batches(lulu_gc_numbers, MAX_THREADS)
    logging.info("All batch tasks completed")

    return jsonify({"results": final_results})

if __name__ == '__main__':
    app.run(debug=True)
