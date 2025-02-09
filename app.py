from flask import Flask, request, jsonify
import pandas as pd
import logging
import asyncio
from playwright_helpers import close_popup, human_like_actions, input_card_number_and_check, click_check_another_card
from playwright_init import init_driver
from card_processing import process_card_batches

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("../log/api_requests.log"), logging.StreamHandler()],
)

MAX_THREADS = 3  # 增加并发线程数

@app.route('/hello')
def hello_world():
    return 'Hello, World!'

@app.route('/check_lululemon_gift_card_values', methods=['POST'])
def check_gift_card_values():
    input_data = request.json
    if not isinstance(input_data, list):
        return jsonify({"error": "Invalid data format. Expected a list of objects."}), 200

    if len(input_data) > 3:
        return jsonify({"error": "Query cannot exceed 3 items per request."}), 200

    for item in input_data:
        if not all(key in item for key in ["card_type", "card_number", "card_issue_country", "calling_time"]):
            return jsonify({"error": "Each object must contain 'card_type', 'card_number', 'card_issue_country', and 'calling_time' fields."}), 200

    print("==== input_data ====")
    print(input_data)

    df = pd.DataFrame(input_data)
    lulu_cards = df[df['card_type'] == 'Lululemon-GC']
    print("==== luluCards ====")
    print(lulu_cards)

    lulu_gc_numbers = lulu_cards['card_number'].tolist()
    print("==== card_numbers ====")
    print(lulu_gc_numbers)

    logging.info(f"Total Lululemon cards to check: {len(lulu_gc_numbers)}")

    # 等待异步任务的结果
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    final_results = loop.run_until_complete(process_card_batches(lulu_gc_numbers, MAX_THREADS))
    
    if isinstance(final_results, list):
        print("======原始数据=======")
        print(input_data)
        print("========最终结果========")
        print(final_results)
    else:
        print("========错误: process_card_batches 没有返回列表========")
        return jsonify({"error": "Internal processing error"}), 500
    
    for original, result in zip(input_data, final_results):
        original["is_call_success"] = True if result.get("balance") is not None else False
        original["balance"] = result.get("balance")
        original["balance_timestamp"] = result.get("timestamp")
        original["time_used_by_s"] = result.get("timestamp", 0) - original["calling_time"]
    
    logging.info("All batch tasks completed")
    return jsonify({"results": input_data})

if __name__ == '__main__':
    app.run(debug=True)
