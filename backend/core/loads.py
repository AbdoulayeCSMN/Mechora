"""Loads and supports. SI units (N, m, N/m)."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SupportType(str, Enum):
    SIMPLY_SUPPORTED = "simply_supported"
    CANTILEVER = "cantilever"


class PointLoad(BaseModel):
    """Concentrated downward load applied at `position` (m from left end).

    `magnitude` is the absolute force in Newtons; direction is downward.
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["point"] = "point"
    magnitude: float = Field(..., description="Downward force, N (> 0)")
    position: float = Field(..., description="Position from left end, m (>= 0)")

    @field_validator("magnitude")
    @classmethod
    def _positive_force(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("load magnitude must be > 0 N")
        return v

    @field_validator("position")
    @classmethod
    def _non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("position must be >= 0 m")
        return v


class DistributedLoad(BaseModel):
    """Uniformly distributed downward load between `start` and `end` (m)."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["distributed"] = "distributed"
    magnitude: float = Field(..., description="Line load intensity, N/m (> 0)")
    start: float = Field(..., description="Start position from left end, m")
    end: float = Field(..., description="End position from left end, m")

    @field_validator("magnitude")
    @classmethod
    def _positive_q(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("distributed load magnitude must be > 0 N/m")
        return v

    @field_validator("start", "end")
    @classmethod
    def _non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("position must be >= 0 m")
        return v

    @model_validator(mode="after")
    def _check_span(self) -> "DistributedLoad":
        if self.end <= self.start:
            raise ValueError("distributed load: end must be > start")
        return self


Load = Annotated[
    Union[PointLoad, DistributedLoad],
    Field(discriminator="kind"),
]
