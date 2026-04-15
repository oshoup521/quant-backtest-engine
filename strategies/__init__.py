from strategies import ma_crossover, rsi_mean_reversion, buy_and_hold

STRATEGY_MAP = {
    "Moving Average Crossover": ma_crossover,
    "RSI Mean Reversion": rsi_mean_reversion,
    "Buy & Hold": buy_and_hold,
}
