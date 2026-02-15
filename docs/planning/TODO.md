# Work Plan

> Seed: [VISION.md](../../VISION.md) — the single source of truth
> Generated: 2026-02-15
> Delete when complete

---

## Honest State Assessment

**What the docs claim:** "Production ready, 5/5 everything, ship NOW!"
**What's actually true:**
- The **pipeline architecture is solid** (data → indicators → scoring → ranking → reports)
- Technical + fundamental analysis **works** against real yfinance data
- HTML reports **generate** and look decent
- BUT: it's a **generic stock screener**. Zero "dark flow" or hidden signal capability.
- Dependencies broken (`pandas-ta` fails to install on Python 3.9)
- Trade Republic stock list is **33 hardcoded US mega-caps** (not real TR universe)
- Tests pass but are shallow (happy path only)
- Copilot generated all the "5/5 excellent" documentation — it's marketing, not assessment

**The gap between "generic screener" and "see what nobody else sees" is ~80% of the work.**

---

## Gap Summary

| Metric | Count |
|--------|-------|
| Total requirements (vision) | 24 |
| Done (reusable as-is) | 6 |
| Partial (needs rework) | 4 |
| Missing (new build) | 14 |
| Packages | 9 |

## Progress
[██░░░░░░░░] 25% — 0/9 packages complete (foundation exists but no dark signals)

---

## Package 0: Fix Foundation
**Delivers:** App actually runs, deps work, real Trade Republic stock list
- [ ] [S] Fix dependency issue — replace `pandas-ta` or pin working version
- [ ] [S] Verify all 15 tests pass on clean install
- [ ] [M] Replace hardcoded 33 US stocks with **real Trade Republic universe** (EU/DE stocks, ISINs → tickers)
- [ ] [S] Add `pyproject.toml` or fix `requirements.txt` for reproducible installs
- [ ] [S] Clean up Copilot-generated marketing docs (keep only useful ones)
**Verify:** `pip install -r requirements.txt && python -m pytest tests/ && python main.py` all succeed

---

## Package 1: SEC Insider Trading Detection (Form 4)
**Delivers:** Real-time insider buy/sell signals — the single highest-alpha free signal
- [ ] [M] Build `src/signals/insider_flow.py` — fetch Form 4 filings via `edgartools`
- [ ] [M] Parse insider transactions: who bought/sold, how much, what % of holdings
- [ ] [S] Detect **cluster buys** (multiple insiders buying within 2 weeks = strong signal)
- [ ] [M] Score insider activity: weight by insider role (CEO > VP), size, cluster
- [ ] [S] Add to scoring pipeline — insider_signal feeds into composite score
- [ ] [S] Tests for insider signal parsing
**Verify:** Run against 5 known recent insider buys, confirm detection

---

## Package 2: Dark Pool & Short Sale Volume (FINRA)
**Delivers:** Off-exchange volume analysis — see where smart money is moving
- [ ] [M] Build `src/signals/dark_pool.py` — fetch FINRA short sale volume daily files
- [ ] [M] Calculate dark pool ratio (short vol / total vol) per ticker per day
- [ ] [M] Detect anomalies: sudden spikes in dark pool activity vs. 20-day average
- [ ] [S] Track dark pool ratio trends (accumulation vs. distribution patterns)
- [ ] [S] Score dark pool signals and feed into composite
- [ ] [S] Tests for FINRA data parsing and anomaly detection
**Verify:** Run against recent FINRA data, confirm anomaly detection on known events

---

## Package 3: Unusual Options Flow Scanner
**Delivers:** Detect large unusual options bets that signal informed money
- [ ] [M] Build `src/signals/options_flow.py` — use Tradier free API for options chains
- [ ] [M] Detect unusual activity: volume > 3x open interest, large single trades
- [ ] [S] Classify: bullish (call sweeps, put sells) vs. bearish (put sweeps, call sells)
- [ ] [M] Score conviction: premium spent, days to expiry, OTM distance
- [ ] [S] Feed into composite scoring
- [ ] [S] Tests with mock options data
**Verify:** Scanner correctly flags known unusual activity patterns

---

## Package 4: Congressional & Political Trading
**Delivers:** Follow the politicians — legally required disclosures, historically alpha-generating
- [ ] [M] Build `src/signals/congress_trades.py` — pull from House Stock Watcher API + Senate
- [ ] [S] Filter for purchases only, recent (< 30 days)
- [ ] [S] Track which politicians have best track records
- [ ] [S] Score by: size of trade, politician track record, recency
- [ ] [S] Feed into composite
- [ ] [S] Tests
**Verify:** Pull recent congressional trades, verify against capitoltrades.com

---

## Package 5: Fail-to-Deliver & Short Interest Patterns
**Delivers:** Detect FTD spikes that precede price movements
- [ ] [M] Build `src/signals/ftd_tracker.py` — parse SEC FTD data files
- [ ] [M] Detect FTD threshold securities, sudden FTD spikes
- [ ] [S] Correlate FTD patterns with price action (leading indicator)
- [ ] [S] Add FINRA short interest ratio as supplementary signal
- [ ] [S] Score and feed into composite
- [ ] [S] Tests
**Verify:** Backtest FTD spikes vs. subsequent price action on 5 known cases

---

## Package 6: Social Sentiment & Momentum
**Delivers:** Reddit/social buzz detection before mainstream picks up
- [ ] [M] Build `src/signals/social_sentiment.py` — ApeWisdom API for WSB mentions
- [ ] [S] Track mention velocity (acceleration in mentions = early signal)
- [ ] [S] Sentiment scoring via keyword heuristics (bullish/bearish language)
- [ ] [S] Filter noise: require minimum upvote threshold, ignore penny stocks
- [ ] [S] Feed into composite (low weight — noisy signal)
- [ ] [S] Tests
**Verify:** Pull current WSB top mentions, compare to known momentum plays

---

## Package 7: Conviction Engine (Signal Aggregator)
**Delivers:** Combined multi-signal scoring that weighs all dark flow signals
- [ ] [L] Redesign `src/scoring/vc_scorer.py` → `src/scoring/conviction_engine.py`
- [ ] [M] New composite: Technical (15%) + Fundamental (20%) + Insider Flow (20%) + Dark Pool (15%) + Options Flow (15%) + Congress (5%) + Social (5%) + FTD (5%)
- [ ] [M] Implement signal confluence detection (multiple signals firing = high conviction)
- [ ] [S] Grade system: "Dark Flow Alert" (3+ dark signals aligned) vs. regular picks
- [ ] [M] Position sizing based on signal conviction (more signals = larger size)
- [ ] [S] Tests for composite scoring
**Verify:** Run full pipeline, verify scoring reflects signal quality

---

## Package 8: Dark Flow Report & Sunday Automation
**Delivers:** Beautiful weekly report + automated Sunday morning runs
- [ ] [L] Redesign `src/reports/report_generator.py` — new "Dark Flow Dashboard" HTML
- [ ] [M] Report sections: Dark Flow Alerts, Insider Clusters, Unusual Options, Congress Buys, Top Ranked
- [ ] [M] Each stock card shows: which signals fired, signal strength, confidence
- [ ] [S] Add signal timeline visualization (when did each signal fire this week?)
- [ ] [M] Sunday cron automation with email/notification on completion
- [ ] [S] Error handling: partial data (some APIs down) → still generates report with available data
- [ ] [S] Tests for report generation
**Verify:** Full Sunday run produces complete Dark Flow report

---

## Dependency Order

```
Package 0 (Foundation) ← MUST be first
    ↓
Packages 1-6 (Signals) ← can be built in parallel, each independent
    ↓
Package 7 (Conviction Engine) ← needs all signals
    ↓
Package 8 (Report + Automation) ← needs engine
```

## Critical Path
`Package 0 → Package 1 (highest alpha) → Package 2 → Package 7 → Package 8`

Packages 3-6 can be interleaved but aren't blocking.

---

## Data Source Summary

| Signal | Source | Cost | Delay | Alpha |
|--------|--------|------|-------|-------|
| Insider Trading | SEC EDGAR (edgartools) | Free | 0-2 days | HIGH |
| Dark Pool Volume | FINRA CDN | Free | 1 day | HIGH |
| Options Flow | Tradier API | Free | Real-time | HIGH |
| Congress Trades | House Stock Watcher | Free | 1-45 days | MEDIUM |
| FTD Data | SEC.gov | Free | ~30 days | MEDIUM |
| Social Sentiment | ApeWisdom | Free | Real-time | LOW (noisy) |
| Market Data | yfinance | Free | Real-time | BASE |
| Fundamentals | yfinance | Free | Quarterly | BASE |

**Total monthly cost: $0** (all free tier)
Optional upgrade: Unusual Whales ($40/mo) bundles dark pool + options + congress

---

## Sizing

| Package | Tasks | Estimated Size |
|---------|-------|---------------|
| 0: Foundation | 5 | S session |
| 1: Insider Flow | 6 | M session |
| 2: Dark Pool | 6 | M session |
| 3: Options Flow | 6 | M session |
| 4: Congress | 6 | S-M session |
| 5: FTD/Short | 6 | M session |
| 6: Social | 6 | S session |
| 7: Conviction Engine | 6 | L session |
| 8: Report + Auto | 7 | L session |
| **Total** | **54** | **9 sessions** |
