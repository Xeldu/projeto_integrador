from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Numeric, DateTime
from .database import Base


class Reading(Base):
    __tablename__ = "readings"

    id          = Column(Integer, primary_key=True, index=True)
    device_id   = Column(String(64), nullable=False)
    temperature = Column(Numeric(6, 2), nullable=False)
    timestamp   = Column(DateTime(timezone=True), nullable=False,
                         default=lambda: datetime.now(timezone.utc))
