import asyncio
from playwright.async_api import async_playwright
import json

async def scrape_page_content(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        
        # Block images and media to speed up loading
        await context.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "media", "font"] else route.continue_())
        page = await context.new_page()
        await page.goto(url)
        
        # Wait for the necessary content to load
        await page.wait_for_selector('body')
        
        # Extract all text content inside the body
        page_content = await page.locator('body').inner_text()
        print(page_content[:40000])

        await browser.close()

        return {
            "url": url,
            "content": page_content
        }

async def main():
    url = "https://apnews.com/"
    page_data = await scrape_page_content(url)
    
    with open("page_content.json", "w", encoding="utf-8") as file:
        json.dump(page_data, file, indent=4)

    print("Page content has been saved to page_content.json")

# Execute the main function
asyncio.run(main())
