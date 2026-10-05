from pydantic import BaseModel

from bridgescope.api.v1.schemas.bridge import BridgeSummary


class BridgePage(BaseModel):
    items: list[BridgeSummary]
    page: int
    page_size: int
    total_items: int
    total_pages: int

