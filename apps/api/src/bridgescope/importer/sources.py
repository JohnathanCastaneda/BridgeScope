from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from bridgescope.importer.orchestrator import ImportRequest


@dataclass(frozen=True)
class SourceDefinition:
    provider: str
    state_name: str
    state_code: str
    inventory_year: int
    source_format: str
    source_specification: str
    source_url: str
    retrieved_at: datetime

    def to_import_request(
        self,
        *,
        source_path: Path,
        source_sha256: str,
    ) -> ImportRequest:
        return ImportRequest(
            source_path=source_path,
            provider=self.provider,
            state_code=self.state_code,
            inventory_year=self.inventory_year,
            source_format=self.source_format,
            source_specification=self.source_specification,
            source_url=self.source_url,
            source_file_name=source_path.name,
            source_sha256=source_sha256,
            retrieved_at=self.retrieved_at,
            state_name=self.state_name,
        )


CALIFORNIA_NBI_2025 = SourceDefinition(
    provider="FHWA",
    state_name="California",
    state_code="06",
    inventory_year=2025,
    source_format="fhwa_nbi_legacy_delimited_v2025",
    source_specification="legacy_nbi_export_format",
    source_url="https://www.fhwa.dot.gov/bridge/nbi/2025/delimited/CA25.txt",
    retrieved_at=datetime(2026, 8, 24, 4, 41, 55, tzinfo=timezone.utc),
)

