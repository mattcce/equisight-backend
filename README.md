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

#### Home

**GET /**
Welcome message.

**Response:**
```json
{ "message": "Equisight Home Page!" }
```

#### Ticker Info

**GET /ticker/{ticker}**
Returns basic information about a ticker.

**Parameters:**
- 'ticker' (str): The stock symbol (e.g., 'AAPL).

**Response Example:**
```json
{
  "symbol": "AAPL",
  "currentPrice": 190.5,
  "marketCap": 3000000000000,
  "sector": "Technology",
  "industry": "Consumer Electronics",
  "longBusinessSummary": "Apple Inc. designs, manufactures, and markets smartphones..."
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
[
  {
    "ticker": "AAPL",
    "date": "2024-05-28",
    "close": 190.5,
    "volume": 100000000
  },
  ...
]
```

#### Ticker News & Press Releases

**GET /ticker/{ticker}/news**

**Parameters:**
- `count` (int, optional): Number of articles to return (default: 10)

**Usage Example:**
/ticker/{ticker}/news?count=20

**Response Example:**
```json
[
  {
    "id": "0a3e8a8a-b475-369c-b164-5a8a68429c1f",
    "title": "Jim Cramer on UnitedHealth Group (UNH): “I Have to Take a Pass”",
    "summary": "We recently published a list of Jim Cramer Had These 21 Stocks on His Radar...",
    "date": "2025-05-27",
    "thumbnailurl": "https://media.zenfs.com/en/insidermonkey.com/c34a56642082d17e3fa7c8675c6742b3",
    "alternate_thumbnailurl": "https://s.yimg.com/uu/api/res/1.2/9qB3DEDzhZm_JxOjrZMe4w--~B/...",
    "canonicalUrl": "https://finance.yahoo.com/news/jim-cramer-unitedhealth-group-unh-215408103.html",
    "clickThroughUrl": "https://finance.yahoo.com/news/jim-cramer-unitedhealth-group-unh-215408103.html"
  },
  ...
]
```

### Notes
- All endpoints return in JSON
- Historical data is cached in local SQLite database (equisight-backend.db)

### Running the app
1. Start the server:
```bash
uvicorn main:app --reload
```
