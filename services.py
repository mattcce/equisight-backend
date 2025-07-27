import yfinance as yf
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import desc
from models import QuarterlyMetrics, AnnualMetrics
import numpy as np
import exchange_calendars as xcals
from datetime import datetime


# Exchange ISO
def getExchangeISO(tzn):
    match tzn:
        case "America/New_York":
            return "XNYS"
        case "Asia/Singapore":
            return "XSES"
        case "Asia/Hong_Kong":
            return "XHKG"
        case "Europe/London":
            return "XLON"
        case "Asia/Tokyo":
            return "XTKS"


# Exchange Timezone
def getExchangeHours(iso, dayStr):
    calendar = xcals.get_calendar(iso)
    schedule = calendar.schedule
    dayTimes = schedule.loc[dayStr] if dayStr in schedule.index else None
    openTs = None
    closeTs = None
    if dayTimes is not None:
        openTs = int(dayTimes["open"].timestamp())
        closeTs = int(dayTimes["close"].timestamp())
    return {"openTimestamp": openTs, "closeTimestamp": closeTs}


def getHoursWeek(iso, now):
    xc = xcals.get_calendar(iso)
    day = now.date()

    latest_session = None
    # Today is trading day
    if xc.is_session(day):
        mkt_open_tdy = xc.session_open(day)

        if now < mkt_open_tdy:
            latest_session = xc.previous_session(day)
        else:
            latest_session = day

    # Today is not trading day
    else:
        latest_session = xc.date_to_session(day, direction="previous")

    if latest_session is not None:
        past_five_trading_days = xc.sessions_window(latest_session, -5)

    oldest_day = past_five_trading_days[0]
    latest_day = past_five_trading_days[-1]
    oldest_open = xc.schedule.loc[oldest_day]["open"]
    latest_close = xc.schedule.loc[latest_day]["close"]

    return {
        "oldestOpen": int(oldest_open.timestamp()),
        "latestClose": int(latest_close.timestamp()),
    }


# Foreign Exchange Rates relative to SGD
def getForex(fromCur, toCur):
    if fromCur.upper() == toCur.upper():
        return 1.00
    ticker = f"{fromCur.upper()}{toCur.upper()}=X"
    marketState = yf.Ticker(ticker).info["marketState"]
    if marketState != "REGULAR":
        price = yf.Ticker(ticker).history(period="1d").iloc[0, 3]
        return price
    price = (
        yf.Ticker(ticker)
        .history(start=int(datetime.now().timestamp()) - 600, interval="1m")
        .iloc[-1, 3]
    )
    return price


def isCurrency(cur):
    if cur == "USD":
        return True
    ticker = f"{cur.upper()}USD=X"

    try:
        yf.Ticker(ticker).info
    except Exception:
        return False

    return True


# Convert NaN to None
def safe_get_metric(statement_series, key):
    value = statement_series.get(key)
    if value is None:
        return None
    if isinstance(value, float) and np.isnan(value):
        return None
    return value


def get_and_store_quarterly_metrics(
    ticker_obj: yf.Ticker, ticker_symbol: str, db: Session
):
    # Peek at yfinance to get the latest quarter date
    try:
        cashflow_peek = ticker_obj.quarterly_cashflow
        if cashflow_peek.empty:
            print(f"No quarterly data available from yfinance for {ticker_symbol}.")
            return []

        latest_yf_quarter = cashflow_peek.columns[0]
        if not isinstance(latest_yf_quarter, pd.Timestamp):
            print(
                f"Warning: Latest quarter column {latest_yf_quarter} is not a Timestamp."
            )
            latest_yf_quarter_unix = None
        else:
            latest_yf_quarter_unix = int(latest_yf_quarter.timestamp())

    except Exception as e:
        print(f"Error peeking at yfinance data for {ticker_symbol}: {e}")
        return []

    # Check if this latest quarter is already in db
    if latest_yf_quarter_unix is not None:
        latest_in_db = (
            db.query(QuarterlyMetrics)
            .filter_by(ticker=ticker_symbol, quarterEndDate=latest_yf_quarter_unix)
            .first()
        )

        if latest_in_db:
            print(
                f"Latest report for {ticker_symbol} (quarter ending {latest_yf_quarter.strftime('%Y-%m-%d')}) found in DB. Using cached data."
            )

            # Fetch up to 4 most recent quarters from DB
            cached_reports = (
                db.query(QuarterlyMetrics)
                .filter_by(ticker=ticker_symbol)
                .order_by(desc(QuarterlyMetrics.quarterEndDate))
                .limit(4)
                .all()
            )

            # Convert to list of dictionaries
            all_quarters_metrics_data = []
            for report in cached_reports:
                metrics_dict = {
                    column.name: getattr(report, column.name)
                    for column in QuarterlyMetrics.__table__.columns
                    if column.name != "id"
                }
                all_quarters_metrics_data.append(metrics_dict)

            return all_quarters_metrics_data

    # Latest quarter not in DB, proceed with yfinance fetch and store
    print(
        f"Latest report for {ticker_symbol} not in DB. Fetching from yfinance and updating cache."
    )

    try:
        income_q_df = ticker_obj.quarterly_income_stmt
        balance_q_df = ticker_obj.quarterly_balance_sheet
        cashflow_q_df = ticker_obj.quarterly_cashflow
    except Exception as e:
        print(
            f"Error fetching financial statements for {ticker_symbol} from yfinance: {e}"
        )
        return []

    all_quarters_metrics_data = []
    num_quarters_to_process = min(len(income_q_df.columns), 4)
    new_data_added = False

    for i in range(num_quarters_to_process):
        quarter_timestamp_col = income_q_df.columns[i]

        if not isinstance(quarter_timestamp_col, pd.Timestamp):
            print(
                f"Warning: Column {quarter_timestamp_col} is not a Timestamp. Skipping."
            )
            continue

        quarter_end_date_unix = int(quarter_timestamp_col.timestamp())

        # Check if this specific quarter already exists in DB
        existing_metrics = (
            db.query(QuarterlyMetrics)
            .filter_by(ticker=ticker_symbol, quarterEndDate=quarter_end_date_unix)
            .first()
        )

        if existing_metrics:
            # Use existing data from DB
            metrics_dict = {
                column.name: getattr(existing_metrics, column.name)
                for column in QuarterlyMetrics.__table__.columns
                if column.name != "id"
            }
            all_quarters_metrics_data.append(metrics_dict)
            continue

        # Process new quarter data from yfinance
        print(
            f"Processing new quarter {quarter_timestamp_col.strftime('%Y-%m-%d')} for {ticker_symbol}."
        )

        income_statement = income_q_df[quarter_timestamp_col]
        balance_sheet = balance_q_df[quarter_timestamp_col]
        cash_flow_statement = cashflow_q_df[quarter_timestamp_col]

        revenue = safe_get_metric(income_statement, "Total Revenue")
        eps = safe_get_metric(income_statement, "Diluted EPS")
        ebitda = safe_get_metric(income_statement, "EBITDA")
        net_income = safe_get_metric(income_statement, "Net Income")
        gross_profit = safe_get_metric(income_statement, "Gross Profit")

        total_assets = safe_get_metric(balance_sheet, "Total Assets")
        total_liabilities = None
        total_liabilities_keys = [
            "Total Liab",
            "Total Liabilities Net Minority Interest",
            "Total Liabilities",
        ]
        for key in total_liabilities_keys:
            val = safe_get_metric(balance_sheet, key)
            if val is not None:
                total_liabilities = val
                break

        shareholder_equity = safe_get_metric(balance_sheet, "Stockholders Equity")
        long_term_debt = safe_get_metric(
            balance_sheet, "Long Term Debt And Capital Lease Obligation"
        )
        cash_and_equivalents = safe_get_metric(
            balance_sheet, "Cash And Cash Equivalents"
        )

        operating_cf = safe_get_metric(cash_flow_statement, "Operating Cash Flow")
        free_cash_flow = safe_get_metric(cash_flow_statement, "Free Cash Flow")

        # Derived metrics
        gross_margin = (
            (gross_profit / revenue)
            if gross_profit is not None and revenue is not None and revenue != 0
            else None
        )

        debt_to_equity = (
            (total_liabilities / shareholder_equity)
            if total_liabilities is not None
            and shareholder_equity is not None
            and shareholder_equity != 0
            else None
        )

        current_quarter_data = {
            "ticker": ticker_symbol,
            "quarterEndDate": quarter_end_date_unix,
            "revenue": revenue,
            "eps": eps,
            "ebitda": ebitda,
            "netIncome": net_income,
            "totalAssets": total_assets,
            "totalLiabilities": total_liabilities,
            "shareholderEquity": shareholder_equity,
            "longTermDebt": long_term_debt,
            "cashAndEquivalents": cash_and_equivalents,
            "operatingCashFlow": operating_cf,
            "freeCashFlow": free_cash_flow,
            "grossMargin": gross_margin,
            "roe": None,
            "roa": None,
            "debtToEquity": debt_to_equity,
        }

        # Store in DB
        db_entry = QuarterlyMetrics(**current_quarter_data)
        db.add(db_entry)
        new_data_added = True

        all_quarters_metrics_data.append(current_quarter_data)

    # Only commit if new data was added
    if new_data_added:
        try:
            db.commit()
            print(f"Committed new quarterly metrics to DB for {ticker_symbol}.")
        except Exception as e:
            db.rollback()
            print(f"Error committing quarterly metrics to DB for {ticker_symbol}: {e}")

    return all_quarters_metrics_data


def get_and_store_annual_metrics(
    ticker_obj: yf.Ticker, ticker_symbol: str, db: Session
):
    # Peek at yfinance to get the latest year date
    try:
        income_peek = ticker_obj.income_stmt
        if income_peek.empty:
            print(f"No yearly data available from yfinance for {ticker_symbol}.")
            return []

        latest_yf_year = income_peek.columns[0]
        if not isinstance(latest_yf_year, pd.Timestamp):
            print(f"Warning: Latest year column {latest_yf_year} is not a Timestamp.")
            latest_yf_year_unix = None
        else:
            latest_yf_year_unix = int(latest_yf_year.timestamp())

    except Exception as e:
        print(f"Error peeking at yfinance data for {ticker_symbol}: {e}")
        return []

    # Check if this latest year is already in db
    if latest_yf_year_unix is not None:
        latest_in_db = (
            db.query(AnnualMetrics)
            .filter_by(ticker=ticker_symbol, yearEndDate=latest_yf_year_unix)
            .first()
        )

        if latest_in_db:
            print(
                f"Latest report for {ticker_symbol} (year ending {latest_yf_year.strftime('%Y-%m-%d')}) found in DB. Using cached data."
            )

            # Fetch up to 4 most recent years from DB
            cached_reports = (
                db.query(AnnualMetrics)
                .filter_by(ticker=ticker_symbol)
                .order_by(desc(AnnualMetrics.yearEndDate))
                .limit(4)
                .all()
            )

            # Convert to list of dictionaries
            all_years_metrics_data = []
            for report in cached_reports:
                metrics_dict = {
                    column.name: getattr(report, column.name)
                    for column in AnnualMetrics.__table__.columns
                    if column.name != "id"
                }
                all_years_metrics_data.append(metrics_dict)

            return all_years_metrics_data

    # Latest year not in DB, proceed with yfinance fetch and store
    print(
        f"Latest report for {ticker_symbol} not in DB. Fetching from yfinance and updating cache."
    )

    try:
        income_q_df = ticker_obj.income_stmt
        balance_q_df = ticker_obj.balance_sheet
        cashflow_q_df = ticker_obj.cashflow
    except Exception as e:
        print(
            f"Error fetching financial statements for {ticker_symbol} from yfinance: {e}"
        )
        return []

    metrics_data = []
    num_years_to_process = min(len(income_q_df.columns), 4)
    new_data_added = False

    for i in range(num_years_to_process):
        year_timestamp_col = income_q_df.columns[i]

        if not isinstance(year_timestamp_col, pd.Timestamp):
            print(f"Warning: Column {year_timestamp_col} is not a Timestamp. Skipping.")
            continue

        year_end_date_unix = int(year_timestamp_col.timestamp())

        # Check if this specific year already exists in DB
        existing_metrics = (
            db.query(AnnualMetrics)
            .filter_by(ticker=ticker_symbol, yearEndDate=year_end_date_unix)
            .first()
        )

        if existing_metrics:
            # Use existing data from DB
            metrics_dict = {
                column.name: getattr(existing_metrics, column.name)
                for column in AnnualMetrics.__table__.columns
                if column.name != "id"
            }
            metrics_data.append(metrics_dict)
            continue

        # Process new year data from yfinance
        print(
            f"Processing new year {year_timestamp_col.strftime('%Y-%m-%d')} for {ticker_symbol}."
        )

        income_statement = income_q_df[year_timestamp_col]
        balance_sheet = balance_q_df[year_timestamp_col]
        cash_flow_statement = cashflow_q_df[year_timestamp_col]

        revenue = safe_get_metric(income_statement, "Total Revenue")
        eps = safe_get_metric(income_statement, "Diluted EPS")
        ebitda = safe_get_metric(income_statement, "EBITDA")
        net_income = safe_get_metric(income_statement, "Net Income")
        gross_profit = safe_get_metric(income_statement, "Gross Profit")

        total_assets = safe_get_metric(balance_sheet, "Total Assets")
        total_liabilities = None
        total_liabilities_keys = [
            "Total Liab",
            "Total Liabilities Net Minority Interest",
            "Total Liabilities",
        ]
        for key in total_liabilities_keys:
            val = safe_get_metric(balance_sheet, key)
            if val is not None:
                total_liabilities = val
                break

        shareholder_equity = safe_get_metric(balance_sheet, "Stockholders Equity")
        long_term_debt = safe_get_metric(
            balance_sheet, "Long Term Debt And Capital Lease Obligation"
        )
        cash_and_equivalents = safe_get_metric(
            balance_sheet, "Cash And Cash Equivalents"
        )

        operating_cf = safe_get_metric(cash_flow_statement, "Operating Cash Flow")
        free_cash_flow = safe_get_metric(cash_flow_statement, "Free Cash Flow")

        # Derived metrics
        gross_margin = (
            (gross_profit / revenue)
            if gross_profit is not None and revenue is not None and revenue != 0
            else None
        )
        roe = (
            (net_income / shareholder_equity)
            if net_income is not None
            and shareholder_equity is not None
            and shareholder_equity != 0
            else None
        )
        roa = (
            (net_income / total_assets)
            if net_income is not None and total_assets is not None and total_assets != 0
            else None
        )
        debt_to_equity = (
            (total_liabilities / shareholder_equity)
            if total_liabilities is not None
            and shareholder_equity is not None
            and shareholder_equity != 0
            else None
        )

        current_year_data = {
            "ticker": ticker_symbol,
            "yearEndDate": year_end_date_unix,
            "revenue": revenue,
            "eps": eps,
            "ebitda": ebitda,
            "netIncome": net_income,
            "totalAssets": total_assets,
            "totalLiabilities": total_liabilities,
            "shareholderEquity": shareholder_equity,
            "longTermDebt": long_term_debt,
            "cashAndEquivalents": cash_and_equivalents,
            "operatingCashFlow": operating_cf,
            "freeCashFlow": free_cash_flow,
            "grossMargin": gross_margin,
            "roe": roe,
            "roa": roa,
            "debtToEquity": debt_to_equity,
        }

        # Store in DB
        db_entry = AnnualMetrics(**current_year_data)
        db.add(db_entry)
        new_data_added = True

        metrics_data.append(current_year_data)

    # Only commit if new data was added
    if new_data_added:
        try:
            db.commit()
            print(f"Committed new yearly metrics to DB for {ticker_symbol}.")
        except Exception as e:
            db.rollback()
            print(f"Error committing yearly metrics to DB for {ticker_symbol}: {e}")

    return metrics_data
