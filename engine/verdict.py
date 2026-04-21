"""
Strategy Verdict Engine
------------------------
Turns raw backtest metrics into a plain-English verdict on whether the
strategy is worth using vs. a passive Buy & Hold benchmark.

Pure function — no UI, no I/O. Takes metrics dicts in, returns a verdict dict.
"""

from typing import Literal

# ---------------------------------------------------------------------------
# Scoring thresholds
# ---------------------------------------------------------------------------
# Each check returns one of: "good", "okay", "bad"
# Overall rating is derived from the count of good vs. bad checks.

CAGR_EDGE_GOOD = 2.0       # beat B&H by >2% CAGR
CAGR_EDGE_BAD = -2.0       # underperform B&H by >2% CAGR

SHARPE_GOOD = 1.0
SHARPE_OKAY = 0.5

DD_BETTER_THRESHOLD = 5.0  # max drawdown at least 5% better (less negative) than B&H
DD_WORSE_THRESHOLD = 5.0   # max drawdown at least 5% worse (more negative) than B&H

TRADES_GOOD_MIN = 5
TRADES_GOOD_MAX = 50
TRADES_OKAY_MAX = 200
TRADES_INSUFFICIENT = 5    # below this, verdict cannot be trusted

WIN_RATE_GOOD = 55.0
WIN_RATE_OKAY = 40.0


Score = Literal["good", "okay", "bad"]
Rating = Literal["strong", "mixed", "weak", "insufficient"]


def _score_cagr_vs_benchmark(strategy_cagr: float, benchmark_cagr: float) -> tuple[Score, str]:
    edge = strategy_cagr - benchmark_cagr
    if edge >= CAGR_EDGE_GOOD:
        return "good", f"Beat Buy & Hold by +{edge:.2f}% CAGR"
    if edge <= CAGR_EDGE_BAD:
        return "bad", f"Lagged Buy & Hold by {edge:.2f}% CAGR"
    return "okay", f"Roughly matched Buy & Hold ({edge:+.2f}% CAGR)"


def _score_sharpe(sharpe: float) -> tuple[Score, str]:
    if sharpe >= SHARPE_GOOD:
        return "good", f"Strong risk-adjusted return (Sharpe {sharpe:.2f})"
    if sharpe >= SHARPE_OKAY:
        return "okay", f"Moderate risk-adjusted return (Sharpe {sharpe:.2f})"
    return "bad", f"Weak risk-adjusted return (Sharpe {sharpe:.2f})"


def _score_drawdown(strategy_dd: float, benchmark_dd: float) -> tuple[Score, str]:
    # Drawdowns are negative; "better" means closer to zero.
    diff = strategy_dd - benchmark_dd  # positive = strategy is less negative = better
    if diff >= DD_BETTER_THRESHOLD:
        return "good", f"Lower drawdown than Buy & Hold ({strategy_dd:.1f}% vs {benchmark_dd:.1f}%)"
    if diff <= -DD_WORSE_THRESHOLD:
        return "bad", f"Worse drawdown than Buy & Hold ({strategy_dd:.1f}% vs {benchmark_dd:.1f}%)"
    return "okay", f"Drawdown similar to Buy & Hold ({strategy_dd:.1f}% vs {benchmark_dd:.1f}%)"


def _score_trade_count(n_trades: int) -> tuple[Score, str]:
    if TRADES_GOOD_MIN <= n_trades <= TRADES_GOOD_MAX:
        return "good", f"Healthy trade frequency ({n_trades} trades)"
    if n_trades < TRADES_GOOD_MIN:
        return "bad", f"Too few trades ({n_trades}) — results may not be statistically robust"
    if n_trades <= TRADES_OKAY_MAX:
        return "okay", f"High trade frequency ({n_trades}) — watch transaction costs"
    return "bad", f"Excessive trading ({n_trades}) — likely over-trading"


def _score_win_rate(win_rate: float, n_trades: int) -> tuple[Score, str]:
    if n_trades < TRADES_INSUFFICIENT:
        return "okay", f"Win rate {win_rate:.0f}% (too few trades to judge)"
    if win_rate >= WIN_RATE_GOOD:
        return "good", f"High win rate ({win_rate:.0f}%)"
    if win_rate >= WIN_RATE_OKAY:
        return "okay", f"Moderate win rate ({win_rate:.0f}%)"
    return "bad", f"Low win rate ({win_rate:.0f}%)"


def _overall_rating(scores: list[Score], n_trades: int) -> Rating:
    if n_trades < TRADES_INSUFFICIENT:
        return "insufficient"
    good = scores.count("good")
    bad = scores.count("bad")
    if good >= 4 and bad == 0:
        return "strong"
    if bad >= 3 or (good == 0 and bad >= 2):
        return "weak"
    return "mixed"


def _headline(rating: Rating, strategy_cagr: float, benchmark_cagr: float,
              sharpe: float, n_trades: int) -> str:
    if rating == "insufficient":
        return (f"Only {n_trades} trades — not enough data to draw a verdict. "
                "Try a longer date range or different parameters.")
    edge = strategy_cagr - benchmark_cagr
    if rating == "strong":
        return (f"Strategy outperformed Buy & Hold by {edge:+.2f}% CAGR with "
                f"a strong Sharpe of {sharpe:.2f} across {n_trades} trades.")
    if rating == "weak":
        if edge < 0:
            return (f"Strategy underperformed: {edge:+.2f}% CAGR vs benchmark, "
                    f"Sharpe {sharpe:.2f}. Buy & Hold likely a better choice.")
        return (f"Despite a {edge:+.2f}% CAGR edge over Buy & Hold, weak Sharpe "
                f"({sharpe:.2f}) and other red flags suggest caution.")
    return (f"Mixed results: {edge:+.2f}% CAGR vs Buy & Hold, Sharpe {sharpe:.2f}. "
            "Some checks passed, some didn't — review the details below.")


def evaluate_strategy(metrics: dict, benchmark_metrics: dict) -> dict:
    """
    Score a backtest against its Buy & Hold benchmark.

    Parameters
    ----------
    metrics            : dict from compute_metrics() for the active strategy
    benchmark_metrics  : dict from compute_metrics() for Buy & Hold

    Returns
    -------
    dict with keys:
        rating          : "strong" | "mixed" | "weak" | "insufficient"
        headline        : one-sentence plain-English summary
        checks          : list of {name, score, message} per dimension
        good_count      : int
        bad_count       : int
    """
    n_trades = metrics["total_trades"]

    checks_raw = [
        ("Beats Buy & Hold",
         _score_cagr_vs_benchmark(metrics["cagr_pct"], benchmark_metrics["cagr_pct"])),
        ("Risk-adjusted return",
         _score_sharpe(metrics["sharpe_ratio"])),
        ("Drawdown control",
         _score_drawdown(metrics["max_drawdown_pct"], benchmark_metrics["max_drawdown_pct"])),
        ("Trade frequency",
         _score_trade_count(n_trades)),
        ("Win rate",
         _score_win_rate(metrics["win_rate_pct"], n_trades)),
    ]

    checks = [
        {"name": name, "score": score, "message": message}
        for name, (score, message) in checks_raw
    ]
    scores: list[Score] = [c["score"] for c in checks]

    rating = _overall_rating(scores, n_trades)
    headline = _headline(
        rating,
        metrics["cagr_pct"],
        benchmark_metrics["cagr_pct"],
        metrics["sharpe_ratio"],
        n_trades,
    )

    return {
        "rating": rating,
        "headline": headline,
        "checks": checks,
        "good_count": scores.count("good"),
        "bad_count": scores.count("bad"),
    }
