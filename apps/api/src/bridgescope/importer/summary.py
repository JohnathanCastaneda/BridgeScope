from collections.abc import Mapping

from bridgescope.importer.orchestrator import ImportResult


def format_import_summary(result: ImportResult) -> str:
    lines: list[str] = ["BridgeScope NBI Import", ""]

    _append_metadata(lines, result)

    if result.status == "skipped_duplicate_file":
        lines.extend(
            [
                f"Status:           {result.status}",
                "",
                "No bridge records were imported because this exact",
                "source file has already been processed.",
                "",
                f"Import run ID:    {result.import_run_id}",
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            f"Rows read:        {_format_number(result.rows_read)}",
            f"Inserted:         {_format_number(result.rows_inserted)}",
            f"Updated:          {_format_number(result.rows_updated)}",
            f"Unchanged:        {_format_number(result.rows_unchanged)}",
            f"Rejected:         {_format_number(result.rows_rejected)}",
            "",
            f"Warnings:         {_format_number(result.warnings_count)}",
            f"Errors:           {_format_number(result.errors_count)}",
        ]
    )

    if result.issue_counts_by_code:
        lines.extend(["", "Issues:", ""])
        lines.extend(_format_issue_counts(result.issue_counts_by_code))

    lines.extend(["", f"Status:           {result.status}"])

    if result.dataset_id is not None:
        lines.append(f"Dataset ID:       {result.dataset_id}")

    lines.append(f"Import run ID:    {result.import_run_id}")

    return "\n".join(lines)


def _append_metadata(lines: list[str], result: ImportResult) -> None:
    if result.source_file_name is not None:
        lines.append(f"Source file:      {result.source_file_name}")

    if result.inventory_year is not None:
        lines.append(f"Inventory year:   {result.inventory_year}")

    if result.state_code is not None:
        if result.state_name is None:
            lines.append(f"State code:       {result.state_code}")
        else:
            lines.append(f"State:            {result.state_name} ({result.state_code})")

    if result.source_sha256 is not None:
        lines.append(f"SHA-256:          {_short_sha256(result.source_sha256)}")

    if len(lines) > 2:
        lines.append("")


def _format_issue_counts(issue_counts_by_code: Mapping[str, int]) -> list[str]:
    max_code_length = max(len(code) for code in issue_counts_by_code)

    return [
        f"  {code:<{max_code_length}}  {_format_number(count)}"
        for code, count in sorted(issue_counts_by_code.items())
    ]


def _format_number(value: int) -> str:
    return f"{value:,}"


def _short_sha256(value: str) -> str:
    if len(value) <= 12:
        return value

    return f"{value[:12]}..."

