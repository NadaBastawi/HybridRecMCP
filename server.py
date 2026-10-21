"""Official MCP SDK stdio bridge to the authenticated recommendation API."""

import os
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from domain import DISCLAIMER, ROOT
from schemas import (
    Days,
    NewCustomerRequest,
    PropertyType,
    RecommendRequest,
    RecommendResponse,
    Region,
    Season,
    Service,
    TopN,
)


def create_mcp_server(api_base=None, api_key=None, transport=None):
    load_dotenv(ROOT / ".env", override=False)
    base = (api_base or os.getenv("API_BASE", "http://127.0.0.1:8000")).rstrip("/")
    parsed = urlparse(base)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("API_BASE must be a valid HTTP(S) service URL")
    if parsed.scheme == "http" and parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("Remote API_BASE must use HTTPS")
    key = api_key if api_key is not None else os.getenv("API_KEY", "")
    mcp = FastMCP("HybridRecMCP", instructions=DISCLAIMER)

    async def call(method, path, payload=None):
        if len(key) < 16:
            raise ToolError("Configure API_KEY with the same secret used by the API")
        try:
            async with httpx.AsyncClient(
                base_url=base, headers={"X-API-Key": key}, timeout=15, transport=transport
            ) as client:
                response = await client.request(method, path, json=payload)
                response.raise_for_status()
                data = response.json()
                if path == "/services":
                    return [Service.model_validate(item).model_dump() for item in data]
                return RecommendResponse.model_validate(data).model_dump()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            message = {
                401: "API authentication failed",
                404: "Customer not found",
                422: "Invalid recommendation inputs",
            }.get(status, "Recommendation API failed")
            raise ToolError(message) from None
        except httpx.RequestError:
            raise ToolError(
                "Recommendation API is unavailable; check API_BASE and the API process"
            ) from None
        except (ValueError, TypeError):
            raise ToolError("Recommendation API returned an invalid response") from None

    @mcp.tool()
    async def recommend_for_customer(
        customer_id: str,
        season: Season = "summer",
        days_since_last_service: Days = 180,
        top_n: TopN = 5,
    ) -> dict:
        """Suggest services for an existing synthetic customer; scores and prices are demonstrative."""
        payload = RecommendRequest(
            customer_id=customer_id,
            season=season,
            days_since_last_service=days_since_last_service,
            top_n=top_n,
        )
        return await call("POST", "/recommend", payload.model_dump())

    @mcp.tool()
    async def recommend_for_new_customer(
        property_type: PropertyType,
        zip_code: str,
        building_age_years: int,
        season: Season = "summer",
        region: Region = "tucson",
        days_since_last_service: Days | None = 365,
        top_n: TopN = 5,
    ) -> dict:
        """Suggest relevant services for a new property, with separate simulated priority and illustrative prices."""
        payload = NewCustomerRequest(
            property_type=property_type,
            zip_code=zip_code,
            building_age_years=building_age_years,
            season=season,
            region=region,
            days_since_last_service=days_since_last_service,
            top_n=top_n,
        )
        return await call("POST", "/recommend/new-customer", payload.model_dump())

    @mcp.tool()
    async def list_services() -> dict:
        """List the illustrative service catalog, suitability flags and prices; these are not company quotes."""
        return dict(
            services=await call("GET", "/services"), synthetic_data=True, disclaimer=DISCLAIMER
        )

    return mcp


mcp = create_mcp_server()

if __name__ == "__main__":
    mcp.run(transport="stdio")
