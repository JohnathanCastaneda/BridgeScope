import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

@dataclass
class SelectedRecord:
    row_index: int
    data: dict[str, str]


REQUIRED_FIELDS = [
    "STATE_CODE_001",
    "STRUCTURE_NUMBER_008",
    "FACILITY_CARRIED_007",
    "FEATURES_DESC_006A",
    "YEAR_RECONSTRUCTED_106",
    "ADT_029",
    "YEAR_ADT_030",
    "PERCENT_ADT_TRUCK_109",
    "DECK_COND_058",
    "SUPERSTRUCTURE_COND_059",
    "SUBSTRUCTURE_COND_060",
    "CULVERT_COND_062"
]

# parse_arguments function to handle command-line arguments 
def parse_arguments() -> argparse.Namespace: 
    parser = argparse.ArgumentParser(
        description="Sample CA NBI records"
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to the raw CA NBI data file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to the output sample CSV file.",
    )
    return parser.parse_args()

# read_source function to read the input CSV file and validate required fields
def read_source(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.is_file():
        raise FileNotFoundError(f"Input file not found: {path}")
    
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=",", quotechar="'")
        fieldnames = reader.fieldnames
        
        missing_fields = [field for field in REQUIRED_FIELDS if field not in fieldnames]
        if missing_fields:
            raise KeyError(f"Missing required fields in input file: {', '.join(missing_fields)}")
        
        rows = list(reader)

    return fieldnames, rows

# parse_optional_integer function to convert string to integer or None
def parse_optional_integer(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None

# bridge_key function to create a unique key for each row based on specific fields
def bridge_key(row: dict[str, str]) -> tuple[str, str]:
    return row["STATE_CODE_001"].strip(), row["STRUCTURE_NUMBER_008"].strip()

# select_sample_rows function to select a sample of rows from the input data
def select_sample_rows(
    rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], dict[str, int]]:
    selected_by_key: dict[tuple[str, str], SelectedRecord] = {}
    category_counts: dict[str, int] = {
        "highest ADT": 0,
        "lowest positive ADT": 0,
        "culvert condition records": 0,
        "year reconstructed": 0,
        "unusual structure identifiers": 0,
        "oldest observed ADT": 0,
        "missing optional data": 0,
        "punctuation in description": 0
    }
    
    def add_candidates(candidates: list[dict[str, str]], category_name: str) -> None:
        added = 0
        for index, row in candidates:
            key = bridge_key(row)
            if key not in selected_by_key:
                selected_by_key[key] = SelectedRecord(row_index=index, data=row)
                category_counts[category_name] += 1
                added += 1
            category_counts[category_name] = added
            
    indexed_candidates = list(enumerate(rows))
        
    # Select highest ADT
    valid_adt_candidates = [
        (index, row, adt) for index, row in indexed_candidates
        if (adt := parse_optional_integer(row.get("ADT_029", ""))) is not None
    ]
    sorted_highest_adt = sorted(valid_adt_candidates, key=lambda item: (-item[2], item[0]))[:5]  # Sort by ADT descending, then by index ascending
    add_candidates([(index, row) for index, row, _ in sorted_highest_adt], "highest ADT")
        
    # Select lowest positive ADT
    positive_adt_candidates = [item for item in valid_adt_candidates if item[2] > 0]
    sorted_lowest_positive_adt = sorted(positive_adt_candidates, key=lambda item: (item[2], item[0]))[:5]  # Sort by ADT ascending, then by index ascending
    add_candidates([(index, row) for index, row, _ in sorted_lowest_positive_adt], "lowest positive ADT")
        
    # Select culvert condition records
    culvert_candidates = [
        (index, row)
        for index, row in indexed_candidates
        if (val := row["CULVERT_COND_062"].strip()) and val not in ("N", "") and val.isdigit()][:5]
    add_candidates(culvert_candidates, "culvert condition records")
        
    # Select year reconstructed
    year_reconstructed_candidates = [
        (index, row)
        for index, row in indexed_candidates
        if (year := parse_optional_integer(row["YEAR_RECONSTRUCTED_106"])) is not None and year > 0
    ][:5]
    add_candidates(year_reconstructed_candidates, "year reconstructed")
        
    # Select unusual structure identifiers
    unusual_structure_candidates = [
        (index, row)
        for index, row in indexed_candidates
        if any(not char.isdigit() for char in row.get("STRUCTURE_NUMBER_008", ""))][:5]
    add_candidates(unusual_structure_candidates, "unusual structure identifiers")
        
    # Select oldest observed ADT
    oldest_adt_candidates = [
        (index, row, year)
        for index, row in indexed_candidates
        if (year := parse_optional_integer(row.get("YEAR_ADT_030", ""))) is not None and year > 0
    ]
    sorted_oldest_adt = sorted(oldest_adt_candidates, key=lambda item: (item[2], item[0]))[:5]  # Sort by year ascending, then by index ascending
    add_candidates([(index, row) for index, row, _ in sorted_oldest_adt], "oldest observed ADT")
        
    # Select missing optional data
    missing_optional_data_candidates = [
        (index, row)
        for index, row in indexed_candidates
        if not row.get("PERCENT_ADT_TRUCK_109", "").strip() or not row.get("YEAR_RECONSTRUCTED_106", "").strip()
    ][:5]
    add_candidates(missing_optional_data_candidates, "missing optional data")
        
    # Select punctuation in description
    punctuation_candidates = [
        (index, row)
        for index, row in indexed_candidates
        if any(char in (",", "'") for char in row.get("FEATURES_DESC_006A", "") + row.get("FACILITY_CARRIED_007", "")) 
    ][:5]
    add_candidates(punctuation_candidates, "punctuation in description")
        
    # Enforce sample size
    current_sample_size = list(selected_by_key.values())
    if len(current_sample_size) < 25:
        for index, row in indexed_candidates:
            key = bridge_key(row)
            if key not in selected_by_key:
                selected_by_key[key] = SelectedRecord(row_index=index, data=row)
                if len(selected_by_key) >= 25:
                    break
                    
    sorted_samples = sorted(selected_by_key.values(), key=lambda record: record.row_index)
    if len(sorted_samples) > 40:
        sorted_samples = sorted_samples[:40]
            
    final_sample_rows = [record.data for record in sorted_samples]
    return final_sample_rows, category_counts

def write_sample(
    path: Path,
    fieldnames: list[str],
    rows: list[dict[str, str]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=",", quotechar="'", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

def main() -> None:
    args = parse_arguments()
    fieldnames, rows = read_source(args.input)
    sample_rows, category_counts = select_sample_rows(rows)
    write_sample(args.output, fieldnames, sample_rows)
    
    print(f"Sample records read: {len(rows)}")
    print(f"Unique sample records selected: {len(sample_rows)}\n")
    print("Selection categories:")
    for category, count in category_counts.items():
        print(f"  {category}: {count}")
    print(f"\nOutput: {args.output}")
    
    
if __name__ == "__main__":
    main()
