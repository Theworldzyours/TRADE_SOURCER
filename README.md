# 📊 Trade Sourcer

> A Venture Capital approach to public markets - Systematic weekend stock analysis for **next week's trading opportunities**

## ✅ STATUS: FULLY WORKING

The application is **production-ready** and **fully functional**! Run demos now, or connect to real market data when ready.

## Overview

Trade Sourcer is an intelligent stock analysis application that evaluates leading indicators on weekends to source high-quality trading ideas for the upcoming week. It focuses exclusively on stocks tradable on Trade Republic and applies a venture capital investment framework to public equities.

**NEW**: Now includes **volatility analysis** and **next week price predictions** with indicative change intervals!

## 🎯 Key Features

- **Next Week Focus**: Analysis specifically designed for Monday-Friday trading opportunities
- **Volatility Analysis**: Comprehensive volatility metrics including historical, Parkinson, and ATR
- **Price Predictions**: Next week expected ranges with bear, base, and bull scenarios
- **Weekend Analysis**: Automated analysis runs on weekends to prepare for Monday trading
- **Trade Republic Focus**: Analyzes only stocks available on Trade Republic platform
- **VC Approach**: Evaluates stocks like a VC evaluates startups - growth, innovation, execution
- **Multi-Factor Scoring**: Combines technical, fundamental, volatility, and qualitative factors
- **Risk-Adjusted Rankings**: Categorizes opportunities by risk profile
- **Beautiful Reports**: Generates comprehensive HTML and CSV reports
- **Sector Diversification**: Ensures portfolio diversification guidelines

## 🏗️ Architecture

The application consists of several key modules:

### Data Sources
- **Trade Republic Universe**: Manages list of tradable stocks
- **Market Data**: Fetches historical prices, volume, and real-time data
- **Fundamental Data**: Company financials, growth metrics, profitability

### Analysis Engines
- **Technical Indicators**: RSI, MACD, Bollinger Bands, volume analysis
- **Fundamental Indicators**: Growth rates, margins, ROE, quality metrics
- **Volatility Analysis**: Historical volatility, Parkinson volatility, ATR, regime analysis
- **Next Week Predictions**: Expected price ranges with confidence intervals
- **Scenario Generation**: Bear, base, and bull case scenarios for upcoming week
- **VC Scoring**: Innovation, growth, team/execution, risk/reward analysis

### Output
- **Ranking System**: Filters and ranks stocks by composite score
- **Report Generator**: Creates beautiful HTML reports and CSV exports
- **Position Sizing**: Recommends allocation based on conviction

## 🚀 Quick Start

### Run Working Demo (No Network Required!)

```bash
# Complete end-to-end workflow with sample data
python3 demo_end_to_end.py

# View generated report
open reports/weekend_report_*.html
```

This generates real HTML reports and demonstrates all features working!

### Run With Real Market Data

```bash
# Install dependencies
pip install -r requirements-minimal.txt

# Run weekend analysis
python main.py

# View report
open reports/weekend_report_*.html
```

See [GETTING_CONNECTED.md](GETTING_CONNECTED.md) for detailed setup instructions.

### Configuration

Edit `config/config.yaml` to customize:

- **Filters**: Minimum market cap, volume, growth rates
- **Scoring Weights**: Adjust importance of different factors
- **Risk Management**: Position sizing, sector exposure limits
- **Technical Indicators**: RSI periods, MACD settings, etc.

## 📈 Scoring Methodology

### Composite Score (0-100)

The application calculates a composite score based on five key factors:

1. **Innovation Score (25%)**: Disruptive potential, competitive moat, pricing power
2. **Growth Score (25%)**: Revenue growth, earnings growth, margin expansion
3. **Team & Execution (15%)**: ROIC, ROE, capital allocation track record
4. **Risk/Reward (20%)**: Valuation, balance sheet strength, asymmetric upside
5. **Technical Setup (15%)**: Trend, momentum, volume confirmation

### Quality Filters

Before scoring, stocks must pass quality filters:
- Minimum market cap: €100M
- Minimum daily volume: 100K shares
- Minimum revenue growth: 15% YoY
- Debt-to-equity ratio: < 2.0
- Current ratio: > 1.0

### VC Approach

Unlike traditional stock screening, this application focuses on:
- **Long-term growth potential** (3-5 year horizon)
- **Asymmetric risk/reward** (3:1 minimum ratio)
- **Quality over quantity** (10-20 high-conviction ideas)
- **Catalyst-driven** (upcoming events that could drive stock higher)
- **Contrarian elements** (undervalued growth before mainstream)

## 📊 Sample Output

### Weekend Report Includes:

1. **Executive Summary**: Top 5 high-conviction ideas
2. **Detailed Analysis**: Complete breakdown of top 20 stocks
   - Composite score and grade (A+ to F)
   - Innovation, growth, and technical scores
   - Key metrics: revenue growth, margins, valuation
   - Position sizing recommendation
3. **Sector Allocation**: Diversification breakdown
4. **Complete List**: All stocks with scores
5. **Risk Warnings**: Concentration alerts

### Report Format

Reports are generated in multiple formats:
- **HTML**: Beautiful, interactive report with charts and next week predictions
- **CSV**: Raw data for further analysis
- **Console**: Quick summary printed to terminal

Each stock includes:
- **Current Analysis**: Technical and fundamental scores
- **Next Week Outlook**: Expected price range with confidence levels
- **Volatility Metrics**: Historical volatility and regime analysis  
- **Scenarios**: Bear (-1σ), Base (trend), Bull (+1σ) price targets
- **Position Sizing**: Conviction-based allocation recommendations

## 🛠️ Advanced Usage

### Custom Stock Universe

Edit the Trade Republic stock list:

```python
from src.data_sources.trade_republic import TradeRepublicUniverse

universe = TradeRepublicUniverse()
universe.add_stock('TICKER', 'Company Name', 'EXCHANGE', 'Sector')
```

### Analyze Specific Stocks

```python
from main import TradeSourcer

app = TradeSourcer()
results = app.run_analysis(tickers=['AAPL', 'MSFT', 'GOOGL'])
```

### Backtesting (Coming Soon)

```python
from src.backtesting import Backtester

backtester = Backtester()
results = backtester.run('2020-01-01', '2023-12-31')
```

## 📁 Project Structure

```
TRADE_SOURCER/
├── main.py                      # Main application entry point
├── requirements.txt             # Python dependencies
├── config/
│   └── config.yaml             # Configuration settings
├── src/
│   ├── data_sources/           # Data fetching modules
│   │   ├── market_data.py     # Market data fetcher
│   │   └── trade_republic.py  # Trade Republic universe
│   ├── indicators/             # Analysis modules
│   │   ├── technical.py       # Technical indicators
│   │   └── fundamental.py     # Fundamental indicators
│   ├── scoring/                # Scoring system
│   │   └── vc_scorer.py       # VC-style scorer
│   ├── ranking/                # Ranking and filtering
│   │   └── ranker.py          # Stock ranker
│   ├── reports/                # Report generation
│   │   └── report_generator.py
│   ├── backtesting/            # Backtesting (future)
│   └── utils/                  # Utility modules
│       ├── config_loader.py   # Configuration loader
│       └── logger.py          # Logging setup
├── data/                       # Data storage
│   └── trade_republic_stocks.csv
├── reports/                    # Generated reports
└── logs/                       # Application logs
```

## 🔧 Configuration Options

### Key Settings in `config.yaml`

**Analysis Schedule:**
```yaml
analysis:
  schedule_days: [5, 6]  # Saturday and Sunday
  schedule_time: "08:00"
  historical_days: 365
```

**Stock Filters:**
```yaml
filters:
  min_market_cap: 100_000_000    # €100M
  min_avg_volume: 100_000         # 100K shares/day
  min_revenue_growth: 0.15        # 15% YoY
```

**Scoring Weights:**
```yaml
scoring:
  innovation_weight: 0.25
  growth_weight: 0.25
  team_weight: 0.15
  risk_reward_weight: 0.20
  technical_weight: 0.15
```

## 📚 Documentation

For detailed documentation, see:
- [ARCHITECTURE.md](ARCHITECTURE.md) - Complete system architecture
- [config/config.yaml](config/config.yaml) - Configuration reference

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## ⚠️ Disclaimer

This software is for informational and educational purposes only. It does not constitute financial advice, investment advice, trading advice, or any other sort of advice. You should not treat any of the software's output or recommendations as such.

The software's analysis should not be relied upon for making investment decisions. Always do your own research and consult with a qualified financial advisor before making any investment decisions.

## 📄 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- Built with Python, pandas, yfinance, and other open-source libraries
- Inspired by venture capital investment frameworks
- Data sources: Yahoo Finance, Alpha Vantage (optional)

## 📧 Contact

For questions or feedback, please open an issue on GitHub.

---

**Happy Trading! 🚀📈**
