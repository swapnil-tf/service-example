from __future__ import annotations

from typing import Dict, Optional

import docker
from openai import OpenAI
from pydantic import Field
from rich.console import Console

from truefoundry.autodeploy.agents.base import Agent
from truefoundry.autodeploy.agents.project_identifier import ProjectIdentifier
from truefoundry.autodeploy.tools import (
    Ask,
    DockerRun,
    RequestEvent,
    ResponseEvent,
    SendRequest,
)


class Tester(Agent):
    description = """
Tester
"""
    system_prompt = """
Your goal is to test a docker image.
In case the image is running a service, you can send a request to the endpoint to verify everything is running fine.
If you find any port number in the logs. Re run the docker image by exposing that port correctly.

If the image is not running a service, try to identify whether there is any issue.
Your goal is not to fix the issue. Your goal is to create a very detailed justification and report whether
the testing was succesful.
Always response with a function call.
Return response once you are done testing.
    """
    max_iter = 30

    class Request(RequestEvent):
        project_identity: ProjectIdentifier.Response
        image_tag: str
        command: str
        port_to_be_exposed: Optional[int] = None

    class Response(ResponseEvent):
        successful: bool = Field(..., description="is everything fine?")
        justification: str = Field(
            ...,
            description="""
Why was the testing a failure or successful?
        """,
        )
        logs: str

        def render(self, console: Console):
            console.print(
                f"[bold cyan]TrueFoundry:[/] The given project has been {'[bold green]successfully built[/]' if self.successful else '[bold red]failed to build[/]'}"
            )
            console.print(
                f"[bold magenta]TrueFoundry:[/] [italic]{self.justification}[/]"
            )
            if not self.successful:
                console.print(f"[cyan]logs:[/] {self.logs}")

    def __init__(
        self,
        docker_client: docker.DockerClient,
        openai_client: OpenAI,
        environment: Dict,
    ):
        self.tools = [
            SendRequest(),
            Ask(),
            DockerRun(docker_client=docker_client, environment=environment),
        ]
        self.openai_client = openai_client
