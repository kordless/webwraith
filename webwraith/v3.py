import click
import sys
import os
import json
import ast
import re
import inspect
import easyocr
from typing import Dict, Any, List
from playwright.async_api import async_playwright
import easyocr
from PIL import Image
import numpy as np

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Configuration and logging
from lib.config import Config
from substrate import Substrate, ComputeJSON

config = Config()
logger = config.logger

function_registry = {}  # A registry to hold function metadata

def register_function(func):
    """
    Register a function and its metadata in the function registry.
    """
    function_info = extract_function_info(func)
    function_registry[func.__name__] = {
        'function': func,
        'info': function_info
    }
    return func

def extract_function_info(func):
    source = inspect.getsource(func)
    tree = ast.parse(source)
    function_name = tree.body[0].name
    function_description = extract_description_from_docstring(func.__doc__)
    args = tree.body[0].args
    parameters = {"type": "object", "properties": {}, "required": []}
    for arg in args.args:
        argument_name = arg.arg
        argument_type = convert_type_name(extract_parameter_type(argument_name, func.__doc__)) or "string"
        parameter_description = extract_parameter_description(argument_name, func.__doc__)
        parameters["properties"][argument_name] = {
            "type": argument_type,
            "description": parameter_description,
        }
        if arg.arg != 'self':  # Exclude 'self' from required parameters for class methods
            parameters["required"].append(argument_name)
    
    return_type = convert_type_name(extract_return_type(tree))
    function_info = {
        "name": function_name,
        "description": function_description,
        "parameters": parameters,
        "return_type": return_type,
    }
    return function_info

def extract_description_from_docstring(docstring):
    if docstring:
        lines = docstring.strip().split("\n")
        description_lines = []
        for line in lines:
            line = line.strip()
            if line.startswith(":param") or line.startswith(":type") or line.startswith(":return"):
                break
            if line:
                description_lines.append(line)
        return "\n".join(description_lines)
    return "No description provided."

def extract_parameter_type(parameter_name, docstring):
    if docstring:
        type_prefix = f":type {parameter_name}:"
        lines = docstring.strip().split("\n")
        for line in lines:
            if line.strip().startswith(type_prefix):
                return line.replace(type_prefix, "").strip()
    return None

def extract_parameter_description(parameter_name, docstring):
    if docstring:
        param_prefix = f":param {parameter_name}:"
        lines = docstring.strip().split("\n")
        for line in lines:
            if line.strip().startswith(param_prefix):
                return line.replace(param_prefix, "").strip()
    return "No description provided."

def extract_return_type(tree):
    if isinstance(tree.body[0], ast.FunctionDef):
        returns = tree.body[0].returns
        if returns:
            if isinstance(returns, ast.Name):
                return returns.id
            elif isinstance(returns, ast.Subscript):
                return ast.unparse(returns)
    return "None"

def convert_type_name(type_name):
    type_mapping = {
        'int': 'integer',
        'str': 'string',
        'bool': 'boolean',
        'float': 'number',
        'list': 'array',
        'dict': 'object',
    }
    return type_mapping.get(type_name, type_name)

# Browser control class
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


# The CLI
@click.group()
def cli():
    """WebWraith CLI - A powerful web crawling tool."""

@cli.command()
@click.option('--substrate-key', help='API key for Substrate. If not provided, validates the existing key.', default=None)
@register_function
def setup(substrate_key: str = None) -> Dict[str, Any]:
    """
    Setup or validates the Substrate.run API key.

    :param substrate_key: API key for Substrate.run. If not provided, validates the existing key.
    :type substrate_key: str or None
    :return: A dictionary containing the result of the operation.
    :rtype: Dict[str, Any]
    """
    if substrate_key is not None:
        # If a new key is provided, set it
        result = config.set_substrate_token(substrate_key)
    else:
        # If no key is provided, validate the existing one
        result = config.get_substrate_token()

    if result.get('error'):
        error_message = f"Error: {result['error']}"
        click.echo(error_message)
        return {"success": False, "error": error_message}
    else:
        if substrate_key is not None:
            success_message = 'New substrate key is valid and has been configured.'
        else:
            success_message = 'Existing substrate key is valid.'
        click.echo(success_message)
        return {"success": True, "result": success_message}

@cli.command()
@click.argument('message', nargs=-1, default=None)
@click.option('--message', '-m', 'message_option', help='Custom message to display')
@register_function
def hello(message: tuple = None, message_option: str = None) -> Dict[str, Any]:
    """
    Prints a greeting message, either 'Hello, World!' or a custom message if provided.
    The message can be provided as positional arguments or using the --message option.
    When the model returns a value, it can put \(<val>\) around it to colorize it.
    
    :param message: Optional custom message to display (as positional arguments).
    :type message: tuple
    :param message_option: Optional custom message to display (using --message option).
    :type message_option: str
    :return: A dictionary containing the result of the operation.
    :rtype: dict
    """
    logger.info("Hello, World! command was called")
    
    if message_option:
        display_message = f'Hello, {message_option}! Welcome to WebWraith CLI.'
    elif message:
        display_message = f'Hello, {"".join(message)}! Welcome to WebWraith CLI.'
    else:
        display_message = 'Hello, World! Welcome to WebWraith CLI.'
    
    click.echo(display_message)
    
    return {
        "success": True,
        "result": display_message
    }

import asyncio

@cli.command()
@click.option('-f', '--file', help="The path to the file of URLs to crawl.")
@click.option('-u', '--uri', help="A single URI to crawl.")
@click.option('-s', '--statement', help="An optional statement to associate with the crawl.")
def crawl(file, uri, statement):
    """
    Crawl the given file of URLs or a single URI, take screenshots, and optionally associate a statement.
    Either --file or --uri must be provided.
    """
    if not file and not uri:
        click.echo("Error: Either --file or --uri must be provided.")
        return

    if file and uri:
        click.echo("Error: Please provide either --file or --uri, not both.")
        return

    asyncio.run(async_crawl(file, uri, statement))

async def async_crawl(file, uri, statement):
    try:
        urls = []
        if file:
            with open(file, 'r') as f:
                content = f.read()
                urls = extract_urls(content)
        elif uri:
            urls = [uri]

        # Ensure the screenshots directory exists
        screenshots_dir = config.get_screenshots_dir()
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)

        # Start the browser and crawl URLs
        await crawl_urls(urls, screenshots_dir, statement)
        
        click.echo(f"Crawling completed. {len(urls)} URLs processed.")
        return {
            "success": True,
            "result": {
                "file": file,
                "uri": uri,
                "statement": statement,
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
        error_message = f"An error occurred while processing: {str(e)}"
        click.echo(error_message)
        return {
            "success": False,
            "error": error_message
        }

async def crawl_urls(urls, screenshots_dir, statement=None):
    """Crawl each URL and take screenshots."""
    browser_control = BrowserControl()
    await browser_control.start_browser()

    for url in urls:
        # Remove slashes and dots to create a valid filename
        filename = url.replace('https://', '').replace('http://', '').replace('/', '_').replace('.', '_') + '.png'
        screenshot_path = os.path.join(screenshots_dir, filename)
        
        try:
            await browser_control.navigate(url)
            await browser_control.screenshot(screenshot_path)
            click.echo(f"Screenshot saved for {url}")
            
            # Extract text from the screenshot
            text = await browser_control.extract_text_from_screenshot(screenshot_path)
            click.echo(f"Extracted text from {url}: {text[:100]}...")  # Print first 100 characters
            
            if statement:
                click.echo(f"Associated statement: {statement}")
        except Exception as e:
            click.echo(f"Error processing {url}: {str(e)}")

    await browser_control.close()

# Crawl functions
def extract_urls(file_content):
    """Extract URLs from the given file content."""
    url_pattern = re.compile(r'https?://\S+')
    return url_pattern.findall(file_content)


@cli.command()
@click.argument('command', nargs=-1)
def run(command: tuple) -> Dict[str, Any]:
    """
    Catch-all command that uses AI to process the input.
    :param command: The command and arguments to process.
    :type command: tuple
    """
    logger.info(f"Run command called with arguments: {command}")
    
    substrate_key = config.get_substrate_token()
    if substrate_key.get('error'):
        logger.error(f"Substrate key error: {substrate_key['error']}")
        click.echo(f"Error: {substrate_key['error']}")
        return {"success": False, "error": substrate_key['error']}

    substrate = Substrate(api_key=substrate_key['token'])

    # Simplified schema for function calling
    function_call_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "parameters": {"type": "object"}
        },
        "required": ["name", "parameters"]
    }

    # Construct the prompt with tools information
    tools_info = json.dumps([info['info'] for info in function_registry.values()], indent=2)
    prompt = f"""Process the following command: {' '.join(command)}

Available tools:
{tools_info}

Based on the command and available tools, determine the appropriate function to call and its parameters.
Respond with a JSON object containing the function name and parameters."""

    json_node = ComputeJSON(
        prompt=prompt,
        json_schema=function_call_schema
    )

    try:
        logger.info("Sending request to Substrate API")
        result = substrate.run(json_node)
        logger.info("Received response from Substrate API")
        logger.debug(f"Raw API response: {result.api_response.json}")
        
        # Extract the function call details from the API response
        ai_response = result.api_response.json
        logger.debug(f"AI response: {ai_response}")
        
        compute_json_key = next(iter(ai_response['data']))
        function_call = ai_response['data'][compute_json_key]['json_object']
        
        logger.info(f"Extracted function call: {function_call}")
        
        func_name = function_call['name']
        func_params = function_call['parameters']
        
        if func_name in function_registry:
            logger.info(f"Executing function: {func_name} with parameters: {func_params}")
            func = function_registry[func_name]['function']
            result = func(**func_params)
            logger.info(f"Function result: {result}")
            # click.echo(f"Function result: {json.dumps(result, indent=2)}")
            return {"success": True, "result": result}
        else:
            logger.warning(f"Function '{func_name}' not found in registry")
            error_message = f"Error: Function '{func_name}' not found in registry."
            click.echo(error_message)
            return {"success": False, "error": error_message}
    except json.JSONDecodeError as e:
        logger.error(f"JSON decoding error: {str(e)}")
        error_message = f"Error decoding JSON: {str(e)}"
        click.echo(error_message)
        return {"success": False, "error": error_message}
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        line_number = exc_traceback.tb_lineno
        error_message = f"Error processing command with AI on line {line_number}: {str(e)}"
        logger.error(error_message, exc_info=True)
        click.echo(error_message)
        return {"success": False, "error": error_message}

if __name__ == '__main__':
    cli()