import enum
import warnings
from typing import Any, Dict, List, Mapping, Optional
from urllib.parse import urljoin

import requests
from requests.auth import HTTPBasicAuth

from servicefoundry.lib.auth.servicefoundry_session import ServiceFoundrySession
from servicefoundry.pydantic_v1 import root_validator

try:
    from langchain.callbacks.manager import CallbackManagerForLLMRun
    from langchain.llms.base import LLM
    from langchain.llms.utils import enforce_stop_tokens
except Exception as ex:
    raise Exception(
        "Failed to import langchain."
        " Please install langchain by using `pip install langchain` command"
    ) from ex


class _ModelServerImpl(str, enum.Enum):
    MLSERVER = "MLSERVER"
    TGI = "TGI"
    VLLM = "VLLM"


def _get_model_server_and_validate_if_mlserver(endpoint_url, auth, model_name=None):
    try:
        response = requests.get(urljoin(endpoint_url, "info"), json={}, auth=auth)
        if response.status_code == 200:
            return _ModelServerImpl.TGI, None
        elif response.status_code == 404:
            # We are not using TGI, try for mlserver
            response = requests.post(
                urljoin(endpoint_url, "v2/repository/index"), json={}, auth=auth
            )
            if response.status_code == 200:
                models = response.json()
                if len(models) == 0:
                    raise ValueError("No model is deployed in the model server")
                model_names = [m.get("name") for m in models]
                if model_name and model_name not in model_names:
                    raise ValueError(
                        f"Model {model_name!r} is not available in the model server. "
                        f"Available models {model_names!r}"
                    )
                if not model_name and len(model_names) > 1:
                    raise ValueError(
                        f"Please pass `model_name` while instantiating `TruefoundryLLM`. "
                        f"Available models are {model_names!r} "
                    )
                if model_name:
                    return _ModelServerImpl.MLSERVER, model_name
                return _ModelServerImpl.MLSERVER, model_names[0]
            if response.status_code == 404:
                return _ModelServerImpl.VLLM, None
        response.raise_for_status()
    except Exception as e:
        raise Exception(f"Error raised by inference API: {e}") from e


# TODO (chiragjn): Refactor this into separate implementations for each model server


class TruefoundryLLM(LLM):
    """Wrapper around TFY model deployment.
    To use this class, you need to have the langchain library installed.
    Example:
        .. code-block:: python
            from servicefoundry.langchain import TruefoundryLLM
            endpoint_url = (
                "https://pythia-70m-model-model-catalogue.demo2.truefoundry.tech"
            )
            model = TruefoundryLLM(
                endpoint_url=endpoint_url,
                parameters={
                    "max_new_tokens": 100,
                    "temperature": 0.7,
                    "top_k": 5,
                    "top_p": 0.9
                }
            )
    """

    endpoint_url: str
    model_name: Optional[str] = None
    auth: Optional[HTTPBasicAuth] = None
    parameters: Optional[Dict[str, Any]] = None
    model_server_impl: Optional[_ModelServerImpl] = None

    @root_validator(pre=False)
    def validate_model_server_and_name(cls, values: Dict):
        warnings.warn(
            message=f"{cls.__name__} is deprecated and will be removed soon. Please use `TrueFoundryLLM` or `TrueFoundryChat` to invoke models using the new TrueFoundry LLM Gateway",
            category=DeprecationWarning,
            stacklevel=2,
        )
        endpoint_url = values["endpoint_url"]
        model_name = values.get("model_name")
        auth = values.get("auth")
        model_server_impl, model_name = _get_model_server_and_validate_if_mlserver(
            endpoint_url=endpoint_url, model_name=model_name, auth=auth
        )
        values["model_server_impl"] = model_server_impl
        if model_server_impl == _ModelServerImpl.MLSERVER:
            values["model_name"] = model_name
        return values

    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        """Get the identifying parameters."""
        return {
            "endpoint_url": self.endpoint_url,
            "model_name": self.model_name,
        }

    @property
    def _llm_type(self) -> str:
        """Return type of llm."""
        return "tfy_model_deployment"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **params: Any,
    ) -> str:
        """Call out to the deployed model
        Args:
            prompt: The prompt to pass into the model.
            stop: Optional list of stop words to use when generating.
        Returns:
            The string generated by the model.
        Example:
            .. code-block:: python
                response = model("Tell me a joke.")
        """
        _params_already_set = self.parameters or {}
        params = {**_params_already_set, **params, "return_full_text": False}

        if self.model_server_impl == _ModelServerImpl.MLSERVER:
            generate_path = f"v2/models/{self.model_name}/infer/simple"
            payload = {"inputs": prompt, "parameters": params}
        elif self.model_server_impl == _ModelServerImpl.TGI:
            generate_path = "generate"
            payload = {"inputs": prompt, "parameters": params}
        elif self.model_server_impl == _ModelServerImpl.VLLM:
            generate_path = "generate"
            payload = {**params, "prompt": prompt}
        else:
            raise ValueError(f"No known generate path for {self.model_server_impl}")
        url = urljoin(self.endpoint_url, generate_path)

        try:
            response = requests.post(url, json=payload, auth=self.auth)
            response.raise_for_status()
        except Exception as e:
            raise Exception(f"Error raised by inference API: {e}") from e
        response_dict = response.json()
        if "error" in response_dict:
            raise ValueError(
                f"Error raised by inference API: {response_dict['error']!r}"
            )

        if self.model_server_impl == _ModelServerImpl.MLSERVER:
            inference_result = response_dict[0]
        elif self.model_server_impl == _ModelServerImpl.TGI:
            inference_result = response_dict
        elif self.model_server_impl == _ModelServerImpl.VLLM:
            inference_result = response_dict
        else:
            raise ValueError(
                f"Unknown model server {self.model_server_impl}, cannot parse response"
            )

        if "generated_text" in inference_result:
            text = inference_result["generated_text"]
        elif "summarization" in inference_result:
            text = inference_result["summary_text"]
        elif "text" in inference_result:
            text = inference_result["text"]
        else:
            raise ValueError(f"Could not parse inference response: {response_dict!r}")

        if isinstance(text, list):
            text = text[0]

        if stop:
            text = enforce_stop_tokens(text, stop)

        return text


class TruefoundryPlaygroundLLM(LLM):
    """Wrapper around TFY Playground.
    To use this class, you need to have the langchain library installed.
    Example:
        .. code-block:: python
            from servicefoundry.langchain import TruefoundryPlaygroundLLM
            import os
            # Note: Login using servicefoundry login --host <https://example-domain.com>
            model = TruefoundryPlaygroundLLM(
                model_name="vicuna-13b",
                parameters={
                    "maximumLength": 100,
                    "temperature": 0.7,
                    "topP": 0.9,
                    "repetitionPenalty": 1
                }
            )
            response = model.predict("Enter the prompt here")
    """

    model_name: str
    parameters: Optional[Dict[str, Any]] = None
    provider: str = "truefoundry-public"

    @root_validator(pre=False)
    def validate_model_server_and_name(cls, values: Dict):
        warnings.warn(
            message=f"{cls.__name__} is deprecated and will be removed soon. Please use `TrueFoundryLLM` or `TrueFoundryChat` to invoke models using the new TrueFoundry LLM Gateway",
            category=DeprecationWarning,
            stacklevel=2,
        )
        return values

    @property
    def _get_model(self) -> str:
        """returns the model name"""
        return self.model_name

    @property
    def _get_provider(self) -> str:
        """Returns the provider name"""
        return self.provider

    @property
    def _llm_type(self) -> str:
        """Return type of llm."""
        return "tfy_playground"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        **params: Any,
    ) -> str:
        """Call out to the deployed model
        Args:
            prompt: The prompt to pass into the model.
            stop: Optional list of stop words to use when generating.
        Returns:
            The string generated by the model.
        Example:
            .. code-block:: python
                response = model("I have a joke for you...")
        """
        _params_already_set = self.parameters or {}
        params = {**_params_already_set, **params}
        if stop:
            params["stopSequences"] = stop
        session = ServiceFoundrySession()

        if not session:
            raise Exception(
                f"Unauthenticated: Please login using servicefoundry login --host <https://example-domain.com>"
            )

        host = session.base_url

        if host[-1] == "/":
            host = host[: len(host) - 1]

        url = f"{host}/llm-playground/api/inference/text"
        headers = {"Authorization": f"Bearer {session.access_token}"}

        json = {
            "prompt": prompt,
            "models": [
                {
                    "name": self.model_name,
                    "provider": self.provider,
                    "tag": self.model_name,
                    "parameters": params,
                }
            ],
        }

        try:
            response = requests.post(url=url, headers=headers, json=json)
            response.raise_for_status()
        except Exception as ex:
            raise Exception(f"Error inferencing the model: {ex}") from ex

        data = response.json()
        text = data[0].get("text")
        if stop:
            text = enforce_stop_tokens(text, stop)
        return text
