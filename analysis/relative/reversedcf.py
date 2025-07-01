import yfinance as yf
from analysis.analysis_services import (
    LARGE_NON_FINANCIAL,
    SMALL_NON_FINANCIAL,
    FINANCIAL,
    get_spread,
    get_spread_backup,
    COUNTRY_CRP,
    # ESTIMATED_R_D_EXPENSES,
)
import math
import numpy as np
from scipy.optimize import fsolve

EQUITY_RISK_PREMIUM = 4.02  # June 2025, from Damodaran
TERMINAL_GROWTH_RATE = 0.03  # Assumption


def get_avg_EBIT(income):
    res = 0
    for i in range(0, 4):
        ts = income.columns[i]
        ebit = income[ts].get("EBIT")
        res += ebit

    return res / 4


def get_avg_ebit_margin(income):
    sum = 0
    for i in range(0, 4):
        ts = income.columns[i]
        ebit = income[ts].get("EBIT")
        revenue = income[ts].get("Total Revenue")
        margin = ebit / revenue
        sum += margin

    return sum / 4


def get_nwc(balance_sheet):
    now = balance_sheet.columns[0]
    bs_now = balance_sheet[now]
    # nwc_now = bs_now['Current Assets'] - bs_now['Current Liabilities']
    st_debt_now = bs_now.get("Current Debt")
    nwc_now = (
        bs_now.get("Current Assets")
        - bs_now.get("Cash And Cash Equivalents")
        - (
            bs_now.get("Current Liabilities")
            - (
                0
                if st_debt_now is None
                or (isinstance(st_debt_now, float) and np.isnan(st_debt_now))
                else st_debt_now
            )
        )
    )

    return nwc_now


def get_unadjusted_net_capex(bs_now, bs_then):
    net_ppe_now = bs_now.get("Net PPE")
    net_ppe_then = bs_then.get("Net PPE")
    capex = net_ppe_now - net_ppe_then
    return capex


def get_avg_netCapex(income, cashflow, balance):
    # Assumption: R&D Amortization is 20%, Acquisition Amortization is 7.5%
    rd_amort = 0.2
    acq_amort = 0.075
    res = 0
    for i in range(0, 3):
        ts = cashflow.columns[i]
        ts_next = cashflow.columns[i + 1]
        rd = income[ts].get("Research And Development")
        rd = 0 if rd is None or isinstance(rd, float) and np.isnan(rd) else rd
        acquisition = -cashflow[ts].get("Purchase Of Business")
        acquisition = (
            0
            if acquisition is None
            or isinstance(acquisition, float)
            and np.isnan(acquisition)
            else acquisition
        )
        # print("RD: ", rd)
        # print("Acquisition: ", acquisition)
        unadj_net_capex = get_unadjusted_net_capex(balance[ts], balance[ts_next])
        adj_net_capex = (
            unadj_net_capex + rd * (1 - rd_amort) + acquisition * (1 - acq_amort)
        )
        res += adj_net_capex
    return res / 3


def get_avg_eps(income):
    sum = 0
    for i in range(0, 4):
        ts = income.columns[i]
        eps = income[ts].get("Diluted EPS")
        sum += eps

    return sum / 4


def reverse_dcf(ticker, terminal_growth_rate, high_growth_period):
    company = yf.Ticker(ticker)
    info = company.get_info()

    try:
        income_stmt = company.income_stmt
        balance_sheet = company.balance_sheet
        cashflow = company.cashflow
        latest_ts = income_stmt.columns[0]
        latest_income = income_stmt[latest_ts]
        latest_balance = balance_sheet[latest_ts]
        # latest_cf = cashflow[latest_ts]
    except Exception:
        raise Exception("Company does not have enough data to perform this analysis.")

    # Risk Free Rate
    rfr = float(yf.Ticker("^TNX").history(period="1d").iloc[0, 3])

    # Getting Equity Value
    price = info["regularMarketPrice"]
    diluted_shares = latest_income.get("Diluted Average Shares")
    equity_value = diluted_shares * price

    # Total Debt
    total_debt = latest_balance.get("Total Debt")

    # Effective Tax Rate
    effective_tax = latest_income.get("Tax Rate For Calcs")

    # Interest Expense
    interest_expense = latest_income["Interest Expense"]

    # EBIT
    ebit = latest_income.get("EBIT")
    # delNWC = get_del_nwc(balance_sheet)
    # netCapex = get_avg_netCapex(income_stmt, cashflow, balance_sheet)

    if ebit is None:
        # nopat = latest_cf.get('Free Cash Flow') + delNWC + netCapex
        # ebit = nopat/(1 - effective_tax)
        ebit = latest_income.get("Pretax Income")

    # else:
    #     nopat = ebit * (1 - effective_tax)

    nopat = ebit * (1 - effective_tax)

    # Getting Cost of Debt
    market_cap = info["marketCap"]
    if math.isnan(interest_expense):
        company_debt_spread = get_spread_backup(market_cap)
    else:
        sector = info["sector"]
        if sector == "Financial Services":
            company_type = FINANCIAL
        elif market_cap < 2e9:
            company_type = SMALL_NON_FINANCIAL
        else:
            company_type = LARGE_NON_FINANCIAL

        interest_coverage_ratio = ebit / interest_expense
        company_debt_spread = get_spread(interest_coverage_ratio, company_type)

    cost_of_debt = company_debt_spread + rfr

    # Getting Cost of Equity
    country = info["country"]
    crp = COUNTRY_CRP[country]
    beta = info["beta"]

    cost_of_equity = rfr + beta * EQUITY_RISK_PREMIUM + crp

    # Getting Weighted Average Cost of Capital (WACC)
    enterprise_value = total_debt + equity_value

    wacc = cost_of_debt * (total_debt / enterprise_value) + cost_of_equity * (
        equity_value / enterprise_value
    )
    wacc = wacc / 100
    # print("WACC: ", wacc)

    # Base Year FCFF
    latest_revenue = latest_income.get("Total Revenue")
    prev_revenue = income_stmt[income_stmt.columns[1]].get("Total Revenue")
    avg_ebit = get_avg_EBIT(income_stmt)
    avg_net_capex = get_avg_netCapex(income_stmt, cashflow, balance_sheet)
    net_capex_ebit_ratio = avg_net_capex / avg_ebit
    norm_net_capex = net_capex_ebit_ratio * ebit
    nwc = get_nwc(balance_sheet)
    norm_del_nwc = nwc / latest_revenue * (latest_revenue - prev_revenue)
    reinvestment_rate = (norm_del_nwc + norm_net_capex) / nopat
    base_fcff = nopat * (1 - reinvestment_rate)
    rr_stable = terminal_growth_rate / wacc

    def dcf_value(growth_rate):
        fcff_list = [
            base_fcff * ((1 + growth_rate) ** t)
            for t in range(1, high_growth_period + 1)
        ]
        dcf_sum = sum(
            [fcff / ((1 + wacc) ** (i + 1)) for i, fcff in enumerate(fcff_list)]
        )
        terminal_fcff = (
            fcff_list[-1]
            * (1 + terminal_growth_rate)
            / (1 - reinvestment_rate)
            * (1 - rr_stable)
        )
        terminal_value = terminal_fcff / (wacc - terminal_growth_rate)
        terminal_value_discounted = terminal_value / ((1 + wacc) ** high_growth_period)
        return dcf_sum + terminal_value_discounted

    # --- Objective: difference between DCF and EV ---
    def objective(g):
        return dcf_value(g) - enterprise_value

    implied_growth = fsolve(objective, x0=0.10)[0]
    # print("Implied Growth: ", implied_growth)

    # Graham Valuation
    avg_eps = get_avg_eps(income_stmt)

    # Graham's Formula
    value = avg_eps * (8.5 + (2 * implied_growth * 100))

    return {
        "Ticker": ticker,
        "Implied Growth": implied_growth,
        "WACC": wacc,
        "Graham Value": value,
    }
