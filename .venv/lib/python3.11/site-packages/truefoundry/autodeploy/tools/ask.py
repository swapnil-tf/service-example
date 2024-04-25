from __future__ import annotations

from typing import Iterable

from rich.console import Console

from truefoundry.autodeploy.tools.base import Event, RequestEvent, ResponseEvent, Tool
from truefoundry.autodeploy.utils.pydantic_compat import model_dump


class AskQuestion(Event):
    question: str

    def render(self, console: Console) -> str:
        console.print(f"[bold magenta]TrueFoundry:[/] {self.question}")
        response = console.input("[bold green]You:[/] ")
        return response


class Ask(Tool):
    description = """
Ask a question to the user.
"""

    class Request(RequestEvent):
        question: str

    class Response(ResponseEvent):
        response: str

    def run(self, request: Ask.Request) -> Iterable[Event]:
        response = yield AskQuestion(**model_dump(request))
        return Ask.Response(response=response)
