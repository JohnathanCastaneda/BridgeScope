# ADR 0002: Use the FHWA 2025 California NBI export

- Status: Accepted
- Date: 2026-08-14

## Context

BridgeScope is a web application for exploring public bridge inventory data. The MVP requires an authoritative California dataset containing traffic, construction, ownership, location, and condition information. Although the long-term vision is nationwide coverage, the MVP supports California only.

## Decision

The MVP will use the FHWA 2025 California National Bridge Inventory
highway-bridge comma-delimited export.

The exact downloaded file will be identified using:

- Source URL
- File name
- Inventory year
- Retrieval timestamp
- File size
- SHA-256 checksum

The full raw source file will not be committed to Git.

## Why this source was selected

FHWA publishes annual NBI inventory snapshots. This gives the application a reproducible baseline and creates a possible path toward supporting later inventory years. Individual values may still have different measurement years, and FHWA may publish corrected revisions of an annual file.

## Alternatives considered

### California state-highway bridge dataset

California publishes separate bridge datasets for different ownership categories. Using those sources would require combining multiple schemas and still might not provide all fields required by the MVP in one authoritative export.

### Combining multiple California datasets

Combining multiple California datasets would add unnecessary complexity to the application.

## Risks

Document:
- Coded and missing values
- Different inventory, inspection, and traffic years
- Possible corrected source-file revisions
- The transition from the legacy NBI format to SNBI
- The risk of presenting condition classifications incorrectly

## Consequences

- Raw FHWA column names will be isolated in the source-mapping layer
- Dataset provenance will be stored in the database
- The initial importer will support one known source format
- Future SNBI support will require a separate source adapter
