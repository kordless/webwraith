import asyncio
from playwright.async_api import async_playwright
from typing import List, Dict

class LinkedInCrawler:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None

    async def start_browser(self):
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=False)  # Set to True for production
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

    async def login_to_linkedin(self, username: str, password: str):
        await self.page.goto("https://www.linkedin.com/login")
        await self.page.fill('input#username', username)
        await self.page.fill('input#password', password)
        await self.page.click('button[type="submit"]')
        await self.page.wait_for_load_state('networkidle')

    async def go_to_connections_page(self):
        await self.page.goto("https://www.linkedin.com/mynetwork/invite-connect/connections/")
        await self.page.wait_for_load_state('networkidle')

    async def scroll_and_extract_connections(self, max_connections: int = 100) -> List[Dict[str, str]]:
        connections = []
        last_height = await self.page.evaluate('document.body.scrollHeight')
        while len(connections) < max_connections:
            connection_elements = await self.page.query_selector_all('.mn-connection-card')
            for element in connection_elements[:max_connections - len(connections)]:
                name = await element.query_selector('.mn-connection-card__name')
                headline = await element.query_selector('.mn-connection-card__occupation')
                if name and headline:
                    connections.append({
                        "name": (await name.inner_text()).strip(),
                        "headline": (await headline.inner_text()).strip()
                    })
            await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(2)
            new_height = await self.page.evaluate('document.body.scrollHeight')
            if new_height == last_height:
                break
            last_height = new_height
        return connections

    async def close(self):
        if self.browser:
            await self.browser.close()

async def main():
    crawler = LinkedInCrawler()
    await crawler.start_browser()
    await crawler.login_to_linkedin("your_username", "your_password")
    await crawler.go_to_connections_page()
    connections = await crawler.scroll_and_extract_connections(max_connections=50)
    for connection in connections:
        print(f"Name: {connection['name']}, Headline: {connection['headline']}")
    await crawler.close()

if __name__ == "__main__":
    asyncio.run(main())