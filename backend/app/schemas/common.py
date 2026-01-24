"""Common schemas used across the application."""

from typing import List, Optional, Any
from pydantic import BaseModel, Field


class Coordinate(BaseModel):
    """Geographic coordinate."""

    latitude: float = Field(..., ge=-90, le=90, description="Latitude in degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in degrees")


class GeoJSONPoint(BaseModel):
    """GeoJSON Point geometry."""

    type: str = "Point"
    coordinates: List[float] = Field(
        ..., min_length=2, max_length=3, description="[longitude, latitude, elevation?]"
    )


class GeoJSONLineString(BaseModel):
    """GeoJSON LineString geometry."""

    type: str = "LineString"
    coordinates: List[List[float]] = Field(
        ..., description="Array of [longitude, latitude, elevation?] coordinates"
    )


class GeoJSONPolygon(BaseModel):
    """GeoJSON Polygon geometry."""

    type: str = "Polygon"
    coordinates: List[List[List[float]]] = Field(
        ..., description="Array of linear rings"
    )


class GeoJSONFeature(BaseModel):
    """GeoJSON Feature."""

    type: str = "Feature"
    geometry: Any
    properties: dict = Field(default_factory=dict)
    id: Optional[str] = None


class GeoJSONFeatureCollection(BaseModel):
    """GeoJSON FeatureCollection."""

    type: str = "FeatureCollection"
    features: List[GeoJSONFeature] = Field(default_factory=list)


class BoundingBox(BaseModel):
    """Bounding box for spatial queries."""

    min_lon: float = Field(..., ge=-180, le=180)
    min_lat: float = Field(..., ge=-90, le=90)
    max_lon: float = Field(..., ge=-180, le=180)
    max_lat: float = Field(..., ge=-90, le=90)

    @classmethod
    def from_string(cls, bbox_str: str) -> "BoundingBox":
        """Parse bounding box from comma-separated string."""
        parts = [float(x) for x in bbox_str.split(",")]
        if len(parts) != 4:
            raise ValueError("Bounding box must have 4 values: min_lon,min_lat,max_lon,max_lat")
        return cls(
            min_lon=parts[0],
            min_lat=parts[1],
            max_lon=parts[2],
            max_lat=parts[3],
        )
