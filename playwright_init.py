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
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--enable-webgl",
            "--ignore-certificate-errors",
            "--allow-running-insecure-content",
            "--disable-popup-blocking",
            "--disable-features=script-streaming",
            "--disable-extensions",
            "--mute-audio",
            "--disable-background-networking",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-breakpad",
            "--disable-client-side-phishing-detection",
        ]
    }
    if use_proxy:
        launch_args["proxy"] = {"server": proxy_server}

    browser = await playwright.chromium.launch(**launch_args)

    context_args = {
        "user_agent": user_agent,
        "viewport": {"width": 1920, "height": 1080},
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
        Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
        Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
        Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 2});
        Object.defineProperty(navigator, 'vendor', {get: () => 'Google Inc.'});
        Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
        
        window.chrome = { runtime: {} };
        
        Object.defineProperty(window, 'outerHeight', { get: () => window.innerHeight });
        Object.defineProperty(window, 'outerWidth', { get: () => window.innerWidth });

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

    # 图片请求拦截 + 网络请求反检测
    await page.route("**/*", lambda route: (
        route.abort()
        if route.request.resource_type in ["image"]
        else route.continue_()
    ))
    
    if USE_STEALTH:
        await stealth_async(page)

    logging.info("Browser initialized with advanced stealth settings")
    return playwright, browser, context, page
