from __future__ import annotations

from datetime import datetime, date
from symtable import Class
from typing import Dict, Any, Optional

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, JSON, UniqueConstraint

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
class CimisRequestCache(Base):
    __tablename__ = "cimis_request_cache"

    id = Column(Integer, primary_key=True)
    # hash of the request parameters
    cache_key = Column(String, unique=True, nullable=False, index=True)
    scope = Column(String, nullable=False)  # "daily", "hourly", "both"
    raw_json = Column(JSON, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("cache_key", name="uq_cimis_cache_cache_key"),
    )

class CimisDaily(Base):
    __tablename__ = "cimis_daily"

    id = Column(Integer, primary_key=True)
    station_id = Column(String, index=True, nullable=False)
    date = Column(Date, index=True, nullable=False)

    # normalized subset of useful fields
    air_temp_min = Column(Float)
    air_temp_max = Column(Float)
    dew_point_min = Column(Float)
    dew_point_max = Column(Float)
    humidity_min = Column(Float)
    humidity_max = Column(Float)
    wind_speed_avg = Column(Float)
    et0 = Column(Float)

    # raw CIMIS JSON payload
    raw = Column(JSON, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("station_id", "date", name="uq_cimis_daily_station_date"),
    )

class CimisHourly(Base):
    __tablename__ = "cimis_hourly"

    id = Column(Integer, primary_key=True, index=True)
    station_id = Column(String, index=True, nullable=False)
    station_name = Column(String, nullable=False)
    date = Column(Date, index=True, nullable=False)
    hour = Column(Integer, index=True, nullable=False)
    air_temp = Column(Float, nullable=True)
    dew_point = Column(Float, nullable=True)
    humidity = Column(Integer, nullable=True)
    wind_speed = Column(Float, nullable=True)
    solar_radiation = Column(Float, nullable=True)
    et0 = Column(Float, nullable=True)
    raw_data = Column(JSON, nullable=True)  # Store raw CIMIS JSON response
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("station_id", "date", "hour", name="uq_cimis_station_date_hour"),
    )


class CimisRecord(Base):
    __tablename__ = "cimis_record"

    id = Column(Integer, primary_key=True)
    station = Column(String, index=True, nullable=False)
    date = Column(Date, index=True, nullable=False)
    hour = Column(Integer, index=True, nullable=True)  # null for daily-only rows

    # All data items for that (station, date, hour) go in here:
    data = Column(JSON, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("station", "date", "hour",
                         name="uq_cimis_record_station_date_hour"),
    )