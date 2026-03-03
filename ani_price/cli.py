"""Command-line interface for Ani-Price token tracker."""

import argparse
import json
import sys

from .tracker import PriceTracker, format_usd, format_pct, format_volume


def _add_nansen_key(parser):
    parser.add_argument("--key", required=True, help="Nansen API key")


def _add_chains(parser):
    parser.add_argument(
        "--chains", nargs="+", default=["ethereum", "solana", "base"],
        help="Chains to screen (default: ethereum solana base)",
    )


def _add_pagination(parser):
    parser.add_argument("--page", type=int, default=1, help="Page number")
    parser.add_argument("--per-page", type=int, default=10, help="Results per page")


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="ani-price",
        description="Token price tracker powered by DexScreener & Nansen",
    )
    sub = parser.add_subparsers(dest="command")

    # ── price ──────────────────────────────────────────────────────
    p_price = sub.add_parser("price", help="Get the price of a token")
    p_price.add_argument("token", help="Token contract address")
    p_price.add_argument("--chain", help="Filter by chain (e.g. solana, ethereum)")

    # ── search ─────────────────────────────────────────────────────
    p_search = sub.add_parser("search", help="Search tokens by name or symbol")
    p_search.add_argument("query", help="Search query (name, symbol, or pair)")

    # ── detail ─────────────────────────────────────────────────────
    p_detail = sub.add_parser("detail", help="Get detailed pair information")
    p_detail.add_argument("chain", help="Chain ID (e.g. ethereum)")
    p_detail.add_argument("pair", help="Pair contract address")

    # ── screener ────────────────────────────────────────────────────
    p_scr = sub.add_parser("screener", help="Nansen smart-money token screener")
    _add_nansen_key(p_scr)
    _add_chains(p_scr)
    _add_pagination(p_scr)
    p_scr.add_argument("--timeframe", help="Predefined window: 24h, 7d, 30d")
    p_scr.add_argument("--from", dest="date_from", help="Start date (ISO format)")
    p_scr.add_argument("--to", dest="date_to", help="End date (ISO format)")
    p_scr.add_argument("--smart-money", action="store_true", help="Smart money tokens only")
    p_scr.add_argument("--age-min", type=int, help="Min token age in days")
    p_scr.add_argument("--age-max", type=int, help="Max token age in days")
    p_scr.add_argument("--mcap-min", type=float, help="Min market cap (USD)")
    p_scr.add_argument("--mcap-max", type=float, help="Max market cap (USD)")
    p_scr.add_argument("--sort", help="Sort field (e.g. volume, market_cap_usd)")
    p_scr.add_argument("--order", choices=["ASC", "DESC"], default="DESC")

    # ── holdings ────────────────────────────────────────────────────
    p_hold = sub.add_parser("holdings", help="Nansen smart money holdings")
    _add_nansen_key(p_hold)
    _add_chains(p_hold)
    _add_pagination(p_hold)
    p_hold.add_argument("--sort", default="value_usd", help="Sort field")
    p_hold.add_argument("--order", choices=["ASC", "DESC"], default="DESC")

    # ── netflows ────────────────────────────────────────────────────
    p_net = sub.add_parser("netflows", help="Nansen smart money netflows")
    _add_nansen_key(p_net)
    _add_chains(p_net)
    _add_pagination(p_net)
    p_net.add_argument("--sort", default="net_flow_24h_usd", help="Sort field")
    p_net.add_argument("--order", choices=["ASC", "DESC"], default="DESC")

    # ── flows ───────────────────────────────────────────────────────
    p_flows = sub.add_parser("flows", help="Nansen flow intelligence for a token")
    _add_nansen_key(p_flows)
    p_flows.add_argument("chain", help="Chain (e.g. ethereum)")
    p_flows.add_argument("token", help="Token contract address")
    p_flows.add_argument("--timeframe", default="7d", help="Timeframe: 1h, 24h, 7d, 30d")

    # ── wallet ──────────────────────────────────────────────────────
    p_wal = sub.add_parser("wallet", help="Nansen wallet analysis")
    _add_nansen_key(p_wal)
    p_wal.add_argument("address", help="Wallet address to analyse")
    p_wal.add_argument("--chain", default="all", help="Chain (default: all)")

    # ── leaderboard ─────────────────────────────────────────────────
    p_lb = sub.add_parser("leaderboard", help="Nansen PnL leaderboard for a token")
    _add_nansen_key(p_lb)
    p_lb.add_argument("chain", help="Chain (e.g. ethereum)")
    p_lb.add_argument("token", help="Token contract address")
    _add_pagination(p_lb)

    # ── watch ──────────────────────────────────────────────────────
    p_watch = sub.add_parser("watch", help="Manage your watchlist")
    watch_sub = p_watch.add_subparsers(dest="watch_action")

    p_wa = watch_sub.add_parser("add", help="Add a token to the watchlist")
    p_wa.add_argument("token", help="Token contract address")
    p_wa.add_argument("--chain", help="Chain ID")
    p_wa.add_argument("--label", help="Custom label for the token")

    p_wr = watch_sub.add_parser("remove", help="Remove a token from the watchlist")
    p_wr.add_argument("token", help="Token contract address")

    watch_sub.add_parser("list", help="Show watchlist entries")
    watch_sub.add_parser("prices", help="Show current prices for all watchlist tokens")

    return parser


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    tracker = PriceTracker()

    try:
        handlers = {
            "price": _cmd_price,
            "search": _cmd_search,
            "detail": _cmd_detail,
            "screener": _cmd_screener,
            "holdings": _cmd_holdings,
            "netflows": _cmd_netflows,
            "flows": _cmd_flows,
            "wallet": _cmd_wallet,
            "leaderboard": _cmd_leaderboard,
            "watch": _cmd_watch,
        }
        handler = handlers.get(args.command)
        if handler:
            return handler(tracker, args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


# ── DexScreener commands ────────────────────────────────────────

def _cmd_price(tracker, args):
    info = tracker.get_price(args.token, chain_id=args.chain)
    if not info:
        print("No trading pairs found for this token.")
        return 1
    print()
    print(tracker.format_detail(info))
    print()
    return 0


def _cmd_search(tracker, args):
    results = tracker.search(args.query)
    if not results:
        print("No results found.")
        return 1

    print(f"\n  Search results for '{args.query}':\n")
    print(f"  {'Symbol':<12} {'Price':>14}   {'24h Change':>12}   {'Volume 24h':>12}   {'Chain':<10}")
    print(f"  {'-' * 70}")

    for info in results:
        price_str = format_usd(float(info["priceUsd"])) if info.get("priceUsd") else "N/A"
        change = format_pct(info.get("change24h"))
        vol = format_volume(info.get("volume24h"))
        chain = info.get("chain", "")
        print(f"  {info['symbol']:<12} {price_str:>14}   {change:>12}   {vol:>12}   {chain:<10}")

    print(f"\n  Showing top {len(results)} results. Use 'ani-price price <address>' for details.\n")
    return 0


def _cmd_detail(tracker, args):
    info = tracker.get_pair_detail(args.chain, args.pair)
    if not info:
        print("Pair not found.")
        return 1
    print()
    print(tracker.format_detail(info))
    print()
    return 0


# ── Nansen commands ─────────────────────────────────────────────

def _cmd_screener(tracker, args):
    order_by = [{"field": args.sort, "direction": args.order}] if args.sort else None
    result = tracker.screener(
        api_key=args.key, chains=args.chains,
        date_from=args.date_from, date_to=args.date_to,
        timeframe=args.timeframe, page=args.page, per_page=args.per_page,
        only_smart_money=args.smart_money,
        token_age_min=args.age_min, token_age_max=args.age_max,
        market_cap_min=args.mcap_min, market_cap_max=args.mcap_max,
        order_by=order_by,
    )
    tokens = result.get("tokens") or []
    pagination = result.get("pagination") or {}
    if not tokens:
        print("No tokens found matching the criteria.")
        return 1

    print(f"\n  Nansen Token Screener — Page {pagination.get('page', args.page)}\n")
    print(f"  {'Symbol':<10} {'Chain':<10} {'Price':>14} {'Change':>9} {'MCap':>10} {'Volume':>10} {'Liquidity':>10} {'Age':>6}")
    print(f"  {'-' * 86}")
    for info in tokens:
        print(tracker.format_screener_line(info))
    is_last = pagination.get("is_last_page", True)
    status = "last page" if is_last else f"more results on page {args.page + 1}"
    print(f"\n  Showing {len(tokens)} tokens ({status}).\n")
    return 0


def _cmd_holdings(tracker, args):
    order_by = [{"field": args.sort, "direction": args.order}]
    result = tracker.sm_holdings(args.key, args.chains, page=args.page,
                                 per_page=args.per_page, order_by=order_by)
    data = result.get("data") or []
    if not data:
        print("No smart money holdings found.")
        return 1

    print(f"\n  Smart Money Holdings — Page {args.page}\n")
    print(f"  {'Symbol':<10} {'Chain':<10} {'Value':>14} {'Holders':>8} {'24h Chg':>9} {'MCap':>10} {'Age':>6}")
    print(f"  {'-' * 73}")
    for t in data:
        sym = t.get("token_symbol", "???")
        chain = t.get("chain", "")
        val = format_volume(t.get("value_usd"))
        holders = str(t.get("holders_count", 0))
        chg = format_pct(t.get("balance_24h_percent_change"))
        mcap = format_volume(t.get("market_cap_usd"))
        age = f"{t['token_age_days']}d" if t.get("token_age_days") is not None else "N/A"
        print(f"  {sym:<10} {chain:<10} {val:>14} {holders:>8} {chg:>9} {mcap:>10} {age:>6}")
    print()
    return 0


def _cmd_netflows(tracker, args):
    order_by = [{"field": args.sort, "direction": args.order}]
    result = tracker.sm_netflows(args.key, args.chains, page=args.page,
                                 per_page=args.per_page, order_by=order_by)
    data = result.get("data") or []
    if not data:
        print("No smart money netflow data found.")
        return 1

    print(f"\n  Smart Money Netflows — Page {args.page}\n")
    print(f"  {'Symbol':<10} {'Chain':<10} {'1h Flow':>12} {'24h Flow':>12} {'7d Flow':>12} {'30d Flow':>12} {'Traders':>8}")
    print(f"  {'-' * 82}")
    for t in data:
        sym = t.get("token_symbol", "???")
        chain = t.get("chain", "")
        f1h = format_volume(t.get("net_flow_1h_usd"))
        f24h = format_volume(t.get("net_flow_24h_usd"))
        f7d = format_volume(t.get("net_flow_7d_usd"))
        f30d = format_volume(t.get("net_flow_30d_usd"))
        traders = str(t.get("trader_count", 0))
        print(f"  {sym:<10} {chain:<10} {f1h:>12} {f24h:>12} {f7d:>12} {f30d:>12} {traders:>8}")
    print()
    return 0


def _cmd_flows(tracker, args):
    result = tracker.flow_intelligence(args.key, args.chain, args.token,
                                       timeframe=args.timeframe)
    data = result.get("data") or []
    if not data:
        print("No flow intelligence data found.")
        return 1

    row = data[0] if isinstance(data, list) else data
    print(f"\n  Flow Intelligence — {args.chain} / {args.token[:16]}...\n")
    segments = [
        ("Smart Traders", "smart_trader"),
        ("Exchanges", "exchange"),
        ("Whales", "whale"),
        ("Top PnL", "top_pnl"),
        ("Public Figures", "public_figure"),
        ("Fresh Wallets", "fresh_wallets"),
    ]
    print(f"  {'Segment':<18} {'Net Flow':>14} {'Avg Flow':>14} {'Wallets':>8}")
    print(f"  {'-' * 58}")
    for label, key in segments:
        nf = format_volume(row.get(f"{key}_net_flow_usd"))
        af = format_volume(row.get(f"{key}_avg_flow_usd"))
        wc = str(row.get(f"{key}_wallet_count", 0))
        print(f"  {label:<18} {nf:>14} {af:>14} {wc:>8}")
    print()
    return 0


def _cmd_wallet(tracker, args):
    # PnL summary
    summary = tracker.wallet_pnl_summary(args.key, args.address, chain=args.chain)
    print(f"\n  Wallet Analysis — {args.address[:20]}...\n")

    if summary:
        pnl = format_volume(summary.get("realized_pnl_usd"))
        wr = summary.get("win_rate")
        wr_str = f"{wr:.0%}" if wr is not None else "N/A"
        trades = summary.get("traded_times", 0)
        tokens = summary.get("traded_token_count", 0)
        print(f"  Realized PnL:  {pnl}")
        print(f"  Win Rate:      {wr_str}")
        print(f"  Trades:        {trades}")
        print(f"  Tokens Traded: {tokens}")

        top5 = summary.get("top5_tokens") or []
        if top5:
            print(f"\n  Top Tokens:")
            for t in top5:
                sym = t.get("token_symbol", "???")
                rpnl = format_volume(t.get("realized_pnl"))
                roi = format_pct(t.get("realized_roi"))
                print(f"    {sym:<10} PnL: {rpnl:>12}  ROI: {roi:>9}")

    # Balances
    try:
        bal_result = tracker.wallet_balances(args.key, [args.address], chain=args.chain)
        balances = bal_result if isinstance(bal_result, list) else bal_result.get("data", [])
        if balances:
            balances.sort(key=lambda b: b.get("usdValue") or 0, reverse=True)
            print(f"\n  Top Balances:")
            print(f"  {'Token':<10} {'Chain':<10} {'Balance':>14} {'USD Value':>14}")
            print(f"  {'-' * 52}")
            for b in balances[:15]:
                sym = b.get("symbol", "???")
                chain = b.get("chain", "")
                amt = f"{b.get('tokenAmount', 0):,.2f}"
                val = format_volume(b.get("usdValue"))
                print(f"  {sym:<10} {chain:<10} {amt:>14} {val:>14}")
    except Exception:
        pass  # balances endpoint may fail

    print()
    return 0


def _cmd_leaderboard(tracker, args):
    result = tracker.pnl_leaderboard(args.key, args.chain, args.token,
                                     page=args.page, per_page=args.per_page)
    data = result.get("data") or []
    if not data:
        print("No leaderboard data found.")
        return 1

    print(f"\n  PnL Leaderboard — {args.chain} / {args.token[:16]}...\n")
    print(f"  {'#':<4} {'Address':<18} {'Realized PnL':>14} {'ROI':>9} {'Trades':>7}")
    print(f"  {'-' * 56}")
    for i, t in enumerate(data, 1):
        addr = t.get("address", "???")
        if len(addr) > 16:
            addr = addr[:8] + ".." + addr[-6:]
        rpnl = format_volume(t.get("pnl_usd_realised"))
        roi = format_pct(t.get("roi_percent_realised"))
        trades = str(t.get("nof_trades", 0))
        print(f"  {i:<4} {addr:<18} {rpnl:>14} {roi:>9} {trades:>7}")
    print()
    return 0


# ── Watch commands ──────────────────────────────────────────────

def _cmd_watch(tracker, args):
    if not args.watch_action:
        print("Usage: ani-price watch {add|remove|list|prices}")
        return 1

    if args.watch_action == "add":
        added = tracker.watchlist_add(args.token, chain_id=args.chain, label=args.label)
        if added:
            label = args.label or args.token[:16] + "..."
            print(f"Added {label} to watchlist.")
        else:
            print("Token is already in the watchlist.")
        return 0

    elif args.watch_action == "remove":
        removed = tracker.watchlist_remove(args.token)
        if removed:
            print("Removed from watchlist.")
        else:
            print("Token not found in watchlist.")
        return 0

    elif args.watch_action == "list":
        entries = tracker.watchlist_list()
        if not entries:
            print("Watchlist is empty. Use 'ani-price watch add <address>' to add tokens.")
            return 0
        print("\n  Watchlist:\n")
        for i, e in enumerate(entries, 1):
            label = e.get("label") or e["address"]
            chain = e.get("chain") or "any"
            print(f"  {i}. {label:<20} chain: {chain}")
        print()
        return 0

    elif args.watch_action == "prices":
        results = tracker.watchlist_prices()
        if not results:
            print("Watchlist is empty. Use 'ani-price watch add <address>' to add tokens.")
            return 0
        print("\n  Watchlist Prices:\n")
        for info in results:
            print(tracker.format_price_line(info))
        print()
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
