"""
Quantitative Metrics Calculator
---------------------------------
Computes all performance statistics from portfolio and trade log DataFrames.
"""

import pandas as pd
import numpy as np
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TRADING_DAYS_PER_YEAR: int = 252
DEFAULT_RISK_FREE_RATE: float = 0.06  # 6% annualised (India benchmark)


def compute_metrics(
    portfolio_df: pd.DataFrame,
    trade_log_df: pd.DataFrame,
    initial_capital: float,
    risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
) -> dict:
    """
    Compute full suite of quantitative performance metrics.

    Parameters
    ----------
    portfolio_df    : daily portfolio value with 'Portfolio_Value' column
    trade_log_df    : trade log from engine.backtest.run_backtest
    initial_capital : float — starting portfolio value
    risk_free_rate  : float — annual risk-free rate (default 6% for India)

    Returns
    -------
    dict with keys:
        total_return_pct, cagr_pct, max_drawdown_pct, sharpe_ratio,
        win_rate_pct, total_trades, avg_duration_days,
        best_trade_pct, worst_trade_pct
    """
    pv = portfolio_df["Portfolio_Value"]
    final_value = pv.iloc[-1]
    n_days = len(pv)
    n_years = n_days / TRADING_DAYS_PER_YEAR

    # --- Total Return ---
    total_return_pct = (final_value - initial_capital) / initial_capital * 100

    # --- CAGR ---
    if n_years > 0:
        cagr_pct = ((final_value / initial_capital) ** (1 / n_years) - 1) * 100
    else:
        cagr_pct = 0.0

    # --- Maximum Drawdown ---
    rolling_max = pv.cummax()
    drawdown_series = (pv - rolling_max) / rolling_max * 100
    max_drawdown_pct = drawdown_series.min()  # most negative value

    # --- Sharpe Ratio ---
    daily_returns = portfolio_df["Daily_Return"]
    rf_daily = risk_free_rate / TRADING_DAYS_PER_YEAR
    excess = daily_returns - rf_daily
    std = excess.std()
    sharpe_ratio = (excess.mean() / std * np.sqrt(TRADING_DAYS_PER_YEAR)) if std > 0 else 0.0

    # --- Trade statistics ---
    if not trade_log_df.empty:
        total_trades = len(trade_log_df)
        winning_trades = (trade_log_df["return_pct"] > 0).sum()
        win_rate_pct = winning_trades / total_trades * 100
        avg_duration_days = trade_log_df["duration_days"].mean()
        best_trade_pct = trade_log_df["return_pct"].max()
        worst_trade_pct = trade_log_df["return_pct"].min()
    else:
        total_trades = 0
        win_rate_pct = 0.0
        avg_duration_days = 0.0
        best_trade_pct = 0.0
        worst_trade_pct = 0.0

    return {
        "total_return_pct": round(total_return_pct, 2),
        "cagr_pct": round(cagr_pct, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "sharpe_ratio": round(sharpe_ratio, 3),
        "win_rate_pct": round(win_rate_pct, 1),
        "total_trades": total_trades,
        "avg_duration_days": round(avg_duration_days, 1),
        "best_trade_pct": round(best_trade_pct, 2),
        "worst_trade_pct": round(worst_trade_pct, 2),
    }


def compute_drawdown_series(portfolio_df: pd.DataFrame) -> pd.Series:
    """Return the full drawdown series (%) for charting."""
    pv = portfolio_df["Portfolio_Value"]
    rolling_max = pv.cummax()
    return (pv - rolling_max) / rolling_max * 100
