# Trade Sourcer - Usage Guide

## Table of Contents
1. [Getting Started](#getting-started)
2. [Running Analysis](#running-analysis)
3. [Understanding Reports](#understanding-reports)
4. [Customization](#customization)
5. [Advanced Features](#advanced-features)
6. [Troubleshooting](#troubleshooting)

## Getting Started

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Theworldzyours/TRADE_SOURCER.git
   cd TRADE_SOURCER
   ```

2. **Run the setup script:**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```
   
   Or install manually:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure API keys (optional):**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

### Quick Test

Run the quick start example with a few stocks:

```bash
python quick_start.py
```

This will analyze 5 popular stocks (AAPL, MSFT, GOOGL, TSLA, NVDA) and generate a sample report.

## Running Analysis

### Full Weekend Analysis

Analyze all stocks in the Trade Republic universe:

```bash
python main.py
```

This will:
1. Load all stocks from `data/trade_republic_stocks.csv`
2. Fetch market data for each stock
3. Calculate technical indicators
4. Analyze fundamentals
5. Score and rank all stocks
6. Generate HTML and CSV reports in `reports/`

**Note:** Full analysis may take 10-30 minutes depending on the number of stocks.

### Analyze Specific Stocks

Create a custom Python script:

```python
from main import TradeSourcer

app = TradeSourcer()
results = app.run_analysis(tickers=['AAPL', 'MSFT', 'GOOGL'])
```

### Scheduled Analysis

To run analysis automatically on weekends, use cron:

```bash
# Edit crontab
crontab -e

# Add this line to run every Saturday at 8 AM
0 8 * * 6 cd /path/to/TRADE_SOURCER && /path/to/venv/bin/python main.py
```

## Understanding Reports

### Report Location

Reports are saved in the `reports/` directory with timestamp:
- `weekend_report_YYYYMMDD.html` - HTML report
- `stocks_data_YYYYMMDD.csv` - CSV data export

### HTML Report Sections

#### 1. Executive Summary
- Total opportunities found
- Average score
- Diversification warnings

#### 2. Top 5 Ideas
Detailed cards for the highest-scoring stocks including:
- **Composite Score**: Overall rating (0-100)
- **Grade**: Letter grade (A+ to F)
- **Innovation Score**: Disruptive potential
- **Growth Score**: Revenue/earnings growth
- **Technical Score**: Chart setup quality
- **Position Size**: Recommended allocation

#### 3. Sector Allocation
Table showing sector diversification:
- Number of stocks per sector
- Percentage allocation
- Warnings if over-concentrated

#### 4. Complete List
Table with all qualifying stocks sorted by score

### Understanding Scores

**Composite Score (0-100):**
- **90-100 (A+/A)**: Exceptional opportunity, high conviction
- **80-89 (A-/B+)**: Strong opportunity, medium-high conviction
- **70-79 (B/B-)**: Good opportunity, medium conviction
- **60-69 (C+/C)**: Acceptable opportunity, low-medium conviction
- **Below 60**: Does not meet quality threshold

**Score Components:**
- **Innovation (25%)**: Competitive moat, pricing power, sector leadership
- **Growth (25%)**: Revenue/earnings growth, margin expansion
- **Team (15%)**: Capital allocation, ROE, ROIC
- **Risk/Reward (20%)**: Valuation, balance sheet, upside potential
- **Technical (15%)**: Trend, momentum, volume

### Interpreting Metrics

**Key Fundamental Metrics:**
- **Revenue Growth**: YoY revenue growth rate (target: >15%)
- **Gross Margin**: Profitability indicator (target: >20%)
- **Debt to Equity**: Leverage ratio (target: <2.0)
- **Current Ratio**: Liquidity (target: >1.0)
- **ROE**: Return on equity (target: >15%)

**Key Technical Metrics:**
- **RSI**: Overbought (>70) or oversold (<30)
- **MACD**: Bullish or bearish momentum
- **Trend**: Uptrend, downtrend, or neutral
- **Volume**: Above or below average

## Customization

### Adjusting Filters

Edit `config/config.yaml`:

```yaml
filters:
  min_market_cap: 100_000_000    # Minimum €100M
  min_avg_volume: 100_000         # Minimum 100K shares/day
  min_revenue_growth: 0.15        # Minimum 15% YoY growth
  min_gross_margin: 0.20          # Minimum 20% margin
```

### Adjusting Scoring Weights

Customize the importance of different factors:

```yaml
scoring:
  innovation_weight: 0.30     # Increase innovation importance
  growth_weight: 0.25
  team_weight: 0.15
  risk_reward_weight: 0.15
  technical_weight: 0.15      # Decrease technical importance
```

### Adjusting Technical Indicators

Customize indicator parameters:

```yaml
technical_indicators:
  rsi_period: 14              # RSI calculation period
  rsi_oversold: 30            # Oversold threshold
  rsi_overbought: 70          # Overbought threshold
  macd_fast: 12               # MACD fast EMA
  macd_slow: 26               # MACD slow EMA
```

### Managing Stock Universe

Add stocks to analyze:

```python
from src.data_sources.trade_republic import TradeRepublicUniverse

universe = TradeRepublicUniverse()
universe.add_stock('SHOP', 'Shopify Inc.', 'NYSE', 'Technology')
```

Or directly edit `data/trade_republic_stocks.csv`:

```csv
ticker,name,exchange,sector,active,added_date
SHOP,Shopify Inc.,NYSE,Technology,True,2024-01-01
```

## Advanced Features

### Custom Scoring Logic

Create your own scorer:

```python
from src.scoring.vc_scorer import VCScorer

class MyCustomScorer(VCScorer):
    def _calculate_innovation_score(self, fundamental, additional):
        # Your custom logic
        score = super()._calculate_innovation_score(fundamental, additional)
        # Add custom adjustments
        return score
```

### Integrating Additional Data

Add sentiment analysis, insider trading, or other data:

```python
def _analyze_stock(self, ticker):
    # Standard analysis
    result = super()._analyze_stock(ticker)
    
    # Add custom data
    result['sentiment_score'] = get_sentiment(ticker)
    result['insider_buying'] = get_insider_activity(ticker)
    
    return result
```

### Backtesting

Test your strategy on historical data (coming soon):

```python
from src.backtesting import Backtester

backtester = Backtester()
results = backtester.run(
    start_date='2020-01-01',
    end_date='2023-12-31',
    initial_capital=100000
)
```

## Troubleshooting

### Common Issues

**1. "No module named 'talib'"**

TA-Lib requires system-level installation:

```bash
# macOS
brew install ta-lib

# Ubuntu/Debian
sudo apt-get install ta-lib

# Then reinstall Python package
pip install ta-lib
```

Or use pandas-ta as alternative (already in requirements).

**2. "No data found for ticker"**

- Check if ticker is correct
- Verify internet connection
- Try with different ticker
- Check if stock exists on yfinance

**3. Rate limiting errors**

Adjust rate limiting in `config.yaml`:

```yaml
data_sources:
  requests_per_minute: 5    # Reduce this number
  retry_attempts: 3
  retry_delay: 5            # Increase delay
```

**4. Out of memory errors**

Reduce the number of stocks analyzed:

```python
# Analyze in batches
tickers = universe.get_active_tickers()
batch_size = 10

for i in range(0, len(tickers), batch_size):
    batch = tickers[i:i+batch_size]
    results = app.run_analysis(tickers=batch)
```

### Getting Help

1. Check the logs in `logs/trade_sourcer.log`
2. Review configuration in `config/config.yaml`
3. Test with quick_start.py first
4. Open an issue on GitHub with error details

### Best Practices

1. **Start Small**: Test with quick_start.py before full analysis
2. **Review Configuration**: Understand all settings before running
3. **Check Reports**: Review HTML reports for data quality
4. **Iterate**: Adjust filters and weights based on results
5. **Backup**: Keep copies of good configurations
6. **Schedule**: Run on weekends when markets are closed

## Next Steps

1. Run `quick_start.py` to see the application in action
2. Review the generated HTML report
3. Customize `config/config.yaml` to match your criteria
4. Run full analysis with `main.py`
5. Review and refine based on results
6. Set up automated weekend runs

## Support

For questions or issues:
- GitHub Issues: https://github.com/Theworldzyours/TRADE_SOURCER/issues
- Documentation: See ARCHITECTURE.md for technical details

---

**Happy Trading! 📈🚀**
