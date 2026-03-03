"""Nansen Token Screener API client for smart money token discovery."""

import requests

NANSEN_BASE_URL = "https://api.nansen.ai/api/v1"

SUPPORTED_CHAINS = [
    "ethereum", "solana", "base", "arbitrum", "optimism",
    "polygon", "avalanche", "bsc", "blast", "zksync",
]

DEFAULT_ORDER_FIELDS = [
    "chain", "token_symbol", "token_age_days", "market_cap_usd",
    "liquidity", "price_usd", "price_change", "fdv", "volume",
    "buy_volume", "sell_volume", "netflow",
]


class NansenError(Exception):
    """Raised when a Nansen API request fails."""


class NansenClient:
    """Client for the Nansen Token Screener API."""

    def __init__(self, api_key):
        self._api_key = api_key
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "apiKey": api_key,
        })

    def token_screener(
        self,
        chains,
        date_from=None,
        date_to=None,
        timeframe=None,
        page=1,
        per_page=10,
        only_smart_money=False,
        token_age_min=None,
        token_age_max=None,
        market_cap_min=None,
        market_cap_max=None,
        liquidity_min=None,
        liquidity_max=None,
        order_by=None,
    ):
        """Query the Nansen Token Screener endpoint.

        Args:
            chains: List of chain names (e.g. ["ethereum", "solana"]).
            date_from: ISO datetime string for custom date range start.
            date_to: ISO datetime string for custom date range end.
            timeframe: Predefined window like "24h", "7d", "30d".
                       Cannot be used together with date_from/date_to.
            page: Page number for pagination.
            per_page: Results per page.
            only_smart_money: Filter for smart money activity only.
            token_age_min: Minimum token age in days.
            token_age_max: Maximum token age in days.
            market_cap_min: Minimum market cap in USD.
            market_cap_max: Maximum market cap in USD.
            liquidity_min: Minimum liquidity in USD.
            liquidity_max: Maximum liquidity in USD.
            order_by: List of dicts with "field" and "direction" keys.

        Returns:
            Dict with "data" (list of token dicts) and "pagination" info.
        """
        body = {
            "chains": chains,
            "pagination": {"page": page, "per_page": per_page},
        }

        if timeframe:
            body["timeframe"] = timeframe
        elif date_from and date_to:
            body["date"] = {"from": date_from, "to": date_to}

        filters = {}
        if only_smart_money:
            filters["only_smart_money"] = True
        if token_age_min is not None or token_age_max is not None:
            age = {}
            if token_age_min is not None:
                age["min"] = token_age_min
            if token_age_max is not None:
                age["max"] = token_age_max
            filters["token_age_days"] = age
        if market_cap_min is not None or market_cap_max is not None:
            mc = {}
            if market_cap_min is not None:
                mc["min"] = market_cap_min
            if market_cap_max is not None:
                mc["max"] = market_cap_max
            filters["market_cap_usd"] = mc
        if liquidity_min is not None or liquidity_max is not None:
            liq = {}
            if liquidity_min is not None:
                liq["min"] = liquidity_min
            if liquidity_max is not None:
                liq["max"] = liquidity_max
            filters["liquidity"] = liq

        if filters:
            body["filters"] = filters
        if order_by:
            body["order_by"] = order_by

        return self._post("/token-screener", body)

    def _post(self, path, body):
        """Make a POST request to the Nansen API."""
        url = f"{NANSEN_BASE_URL}{path}"
        try:
            resp = self._session.post(url, json=body, timeout=30)
        except requests.RequestException as e:
            raise NansenError(f"Request failed: {e}") from e

        if resp.status_code != 200:
            raise NansenError(
                f"Nansen API error ({resp.status_code}): {resp.text[:200]}"
            )
        return resp.json()
