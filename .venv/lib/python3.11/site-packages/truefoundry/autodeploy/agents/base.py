from __future__ import annotations

import json
from typing import ClassVar, Iterable, List, Protocol, Type, runtime_checkable

from openai import OpenAI
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_system_message_param import (
    ChatCompletionSystemMessageParam,
)
from openai.types.chat.chat_completion_tool_message_param import (
    ChatCompletionToolMessageParam,
)
from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam
from openai.types.chat.chat_completion_user_message_param import (
    ChatCompletionUserMessageParam,
)
from openai.types.shared_params.function_definition import FunctionDefinition
from pydantic import BaseModel, ValidationError

from truefoundry.autodeploy.constants import AUTODEPLOY_MODEL_NAME
from truefoundry.autodeploy.logger import logger
from truefoundry.autodeploy.tools import Event, RequestEvent, Tool
from truefoundry.autodeploy.utils.pydantic_compat import model_dump, model_json_schema


def llm(
    openai_client: OpenAI,
    messages: List[ChatCompletionMessageParam],
    tools: List[ChatCompletionToolParam],
    model: str,
    max_tokens: int = 4096,
) -> ChatCompletionMessage:
    completion = openai_client.chat.completions.create(
        tools=tools,
        stream=False,
        messages=messages,
        model=model,
        max_tokens=max_tokens,
        temperature=1,
        top_p=0.01,
        n=1,
        frequency_penalty=0.01,
    )
    return completion.choices[0].message


def format_tool_response(
    response: BaseModel, tool_call_id: str
) -> ChatCompletionToolMessageParam:
    return ChatCompletionToolMessageParam(
        role="tool",
        content=json.dumps(model_dump(response), indent=1),
        tool_call_id=tool_call_id,
    )


def format_user_response(response: str) -> ChatCompletionUserMessageParam:
    return ChatCompletionUserMessageParam(
        role="user",
        content=response,
    )


def get_tool_descriptions(
    tools: List, response: Type[BaseModel]
) -> List[ChatCompletionToolParam]:
    descriptions = []
    for tool in tools:
        tool = ChatCompletionToolParam(
            type="function",
            function=FunctionDefinition(
                name=tool.__class__.__name__,
                description=tool.description.strip(),
                parameters=model_json_schema(tool.Request),
            ),
        )
        descriptions.append(tool)

    if response:
        tool = ChatCompletionToolParam(
            type="function",
            function=FunctionDefinition(
                name="Response",
                parameters=model_json_schema(response),
            ),
        )
        descriptions.append(tool)

    return descriptions


class ToolParamParseError(BaseModel):
    error: str


@runtime_checkable
class Agent(Tool, Protocol):
    system_prompt: ClassVar[str]
    tools: List[Tool]
    max_iter: ClassVar[int] = 30
    openai_client: OpenAI
    model: str = AUTODEPLOY_MODEL_NAME

    def run(self, request: RequestEvent) -> Iterable[Event]:  # noqa: C901
        messages: List[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(
                role="system",
                content=self.system_prompt + "\nrequest:\n" + request.json(),
            ),
        ]
        tool_descriptions = get_tool_descriptions(self.tools, self.Response)
        tool_map = {}
        for tool in self.tools:
            tool_map[tool.__class__.__name__] = tool
        for _ in range(self.max_iter):
            r = llm(
                messages=messages,
                tools=tool_descriptions,
                openai_client=self.openai_client,
                model=self.model,
            )
            messages.append(r)
            if r.content:
                logger.debug(r.content)
            if not r.tool_calls:
                messages.append(
                    format_user_response(
                        "You must respond with a tool call. Use the Ask tool to ask user."
                    )
                )
                continue

            for tool_call in r.tool_calls:
                if tool_call.function.name == "Response":
                    try:
                        response = self.Response(
                            **json.loads(tool_call.function.arguments)
                        )
                    except (json.decoder.JSONDecodeError, ValidationError) as ex:
                        logger.debug(f"{tool_call.function.arguments}, {ex}")
                        messages.append(
                            format_tool_response(
                                ToolParamParseError(error=str(ex)), tool_call.id
                            )
                        )
                        continue
                    logger.debug(response)
                    yield response
                    return response
                tool = tool_map[tool_call.function.name]
                try:
                    request = tool.Request(**json.loads(tool_call.function.arguments))
                except (json.decoder.JSONDecodeError, ValidationError) as ex:
                    logger.debug(f"{tool_call.function.arguments}, {ex}")
                    messages.append(
                        format_tool_response(
                            ToolParamParseError(error=str(ex)), tool_call.id
                        )
                    )
                    continue
                logger.debug(f"{self.__class__.__name__}, {tool_call.function.name}")
                logger.debug(request)
                yield request
                tool_run = tool.run(request)
                response = None
                inp = None
                while True:
                    try:
                        event = tool_run.send(inp)
                        inp = yield event
                    except StopIteration as ex:
                        response = ex.value
                        break
                logger.debug(response)
                logger.debug(f"{self.__class__.__name__}, {tool_call.function.name}")
                messages.append(format_tool_response(response, tool_call.id))
                if not isinstance(tool, Agent):
                    yield response
        raise Exception()
