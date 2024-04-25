from my_module import Model, preprocess

from servicefoundry.function_service import FunctionService

preprocess_service = FunctionService("preprocess", port=4000)
preprocess_service.register_function(preprocess)

model_service = FunctionService("model-service", port=4001)
model_service.register_class(Model, init_kwargs={"path": "foo"}, name="model")

preprocess_service.run()
model_service.run().join()
