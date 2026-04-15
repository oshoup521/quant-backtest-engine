"""
Strategy 1 — Moving Average Crossover (Trend Following)
--------------------------------------------------------
Buy  : Short-term SMA crosses ABOVE long-term SMA (Golden Cross)
Sell : Short-term SMA crosses BELOW long-term SMA (Death Cross)
"""

import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_SHORT_WINDOW: int = 50
DEFAULT_LONG_WINDOW: int = 200


def generate_signals(
    df: pd.DataFrame,
    short_window: int = DEFAULT_SHORT_WINDOW,
    long_window: int = DEFAULT_LONG_WINDOW,
) -> pd.DataFrame:
    """
    Add SMA columns and trade signals to the OHLCV DataFrame.

    Parameters
    ----------
    df           : pd.DataFrame  — OHLCV data with DatetimeIndex
    short_window : int           — period for short-term SMA
    long_window  : int           — period for long-term SMA

    Returns
    -------
    pd.DataFrame with additional columns:
        SMA_short, SMA_long, Signal (1/−1/0), Position (1/0)

    Raises
    ------
    ValueError
        If short_window >= long_window or data is insufficient.
    """
    if short_window >= long_window:
        raise ValueError(
            f"Short window ({short_window}) must be less than long window ({long_window})."
        )

    min_required = long_window + 1
    if len(df) < min_required:
        raise ValueError(
            f"Not enough data. Need at least {min_required} rows for a {long_window}-day SMA, "
            f"but only {len(df)} rows available. Extend your date range."
        )

    out = df.copy()
    out["SMA_short"] = out["Close"].rolling(window=short_window).mean()
    out["SMA_long"] = out["Close"].rolling(window=long_window).mean()

    # Raw signal: 1 when short > long, else 0
    out["_raw"] = np.where(out["SMA_short"] > out["SMA_long"], 1, 0)

    # Signal fires only on the crossover day (diff), not every day in trend
    out["Signal"] = out["_raw"].diff().fillna(0).astype(int)
    # +1 = buy crossover, -1 = sell crossover

    # Running position: 1 = in trade, 0 = out of trade
    out["Position"] = out["_raw"]

    out.drop(columns=["_raw"], inplace=True)
    return out


def get_strategy_name() -> str:
    return "Moving Average Crossover"
