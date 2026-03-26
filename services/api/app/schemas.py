from datetime import datetime
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
