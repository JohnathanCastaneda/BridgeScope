from pydantic import BaseModel


class HighestAdtItem(BaseModel):
    rank: int

    state_code: str
    structure_number: str

    facility_carried: str | None
    feature_crossed: str | None
    county_code: str | None

    average_daily_traffic: int
    traffic_year: int | None


class HighestAdtRanking(BaseModel):
    items: list[HighestAdtItem]
    limit: int
