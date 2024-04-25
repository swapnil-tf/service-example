from typing import Any, Dict, List, Optional

from langchain.chat_models.base import SimpleChatModel
from langchain.pydantic_v1 import Extra, Field, root_validator
from langchain.schema.messages import (
    AIMessage,
    BaseMessage,
    ChatMessage,
    HumanMessage,
    SystemMessage,
)

from servicefoundry.langchain.utils import (
    ModelParameters,
    requests_retry_session,
    validate_tfy_environment,
)
from servicefoundry.logger import logger


class TrueFoundryChat(SimpleChatModel):
    """`TrueFoundry LLM Gateway` chat models API.

    To use, you must have the environment variable ``TFY_API_KEY`` set with your API key and ``TFY_HOST`` set with your host or pass it as a named parameter to the constructor.
    """

    model: str = Field(description="The model to use for chat.")
    """The model to use for chat."""
    tfy_llm_gateway_url: Optional[str] = Field(default=None)
    """TrueFoundry LLM Gateway endpoint URL. Automatically inferred from env var `TFY_LLM_GATEWAY_URL` if not provided."""
    tfy_api_key: Optional[str] = Field(default=None)
    """TrueFoundry API Key. Automatically inferred from env var `TFY_API_KEY` if not provided."""
    model_parameters: Optional[dict] = Field(default_factory=dict)
    """Model parameters"""
    request_timeout: int = Field(default=30)
    """The timeout for the request in seconds."""
    max_retries: int = Field(default=5)
    """The number of retries for HTTP requests."""
    retry_backoff_factor: float = Field(default=0.3)
    """The backoff factor for exponential backoff during retries."""
    system_prompt: str = Field(default="You are a AI assistant")

    class Config:
        """Configuration for this pydantic object."""

        extra = Extra.forbid
        allow_population_by_field_name = True

    @root_validator()
    def validate_environment(cls, values: Dict) -> Dict:
        values = validate_tfy_environment(values)
        if not values["tfy_api_key"]:
            raise ValueError(
                f"Did not find `tfy_api_key`, please add an environment variable"
                f" `TFY_API_KEY` which contains it, or pass"
                f"  `tfy_api_key` as a named parameter."
            )
        if not values["tfy_llm_gateway_url"]:
            raise ValueError(
                f"Did not find `tfy_llm_gateway_url`, please add an environment variable"
                f" `TFY_LLM_GATEWAY_URL` which contains it, or pass"
                f"  `tfy_llm_gateway_url` as a named parameter."
            )
        return values

    @property
    def _llm_type(self) -> str:
        """Return type of chat model."""
        return "truefoundry-chat"

    def _call(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> str:

        if len(messages) == 0:
            raise ValueError("No messages provided to chat.")

        if not isinstance(messages[0], SystemMessage):
            messages.insert(0, SystemMessage(content=self.system_prompt))

        message_dicts = [
            TrueFoundryChat._convert_message_to_dict(message) for message in messages
        ]

        payload = {**self.model_parameters} if self.model_parameters else {}

        if stop:
            payload["stop_sequences"] = stop

        payload["messages"] = message_dicts
        payload["model"] = self.model

        session = requests_retry_session(
            retries=self.max_retries, backoff_factor=self.retry_backoff_factor
        )

        url = f"{self.tfy_llm_gateway_url}/openai/chat/completions"
        logger.debug(f"Chat using - model: {self.model} at endpoint: {url}")
        response = session.post(
            url=url,
            json=payload,
            headers={
                "Authorization": f"Bearer {self.tfy_api_key}",
            },
            timeout=self.request_timeout,
        )
        response.raise_for_status()
        output = response.json()
        return output["choices"][0]["message"]["content"]

    @staticmethod
    def _convert_message_to_dict(message: BaseMessage) -> dict:
        if isinstance(message, ChatMessage):
            message_dict = {"role": message.role, "content": message.content}
        elif isinstance(message, HumanMessage):
            message_dict = {"role": "user", "content": message.content}
        elif isinstance(message, AIMessage):
            message_dict = {"role": "assistant", "content": message.content}
        elif isinstance(message, SystemMessage):
            message_dict = {"role": "system", "content": message.content}
        else:
            raise ValueError(f"Got unknown message type: {message}")
        if message.additional_kwargs:
            logger.debug(
                "Additional message arguments are unsupported by TrueFoundry LLM Gateway "
                " and will be ignored: %s",
                message.additional_kwargs,
            )
        return message_dict
