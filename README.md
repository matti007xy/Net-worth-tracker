# Net Worth Tracker

A personal net worth tracker built with Flask, designed for Swedish investors. Tracks assets across multiple platforms and calculates total net worth in SEK with live price updates.

## Supported Asset Types

- **Bitcoin** — Enter your BTC amount, price fetched live from CoinGecko in SEK
- **Avanza (Stocks, Funds & Certificates)** — Enter the ISIN and either number of shares or current value. The app auto-resolves ISINs to Yahoo Finance tickers for live price tracking. Works with Swedish funds (e.g. Avanza Global), stocks, and crypto certificates (e.g. CoinShares XBT, Valour Solana)
- **Bondora (P2P Lending)** — Enter principal in EUR, annual interest rate, and start date. The app calculates daily accrued simple interest and converts to SEK
- **CSN Student Loans** — Enter outstanding balance in SEK. Displayed as a liability (subtracted from net worth). Supports multiple loans

## Features

- Dashboard with total net worth, doughnut chart breakdown by category, and holdings table
- ISIN auto-resolution: Yahoo Finance search with OpenFIGI fallback for tickers not found directly
- Daily snapshots at 18:00 (while server is running) + manual snapshot button
- Historical net worth chart on the History page
- SEK formatting throughout (e.g. `1 234 567 kr`)
- 5-minute in-memory price cache to avoid API rate limits
- All data persisted in SQLite — survives server restarts

## APIs Used (all free, no keys required)

| Data | Source |
|------|--------|
| BTC/SEK price | [CoinGecko](https://www.coingecko.com/en/api) |
| Stock/fund prices | [Yahoo Finance](https://finance.yahoo.com/) via yfinance |
| EUR/SEK exchange rate | [exchangerate-api.com](https://www.exchangerate-api.com/) |
| ISIN to ticker mapping | [OpenFIGI](https://www.openfigi.com/) (fallback) |

## Setup

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/net-worth-tracker.git
cd net-worth-tracker

# Create virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the app
python app.py
```

Open http://127.0.0.1:5000 in your browser.

## Project Structure

```
.
├── app.py                  # Flask app, routes, scheduler
├── config.py               # Configuration (DB path, API URLs)
├── models.py               # SQLAlchemy models (Holding, Snapshot, SnapshotDetail)
├── services/
│   ├── price_service.py    # BTC, stock, FX price fetching, ISIN resolution, caching
│   ├── bondora_service.py  # Simple interest calculation
│   └── snapshot_service.py # Daily snapshot logic
├── templates/              # Jinja2 HTML templates
├── static/                 # CSS and JS
├── instance/               # SQLite database (gitignored)
└── requirements.txt
```

## Tech Stack

Python 3.12, Flask, Flask-SQLAlchemy, SQLite, yfinance, Bootstrap 5, Chart.js
