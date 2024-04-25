import functools
import sys
import zipfile

import rich_click as click
from packaging.version import parse as parse_version
from requests.exceptions import ConnectionError
from rich.padding import Padding
from rich.panel import Panel

from servicefoundry.cli.console import console
from servicefoundry.lib.exceptions import BadRequestException, ConfigurationException
from servicefoundry.lib.util import is_debug_env_set


def setup_rich_click():
    click.rich_click.STYLE_ERRORS_SUGGESTION = "blue italic"
    click.rich_click.SHOW_ARGUMENTS = True
    click.rich_click.USE_RICH_MARKUP = True
    click.rich_click.STYLE_HELPTEXT = ""


def handle_exception(exception):
    if is_debug_env_set():
        console.print_exception(show_locals=True)
    if isinstance(exception, BadRequestException):
        print_error(
            f"[cyan bold]status_code[/] {exception.status_code}\n"
            f"[cyan bold]message[/]     {exception.message}"
        )
    elif isinstance(exception, ConnectionError):
        print_error(f"Couldn't connect to Servicefoundry.")
    elif isinstance(exception, ConfigurationException):
        print_error(f"[cyan bold]message[/]     {exception.message}")
    else:
        console.print(f"[red][bold]Error:[/] {str(exception)}[/]")


def handle_exception_wrapper(fn):
    @functools.wraps(fn)
    def inner(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            handle_exception(e)
            sys.exit(1)

    return inner


def print_error(message):
    text = Padding(message, (0, 1))
    console.print(
        Panel(
            text,
            border_style="red",
            title="Command failed",
            title_align="left",
            width=click.rich_click.MAX_WIDTH,
        )
    )


def print_message(message):
    text = Padding(message, (0, 1))
    console.print(
        Panel(
            text,
            border_style="cyan",
            title="Success",
            title_align="left",
            width=click.rich_click.MAX_WIDTH,
        )
    )


def unzip_package(path_to_package, destination):
    with zipfile.ZipFile(path_to_package, "r") as zip_ref:
        zip_ref.extractall(destination)


def _prompt_if_no_value_and_supported(prompt: str, hide_input: bool = True):
    import click as _click

    kwargs = {}
    if parse_version(_click.__version__).major >= 8:
        kwargs = dict(prompt=prompt, hide_input=hide_input, prompt_required=False)

    return kwargs
