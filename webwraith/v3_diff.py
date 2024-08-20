import re
import click
import os
import asyncio
import sys
from browser_control_v2 import BrowserControl

# Add additional functions and modifications
@click.command()
@click.option('-f', '--file', required=True, help="The path to the file of URLs to crawl.")
def crawl(file):
    """Crawl the given file, take screenshots of each URL, and save them in the screenshots directory."""
    try:
        with open(file, 'r') as f:
            content = f.read()
            urls = extract_urls(content)

            # Ensure the screenshots directory exists
            screenshots_dir = Config().get_screenshots_dir()
            if not os.path.exists(screenshots_dir):
                os.makedirs(screenshots_dir)

            # Start the browser and crawl URLs
            asyncio.run(crawl_urls(urls, screenshots_dir))
            
            return {
                "success": True,
                "result": {
                    "file": file,
                    "urls_found": urls,
                    "url_count": len(urls)
                }
            }

    except FileNotFoundError:
        error_message = f"File '{file}' not found."
        click.echo(error_message)
        return {
            "success": False,
            "error": error_message
        }
    except Exception as e:
        error_message = f"An error occurred while processing the file: {str(e)}"
        click.echo(error_message)
        return {
            "success": False,
            "error": error_message
        }


def extract_urls(file_content):
    """Extract URLs from the given file content."""
    url_pattern = re.compile(r'https?://\S+')
    return url_pattern.findall(file_content)


async def crawl_urls(urls, screenshots_dir):
    """Crawl each URL and take screenshots."""
    browser_control = BrowserControl()
    await browser_control.start_browser()

    for url in urls:
        # Remove slashes and dots to create a valid filename
        filename = url.replace('https://', '').replace('http://', '').replace('/', '_').replace('.', '_') + '.png'
        screenshot_path = os.path.join(screenshots_dir, filename)
        
        await browser_control.navigate(url)
        await browser_control.screenshot(screenshot_path)

    await browser_control.close()


if __name__ == "__main__":
    crawl()