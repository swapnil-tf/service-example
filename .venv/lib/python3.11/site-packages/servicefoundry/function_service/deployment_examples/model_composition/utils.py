import numpy as np


def preprocess(image_url: str):
    print(f"preprocessing {image_url}")
    return np.random.uniform(0, 1, size=(1, 1, 1)).tolist()
