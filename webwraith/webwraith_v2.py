import click
import sys
import os

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Configuration and logging
from lib.config import Config
config = Config()
logger = config.logger

@click.group()
def cli():
    pass

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
def world():
    """Prints Hello, world!"""
    logger.info("Hello, World! command was called")
    click.echo('Hello, World! Welcome to WebWraith CLI.')

if __name__ == '__main__':
    cli()