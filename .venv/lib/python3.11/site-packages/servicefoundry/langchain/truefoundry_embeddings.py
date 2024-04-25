import concurrent.futures
import math
from typing import Dict, List, Optional

import tqdm
from langchain.embeddings.base import Embeddings
from langchain.pydantic_v1 import BaseModel, Extra, Field, root_validator

from servicefoundry.langchain.utils import (
    ModelParameters,
    requests_retry_session,
    validate_tfy_environment,
)
from servicefoundry.logger import logger

EMBEDDER_BATCH_SIZE = 32
PARALLEL_WORKERS = 4


class TrueFoundryEmbeddings(BaseModel, Embeddings):
    """`TrueFoundry LLM Gateway` embedding models API.

    To use, you must have the environment variable ``TFY_API_KEY`` set with your API key and ``TFY_HOST`` set with your host or pass it
    as a named parameter to the constructor.
    """

    model: str = Field(description="The model to use for embedding.")
    """The model to use for embedding."""
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
    batch_size: int = Field(default=EMBEDDER_BATCH_SIZE)
    """The batch size to use for embedding."""
    parallel_workers: int = Field(default=PARALLEL_WORKERS)
    """The number of parallel workers to use for embedding."""

    __private_attributes__ = {"_executor"}

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

    def _init_private_attributes(self):
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.parallel_workers
        )

    @property
    def _llm_type(self) -> str:
        """Return type of embedding model."""
        return "truefoundry-embeddings"

    def __del__(self):
        """
        Destructor method to clean up the executor when the object is deleted.

        Args:
            None

        Returns:
            None
        """
        self._executor.shutdown()

    def _remote_embed(self, texts, query_mode=False):
        """
        Perform remote embedding using a HTTP POST request to a designated endpoint.

        Args:
            texts (List[str]): A list of text strings to be embedded.
            query_mode (bool): A flag to indicate if running in query mode or in embed mode (indexing).
        Returns:
            List[List[float]]: A list of embedded representations of the input texts.
        """
        session = requests_retry_session(
            retries=self.max_retries, backoff_factor=self.retry_backoff_factor
        )

        payload = {
            "input": texts,
            "model": self.model,
        }

        url = f"{self.tfy_llm_gateway_url}/openai/embeddings"
        logger.debug(
            f"Embedding using - model: {self.model} at endpoint: {url}, for {len(texts)} texts"
        )
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
        return [data["embedding"] for data in output["data"]]

    def _embed(self, texts: List[str], query_mode: bool):
        """
        Perform embedding on a list of texts using remote embedding in chunks.

        Args:
            texts (List[str]): A list of text strings to be embedded.
            query_mode (bool): A flag to indicate if running in query mode or in embed mode (indexing).
        Returns:
            List[List[float]]: A list of embedded representations of the input texts.
        """
        embeddings = []

        def _feeder():
            for i in range(0, len(texts), self.batch_size):
                chunk = texts[i : i + self.batch_size]
                yield chunk

        embeddings = list(
            tqdm.tqdm(
                self._executor.map(self._remote_embed, _feeder()),
                total=int(math.ceil(len(texts) / self.batch_size)),
            )
        )
        return [item for batch in embeddings for item in batch]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of text documents.

        Args:
            texts (List[str]): A list of text documents to be embedded.

        Returns:
            List[List[float]]: A list of embedded representations of the input documents.
        """
        return self._embed(texts, query_mode=False)

    def embed_query(self, text: str) -> List[float]:
        """
        Embed a query text.

        Args:
            text (str): The query text to be embedded.

        Returns:
            List[float]: The embedded representation of the input query text.
        """
        return self._embed([text], query_mode=True)[0]
