import hashlib
from pathlib import Path

import pytest

from bridgescope.importer.cli import calculate_sha256, parse_arguments


def test_calculate_sha256_reads_file_bytes(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    payload = b"BridgeScope checksum test\n"
    source.write_bytes(payload)

    assert calculate_sha256(source) == hashlib.sha256(payload).hexdigest()


def test_parse_arguments_accepts_input_path() -> None:
    args = parse_arguments(["--input", "data/raw/CA25.txt"])

    assert args.input == Path("data/raw/CA25.txt")


def test_parse_arguments_requires_input() -> None:
    with pytest.raises(SystemExit) as exc_info:
        parse_arguments([])

    assert exc_info.value.code == 2

