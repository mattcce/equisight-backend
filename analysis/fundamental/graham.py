import yfinance as yf
from analysis.relative.reversedcf import reverse_dcf


def get_avg_eps(income):
    sum = 0
    for i in range(0, 4):
        ts = income.columns[i]
        eps = income[ts].get("Diluted EPS")
        sum += eps

    return sum / 4


def graham_valuation(ticker):
    company = yf.Ticker(ticker)
    # info = company.get_info()

    try:
        income_stmt = company.income_stmt
        # balance_sheet = company.balance_sheet
        # cashflow = company.cashflow
        # latest_ts = income_stmt.columns[0]
        # latest_income = income_stmt[latest_ts]
        # latest_balance = balance_sheet[latest_ts]
        # latest_cf = cashflow[latest_ts]
    except Exception:
        raise Exception("Company does not have enough data to perform this analysis.")

    implied_growth = reverse_dcf(ticker, 0.05, 8)

    avg_eps = get_avg_eps(income_stmt)

    value = avg_eps * (8.5 + (2 * implied_growth * 100))

    print("Graham value: ", value)

    return value


print(graham_valuation("GOOG"))
