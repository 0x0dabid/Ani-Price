"""Nansen API client for onchain analytics and smart money intelligence."""

import requests

NANSEN_BASE_URL = "https://api.nansen.ai/api/v1"
NANSEN_BETA_URL = "https://api.nansen.ai/api/beta"

SUPPORTED_CHAINS = [
    "ethereum", "solana", "base", "arbitrum", "optimism",
    "polygon", "avalanche", "bsc", "blast", "zksync",
    "linea", "scroll", "mantle", "sei", "sonic",
    "hyperevm", "monad", "unichain", "ronin", "plasma",
]


class NansenError(Exception):
    """Raised when a Nansen API request fails."""


class NansenClient:
    """Full Nansen API client covering Token Screener, Smart Money,
    Wallet Profiler, and Token God Mode endpoints."""

    def __init__(self, api_key):
        self._api_key = api_key
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "apiKey": api_key,
        })

    # ── helpers ────────────────────────────────────────────────────

    def _post(self, path, body, base=None):
        """POST to *base*/*path* and return parsed JSON."""
        url = f"{base or NANSEN_BASE_URL}{path}"
        try:
            resp = self._session.post(url, json=body, timeout=30)
        except requests.RequestException as e:
            raise NansenError(f"Request failed: {e}") from e
        if resp.status_code != 200:
            raise NansenError(
                f"Nansen API error ({resp.status_code}): {resp.text[:200]}"
            )
        return resp.json()

    @staticmethod
    def _range_filter(filters, key, vmin, vmax):
        if vmin is not None or vmax is not None:
            f = {}
            if vmin is not None:
                f["min"] = vmin
            if vmax is not None:
                f["max"] = vmax
            filters[key] = f

    # ── Token Screener ─────────────────────────────────────────────

    def token_screener(self, chains, timeframe=None, date_from=None,
                       date_to=None, page=1, per_page=10,
                       only_smart_money=False, token_age_min=None,
                       token_age_max=None, market_cap_min=None,
                       market_cap_max=None, liquidity_min=None,
                       liquidity_max=None, order_by=None):
        """POST /token-screener — discover trending tokens."""
        body = {"chains": chains,
                "pagination": {"page": page, "per_page": per_page}}
        if timeframe:
            body["timeframe"] = timeframe
        elif date_from and date_to:
            body["date"] = {"from": date_from, "to": date_to}

        filters = {}
        if only_smart_money:
            filters["only_smart_money"] = True
        self._range_filter(filters, "token_age_days", token_age_min, token_age_max)
        self._range_filter(filters, "market_cap_usd", market_cap_min, market_cap_max)
        self._range_filter(filters, "liquidity", liquidity_min, liquidity_max)
        if filters:
            body["filters"] = filters
        if order_by:
            body["order_by"] = order_by
        return self._post("/token-screener", body)

    # ── Smart Money ────────────────────────────────────────────────

    def smart_money_holdings(self, chains, page=1, per_page=10,
                             include_stablecoins=False,
                             include_native_tokens=False,
                             order_by=None):
        """POST /smart-money/holdings — aggregated SM token holdings."""
        body = {"chains": chains,
                "pagination": {"page": page, "per_page": per_page}}
        filters = {"include_stablecoins": include_stablecoins,
                   "include_native_tokens": include_native_tokens}
        body["filters"] = filters
        if order_by:
            body["order_by"] = order_by
        return self._post("/smart-money/holdings", body)

    def smart_money_netflows(self, chains, page=1, per_page=10,
                             include_stablecoins=False,
                             include_native_tokens=False,
                             order_by=None):
        """POST /smart-money/netflow — SM net capital flows."""
        body = {"chains": chains,
                "pagination": {"page": page, "per_page": per_page}}
        filters = {"include_stablecoins": include_stablecoins,
                   "include_native_tokens": include_native_tokens}
        body["filters"] = filters
        if order_by:
            body["order_by"] = order_by
        return self._post("/smart-money/netflow", body)

    def smart_money_dex_trades(self, chains, page=1, per_page=10,
                               order_by=None):
        """POST /smart-money/dex-trades — recent SM DEX trades."""
        body = {"chains": chains,
                "pagination": {"page": page, "per_page": per_page}}
        if order_by:
            body["order_by"] = order_by
        return self._post("/smart-money/dex-trades", body)

    # ── Token God Mode ─────────────────────────────────────────────

    def flow_intelligence(self, chain, token_address, timeframe="7d"):
        """POST /tgm/flow-intelligence — categorised flow analysis."""
        body = {"chain": chain, "token_address": token_address,
                "timeframe": timeframe}
        return self._post("/tgm/flow-intelligence", body)

    def pnl_leaderboard(self, chain, token_address, page=1,
                        per_page=10, date_from=None, date_to=None,
                        pnl_min=None, order_by=None):
        """POST /tgm/pnl-leaderboard — top traders by PnL."""
        body = {"chain": chain, "token_address": token_address,
                "pagination": {"page": page, "per_page": per_page}}
        if date_from and date_to:
            body["date"] = {"from": date_from, "to": date_to}
        filters = {}
        if pnl_min is not None:
            filters["pnl_usd_realised"] = {"min": pnl_min}
        if filters:
            body["filters"] = filters
        if order_by:
            body["order_by"] = order_by
        return self._post("/tgm/pnl-leaderboard", body)

    def token_dex_trades(self, chain, token_address, page=1,
                         per_page=10, action=None,
                         only_smart_money=False):
        """POST /tgm/dex-trades — DEX trades for a specific token."""
        body = {"chain": chain, "token_address": token_address,
                "pagination": {"page": page, "per_page": per_page}}
        filters = {}
        if action:
            filters["action"] = action
        if only_smart_money:
            filters["only_smart_money"] = True
        if filters:
            body["filters"] = filters
        return self._post("/tgm/dex-trades", body)

    # ── Profiler (Wallet Analysis) ─────────────────────────────────

    def address_balances(self, addresses, chain="all"):
        """POST /profiler/address/balances — current token balances (FREE)."""
        body = {"parameters": {"chain": chain,
                               "walletAddresses": addresses},
                "pagination": {"page": 1, "recordsPerPage": 100}}
        return self._post("/profiler/address/balances", body,
                          base=NANSEN_BETA_URL)

    def address_pnl(self, address, chain="all", date_from=None,
                    date_to=None, page=1, per_page=10):
        """POST /profiler/address/pnl — detailed PnL per token."""
        body = {"address": address, "chain": chain,
                "pagination": {"page": page, "per_page": per_page}}
        if date_from and date_to:
            body["date"] = {"from": date_from, "to": date_to}
        return self._post("/profiler/address/pnl", body)

    def address_pnl_summary(self, address, chain="all",
                            date_from=None, date_to=None):
        """POST /profiler/address/pnl-summary — aggregate PnL stats."""
        body = {"address": address, "chain": chain}
        if date_from and date_to:
            body["date"] = {"from": date_from, "to": date_to}
        return self._post("/profiler/address/pnl-summary", body)

    def address_counterparties(self, addresses, chain="all",
                               page=1, per_page=20):
        """POST /profiler/address/counterparties — top interacting addresses."""
        body = {"parameters": {"walletAddresses": addresses,
                               "chain": chain,
                               "groupBy": "wallet"},
                "pagination": {"page": page,
                               "recordsPerPage": per_page}}
        return self._post("/profiler/address/counterparties", body,
                          base=NANSEN_BETA_URL)

    def address_related_wallets(self, address, chain="all"):
        """POST /profiler/address/related-wallets — funding/deployment links."""
        body = {"address": address, "chain": chain}
        return self._post("/profiler/address/related-wallets", body)
