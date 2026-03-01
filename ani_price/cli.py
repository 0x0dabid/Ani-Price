"""Command-line interface for Ani-Price token tracker."""

import argparse
import sys

from .tracker import PriceTracker


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="ani-price",
        description="Token price tracker powered by DexScreener",
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
        if args.command == "price":
            return _cmd_price(tracker, args)
        elif args.command == "search":
            return _cmd_search(tracker, args)
        elif args.command == "detail":
            return _cmd_detail(tracker, args)
        elif args.command == "watch":
            return _cmd_watch(tracker, args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


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
        price_str = ""
        if info.get("priceUsd"):
            from .tracker import format_usd
            price_str = format_usd(float(info["priceUsd"]))
        else:
            price_str = "N/A"

        from .tracker import format_pct, format_volume
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
