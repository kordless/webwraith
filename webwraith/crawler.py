import functools
import logging
import requests

def function_call_logger(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger('webwraith')
        logger.info(f"Calling function: {func.__name__}")
        logger.info(f"Arguments: {args}, {kwargs}")
        result = func(*args, **kwargs)
        logger.info(f"Function {func.__name__} returned: {result}")
        return result
    return wrapper

class Crawler:
    @function_call_logger
    def crawl(self, url):
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            return f"Error crawling {url}: {str(e)}"

    @function_call_logger
    def parse(self, content):
        # Simple parsing logic - count words
        words = content.split()
        return f"Parsed content contains {len(words)} words"