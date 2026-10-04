# ADR 0001: Selecting the MVP application stack

- Status: Accepted
- Date: 2026-08-14

## Context

BridgeScope is a web application that allows users to search, sort, and inspect public bridge records for California. The MVP includes a bridge table, individual bridge detail pages, an Average Daily Traffic ranking, a backend API, and a relational database.

## Decision

- React with TypeScript and Vite for the frontend
- Python and FastAPI for the backend API
- Python's CSV tools for the importer
- PostgreSQL for relational storage
- SQLAlchemy for database access
- Alembic for schema migrations
- pytest for backend testing
- Vitest and React Testing library for frontend testing

## Alternative considered

### All-TypeScript stack

Using one language throughout the application makes it potentially simpler throughout the development process.

## Consequences

### Positive

Interactive table, filters, loading states using React + TypeScript
API routing and request validation via FastAPI
Database models and queries from SQLAlchemy
Relational storage, sorting, and filtering with PostgreSQL

### Negative

- Separate frontend build and API integration
- Added complexity
- Tools that are new which needs time to learn

### Deferred Decisions

- Redis
- Elasticsearch
- PostGIS
- Kubernetes
- Microservices
- Asynchronous database access
