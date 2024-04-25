import time

from model import Model
from model_composition import ModelComposition
from utils import preprocess

from servicefoundry.function_service import BuildConfig, FunctionService, remote

MODEL_PATHS = {
    "model_1_path": "foo",
    "model_2_path": "bar",
    "model_3_path": "baz",
}

preprocess_service = FunctionService(
    name="preprocess-service",
    build_config=BuildConfig(pip_packages=["numpy<1.22.0"]),
    port=7000,
)
preprocess_service.register_function(preprocess)

model_service = FunctionService(name="model-service", port=7001)
model_service.register_class(
    Model, init_kwargs={"model_path": MODEL_PATHS["model_1_path"]}, name="model_1"
)
model_service.register_class(
    Model,
    init_kwargs={"model_path": MODEL_PATHS["model_2_path"]},
    name="model_2",
)
model_service.register_class(
    Model,
    init_kwargs={"model_path": MODEL_PATHS["model_2_path"]},
    name="model_3",
)

print(preprocess_service)
print(model_service)

preprocess_service.run()
model_service.run()
time.sleep(5)

composed_model = remote(
    ModelComposition,
    init_kwargs=MODEL_PATHS,
)
print(composed_model.predict(image_url="foo"))
time.sleep(3)


composed_model_service = FunctionService(name="composed-model-service", port=7002)
composed_model_service.register_class(ModelComposition, init_kwargs=MODEL_PATHS)
print(composed_model_service)
composed_model_service.run().join()
time.sleep(1)

# 1. Multiple classes, each class can have its own route prefix.
# 2. module vs filepath. Can I import a path directly as a module. This is relative to source.
# 3. What is the FQN for a normal function and a method. which I can deterministically generate at run time.
# 4. What if someone uses the same class and want to init it with two diff model path.
