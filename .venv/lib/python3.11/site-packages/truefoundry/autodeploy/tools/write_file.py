# deprecated
from __future__ import annotations

import os
from typing import Optional

from pydantic import BaseModel, Field
from rich.console import Console
from rich.prompt import Confirm

from truefoundry.autodeploy.tools.base import Tool
from truefoundry.autodeploy.utils.diff import Diff

INTERACTIVE_SESSION = True


class WriteFile(Tool):
    description = """
Write contents to a file.
Read first before write.
"""

    class Request(BaseModel):
        path: str = Field(
            ...,
            pattern=r"^[a-zA-Z0-9\.]{1}.*$",
            description="File path to write.",
        )
        content: str = Field(..., description="Content of the file.")
        justification: str = Field(
            ...,
            description="Justification of why the new content is required. Ensure the justification, justifies the content.",
        )

    class Response(BaseModel):
        cancellation_reason: Optional[str] = Field(
            None, description="Operation cancelled by user"
        )

        error: Optional[str] = Field(
            None,
            description="Error while opening a file.",
        )

    def __init__(self, project_root_path: str):
        self.project_root_path = project_root_path

    def _user_interaction(
        self, request: WriteFile.Request, console: Console
    ) -> Optional[WriteFile.Response]:
        console.log("You are about to write or edit a file.")

        console.print(f"Displaying changes in {request.path}")
        prev_content = ""

        if os.path.exists(os.path.join(self.project_root_path, request.path)):
            with open(
                os.path.join(self.project_root_path, request.path),
                "r",
                encoding="utf8",
            ) as f:
                prev_content = f.read()

        console.print(
            Diff(
                lhs=prev_content,
                rhs=request.content,
                width=os.get_terminal_size().columns,
            )
        )
        response = Confirm.ask(
            f"Writing file at {request.path}?",
        )
        if not response:
            description = console.input(
                "You chose to cancel. Can you provide a reason why? [green]>> "
            )
            return WriteFile.Response(
                cancellation_reason=description, error="Operation cancelled by user."
            )
        console.log(f"Writing file to {request.path}")

    def run(
        self,
        request: WriteFile.Request,
        console: Console,
    ) -> WriteFile.Response:
        if INTERACTIVE_SESSION:
            interaction_response = self._user_interaction(request, console)
            if isinstance(interaction_response, WriteFile.Response):
                return interaction_response
        try:
            with open(
                os.path.join(self.project_root_path, request.path),
                "w",
                encoding="utf8",
            ) as f:
                f.write(request.content)
                return WriteFile.Response()
        except FileNotFoundError as ex:
            return WriteFile.Response(error=str(ex))
