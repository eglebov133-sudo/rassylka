"""
Yandex Direct API v5 — service wrapper for campaign management.
API docs: https://yandex.ru/dev/direct/doc/ref-v5/concepts/about.html

Supports full campaign hierarchy:
  Campaign → Ad Groups → Ads + Keywords
"""
import asyncio
import logging
import httpx
from typing import Optional
from datetime import datetime, timedelta

logger = logging.getLogger("bidroute.yandex_direct")

API_URL = "https://api.direct.yandex.com/json/v5/"
SANDBOX_URL = "https://api-sandbox.direct.yandex.com/json/v5/"

# Use sandbox for testing, production for real campaigns
USE_SANDBOX = False

# Rate limiting: max 5 requests per second
REQUEST_DELAY = 1.0  # max 1 req/s — safe for heavy batch operations
MAX_RETRIES = 3
RETRY_BACKOFF = [1, 2, 4]  # seconds between retries


class YandexDirectClient:
    """Wrapper around Yandex Direct API v5."""

    def __init__(self, oauth_token: str, client_login: str = ""):
        self.token = oauth_token
        self.login = client_login
        self.base_url = SANDBOX_URL if USE_SANDBOX else API_URL
        self._last_request_time = 0.0

    def _headers(self):
        h = {
            "Authorization": f"Bearer {self.token}",
            "Accept-Language": "ru",
            "Content-Type": "application/json; charset=utf-8",
        }
        # Client-Login header is ONLY for agency accounts managing client sub-accounts.
        # For direct advertiser accounts, this header causes error 152.
        # We don't use it since umit-parts is a direct advertiser.
        return h

    async def _rate_limit(self):
        """Ensure we don't exceed 5 req/s."""
        import time
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < REQUEST_DELAY:
            await asyncio.sleep(REQUEST_DELAY - elapsed)
        self._last_request_time = time.monotonic()

    async def _request(self, service: str, method: str, params: dict) -> dict:
        """Make a request to Yandex Direct API with rate limiting and retry."""
        url = f"{self.base_url}{service}"
        body = {"method": method, "params": params}

        for attempt in range(MAX_RETRIES + 1):
            await self._rate_limit()

            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(url, json=body, headers=self._headers())
                    data = resp.json()
            except Exception as e:
                if attempt < MAX_RETRIES:
                    wait = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF)-1)]
                    logger.warning(f"YD API request failed (attempt {attempt+1}/{MAX_RETRIES}), retrying in {wait}s: {e}")
                    await asyncio.sleep(wait)
                    continue
                raise

            if "error" in data:
                err = data["error"]
                code = err.get("error_code", 0)
                detail = err.get('error_detail', '')
                msg = err.get('error_string', 'Unknown error')
                logger.error(f"YD API error: [{code}] {msg} — {detail}")

                # Retry on rate limit (506) or server errors
                if code in (506, 9000, 9001, 9002) and attempt < MAX_RETRIES:
                    wait = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF)-1)]
                    logger.warning(f"Retrying in {wait}s (attempt {attempt+1})...")
                    await asyncio.sleep(wait)
                    continue

                raise Exception(f"Yandex Direct: {msg} — {detail}")

            return data.get("result", {})

        raise Exception("Yandex Direct: max retries exceeded")

    # ═══════════════════════════════════════════════════
    #  Campaigns
    # ═══════════════════════════════════════════════════

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
                "daily_budget": (c.get("DailyBudget") or {}).get("Amount", 0) / 1_000_000,
                "impressions": (c.get("Statistics") or {}).get("Impressions", 0),
                "clicks": (c.get("Statistics") or {}).get("Clicks", 0),
                "cost": 0.0,
            }
            for c in campaigns
        ]

    async def create_campaign(
        self, name: str, daily_budget: float = 300.0,
        keywords: list[str] = None, regions: list[int] = None,
        negative_keywords: list[str] = None,
        geo_segment: str = "",
    ) -> dict:
        """Create a search-only text campaign in Yandex Direct.
        
        Strategy: HIGHEST_POSITION — bid to top positions.
        Network: SERVING_OFF — search only, no RSYa.
        Min daily budget: 300₽ (API constraint).
        """
        if not regions:
            regions = [225]  # 225 = Russia

        if not negative_keywords:
            from backend.services.keyword_generator import NEGATIVE_KEYWORDS
            negative_keywords = NEGATIVE_KEYWORDS

        # Enforce minimum budget (API requires >= 300 RUB)
        daily_budget = max(daily_budget, 300.0)
        budget_micros = int(daily_budget * 1_000_000)

        campaign_data = {
            "Name": name,
            # Yandex Direct uses Moscow time (UTC+3); UTC date can be 'in the past' after 21:00 UTC
            "StartDate": (datetime.utcnow() + timedelta(hours=3)).strftime("%Y-%m-%d"),
            "DailyBudget": {
                "Amount": budget_micros,
                "Mode": "STANDARD",
            },
            "NegativeKeywords": {"Items": negative_keywords[:200]},  # API limit: 200
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
                    {"Option": "ENABLE_COMPANY_INFO", "Value": "YES"},
                    {"Option": "ENABLE_SITE_MONITORING", "Value": "YES"},
                ],
            },
        }

        result = await self._request("campaigns", "add", {
            "Campaigns": [campaign_data],
        })

        add_results = result.get("AddResults", [])
        if add_results and add_results[0].get("Id"):
            campaign_id = add_results[0]["Id"]
            logger.info(f"Created YD campaign: {name} (ID={campaign_id})")
            return {"id": campaign_id, "name": name, "status": "DRAFT"}
        else:
            errors = add_results[0].get("Errors", []) if add_results else []
            error_details = "; ".join(
                f"[{e.get('Code')}] {e.get('Message', '')} — {e.get('Details', '')}"
                for e in errors
            ) or "Unknown error"
            logger.error(f"Campaign create failed: {error_details}")
            raise Exception(f"Failed to create campaign: {error_details}")

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

    # ═══════════════════════════════════════════════════
    #  Ad Groups
    # ═══════════════════════════════════════════════════

    async def create_ad_groups(
        self, campaign_id: int, groups: list[dict],
        regions: list[int] = None,
    ) -> list[dict]:
        """Create ad groups for a campaign.
        
        Each group: {"name": str, "autotarget": bool}
        Returns: [{"name": str, "id": int}, ...]
        
        API limit: up to 1000 ad groups per call.
        """
        if not regions:
            regions = [225]

        ad_groups = []
        for g in groups:
            group_data = {
                "Name": g["name"][:255],
                "CampaignId": campaign_id,
                "RegionIds": regions,
            }
            # Autotarget groups are just regular groups without keywords
            # No special params needed — just don't add keywords later
            ad_groups.append(group_data)

        # Batch: API allows up to 1000 groups per request
        results = []
        for i in range(0, len(ad_groups), 1000):
            batch = ad_groups[i:i+1000]
            result = await self._request("adgroups", "add", {
                "AdGroups": batch,
            })
            for j, r in enumerate(result.get("AddResults", [])):
                if r.get("Id"):
                    results.append({
                        "name": groups[i + j]["name"],
                        "id": r["Id"],
                        "autotarget": groups[i + j].get("autotarget", False),
                    })
                    logger.info(f"  Created ad group: {groups[i + j]['name']} (ID={r['Id']})")
                else:
                    errors = r.get("Errors", [])
                    err = "; ".join(e.get("Message", "") for e in errors)
                    logger.warning(f"  Failed to create ad group '{groups[i + j]['name']}': {err}")
                    results.append({
                        "name": groups[i + j]["name"],
                        "id": None,
                        "error": err,
                    })

        return results

    # ═══════════════════════════════════════════════════
    #  Ads (Text Ads)
    # ═══════════════════════════════════════════════════

    async def create_ads(self, ads: list[dict]) -> list[dict]:
        """Create text ads for ad groups.
        
        Each ad: {"ad_group_id": int, "title1": str, "title2": str, "text": str, "href": str}
        Returns: [{"id": int, "ad_group_id": int}, ...]
        
        API limit: up to 1000 ads per call.
        """
        ad_items = []
        for a in ads:
            ad_items.append({
                "AdGroupId": a["ad_group_id"],
                "TextAd": {
                    "Title": a["title1"][:56],
                    "Title2": a.get("title2", "")[:30],
                    "Text": a["text"][:81],
                    "Href": a.get("href", "https://umit.pro"),
                    "Mobile": "NO",
                },
            })

        results = []
        for i in range(0, len(ad_items), 1000):
            batch = ad_items[i:i+1000]
            result = await self._request("ads", "add", {"Ads": batch})
            for j, r in enumerate(result.get("AddResults", [])):
                if r.get("Id"):
                    results.append({
                        "id": r["Id"],
                        "ad_group_id": ads[i + j]["ad_group_id"],
                    })
                else:
                    errors = r.get("Errors", [])
                    err = "; ".join(e.get("Message", "") for e in errors)
                    logger.warning(f"  Failed to create ad: {err}")
                    results.append({"id": None, "error": err})

        logger.info(f"Created {len([r for r in results if r.get('id')])} ads")
        return results

    # ═══════════════════════════════════════════════════
    #  Keywords
    # ═══════════════════════════════════════════════════

    async def add_keywords(self, keywords: list[dict]) -> list[dict]:
        """Add keywords to ad groups.
        
        Each kw: {"ad_group_id": int, "keyword": str}
        Returns: [{"id": int, "keyword": str}, ...]
        
        API limit: up to 1000 keywords per call.
        """
        kw_items = [
            {
                "AdGroupId": kw["ad_group_id"],
                "Keyword": kw["keyword"][:4096],
            }
            for kw in keywords
        ]

        results = []
        for i in range(0, len(kw_items), 1000):
            batch = kw_items[i:i+1000]
            result = await self._request("keywords", "add", {"Keywords": batch})
            for j, r in enumerate(result.get("AddResults", [])):
                if r.get("Id"):
                    results.append({
                        "id": r["Id"],
                        "keyword": keywords[i + j]["keyword"],
                    })
                else:
                    errors = r.get("Errors", [])
                    err = "; ".join(e.get("Message", "") for e in errors)
                    # Don't log each — too noisy
                    results.append({"id": None, "keyword": keywords[i + j]["keyword"], "error": err})

        ok = len([r for r in results if r.get("id")])
        logger.info(f"Added {ok}/{len(keywords)} keywords")
        return results

    # ═══════════════════════════════════════════════════
    #  Stats / Reports
    # ═══════════════════════════════════════════════════

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
