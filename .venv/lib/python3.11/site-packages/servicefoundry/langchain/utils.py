import os
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from langchain.pydantic_v1 import BaseModel
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from servicefoundry.lib.auth.servicefoundry_session import ServiceFoundrySession


class ModelParameters(BaseModel):
    temperature: Optional[float]
    maximum_length: Optional[int]
    top_p: Optional[float]
    top_k: Optional[int]
    repetition_penalty: Optional[float]
    frequency_penalty: Optional[float]
    presence_penalty: Optional[float]
    stop_sequences: Optional[List[str]]


def validate_tfy_environment(values: Dict):
    gateway_url = values["tfy_llm_gateway_url"] or os.getenv("TFY_LLM_GATEWAY_URL")
    api_key = values["tfy_api_key"] or os.getenv("TFY_API_KEY")

    if gateway_url and api_key:
        values["tfy_llm_gateway_url"] = gateway_url
        values["tfy_api_key"] = api_key
        return values

    sfy_session = ServiceFoundrySession()
    if not sfy_session:
        raise Exception(
            f"Unauthenticated: Please login using servicefoundry login --host <https://example-domain.com>"
        )

    if not gateway_url:
        gateway_url = urljoin(sfy_session.base_url, "/api/llm")

    if not api_key:
        api_key = sfy_session.access_token

    values["tfy_llm_gateway_url"] = gateway_url
    values["tfy_api_key"] = api_key
    return values


def requests_retry_session(
    retries=5,
    backoff_factor=0.3,
    status_forcelist=(500, 502, 503, 504),
    method_whitelist=frozenset({"GET", "POST"}),
    session=None,
):
    """
    Returns a `requests` session with retry capabilities for certain HTTP status codes.

    Args:
        retries (int): The number of retries for HTTP requests.
        backoff_factor (float): The backoff factor for exponential backoff during retries.
        status_forcelist (tuple): A tuple of HTTP status codes that should trigger a retry.
        method_whitelist (frozenset): The set of HTTP methods that should be retried.
        session (requests.Session, optional): An optional existing requests session to use.

    Returns:
        requests.Session: A session with retry capabilities.
    """
    # Implementation taken from https://www.peterbe.com/plog/best-practice-with-retries-with-requests
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        status=retries,
        backoff_factor=backoff_factor,
        allowed_methods=method_whitelist,
        status_forcelist=status_forcelist,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session
