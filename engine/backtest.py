"""
Core Backtesting Engine
------------------------
Simulates trade execution from strategy signals and produces:
  - portfolio_df : daily portfolio value over time
  - trade_log_df : one row per completed round-trip trade
"""

import pandas as pd
import numpy as np
from typing import Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_INITIAL_CAPITAL: float = 100_000.0
DEFAULT_TRANSACTION_COST: float = 0.001  # 0.1% per trade leg


def run_backtest(
    df: pd.DataFrame,
    initial_capital: float = DEFAULT_INITIAL_CAPITAL,
    transaction_cost: float = DEFAULT_TRANSACTION_COST,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Execute a backtest from pre-computed signals in `df`.

    Parameters
    ----------
    df               : pd.DataFrame
        OHLCV DataFrame with 'Signal' (1/−1/0) and 'Position' (1/0) columns.
    initial_capital  : float
        Starting portfolio value (default ₹1,00,000).
    transaction_cost : float
        Fraction of trade value charged on each leg (e.g. 0.001 = 0.1%).

    Returns
    -------
    portfolio_df : pd.DataFrame
        Index = DatetimeIndex, columns = ['Portfolio_Value', 'Daily_Return']
    trade_log_df : pd.DataFrame
        One row per completed trade with entry/exit details and P&L.
    """
    if "Signal" not in df.columns or "Position" not in df.columns:
        raise ValueError("DataFrame must contain 'Signal' and 'Position' columns.")

    cash = initial_capital
    shares = 0.0
    entry_price = 0.0
    entry_date = None

    portfolio_values = []
    trades = []

    for date, row in df.iterrows():
        signal = row["Signal"]
        close = row["Close"]

        # --- BUY signal (+1): enter long position ---
        if signal == 1 and shares == 0:
            effective_price = close * (1 + transaction_cost)
            shares = cash / effective_price
            cash = 0.0
            entry_price = effective_price
            entry_date = date

        # --- SELL signal (-1): exit long position ---
        elif signal == -1 and shares > 0:
            effective_price = close * (1 - transaction_cost)
            cash = shares * effective_price
            gross_return = (effective_price - entry_price) / entry_price * 100

            trades.append(
                {
                    "entry_date": entry_date,
                    "entry_price": round(entry_price, 4),
                    "exit_date": date,
                    "exit_price": round(effective_price, 4),
                    "return_pct": round(gross_return, 2),
                    "trade_type": "Long",
                    "duration_days": (date - entry_date).days,
                }
            )
            shares = 0.0
            entry_price = 0.0
            entry_date = None

        # --- Mark-to-market portfolio value ---
        portfolio_value = cash + shares * close
        portfolio_values.append({"Date": date, "Portfolio_Value": portfolio_value})

    portfolio_df = pd.DataFrame(portfolio_values).set_index("Date")
    portfolio_df["Daily_Return"] = portfolio_df["Portfolio_Value"].pct_change().fillna(0)

    trade_log_df = pd.DataFrame(trades) if trades else _empty_trade_log()

    return portfolio_df, trade_log_df


def _empty_trade_log() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "entry_date",
            "entry_price",
            "exit_date",
            "exit_price",
            "return_pct",
            "trade_type",
            "duration_days",
        ]
    )
