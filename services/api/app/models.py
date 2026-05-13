from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, Enum, JSON
from sqlalchemy.orm import relationship
import enum
from .database import Base


class Reading(Base):
    __tablename__ = "readings"
    id          = Column(Integer, primary_key=True, index=True)
    device_id   = Column(String(64), nullable=False)
    temperature = Column(Numeric(6, 2), nullable=False)
    timestamp   = Column(DateTime(timezone=True), nullable=False,
                         default=lambda: datetime.now(timezone.utc))


class Machine(Base):
    __tablename__ = "machines"
    id             = Column(Integer, primary_key=True, index=True)
    name           = Column(String(128), nullable=False, unique=True)
    power_kw       = Column(Numeric(10, 2), nullable=True)
    voltage_v      = Column(Numeric(10, 2), nullable=True)
    current_a      = Column(Numeric(10, 2), nullable=True)
    resistance_ohm = Column(Numeric(10, 4), nullable=True)
    notes          = Column(Text, nullable=True)
    extra_fields   = Column(JSON, nullable=True)   # [{name, value, unit}, ...]
    created_at     = Column(DateTime(timezone=True), nullable=False,
                            default=lambda: datetime.now(timezone.utc))
    tests          = relationship("Test", back_populates="machine")


class TestStatus(str, enum.Enum):
    running  = "running"
    finished = "finished"
    aborted  = "aborted"


class TestType(str, enum.Enum):
    temperature = "temperature"
    pressure    = "pressure"


class Test(Base):
    __tablename__ = "tests"
    id                = Column(Integer, primary_key=True, index=True)
    machine_id        = Column(Integer, ForeignKey("machines.id"), nullable=False)
    type              = Column(Enum(TestType), nullable=False)
    status            = Column(Enum(TestStatus), nullable=False, default=TestStatus.running)
    reference_channel = Column(Integer, nullable=False, default=1)
    started_at        = Column(DateTime(timezone=True), nullable=False,
                               default=lambda: datetime.now(timezone.utc))
    finished_at       = Column(DateTime(timezone=True), nullable=True)
    machine           = relationship("Machine", back_populates="tests")
    readings          = relationship("TestReading", back_populates="test",
                                     order_by="TestReading.timestamp")


class TestReading(Base):
    __tablename__ = "test_readings"
    id        = Column(Integer, primary_key=True, index=True)
    test_id   = Column(Integer, ForeignKey("tests.id"), nullable=False)
    channel   = Column(Integer, nullable=False)
    value     = Column(Numeric(8, 3), nullable=False)
    unit      = Column(String(16), nullable=False, default="°C")
    timestamp = Column(DateTime(timezone=True), nullable=False,
                       default=lambda: datetime.now(timezone.utc))
    test      = relationship("Test", back_populates="readings")
