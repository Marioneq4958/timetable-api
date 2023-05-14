from typing import TypeVar, Optional, Generic, Any

from pydantic.generics import GenericModel

Data = TypeVar("Data")


class APIResponse(GenericModel, Generic[Data]):
    data: Optional[Data] = None
    message: Optional[str] = None
    detail: Optional[Any] = None
