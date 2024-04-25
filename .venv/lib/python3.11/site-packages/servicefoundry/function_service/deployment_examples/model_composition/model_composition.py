from typing import Dict

from model import Model
from utils import preprocess

from servicefoundry.function_service import remote


class ModelComposition:
    def __init__(self, model_1_path: str, model_2_path: str, model_3_path: str):
        # self.model_1 = Model(model_path="foo")
        # self.model_2 = Model(model_path="bar")
        # self.model_3 = Model(model_path="baz")
        self.model_1 = remote(
            Model, init_kwargs={"model_path": model_1_path}, name="model_1"
        )
        self.model_2 = remote(
            Model, init_kwargs={"model_path": model_2_path}, name="model_2"
        )
        self.model_3 = remote(
            Model, init_kwargs={"model_path": model_3_path}, name="model_3"
        )

    def predict(self, image_url: str) -> Dict:
        # preprocessed_data = preprocess(image_url)
        preprocessed_data = remote(preprocess)(image_url=image_url)

        model_1_prediction = self.model_1.predict(preprocessed_data=preprocessed_data)
        model_2_prediction = self.model_2.predict(preprocessed_data=preprocessed_data)
        model_3_prediction = self.model_3.predict(preprocessed_data=preprocessed_data)

        return dict(
            model_1_prediction=model_1_prediction,
            model_2_prediction=model_2_prediction,
            model_3_prediction=model_3_prediction,
        )


if __name__ == "__main__":

    model = ModelComposition(model_1_path="foo", model_2_path="bar", model_3_path="baz")
    print(model.predict(image_url="hello"))
