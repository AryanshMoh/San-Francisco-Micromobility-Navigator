# SF Micromobility Navigation

A web application for safe micromobility navigation in San Francisco with intelligent routing, risk zone awareness, and real-time audio alerts.

## Features

- **Smart Routing**: Calculate optimal routes for scooters, bikes, and e-bikes
- **Bike Lane Preference**: Routes prioritize protected and dedicated bike lanes
- **Hill Awareness**: Optional hill avoidance for SF's steep terrain
- **Risk Zone Alerts**: Audio warnings when approaching hazards (potholes, dangerous intersections, etc.)
- **Dynamic Rerouting**: Automatic route recalculation when conditions change
- **User Reporting**: Community-driven hazard reporting system

## Tech Stack

- **Frontend**: React 18 + TypeScript + Vite
- **Backend**: Python FastAPI
- **Database**: PostgreSQL + PostGIS
- **Routing Engine**: Valhalla
- **Cache**: Redis
- **Maps**: Mapbox GL JS

## Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)
- Mapbox API token

## Quick Start

1. **Clone and setup environment**

```bash
cd sf-micromobility-nav
cp .env.example .env
# Edit .env and add your Mapbox token and other API keys
```

2. **Start all services with Docker Compose**

```bash
docker-compose up -d
```

This will start:
- PostgreSQL/PostGIS database on port 5432
- Redis on port 6379
- Valhalla routing engine on port 8002
- FastAPI backend on port 8000
- React frontend on port 5173

3. **Wait for Valhalla to build routing tiles** (first run only, ~5-10 minutes)

```bash
docker-compose logs -f valhalla
```

4. **Access the application**

Open http://localhost:5173 in your browser.

## Development Setup

### Backend (without Docker)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend (without Docker)

```bash
cd frontend
npm install
npm run dev
```

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
sf-micromobility-nav/
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── api/       # API routes
│   │   ├── models/    # Database models
│   │   ├── schemas/   # Pydantic schemas
│   │   ├── services/  # Business logic
│   │   └── db/        # Database config
│   └── tests/
├── frontend/          # React frontend
│   └── src/
│       ├── components/
│       ├── hooks/
│       ├── store/
│       └── api/
├── routing-engine/    # Valhalla config
└── docker-compose.yml
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `POSTGRES_USER` | Database username |
| `POSTGRES_PASSWORD` | Database password |
| `POSTGRES_DB` | Database name |
| `MAPBOX_ACCESS_TOKEN` | Mapbox API token for maps |
| `SF_OPENDATA_APP_TOKEN` | SF Open Data API token |
| `OPENWEATHER_API_KEY` | OpenWeather API key |

## Data Sources

- **OpenStreetMap**: Road network, bike infrastructure
- **SF Open Data**: 311 reports, bike network, pavement conditions
- **OpenWeather**: Weather conditions for safety adjustments

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License
