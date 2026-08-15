# ADR 001 - Selecting the MVP application stack

- Status: Accepted
- Date: 08/14/26

## Context

BridgeScope is a application where users are able to interact with a map of California and select each of the thousands bridges across the state
using the Federal Highway Administation Nationaly Bridge Inventory (NBI). The tool catalogs plentiful information about bridges nationwide, but for the MVP, California is the only state being considered with bridge informaiton such as condition, year built, average daily traffic, etc.

## Decision

- React with TypeScrupt and Vite for the frontend
- Python and FastAPI for the backend API
- Python's CSV tools for the importer
- PostgreSQL for relational storage
- SQLAlechmy for database Access
- Alebmic for schema migrations
- pytest for backend testing
- Vitest and React Testing library for frontend testing

## Alternative considered

### All-TypeScript stack

Using one langauge throughout the application makes it potentially simpler throughout the development process.

## Consequences

### Postiive

Interactive table, filters, loading states using React + TypeScript
API Routing, request validation, via FastAPI
Database models and queries from SQLAlchemy
Relational Storage, sorting, and filtering with PostgreSQL

### Negative

- Serparte frontend build and API integration
- Added complexity
- Tools that are new which needs time to learn

### Deferred Decisions

- Redis
- Elasticsearch
- PostGIS
- Kubernetes
- Microservices
- Asynchronous database access