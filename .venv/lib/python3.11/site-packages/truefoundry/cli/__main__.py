import sys

import click

from truefoundry.deploy.cli.cli import create_truefoundry_cli

MLFOUNDRY_INSTALLED = True


try:
    from mlfoundry.cli.commands import download
except ImportError:
    MLFOUNDRY_INSTALLED = False


@click.group()
def ml():
    """MlFoundry CLI"""


def main():
    # Exit the interpreter by raising SystemExit(status).
    # If the status is omitted or None, it defaults to zero (i.e., success).
    # If the status is an integer, it will be used as the system exit status.
    # If it is another kind of object, it will be printed and the system exit status will be one (i.e., failure).
    try:
        cli = create_truefoundry_cli()
        if MLFOUNDRY_INSTALLED:
            ml.add_command(download)
            cli.add_command(ml)
    except Exception as e:
        raise click.exceptions.UsageError(message=str(e)) from e
    sys.exit(cli())


if __name__ == "__main__":
    main()
