"""Pydantic schemas (request/response shapes) for YantraSetu."""
from app.schemas.chc import CHCBase, CHCCreate, CHCRead, CHCUpdate
from app.schemas.farmer import FarmerBase, FarmerCreate, FarmerRead, FarmerUpdate
from app.schemas.field import FieldBase, FieldCreate, FieldRead, FieldUpdate
from app.schemas.machine import (
    MachineBase,
    MachineCreate,
    MachineRead,
    MachineUpdate,
)

__all__ = [
    "CHCBase", "CHCCreate", "CHCUpdate", "CHCRead",
    "MachineBase", "MachineCreate", "MachineUpdate", "MachineRead",
    "FarmerBase", "FarmerCreate", "FarmerUpdate", "FarmerRead",
    "FieldBase", "FieldCreate", "FieldUpdate", "FieldRead",
]
