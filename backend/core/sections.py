"""Cross-section geometries and properties. All values in SI (m, m^2, m^4)."""

from __future__ import annotations

import math
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class _SectionBase(BaseModel):
    model_config = ConfigDict(frozen=True)

    @property
    def area(self) -> float:  # pragma: no cover - abstract
        raise NotImplementedError

    @property
    def inertia(self) -> float:  # pragma: no cover - abstract
        raise NotImplementedError

    @property
    def extreme_fiber(self) -> float:  # pragma: no cover - abstract
        raise NotImplementedError

    @property
    def section_modulus(self) -> float:
        return self.inertia / self.extreme_fiber


class RectangularSection(_SectionBase):
    kind: Literal["rectangle"] = "rectangle"
    width: float = Field(..., description="b, in m")
    height: float = Field(..., description="h, in m")

    @field_validator("width", "height")
    @classmethod
    def _positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("dimension must be > 0 (m)")
        return v

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def inertia(self) -> float:
        return self.width * self.height ** 3 / 12.0

    @property
    def extreme_fiber(self) -> float:
        return self.height / 2.0


class CircularSection(_SectionBase):
    kind: Literal["circle"] = "circle"
    diameter: float = Field(..., description="d, in m")

    @field_validator("diameter")
    @classmethod
    def _positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("diameter must be > 0 (m)")
        return v

    @property
    def area(self) -> float:
        return math.pi * self.diameter ** 2 / 4.0

    @property
    def inertia(self) -> float:
        return math.pi * self.diameter ** 4 / 64.0

    @property
    def extreme_fiber(self) -> float:
        return self.diameter / 2.0


class TubeSection(_SectionBase):
    kind: Literal["tube"] = "tube"
    outer_diameter: float = Field(..., description="D, in m")
    inner_diameter: float = Field(..., description="d, in m")

    @field_validator("outer_diameter", "inner_diameter")
    @classmethod
    def _positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("diameter must be > 0 (m)")
        return v

    @model_validator(mode="after")
    def _check_order(self) -> "TubeSection":
        if self.inner_diameter >= self.outer_diameter:
            raise ValueError("inner_diameter must be < outer_diameter")
        return self

    @property
    def area(self) -> float:
        return math.pi * (self.outer_diameter ** 2 - self.inner_diameter ** 2) / 4.0

    @property
    def inertia(self) -> float:
        return math.pi * (self.outer_diameter ** 4 - self.inner_diameter ** 4) / 64.0

    @property
    def extreme_fiber(self) -> float:
        return self.outer_diameter / 2.0


# Discriminated union for (de)serialization at the API boundary later on.
# CatalogProfile is imported from profiles.py and shares the same informal
# interface (area / inertia / extreme_fiber / section_modulus), so the Beam
# engine can consume any of these section variants transparently.
from .profiles import CatalogProfile  # noqa: E402  (defined below to keep file order readable)

Section = Annotated[
    Union[RectangularSection, CircularSection, TubeSection, CatalogProfile],
    Field(discriminator="kind"),
]
