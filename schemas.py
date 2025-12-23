from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field


class Motor(BaseModel):
    frequency: Annotated[int, Field(strict=True, gt=-2000, le=2000, default=200)]

class Light(BaseModel):
    brightness: Annotated[int, Field(strict=True, ge=0, le=100, default=10)]

class SystemVersionResponse(BaseModel):
    commit_hash: str