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

**GET /ticker/{ticker}/info**
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
{
  "history": [
    {
      "ticker": "UNH",
      "date": 1748577600,
      "close": 301.9100036621094,
      "volume": 16272600
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
  "ticker": "UNH",
  "articles": [
    {
      "id": "f8adee8c-3096-35ea-b04a-71a400cbc4c0",
      "title": "NRG Energy and UnitedHealth Are the S&P 500’s Best and Worst for May. Here’s Why.",
      "summary": "Investors flocked to shares of NRG as the energy supplier boosted capacity. UnitedHealth stock slumped, and the company’s CEO resigned.",
      "date": "2025-05-30",
      "thumbnailurl": "https://media.zenfs.com/en/Barrons.com/313d58a7bd78121327fe567942df304e",
      "alternate_thumbnailurl": "https://s.yimg.com/uu/api/res/1.2/IPnNwOM57KDU__ahZ_2Lmg--~B/Zmk9c3RyaW07aD0xMjg7dz0xNzA7YXBwaWQ9eXRhY2h5b24-/https://media.zenfs.com/en/Barrons.com/313d58a7bd78121327fe567942df304e",
      "canonicalUrl": "https://www.barrons.com/articles/nrg-stock-unitedhealth-sp-500-80596d4e?siteid=yhoof2&yptr=yahoo",
      "clickThroughUrl": null
    },
    ...
  ]
}
```

### Notes
- All endpoints return in JSON
- Historical data is cached in local SQLite database (equisight-backend.db)

### Running the app
1. Start the server:
```bash
uvicorn main:app --reload
```
