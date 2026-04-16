import numpy as np
import pandas as pd

from strategies.rsi_mean_reversion import _compute_rsi, generate_signals


def _ohlcv_from_close(close: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": close,
            "High": close,
            "Low": close,
            "Close": close,
            "Volume": 1,
        },
        index=close.index,
    )


def test_rsi_monotonic_uptrend_reaches_100_not_nan() -> None:
    idx = pd.date_range("2024-01-01", periods=40, freq="D")
    close = pd.Series(np.arange(1, 41, dtype=float), index=idx)
    rsi = _compute_rsi(close, period=14)

    tail = rsi.dropna()
    assert not tail.empty
    assert np.isclose(tail.iloc[-1], 100.0)
    assert tail.notna().all()


def test_rsi_flat_series_converges_to_50() -> None:
    idx = pd.date_range("2024-01-01", periods=40, freq="D")
    close = pd.Series(100.0, index=idx)
    rsi = _compute_rsi(close, period=14)

    tail = rsi.dropna()
    assert not tail.empty
    assert np.isclose(tail.iloc[-1], 50.0)


def test_generate_signals_shape_and_columns() -> None:
    idx = pd.date_range("2024-01-01", periods=120, freq="D")
    close = pd.Series(np.linspace(100, 120, 120), index=idx)
    df = _ohlcv_from_close(close)

    out = generate_signals(df, rsi_period=14, oversold=30, overbought=70)

    assert "RSI" in out.columns
    assert "Signal" in out.columns
    assert "Position" in out.columns
    assert set(out["Position"].unique()).issubset({0, 1})
