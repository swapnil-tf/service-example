from typing import Any, Dict, Type

import pydantic

PYDANTIC_V2 = pydantic.VERSION.startswith("2.")


def model_dump(
    model: pydantic.BaseModel,
) -> Dict[str, Any]:
    if PYDANTIC_V2:
        return model.model_dump()
    return model.dict()


def model_json_schema(model: Type[pydantic.BaseModel]) -> Dict[str, Any]:
    if PYDANTIC_V2:
        return model.model_json_schema()
    return model.schema()
