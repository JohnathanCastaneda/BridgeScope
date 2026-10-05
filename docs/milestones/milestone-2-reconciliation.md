# Milestone 2 — Import Reconciliation

## Source

- Provider:
- Inventory year:
- State:
- Source filename:
- SHA-256:
- Source records:

## Import Result

- Status:
- Rows read:
- Rows inserted:
- Rows rejected:
- Warnings:
- Errors:

## Reconciliation Checks

| Check | Source | PostgreSQL | Result |
|---|---:|---:|---|
| Record count | 25,975 | ... | PASS |
| Unique bridge identities | 25,975 | ... | PASS |
| Minimum year built | 1860 | ... | PASS |
| Maximum year built | 2025 | ... | PASS |
| Maximum ADT | 550,000 | ... | PASS |
| Overall G | 12,239 | ... | PASS |
| Overall F | 12,452 | ... | PASS |
| Overall P | 1,284 | ... | PASS |

## Normalization Reconciliation

Document intentional differences between raw source values and
database values.

Examples:

- Reconstruction year `0` → NULL
- Traffic year `0` → NULL
- Outer structure-number whitespace removed
- Internal structure-number whitespace preserved
- N condition values preserved
- Packed coordinates converted to decimal coordinates
- Inspection values converted to month/year without inventing a day

## Duplicate Import Verification

- Dataset count before second import:
- Dataset count after second import:
- Bridge count before:
- Bridge count after:
- Second run status:

## Conclusion

The BridgeScope importer successfully reproduces the expected
California 2025 bridge dataset according to the documented
normalization and validation policies.