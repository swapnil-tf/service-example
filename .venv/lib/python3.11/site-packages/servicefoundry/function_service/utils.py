import inspect
from typing import Any

from servicefoundry.pydantic_v1 import BaseModel


def get_qual_name(obj):
    return f"{obj.__module__}.{obj.__qualname__}"


def create_pydantic_model_from_function_signature(func, model_name: str):
    # https://github.com/pydantic/pydantic/issues/1391
    (
        args,
        _,
        varkw,
        defaults,
        kwonlyargs,
        kwonlydefaults,
        annotations,
    ) = inspect.getfullargspec(func)
    defaults = defaults or []
    args = args or []
    if len(args) > 0 and args[0] == "self":
        del args[0]

    non_default_args = len(args) - len(defaults)
    defaults = [
        ...,
    ] * non_default_args + defaults

    keyword_only_params = {
        param: kwonlydefaults.get(param, Any) for param in kwonlyargs
    }
    params = {
        param: (annotations.get(param, Any), default)
        for param, default in zip(args, defaults)
    }

    class Config:
        extra = "allow"

    # Allow extra params if there is a **kwargs parameter in the function signature
    config = Config if varkw else None

    return pydantic.create_model(
        model_name,
        **params,
        **keyword_only_params,
        __base__=BaseModel,
        __config__=config,
    )
