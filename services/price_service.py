import time

import requests
import yfinance as yf
from flask import current_app

from services.bondora_service import bondora_value_eur

# Simple in-memory cache (key -> {"value": ..., "ts": ...})
_cache = {}
CACHE_TTL = 300  # 5 minutes


def _cached_get(key, fetcher):
    now = time.time()
    if key in _cache and now - _cache[key]["ts"] < CACHE_TTL:
        return _cache[key]["value"]
    value = fetcher()
    _cache[key] = {"value": value, "ts": now}
    return value


def get_btc_price_sek():
    """Fetch current BTC price in SEK from CoinGecko."""
    def fetch():
        url = current_app.config["COINGECKO_BTC_SEK"]
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()["bitcoin"]["sek"]
    return _cached_get("btc_sek", fetch)


def get_eur_sek_rate():
    """Fetch current EUR/SEK exchange rate."""
    def fetch():
        url = current_app.config["EUR_SEK_API"]
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()["rates"]["SEK"]
    return _cached_get("eur_sek", fetch)


def get_stock_price_sek(ticker):
    """Fetch current price for a Yahoo Finance ticker.
    Swedish stocks on Nasdaq Stockholm trade in SEK.
    Uses 5d period since funds may not have data for every single day."""
    def fetch():
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d")
        if hist.empty:
            raise ValueError(f"No price data for ticker {ticker}")
        return float(hist["Close"].iloc[-1])
    return _cached_get(f"stock_{ticker}", fetch)


def resolve_isin_to_ticker(isin):
    """Map ISIN to a Yahoo ticker. Tries Yahoo search first, then OpenFIGI + Yahoo name search."""
    # 1. Try Yahoo Finance direct ISIN search
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={isin}&quotesCount=1&newsCount=0"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    resp.raise_for_status()
    quotes = resp.json().get("quotes", [])
    if quotes:
        return quotes[0]["symbol"]

    # 2. Fallback: get name from OpenFIGI, then search Yahoo by name + Stockholm
    try:
        figi_resp = requests.post(
            "https://api.openfigi.com/v3/mapping",
            json=[{"idType": "ID_ISIN", "idValue": isin}],
            timeout=10,
        )
        figi_resp.raise_for_status()
        figi_data = figi_resp.json()
        if figi_data and "data" in figi_data[0]:
            name = figi_data[0]["data"][0].get("name", "")
            if name:
                # Search Yahoo with the instrument name
                search_url = f"https://query2.finance.yahoo.com/v1/finance/search?q={name}&quotesCount=10&newsCount=0"
                search_resp = requests.get(
                    search_url,
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=10,
                )
                search_resp.raise_for_status()
                search_quotes = search_resp.json().get("quotes", [])
                # Prefer Stockholm (.ST) exchange
                for q in search_quotes:
                    if q.get("symbol", "").endswith(".ST"):
                        return q["symbol"]
                if search_quotes:
                    return search_quotes[0]["symbol"]
    except Exception:
        pass

    raise ValueError(f"No Yahoo ticker found for ISIN {isin}")


def valuate_holding(holding, btc_price=None, eur_sek=None):
    """Return the current SEK value of a single holding.
    Positive for assets, negative for liabilities (CSN)."""
    if holding.category == "btc":
        price = btc_price or get_btc_price_sek()
        return holding.btc_amount * price

    elif holding.category == "avanza":
        if holding.ticker and holding.shares:
            price = get_stock_price_sek(holding.ticker)
            return holding.shares * price
        if holding.manual_value_sek is not None:
            return holding.manual_value_sek
        return 0.0

    elif holding.category == "bondora":
        rate = eur_sek or get_eur_sek_rate()
        value_eur = bondora_value_eur(holding)
        return value_eur * rate

    elif holding.category == "csn":
        return -abs(holding.balance_sek)

    return 0.0


def get_all_valuations(holdings):
    """Batch-valuate all holdings. Fetches shared rates once."""
    categories = {h.category for h in holdings}

    btc_price = None
    eur_sek = None

    if "btc" in categories:
        try:
            btc_price = get_btc_price_sek()
        except Exception:
            btc_price = None

    if "bondora" in categories:
        try:
            eur_sek = get_eur_sek_rate()
        except Exception:
            eur_sek = None

    results = []
    for h in holdings:
        try:
            val = valuate_holding(h, btc_price=btc_price, eur_sek=eur_sek)
        except Exception:
            val = None  # Will show as N/A
        results.append((h, val))
    return results
