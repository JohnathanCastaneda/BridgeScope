# BridgeScope
BridgeScope is a web application for exploring public bridge inventory data. The MVP requires an authoritative California dataset containing traffic, construction, ownership, location, and condition information. Although the long-term vision is nationwide coverage, the MVP supports California only.

# Current MVP scope

Current MVP scope
Repository layout
Backend setup
Backend test command
Backend development command
Frontend setup
Frontend development command
Frontend build command
Data-file policy

# PostgreSQL development database

Start PostgreSQL:

bash
docker compose up -d

Check its status
- docker compose ps

Stop PostgreSQL
- docker compose down

Reset the local database and remove its persistent volume
- docker compose down -v

Connect using psql
- docker compose exec db psql -U bridgescope -d bridgescope