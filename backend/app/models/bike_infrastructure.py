"""Bike Infrastructure database model."""

import enum
from datetime import datetime
from typing import Optional

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    Enum,
    Integer,
    Numeric,
    String,
    DateTime,
    BigInteger,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.risk_zone import DataSource


class BikeLaneType(str, enum.Enum):
    """Types of bike lane infrastructure."""

    PROTECTED = "protected"  # Physical barrier separation
    BUFFERED = "buffered"  # Painted buffer, no barrier
    DEDICATED = "dedicated"  # Painted bike lane
    SHARED_LANE = "shared_lane"  # Sharrows
    BIKE_BOULEVARD = "bike_boulevard"  # Low-traffic street with bike priority
    SHARED_BUS_BIKE = "shared_bus_bike"  # Shared bus/bike lane
    PATH = "path"  # Off-street bike path
    NONE = "none"  # No bike infrastructure


class BikeInfrastructure(Base):
    """Bike infrastructure segment."""

    __tablename__ = "bike_infrastructure"

    # Geometry (LineString for road segments)
    geometry: Mapped[str] = mapped_column(
        Geometry(geometry_type="LINESTRING", srid=4326),
        nullable=False,
    )

    # Infrastructure details
    lane_type: Mapped[BikeLaneType] = mapped_column(
        Enum(BikeLaneType),
        nullable=False,
    )
    lane_width_meters: Mapped[Optional[float]] = mapped_column(
        Numeric(4, 2), nullable=True
    )
    is_bidirectional: Mapped[bool] = mapped_column(Boolean, default=False)
    surface_quality: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # 1=poor, 5=excellent

    # Road context
    street_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    speed_limit_mph: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    traffic_volume: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # Estimated daily vehicles

    # OSM reference
    osm_way_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Metadata
    source: Mapped[DataSource] = mapped_column(Enum(DataSource), nullable=False)
    last_surveyed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class SegmentGrade(Base):
    """Pre-computed segment elevation grades for hill analysis."""

    __tablename__ = "segment_grades"

    # Segment geometry
    geometry: Mapped[str] = mapped_column(
        Geometry(geometry_type="LINESTRING", srid=4326),
        nullable=False,
    )

    # Elevation data
    start_elevation_meters: Mapped[Optional[float]] = mapped_column(
        Numeric(8, 2), nullable=True
    )
    end_elevation_meters: Mapped[Optional[float]] = mapped_column(
        Numeric(8, 2), nullable=True
    )
    length_meters: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    grade_percent: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2), nullable=True
    )  # Positive = uphill
    max_grade_percent: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2), nullable=True
    )

    # OSM reference
    osm_way_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Classification
    difficulty: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # 1=flat, 5=steep
