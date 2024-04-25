from typing import Dict, List

import numpy as np


class Model:
    def __init__(self, model_path: str):
        self.model_path = model_path

    def predict(self, preprocessed_data: List[List[List[int]]]) -> Dict:
        print(np.asarray(preprocessed_data))
        print(f"prediction running for model_path {self.model_path}")
        return {"prediction": "cat"}
