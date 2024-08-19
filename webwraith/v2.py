import click
import sys
import os
import json
import ast
import inspect
from typing import Dict, Any, List

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Configuration and logging
from lib.config import Config
from substrate import Substrate, ComputeJSON

config = Config()
logger = config.logger

tools = []  # A registry to hold all decorated functions' info
callable_registry = {}  # A registry to hold the functions themselves

class FunctionWrapper:
    def __init__(self, func):
        self.func = func
        self.info = self.extract_function_info()
        callable_registry[func.__name__] = func
        tools.append({'type': 'function', 'function': self.info})  # Add function info to registry

    def extract_function_info(self):
        source = inspect.getsource(self.func)
        tree = ast.parse(source)
        function_name = tree.body[0].name
        function_description = self.extract_description_from_docstring(self.func.__doc__)
        args = tree.body[0].args
        parameters = {"type": "object", "properties": {}, "required": []}
        for arg in args.args:
            argument_name = arg.arg
            argument_type = self.convert_type_name(self.extract_parameter_type(argument_name, self.func.__doc__)) or "string"
            parameter_description = self.extract_parameter_description(argument_name, self.func.__doc__)
            parameters["properties"][argument_name] = {
                "type": argument_type,
                "description": parameter_description,
            }
            if arg.arg != 'self':  # Exclude 'self' from required parameters for class methods
                parameters["required"].append(argument_name)
        
        return_type = self.convert_type_name(self.extract_return_type(tree))
        function_info = {
            "name": function_name,
            "description": function_description,
            "parameters": parameters,
            "return_type": return_type,
        }
        return function_info

    def extract_description_from_docstring(self, docstring):
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

    def extract_parameter_type(self, parameter_name, docstring):
        if docstring:
            type_prefix = f":type {parameter_name}:"
            lines = docstring.strip().split("\n")
            for line in lines:
                if line.strip().startswith(type_prefix):
                    return line.replace(type_prefix, "").strip()
        return None

    def extract_parameter_description(self, parameter_name, docstring):
        if docstring:
            param_prefix = f":param {parameter_name}:"
            lines = docstring.strip().split("\n")
            for line in lines:
                if line.strip().startswith(param_prefix):
                    return line.replace(param_prefix, "").strip()
        return "No description provided."

    def extract_return_type(self, tree):
        if tree.body[0].returns:
            return_type_segment = ast.get_source_segment(inspect.getsource(self.func), tree.body[0].returns)
            if return_type_segment:
                return return_type_segment.strip()
        return "None"

    def convert_type_name(self, type_name):
        type_mapping = {
            'int': 'integer',
            'str': 'string',
            'bool': 'boolean',
            'float': 'number',
            'list': 'array',
            'dict': 'object',
        }
        return type_mapping.get(type_name, type_name)

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

def function_info_decorator(func):
    wrapped_function = FunctionWrapper(func)
    def wrapper(*args, **kwargs):
        return wrapped_function(*args, **kwargs)
    wrapper.function_info = wrapped_function.info
    return wrapper

@click.group()
def cli():
    """WebWraith CLI - A powerful web crawling and automation tool."""

# Setup
@cli.command()
@click.option('--substrate-key', prompt='Substrate Key', help='API key for the substrate.', default='')
def setup(substrate_key):
    """Setup the substrate key."""
    result = config.get_substrate_token()
    if result['error']:
        click.echo(f"Error: {result['error']}")
    else:
        click.echo('Substrate key is valid and configured.')

@cli.command()
@click.option('--message', default=None, help='Custom message to display')
def hello(message: str = None) -> Dict[str, Any]:
    """
    Prints a greeting message, either 'Hello, World!' or a custom message if provided.
    When the model returns a value, it can put \(<val>\) around it to colorize it.
    
    :param message: Optional custom message to display instead of 'World'.
    :type message: str
    :return: A dictionary containing the result of the operation.
    :rtype: dict
    """
    logger.info("Hello, World! command was called")
    
    if message:
        display_message = f'Hello, {message}! Welcome to WebWraith CLI.'
    else:
        display_message = 'Hello, World! Welcome to WebWraith CLI.'
    
    click.echo(display_message)
    
    return {
        "success": True,
        "result": display_message
    }

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
    tools_info = json.dumps(tools, indent=2)
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
        
        if func_name in callable_registry:
            logger.info(f"Executing function: {func_name} with parameters: {func_params}")
            func = callable_registry[func_name]
            result = func(**func_params)
            logger.info(f"Function result: {result}")
            click.echo(f"Function result: {json.dumps(result, indent=2)}")
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