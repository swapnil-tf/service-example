from __future__ import annotations

import abc
import json
from typing import TYPE_CHECKING

import requests

from servicefoundry.function_service.remote.context import QUAL_NAME_TO_URL_MAP

if TYPE_CHECKING:
    from servicefoundry.function_service.remote.remote import Remote


class Method(abc.ABC):
    def __call__(self, *args, **kwargs):
        if len(args) > 0:
            raise Exception(
                "Positional arguments are not supported now.\n"
                "Please use keyword arguments"
            )
        return self.run(**kwargs)

    @abc.abstractmethod
    def run(self, **kwargs):
        ...

    @abc.abstractmethod
    async def run_async(self, **kwargs):
        ...


class LocalMethod(Method):
    def __init__(self, remote_object: Remote, method):
        self._remote_object = remote_object
        self._method_name = method.__name__

    def run(self, **kwargs):
        return getattr(self._remote_object.instance, self._method_name)(**kwargs)

    async def run_async(self, **kwargs):
        raise NotImplementedError()


class RemoteMethod(Method):
    def __init__(self, remote_object: Remote, method):
        self._remote_object = remote_object
        self._method_name = method.__name__
        self._qual_name = self._remote_object.get_qual_name(method)

    def check(self) -> bool:
        return self._qual_name in QUAL_NAME_TO_URL_MAP

    def run(self, **kwargs):
        url = QUAL_NAME_TO_URL_MAP.get(self._qual_name)
        r = requests.post(url, json=kwargs)
        assert r.status_code == 200, r.text
        return json.loads(r.text)

    async def run_async(self, **kwargs):
        raise NotImplementedError()


def method_factory(*args, **kwargs) -> Method:
    remote_method = RemoteMethod(*args, **kwargs)
    if remote_method.check():
        return remote_method

    return LocalMethod(*args, **kwargs)
