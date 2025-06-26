# Backend API Features

## User Account Authentication and Data Storage

User account authentication is used to ensure user data can be uniquely identified to an individual, saved, and synced across different devices.

### Architecture

:::tip Implementation Status
This feature has been implemented.
:::

The backend uses a standard username/password scheme for authentication, powered by the `fastapi-users` library to ensure security best practices. When a user logs in successfully, a session cookie is returned to the client, which is then used to authenticate subsequent requests.

The following authentication-related endpoints are provided under the `/auth` prefix:
-   **Login/Logout**: Handles user login and logout.
-   **Registration**: Allows new users to create an account.
<!-- -   **Password Reset**: Provides a flow for users to reset their password.
-   **Email Verification**: Handles the verification of a user's email address. -->

### Design Decisions

We chose `fastapi-users` because it is a well-maintained, secure, and feature-rich library that handles the complexities of user authentication out of the box. This includes password hashing, token management, and email verification. Using a dedicated library saves significant development time and reduces the risk of security vulnerabilities that can arise from a custom implementation.

---

## Ticker API

Provides detailed financial information for a given stock ticker.

### Architecture

:::tip Implementation Status
This feature has been implemented.
:::

The Ticker API, available under the `/ticker` prefix, is the primary source of financial data for individual stocks. It fetches data from the `yfinance` library on-demand and caches it in a local database to improve performance and reduce reliance on the external API.

Key endpoints include:
-   `/{ticker}/info`: Retrieves general information about a company, such as its business summary, industry, and market cap.
-   `/{ticker}/history`: Provides historical price data for a specified date range. The backend caches historical data to speed up subsequent requests for the same date ranges.
-   `/{ticker}/quarterly-reports` and `/{ticker}/annual-reports`: Returns quarterly and annual metrics from the 3 financial statements (Income Statement, Balance Sheet, Cash Flow). This data is fetched and stored in the database.
-   `/{ticker}/intraday` & `/{ticker}/intraweek`: Delivers recent price data for the last day or week, respectively. This is designed to give users a view of recent price action.
-   `/{ticker}/news`: Delivers recent news published about the particular ticker.

### Design Decisions

The caching layer is a critical part of the Ticker API's design. Financial data APIs can have rate limits or costs associated with them. By caching results from `yfinance`, we can serve popular requests quickly from our own database, reducing latency for the end-user and minimizing the number of calls to the external API.

The API is designed to be RESTful, with logical and predictable endpoint URLs. This makes it easy for the frontend to consume and for developers to understand.

### Challenges

A significant challenge was handling the different timezones of various stock exchanges. To ensure that historical and intraday data is accurate, particularly the open and close timestamps of the exchanges that the respective tickers are traded in, the backend needs to be aware of the exchange's timezone. This information is fetched and stored alongside the ticker data.

Furthermore, due to the nature of the `exchange-calendars` API that fetches the data for any exchange, and how the codes for the exchange differ from the output from `yfinance`, we are only able to support ticker intraday and intraweek routes for the following regions: America/New York, Asia/Singapore, Asia/Hong Kong, Europe/London, and Asia/Tokyo.

Another challenge is data consistency. The `yfinance` library is a wrapper around Yahoo! Finance's public data, which can sometimes be inconsistent or unavailable. The backend has some implicit error handling, but more robust mechanisms could be added to handle cases where the external API fails or returns unexpected data.

---

## Watchlist API

Allows users to create and manage their personal watchlist of stocks.

### Architecture

:::tip Implementation Status
This feature has been implemented.
:::

The Watchlist API, under the `/watchlist` prefix, provides endpoints for managing a user's watchlist. It is tightly integrated with the authentication system to ensure that each user can only access their own watchlist.

The core functionalities are:
-   **Get Watchlist**: `GET /watchlist` - Retrieves the current user's watchlist in the form of an array of tickers.
-   **Add to Watchlist**: `POST /watchlist/{ticker}` - Adds a new ticker to the user's watchlist.
-   **Remove from Watchlist**: `DELETE /watchlist/{ticker}` - Removes a ticker and all its associated positions from the user's watchlist.
-   **Get Ticker Positions**: `GET /watchlist/{ticker}/positions` - Retrieves the current ticker's associated positions.
-   **Add Ticker Positions**: `POST /watchlist/{ticker}/positions` - Adds positions (single or multiple) to a user's watched ticker.
-   **Get Specific Position**: `GET /watchlist/{ticker}/positions/{positions_id}` - Retrieves a specific position based on its id.
-   **Update Specific Position**: `PUT /watchlist/{ticker}/positions/{positions_id}` - Updates a specific position based on its id.
-   **Delete Specific Position**: `DELETE /watchlist/{ticker}/positions/{positions_id}` - Deletes a specific position based on its id.

All watchlist data is stored in the application's database and linked to the user's account.

### Design Decisions

The API is designed to be stateful on the server. The user's watchlist is the single source of truth, stored in the database. This allows for data to be synced seamlessly across multiple devices. When the user makes a change on one device, it is reflected on all others upon the next data fetch.

The separation of watchlist management from the ticker data API allows for a clean, decoupled architecture. The watchlist service is only concerned with which tickers a user is interested in, not the financial data for those tickers.

---

## Forex API

Provides foreign exchange (forex) rates for currency conversion.

### Architecture

:::warning Implementation Status
This feature has been partially implemented. Caching and more robust error handling are planned.
:::

The Forex API, under the `/forex` prefix, is a simple service for retrieving currency exchange rates.

The main endpoint is:
-   `/forex?fromCUR=base&toCUR=quote`: Retrieves the latest exchange rate between a `base` currency and a `quote` currency (e.g., `/forex?fromCUR=SGD&toCUR=USD`).

Like the Ticker API, it uses the `yfinance` library as its data source.

### Design Decisions

This API was created to support currency conversion features in the frontend, such as displaying the total portfolio value in the user's preferred currency. By centralizing the forex logic in a dedicated API, we can easily add features like caching or switch to a different data provider in the future without affecting other parts of the backend.

### Challenges

The main challenge for the Forex API is the reliability and accuracy of the data source. For a production application, it would be important to use a more reliable, paid forex data provider to ensure users are seeing accurate conversion rates.
