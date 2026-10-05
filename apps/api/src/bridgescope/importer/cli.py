import argparse
import hashlib
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from bridgescope.importer.orchestrator import import_dataset
from bridgescope.importer.sources import CALIFORNIA_NBI_2025
from bridgescope.importer.summary import format_import_summary


def calculate_sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m bridgescope.importer",
        description="Import the FHWA 2025 California NBI source into BridgeScope.",
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to the FHWA NBI source file to import.",
    )
    return parser.parse_args(argv)


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr

    args = parse_arguments(argv)
    source_path = args.input

    try:
        source_sha256 = calculate_sha256(source_path)
        request = CALIFORNIA_NBI_2025.to_import_request(
            source_path=source_path,
            source_sha256=source_sha256,
        )
        result = import_dataset(request)
    except Exception as exc:
        print(_format_failure(source_path, exc), file=stderr)
        return 1

    print(format_import_summary(result), file=stdout)
    return 0


def _format_failure(source_path: Path, exc: Exception) -> str:
    return "\n".join(
        [
            "BridgeScope import failed.",
            "",
            f"Source: {source_path.name}",
            f"Reason: {_safe_error_message(exc)}",
            "",
            "Import run status: failed",
        ]
    )


def _safe_error_message(exc: Exception) -> str:
    message = str(exc).splitlines()[0].strip() or exc.__class__.__name__
    message = _redact_url_credentials(message)

    if len(message) > 240:
        return f"{message[:237]}..."

    return message


def _redact_url_credentials(message: str) -> str:
    return re.sub(r"://([^:@/\s]+):([^@/\s]+)@", r"://\1:***@", message)

