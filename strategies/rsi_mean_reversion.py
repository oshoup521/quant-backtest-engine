"""
Strategy 2 — RSI Mean Reversion
---------------------------------
Buy  : RSI drops BELOW oversold threshold (e.g. 30) → expect bounce up
Sell : RSI rises ABOVE overbought threshold (e.g. 70) → expect pullback

RSI uses Wilder's smoothing (EMA-based, equivalent to ewm with alpha=1/period).
"""

import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_RSI_PERIOD: int = 14
DEFAULT_OVERSOLD: int = 30
DEFAULT_OVERBOUGHT: int = 70


def _compute_rsi(close: pd.Series, period: int) -> pd.Series:
    """
    Compute RSI using Wilder's smoothing method.
    Returns a Series of RSI values (0–100), NaN for the first `period` rows.
    """
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # Wilder smoothing = EMA with alpha = 1/period
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def generate_signals(
    df: pd.DataFrame,
    rsi_period: int = DEFAULT_RSI_PERIOD,
    oversold: int = DEFAULT_OVERSOLD,
    overbought: int = DEFAULT_OVERBOUGHT,
) -> pd.DataFrame:
    """
    Add RSI column and trade signals to the OHLCV DataFrame.

    Parameters
    ----------
    df         : pd.DataFrame — OHLCV data with DatetimeIndex
    rsi_period : int          — lookback period for RSI calculation
    oversold   : int          — RSI level below which we buy (e.g. 30)
    overbought : int          — RSI level above which we sell (e.g. 70)

    Returns
    -------
    pd.DataFrame with additional columns:
        RSI, Signal (1/−1/0), Position (1/0)

    Raises
    ------
    ValueError
        If oversold >= overbought or insufficient data.
    """
    if oversold >= overbought:
        raise ValueError(
            f"Oversold ({oversold}) must be less than overbought ({overbought})."
        )

    min_required = rsi_period + 1
    if len(df) < min_required:
        raise ValueError(
            f"Need at least {min_required} rows for RSI({rsi_period}), "
            f"but only {len(df)} rows available."
        )

    out = df.copy()
    out["RSI"] = _compute_rsi(out["Close"], rsi_period)

    # Position logic: enter when RSI < oversold, exit when RSI > overbought
    position = pd.Series(np.nan, index=out.index)
    in_trade = False

    for i, (idx, row) in enumerate(out.iterrows()):
        if pd.isna(row["RSI"]):
            position.iloc[i] = 0
            continue
        if not in_trade and row["RSI"] < oversold:
            in_trade = True
        elif in_trade and row["RSI"] > overbought:
            in_trade = False
        position.iloc[i] = 1 if in_trade else 0

    out["Position"] = position.fillna(0).astype(int)

    # Signal: +1 on entry day, -1 on exit day
    out["Signal"] = out["Position"].diff().fillna(0).astype(int)

    return out


def get_strategy_name() -> str:
    return "RSI Mean Reversion"
