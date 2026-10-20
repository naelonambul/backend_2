from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, Field


class PropertyCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    address: str = Field(min_length=1, max_length=300)
    price_krw: int = Field(ge=0)
    area_m2: float = Field(gt=0)
    room_count: int = Field(ge=0)
    description: str = Field(min_length=1, max_length=5000)
    image_url: AnyHttpUrl | None = None


class PropertyRead(BaseModel):
    idx: int
    title: str
    address: str
    price_krw: int
    area_m2: float
    room_count: int
    description: str
    image_url: str | None
    availability: Literal["available", "reserved", "sold"] = "available"

    model_config = {"from_attributes": True}
