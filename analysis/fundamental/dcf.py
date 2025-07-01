import yfinance as yf
from analysis.analysis_services import (
    LARGE_NON_FINANCIAL,
    SMALL_NON_FINANCIAL,
    FINANCIAL,
    get_spread,
    get_spread_backup,
    COUNTRY_CRP,
    COUNTRY_TAX_RATES,
    # ESTIMATED_R_D_EXPENSES,
)
import math
import numpy as np

EQUITY_RISK_PREMIUM = 4.02  # June 2025, from Damodaran
TERMINAL_GROWTH_RATE = 0.03  # Assumption


def get_avg_invested_capital(balance_sheet):
    res = 0
    for i in range(0, 2):
        ts = balance_sheet.columns[i]
        data = balance_sheet[ts]
        res += data.get("Invested Capital")
        res += data.get("Goodwill and Other Intangible Assets") or 0
    return res / 2


# def get_del_nwc(balance_sheet):
#     now = balance_sheet.columns[0]
#     bs_now = balance_sheet[now]
#     # nwc_now = bs_now['Current Assets'] - bs_now['Current Liabilities']
#     st_debt_now = bs_now.get('Current Debt')
#     nwc_now = bs_now.get('Current Assets') - bs_now.get('Cash And Cash Equivalents') - (bs_now.get('Current Liabilities') - (0 if st_debt_now is None or (isinstance(st_debt_now, float) and np.isnan(st_debt_now)) else st_debt_now))
#     then = balance_sheet.columns[1]
#     bs_then = balance_sheet[then]
#     # nwc_then = bs_then['Current Assets'] - bs_then['Current Liabilities']
#     st_debt_then = bs_then.get('Current Debt')
#     nwc_then = bs_then.get('Current Assets') - bs_then.get('Cash And Cash Equivalents') - (bs_then.get('Current Liabilities') - (0 if st_debt_then is None or (isinstance(st_debt_then, float) and np.isnan(st_debt_then)) else st_debt_then))

#     return nwc_now - nwc_then


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


# def get_historical_fcf_growth(cashflow):
#     ts_now = cashflow.columns[0]
#     ts_then = cashflow.columns[3]
#     fcf_now = cashflow[ts_now].get('Free Cash Flow')
#     fcf_then = cashflow[ts_then].get('Free Cash Flow')
#     growth = (fcf_now / fcf_then)**(1/3) - 1
#     return growth * 100


def get_avg_EBIT(income):
    res = 0
    for i in range(0, 4):
        ts = income.columns[i]
        ebit = income[ts].get("EBIT")
        res += ebit

    return res / 4


# def get_avg_netCapex_og(income, cashflow, balance):
#     res = 0
#     for i in range(0,4):
#         ts = cashflow.columns[i]
#         depreciation = cashflow[ts].get('Depreciation Amortization Depletion')
#         rd = income[ts].get('Research And Development')
#         acquisition = -cashflow[ts].get('Purchase Of Business')
#         netCapex = (-cashflow[ts].get('Capital Expenditure')
#                     - (cashflow[ts].get('Depreciation') if depreciation is None or isinstance(depreciation, float) and np.isnan(depreciation) else depreciation)
#                     + (0 if rd is None or isinstance(rd, float) and np.isnan(rd) else rd)
#                     + (0 if acquisition is None or isinstance(acquisition, float) and np.isnan(acquisition) else acquisition))
#         res += netCapex

#     return res/4


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


def get_norm_debt_issued(balance_sheet, info, norm_del_nwc, norm_netCapex):
    ts = balance_sheet.columns[0]
    latest_bal = balance_sheet[ts]
    mkt_cap = info["marketCap"]
    debt = latest_bal["Total Debt"]
    debt_ratio = debt / (debt + mkt_cap)
    norm_debt_issued = (norm_del_nwc + norm_netCapex) * debt_ratio
    return norm_debt_issued


def get_avg_payout_ratio(income_stmt, cashflow):
    sum = 0
    for i in range(0, 4):
        ts = income_stmt.columns[i]
        ni = income_stmt[ts].get("Net Income")
        # dil_shares = income_stmt[ts].get("Diluted Average Shares")
        dpr = -cashflow[ts].get("Cash Dividends Paid") / ni
        sum += dpr

    return sum / 4


def get_norm_roe(income, balance):
    sum = 0
    for i in range(0, 4):
        ts = income.columns[i]
        ni = income[ts].get("Net Income")
        shareholder_equity = balance[ts].get("Stockholders Equity")
        roe = ni / shareholder_equity
        sum += roe
    return sum / 4


def get_leverage_stability(balance):
    values = []
    for i in range(0, 4):
        ts = balance.columns[i]
        debt = balance[ts].get("Total Debt")
        equity = balance[ts].get("Stockholders Equity")
        leverage = debt / equity
        values.append(leverage)
    mean = np.mean(values)
    std_dev = np.std(values)
    cv = std_dev / mean
    return cv < 0.10


def get_fcfe(
    income_statement,
    balance_sheet,
    cashflow,
    info,
    cost_of_equity,
    high_growth_period,
    stable_growth_period,
):
    avg_ebit = get_avg_EBIT(income_statement)
    avg_net_capex = get_avg_netCapex(income_statement, cashflow, balance_sheet)
    # avg_net_capex = get_avg_netCapex_og(income_statement, cashflow)
    net_capex_ebit_ratio = avg_net_capex / avg_ebit

    latest_ts = income_statement.columns[0]
    prev_ts = income_statement.columns[1]
    latest_ebit = income_statement[latest_ts].get("EBIT")

    # del_nwc = get_del_nwc(balance_sheet)
    nwc = get_nwc(balance_sheet)
    # print("nwc: ", nwc)
    latest_revenue = income_statement[latest_ts].get("Total Revenue")
    prev_revenue = income_statement[prev_ts].get("Total Revenue")

    net_income = income_statement[latest_ts].get("Net Income")

    norm_net_capex = net_capex_ebit_ratio * latest_ebit
    norm_del_nwc = nwc / latest_revenue * (latest_revenue - prev_revenue)
    norm_debt_issued = get_norm_debt_issued(
        balance_sheet, info, norm_del_nwc, norm_net_capex
    )
    norm_fcfe = net_income - norm_net_capex - norm_del_nwc + norm_debt_issued

    eq_reinvestment_rate = 1 - (norm_fcfe / net_income)
    shareholder_equity = balance_sheet[latest_ts].get("Stockholders Equity")
    roe = net_income / shareholder_equity
    # print("ROE: ", roe)

    expected_growth_rate = eq_reinvestment_rate * roe
    # print("Expected Equity Growth: ", expected_growth_rate)

    # Assumption: ROE drops to 20% in the long run
    # Assumption: Growth rate in perpetuity in net income is 5%
    roe_terminal = 0.20
    growth_rate_terminal = (
        0.04 if expected_growth_rate >= 0.04 else expected_growth_rate
    )
    eq_rr_stable = growth_rate_terminal / roe_terminal
    eq_rr_stable = (
        eq_rr_stable if eq_reinvestment_rate >= eq_rr_stable else eq_reinvestment_rate
    )

    if eq_reinvestment_rate >= 1:
        value_of_equity = neg_fcf_adj(
            roe,
            expected_growth_rate,
            growth_rate_terminal,
            high_growth_period,
            stable_growth_period,
            net_income,
            cost_of_equity,
        )

    else:
        sum = 0
        curr_per_ni = net_income
        for i in range(1, high_growth_period + 1):
            curr_per_ni = curr_per_ni * (1 + expected_growth_rate)
            fcfe = curr_per_ni * (1 - eq_reinvestment_rate)
            pv = fcfe / (1 + cost_of_equity) ** i
            sum += pv

        step_size = (expected_growth_rate - growth_rate_terminal) / stable_growth_period
        current_rate = expected_growth_rate
        for i in range(
            high_growth_period + 1, high_growth_period + stable_growth_period + 1
        ):
            current_rate = current_rate - step_size
            curr_per_ni = curr_per_ni * (1 + current_rate)
            fcfe = curr_per_ni * (1 - eq_reinvestment_rate)
            pv = fcfe / (1 + cost_of_equity) ** i
            sum += pv

        terminal_ni = curr_per_ni * (1 + growth_rate_terminal)
        terminal_fcfe = terminal_ni * (1 - eq_rr_stable)
        terminal_value = terminal_fcfe / (cost_of_equity - growth_rate_terminal)
        pv_of_tv = terminal_value / (1 + cost_of_equity) ** (
            high_growth_period + stable_growth_period
        )

        value_of_equity = sum + pv_of_tv
    diluted_shares = income_statement[latest_ts].get("Diluted Average Shares")
    value_per_share = value_of_equity / diluted_shares

    # print(f"FCFE Valuation: ROE: {roe}, netCapex: {norm_net_capex}, delNWC: {norm_del_nwc}, debt_issued: {norm_debt_issued}, norm_fcfe: {norm_fcfe}, net income: {net_income}, expected_growth: {expected_growth_rate}, eq_rr: {eq_reinvestment_rate}, eq_rr_stable: {eq_rr_stable}, sum: {sum}, terminal ni: {terminal_ni}, terminal: {terminal_value}, value of equity: {value_of_equity}")
    # print("Equity Valuation: ", value_per_share)

    return {"Value": value_per_share, "Expected Growth": expected_growth_rate}


def get_fcff(
    income_statement,
    balance_sheet,
    cashflow,
    info,
    wacc,
    high_growth_period,
    stable_growth_period,
    roc,
    terminal_growth_rate,
):
    avg_ebit = get_avg_EBIT(income_statement)
    avg_net_capex = get_avg_netCapex(income_statement, cashflow, balance_sheet)
    # avg_net_capex = get_avg_netCapex_og(income_statement, cashflow)
    net_capex_ebit_ratio = avg_net_capex / avg_ebit

    latest_ts = income_statement.columns[0]
    prev_ts = income_statement.columns[1]
    latest_ebit = income_statement[latest_ts].get("EBIT")
    effective_tax = income_statement[latest_ts].get("Tax Rate For Calcs")
    nopat = latest_ebit * (1 - effective_tax)

    nwc = get_nwc(balance_sheet)
    # print("nwc: ", nwc)
    latest_revenue = income_statement[latest_ts].get("Total Revenue")
    prev_revenue = income_statement[prev_ts].get("Total Revenue")

    norm_net_capex = net_capex_ebit_ratio * latest_ebit
    norm_del_nwc = nwc / latest_revenue * (latest_revenue - prev_revenue)
    # del_nwc = get_del_nwc(balance_sheet)
    # alpha = 0.75
    # norm_del_nwc = alpha * del_nwc + (1 - alpha) * norm_del_nwc
    # norm_fcff = nopat - norm_del_nwc - norm_net_capex

    reinvestment_rate = (norm_del_nwc + norm_net_capex) / nopat
    expected_growth_rate = reinvestment_rate * roc
    # print("Expected Firm Growth: ", expected_growth_rate)

    # Assumption: Growth rate in perpetuity is fixed
    growth_rate_terminal = (
        terminal_growth_rate
        if expected_growth_rate >= terminal_growth_rate
        else expected_growth_rate
    )
    # terminal_roc = (roc + wacc) / 2
    terminal_roc = wacc
    rr_stable = growth_rate_terminal / terminal_roc
    rr_stable = rr_stable if reinvestment_rate >= rr_stable else reinvestment_rate
    # print("nopat: ", nopat)
    # print("norm_capex: ", norm_net_capex)
    # print("norm nwc: ", norm_del_nwc)
    # print("Reinvestment Rate: ", reinvestment_rate)
    # print("Reinvestment Rate Stable: ", rr_stable)

    if reinvestment_rate >= 1:
        value_of_firm = neg_fcf_adj(
            roc,
            expected_growth_rate,
            growth_rate_terminal,
            high_growth_period,
            stable_growth_period,
            nopat,
            wacc,
        )

    else:
        sum = 0
        curr_per_nopat = nopat
        for i in range(1, high_growth_period + 1):
            curr_per_nopat = curr_per_nopat * (1 + expected_growth_rate)
            fcff = curr_per_nopat * (1 - reinvestment_rate)
            # print("fcff: ", fcff)
            # print(f"FCFF for year {i}: {fcff}")
            pv = fcff / (1 + wacc) ** i
            sum += pv

        step_size = (expected_growth_rate - growth_rate_terminal) / stable_growth_period
        current_rate = expected_growth_rate
        for i in range(
            high_growth_period + 1, high_growth_period + stable_growth_period + 1
        ):
            current_rate = current_rate - step_size
            # print("Current Rate: ", current_rate)
            curr_per_nopat = curr_per_nopat * (1 + current_rate)
            fcff = curr_per_nopat * (1 - reinvestment_rate)
            pv = fcff / (1 + wacc) ** i
            sum += pv

        terminal_nopat = curr_per_nopat * (1 + growth_rate_terminal)
        terminal_fcff = terminal_nopat * (1 - rr_stable)
        terminal_value = terminal_fcff / (wacc - growth_rate_terminal)
        pv_of_tv = terminal_value / (1 + wacc) ** (
            high_growth_period + stable_growth_period
        )

        value_of_firm = sum + pv_of_tv
    diluted_shares = income_statement[latest_ts].get("Diluted Average Shares")
    # print("Value of Firm: ", value_of_firm)
    value_per_share = value_of_firm / diluted_shares

    # print(f"FCFF Valuation: netCapex: {norm_net_capex}, delNWC: {norm_del_nwc}, norm_fcff: {norm_fcff}, expected_growth: {expected_growth_rate}, rr: {reinvestment_rate}, rr_stable: {rr_stable}, sum: {sum}, terminal_nopat: {terminal_nopat}, terminal: {terminal_value}, value of firm: {value_of_firm}")
    # print("Firm Valuation: ", value_per_share)

    return {"Value": value_per_share, "Expected Growth": expected_growth_rate}


def get_ni_cagr(income_stmt):
    ts_now = income_stmt.columns[0]
    ts_then = income_stmt.columns[3]
    ni_now = income_stmt[ts_now].get("Net Income")
    ni_then = income_stmt[ts_then].get("Net Income")
    cagr = (ni_now / ni_then) ** (1 / 3) - 1
    return cagr


def get_excess_return_valuation(
    bve,
    cost_of_equity,
    norm_roe,
    high_growth_period,
    income_stmt,
    cashflow,
    terminal_growth_rate,
    industry,
):
    avg_payout_ratio = get_avg_payout_ratio(income_stmt, cashflow)
    base_net_income = bve * norm_roe
    retained_earnings = base_net_income * (1 - avg_payout_ratio)
    curr_bve = bve + retained_earnings
    if (
        industry != "banks-diversified"
        and industry != "banks-regional"
        and industry != "capital-markets"
    ):
        ni_cagr = get_ni_cagr(income_stmt)
        term_roe = ni_cagr / (1 - avg_payout_ratio) if ni_cagr > 0 else norm_roe
    else:
        term_roe = norm_roe
    step_size = (norm_roe - term_roe) / (high_growth_period + 1)
    roe = norm_roe
    sum = 0
    for i in range(1, high_growth_period + 1):
        net_income = curr_bve * roe
        retained_earnings = net_income * (1 - avg_payout_ratio)
        excess_returns = net_income - (curr_bve * cost_of_equity)
        pv = excess_returns / (1 + cost_of_equity) ** i
        sum += pv
        curr_bve = curr_bve + retained_earnings
        roe = roe - step_size

    terminal_value = ((term_roe - cost_of_equity) * curr_bve) / (
        cost_of_equity - terminal_growth_rate
    )
    pv_of_tv = terminal_value / (1 + cost_of_equity) ** (high_growth_period + 1)

    value = pv_of_tv + sum
    latest_ts = income_stmt.columns[0]
    diluted_shares = income_stmt[latest_ts].get("Diluted Average Shares")
    value_per_share = value / diluted_shares
    # print("Excess Valuation: ", value_per_share)
    return {"Value": value_per_share, "Expected Growth": 0}


def neg_fcf_adj(
    roc,
    growth,
    growth_stable,
    high_growth_period,
    stable_growth_period,
    base,
    discount_factor,
):
    step_size = (growth - growth_stable) / (high_growth_period + 1)
    growth_rate = growth + step_size
    curr_per_base = base
    sum = 0
    for i in range(1, high_growth_period + 1):
        growth_rate = growth_rate - step_size
        reinvestment_rate = growth_rate / roc
        curr_per_base = curr_per_base * (1 + growth_rate)
        fcf = curr_per_base * (1 - reinvestment_rate)
        # print("FCF: ", fcf)
        pv = fcf / (1 + discount_factor) ** i
        sum += pv

    rr_stable = growth_stable / roc
    for i in range(
        high_growth_period + 1, high_growth_period + stable_growth_period + 1
    ):
        curr_per_base = curr_per_base * (1 + growth_stable)
        fcf = curr_per_base * (1 - reinvestment_rate)
        pv = fcf / (1 + discount_factor) ** i
        sum += pv

    terminal_base = curr_per_base * (1 + growth_stable)
    terminal_fcf = terminal_base * (1 - rr_stable)
    terminal_value = terminal_fcf / (discount_factor - growth_stable)
    pv_of_tv = terminal_value / (1 + discount_factor) ** (
        high_growth_period + stable_growth_period
    )

    value = sum + pv_of_tv
    return value


def fair_value(ticker, period_of_high_growth, period_of_stable_growth):
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

    # Determine ROIC
    average_invested_capital = get_avg_invested_capital(balance_sheet)

    roic = nopat / average_invested_capital * 100  # In percentage

    # Determine ROC
    # minority_interest = latest_balance.get('Minority Interest')
    # minority_interest = (0 if minority_interest is None or isinstance(minority_interest, float) and np.isnan(minority_interest) else minority_interest)
    # bve = latest_balance.get('Total Equity Gross Minority Interest') - minority_interest
    bve = latest_balance.get("Stockholders Equity")
    bvd = latest_balance.get("Total Debt")
    ctry_marginal_tax = COUNTRY_TAX_RATES[country]
    roc = ebit * (1 - ctry_marginal_tax) / (bve + bvd) * 100
    stability = get_leverage_stability(balance_sheet)
    fair_value_of_firm = 0

    if info["sectorKey"] == "financial-services":
        # Excess Return Valuation (For Financial Firms)
        norm_roe = get_norm_roe(income_stmt, balance_sheet)
        # print("Norm ROE:", norm_roe)
        value = get_excess_return_valuation(
            bve,
            cost_of_equity / 100,
            norm_roe,
            period_of_high_growth,
            income_stmt,
            cashflow,
            0.05,
            info["industryKey"],
        )

    else:
        if stability:
            # FCFE
            value = get_fcfe(
                income_stmt,
                balance_sheet,
                cashflow,
                info,
                cost_of_equity / 100,
                period_of_high_growth,
                period_of_stable_growth,
            )
            # return fcfe_value

        else:
            # FCFF
            # print("Free Cash Flow: ", latest_cf.get('Free Cash Flow'))
            value = get_fcff(
                income_stmt,
                balance_sheet,
                cashflow,
                info,
                wacc / 100,
                period_of_high_growth,
                period_of_stable_growth,
                roic / 100,
                0.05,
            )

        fair_value_of_firm = value["Value"]
        expected_growth = value["Expected Growth"]

    return {
        "Ticker": ticker,
        "Cost of Equity": cost_of_equity,
        "Cost of Debt": cost_of_debt,
        "WACC": wacc,
        "ROIC": roic,
        "ROC": roc,
        "Fair Value": fair_value_of_firm,
        "Expected Growth Rate": expected_growth * 100,
    }


# FCFE: Stable Leverage firms (Debt/Equity Ratio is stable)
