from sqlalchemy.orm import DeclarativeBase, mapped_column
from sqlalchemy import Integer, String, DateTime, func
import datetime

class Base(DeclarativeBase):
    pass

class OdometerReport(Base):
    __tablename__ = "odometer_reports"
    id = mapped_column(String(50), primary_key=True)
    VIN = mapped_column(String(50), primary_key=False)
    owner_id = mapped_column(String(50), nullable=False)
    odometer = mapped_column(Integer, nullable=False)
    time_stamp = mapped_column(DateTime, nullable=False)
    date_created = mapped_column(DateTime, nullable=False, default=func.now())
    trace_id = mapped_column(String(50), nullable=False)

class JobCompletion(Base):
    __tablename__ = "job_completions"
    id = mapped_column(String(50), primary_key=True)
    job_id = mapped_column(String(50), primary_key=False)
    bay_id = mapped_column(Integer, primary_key=False)
    VIN = mapped_column(String(50), nullable=False)
    description = mapped_column(String(50), nullable=False)
    time_stamp = mapped_column(DateTime, nullable=False)
    date_created = mapped_column(DateTime, nullable=False, default=func.now())
    trace_id = mapped_column(String(50), nullable=False)
