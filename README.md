# API Overview
## Overview
This is a FastAPI-based backend service that provides financial data, including stock ticker information, historical data, news, and financial reports. It also features analysis features (coming soon) and user authentication with a personalized watchlist functionality.

## Project Structure

The project is organized into several key files:
- `main.py`: The main application file that initializes the FastAPI app, includes middleware, and mounts the API routers.
- `database.py`: Handles database connection (SQLite), session management (sync and async), and initialization.
-   `models.py`: Contains all SQLAlchemy ORM models, defining the database table structures.
-   `schemas.py`: Includes all Pydantic models used for data validation, serialization, and API request/response schemas.
-   `services.py`: Holds the business logic, including fetching data from external APIs like `yfinance` and caching results in the database.
-   `auth.py`: Manages user authentication, registration, and user management using `fastapi-users`.
- `routers/`: A package containing the API routers for different parts of the application.
    - `ticker.py`: Contains all API endpoints related to ticker data (`/ticker/...`).
    - `watchlist.py`: Contains all API endpoints for the user watchlist (`/users/me/watchlist/...`).
    - `forex.py`: Contains the API endpoint for foreign exchange rates (`/forex`).

## Architecture and Design
### Architectural Overview
Equisight backend follows a layered architecture common in modern web apps:
- **Presentation Layer (`main.py`, `routers/`):** Build with FastAPI, responsible for handling HTTP requests, routing them to appropriate handlers, and managing request/response validation using Pydantic schemas from `schemas.py`
- **Business Logic Layer (`services.py`, `auth.py`):** Contains core application logic. `services.py` handles fetching and caching of data from external sources. `auth.py` manages user authentication and session management using `fastapi-users`
- **Data Access Layer (`database.py`, `models.py`):** Database interactions using SQLAlchemy as the ORM. `models.py` defines the database schema, while `database.py` manages database connection.
- **External Services:** The application integrates `yfinance` to retrieve real-time and historical financial data.

### Module Dependencies

The following diagram illustrates the primary dependencies between the modules:

```
+----------------------------------+
|    main.py (FastAPI App)         |
|  - Initializes DB                |
|  - Mounts Routers                |
+----------------------------------+
              |
              v
+----------------------------------+
|    routers/ (API Endpoints)      |
|  - watchlist.py, ticker.py, ...  |
+----------------------------------+
      |        |           |
      |        |           +--------------------+
      |        |                                |
      v        v                                v
+----------------+                     +----------------------+
|  services.py   |                     |       auth.py        |
| (Business Logic) |                     | (Auth & User Mgmt)   |
+----------------+                     +----------------------+
      |        |                                |
      |        +-----------------+--------------+
      |                          |
      v                          v
+----------------+     +----------------+     +----------------+
|   yfinance     |     |   database.py  |     |    models.py   |
|  (External)    |     |  (DB Session)  |     |   (ORM Tables) |
+----------------+     +----------------+     +----------------+
                                 ^                    ^
                                 |                    |
                                 +--------------------+
                                 |
                         +----------------+
                         |   schemas.py   |
                         | (Pydantic Models)|
                         +----------------+
```


## Endpoints

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

### Ticker Intraweek (Past 5 days) Data

`GET /ticker/{ticker}/intraweek`

**Response Example:**
```json
{
  "oldestOpen": 1749216600,
  "latestClose": 1749758400,
  "intraday": [
    {
      "ticker": "AAPL",
      "timestamp": 1749742200,
      "close": 198.22000122070312
    },
    ...
  ]
}
```

**Note:**
- If market is closed, it will return data for the past 5 trading days in 1h resolution
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
      "roe": null,
      "roa": null,
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

## User Specific Features

### User Watchlist

`GET /users/me/watchlist` (UNFINISHED)
**Description:** Returns positions and other details that user specifies about a watched ticker.

**Response Example:**
```json
{
  "identifier": "user@example.com",
  "tickers": [
    "MA",
    "UNH",
    "V"
  ]
}
```

`POST /users/me/watchlist/{ticker}`

**Description:** Adds a ticker to the user's watchlist. Empty request body.

**Response:** `201 Created` on success.


`DELETE /users/me/watchlist/{ticker}`
**Description:** Removes a ticker and all its associated positions from the watchlist.

**Response:** `204 No Content` on success.

`GET /users/me/watchlist/{ticker}`

**Usage Example:** `/users/me/watchlist/UNH`

**Response Example:**
```json
{
  "ticker": "UNH",
  "positions": [
    {
      "id": 18,
      "direction": "BUY",
      "quantity": 2.0,
      "unitCost": 300.0,
      "createdAt": 1750696547
    },
    ...
  ]
}
```
`POST /users/me/watchlist/{ticker}/positions`

**Description:** Adds one or more new positions for a ticker that is already in the user's watchlist.

**Request Example:**
```json
{
  "direction": "SELL",
  "quantity": 5,
  "unitCost": 500.00
}
```

**Response Example:**
```json
{
  "id": 2,
  "direction": "SELL",
  "quantity": 5,
  "unitCost": 500.00,
  "createdAt": 1750044120
}
```

`GET /users/me/watchlist/{ticker}/positions`

**Description:** Returns all positions that a user has in a watched ticker.

**Usage Example:** `/users/me/watchlist/UNH`

**Response Example:**
```json
{
  "ticker": "UNH",
  "positions": [
    {
      "id": 18,
      "direction": "BUY",
      "quantity": 2.0,
      "unitCost": 300.0,
      "createdAt": 1750696547
    },
    ...
  ]
}
```


`PUT /users/me/watchlist/{ticker}/positions/{positionId}`

**Description:** Updates/overrides an existing position, identified by its unique `positionId`.

**Request Example:**
```json
{
  "direction": "BUY",
  "quantity": 20,
  "unitCost": 825.50
}
```

**Response Example:**
```json
{
  "id": 1,
  "direction": "BUY",
  "quantity": 20,
  "unitCost": 825.50,
  "createdAt": 1750043545
}
```

`DELETE /users/me/watchlist/{ticker}/positions/{positionId}`

`GET /users/me/watchlist/{ticker}/positions/{positionId}`

**Description:** Outputs a particular position in a watched ticker by position ID.

**Response Example:**
```json
{
  "id": 1,
  "direction": "BUY",
  "quantity": 20,
  "unitCost": 825.50,
  "createdAt": 1750043545
}
```

**Description:** Deletes a specific position by its `positionId`.

**Response:** `204 No Content` on success.


## Miscellaneous
### Foreign Exchange Rate

`GET /forex`

**Parameters:**

- `fromCur` (str, optional): Base Currency (default: USD)
- `toCur` (str, optional): New Currency (default: SGD)

**Usage Example:** `/forex?fromCur=USD&toCur=JPY`

**Response Example:**
```json
{
  "fromCurrency": "USD",
  "toCurrency": "JPY",
  "forexRate": 143.54200744628906
}
```

## Authentication
The following authentication endpoints are available under the `/auth` prefix, largely provided by `fastapi-users`:

*   **`POST /auth/login`**: Logs in a user.
    *   Request Body: `OAuth2PasswordRequestForm` (expects `username` and `password` in form data).
    *   Response: Sets an authentication cookie (`equisightauth`) and returns user information ([`schemas.UserRead`](schemas.py)).
*   **`POST /auth/logout`**: Logs out a user.
    *   Response: Clears the authentication cookie.
*   **`POST /auth/register`**: Registers a new user.
    *   Request Body: [`schemas.UserCreate`](schemas.py) (email, password, username).
    *   Response: User information ([`schemas.UserRead`](schemas.py)).
*   **`POST /auth/forgot-password`**: Requests a password reset token.
    *   Request Body: Email of the user.
*   **`POST /auth/reset-password`**: Resets the password using a token.
    *   Request Body: Token and new password.
*   **`POST /auth/request-verify-token`**: Requests an email verification token.
    *   Request Body: Email of the user.
*   **`POST /auth/verify`**: Verifies the user's email using a token.
    *   Request Body: Verification token.
