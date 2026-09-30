#!/usr/bin/env python3
import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

REQUIRED_FIELDS = [
    "STATE_CODE_001",
    "STRUCTURE_NUMBER_008",
    "FACILITY_CARRIED_007",
    "FEATURES_DESC_006A",
    "COUNTY_CODE_003",
    "LAT_016",
    "LONG_017",
    "YEAR_BUILT_027",
    "YEAR_RECONSTRUCTED_106",
    "ADT_029",
    "YEAR_ADT_030",
    "PERCENT_ADT_TRUCK_109",
    "TRAFFIC_LANES_ON_028A",
    "STRUCTURE_LEN_MT_049",
    "MAX_SPAN_LEN_MT_048",
    "OWNER_022",
    "STRUCTURE_KIND_043A",
    "STRUCTURE_TYPE_043B",
    "DATE_OF_INSPECT_090",
    "DECK_COND_058",
    "SUPERSTRUCTURE_COND_059",
    "SUBSTRUCTURE_COND_060",
    "CULVERT_COND_062",
    "BRIDGE_CONDITION",
    "LOWEST_RATING",
]

NUMERIC_FIELDS = [
    "YEAR_BUILT_027",
    "YEAR_RECONSTRUCTED_106",
    "ADT_029",
    "YEAR_ADT_030",
    "PERCENT_ADT_TRUCK_109",
    "TRAFFIC_LANES_ON_028A",
    "STRUCTURE_LEN_MT_049",
    "MAX_SPAN_LEN_MT_048",
    "LOWEST_RATING",
]

CODE_FIELDS = [
    "STATE_CODE_001",
    "COUNTY_CODE_003",
    "OWNER_022",
    "STRUCTURE_KIND_043A",
    "STRUCTURE_TYPE_043B",
    "DECK_COND_058",
    "SUPERSTRUCTURE_COND_059",
    "SUBSTRUCTURE_COND_060",
    "CULVERT_COND_062",
    "BRIDGE_CONDITION",
]

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Profile NBI CSV data.")
    parser.add_argument("--input", type=Path, required=True, help="Path to raw NBI text/CSV file.")
    parser.add_argument("--output", type=Path, required=True, help="Path to write the Markdown report.")
    return parser.parse_args()

def validate_headers(headers: list[str]) -> None:
    missing = [f for f in REQUIRED_FIELDS if f not in headers]
    if missing:
        print("Missing required fields:")
        for f in missing:
            print(f"- {f}")
        sys.exit(1)

def parse_optional_number(value: str) -> float | None:
    v = value.strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None

def read_source(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=",", quotechar="'")
        try:
            headers = next(reader)
        except StopIteration:
            print("Error: File is empty.")
            sys.exit(1)
        
        validate_headers(headers)
        
        rows = []
        for row in reader:
            rows.append(dict(zip(headers, row)))
        
        return headers, rows

def profile_basic(headers: list[str], rows: list[dict[str, str]]) -> dict:
    unexpected_field_counts = sum(1 for r in rows if len(r) != len(headers))
    empty_structures = sum(1 for r in rows if not r.get("STRUCTURE_NUMBER_008", "").strip())
    non_ca_state = sum(1 for r in rows if r.get("STATE_CODE_001", "").strip() != "06")
    
    header_counts = Counter(headers)
    duplicates = [h for h, c in header_counts.items() if c > 1]
    
    return {
        "records": len(rows),
        "columns": len(headers),
        "missing_required_columns": 0,
        "duplicate_headers": len(duplicates),
        "unexpected_field_counts": unexpected_field_counts,
        "empty_structure_numbers": empty_structures,
        "state_code_not_06": non_ca_state
    }

def profile_candidate_keys(rows: list[dict[str, str]]) -> dict:
    seen = Counter()
    for row in rows:
        state = row.get("STATE_CODE_001", "").strip()
        struct = row.get("STRUCTURE_NUMBER_008", "").strip()
        seen[(state, struct)] += 1
    
    duplicates = {k: v for k, v in seen.items() if v > 1}
    
    return {
        "unique_keys": len(seen),
        "duplicate_keys": len(duplicates),
        "duplicate_examples": sorted(list(duplicates.keys()))[:5],
        "empty_structure_numbers": sum(1 for k in seen.keys() if not k[1])
    }

def profile_missing_values(rows: list[dict[str, str]]) -> list[dict]:
    stats = []
    for field in REQUIRED_FIELDS:
        counts = {"blank": 0, "whitespace": 0, "zero": 0, "n": 0}
        for row in rows:
            val = row.get(field, "")
            if val == "":
                counts["blank"] += 1
            elif val.isspace():
                counts["whitespace"] += 1
            elif val == "0":
                counts["zero"] += 1
            elif val == "N":
                counts["n"] += 1
        stats.append({"field": field, **counts})
    return stats

def profile_codes(rows: list[dict[str, str]]) -> dict:
    stats = {}
    for field in CODE_FIELDS:
        counts = Counter(row.get(field, "") for row in rows)
        stats[field] = sorted(counts.items())
    return stats

def profile_numerics(rows: list[dict[str, str]]) -> dict:
    stats = {}
    for field in NUMERIC_FIELDS:
        valid_count = 0
        zero_count = 0
        malformed = 0
        min_val = float('inf')
        max_val = float('-inf')
        
        for row in rows:
            raw = row.get(field, "")
            stripped = raw.strip()
            
            if stripped == "":
                continue
                
            num = parse_optional_number(raw)
            if num is None:
                malformed += 1
            else:
                valid_count += 1
                if num == 0:
                    zero_count += 1
                min_val = min(min_val, num)
                max_val = max(max_val, num)
                
        stats[field] = {
            "valid": valid_count,
            "min": min_val if valid_count > 0 else None,
            "max": max_val if valid_count > 0 else None,
            "zeros": zero_count,
            "malformed": malformed
        }
    return stats

def profile_years(rows: list[dict[str, str]]) -> dict:
    recon_before_build = 0
    for row in rows:
        build_str = row.get("YEAR_BUILT_027", "")
        recon_str = row.get("YEAR_RECONSTRUCTED_106", "")
        
        b = parse_optional_number(build_str)
        r = parse_optional_number(recon_str)
        
        if b is not None and r is not None and r > 0 and r < b:
            recon_before_build += 1
            
    return {"recon_before_build": recon_before_build}

def profile_inspection_dates(rows: list[dict[str, str]]) -> dict:
    counts = Counter()
    non_numeric = 0
    
    for row in rows:
        val = row.get("DATE_OF_INSPECT_090", "")
        if not val:
            counts["blank"] += 1
        else:
            if not val.isdigit():
                non_numeric += 1
            counts[f"length_{len(val)}"] += 1
            
    return {
        "blank": counts["blank"],
        "length_3": counts["length_3"],
        "length_4": counts["length_4"],
        "other_lengths": sum(v for k, v in counts.items() if k not in ("blank", "length_3", "length_4")),
        "non_numeric": non_numeric
    }

def profile_coordinates(rows: list[dict[str, str]]) -> dict:
    stats = {}
    for field in ["LAT_016", "LONG_017"]:
        blank = 0
        zero_only = 0
        lengths = Counter()
        non_digit = 0
        min_val = float('inf')
        max_val = float('-inf')
        
        for row in rows:
            val = row.get(field, "")
            if not val:
                blank += 1
                continue
            
            lengths[len(val)] += 1
            
            if not val.isdigit():
                non_digit += 1
            
            if set(val) == {'0'}:
                zero_only += 1
                
            num = parse_optional_number(val)
            if num is not None:
                min_val = min(min_val, num)
                max_val = max(max_val, num)
                
        stats[field] = {
            "blank": blank,
            "zero_only": zero_only,
            "lengths": sorted(lengths.items()),
            "non_digit": non_digit,
            "min": min_val if min_val != float('inf') else None,
            "max": max_val if max_val != float('-inf') else None
        }
    return stats

def profile_structure_numbers(rows: list[dict[str, str]]) -> dict:
    letters, spaces, non_digits, lead_zeros = [], [], [], []
    
    for row in rows:
        # Strip outer fixed-width whitespace padding before inspecting internal characteristics
        struct = row.get("STRUCTURE_NUMBER_008", "").strip()
        if not struct:
            continue

        if any(c.isalpha() for c in struct) and len(letters) < 5:
            letters.append(struct)
        if " " in struct and len(spaces) < 5:
            spaces.append(struct)
        if not struct.isdigit() and len(non_digits) < 5:
            non_digits.append(struct)
        if struct.startswith("0") and len(lead_zeros) < 5:
            lead_zeros.append(struct)
            
    # Count totals
    total_letters = sum(1 for r in rows if any(c.isalpha() for c in r.get("STRUCTURE_NUMBER_008", "").strip()))
    total_spaces = sum(1 for r in rows if " " in r.get("STRUCTURE_NUMBER_008", "").strip())
    total_non_digits = sum(1 for r in rows if not r.get("STRUCTURE_NUMBER_008", "").strip().isdigit() and r.get("STRUCTURE_NUMBER_008", "").strip())
    total_lead_zeros = sum(1 for r in rows if r.get("STRUCTURE_NUMBER_008", "").strip().startswith("0"))
    
    return {
        "letters": (total_letters, letters),
        "spaces": (total_spaces, spaces),
        "non_digits": (total_non_digits, non_digits),
        "leading_zeros": (total_lead_zeros, lead_zeros),
    }

def profile_traffic_years(rows: list[dict[str, str]]) -> list[tuple[str, int]]:
    counts = Counter(row.get("YEAR_ADT_030", "").strip() for row in rows)
    return sorted(counts.items(), key=lambda x: (x[0] == "", x[0]), reverse=True)

def render_markdown(profile: dict) -> str:
    md = ["# NBI Data Profile\n"]
    
    # Basic
    b = profile["basic"]
    md.append("## File summary\n")
    md.append(f"- Records: {b['records']:,}")
    md.append(f"- Columns: {b['columns']:,}")
    md.append(f"- Missing required columns: {b['missing_required_columns']:,}")
    md.append(f"- Duplicate header names: {b['duplicate_headers']:,}")
    md.append(f"- Rows with unexpected field counts: {b['unexpected_field_counts']:,}")
    md.append(f"- Empty structure numbers: {b['empty_structure_numbers']:,}")
    md.append(f"- State code not 06: {b['state_code_not_06']:,}\n")
    
    # Keys
    k = profile["keys"]
    md.append("## Candidate key\n")
    md.append("Candidate key: `(STATE_CODE_001, trimmed STRUCTURE_NUMBER_008)`\n")
    md.append(f"- Unique keys: {k['unique_keys']:,}")
    md.append(f"- Duplicate keys: {k['duplicate_keys']:,}")
    md.append(f"- Empty structure numbers: {k['empty_structure_numbers']:,}")
    if k['duplicate_examples']:
        md.append("\nDuplicate examples:")
        for ex in k['duplicate_examples']:
            md.append(f"  - {ex}")
    md.append("\n")
    
    # Missing
    md.append("## Missing values (MVP fields)\n")
    md.append("| Field | Blank | Whitespace only | \"0\" | \"N\" |")
    md.append("|---|---:|---:|---:|---:|")
    for m in profile["missing"]:
        md.append(f"| {m['field']} | {m['blank']:,} | {m['whitespace']:,} | {m['zero']:,} | {m['n']:,} |")
    md.append("\n")
    
    # Codes
    md.append("## Coded fields\n")
    for field, counts in profile["codes"].items():
        md.append(f"### {field}\n")
        md.append("| Value | Count |")
        md.append("|---|---:|")
        for val, count in counts:
            display_val = val if val else "*(blank)*"
            md.append(f"| `{display_val}` | {count:,} |")
        md.append("\n")
    
    # Numerics
    md.append("## Numeric fields\n")
    total_malformed = 0
    for field, stats in profile["numerics"].items():
        total_malformed += stats['malformed']
        md.append(f"### {field}\n")
        md.append(f"- Valid numeric values: {stats['valid']:,}")
        md.append(f"- Minimum: {stats['min']}")
        md.append(f"- Maximum: {stats['max']}")
        md.append(f"- Zero values: {stats['zeros']:,}")
        md.append(f"- Malformed values: {stats['malformed']:,}\n")
    
    md.append(f"**Total malformed numerics across fields:** {total_malformed:,}\n")
    md.append(f"**Reconstruction years earlier than build years:** {profile['years']['recon_before_build']:,}\n")
    
    # Inspection
    i = profile["inspection"]
    md.append("## Inspection dates (DATE_OF_INSPECT_090)\n")
    md.append(f"- Blank: {i['blank']:,}")
    md.append(f"- Length 3: {i['length_3']:,}")
    md.append(f"- Length 4: {i['length_4']:,}")
    md.append(f"- Other lengths: {i['other_lengths']:,}")
    md.append(f"- Non-numeric values: {i['non_numeric']:,}\n")
    
    # Coordinates
    md.append("## Coordinates\n")
    for field, stats in profile["coords"].items():
        md.append(f"### {field}\n")
        md.append(f"- Blank: {stats['blank']:,}")
        md.append(f"- Zero-only values: {stats['zero_only']:,}")
        md.append(f"- Non-digit values: {stats['non_digit']:,}")
        md.append(f"- Min raw numeric: {stats['min']}")
        md.append(f"- Max raw numeric: {stats['max']}")
        
        md.append("- Distinct string lengths:")
        for length, count in stats['lengths']:
            md.append(f"  - Length {length}: {count:,}")
        md.append("\n")
        
    # Structure numbers
    sn = profile["structures"]
    md.append("## Structure number characteristics\n")
    
    md.append(f"- Contains letters: {sn['letters'][0]:,}")
    for ex in sn['letters'][1]:
        md.append(f"  - `{ex}`")
        
    md.append(f"- Contains internal spaces: {sn['spaces'][0]:,}")
    for ex in sn['spaces'][1]:
        md.append(f"  - `{ex}`")
        
    md.append(f"- Contains non-digit characters: {sn['non_digits'][0]:,}")
    for ex in sn['non_digits'][1]:
        md.append(f"  - `{ex}`")
        
    md.append(f"- Begins with zero: {sn['leading_zeros'][0]:,}")
    for ex in sn['leading_zeros'][1]:
        md.append(f"  - `{ex}`")
    md.append("\n")
    
    # Traffic Years
    md.append("## Traffic measurement years (YEAR_ADT_030)\n")
    md.append("| Year | Records |")
    md.append("|---:|---:|")
    for yr, count in profile["traffic"]:
        display_yr = yr if yr else "*(blank)*"
        md.append(f"| {display_yr} | {count:,} |")
    md.append("\n")
    
    return "\n".join(md)

def main() -> None:
    args = parse_arguments()
    
    # Prepare output dir
    args.output.parent.mkdir(parents=True, exist_ok=True)
    
    headers, rows = read_source(args.input)
    
    profile = {
        "basic": profile_basic(headers, rows),
        "keys": profile_candidate_keys(rows),
        "missing": profile_missing_values(rows),
        "codes": profile_codes(rows),
        "numerics": profile_numerics(rows),
        "years": profile_years(rows),
        "inspection": profile_inspection_dates(rows),
        "coords": profile_coordinates(rows),
        "structures": profile_structure_numbers(rows),
        "traffic": profile_traffic_years(rows),
    }
    
    md_content = render_markdown(profile)
    args.output.write_text(md_content, encoding="utf-8")
    
    # Calculate malformed sum for console output
    malformed_num = sum(s['malformed'] for s in profile['numerics'].values())
    
    print("Profile complete.\n")
    print(f"Records: {profile['basic']['records']}")
    print(f"Columns: {profile['basic']['columns']}")
    print(f"Duplicate candidate keys: {profile['keys']['duplicate_keys']}")
    print(f"Malformed numeric values: {malformed_num}\n")
    print(f"Report written to:\n{args.output}")

if __name__ == "__main__":
    main()