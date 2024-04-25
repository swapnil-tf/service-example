from __future__ import annotations

from typing import Any, Generator, Optional

import requests
from pydantic import Field

from truefoundry.autodeploy.tools.base import (
    Event,
    Message,
    RequestEvent,
    ResponseEvent,
    Tool,
)


class SendRequest(Tool):
    description = """
Send an HTTP request.
"""

    def __init__(self):
        self.call_count = 0

    class Request(RequestEvent):
        method: str
        url: str

    class Response(ResponseEvent):
        response_code: Optional[int] = Field(None, description="Response Code")
        response_body: Optional[str] = None
        error: Optional[str] = Field(None, description="Error.")

    def run(self, request: SendRequest.Request) -> Generator[Event, Any, ResponseEvent]:
        self.call_count += 1
        yield Message(
            message=f"[bold cyan]Testing:[/] Sending a [magenta]{request.method.upper()}[/] request to [magenta]{request.url}[/]..."
        )
        try:
            response = requests.request(request.method.lower(), url=request.url)
            yield Message(
                message=f"[bold green]Success:[/] Received response with status code [magenta]{response.status_code}[/]"
            )
            return SendRequest.Response(
                response_code=response.status_code,
                response_body=response.text[-50:],
            )
        except Exception as ex:
            yield Message(
                message="[red]Alert:[/] Request could not be completed successfully."
            )
            return SendRequest.Response(
                error=str(ex),
            )
