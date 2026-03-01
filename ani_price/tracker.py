"""Price tracker with watchlist management and display formatting."""

import json
import os

from .api import DexScreenerClient, DexScreenerError

DEFAULT_WATCHLIST_PATH = os.path.join(os.path.expanduser("~"), ".ani-price-watchlist.json")


def _load_watchlist(path):
    """Load the watchlist from disk. Returns a list of token entries."""
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)


def _save_watchlist(path, watchlist):
    """Persist the watchlist to disk."""
    with open(path, "w") as f:
        json.dump(watchlist, f, indent=2)


def format_usd(value):
    """Format a number as USD string."""
    if value is None:
        return "N/A"
    if value >= 1:
        return f"${value:,.2f}"
    # Show more decimals for small prices
    return f"${value:.6f}"


def format_pct(value):
    """Format a percentage with a sign and color hint."""
    if value is None:
        return "N/A"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"


def format_volume(value):
    """Format volume in a compact human-readable way."""
    if value is None:
        return "N/A"
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"${value / 1_000:.2f}K"
    return f"${value:.2f}"


def _best_pair(pairs):
    """Pick the pair with highest USD liquidity from a list."""
    if not pairs:
        return None
    return max(
        pairs,
        key=lambda p: (p.get("liquidity") or {}).get("usd") or 0,
    )


class PriceTracker:
    """High-level price tracker that wraps the DexScreener client."""

    def __init__(self, watchlist_path=None):
        self.client = DexScreenerClient()
        self.watchlist_path = watchlist_path or DEFAULT_WATCHLIST_PATH

    # ── Price queries ──────────────────────────────────────────────

    def get_price(self, token_address, chain_id=None):
        """Get price info for a single token. Returns a summary dict."""
        if chain_id:
            pairs = self.client.get_token_pairs_by_chain(chain_id, token_address)
        else:
            pairs = self.client.get_token_pairs(token_address)

        pair = _best_pair(pairs)
        if not pair:
            return None
        return self._summarize_pair(pair)

    def search(self, query):
        """Search tokens and return summaries for top results."""
        pairs = self.client.search_tokens(query)
        # Deduplicate by base token address, keeping highest-liquidity pair
        seen = {}
        for p in pairs:
            addr = p.get("baseToken", {}).get("address", "")
            liq = (p.get("liquidity") or {}).get("usd") or 0
            if addr not in seen or liq > (seen[addr].get("liquidity") or {}).get("usd", 0):
                seen[addr] = p
        return [self._summarize_pair(p) for p in list(seen.values())[:10]]

    def get_pair_detail(self, chain_id, pair_address):
        """Get detailed info for a specific pair."""
        pair = self.client.get_pair(chain_id, pair_address)
        if not pair:
            return None
        return self._summarize_pair(pair, detailed=True)

    # ── Watchlist ──────────────────────────────────────────────────

    def watchlist_add(self, token_address, chain_id=None, label=None):
        """Add a token to the watchlist."""
        wl = _load_watchlist(self.watchlist_path)
        for entry in wl:
            if entry["address"].lower() == token_address.lower():
                return False  # already exists
        entry = {"address": token_address}
        if chain_id:
            entry["chain"] = chain_id
        if label:
            entry["label"] = label
        wl.append(entry)
        _save_watchlist(self.watchlist_path, wl)
        return True

    def watchlist_remove(self, token_address):
        """Remove a token from the watchlist."""
        wl = _load_watchlist(self.watchlist_path)
        new_wl = [e for e in wl if e["address"].lower() != token_address.lower()]
        if len(new_wl) == len(wl):
            return False
        _save_watchlist(self.watchlist_path, new_wl)
        return True

    def watchlist_list(self):
        """Return the current watchlist entries."""
        return _load_watchlist(self.watchlist_path)

    def watchlist_prices(self):
        """Fetch current prices for all watchlist tokens."""
        wl = _load_watchlist(self.watchlist_path)
        if not wl:
            return []

        results = []
        for entry in wl:
            try:
                info = self.get_price(entry["address"], entry.get("chain"))
                if info:
                    if entry.get("label"):
                        info["label"] = entry["label"]
                    results.append(info)
                else:
                    results.append({
                        "symbol": entry.get("label") or entry["address"][:10] + "...",
                        "error": "No pair data found",
                    })
            except DexScreenerError as e:
                results.append({
                    "symbol": entry.get("label") or entry["address"][:10] + "...",
                    "error": str(e),
                })
        return results

    # ── Formatting ─────────────────────────────────────────────────

    @staticmethod
    def _summarize_pair(pair, detailed=False):
        """Extract a clean summary dict from a raw pair object."""
        base = pair.get("baseToken") or {}
        quote = pair.get("quoteToken") or {}
        price_change = pair.get("priceChange") or {}
        volume = pair.get("volume") or {}
        liquidity = pair.get("liquidity") or {}

        summary = {
            "symbol": base.get("symbol", "???"),
            "name": base.get("name", "Unknown"),
            "address": base.get("address", ""),
            "priceUsd": pair.get("priceUsd"),
            "priceNative": pair.get("priceNative"),
            "quoteSymbol": quote.get("symbol", ""),
            "change5m": price_change.get("m5"),
            "change1h": price_change.get("h1"),
            "change6h": price_change.get("h6"),
            "change24h": price_change.get("h24"),
            "volume24h": volume.get("h24"),
            "liquidityUsd": liquidity.get("usd"),
            "marketCap": pair.get("marketCap"),
            "fdv": pair.get("fdv"),
            "chain": pair.get("chainId", ""),
            "dex": pair.get("dexId", ""),
            "pairAddress": pair.get("pairAddress", ""),
            "url": pair.get("url", ""),
        }

        if detailed:
            summary["volume5m"] = volume.get("m5")
            summary["volume1h"] = volume.get("h1")
            summary["volume6h"] = volume.get("h6")
            txns = pair.get("txns") or {}
            summary["txns24h"] = txns.get("h24")
            summary["pairCreatedAt"] = pair.get("pairCreatedAt")

        return summary

    @staticmethod
    def format_price_line(info):
        """Format a single token's price info as a one-line string."""
        if "error" in info:
            return f"  {info['symbol']}: {info['error']}"

        price_str = format_usd(float(info["priceUsd"])) if info.get("priceUsd") else "N/A"
        change = format_pct(info.get("change24h"))
        vol = format_volume(info.get("volume24h"))
        label = info.get("label") or info["symbol"]

        return f"  {label:<12} {price_str:>14}   24h: {change:>9}   Vol: {vol:>10}"

    @staticmethod
    def format_detail(info):
        """Format detailed pair information as a multi-line string."""
        if not info:
            return "  No data found."

        lines = []
        lines.append(f"  {info['name']} ({info['symbol']})")
        lines.append(f"  Chain: {info['chain']}  |  DEX: {info['dex']}")
        lines.append(f"  Pair: {info.get('pairAddress', 'N/A')}")
        lines.append("")

        price_str = format_usd(float(info["priceUsd"])) if info.get("priceUsd") else "N/A"
        lines.append(f"  Price (USD):     {price_str}")
        if info.get("priceNative"):
            lines.append(f"  Price (Native):  {info['priceNative']} {info.get('quoteSymbol', '')}")
        lines.append("")

        lines.append("  Price Change:")
        lines.append(f"    5m:  {format_pct(info.get('change5m')):>9}    1h: {format_pct(info.get('change1h')):>9}")
        lines.append(f"    6h:  {format_pct(info.get('change6h')):>9}   24h: {format_pct(info.get('change24h')):>9}")
        lines.append("")

        lines.append("  Volume:")
        lines.append(f"    24h: {format_volume(info.get('volume24h'))}")
        if info.get("volume5m") is not None:
            lines.append(f"    5m:  {format_volume(info.get('volume5m'))}   1h: {format_volume(info.get('volume1h'))}   6h: {format_volume(info.get('volume6h'))}")
        lines.append("")

        lines.append(f"  Liquidity:  {format_volume(info.get('liquidityUsd'))}")
        lines.append(f"  Market Cap: {format_volume(info.get('marketCap'))}")
        lines.append(f"  FDV:        {format_volume(info.get('fdv'))}")

        if info.get("txns24h"):
            txns = info["txns24h"]
            lines.append(f"  Txns (24h): {txns.get('buys', 0)} buys / {txns.get('sells', 0)} sells")

        if info.get("url"):
            lines.append(f"\n  DexScreener: {info['url']}")

        return "\n".join(lines)
