# BridgeScope Database Schema

## Purpose

This document defines the relational database design for the BridgeScope MVP.

The database must support:
- California bridge records from an FHWA NBI dataset
- Source-file provenance
- Repeatable imports
- Duplicate prevention
- Import execution history
- Structured import warnings and errors
- Bridge search, filtering, sorting, and pagination
- Highest estimated Average Daily Traffic rankings

The MVP stores one or more source dataset revisions, but the application will expose only the active California dataset.
Historical comparison between annual datasets is outside the MVP scope.

## Schema overview

The MVP uses four tables:
- bridge_datasets
- bridges
- import_runs
- import_issues

Their responsibilities are:
Table / Responsibility
- bridge_datasets
- Identifies an exact FHWA source dataset revision

- bridges
- Stores normalized bridge records belonging to a dataset

- import_runs
- Records each importer execution

- import_issues
- Records warnings and errors discovered during an import

The corresponding relationships are documented in erd.md.

## 1. bridge_datasets

### Purpose

Represents one exact source dataset revision.
A dataset is identified by more than its inventory year because FHWA may publish a corrected file for the same year. The SHA-256 checksum identifies the exact bytes processed by BridgeScope.

| Column | Type | Null? | Description |
| --- | --- | --- | --- |
| `id` | `BIGINT` | No | Internal primary key |
| `provider` | `VARCHAR(32)` | No | Data publisher, initially `FHWA` |
| `state_code` | `CHAR(2)` | No | State identifier, `06` for California |
| `inventory_year` | `SMALLINT` | No | NBI inventory year |
| `source_format` | `VARCHAR(64)` | No | Machine-readable source format identifier |
| `source_specification` | `VARCHAR(64)` | No | Specification used to interpret the source file |
| `source_url` | `TEXT` | No | Original source location |
| `source_file_name` | `TEXT` | No | Original source filename |
| `source_sha256` | `CHAR(64)` | No | SHA-256 checksum of the source file |
| `retrieved_at` | `TIMESTAMPTZ` | No | UTC time at which the source file was retrieved |
| `is_active` | `BOOLEAN` | No | Indicates whether API queries should use this dataset |
| `created_at` | `TIMESTAMPTZ` | No | Database creation timestamp |

### Constraints

PRIMARY KEY (id)
UNIQUE (source_sha256)

source_sha256 is unique because importing the exact same source bytes should not create another dataset revision.

### Future consideration

Only one dataset for a state should normally be active at a time.
The MVP can initially enforce this through application logic. A partial unique index may be considered later if needed.

# 2. bridges

## Purpose

Stores the canonical representation of one FHWA bridge record within one dataset revision.
The table contains only the source fields required by the BridgeScope MVP rather than all 123 source columns.

## Identity

BridgeScope uses an internal numeric primary key:

id

The source-level candidate key is:

(dataset_id, state_code, structure_number)

structure_number is not globally unique and is therefore not used as the database primary key.

##Columns

| Column | Type | Null? | Description |
| --- | --- | --- | --- |
| `id` | `BIGINT` | No | Internal primary key |
| `dataset_id` | `BIGINT` | No | Foreign key referencing `bridge_datasets.id` |
| `state_code` | `CHAR(2)` | No | NBI state code |
| `structure_number` | `VARCHAR(15)` | No | Normalized bridge structure identifier |
| `county_code` | `CHAR(3)` | No | County code associated with the bridge |
| `facility_carried` | `TEXT` | Yes | Road or facility carried by the structure |
| `feature_crossed` | `TEXT` | Yes | Feature intersected or crossed by the structure |
| `latitude` | `NUMERIC(9,6)` | Yes | Normalized decimal latitude |
| `longitude` | `NUMERIC(10,6)` | Yes | Normalized decimal longitude |
| `source_latitude_code` | `CHAR(8)` | Yes | Original packed NBI latitude value |
| `source_longitude_code` | `CHAR(9)` | Yes | Original packed NBI longitude value |
| `year_built` | `SMALLINT` | No | Original construction year |
| `year_reconstructed` | `SMALLINT` | Yes | Reconstruction year when applicable |
| `average_daily_traffic` | `INTEGER` | Yes | Reported estimated Average Daily Traffic |
| `traffic_year` | `SMALLINT` | Yes | Year associated with the reported ADT |
| `truck_traffic_percent` | `NUMERIC(5,2)` | Yes | Reported truck traffic percentage |
| `lanes_on` | `SMALLINT` | Yes | Number of traffic lanes carried by the structure |
| `bridge_length_m` | `NUMERIC(10,2)` | Yes | Structure length in meters |
| `maximum_span_m` | `NUMERIC(10,2)` | Yes | Maximum span length in meters |
| `owner_code` | `VARCHAR(4)` | Yes | FHWA owner code |
| `material_code` | `VARCHAR(4)` | Yes | FHWA structure material code |
| `design_type_code` | `VARCHAR(4)` | Yes | FHWA design or structure type code |
| `inspection_month` | `SMALLINT` | Yes | Month of the reported inspection |
| `inspection_year` | `SMALLINT` | Yes | Year of the reported inspection |
| `deck_condition_code` | `CHAR(1)` | Yes | Deck condition code |
| `superstructure_condition_code` | `CHAR(1)` | Yes | Superstructure condition code |
| `substructure_condition_code` | `CHAR(1)` | Yes | Substructure condition code |
| `culvert_condition_code` | `CHAR(1)` | Yes | Culvert condition code |
| `overall_condition_code` | `CHAR(1)` | Yes | FHWA overall condition classification |
| `lowest_condition_rating` | `SMALLINT` | Yes | Lowest applicable component condition rating |
| `source_row_number` | `INTEGER` | No | Original logical row position in the source file |
| `created_at` | `TIMESTAMPTZ` | No | Database creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | Last modification timestamp |

### Foreign keys

dataset_id
    REFERENCES bridge_datasets(id)

Suggested delete behavior:

ON DELETE CASCADE

A bridge record has no meaning without its source dataset.

## Bridge constraints

### Candidate key
UNIQUE (
    dataset_id,
    state_code,
    structure_number
)

This protects against accidental duplicate bridge records within one source dataset.
The structure number must remain text because source identifiers may contain:
- Leading zeros
- Letters
- Internal spaces

Only leading and trailing padding is removed during normalization.

### Numeric constraints

average_daily_traffic >= 0
truck_traffic_percent BETWEEN 0 AND 100
lanes_on >= 0
bridge_length_m >= 0
maximum_span_m >= 0

These checks operate on already-normalized canonical values.
Source-specific sentinel conversion occurs before database insertion.

### Coordinate constraints

latitude BETWEEN -90 AND 90
longitude BETWEEN -180 AND 180

California-specific geographic bounds should remain importer validation rather than database constraints.
This keeps the canonical schema usable if nationwide support is added later.

### Inspection constraints

inspection_month BETWEEN 1 AND 12

BridgeScope stores inspection month and year separately because the source does not provide a day.
The importer must not create artificial dates such as:

2024-05-01

when the actual source contains only May 2024.

### Component condition constraints

Valid component condition codes are:
0
1
2
3
4
5
6
7
8
9
N
NULL

N means a rating is not applicable.
It must not be converted to numeric zero or treated as equivalent to an unknown value.

Applies to:
deck_condition_code
superstructure_condition_code
substructure_condition_code
culvert_condition_code

### Overall condition constraint
Valid canonical values are:

G
F
P
NULL

The values represent FHWA condition classifications.
BridgeScope must not interpret these codes by themselves as declarations that a bridge is safe or unsafe.

### Lowest condition rating constraint

lowest_condition_rating BETWEEN 0 AND 9
or NULL.

# 3. import_runs

## Purpose
Records every attempt to import an NBI source file.
Import history is stored separately from datasets because:
- An import may fail before a dataset is created.
- The same file may be attempted more than once.
- A duplicate file may be deliberately skipped.
- Operational diagnostics should not be stored on bridge rows.

| Column | Type | Null? | Description |
| --- | --- | --- | --- |
| `id` | `BIGINT` | No | Internal primary key |
| `dataset_id` | `BIGINT` | Yes | Foreign key referencing the dataset created or associated with the import |
| `source_file_name` | `TEXT` | No | Name of the source file processed |
| `source_sha256` | `CHAR(64)` | No | SHA-256 checksum of the input file |
| `status` | `VARCHAR(32)` | No | Current or final status of the import |
| `started_at` | `TIMESTAMPTZ` | No | Time the import started |
| `finished_at` | `TIMESTAMPTZ` | Yes | Time the import finished |
| `rows_read` | `INTEGER` | No | Number of logical records read from the source |
| `rows_inserted` | `INTEGER` | No | Number of new bridge records inserted |
| `rows_updated` | `INTEGER` | No | Number of existing bridge records updated |
| `rows_unchanged` | `INTEGER` | No | Number of records that required no database change |
| `rows_rejected` | `INTEGER` | No | Number of source records rejected |
| `warnings_count` | `INTEGER` | No | Number of warnings produced during the import |
| `errors_count` | `INTEGER` | No | Number of errors produced during the import |
| `summary` | `JSONB` | No | Additional structured statistics about the import |
| `failure_message` | `TEXT` | Yes | Run-level failure explanation when the import fails |

## Status values
Initial supported statuses:

running
completed
completed_with_warnings
failed
skipped_duplicate_file

Use a text column with a check constraint rather than a PostgreSQL enum.
This makes adding future statuses easier through migrations.

### Counter constraints
All row and issue counters must satisfy:

>= 0

# 4. import_issues

## Purpose
Stores structured warnings and errors associated with an import run.
This allows importer behavior to be inspected after execution without relying only on console logs.

| Column | Type | Null? | Description |
| --- | --- | --- | --- |
| `id` | `BIGINT` | No | Internal primary key |
| `import_run_id` | `BIGINT` | No | Foreign key referencing `import_runs.id` |
| `severity` | `VARCHAR(16)` | No | Severity of the issue, such as warning, error, or fatal |
| `row_number` | `INTEGER` | Yes | Source row associated with the issue when available |
| `structure_number` | `VARCHAR(15)` | Yes | Bridge structure identifier when available |
| `field_name` | `TEXT` | Yes | Source or canonical field associated with the issue |
| `error_code` | `VARCHAR(64)` | No | Stable machine-readable issue identifier |
| `raw_value` | `TEXT` | Yes | Original source value that caused or contributed to the issue |
| `message` | `TEXT` | No | Human-readable description of the issue |
| `raw_record` | `JSONB` | Yes | Optional original source record used for diagnostics |
| `created_at` | `TIMESTAMPTZ` | No | Database creation timestamp |

### Severity values
warning
error
fatal

Suggested semantics:

### Warning
The bridge can still be imported, but an optional value could not be interpreted normally.

### Error
A specific row cannot be imported reliably.

### Fatal
The import itself cannot proceed safely.

Examples include:
missing required source columns
unsupported source format
unreadable source file

## Indexes
Indexes should correspond to known MVP queries rather than anticipated future features.

### Bridge identity lookup
Provided by:

UNIQUE (
    dataset_id,
    state_code,
    structure_number
)

This supports bridge-detail lookup.

### Highest estimated ADT ranking

INDEX (
    dataset_id,
    average_daily_traffic DESC
)

Supports:

GET /api/rankings/highest-adt

### County filtering

INDEX (
    dataset_id,
    county_code
)

### Year-built filtering

INDEX (
    dataset_id,
    year_built
)

### Condition filtering

INDEX (
    dataset_id,
    overall_condition_code
)

## Text search

The MVP will initially search fields such as:
structure_number
facility_carried
feature_crossed

using normal PostgreSQL text operations.
Specialized search infrastructure is intentionally deferred.
Not included in the initial schema:
- Elasticsearch
- PostgreSQL full-text search configuration
- Trigram indexes
- Dedicated search tables

Search performance will be measured before additional indexing is introduced.

## Duplicate prevention
Duplicate protection exists at two levels.
### Source-file level

bridge_datasets.source_sha256

is unique.
An identical file should therefore not produce another dataset revision.

### Bridge-record level

UNIQUE (
    dataset_id,
    state_code,
    structure_number
)

prevents duplicate normalized bridge records within a dataset.
The importer should detect duplicates explicitly, while database constraints provide the final safeguard.

### Active dataset behavior
The API will query the dataset marked:

is_active = TRUE

This permits BridgeScope to retain more than one dataset revision without exposing historical comparison functionality.
Switching the active dataset is an operational action and does not delete older records.
Historical browsing and year-to-year bridge comparison remain post-MVP features.

### Delete behavior

Recommended ownership rules:

bridge_datasets
    └── bridges
        ON DELETE CASCADE

and:

import_runs
    └── import_issues
        ON DELETE CASCADE

Deletion of dataset or import history should be rare in production.

The cascade behavior primarily prevents orphan rows during development and automated testing.

# Deferred schema features
The MVP intentionally excludes:
- Nationwide support
- Maps and geospatial visualization
- Separate bridge identity/history tables
- PostGIS geometry columns
- Material lookup tables
- Owner lookup tables
- Design-type lookup tables
- Historical comparison tables and year-to-year comparison workflows
- User accounts and account-specific data
- Favorite bridges
- Comments
- Search-specific tables
- Real-time traffic integrations
- Advanced analytics and analytics/event tables
- Multiple databases

These should only be introduced after a concrete requirement justifies them.

## Schema design principles

The schema follows several rules:

Preserve source provenance.

Store canonical values rather than UI-formatted strings.

Preserve important source codes.

Enforce invariants at the database boundary.

Allow optional source-data problems without losing an otherwise valid bridge.

Prevent silent duplicates.

Add indexes only for demonstrated query patterns.

Avoid modeling post-MVP features prematurely.
