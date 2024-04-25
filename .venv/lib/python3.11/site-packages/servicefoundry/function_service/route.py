import inspect
import json
from typing import Any, Callable, Dict, List

from servicefoundry.function_service.remote import RemoteClass
from servicefoundry.function_service.utils import (
    create_pydantic_model_from_function_signature,
    get_qual_name,
)
from servicefoundry.logger import logger
from servicefoundry.pydantic_v1 import BaseModel, Field, constr, validator


def validate_we_can_create_pydantic_model_of_func_args(func: Callable):
    qual_name = get_qual_name(func)
    try:
        create_pydantic_model_from_function_signature(func, get_qual_name(func))
    except Exception as ex:
        raise Exception(
            f"Unable to create a route for {qual_name!r}.\n"
            "Please ensure that in the function type signature, you have only used in-built\n"
            "types like `int`, `float`, `str`, `bool`, `typing.Dict`, `typing.List`, typing.Optional`.\n"
            "To temporarily resolve this error, you can remove the unsupported type signatures.\n"
        ) from ex


def path_pre_processor(path: str, prefix: str = "") -> str:
    path = path.strip("/")

    if not path:
        raise ValueError("path cannot be empty")

    prefix = prefix.strip("/")
    if not prefix:
        return f"/{path}"

    return f"/{prefix}/{path}"


class Route(BaseModel):
    function_name: str
    http_method: str
    path: constr(regex=r"^[A-Za-z0-9\-_/]+$")

    qual_name: str


class FunctionRoute(Route):
    module: str

    @classmethod
    def from_func(cls, func: Callable, path: str):
        validate_we_can_create_pydantic_model_of_func_args(func)
        return cls(
            function_name=func.__name__,
            http_method="POST",
            path=path_pre_processor(path or func.__name__),
            qual_name=get_qual_name(func),
            module=func.__module__,
        )


class ClassRoute(BaseModel):
    class_name: str
    init_kwargs: Dict[str, Any] = Field(default_factory=dict)
    module: str

    routes: List[Route] = Field(default_factory=list)

    @validator("init_kwargs")
    def init_kwargs_is_json_serializable(cls, v, values):
        try:
            json.dumps(v)
        except Exception as ex:
            class_name = values.get("class_name")
            raise ValueError(
                f"init_kwargs {v!r} of class {class_name!r} is not JSON serializable"
            ) from ex

        return v

    @classmethod
    def from_class(cls, remote_class: RemoteClass):
        routes = []
        methods = inspect.getmembers(remote_class.class_, predicate=inspect.isfunction)

        for method_name, method in methods:
            if method_name.startswith("_"):
                continue
            validate_we_can_create_pydantic_model_of_func_args(method)
            route = Route(
                function_name=method_name,
                http_method="POST",
                path=path_pre_processor(prefix=remote_class.name, path=method_name),
                qual_name=remote_class.get_qual_name(method),
            )
            routes.append(route)

        return cls(
            class_name=remote_class.class_.__name__,
            init_kwargs=remote_class.init_kwargs,
            routes=routes,
            module=remote_class.class_.__module__,
        )


class RouteGroups(BaseModel):
    functions: List[FunctionRoute] = Field(default_factory=list)
    classes: Dict[str, ClassRoute] = Field(default_factory=dict)

    def register_function(self, func, path):
        function_route = FunctionRoute.from_func(func=func, path=path)
        logger.info(
            "Function %r from module %r will be deployed on path '%s %s'.",
            function_route.function_name,
            function_route.module,
            function_route.http_method,
            function_route.path,
        )
        self.functions.append(function_route)

    def register_class(self, remote_class: RemoteClass):
        if remote_class.name in self.classes:
            raise ValueError(
                f"name {remote_class.name!r} is already used to register a class"
            )
        class_route = ClassRoute.from_class(remote_class)
        for route in class_route.routes:
            logger.info(
                "Method %r from `%s:%s` will be deployed on path '%s %s'.",
                route.function_name,
                class_route.class_name,
                remote_class.name,
                route.http_method,
                route.path,
            )
        self.classes[remote_class.name] = class_route
