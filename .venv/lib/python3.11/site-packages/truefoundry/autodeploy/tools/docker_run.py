from __future__ import annotations

import atexit
from typing import Any, Dict, Generator, List, Optional

import docker
import requests
from pydantic import Field
from rich.console import Console, ConsoleOptions, RenderResult
from rich.padding import Padding
from rich.text import Text

from truefoundry.autodeploy.tools.base import (
    Event,
    Message,
    RequestEvent,
    ResponseEvent,
    Tool,
)


class DockerRunLog(Event):
    index: int
    log: str

    def render(self, console: Console):
        # if self.index > 1:
        #     print("\r", end="")
        console.print(Padding.indent(renderable=Text.from_ansi(self.log), level=2))
        # console.print("Press control-c to stop waiting for more logs", end="")


class DockerRun(Tool):
    description = """
Run a docker image
"""

    class Request(RequestEvent):
        image_tag: str
        ports: Optional[Dict[str, int]] = Field(
            None,
            description="""
Ports to expose.
The keys of the dictionary are the ports to bind inside the container in 'port'.
The values are the ports to open on the host""",
        )
        command: str

        def render(self, console: Console):
            console.print(
                f"[bold magenta]TrueFoundry[/] is executing the Docker container. Image Tag: [bold green]{self.image_tag}[/], Exposed Port: [bold green]{str(self.ports) if self.ports is not None else 'Not exposed'}[/], Command: [bold green]{self.command}[/]"
            )

    class Response(ResponseEvent):
        logs: Optional[List[str]] = Field(
            None, description="Logs of the container. Only last 50 chars."
        )
        exit_code: Optional[int] = Field(
            None,
            description="""
Exit code of the process if the container stops.
This will not be passed if the container is still running.
""",
        )
        client_error: Optional[str] = Field(None, description="Docker client error.")

        def __rich_console__(
            self, console: Console, options: ConsoleOptions
        ) -> RenderResult:
            none_text = "[italic magenta]None[/]"
            error_text = (
                f"[green]'{self.client_error}'[/]"
                if self.client_error is not None
                else none_text
            )
            exit_code_text = (
                "[green]'0'[/]"
                if self.exit_code == 0
                else (
                    none_text if self.exit_code is None else f"[red]{self.exit_code}[/]"
                )
            )

            yield Text.from_markup("[bold magenta]Response[/](")
            if self.logs is not None:
                yield Text.from_markup('  [yellow]logs=[/]"')
                yield Text.from_ansi("".join(self.logs))
                yield Text.from_markup('"')
            else:
                yield Text.from_markup(f"  [yellow]logs[/]={none_text}")

            yield Text.from_markup(f"  [yellow]exit_code[/]={exit_code_text}")
            yield Text.from_markup(f"  [yellow]client_error[/]={error_text} \n)")

    def __init__(self, docker_client: docker.DockerClient, environment: Dict):
        self.containers = []
        self.docker_client = docker_client
        self.environment = environment
        atexit.register(self._kill_running_containers)

    def _kill_running_containers(self):
        if self.containers:
            container = self.containers.pop()
            try:
                container.remove(force=True)
            except docker.errors.APIError:
                pass

    def run(self, request: DockerRun.Request) -> Generator[Event, Any, ResponseEvent]:
        self._kill_running_containers()
        yield Message(message="[bold cyan]Testing:[/] Running Docker container...")
        try:
            container = self.docker_client.containers.run(
                request.image_tag,
                detach=True,
                remove=False,
                stderr=True,
                ports=request.ports,
                environment=self.environment,
                command=request.command,
            )
        except docker.errors.APIError as ex:
            if ex.is_client_error():
                return DockerRun.Response(client_error=str(ex))
            raise
        yield Message(message="[bold yellow]Docker logs:[/]")
        self.containers.append(container)
        exit_code = None

        all_logs = []
        logs = container.logs(stream=True)

        try:
            for i, log in enumerate(logs):
                log = log.decode()
                all_logs.append(log)
                yield DockerRunLog(index=i, log=log)
        except KeyboardInterrupt:
            pass
        else:
            yield Message(message="\n[bold yellow]There are no more logs.[/]")
        exit_code = None
        try:
            exit_code = container.wait(timeout=1).get("StatusCode")
        except (
            requests.exceptions.ReadTimeout,
            requests.exceptions.ConnectionError,
        ):
            ...
        return DockerRun.Response(logs=all_logs, exit_code=exit_code)
