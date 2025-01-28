from flask import Flask, request, jsonify
import asyncio
from playwright_helpers import init_driver, close_popup, human_like_actions

app = Flask(__name__)

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
    print("=========")
    print(data)

    await asyncio.sleep(100)  # Add a delay after printing data

    # 使用 asyncio.run 包装异步逻辑
    async def process_request():
        playwright, browser, context, page = await init_driver(headless=True)
        try:
            url = "https://www.lululemon.com.au/en-au/content/gift-cards/gift-cards.html"
            await page.goto(url)
            await close_popup(page)

            # Simulate human-like actions
            await human_like_actions(page)

            # Placeholder for actual logic
            return {"message": "Parameters parsed successfully", "data": data}
        except Exception as e:
            return {"error": str(e)}
        finally:
            await browser.close()
            await playwright.stop()

    # Run the async logic and get the result
    result = asyncio.run(process_request())
    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True)
