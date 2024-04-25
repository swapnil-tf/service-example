import importlib
import os
from threading import Thread

import uvicorn
from fastapi import FastAPI

from servicefoundry.function_service.remote import QUAL_NAME_TO_URL_MAP
from servicefoundry.function_service.route import ClassRoute, FunctionRoute, RouteGroups
from servicefoundry.function_service.utils import (
    create_pydantic_model_from_function_signature,
)


def _encapsulate_user_function(function, input_model_name: str):
    model = create_pydantic_model_from_function_signature(
        func=function, model_name=input_model_name
    )

    def func(x: model):
        return function(**dict(x._iter(to_dict=False)))

    return func


def _add_function_route(app: FastAPI, function_route: FunctionRoute, port: int):
    module = importlib.import_module(function_route.module)
    function = getattr(module, function_route.function_name)

    app.add_api_route(
        path=function_route.path,
        endpoint=_encapsulate_user_function(
            function, input_model_name=function_route.qual_name
        ),
        methods=[function_route.http_method],
    )
    QUAL_NAME_TO_URL_MAP[
        function_route.qual_name
    ] = f"http://localhost:{port}{function_route.path}"


def _add_class_route(app: FastAPI, class_route: ClassRoute, port: int):
    module = importlib.import_module(class_route.module)
    class_factory = getattr(module, class_route.class_name)
    instance = class_factory(**class_route.init_kwargs)

    for route in class_route.routes:
        function = getattr(instance, route.function_name)
        app.add_api_route(
            path=route.path,
            endpoint=_encapsulate_user_function(function, route.qual_name),
            methods=[route.http_method],
        )

        QUAL_NAME_TO_URL_MAP[route.qual_name] = f"http://localhost:{port}{route.path}"


def build_app(route_groups: RouteGroups, port: int) -> FastAPI:
    _root_path = os.getenv("TFY_SERVICE_ROOT_PATH")
    app_kwargs = {"root_path": _root_path} if _root_path else {}
    app = FastAPI(docs_url="/", **app_kwargs)
    app.add_api_route(path="/ping", endpoint=lambda: "pong")

    for route in route_groups.functions:
        _add_function_route(app=app, function_route=route, port=port)

    for class_route in route_groups.classes.values():
        _add_class_route(app=app, class_route=class_route, port=port)

    # print(json.dumps(QUAL_NAME_TO_URL_MAP, indent=2))
    return app


def build_and_run_app(route_groups: RouteGroups, port: int):
    app = build_app(route_groups=route_groups, port=port)
    uvicorn.run(app, port=port, host="0.0.0.0")


def build_and_run_app_in_background_thread(
    route_groups: RouteGroups, port: int
) -> Thread:
    thread = Thread(
        target=build_and_run_app,
        kwargs=dict(route_groups=route_groups, port=port),
        daemon=True,
    )
    thread.start()
    return thread
