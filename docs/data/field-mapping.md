# FHWA NBI Field Mapping Specification

This document defines the transformation rules from raw FHWA NBI fields to BridgeScope canonical fields.

## Core Principles
1. **Preserve Identity Verbatim**: Primary identifiers retain all internal formatting, characters, and leading zeros.
2. **Explicit Distinction**: `Blank != "0" != "N"`. Semantics are handled on a per-field basis rather than using blanket string-to-null transforms.
3. **No Synthetic Granularity**: If a component does not exist in the source (e.g., day of inspection), it is not fabricated.
4. **Unit Clarity**: Metric values from the source are preserved alongside explicit column naming; unit conversions for the presentation tier are kept out of raw ingestion.

---

## Field Mapping Matrix

| Source Field | Canonical Field | DB Type | Normalization | Missing / Sentinel Behavior | Notes |
|---|---|---|---|---|---|
| `STATE_CODE_001` | `state_code` | `CHAR(2)` | Trim outer whitespace. | **Fatal rejection** if blank/missing. | California is `'06'`. Preserve leading zero. |
| `STRUCTURE_NUMBER_008` | `structure_number` | `VARCHAR(15)` | Trim outer whitespace only. Preserve internal spaces. | **Fatal rejection** if blank/missing. | Natural identifier component. Never cast to integer. |
| `FACILITY_CARRIED_007` | `facility_carried` | `TEXT` | Trim outer whitespace. Collapse internal multi-spaces to single space. | Store empty string as `NULL`. | Street, route, or feature carried by structure. |
| `FEATURES_DESC_006A` | `feature_crossed` | `TEXT` | Trim outer whitespace. Collapse internal multi-spaces. | Store empty string as `NULL`. | Feature crossed (waterway, railroad, highway). |
| `COUNTY_CODE_003` | `county_code` | `CHAR(3)` | Trim outer whitespace. Pad with leading zero if length is 1 or 2 (e.g., `'1'` → `'001'`). | **Fatal rejection** if blank/missing. | 3-digit FIPS county code. Matches Census FIPS standard. |
| `LAT_016` | `latitude` | `NUMERIC(9, 6)` | Parse DMS format `DDMMSSSS` → Decimal Degrees: $DD + \frac{MM}{60} + \frac{SSSS / 100}{3600}$. Round to 6 decimals. | Store as `NULL` if raw string is entirely zero or blank. | Target range for CA: $32.5^\circ \le \text{lat} \le 42.1^\circ$. |
| `LAT_016` | `source_latitude_code` | `CHAR(8)` | Trim outer whitespace and preserve the packed source code. | Store as `NULL` if raw string is entirely zero or blank. | Auditable original latitude value. |
| `LONG_017` | `longitude` | `NUMERIC(10, 6)` | Parse DMS format `DDDMMSSSS` → Decimal Degrees: $-(DDD + \frac{MM}{60} + \frac{SSSS / 100}{3600})$. Round to 6 decimals. | Store as `NULL` if raw string is entirely zero or blank. | Raw longitudes omit negative sign; importer must negate for Western Hemisphere (CA: $-124.5^\circ \le \text{lon} \le -114.1^\circ$). |
| `LONG_017` | `source_longitude_code` | `CHAR(9)` | Trim outer whitespace and preserve the packed source code. | Store as `NULL` if raw string is entirely zero or blank. | Auditable original longitude value. |
| `YEAR_BUILT_027` | `year_built` | `SMALLINT` | Trim outer whitespace. Parse 4-digit integer. | **Fatal rejection** if blank, non-numeric, or `0`. | Baseline age attribute. Must be $\le \text{inventory\_year}$. |
| `YEAR_RECONSTRUCTED_106` | `year_reconstructed` | `SMALLINT` | Trim outer whitespace. Parse 4-digit integer. | Raw `'0'` and blank `""` normalize to `NULL`. | `'0'` denotes "no reconstruction," not year 0. Must be $\ge \text{year\_built}$ when present. |
| `ADT_029` | `average_daily_traffic` | `INTEGER` | Trim outer whitespace. Parse integer. | Raw `'0'` is retained as `0` (represents zero or pedestrian-only traffic), but flagged in validation if motor vehicle route. Blank → `NULL`. | Estimated, non-live metric. |
| `YEAR_ADT_030` | `traffic_year` | `SMALLINT` | Trim outer whitespace. Parse 4-digit integer. | Raw `'0'` or blank `""` normalizes to `NULL`. | Indicates traffic vintage. Do not default to dataset inventory year. |
| `PERCENT_ADT_TRUCK_109` | `truck_traffic_percent` | `NUMERIC(5, 2)` | Trim outer whitespace. Parse integer percentage ($0\text{--}99$). | Blank `""` → `NULL`. Raw `'0'` is stored as `0%`. | Profile shows 963 blanks and 1,063 zeros; both are structurally distinct. |
| `TRAFFIC_LANES_ON_028A` | `lanes_on` | `SMALLINT` | Trim outer whitespace. Parse 2-digit integer. | Blank `""` → `NULL`. | Number of traffic lanes carried on structure. |
| `STRUCTURE_LEN_MT_049` | `bridge_length_m` | `NUMERIC(10, 2)` | Trim outer whitespace. Parse float divided by 10 (e.g., `'000123'` → `12.3`). | Blank or all zeros → `NULL`. | Official total bridge length. |
| `MAX_SPAN_LEN_MT_048` | `maximum_span_m` | `NUMERIC(10, 2)` | Trim outer whitespace. Parse float divided by 10. | Blank or all zeros → `NULL`. | Longest single span length. |
| `OWNER_022` | `owner_code` | `VARCHAR(4)` | Trim outer whitespace. Preserve leading zeros (e.g., `'01'`). | Blank `""` → `NULL`. | 2-digit agency ownership classification code. |
| `STRUCTURE_KIND_043A` | `material_code` | `VARCHAR(4)` | Trim outer whitespace. Single alphanumeric char. | Blank `""` → `NULL`. | Main span material type (concrete, steel, timber, etc.). |
| `STRUCTURE_TYPE_043B` | `design_type_code` | `VARCHAR(4)` | Trim outer whitespace. 2-digit design code. | Blank `""` → `NULL`. | Structural design type (stringer, truss, arch, box culvert). |
| `DATE_OF_INSPECT_090` | `inspection_month`, `inspection_year` | `SMALLINT`, `SMALLINT` | Parse `MYY` (len 3) or `MMYY` (len 4). Expand 2-digit year using cutoff (e.g., $\le 50 \to 20\text{YY}$, $> 50 \to 19\text{YY}$). | Blank `""` → both set to `NULL`. | No day exists; do not fabricate `DATE` or `TIMESTAMP`. |
| `DECK_COND_058` | `deck_condition_code` | `CHAR(1)` | Trim outer whitespace. Must be `'0'`–`'9'` or `'N'`. | Blank `""` → `NULL`. | `'N'` signifies not applicable (e.g., culverts). |
| `SUPERSTRUCTURE_COND_059` | `superstructure_condition_code` | `CHAR(1)` | Trim outer whitespace. Must be `'0'`–`'9'` or `'N'`. | Blank `""` → `NULL`. | `'N'` signifies not applicable. |
| `SUBSTRUCTURE_COND_060` | `substructure_condition_code` | `CHAR(1)` | Trim outer whitespace. Must be `'0'`–`'9'` or `'N'`. | Blank `""` → `NULL`. | `'N'` signifies not applicable. |
| `CULVERT_COND_062` | `culvert_condition_code` | `CHAR(1)` | Trim outer whitespace. Must be `'0'`–`'9'` or `'N'`. | Blank `""` → `NULL`. | For standard bridges, this is expected to be `'N'`. |
| `BRIDGE_CONDITION` | `overall_condition_code` | `CHAR(1)` | Trim outer whitespace. Validated domain: `{'G', 'F', 'P'}`. | Blank or unmapped values normalize to `NULL` with a warning. | FHWA high-level classification: Good, Fair, Poor. Not a safety judgment. |
| `LOWEST_RATING` | `lowest_condition_rating` | `SMALLINT` | Trim outer whitespace. Parse integer (`0`–`9`). | Blank or `'N'` → `NULL`. | Summary rating representing the minimum of items 58, 59, 60, and 62. |

---

## Database Field Coverage

The source-derived `bridges` columns are covered by the mapping matrix above. Generated, provenance, and importer-operational fields are derived as follows so every database column in `database-schema.md` has an explicit origin.

### bridge_datasets

| DB Field | Source or Derivation |
|---|---|
| `id` | Database-generated primary key. |
| `provider` | Source manifest provider, initially `FHWA`. |
| `state_code` | Source manifest state code, matching `STATE_CODE_001`. |
| `inventory_year` | Source manifest inventory year, not inferred from traffic or inspection years. |
| `source_format` | Source manifest source format. |
| `source_specification` | Source manifest source specification. |
| `source_url` | Source manifest direct file URL. |
| `source_file_name` | Source manifest source file name. |
| `source_sha256` | SHA-256 checksum recorded in the source manifest. |
| `retrieved_at` | Retrieval timestamp recorded in the source manifest. |
| `is_active` | Importer or operator flag that selects the dataset exposed by the API. |
| `created_at` | Database-generated creation timestamp. |

### bridges

| DB Field | Source or Derivation |
|---|---|
| `id` | Database-generated primary key. |
| `dataset_id` | Foreign key to the `bridge_datasets` row for the imported source file. |
| `state_code` | `STATE_CODE_001`. |
| `structure_number` | `STRUCTURE_NUMBER_008`. |
| `county_code` | `COUNTY_CODE_003`. |
| `facility_carried` | `FACILITY_CARRIED_007`. |
| `feature_crossed` | `FEATURES_DESC_006A`. |
| `latitude` | Parsed from `LAT_016`. |
| `longitude` | Parsed from `LONG_017`. |
| `source_latitude_code` | Preserved from `LAT_016`. |
| `source_longitude_code` | Preserved from `LONG_017`. |
| `year_built` | `YEAR_BUILT_027`. |
| `year_reconstructed` | `YEAR_RECONSTRUCTED_106`. |
| `average_daily_traffic` | `ADT_029`; estimated, not live traffic. |
| `traffic_year` | `YEAR_ADT_030`; never defaulted from `inventory_year`. |
| `truck_traffic_percent` | `PERCENT_ADT_TRUCK_109`. |
| `lanes_on` | `TRAFFIC_LANES_ON_028A`. |
| `bridge_length_m` | `STRUCTURE_LEN_MT_049`. |
| `maximum_span_m` | `MAX_SPAN_LEN_MT_048`. |
| `owner_code` | `OWNER_022`. |
| `material_code` | `STRUCTURE_KIND_043A`. |
| `design_type_code` | `STRUCTURE_TYPE_043B`. |
| `inspection_month` | Month parsed from `DATE_OF_INSPECT_090`. |
| `inspection_year` | Year parsed from `DATE_OF_INSPECT_090`. |
| `deck_condition_code` | `DECK_COND_058`. |
| `superstructure_condition_code` | `SUPERSTRUCTURE_COND_059`. |
| `substructure_condition_code` | `SUBSTRUCTURE_COND_060`. |
| `culvert_condition_code` | `CULVERT_COND_062`. |
| `overall_condition_code` | `BRIDGE_CONDITION`. |
| `lowest_condition_rating` | `LOWEST_RATING`. |
| `source_row_number` | One-based logical data row number from the source file, excluding the header. |
| `created_at` | Database-generated creation timestamp. |
| `updated_at` | Database-maintained modification timestamp. |

### import_runs

| DB Field | Source or Derivation |
|---|---|
| `id` | Database-generated primary key. |
| `dataset_id` | Nullable foreign key to `bridge_datasets` when a dataset row exists. |
| `source_file_name` | Source manifest or importer input file name. |
| `source_sha256` | SHA-256 checksum of the importer input file. |
| `status` | Importer execution status. |
| `started_at` | Importer execution start timestamp. |
| `finished_at` | Importer execution completion timestamp, when available. |
| `rows_read` | Importer counter. |
| `rows_inserted` | Importer counter. |
| `rows_updated` | Importer counter. |
| `rows_unchanged` | Importer counter. |
| `rows_rejected` | Importer counter. |
| `warnings_count` | Importer counter. |
| `errors_count` | Importer counter. |
| `summary` | Importer-generated JSON summary. |
| `failure_message` | Importer failure detail, when applicable. |

### import_issues

| DB Field | Source or Derivation |
|---|---|
| `id` | Database-generated primary key. |
| `import_run_id` | Foreign key to the `import_runs` row that produced the issue. |
| `severity` | Importer severity: `warning`, `error`, or `fatal`. |
| `row_number` | Source row number when the issue is row-specific. |
| `structure_number` | `STRUCTURE_NUMBER_008`, when identifiable. |
| `field_name` | Source or canonical field associated with the issue. |
| `error_code` | Stable importer-generated machine-readable code. |
| `raw_value` | Raw value associated with the issue. |
| `message` | Human-readable issue description. |
| `raw_record` | Original source record as JSON, when useful for diagnostics. |
| `created_at` | Database-generated creation timestamp. |
