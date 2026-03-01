"""DexScreener API client for fetching token and pair data."""

import time
import requests

BASE_URL = "https://api.dexscreener.com"
RATE_LIMIT_PER_MIN = 300
MIN_REQUEST_INTERVAL = 60.0 / RATE_LIMIT_PER_MIN  # ~0.2s


class DexScreenerError(Exception):
    """Raised when a DexScreener API request fails."""


class DexScreenerClient:
    """Client for interacting with the DexScreener API."""

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json"})
        self._last_request_time = 0.0

    def _throttle(self):
        """Enforce simple rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < MIN_REQUEST_INTERVAL:
            time.sleep(MIN_REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.time()

    def _get(self, path):
        """Make a GET request to the DexScreener API."""
        self._throttle()
        url = f"{BASE_URL}{path}"
        resp = self._session.get(url, timeout=15)
        if resp.status_code != 200:
            raise DexScreenerError(
                f"API request failed ({resp.status_code}): {url}"
            )
        return resp.json()

    def get_token_pairs(self, token_address):
        """Get all trading pairs for a token by its contract address.

        Returns a list of pair dicts, sorted by USD liquidity descending.
        """
        data = self._get(f"/tokens/v1/{token_address}")
        pairs = data if isinstance(data, list) else data.get("pairs") or []
        pairs.sort(
            key=lambda p: (p.get("liquidity") or {}).get("usd") or 0,
            reverse=True,
        )
        return pairs

    def get_pair(self, chain_id, pair_address):
        """Get a specific pair by chain and pair address."""
        data = self._get(f"/latest/dex/pairs/{chain_id}/{pair_address}")
        pairs = data.get("pairs") or []
        return pairs[0] if pairs else None

    def get_token_pairs_by_chain(self, chain_id, token_address):
        """Get pairs for a token on a specific chain."""
        data = self._get(f"/token-pairs/v1/{chain_id}/{token_address}")
        pairs = data if isinstance(data, list) else data.get("pairs") or []
        pairs.sort(
            key=lambda p: (p.get("liquidity") or {}).get("usd") or 0,
            reverse=True,
        )
        return pairs

    def search_tokens(self, query):
        """Search for tokens by name, symbol, or pair identifier."""
        data = self._get(f"/latest/dex/search?q={query}")
        return data.get("pairs") or []

    def get_multiple_tokens(self, token_addresses):
        """Get pairs for multiple token addresses (max 30).

        token_addresses: list of contract address strings.
        """
        if len(token_addresses) > 30:
            raise DexScreenerError("Maximum 30 token addresses per request")
        joined = ",".join(token_addresses)
        data = self._get(f"/tokens/v1/{joined}")
        pairs = data if isinstance(data, list) else data.get("pairs") or []
        return pairs
