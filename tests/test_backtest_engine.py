import pandas as pd

from engine.backtest import run_backtest
from strategies.buy_and_hold import generate_signals


def test_buy_and_hold_generates_portfolio_series() -> None:
    idx = pd.date_range("2024-01-01", periods=10, freq="D")
    df = pd.DataFrame(
        {
            "Open": [100 + i for i in range(10)],
            "High": [100 + i for i in range(10)],
            "Low": [100 + i for i in range(10)],
            "Close": [100 + i for i in range(10)],
            "Volume": [1000] * 10,
        },
        index=idx,
    )

    signals = generate_signals(df)
    portfolio_df, trade_log_df = run_backtest(signals, initial_capital=100_000, transaction_cost=0.001)

    assert len(portfolio_df) == len(df)
    assert "Portfolio_Value" in portfolio_df.columns
    assert "Daily_Return" in portfolio_df.columns
    assert trade_log_df.empty  # Buy & Hold has no exit in current implementation
