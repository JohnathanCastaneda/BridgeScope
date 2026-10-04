# Import Validation Policy

This document defines how the BridgeScope importer treats invalid rows, optional attributes, sentinel values, and import diagnostics for the FHWA 2025 California NBI source.

## 1. Severity Levels

### 1.1 FATAL (Batch Abortion)

**Trigger**: The source file cannot be safely interpreted or imported.

Examples:
- Required source columns from `field-mapping.md` are missing.
- The delimiter or quote encoding cannot be read as the documented comma-delimited format.
- The source file checksum does not match the source manifest for a declared dataset import.
- The importer cannot create the required `bridge_datasets` or `import_runs` records.

**Action**: Roll back the active transaction when one exists. No bridge rows are committed. The importer records an `import_issues` row with `severity = 'fatal'` when an `import_runs` row exists, marks the run as `failed`, and exits with a non-zero status.

### 1.2 REJECT_ROW (Record Rejection)

**Trigger**: A source row fails identity or required baseline validation for non-null `bridges` fields.

Examples:
- Missing or blank `STRUCTURE_NUMBER_008`.
- Missing or non-`06` `STATE_CODE_001`.
- Missing, blank, or invalid `COUNTY_CODE_003`.
- Missing or invalid `YEAR_BUILT_027`, including non-numeric values, `0`, values before 1800, or values after the dataset `inventory_year`.
- Duplicate `(dataset_id, state_code, structure_number)` values with conflicting source data.

**Action**: Discard the row from `bridges`, increment `rows_rejected` and `errors_count`, and write an `import_issues` row with `severity = 'error'`.

### 1.3 WARNING (Attribute Sanitization)

**Trigger**: A nullable attribute is blank, malformed, out of range, or otherwise cannot be interpreted without rejecting the entire bridge row.

Examples:
- Malformed optional numeric values.
- Malformed optional coordinates.
- Optional code fields outside their documented domains.
- Optional dates with invalid month/year values.

**Action**: Keep the bridge row, set the affected nullable canonical column to `NULL` unless the field-specific mapping preserves the raw code, increment `warnings_count`, and write an `import_issues` row with `severity = 'warning'`.

### 1.4 INFO (Audited Normalization)

**Trigger**: A documented sentinel or precision limit is expected and can be normalized without data loss.

Examples:
- `YEAR_RECONSTRUCTED_106 = '0'` means no reconstruction year and normalizes to `NULL`.
- `ADT_029 = '0'` remains numeric `0`; it is not treated as blank or unknown.
- `YEAR_ADT_030 = '0'` normalizes to `NULL`; it is not replaced with `inventory_year`.
- Condition code `N` means not applicable; it is not numeric zero and not unknown.
- `DATE_OF_INSPECT_090` provides month/year precision only.

**Action**: Store the documented canonical value and include the normalization in importer summary statistics when useful. INFO events do not require `import_issues` rows.

## 2. Nullability Alignment

Database nullability in `database-schema.md` defines whether a normalized value may be absent after validation.

### 2.1 Non-null `bridges` Fields

Each inserted bridge must have these non-null fields after importer and database defaults are applied:
- `id`
- `dataset_id`
- `state_code`
- `structure_number`
- `county_code`
- `year_built`
- `source_row_number`
- `created_at`
- `updated_at`

Invalid source values for `state_code`, `structure_number`, `county_code`, or `year_built` reject the row. Generated fields such as `id`, `created_at`, and `updated_at` are supplied by the importer or database.

### 2.2 Nullable `bridges` Fields

The following bridge attributes may be stored as `NULL` after field-specific normalization:
- `facility_carried`
- `feature_crossed`
- `latitude`
- `longitude`
- `source_latitude_code`
- `source_longitude_code`
- `year_reconstructed`
- `average_daily_traffic`
- `traffic_year`
- `truck_traffic_percent`
- `lanes_on`
- `bridge_length_m`
- `maximum_span_m`
- `owner_code`
- `material_code`
- `design_type_code`
- `inspection_month`
- `inspection_year`
- `deck_condition_code`
- `superstructure_condition_code`
- `substructure_condition_code`
- `culvert_condition_code`
- `overall_condition_code`
- `lowest_condition_rating`

Malformed nullable values produce warnings unless the field mapping identifies the value as an expected sentinel.

### 2.3 Import Metadata Nullability

`import_runs.dataset_id` is nullable because an import can fail before a dataset row is created. `import_runs.finished_at` and `import_runs.failure_message` are nullable because they depend on run lifecycle and outcome.

`import_issues.row_number`, `structure_number`, `field_name`, `raw_value`, and `raw_record` are nullable because some fatal issues are file-level rather than row-level.

## 3. Sentinel and Precision Rules

BridgeScope keeps these cases distinct:
- Blank or whitespace-only values
- Numeric `0`
- Condition code `N`
- Malformed values

There is no blanket string-to-null conversion. Each field follows `field-mapping.md`.

Structure numbers are trimmed only at the outer edges. Leading zeros, letters, and internal spaces are preserved. The normalized candidate key is `(STATE_CODE_001, trimmed STRUCTURE_NUMBER_008)` within a dataset.

Traffic year remains separate from inventory year. If `YEAR_ADT_030` is missing or `0`, `traffic_year` is `NULL`; it is never filled with the dataset `inventory_year`.

Inspection dates retain only month and year. The importer must not fabricate a day or store a synthetic `DATE` such as `2024-05-01`.

Average Daily Traffic is an estimated source metric and must not be presented as live traffic.

Condition classifications and ratings are descriptive FHWA data fields. They must not be presented as standalone safety judgments.

## 4. Import Issues Schema

Warnings, row rejections, and fatal import failures are tracked in `import_issues`, matching `database-schema.md`.

| Column | Type | Description |
|---|---|---|
| `id` | `BIGINT` | Database-generated issue primary key. |
| `import_run_id` | `BIGINT NOT NULL REFERENCES import_runs(id)` | Import run that produced the issue. |
| `severity` | `VARCHAR(16) NOT NULL` | `warning`, `error`, or `fatal`. |
| `row_number` | `INTEGER NULL` | Source row associated with the issue when available. |
| `structure_number` | `VARCHAR(15) NULL` | Structure identifier when available. |
| `field_name` | `TEXT NULL` | Source or canonical field associated with the issue. |
| `error_code` | `VARCHAR(64) NOT NULL` | Stable machine-readable issue identifier. |
| `raw_value` | `TEXT NULL` | Raw value associated with the issue. |
| `message` | `TEXT NOT NULL` | Human-readable explanation of the issue. |
| `raw_record` | `JSONB NULL` | Optional source record snapshot for diagnostics. |
| `created_at` | `TIMESTAMPTZ NOT NULL` | Database-generated creation timestamp. |

## 5. Function Separation Architecture

Normalizers and validators remain decoupled.

Normalizers take raw strings and return typed intermediate values or documented sentinel outcomes. Validators decide whether a normalized result is accepted, warned, rejected, or fatal in the context of a specific field and import run.

This separation keeps field parsing testable without hiding validation behavior inside ad hoc string handling.
