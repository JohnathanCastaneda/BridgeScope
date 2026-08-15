# ADR 0002: Use the FHWA 2025 California NBI export

- Status: Accepted
- Date: 2026-08-14

## Context

BridgeScope is a application where it uses bridge data and displays it to users who may be interested in knowing the information on bridges.
To do so, it is important to acquire a authoritative California bridge dataset containing the information users would be interested in such as
traffic, condition, construction, etc. Although the long-term for the application is to support nationwide data, the MVP is strictly California only.

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

The FHWA 2025 California National Bridge Inventory highway-bridge comma-delimited export was selected because it was published by the Federal Highway
Administration, contains the required MVP fields, and covers both state and local highway bridges. The FWHA also provides an annual inventory baseline
which updates fields if necessary such as new bridges or bridge conditions changing throught the future.

## Alternatives considered

### California state-highway bridge dataset

This dataset are split by ownership and does not provide the complete state bridge invenotry needed for the MVP.

### Combining multiple California datasets
 
Combing mulitple Califonria datasets would add uncessary complexity to the application.

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