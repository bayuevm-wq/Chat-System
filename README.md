# Distributed Chat System Backend

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A production-grade distributed chat backend offering real-time messaging, multi-node synchronization, and robust fault tolerance. Built with Modern Python (3.12+), FastAPI, PostgreSQL, and Redis.

## Features

- **Real-Time Messaging**: Bidirectional, low-latency communication over WebSockets.
- **Multi-Node Synchronization**: Horizontally scalable via Redis Pub/Sub for cross-node event distribution.
- **Robust Authentication & Security**: JWT-based authentication, bcrypt password hashing, and encrypted channels.
- **Fault Tolerance**: Implemented with Circuit Breakers, retry mechanisms (Tenacity), and Dead Letter Queues (DLQ) for message workers.
- **Rate Limiting**: Protection against abuse and DDoS using SlowAPI and Redis.
- **Comprehensive Observability**: Structured logging (Structlog), metrics (Prometheus), and distributed tracing (OpenTelemetry).
- **Domain-Driven Design (DDD)**: Clean architecture principles ensuring separation of concerns, maintainability, and testability.

## Technology Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com)
- **Database**: PostgreSQL (with [SQLAlchemy 2.0 Async](https://docs.sqlalchemy.org/) & [Alembic](https://alembic.sqlalchemy.org/))
- **Caching & Pub/Sub**: [Redis](https://redis.io/)
- **Validation**: [Pydantic v2](https://docs.pydantic.dev/)
- **Containerization**: Docker & Docker Compose
- **Testing**: Pytest (with asyncio, cov)

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
- Python 3.12+ (if running locally without Docker)

### Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/bayuevm-wq/Chat-System.git
   cd Chat-System
   ```

2. **Environment Variables**:
   Copy the example environment file and configure it as needed.
   ```bash
   cp .env.example .env
   ```

3. **Run with Docker Compose**:
   The easiest way to start the system (API, PostgreSQL, and Redis) is via Docker.
   ```bash
   docker-compose up --build
   ```

4. **Database Migrations**:
   Run Alembic to apply the latest database schemas.
   ```bash
   docker-compose exec api alembic upgrade head
   ```

### Local Development

If you prefer to run the application locally outside of Docker (you will still need PostgreSQL and Redis running):

1. **Create a virtual environment and install dependencies**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e ".[dev]"
   ```

2. **Start the API server**:
   ```bash
   uvicorn src.main:app --reload
   ```

## Project Structure

```
.
├── src/
│   ├── api/             # REST and WebSocket routers, middleware, dependencies
│   ├── application/     # Service layer, orchestrating domain logic
│   ├── domain/          # Core entities, value objects, domain events, exceptions
│   ├── infrastructure/  # DB, Redis, Security, Workers, Observability implementations
│   ├── shared/          # Constants, utilities, circuit breakers, retries
│   └── main.py          # FastAPI application entry point
├── tests/               # Unit and Integration tests
├── migrations/          # Alembic database migrations
├── docker-compose.yml   # Docker composition for local services
├── Dockerfile           # Backend container definition
└── pyproject.toml       # Dependencies, scripts, and build configurations
```

## Testing

The project uses `pytest` for both unit and integration tests.

To run the test suite:
```bash
pytest
```
For coverage reports:
```bash
pytest --cov=src
```

## Code Quality

We enforce strict code quality using `ruff` and `mypy`.
```bash
# Lint and format
ruff check src tests
ruff format src tests

# Static type checking
mypy src
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
