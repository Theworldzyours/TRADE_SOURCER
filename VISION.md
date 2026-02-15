# Trade Sourcer — Vision & Seed Document

> **See what nobody else sees.** A dark flow intelligence system that surfaces insider movements, institutional accumulation, unusual options activity, and hidden signals — delivered every Sunday morning for the week ahead.

**Last Updated:** 2026-02-15
**Status:** Rebuilding — foundation exists, signal layer is new

---

## Table of Contents

1. [The Problem](#the-problem)
2. [The Vision](#the-vision)
3. [Who This Is For](#who-this-is-for)
4. [The Eight Signals](#the-eight-signals)
5. [Signal Convergence](#signal-convergence)
6. [Data Sources & APIs](#data-sources--apis)
7. [Architecture](#architecture)
8. [The Conviction Engine](#the-conviction-engine)
9. [The Weekly Report](#the-weekly-report)
10. [Trade Republic Universe](#trade-republic-universe)
11. [Current State Assessment](#current-state-assessment)
12. [Work Plan](#work-plan)
13. [Constraints & Non-Goals](#constraints--non-goals)

---

## The Problem

Every retail investor has access to the same tools: RSI, MACD, P/E ratios, moving averages. These are lagging indicators. By the time a stock shows a bullish RSI crossover, the smart money has already positioned.

**The real edge isn't in technical analysis. It's in information asymmetry.**

Insiders know their company's trajectory before earnings. Institutions accumulate positions in dark pools before the price moves. Politicians trade on legislative knowledge weeks before bills pass. Options market makers see the flow before anyone else.

All of this information is **public** — SEC filings, FINRA data, congressional disclosures — but it's scattered across dozens of sources, published in obscure formats, and requires significant effort to collect, parse, and interpret.

**Trade Sourcer assembles these hidden signals into a single weekly intelligence report.**

---

## The Vision

**Every Sunday morning, Trade Sourcer runs.** It pulls the latest data from SEC EDGAR, FINRA, options chains, congressional disclosures, and social platforms. It detects patterns:

- Three C-suite insiders bought $2M of their own stock this week
- Dark pool short volume dropped 40% on a mid-cap while price was flat (accumulation)
- Someone swept $500K in out-of-the-money calls expiring in 3 weeks
- A senator with an 80% hit rate just disclosed a large purchase
- Fail-to-deliver spiked 10x on a heavily shorted stock

When **multiple signals converge on the same ticker**, that's a high-conviction setup. Trade Sourcer scores this confluence and surfaces the strongest opportunities.

**The output:** A beautiful HTML report with:
- Dark Flow Alerts (3+ signals aligned)
- Insider Cluster Buys
- Unusual Options Activity
- Congressional Trades
- Signal timeline (when each signal fired)
- Position sizing based on conviction
- Risk warnings

**What you get Monday morning:** 5-15 high-conviction trade ideas backed by hidden signals that 99% of retail investors never see.

---

## Who This Is For

**Marc.** A Trade Republic user in the EU who:
- Trades weekly, makes decisions on Sunday for Monday-Friday
- Wants a VC-like approach: quality over quantity, asymmetric risk/reward
- Wants to see the institutional playbook, not the retail playbook
- Has no interest in day trading or HFT
- Wants automation: run it, read the report, make decisions

---

## The Eight Signals

### Signal 1: Insider Trading (SEC Form 4)

**What it is.** When corporate insiders — CEOs, CFOs, board members, 10% owners — buy or sell their own company's stock, they must file a Form 4 with the SEC within 2 business days. This is the closest thing to legal inside information that exists in public markets.

**Why it matters.** Insiders know their company better than any analyst. When a CEO spends $500K of their own money buying shares, they're betting their personal wealth on something they know. Academic studies consistently show:

- **Insider cluster buys** (3+ insiders buying within 2 weeks) outperform the market by **7-13% over the following 12 months** (Lakonishok & Lee, 2001; Jeng, Metrick & Zeckhauser, 2003)
- CEO/CFO purchases are **stronger signals** than director purchases — they have the deepest knowledge
- Insider buying during price dips is the strongest signal of all — they're buying when others are selling
- Insider selling is **noisy** — insiders sell for many reasons (taxes, diversification, home purchase). Only unusual selling patterns matter.

**How to read it.**

| Pattern | Signal Strength | Interpretation |
|---------|----------------|----------------|
| CEO buys >$500K | Very Strong | CEO putting real money where mouth is |
| 3+ insiders buy within 14 days | Very Strong | Cluster buy — multiple people seeing the same thing |
| Insider buys after 20%+ price drop | Strong | Insider thinks the drop is overdone |
| Director buys small amount | Weak | Could be routine, board obligation |
| CFO sells everything | Strong Bearish | CFO knows the numbers best |
| Routine scheduled sales (10b5-1) | Noise | Pre-planned, ignore these |

**Real examples.**
- **JPMorgan 2012:** Jamie Dimon bought $26.6M in JPM shares after the London Whale losses. Stock recovered 40%+ within a year.
- **Fortinet 2023:** Multiple insiders bought aggressively during a dip. Stock rebounded 50%+ in the following months.
- **Insider selling before Enron collapse:** Executives sold $1.1B before bankruptcy. The anti-pattern.

**Limitations.**
- Insiders can be wrong. They're optimistic about their own company by nature.
- Form 4 must be filed within 2 days, but some file late.
- Routine 10b5-1 plan sales are noise — filter these out.
- Insider buying in micro-caps can be manipulation.

---

### Signal 2: Dark Pool / Off-Exchange Volume

**What it is.** Dark pools are private trading venues where institutional investors (hedge funds, pension funds, mutual funds) execute large orders without displaying them on public exchanges. About **40-50% of all US equity trading** now happens off-exchange. FINRA publishes daily short sale volume data that reveals dark pool activity.

**Why it matters.** When a large institution wants to buy 10 million shares, they can't just place a market order on NASDAQ — it would spike the price. Instead, they route through dark pools to accumulate quietly. The footprint they leave is in the FINRA data: changes in short volume ratio, off-exchange volume spikes, and accumulation/distribution patterns.

**How to read it.**

The key metric is the **dark pool short volume ratio** (short volume / total volume from FINRA data):

| Pattern | Interpretation |
|---------|----------------|
| Short ratio **dropping** while price flat | Institutions shifting from shorting to buying — **accumulation** |
| Short ratio **spiking** above 60% | Heavy institutional short selling — **distribution** |
| Off-exchange volume **surging** vs. 20-day avg | Large institutional activity — something is happening |
| Short ratio dropping + price rising | Confirmation of bullish institutional flow |
| Short ratio stable at 45-55% | Normal market making activity — **noise** |

**Important nuance:** "Short volume" in FINRA data does NOT mean all those trades are bearish bets. Market makers routinely sell short as part of legitimate market making. The signal is in the **change** from baseline, not the absolute level.

**Real examples.**
- **Tesla 2020:** Dark pool accumulation patterns were visible for weeks before the parabolic run-up. Short ratio dropped while institutional buying quietly built positions.
- **GameStop Jan 2021:** Dark pool data showed massive off-exchange volume weeks before the squeeze — institutions were positioning.
- **Apple 2023:** Consistent dark pool accumulation during the October 2023 dip preceded a 20%+ rally.

**Limitations.**
- FINRA short sale volume is a **proxy**, not actual dark pool data. True dark pool prints require paid services.
- 1-day delay on FINRA data.
- Market maker short selling creates noise in the signal.
- The ATS (Alternative Trading System) data has a 2-4 week delay for individual security-level data.

---

### Signal 3: Unusual Options Activity

**What it is.** When someone places a large bet in the options market — especially when the volume of contracts traded far exceeds the existing open interest — it signals informed money positioning ahead of an expected move. These trades are called "unusual" because they deviate significantly from normal patterns.

**Why it matters.** Options give leverage. If you know a stock is going up, buying call options is far more profitable than buying stock. Smart money — hedge funds, prop desks, well-connected traders — often use options to position before events. The options market frequently **leads** the stock market by days or weeks.

**Key concepts:**

- **Sweep orders:** Large orders broken into smaller pieces and routed across multiple exchanges simultaneously for immediate execution. This urgency signals conviction — the buyer wants the position NOW and doesn't care about getting the best price.
- **Block trades:** Single large orders negotiated privately. Often institutional.
- **Volume > Open Interest:** When today's trading volume exceeds the total number of existing contracts, it means new positions are being opened aggressively. This is the strongest indicator of informed money.
- **Premium spent:** The total dollar amount spent on the trade. A $2M call sweep carries far more weight than a $20K one.

**How to read it.**

| Pattern | Signal | Strength |
|---------|--------|----------|
| Call sweeps, volume >> OI, near-term expiry | Bullish | Very Strong |
| Put sweeps, volume >> OI, near-term expiry | Bearish | Very Strong |
| Large OTM call purchases, 2-4 weeks out | Someone expects a catalyst | Strong |
| Repeated call buying across multiple strikes | Building a large bullish position | Strong |
| Put selling (selling to open) | Bullish (willing to buy at strike price) | Moderate |
| Straddle/strangle purchases | Expecting big move, direction unknown | Moderate |

**Real examples.**
- **Bristol-Myers Squibb / Celgene 2019:** Unusual call activity in Celgene surged days before the $74B acquisition announcement.
- **Nvidia 2023-2024:** Persistent unusual call buying preceded each major AI-driven rally leg.
- **Twitter/X 2022:** Unusual call sweeps appeared before Elon Musk's 13D filing revealed his 9.2% stake.

**Limitations.**
- Not all unusual activity is informed. Hedging looks like betting.
- Market makers delta-hedge, creating secondary flow that can be misread.
- Options flow services often lag — by the time you see it, the move may have started.
- Expiration timing matters: weekly options decay fast. Monthly options give more time to be right.

---

### Signal 4: Congressional / Political Trading

**What it is.** Under the STOCK Act (2012), members of the US Congress must publicly disclose stock trades within 45 days. These disclosures reveal what politicians — who sit on committees with access to non-public information about regulations, contracts, and legislation — are buying and selling.

**Why it matters.** Multiple studies have found that congressional stock portfolios significantly outperform the market:

- A 2004 study by Ziobrowski et al. found **Senate portfolios outperformed by ~12% annually**
- Unusual Whales' 2023 Congressional Trading Report showed **several members beating the S&P 500 by 20%+**
- Politicians trade ahead of legislation, defense contracts, FDA approvals, and regulatory actions

**How to read it.**

| Pattern | Signal |
|---------|--------|
| Committee member buys stock in regulated industry | Strong — potential legislative knowledge |
| Multiple politicians buy same stock within weeks | Very Strong — something is coming |
| Large purchase (>$100K) by politician with good track record | Strong |
| Speaker/leadership purchase | Strong — they control the legislative calendar |
| Small routine purchases | Noise — could be financial advisor |

**Notable track records:**
- **Nancy Pelosi:** Consistently ahead of the market on tech trades. Her husband's Nvidia calls in 2022-2023 preceded the AI rally.
- **Dan Crenshaw:** Strong tech and energy trades
- **Tommy Tuberville:** Defense and energy sector trades with notable timing

**Real examples.**
- **Pelosi NVDA/GOOGL 2022-2023:** Pelosi's household purchased Nvidia and Google calls months before the AI boom and CHIPS Act benefits.
- **PPE/Vaccine trades 2020:** Multiple senators sold stocks and bought pandemic beneficiaries before COVID lockdowns were announced.
- **Semiconductors 2022:** Several politicians purchased semiconductor stocks weeks before the CHIPS Act passed.

**Limitations.**
- 45-day disclosure delay means the trade is old by the time you see it. Still historically alpha-generating.
- Some trades are made by financial advisors, not the politician directly.
- The STOCK Act has weak enforcement — late filings are common with minimal penalties.
- Signal works best when combined with knowledge of what committees the politician serves on.

---

### Signal 5: Fail-to-Deliver (FTD)

**What it is.** When someone sells a stock but fails to deliver the actual shares within the standard settlement period (T+1), it creates a Fail-to-Deliver. The SEC publishes FTD data twice monthly. Large or persistent FTDs can indicate naked short selling — selling shares that don't actually exist.

**Why it matters.** FTD spikes can signal:
- Naked short selling pressure (creating artificial supply)
- Shares being hard to borrow (heavily shorted stocks)
- Settlement system stress that can precede forced buying (short squeezes)
- When FTDs pile up, market makers may be forced to buy shares to satisfy delivery obligations, creating upward price pressure.

**How to read it.**

| Pattern | Signal |
|---------|--------|
| FTD spike 5x+ above 20-day average | Something unusual — heavy short activity |
| Persistent high FTDs over multiple periods | Ongoing settlement stress — squeeze potential |
| FTD drops suddenly after spike | Forced covering — watch for price movement |
| Stock on SEC Threshold List (13+ days of high FTDs) | Regulatory attention, potential forced buy-in |
| FTD spike + high short interest + low float | Classic short squeeze setup |

**Real examples.**
- **GameStop (Jan 2021):** FTDs were elevated for weeks before the squeeze. Combined with 140%+ short interest and low float, this was the perfect storm.
- **AMC 2021:** Similar FTD pattern preceded the retail-driven squeeze.
- **Bed Bath & Beyond 2022:** FTD spikes preceded the August 2022 squeeze.

**Limitations.**
- FTD data has a ~30-day delay. It's better for pattern analysis than real-time trading.
- FTDs can result from administrative errors, not just naked shorting.
- The data is cumulative, not incremental — you need to calculate changes yourself.
- FTD alone is not enough. It needs to be combined with short interest and float data.

---

### Signal 6: Short Interest & Short Sale Volume

**What it is.** Short interest measures the total number of shares currently sold short. Short sale volume measures daily short selling activity. Together, they reveal how much of the market is betting against a stock — and when that bet becomes crowded enough to explode.

**Why it matters.** Shorting is a conviction trade with unlimited loss potential. When short interest gets too high relative to the available float, and a catalyst appears, the resulting **short squeeze** can produce extreme price movements. Even without a squeeze, declining short interest signals that bears are capitulating — a bullish indicator.

**Key metrics:**

| Metric | Formula | What It Tells You |
|--------|---------|-------------------|
| Short Interest (SI) | Shares short / total shares | How much of the stock is shorted |
| Short % of Float | Shares short / float shares | How crowded the short trade is |
| Days to Cover | Shares short / avg daily volume | How long it would take shorts to cover |
| Short Sale Ratio | Daily short volume / daily total volume | Intraday short selling pressure |

**How to read it.**

| Pattern | Signal |
|---------|--------|
| SI > 20% of float | Heavily shorted — squeeze candidate |
| Days to Cover > 5 | Very crowded — hard to exit quickly |
| SI declining + price rising | Short covering rally — bullish confirmation |
| SI increasing + price falling | Bears piling on — could reverse violently |
| Short sale ratio dropping from highs | Shorts stepping back — potential bottom |

**Real examples.**
- **GameStop 2021:** 140% short interest (more shares shorted than existed). The mother of all squeezes.
- **Volkswagen 2008:** Porsche's hidden accumulation + high short interest = infinite squeeze to briefly become the world's most valuable company.
- **Tesla 2020:** Years of heavy shorting unwound in one of the biggest short squeezes in history as the stock went from $30 to $400+ (split-adjusted).

**Limitations.**
- FINRA short interest is published only **twice monthly** with an 11-day delay.
- Daily short sale volume is a proxy — it includes market maker activity.
- High short interest alone isn't a catalyst. Stocks can stay heavily shorted for months.
- Short squeezes are rare events. Most heavily shorted stocks are shorted for good reason.

---

### Signal 7: Social Sentiment / Retail Flow

**What it is.** The collective sentiment of retail investors expressed on platforms like Reddit (r/wallstreetbets, r/stocks), StockTwits, Twitter/X, and other social platforms. Mention velocity (how fast mentions are accelerating), sentiment (bullish vs. bearish language), and upvote momentum can signal emerging retail interest before it hits mainstream.

**Why it matters.** In 2021, retail investors proved they can move markets. When a stock catches fire on WSB, the resulting buying pressure is real. The key is detecting the acceleration **early** — before it's on the front page.

**How to read it.**

| Pattern | Signal |
|---------|--------|
| Mention velocity accelerating (3x+ over 48 hours) | Early momentum — potential breakout |
| High mentions + high upvotes + bullish sentiment | Strong retail conviction |
| Mentions peaking + price at all-time high | Late to the party — potential top |
| Sudden spike from zero baseline | New discovery — watch closely |
| Gradual steady mentions | Sustained interest, not a pump |

**Signal vs. noise filtering:**
- Require minimum upvote threshold (filters out bot spam)
- Ignore penny stocks and sub-$500M market cap (manipulation risk)
- Track mention **acceleration**, not absolute mentions (acceleration leads price)
- Weight sentiment by engagement (upvoted DD post >> random comment)
- Social leads institutional by 1-3 days on momentum plays, but **lags** on fundamental moves

**Real examples.**
- **GameStop Jan 2021:** WSB mentions went parabolic 5-7 days before the price did.
- **AMC, BB, NOK 2021:** Social momentum drove coordinated retail buying.
- **Nvidia 2023:** r/stocks and r/investing discussions on AI preceded the retail wave.

**Limitations.**
- Extremely noisy. Most social "DD" is garbage.
- Bot manipulation is common, especially on StockTwits.
- By the time something trends on WSB's front page, you're late.
- Works best as a confirmation signal, not a primary signal.
- Retail sentiment is often wrong on fundamentals — use for momentum, not valuation.

---

### Signal 8: 13F Institutional Holdings

**What it is.** Any institutional investment manager with $100M+ in assets must file a 13F with the SEC every quarter, disclosing all long equity positions. This reveals what the biggest players — Berkshire Hathaway, Bridgewater, Renaissance Technologies, Soros Fund Management — are buying and selling.

**Why it matters.** Institutional investors manage trillions and employ armies of analysts. When Buffett opens a new position, there's significant research behind it. Tracking **changes** in institutional holdings (new positions, increased positions, complete exits) gives insight into where the smart money is flowing.

**How to read it.**

| Pattern | Signal |
|---------|--------|
| Buffett/big name opens NEW position | Very Strong — they did deep research |
| Multiple institutions increasing same stock | Strong — institutional consensus forming |
| Hedge fund concentrates (>10% of portfolio) | Strong conviction bet |
| Institution exits entire position | Bearish — they see something wrong |
| Small increase in existing large position | Noise — could be rebalancing |

**Famous whale portfolios to track:**
- **Berkshire Hathaway (Buffett):** Value investing with long-term conviction. New positions are major signals.
- **Renaissance Technologies (Simons):** Quantitative — their 13F shows what the best quants think.
- **Soros Fund Management:** Macro bets, often prescient on sector rotation.
- **Appaloosa (David Tepper):** Distressed/recovery plays.
- **Pershing Square (Bill Ackman):** Concentrated activist bets.

**Real examples.**
- **Buffett's Apple accumulation (2016-2018):** Started buying AAPL in Q1 2016, steadily increased to become largest holding. AAPL up 400%+ since first purchase.
- **Soros buying TSLA 2024:** 13F showed new Tesla position ahead of a rally.
- **Michael Burry's puts (2023):** His 13F showing massive S&P 500 puts made headlines.

**Limitations.**
- **45-day delay** is the biggest problem. The filing for Q4 isn't due until mid-February. Positions may have already changed.
- Only shows long positions. No shorts, no options detail (only total value of options positions).
- Doesn't show position timing within the quarter.
- Large institutions change positions frequently — a Q4 buy might be a Q1 sell.
- Works best for long-term investors, not swing traders.

---

## Signal Convergence

**This is where the real edge lives.** Each signal alone is informative but noisy. When multiple signals converge on the same ticker within the same time window, conviction multiplies.

### The Ideal Bullish Convergence

1. Insider cluster buying (CEO + CFO + directors all buying within 2 weeks)
2. Unusual call options activity (large sweeps, volume >> open interest)
3. Dark pool accumulation (elevated volume, declining short volume ratio)
4. Rising FTDs + high short interest (squeeze mechanics loaded)
5. Multiple hedge funds initiating positions in latest 13Fs
6. Social sentiment beginning to accelerate (early-stage mention velocity)

**When 3+ of these signals align on the same stock, the probability of a significant upward move increases substantially.** No single signal is definitive; convergence is where conviction lives.

### The Ideal Bearish Convergence

1. Insider selling outside of plans (especially CFO liquidation)
2. Put sweeps at the ask in unusual size
3. Dark pool distribution (elevated volume during price strength)
4. Congressional members selling stocks in their committee's jurisdiction
5. 13F showing major funds exiting or reducing positions
6. Social sentiment euphoria (contrarian top signal)

### Why Convergence Works

Each signal has a different **information source** and **time horizon**:

| Signal | Information Source | Typical Lead Time |
|--------|-------------------|-------------------|
| Insider buying | Company knowledge | Weeks to months |
| Dark pool flow | Institutional positioning | Days to weeks |
| Options flow | Event anticipation | Days |
| Congressional trades | Legislative/regulatory | Weeks to months |
| FTD / Short interest | Market mechanics | Days to weeks |
| Social sentiment | Crowd intelligence | Hours to days |
| 13F holdings | Deep fundamental research | Quarters (delayed) |

When signals with **different information sources** independently point the same direction, it's unlikely to be coincidence. An insider buying because they know the pipeline is strong, while a dark pool shows institutional accumulation, while unusual call sweeps appear — these are three independent actors, each with their own information, all reaching the same conclusion.

### The Key Principle

> **Deviation from baseline is the signal, not the absolute level.** Every metric has a normal range for each stock. The signal fires when the metric deviates significantly from *that stock's* historical norm — not from some universal threshold.

### Academic Support for Multi-Signal Approaches

- **Lakonishok & Lee (2001):** Insider cluster buys outperform by 7-13% over 12 months
- **Pan & Poteshman (2006):** Options put-call ratios predict returns ~1% per week
- **Ziobrowski et al. (2004):** Senate portfolios outperformed by ~12% annually
- **Cookson, Engelberg & Mullins (2023):** Social media attention generates short-term momentum, then reverses — tradeable if detected early
- **Rapach, Ringgenberg & Zhou (2016):** Aggregate short interest is one of the strongest known market return predictors
- **Comerton-Forde & Putnins (2015):** Dark pool trades contain more predictive information than lit market trades
- **Goldman Sachs VIP List:** Hedge fund consensus longs (from 13Fs) historically outperform S&P 500

No single study proves the convergence thesis, but the independent alpha from each signal type suggests that combining them should compound the edge — particularly when filtering for confluence.

---

## Data Sources & APIs

All sources are free unless noted. Zero monthly cost for the base system.

### Primary Signal Sources

| Signal | Source | API/Access | Delay | Python |
|--------|--------|-----------|-------|--------|
| **Insider Trading** | SEC EDGAR | `edgartools` library | 0-2 days | `pip install edgartools` |
| **Dark Pool Volume** | FINRA CDN | Direct CSV download | 1 day | `pd.read_csv(url)` |
| **Options Flow** | Tradier (free account) | REST API, real-time chains | Real-time | `requests` |
| **Congressional Trades** | House Stock Watcher | Free JSON API | 1-45 days | `requests` |
| **FTD Data** | SEC.gov | Direct CSV download | ~30 days | `pd.read_csv(url)` |
| **Short Interest** | FINRA short sale vol | Direct download | 1 day (proxy) | `pd.read_csv(url)` |
| **Social Sentiment** | ApeWisdom | Free REST API | Real-time | `requests` |
| **13F Holdings** | SEC EDGAR | `edgartools` library | 45 days | `pip install edgartools` |

### Market Data Sources (existing)

| Data | Source | Access | Python |
|------|--------|--------|--------|
| **OHLCV Prices** | Yahoo Finance | Free | `yfinance` |
| **Fundamentals** | Yahoo Finance | Free | `yfinance` |
| **Stock Info** | Yahoo Finance | Free | `yfinance` |

### Supplementary (optional upgrades)

| Source | Cost | Adds |
|--------|------|------|
| **Unusual Whales** | $40/mo | Bundled options flow + dark pool + congress + short data |
| **Polygon.io** | $29/mo | Real-time dark pool prints, better options data |
| **Finnhub** | Free (60 calls/min) | Congressional trading endpoint, social sentiment |
| **OpenFIGI** | Free | ISIN-to-ticker mapping for Trade Republic stocks |

### Key API Details

**SEC EDGAR (edgartools):**
```python
from edgar import *
set_identity("your@email.com")  # Required by SEC
company = Company("AAPL")
filings = company.get_filings(form="4")  # Insider trades
# Rate limit: 10 req/sec. Must include User-Agent.
```

**FINRA Short Sale Volume (free, no auth):**
```python
import pandas as pd
# Published daily, previous trading day's data
url = "https://cdn.finra.org/equity/regsho/daily/CNMSshvol20260213.txt"
df = pd.read_csv(url, delimiter='|')
# Columns: Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market
```

**Tradier Options (free account):**
```python
headers = {"Authorization": "Bearer TOKEN", "Accept": "application/json"}
r = requests.get("https://api.tradier.com/v1/markets/options/chains",
    params={"symbol": "AAPL", "expiration": "2026-03-20"}, headers=headers)
# Compare volume vs open_interest to detect unusual activity
```

**House Stock Watcher (free, no auth):**
```python
import requests
r = requests.get("https://house-stock-watcher-data.s3-us-west-2.amazonaws.com/data/all_transactions.json")
trades = r.json()
# Filter for recent purchases
```

**ApeWisdom (free, no auth):**
```python
r = requests.get("https://apewisdom.io/api/v1.0/filter/all-stocks/page/1")
data = r.json()  # Top mentioned tickers on WSB with mention counts
```

**SEC FTD Data (free, no auth):**
```python
url = "https://www.sec.gov/files/data/fails-deliver-data/cnsfails202601b.zip"
df = pd.read_csv(url, delimiter='|', dtype=str)
```

---

## Architecture

### Current Pipeline (keep + extend)

```
Data Sources → Indicators → Scoring → Ranking → Reports
```

### New Pipeline

```
                    ┌──────────────────────────────────┐
                    │         DATA LAYER                │
                    ├──────────────────────────────────┤
                    │  Market Data (yfinance)           │
                    │  SEC EDGAR (Form 4, 13F)          │
                    │  FINRA (short vol, dark pool)     │
                    │  Tradier (options chains)          │
                    │  House Stock Watcher (congress)    │
                    │  SEC FTD (fails-to-deliver)        │
                    │  ApeWisdom (social sentiment)      │
                    └──────────────┬───────────────────┘
                                   │
                    ┌──────────────▼───────────────────┐
                    │       ANALYSIS LAYER              │
                    ├──────────────────────────────────┤
                    │  Technical Indicators (existing)   │
                    │  Fundamental Indicators (existing) │
                    │  Volatility Analysis (existing)    │
                    │  Insider Flow Detector (NEW)       │
                    │  Dark Pool Analyzer (NEW)          │
                    │  Options Flow Scanner (NEW)        │
                    │  Congressional Tracker (NEW)       │
                    │  FTD/Short Interest Analyzer (NEW) │
                    │  Social Sentiment Scorer (NEW)     │
                    │  13F Whale Tracker (NEW)           │
                    └──────────────┬───────────────────┘
                                   │
                    ┌──────────────▼───────────────────┐
                    │      CONVICTION ENGINE            │
                    ├──────────────────────────────────┤
                    │  Signal Confluence Detection       │
                    │  Multi-factor Composite Score      │
                    │  Dark Flow Alert Generation        │
                    │  Position Sizing by Conviction     │
                    │  Risk Assessment                   │
                    └──────────────┬───────────────────┘
                                   │
                    ┌──────────────▼───────────────────┐
                    │         OUTPUT LAYER              │
                    ├──────────────────────────────────┤
                    │  Dark Flow Dashboard (HTML)        │
                    │  CSV Data Export                   │
                    │  Console Summary                   │
                    │  Signal Timeline Visualization     │
                    └──────────────────────────────────┘
```

### Directory Structure (target)

```
TRADE_SOURCER/
├── main.py                          # Main orchestrator
├── config/
│   └── config.yaml                  # All configuration
├── src/
│   ├── data_sources/                # Data fetching
│   │   ├── market_data.py           # yfinance (existing)
│   │   ├── trade_republic.py        # Stock universe (rework)
│   │   ├── sec_edgar.py             # SEC EDGAR client (NEW)
│   │   ├── finra.py                 # FINRA data client (NEW)
│   │   ├── tradier.py               # Tradier options client (NEW)
│   │   └── social.py                # Social data client (NEW)
│   ├── indicators/                  # Traditional analysis (existing)
│   │   ├── technical.py
│   │   ├── fundamental.py
│   │   └── volatility.py
│   ├── signals/                     # Dark flow signals (NEW)
│   │   ├── insider_flow.py          # Form 4 insider detection
│   │   ├── dark_pool.py             # FINRA dark pool analysis
│   │   ├── options_flow.py          # Unusual options scanner
│   │   ├── congress_trades.py       # Congressional trading
│   │   ├── ftd_tracker.py           # Fail-to-deliver analysis
│   │   ├── short_interest.py        # Short interest patterns
│   │   ├── social_sentiment.py      # Social momentum
│   │   └── whale_tracker.py         # 13F institutional holdings
│   ├── scoring/
│   │   └── conviction_engine.py     # New multi-signal scorer (replaces vc_scorer)
│   ├── ranking/
│   │   └── ranker.py                # Filtering & ranking (extend)
│   ├── reports/
│   │   └── report_generator.py      # Dark Flow Dashboard (rework)
│   └── utils/
│       ├── config_loader.py
│       └── logger.py
├── data/
│   └── trade_republic_stocks.csv    # Full TR universe with ISINs
├── tests/
├── reports/                         # Generated reports
├── docs/
│   └── planning/
│       └── TODO.md                  # Work plan
└── VISION.md                        # This document
```

---

## The Conviction Engine

The heart of Trade Sourcer v2. Replaces the simple VC scoring with a **multi-signal conviction system**.

### Scoring Weights

| Factor | Weight | Source |
|--------|--------|--------|
| Insider Flow | 20% | SEC Form 4 |
| Dark Pool Signals | 15% | FINRA short volume |
| Options Flow | 15% | Tradier options chains |
| Fundamental Quality | 15% | yfinance financials |
| Technical Setup | 10% | yfinance price data |
| Congressional Trades | 5% | House Stock Watcher |
| Social Momentum | 5% | ApeWisdom |
| FTD / Short Interest | 5% | SEC + FINRA |
| 13F Whale Activity | 5% | SEC 13F |
| Volatility Profile | 5% | Calculated |

### Signal Confluence

The real power is when multiple signals align:

| Confluence Level | Definition | Action |
|-----------------|------------|--------|
| **DARK FLOW ALERT** | 3+ dark signals fire on same ticker | Highest conviction. Feature prominently. |
| **Strong Signal** | 2 dark signals + positive technicals | High conviction. Include in top picks. |
| **Single Signal** | 1 dark signal + fundamentals support | Moderate conviction. Watchlist. |
| **Technical Only** | No dark signals, only TA/fundamentals | Low conviction. Background noise. |

"Dark signals" = insider flow, dark pool, options flow, congressional trades, FTD spikes.

### Position Sizing

| Conviction | Position Size | Max Allocation |
|------------|--------------|----------------|
| Dark Flow Alert | 10-15% | 15% |
| Strong Signal | 5-10% | 10% |
| Single Signal | 3-5% | 5% |
| Watchlist | 0% (monitor) | 0% |

---

## The Weekly Report

### Sunday Morning: Dark Flow Intelligence Report

**Header:**
- Report date and data freshness (which signals have latest data)
- Total stocks scanned
- Dark Flow Alerts found
- Market regime context

**Section 1: Dark Flow Alerts**
Cards for each stock with 3+ converging signals:
- Ticker, company name, current price
- Which signals fired and when (timeline)
- Signal strength for each
- Composite conviction score
- Position sizing recommendation
- Key risk factors

**Section 2: Insider Cluster Buys**
Recent insider buying clusters:
- Who bought (name, role, amount)
- Cluster size (how many insiders)
- Days since first buy
- Price at time of purchase vs. current

**Section 3: Unusual Options Flow**
Top unusual options activity:
- Contract details (strike, expiry, type)
- Volume vs. open interest ratio
- Premium spent
- Sweep or block
- Bullish or bearish interpretation

**Section 4: Congressional Trades**
Recent politician purchases:
- Politician name and committee
- Stock, amount, disclosure date
- Politician track record (win rate)
- Relevant legislation or regulation

**Section 5: Short Squeeze Watch**
Stocks with squeeze potential:
- Short interest % of float
- Days to cover
- FTD trend
- Recent short covering activity

**Section 6: Traditional Analysis**
Standard VC scoring for context:
- Top stocks by fundamental quality
- Technical setups
- Sector allocation

**Section 7: Signal Timeline**
Visual timeline of all signals that fired this week, by ticker.

---

## Trade Republic Universe

### Current Problem
The existing code has 33 hardcoded US mega-caps. Trade Republic has ~7,500+ stocks across US, EU, and German markets.

### Solution
- Parse the **official Trade Republic Instrument Universe PDF** (published at `assets.traderepublic.com`)
- Store with ISINs as primary key, tickers for API compatibility
- Use OpenFIGI for ISIN → ticker mapping
- Focus analysis on liquid, tradable stocks (filter by market cap and volume)
- **Execution venue:** LS Exchange (Lang & Schwarz), but data comes from home exchanges via yfinance

### Universe Scope for v2
Start with a focused universe of **200-500 liquid stocks**:
- All DAX 40 components
- Euro Stoxx 50
- Top 100 US stocks by market cap available on TR
- Any stock that triggers a dark signal (dynamic inclusion)

Expand to full ~7,500 over time as signal processing scales.

---

## Current State Assessment

### What exists and works (keep)
- Pipeline architecture: Data → Analysis → Scoring → Ranking → Reports
- Technical indicators: RSI, MACD, Bollinger, Volume, ATR, Stochastic
- Fundamental indicators: Growth, margins, valuation, quality metrics
- Volatility analysis with next-week predictions
- HTML report generation (needs redesign but template engine works)
- Config system (YAML + env vars)
- Logging infrastructure

### What needs rework
- Trade Republic universe (hardcoded 33 stocks → real universe with ISINs)
- Scoring system (generic VC → conviction engine with signal confluence)
- Report template (generic screener → dark flow dashboard)
- Dependencies (pandas-ta broken, needs cleanup)

### What doesn't exist yet (new build)
- All 8 signal detectors (insider, dark pool, options, congress, FTD, short, social, 13F)
- Data clients for SEC EDGAR, FINRA, Tradier, House Stock Watcher, ApeWisdom
- Conviction engine with signal confluence
- Dark flow report design
- Sunday automation with notification
- ISIN-to-ticker mapping layer

### Honest assessment
~25% of the target system exists. The foundation is solid but the differentiating feature — the dark flow signal layer — is 0% built.

---

## Work Plan

See [docs/planning/TODO.md](docs/planning/TODO.md) for the detailed task breakdown.

**9 packages, 54 tasks, dependency-ordered:**

```
Package 0: Fix Foundation          ← first
Packages 1-6: Signal Detectors    ← parallel, independent
Package 7: Conviction Engine       ← needs signals
Package 8: Report + Automation     ← needs engine
```

**Critical path:** Foundation → Insider Flow → Dark Pool → Conviction Engine → Report

---

## Constraints & Non-Goals

### Constraints
- **Trade Republic only:** All stocks must be available on Trade Republic
- **Weekly cadence:** Designed for Sunday analysis → Monday-Friday trading
- **Free data:** $0/month base system using only free APIs
- **Python:** Keep the existing Python stack
- **CLI-first:** No web dashboard, no mobile app (out of scope)
- **Local execution:** Runs on Marc's machine, not cloud-deployed

### Non-Goals (do not build)
- Backtesting engine
- Portfolio tracking / P&L
- Trade execution integration
- Real-time alerts during trading week
- Machine learning / AI predictions
- Multi-user support
- Web dashboard
- Mobile app
- Email notifications (v1 — just read the HTML report)

### Disclaimers
- This is a screening and intelligence tool, not financial advice
- Dark flow signals are probabilistic, not deterministic
- Past signal performance does not guarantee future results
- Always do your own research before trading
- Never invest more than you can afford to lose
