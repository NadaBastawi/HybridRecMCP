"""Validated contracts shared by the API, MCP and interactive demo."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from domain import DISCLAIMER

Season = Literal["winter", "spring", "summer", "fall"]
Region = Literal["tucson", "ohio"]
PropertyType = Literal[
    "residential_house",
    "residential_apartment",
    "commercial_restaurant",
    "commercial_office",
    "commercial_warehouse",
    "mobile_home",
]
TopN = Annotated[int, Field(ge=1, le=10, strict=True)]
Days = Annotated[int, Field(ge=0, le=36500, strict=True)]


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RecommendRequest(RequestModel):
    customer_id: str = Field(pattern=r"^C[0-9]{4,8}$")
    season: Season = "summer"
    days_since_last_service: Days = 180
    top_n: TopN = 5


class NewCustomerRequest(RequestModel):
    property_type: PropertyType
    zip_code: str = Field(pattern=r"^[0-9]{5}$")
    building_age_years: int = Field(ge=0, le=200, strict=True)
    region: Region = "tucson"
    season: Season = "summer"
    days_since_last_service: Days | None = 365
    top_n: TopN = 5


class ServiceRecommendation(BaseModel):
    service_id: str
    service_name: str
    category: str
    price_usd: float = Field(ge=0)
    price_basis: str = "illustrative, not a quote"
    score: float = Field(ge=0, le=1)
    urgency_score: float | None = Field(ge=1, le=10)
    urgency_label: Literal["HIGH", "MEDIUM", "LOW", "UNKNOWN"]
    explanation: str
    follow_up_question: str = ""
    requires_assessment: bool = True


class RecommendResponse(BaseModel):
    customer_id: str | None = None
    customer_type: Literal["existing", "new"]
    profile: dict
    recommendations: list[ServiceRecommendation]
    model_version: str = "2.0.0"
    synthetic_data: bool = True
    disclaimer: str = DISCLAIMER


class Service(BaseModel):
    service_id: str
    service_name: str
    category: str
    price_usd: float
    suitable_residential: bool
    suitable_commercial: bool
    peak_season: str
    price_basis: str = "illustrative, not a quote"


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_version: str
    synthetic_data: bool = True
