import abc
import inspect
from typing import Dict, Optional

from servicefoundry.function_service.remote.method import method_factory
from servicefoundry.function_service.utils import get_qual_name


class Remote(abc.ABC):
    @property
    @abc.abstractmethod
    def instance(self):
        ...

    @abc.abstractmethod
    def get_qual_name(self, method) -> str:
        ...


class RemoteFunction(Remote):
    def __init__(self, func, **kwargs):
        self._func = func
        self._instance = inspect.getmodule(self._func)
        self.method = method_factory(remote_object=self, method=self._func)

    def __call__(self, *args, **kwargs):
        if len(args) > 0:
            raise Exception(
                "Positional arguments are not supported now.\n"
                "Please use keyword arguments"
            )
        return self.method.__call__(**kwargs)

    def run(self, **kwargs):
        return self.method.run(**kwargs)

    async def run_async(self, **kwargs):
        return await self.method.run_async(**kwargs)

    @property
    def instance(self):
        return self._instance

    def get_qual_name(self, method) -> str:
        return get_qual_name(method)


class RemoteClass(Remote):
    def __init__(
        self,
        class_,
        *,
        init_kwargs: Optional[Dict] = None,
        name: Optional[str] = None,
        **kwargs,
    ):
        self._class = class_
        self._name = name or class_.__name__
        self._init_kwargs = init_kwargs or {}

        self._instance = None

        ###############
        # Maybe this is not the right way to model it.
        # Another approach can be, identify whether the environment is local
        # or our service. If local, then we can just return the instance of
        # the user defined class. Else, we return a class which reflects the
        # methods in the class, but internally doing network call.
        # But I am sticking with this now because not all the concepts of a python
        # class right now, will work in both remote and local. Examples, you cannot
        # access arbitary attributes, properties etc. I want to keep the behaviour
        # identical for now.
        absent = object()
        methods = inspect.getmembers(class_, predicate=inspect.isfunction)
        for method_name, method in methods:
            if method_name.startswith("_"):
                continue
            existing_attribute = getattr(self, method_name, absent)
            if existing_attribute is not absent:
                raise Exception(
                    f"Cannot reflect {method_name!r} of class {class_.__name__!r}.\n"
                    f"{method_name!r} is reserved. Use a different method name"
                )

            setattr(
                self,
                method_name,
                method_factory(remote_object=self, method=method),
            )
        ###############

    def get_qual_name(self, method) -> str:
        return f"{self.name}:{get_qual_name(method)}"

    @property
    def instance(self):
        if self._instance:
            return self._instance
        instance = self._class(**self._init_kwargs)
        self._instance = instance
        return self._instance

    @property
    def class_(self):
        return self._class

    @property
    def name(self) -> str:
        return self._name

    @property
    def init_kwargs(self) -> Dict:
        return self._init_kwargs


def remote(func_or_class, **kwargs):
    if inspect.isfunction(func_or_class):
        return RemoteFunction(func_or_class, **kwargs)
    if inspect.isclass(func_or_class):
        return RemoteClass(func_or_class, **kwargs)

    raise Exception()


if __name__ == "__main__":

    def foo(a, b):
        print(a, b)

    remote(foo)(a=1, b=2)

    class Foo:
        def __init__(self, a, b):
            self.a = a
            self.b = b

        def foo(self):
            print(self.a, self.b)

    foo_instance = remote(Foo, name="foo", init_kwargs={"a": 1, "b": 2})
    foo_instance_2 = remote(Foo, name="foo_2", init_kwargs={"a": 3, "b": 2})

    foo_instance.foo()
    foo_instance_2.foo()
    foo_instance.foo.run()
    # foo_instance.foo.async_run()
