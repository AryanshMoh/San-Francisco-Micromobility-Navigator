"""Risk Zone database model."""

import enum
from datetime import datetime, time
from typing import Optional, List

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    Enum,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    DateTime,
    ARRAY,
    BigInteger,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class HazardType(str, enum.Enum):
    """Types of hazards that can be reported."""

    POTHOLE = "pothole"
    DANGEROUS_INTERSECTION = "dangerous_intersection"
    BLIND_TURN = "blind_turn"
    POOR_PAVEMENT = "poor_pavement"
    CONSTRUCTION = "construction"
    HIGH_TRAFFIC = "high_traffic"
    STEEP_GRADE = "steep_grade"
    NARROW_PASSAGE = "narrow_passage"
    DOOR_ZONE = "door_zone"
    TROLLEY_TRACKS = "trolley_tracks"
    CABLE_CAR_TRACKS = "cable_car_tracks"
    MUNI_CONFLICT = "muni_conflict"
    PEDESTRIAN_HEAVY = "pedestrian_heavy"
    OTHER = "other"


class HazardSeverity(str, enum.Enum):
    """Severity levels for hazards."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DataSource(str, enum.Enum):
    """Source of the risk zone data."""

    SF_311 = "sf_311"
    OSM = "osm"
    USER_REPORT = "user_report"
    MUNICIPAL = "municipal"
    AUTOMATED = "automated"
    MANUAL_SURVEY = "manual_survey"


class RiskZone(Base):
    """Risk zone representing a hazardous area for micromobility."""

    __tablename__ = "risk_zones"

    # Geometry (can be point, line, or polygon)
    geometry: Mapped[str] = mapped_column(
        Geometry(geometry_type="GEOMETRY", srid=4326),
        nullable=False,
    )

    # Classification
    hazard_type: Mapped[HazardType] = mapped_column(
        Enum(HazardType),
        nullable=False,
    )
    severity: Mapped[HazardSeverity] = mapped_column(
        Enum(HazardSeverity),
        default=HazardSeverity.MEDIUM,
    )

    # Descriptive information
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Operational details
    is_permanent: Mapped[bool] = mapped_column(Boolean, default=True)
    start_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    end_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    active_days: Mapped[Optional[List[int]]] = mapped_column(
        ARRAY(Integer), nullable=True
    )

    # Audio alert configuration
    alert_radius_meters: Mapped[int] = mapped_column(Integer, default=50)
    alert_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Data provenance
    source: Mapped[DataSource] = mapped_column(Enum(DataSource), nullable=False)
    source_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Numeric(3, 2), default=1.0)

    # Metadata
    reported_count: Mapped[int] = mapped_column(Integer, default=1)
    last_confirmed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # OSM references
    osm_way_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    osm_node_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
