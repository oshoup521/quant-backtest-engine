"""
Strategy 3 — Buy & Hold Benchmark
-----------------------------------
Buy on the first available trading day, hold forever.
Used as the passive benchmark to evaluate whether active strategies
add value over simple compounding.
"""

import pandas as pd


def generate_signals(df: pd.DataFrame, **kwargs) -> pd.DataFrame:
    """
    Mark a single Buy signal on the first row; position = 1 throughout.

    Parameters
    ----------
    df : pd.DataFrame — OHLCV data with DatetimeIndex

    Returns
    -------
    pd.DataFrame with additional columns:
        Signal (1 on day 0, else 0), Position (always 1)
    """
    out = df.copy()
    out["Signal"] = 0
    out["Position"] = 1

    # Mark the first day as the buy signal
    out.iloc[0, out.columns.get_loc("Signal")] = 1

    return out


def get_strategy_name() -> str:
    return "Buy & Hold"
