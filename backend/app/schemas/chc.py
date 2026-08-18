"""Pydantic schemas for CHC (request/response shapes).

Naming pattern used across YantraSetu:
  * <Model>Base   - fields shared by input and output
  * <Model>Create - what the client must send to create one
  * <Model>Update - partial update (every field optional)
  * <Model>Read   - what the API sends back (adds id; reads from ORM objects)
"""
from pydantic import BaseModel, ConfigDict, Field


class CHCBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120, description="Centre name")
    location: str = Field(..., min_length=1, max_length=255)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    operating_hours: str = Field("09:00-18:00", max_length=50, description="HH:MM-HH:MM")


class CHCCreate(CHCBase):
    """Payload to create a CHC."""


class CHCUpdate(BaseModel):
    """Partial update - only the fields you send are changed."""

    name: str | None = Field(None, min_length=1, max_length=120)
    location: str | None = Field(None, min_length=1, max_length=255)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    operating_hours: str | None = Field(None, max_length=50)


class CHCRead(CHCBase):
    """What the API returns for a CHC."""

    # from_attributes lets us build this straight from a SQLAlchemy ORM object.
    model_config = ConfigDict(from_attributes=True)

    id: int
