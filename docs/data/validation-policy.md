### 1.1 FATAL (Batch Abortion)
* **Trigger**: Source schema violations, unreadable delimiter/quote encodings, or missing mandatory columns defined in `REQUIRED_FIELDS`.
* **Action**: Immediate rollback of the active transaction. No bridges are committed. Process terminates with non-zero exit code.

### 1.2 REJECT_ROW (Record Rejection)
* **Trigger**: Failures in primary entity identity or baseline physical reality:
  - Missing or blank `STRUCTURE_NUMBER_008`
  - Missing or non-`06` `STATE_CODE_001`
  - Missing or invalid `YEAR_BUILT_027` (missing, non-numeric, or $< 1800$)
  - Duplicate `(dataset_id, state_code, structure_number)` with conflicting metadata
* **Action**: Discard the record from persistence. Increment `rejected_records_count`. Write a structured entry to `import_issues` detailing the exact raw row and rejection reason.

### 1.3 WARNING (Attribute Sanitization)
* **Trigger**: Optional or secondary metrics contain syntactically invalid data, sentinel representations, or out-of-range numbers.
* **Action**: The bridge record is retained and stored. The offending attribute is normalized to `NULL` (or preserved verbatim in raw code columns). Increment `warning_count` and write an issue record to `import_issues`.

### 1.4 INFO (Audited Normalization)
* **Trigger**: Expected domain sentinels that represent distinct business logic (e.g., `YEAR_RECONSTRUCTED_106 = '0'`, `ADT_029 = '0'`).
* **Action**: Value is canonically represented without discarding the record. Recorded in the import execution log for verification.

---

## 2. Provenance and Issues Schema (`import_issues`)

All warnings and rejections are tracked in a dedicated audit table:

| Column | Type | Description |
|---|---|---|
| `issue_id` | `BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY` | Unique issue surrogate key. |
| `dataset_id` | `INTEGER NOT NULL REFERENCES datasets(dataset_id)` | Foreign key to imported dataset run. |
| `structure_number`| `VARCHAR(15) NULL` | Structure identifier (if identifiable). |
| `severity` | `VARCHAR(10) NOT NULL` | `'REJECT'` or `'WARNING'`. |
| `field_name` | `VARCHAR(50) NOT NULL` | Name of the source field causing the issue. |
| `raw_value` | `TEXT NULL` | Raw value extracted from source file. |
| `message` | `TEXT NOT NULL` | Human-readable explanation of failure/sanitization. |

---

## 3. Function Separation Architecture

To prevent intertwined, untestable ingestion logic, normalizers and validators remain strictly decoupled.

### 3.1 Normalization Signatures
Normalizers take raw string inputs and return typed intermediate structures without raising domain validation exceptions: