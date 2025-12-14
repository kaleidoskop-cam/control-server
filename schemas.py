from enum import StrEnum
from typing import Union

from pydantic import BaseModel, confloat


class Direction(StrEnum):
    CLOCKWISE = "cw"
    COUNTERCLOCKWISE = "ccw"

class MotorSpeed(BaseModel):
    speed: confloat(ge=0, le=1)
    direction: Direction