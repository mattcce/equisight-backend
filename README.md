# Endpoints

## Ticker Data

### Ticker Info

`GET /ticker/{ticker}/info`

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

### Ticker Historical Data

`GET /ticker/{ticker}/history`

**Parameters:**

- `start` (str, optional): Start date in `YYYY-MM-DD` (default: 30 days ago)
- `end` (str, optional): End date in `YYYY-MM-DD` (default: today)

**Usage Example:** `/ticker/{ticker}/history?start=2025-01-01&end=2025-05-05`

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

### Ticker News & Press Releases

`GET /ticker/{ticker}/news`

**Parameters:**

- `count` (int, optional): Number of articles to return (default: 10)

**Usage Example:** `/ticker/{ticker}/news?count=20`

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

### Ticker Intraday Data

`GET /ticker/{ticker}/intraday`

**Response Example:**
```json
{
  "marketOpen": 1749130200,
  "marketClose": 1749153600,
  "exchangeRate": 0.7772907018661499,
  "intraday": [
    {
      "ticker": "AAPL",
      "timestamp": 1749153540,
      "close": 200.5500030517578
    },
    ...
  ]
}
```

**Note:**
- If market is closed, it will return the intraday data from the latest trading day
- Currently only tickers on US, Singapore, Hong Kong, London, and Tokyo Stock Exchanges are supported


### Ticker Financial Metrics

`GET /ticker/{ticker}/quarterly-reports `

**Response Example:**
```json
{
  "ticker": "AAPL",
  "quarterlyReports": [
    {
      "ticker": "AAPL",
      "quarterEndDate": 1743379200,
      "revenue": 95359000000.0,
      "eps": 1.65,
      "ebitda": 32250000000.0,
      "netIncome": 24780000000.0,
      "totalAssets": 331233000000.0,
      "totalLiabilities": 264437000000.0,
      "shareholderEquity": 66796000000.0,
      "longTermDebt": 78566000000.0,
      "cashAndEquivalents": 28162000000.0,
      "operatingCashFlow": 23952000000.0,
      "freeCashFlow": 20881000000.0,
      "grossMargin": 0.47050619238876246,
      "roe": 0.3709802982214504,
      "roa": 0.07481138654663032,
      "debtToEquity": 3.958874782921133
    },
    ...
  ]
}
```

`GET /ticker/{ticker}/annual-reports `

**Response Example:**
```json
{
  "ticker": "AAPL",
  "annualReports": [
    {
      "ticker": "AAPL",
      "yearEndDate": 1727654400,
      "revenue": 391035000000.0,
      "eps": 6.08,
      "ebitda": 134661000000.0,
      "netIncome": 93736000000.0,
      "totalAssets": 364980000000.0,
      "totalLiabilities": 308030000000.0,
      "shareholderEquity": 56950000000.0,
      "longTermDebt": 85750000000.0,
      "cashAndEquivalents": 29943000000.0,
      "operatingCashFlow": 118254000000.0,
      "freeCashFlow": 108807000000.0,
      "grossMargin": 0.4620634981523393,
      "roe": 1.6459350307287095,
      "roa": 0.25682503150857583,
      "debtToEquity": 5.408779631255487
    },
    ...
  ]
}
```

### Foreign Exchange Rate

`GET /forex`

**Parameters:**

- `fromCur` (str, optional): Base Currency (default: USD)
- `toCur` (str, optional): New Currency (default: SGD)

**Usage Example:** `/forex?fromCur=USD&toCur=JPY`

**Response Example:**
```json
{
  "forexRate": 143.54200744628906
}
```
