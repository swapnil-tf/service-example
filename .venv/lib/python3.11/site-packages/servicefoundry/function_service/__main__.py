import json

import click

from servicefoundry.function_service.app import build_and_run_app
from servicefoundry.function_service.route import RouteGroups


####
# I am keeping the CLI here for now. This will get refactored going forward.
@click.group()
def cli():
    pass


# python -m servicefoundry.function_service run --port 8000 --route-group-json ""
# I am going to use this as "CMD" in the dockerfile to bring up the service
@cli.command()
@click.option("--route-groups-json", required=True, type=str)
@click.option("--port", required=True, type=int)
def run(port: int, route_groups_json: str):
    route_groups = RouteGroups.parse_obj(json.loads(route_groups_json))
    build_and_run_app(route_groups=route_groups, port=port)


if __name__ == "__main__":
    cli()
