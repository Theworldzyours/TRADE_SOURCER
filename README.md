# Trade Sourcer

> See what nobody else sees. Dark flow intelligence for weekly trading on Trade Republic.

**Status:** Rebuilding. Foundation exists, signal layer under construction.

## What This Does

Every Sunday morning, Trade Sourcer scans public data sources that most retail investors never touch:

- **SEC Form 4** — Insider buying/selling (who's putting their own money in?)
- **FINRA Dark Pool Data** — Off-exchange volume (where are institutions hiding?)
- **Options Flow** — Unusual options activity (who's making big leveraged bets?)
- **Congressional Trades** — Political stock purchases (who has legislative knowledge?)
- **Fail-to-Deliver** — Settlement failures (where's the short squeeze pressure?)
- **Short Interest** — Bearish positioning (where are the crowded shorts?)
- **Social Sentiment** — Reddit/WSB momentum (where's the retail wave building?)
- **13F Filings** — Institutional whale movements (what's Buffett buying?)

When multiple signals converge on the same stock, that's a **Dark Flow Alert** — the highest conviction setup.

The output is an HTML report with ranked trade ideas for the week, backed by hidden signals.

## Quick Start

```bash
pip install -r requirements.txt
python main.py
open reports/weekend_report_*.html
```

## Documentation

- **[VISION.md](VISION.md)** — Complete vision, signal definitions, data sources, architecture
- **[docs/planning/TODO.md](docs/planning/TODO.md)** — Work plan and progress
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — System architecture
- **[config/config.yaml](config/config.yaml)** — Configuration reference

## Project Structure

```
TRADE_SOURCER/
├── main.py                          # Main orchestrator
├── config/config.yaml               # Configuration
├── src/
│   ├── data_sources/                # Market data, SEC, FINRA, Tradier
│   ├── indicators/                  # Technical, fundamental, volatility
│   ├── signals/                     # Dark flow signal detectors (NEW)
│   ├── scoring/                     # Conviction engine
│   ├── ranking/                     # Filtering & ranking
│   ├── reports/                     # HTML report generation
│   └── utils/                       # Config, logging
├── data/                            # Stock universe, cached data
├── reports/                         # Generated reports
└── VISION.md                        # Seed document
```

## Disclaimer

This software is for informational and educational purposes only. It does not constitute financial advice. Always do your own research.

## License

MIT
