import asyncio
from playwright.async_api import async_playwright
import easyocr
from PIL import Image
import numpy as np
import io

class BrowserControl:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.ocr_reader = easyocr.Reader(['en'])  # Initialize EasyOCR for English

    async def start_browser(self):
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

    async def navigate(self, url):
        if not self.page:
            await self.start_browser()
        await self.page.goto(url)

    async def screenshot(self, path):
        if not self.page:
            raise Exception("Browser not started")
        await self.page.screenshot(path=path)

    async def extract_text_from_screenshot(self, screenshot_path):
        image = Image.open(screenshot_path)
        # Convert PIL Image to numpy array
        image_np = np.array(image)
        results = self.ocr_reader.readtext(image_np)
        return ' '.join([result[1] for result in results])

    async def close(self):
        if self.browser:
            await self.browser.close()

async def main():
    browser_control = BrowserControl()
    await browser_control.start_browser()
    await browser_control.navigate("https://news.google.com")
    await browser_control.screenshot("example_screenshot.png")
    text = await browser_control.extract_text_from_screenshot("example_screenshot.png")
    print(f"Extracted text: {text}")
    await browser_control.close()

if __name__ == "__main__":
    asyncio.run(main())