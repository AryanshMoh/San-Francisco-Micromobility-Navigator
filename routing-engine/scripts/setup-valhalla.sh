#!/bin/bash
# Setup script for Valhalla routing engine with San Francisco OSM data
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OSM_DIR="${PROJECT_ROOT}/../backend/data/osm"
TILES_DIR="${PROJECT_ROOT}/valhalla_tiles"

echo "=== Valhalla Setup for SF Micromobility Navigation ==="
echo ""

# Create directories
mkdir -p "$OSM_DIR" "$TILES_DIR"

# Download SF Bay Area OSM extract (smaller than full NorCal)
OSM_FILE="${OSM_DIR}/sf-bay-area.osm.pbf"

if [ ! -f "$OSM_FILE" ]; then
    echo "Downloading San Francisco Bay Area OSM data..."
    echo "This may take a few minutes..."

    # Use BBBike extract for SF Bay Area (smaller, focused area)
    # Alternative: Geofabrik NorCal extract
    curl -L -o "$OSM_FILE" \
        "https://download.geofabrik.de/north-america/us/california/norcal-latest.osm.pbf"

    echo "Download complete: $OSM_FILE"
else
    echo "OSM file already exists: $OSM_FILE"
fi

echo ""
echo "=== Starting Valhalla Container ==="
echo ""

# Start only the Valhalla service
cd "${PROJECT_ROOT}/.."
docker compose up -d valhalla

echo ""
echo "=== Valhalla Setup Status ==="
echo ""
echo "Valhalla container is starting. It will:"
echo "  1. Download OSM data (if configured via tile_urls)"
echo "  2. Build routing tiles (this may take 10-30 minutes)"
echo "  3. Start the routing service on port 8002"
echo ""
echo "Check status with:"
echo "  docker compose logs -f valhalla"
echo ""
echo "Test the service:"
echo "  curl http://localhost:8002/status"
echo ""
echo "Once ready, test routing:"
echo "  curl -X POST http://localhost:8002/route -H 'Content-Type: application/json' \\"
echo '    -d '"'"'{"locations":[{"lat":37.7749,"lon":-122.4194},{"lat":37.7849,"lon":-122.4094}],"costing":"bicycle"}'"'"
echo ""
