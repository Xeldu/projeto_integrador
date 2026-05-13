from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


class ReadingIn(BaseModel):
    device_id:   str   = Field(..., min_length=1, max_length=64)
    temperature: float = Field(..., ge=-50, le=200)

class ReadingOut(BaseModel):
    id:          int
    device_id:   str
    temperature: float
    timestamp:   datetime
    model_config = {"from_attributes": True}


class ExtraField(BaseModel):
    name:  str
    value: str
    unit:  str = ""

class MachineIn(BaseModel):
    name:            str                    = Field(..., min_length=1, max_length=128)
    power_kw:        Optional[float]        = None
    voltage_v:       Optional[float]        = None
    current_a:       Optional[float]        = None
    resistance_ohm:  Optional[float]        = None
    notes:           Optional[str]          = None
    extra_fields:    Optional[list[ExtraField]] = None

class MachineOut(MachineIn):
    id:         int
    created_at: datetime
    model_config = {"from_attributes": True}


class TestStart(BaseModel):
    machine_id:        int = Field(..., gt=0)
    type:              str = Field(..., pattern="^(temperature|pressure)$")
    reference_channel: int = Field(1, ge=1, le=7)

class TestReadingIn(BaseModel):
    test_id:   int
    channel:   int   = Field(..., ge=1, le=7)
    value:     float
    unit:      str   = Field(default="°C", max_length=16)

class TestReadingOut(BaseModel):
    id:        int
    test_id:   int
    channel:   int
    value:     float
    unit:      str
    timestamp: datetime
    model_config = {"from_attributes": True}

class TestOut(BaseModel):
    id:                int
    machine_id:        int
    type:              str
    status:            str
    reference_channel: int
    started_at:        datetime
    finished_at:       Optional[datetime]
    machine:           MachineOut
    readings:          list[TestReadingOut] = []
    model_config = {"from_attributes": True}

class TestSummary(BaseModel):
    id:          int
    machine_id:  int
    type:        str
    status:      str
    started_at:  datetime
    finished_at: Optional[datetime]
    machine:     MachineOut
    model_config = {"from_attributes": True}
