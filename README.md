# `equisight` Backend

## Development

1. Clone repository: `https://github.com/mattcce/equisight-backend`
2. Navigate to repository: `cd equisight-backend`

### Setting up build system

**macOS/via `brew`**

1. Install `uv`: `brew install uv`
2. Install project dependencies: `uv sync`
3. Setup pre-commit hooks (via `pre-commit`): `uv run pre-commit install`

## `equisight` Backend API

Retrieving, caching, and serving financial ticker data and news with statistical and sentiment analysis.

---

### Endpoints

#### Ticker Info

**GET /ticker/{ticker}/info**
Returns basic information about a ticker.

**Parameters:**
- 'ticker' (str): The stock symbol (e.g., 'AAPL').

**Response Example:**
```json
{
  "symbol": "AAPL",
  "fullExchangeName": "NasdaqGS",
  "shortName": "Apple Inc.",
  "regularMarketPrice": 200.85,
  "marketState": "CLOSED",
  "region": "US",
  "currency": "USD",
  "previousClose": 199.95
}
```

#### Ticker Historical Data

**GET or POST /ticker/{ticker}/history**

**Parameters:**
- `start` (str, optional): Start date in `YYYY-MM-DD` (default: 30 days ago)
- `end` (str, optional): End date in `YYYY-MM-DD` (default: today)

**Usage Example:**
/ticker/{ticker}/history?start=2025-01-01&end=2025-05-05

**Response Example:**
```json
{
  "history": [
    {
      "ticker": "AAPL",
      "timestamp": 1748577600,
      "close": 200.85000610351562,
      "volume": 70753100
    },
    ...
  ]
}
```

#### Ticker News & Press Releases

**GET /ticker/{ticker}/news**

**Parameters:**
- `count` (int, optional): Number of articles to return (default: 10)

**Usage Example:**
/ticker/{ticker}/news?count=20

**Response Example:**
```json
{
  "ticker": "AAPL",
  "articles": [
    {
      "id": "55f60082-b396-3a53-a6ab-f66df41d6fa1",
      "title": "Smartphone Sales Growth Hit by Tariff ‘Whirlwind of Uncertainty’",
      "providerDisplayName": "Bloomberg",
      "summary": "(Bloomberg) -- Sales of Apple Inc.’s iPhone and its closest rivals are expected to take a significant blow...",
      "canonicalUrl": "https://finance.yahoo.com/news/smartphone-sales-growth-hit-tariff-091553675.html",
      "thumbnailUrl": "https://media.zenfs.com/en/bloomberg_holding_pen_162/382f1e8fa70082fcb704824f50dbd2c8",
      "timestamp": 1748596553,
      "alternateThumbnailUrl": "https://s.yimg.com/uu/api/res/1.2/Et.aYmbkVIT_thsf4n06_g--~B/Zmk9c3RyaW07aD0xMjg7dz0xNzA7YXBwaWQ9eXRhY2h5b24-/https://media.zenfs.com/en/bloomberg_holding_pen_162/382f1e8fa70082fcb704824f50dbd2c8",
      "clickThroughUrl": "https://finance.yahoo.com/news/smartphone-sales-growth-hit-tariff-091553675.html"
    },
    ...
  ]
}
```

### Notes
- All endpoints return in JSON
- Historical data is cached in local SQLite database (equisight-backend.db)

### Running the app
- Start the server:
```bash
uvicorn main:app --reload
```
