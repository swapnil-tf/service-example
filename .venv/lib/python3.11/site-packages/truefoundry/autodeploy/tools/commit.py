from __future__ import annotations

import os
import tempfile
from typing import Any, Generator, Optional

from git import Repo
from pydantic import Field
from rich.console import Console
from rich.padding import Padding
from rich.prompt import Confirm

from truefoundry.autodeploy.logger import logger
from truefoundry.autodeploy.tools.base import (
    Event,
    Message,
    RequestEvent,
    ResponseEvent,
    Tool,
)
from truefoundry.autodeploy.utils.diff import LLMDiff
from truefoundry.autodeploy.utils.pydantic_compat import model_dump


class CommitConfirmation(Event):
    patch: str
    commit_message: str

    def render(self, console: Console) -> Optional["Commit.Response"]:
        console.print("[bold magenta]TrueFoundry[/] wants to make a commit,", end=" ")
        console.print(f"with Commit Message: [green]{self.commit_message}[/]")
        console.print("[yellow]Displaying changes to be made by the patch[/]")
        console.print(Padding.indent(renderable=LLMDiff(self.patch), level=2))

        response = Confirm.ask(
            "Apply patch?",
        )
        if not response:
            description = console.input(
                "You chose to cancel. Can you provide a reason why? [green]>> "
            )
            return Commit.Response(
                cancellation_reason=description, error="Operation cancelled by user."
            )


class Commit(Tool):
    description = """
Git commit.
"""

    class Request(RequestEvent):
        patch: str = Field(
            ...,
            description="""
Patch file content.

The format starts with the same two-line header as the context format, except that the original file is preceded by "---" and the new file is preceded by "+++". Following this is one change hunk that contain the line differences in the file. Addition lines are preceded by a plus sign, and deletion lines are preceded by a minus sign.
A hunk begins with range information and is immediately followed with the line additions, line deletions. The range information is surrounded by double at signs, and combines onto a single line what appears on two lines in the context format (above). The format of the range information line is as follows:
@@ -l,s +l,s @@ optional section heading
The hunk range information contains two hunk ranges. The range for the hunk of the original file is preceded by a minus symbol, and the range for the new file is preceded by a plus symbol. Each hunk range is of the format l,s where l is the starting line number and s is the number of lines the change hunk applies to for each respective file. In many versions of GNU diff, each range can omit the comma and trailing value s, in which case s defaults to 1. Note that the only really interesting value is the l line number of the first range; all the other values can be computed from the diff.
The hunk range for the original should be the sum of deletion (including changed) hunk lines. The hunk range for the new file should be a sum of addition (including changed) hunk lines. If hunk size information does not correspond with the number of lines in the hunk, then the diff could be considered invalid and be rejected.
If a line is modified, it is represented as a deletion and addition. Example:
-check this dokument. On
+check this document. On

Example:
--- a/path/to/original
+++ b/path/to/new
@@ -8,13 +14,8 @@
-This paragraph contains
-text that is outdated.
-It will be deleted in the
-near future.
-
 It is important to spell
-check this dokument. On
+check this document. On


A hunk should always contain some modifications.
Always include a new line in the end of the patch.
There can be only one hunk for a single file in a patch.
Minimize number of lines that are unchanged in a hunk.
Within hunk, you cannot ignore lines that are not changing.
Focus on producing smaller focused hunks.
To produce smaller hunks, you can split changes in multiple commits.
Do not use context lines in the hunk.

This will be applied using the `git apply --recount --unidiff-zero` command.
""",
        )
        commit_message: str = Field(
            ...,
            description="""
The commit message should be describing the patch and the reason behind the patch.
The patch should have any changes that is not described in the commit message.
""",
        )

    class Response(ResponseEvent):
        cancellation_reason: Optional[str] = Field(
            None, description="Operation cancelled by user"
        )
        error: Optional[str] = Field(
            None,
            description="Error while applying patch.",
        )

    def __init__(self, project_root_path: str):
        self.project_root_path = project_root_path
        self.repo = Repo(path=self.project_root_path, search_parent_directories=False)

    def run(
        self,
        request: Commit.Request,
    ) -> Generator[Event, Any, ResponseEvent]:
        fp = tempfile.NamedTemporaryFile(mode="w", delete=False)
        try:
            interaction_response = yield CommitConfirmation(**model_dump(request))
            if isinstance(interaction_response, Commit.Response):
                return interaction_response
            fp.write(request.patch)
            fp.close()
            self.repo.git.apply(["--recount", "--unidiff-zero", fp.name], index=True)
            self.repo.index.commit(message=request.commit_message)
            yield Message(
                message=f"[bold green]Success:[/] Changes committed with the message: '{request.commit_message}'"
            )
            return Commit.Response()
        except Exception as ex:
            logger.exception("")
            yield Message(
                message="[red]Alert:[/] Commit failed. Attempting to retry..."
            )
            return Commit.Response(error=str(ex))
        finally:
            if os.path.exists(fp.name):
                os.remove(fp.name)
