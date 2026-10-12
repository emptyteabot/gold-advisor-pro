# Gold Advisor Pro

A Streamlit research dashboard for A-share gold instruments. It combines market-regime detection, technical indicators, candlestick patterns, macro filters and multi-strategy voting into an inspectable signal view.

## Included

- Streamlit dashboard in `gold_advisor_app.py`.
- Market-data adapter in `ashare_provider.py`.
- Strategy and indicator engine in `gold_strategy_engine.py`.
- Configuration and feature tiers in `gold_config.py` and `license_manager.py`.

## Strategy components

- RSI, MACD, Bollinger Bands, moving averages, ATR, KDJ, Williams %R and OBV.
- Trend, range, crash and reversal regime classification.
- Entry, stop-loss, take-profit, confidence and risk/reward fields.
- Multi-signal voting and macro-bias filters.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run gold_advisor_app.py
```

## Status

Research prototype. Signals and backtests should be independently validated before any real-money use.
