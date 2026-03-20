"""
Yandex Direct API v5 — service wrapper for campaign management.
API docs: https://yandex.ru/dev/direct/doc/ref-v5/concepts/about.html
"""
import logging
import httpx
from typing import Optional
from datetime import datetime, timedelta

logger = logging.getLogger("bidroute.yandex_direct")

API_URL = "https://api.direct.yandex.com/json/v5/"
SANDBOX_URL = "https://api-sandbox.direct.yandex.com/json/v5/"

# Use sandbox for testing, production for real campaigns
USE_SANDBOX = False


class YandexDirectClient:
    """Wrapper around Yandex Direct API v5."""

    def __init__(self, oauth_token: str, client_login: str = ""):
        self.token = oauth_token
        self.login = client_login
        self.base_url = SANDBOX_URL if USE_SANDBOX else API_URL

    def _headers(self):
        h = {
            "Authorization": f"Bearer {self.token}",
            "Accept-Language": "ru",
            "Content-Type": "application/json; charset=utf-8",
        }
        if self.login:
            h["Client-Login"] = self.login
        return h

    async def _request(self, service: str, method: str, params: dict) -> dict:
        """Make a request to Yandex Direct API."""
        url = f"{self.base_url}{service}"
        body = {"method": method, "params": params}

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=body, headers=self._headers())
            data = resp.json()

        if "error" in data:
            err = data["error"]
            logger.error(f"YD API error: [{err.get('error_code')}] {err.get('error_string')} — {err.get('error_detail')}")
            raise Exception(f"Yandex Direct: {err.get('error_string', 'Unknown error')}")

        return data.get("result", {})

    # ── Campaigns ──

    async def get_campaigns(self) -> list[dict]:
        """Get all campaigns with basic stats."""
        result = await self._request("campaigns", "get", {
            "SelectionCriteria": {},
            "FieldNames": [
                "Id", "Name", "Status", "State", "StatusPayment",
                "DailyBudget", "StartDate", "Statistics",
            ],
        })
        campaigns = result.get("Campaigns", [])
        return [
            {
                "id": c["Id"],
                "name": c["Name"],
                "status": c.get("Status", ""),
                "state": c.get("State", ""),
                "daily_budget": c.get("DailyBudget", {}).get("Amount", 0) / 1_000_000,
                "impressions": c.get("Statistics", {}).get("Impressions", 0),
                "clicks": c.get("Statistics", {}).get("Clicks", 0),
                "cost": c.get("Statistics", {}).get("Clicks", 0) * 0,  # Stats from reports
            }
            for c in campaigns
        ]

    async def create_campaign(
        self, name: str, daily_budget: float = 300.0,
        keywords: list[str] = None, regions: list[int] = None,
    ) -> dict:
        """Create a new text campaign in Yandex Direct."""
        if not regions:
            regions = [225]  # 225 = Russia

        budget_micros = int(daily_budget * 1_000_000)

        result = await self._request("campaigns", "add", {
            "Campaigns": [{
                "Name": name,
                "StartDate": datetime.utcnow().strftime("%Y-%m-%d"),
                "DailyBudget": {
                    "Amount": budget_micros,
                    "Mode": "STANDARD",
                },
                "NegativeKeywords": {"Items": ["бесплатно", "скачать", "реферат"]},
                "TextCampaign": {
                    "BiddingStrategy": {
                        "Search": {
                            "BiddingStrategyType": "HIGHEST_POSITION",
                        },
                        "Network": {
                            "BiddingStrategyType": "SERVING_OFF",
                        },
                    },
                    "Settings": [
                        {"Option": "ADD_METRICA_TAG", "Value": "YES"},
                        {"Option": "ADD_OPENSTAT_TAG", "Value": "NO"},
                    ],
                },
            }],
        })

        add_results = result.get("AddResults", [])
        if add_results and add_results[0].get("Id"):
            campaign_id = add_results[0]["Id"]
            logger.info(f"Created YD campaign: {name} (ID={campaign_id})")
            return {"id": campaign_id, "name": name, "status": "DRAFT"}
        else:
            errors = add_results[0].get("Errors", []) if add_results else []
            error_msg = "; ".join(e.get("Message", "") for e in errors) or "Unknown error"
            raise Exception(f"Failed to create campaign: {error_msg}")

    async def pause_campaign(self, campaign_id: int):
        """Suspend (pause) a campaign."""
        await self._request("campaigns", "suspend", {
            "SelectionCriteria": {"Ids": [campaign_id]},
        })
        logger.info(f"Suspended YD campaign {campaign_id}")

    async def resume_campaign(self, campaign_id: int):
        """Resume a campaign."""
        await self._request("campaigns", "resume", {
            "SelectionCriteria": {"Ids": [campaign_id]},
        })
        logger.info(f"Resumed YD campaign {campaign_id}")

    async def get_stats(self, campaign_ids: list[int], days: int = 30) -> list[dict]:
        """Get campaign statistics from reports API."""
        date_from = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
        date_to = datetime.utcnow().strftime("%Y-%m-%d")

        try:
            result = await self._request("reports", "get", {
                "SelectionCriteria": {
                    "Filter": [{
                        "Field": "CampaignId",
                        "Operator": "IN",
                        "Values": [str(cid) for cid in campaign_ids],
                    }],
                    "DateFrom": date_from,
                    "DateTo": date_to,
                },
                "FieldNames": ["CampaignId", "Impressions", "Clicks", "Cost", "Ctr"],
                "ReportName": f"BidRoute_Stats_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                "ReportType": "CAMPAIGN_PERFORMANCE_REPORT",
                "DateRangeType": "CUSTOM_DATE",
                "Format": "TSV",
                "IncludeVAT": "YES",
            })
            return result
        except Exception as e:
            logger.warning(f"Failed to get stats: {e}")
            return []

    async def verify_token(self) -> bool:
        """Verify OAuth token by fetching campaigns."""
        try:
            await self.get_campaigns()
            return True
        except Exception as e:
            logger.warning(f"Token verification failed: {e}")
            return False
