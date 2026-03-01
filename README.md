# Ani-Price

Token price tracker powered by the [DexScreener API](https://docs.dexscreener.com/api/reference).

Track token prices, search for tokens, and manage a personal watchlist — via the web UI or the command line.

## Features

- **Price lookup** — get the current price, volume, liquidity, and price changes for any token by contract address
- **Search** — find tokens by name, symbol, or trading pair
- **Pair details** — view detailed information for a specific DEX trading pair
- **Watchlist** — save tokens you care about and check all their prices at once
- **Multi-chain** — supports Ethereum, Solana, BSC, Arbitrum, Base, and all chains indexed by DexScreener

## Web UI

Open `index.html` in your browser — no server or build step needed. Features:

- Search tokens by name, symbol, or contract address
- View detailed price, volume, liquidity, and transaction data
- Manage a watchlist (stored in localStorage)
- Click any token row to see full details

## CLI Installation

```bash
pip install -r requirements.txt
pip install -e .
```

## CLI Usage

### Get a token's price

```bash
# By contract address
ani-price price So11111111111111111111111111111111111111112

# Filter by chain
ani-price price 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2 --chain ethereum
```

### Search for tokens

```bash
ani-price search PEPE
ani-price search SOL/USDC
```

### View pair details

```bash
ani-price detail ethereum 0x11b815efB8f581194ae79006d24E0d814B7697F6
```

### Manage your watchlist

```bash
# Add tokens
ani-price watch add So11111111111111111111111111111111111111112 --label SOL --chain solana
ani-price watch add 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2 --label WETH --chain ethereum

# View watchlist
ani-price watch list

# Check all prices at once
ani-price watch prices

# Remove a token
ani-price watch remove So11111111111111111111111111111111111111112
```

## API

No API key required. DexScreener's public API is free with a rate limit of 300 requests/minute.

## Project Structure

```
index.html            # Web UI (single-page app)
ani_price/
├── __init__.py       # Package metadata
├── api.py            # DexScreener API client
├── tracker.py        # Price tracker, watchlist, formatting
└── cli.py            # Command-line interface
```
