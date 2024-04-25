from __future__ import annotations

import itertools
import re
from typing import Any, Generator, Iterable, Optional

import docker
from docker.models.images import BuildError, json_stream
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


class DockerBuildLog(Event):
    log: str

    def render(self, console: Console):
        console.print(Padding.indent(renderable=Text.from_ansi(self.log), level=2))


# vendored from
# https://github.com/docker/docker-py/blob/9ad4bddc9ee23f3646f256280a21ef86274e39bc/docker/models/images.py#L220
def _build(docker_client: docker.DockerClient, **kwargs) -> Iterable[DockerBuildLog]:
    resp = docker_client.images.client.api.build(**kwargs)
    if isinstance(resp, str):
        return docker_client.images.get(resp)
    last_event = None
    image_id = None
    result_stream, internal_stream = itertools.tee(json_stream(resp))
    for chunk in internal_stream:
        if "error" in chunk:
            raise BuildError(chunk["error"], result_stream)
        if "stream" in chunk:
            yield DockerBuildLog(log=chunk["stream"])
            match = re.search(
                r"(^Successfully built |sha256:)([0-9a-f]+)$", chunk["stream"]
            )
            if match:
                image_id = match.group(2)
        last_event = chunk
    if image_id:
        return None
    raise BuildError(last_event or "Unknown", result_stream)


class DockerBuild(Tool):
    description = """
Build a docker image.
    """

    class Request(RequestEvent):
        dockerfile_path: str = Field(
            ...,
            pattern=r"^[a-zA-Z0-9\.]{1}.*$",
            description="Dockerfile path. ",
        )
        image_tag: str = Field(..., description="image tag")

    class Response(ResponseEvent):
        error: Optional[str] = Field(None, description="Error raised while building")
        build_logs: Optional[str] = Field(None, description="Build logs")

        def __rich_console__(
            self, console: Console, options: ConsoleOptions
        ) -> RenderResult:
            none_text = "[italic magenta]None[/]"
            error_text = (
                f"[green]'{self.error}'[/]" if self.error is not None else none_text
            )
            yield Text.from_markup("[bold magenta]Response[/](")
            if self.build_logs is not None:
                yield Text.from_markup('  [yellow]build_logs[/]= "')
                yield Text.from_ansi(self.build_logs)
                yield Text.from_markup('"')
            else:
                yield Text.from_markup(f"  [yellow]build_logs[/]={none_text}")
            yield Text.from_markup(f"  [yellow]error[/]={error_text}\n)")

    def __init__(self, project_root_path: str, docker_client: docker.DockerClient):
        self.project_root_path = project_root_path
        self.docker_client = docker_client

    def run(self, request: DockerBuild.Request) -> Generator[Event, Any, ResponseEvent]:
        yield Message(message="[bold cyan]Processing:[/] Building Docker image...")
        yield Message(message="[bold yellow]Docker build logs:[/]")
        try:
            for message in _build(
                self.docker_client,
                path=self.project_root_path,
                tag=request.image_tag,
            ):
                yield message
            return DockerBuild.Response()
        except BuildError as ex:
            logs = ""
            for log_line in ex.build_log:
                logs += log_line.get("stream", "")
            return DockerBuild.Response(error=str(ex), build_logs=logs[-800:])
        except (docker.errors.APIError, docker.errors.DockerException) as ex:
            return DockerBuild.Response(error=str(ex), build_logs="")
