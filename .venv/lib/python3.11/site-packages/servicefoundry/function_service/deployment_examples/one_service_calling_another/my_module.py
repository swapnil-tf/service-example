import numpy as np

from servicefoundry.function_service import remote


def preprocess(image_url: str):
    return np.random.uniform(0, 1, [1, 1, 1]).tolist()


class Model:
    def __init__(self, path: str):
        self.path = path

    def predict(self, image_url: str):
        # preprocessed_data = preprocess(image_url=image_url)

        preprocessed_data = remote(preprocess)(image_url=image_url)

        print(f"running prediction on {image_url} using model from {self.path}")
        return {"class": "1"}
