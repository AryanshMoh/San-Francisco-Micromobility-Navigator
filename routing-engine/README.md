# Valhalla Routing Engine Setup

This directory contains configuration for the Valhalla open-source routing engine used for street-level navigation in SF.

## Quick Start

### Option 1: Run with Full Stack
```bash
# From project root
docker compose up valhalla
```

### Option 2: Run Valhalla Standalone
```bash
# From project root
docker compose -f routing-engine/docker-compose.valhalla.yml up
```

## First-Time Setup

On first run, Valhalla will:
1. Download NorCal OSM data (~600MB)
2. Build routing tiles (10-30 minutes depending on hardware)
3. Build admin areas and timezone data
4. Start the routing service on port 8002

Watch the build progress:
```bash
docker compose logs -f valhalla
```

## Verify Installation

Check service status:
```bash
curl http://localhost:8002/status
```

Test a route (SF City Hall to Ferry Building):
```bash
curl -X POST http://localhost:8002/route \
  -H 'Content-Type: application/json' \
  -d '{
    "locations": [
      {"lat": 37.7793, "lon": -122.4193},
      {"lat": 37.7955, "lon": -122.3937}
    ],
    "costing": "bicycle",
    "costing_options": {
      "bicycle": {
        "bicycle_type": "Hybrid",
        "use_roads": 0.3,
        "use_hills": 0.3
      }
    },
    "directions_options": {
      "units": "meters"
    }
  }' | jq .
```

## Configuration

### valhalla.json

The main configuration file with settings for:
- **mjolnir**: Tile storage locations
- **service_limits**: Max distances and locations per request
- **costing_options**: Default bicycle routing parameters
- **httpd**: Server port configuration (8002)

### Bicycle Costing Options

| Parameter | Range | Description |
|-----------|-------|-------------|
| `use_roads` | 0-1 | Higher = prefer roads over bike paths |
| `use_hills` | 0-1 | Higher = accept hillier routes |
| `avoid_bad_surfaces` | 0-1 | Higher = prefer smooth surfaces |
| `bicycle_type` | Road/Hybrid/Cross/Mountain | Affects speed calculations |
| `cycling_speed` | km/h | Base cycling speed |

## Route Profiles

The backend uses different costing options per profile:

| Profile | use_roads | use_hills | avoid_bad_surfaces |
|---------|-----------|-----------|-------------------|
| SAFEST | 0.2 | 0.3 | 0.8 |
| FASTEST | 0.7 | 0.7 | 0.3 |
| BALANCED | 0.5 | 0.5 | 0.5 |
| SCENIC | 0.3 | 0.4 | 0.6 |

## Rebuilding Tiles

To force a rebuild with fresh OSM data:
```bash
# Stop and remove the container
docker compose down valhalla

# Remove the tiles volume
docker volume rm micromobility-navigation-in-sf_valhalla_tiles

# Restart
docker compose up valhalla
```

## Memory Requirements

- **Tile Building**: 4GB RAM recommended
- **Running Service**: 1-2GB RAM for NorCal region

## Troubleshooting

### Container Won't Start
Check logs for errors:
```bash
docker compose logs valhalla
```

### Route Returns Error
Ensure both origin and destination are within the tile coverage area (NorCal).

### Slow First Request
First request after startup may take a few seconds as Valhalla loads tiles into memory.

## API Reference

See [Valhalla API Documentation](https://valhalla.github.io/valhalla/api/) for full endpoint details.

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/status` | GET | Health check |
| `/route` | POST | Calculate route |
| `/optimized_route` | POST | Multi-stop optimization |
| `/isochrone` | POST | Reachability polygons |
| `/locate` | POST | Snap to road network |
