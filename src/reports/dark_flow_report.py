"""
Dark Flow Intelligence Report Generator

Generates the weekly Dark Flow Report — a professional financial dashboard
showing converging dark signals (insider flow, dark pool, options, congress,
FTD/short interest, social sentiment) for stock analysis.
"""
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from jinja2 import Template
from ..utils.logger import get_logger

logger = get_logger()


# ---------------------------------------------------------------------------
# Jinja2 HTML template — self-contained, dark theme, inline CSS
# ---------------------------------------------------------------------------

_DARK_FLOW_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dark Flow Intelligence Report - {{ date_display }}</title>
    <style>
        /* ----- Reset & base ----- */
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        .skip-link {
            position: absolute; top: -50px; left: 0; padding: 8px 16px;
            background: #e94560; color: #fff; z-index: 1000; font-weight: bold;
            text-decoration: none; border-radius: 0 0 4px 0;
        }
        .skip-link:focus { top: 0; }
        *:focus { outline: 2px solid #e94560; outline-offset: 2px; }

        body {
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            background: #0f0f23; color: #eee; line-height: 1.6;
            max-width: 1280px; margin: 0 auto; padding: 16px;
        }
        a { color: #53a8ff; }

        /* ----- Typography ----- */
        h1 { font-size: 1.8rem; font-weight: 700; }
        h2 { font-size: 1.35rem; font-weight: 600; margin-bottom: 12px; border-bottom: 2px solid #0f3460; padding-bottom: 6px; }
        h3 { font-size: 1.1rem; font-weight: 600; }

        /* ----- Header ----- */
        .report-header {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            padding: 28px 24px; border-radius: 8px; margin-bottom: 24px;
            border-left: 4px solid #e94560;
        }
        .report-header h1 { color: #e94560; margin-bottom: 4px; }
        .report-header .subtitle { color: #8899aa; font-size: 0.95rem; }
        .header-stats {
            display: flex; flex-wrap: wrap; gap: 24px; margin-top: 16px;
        }
        .header-stat { text-align: center; }
        .header-stat .value { font-size: 1.8rem; font-weight: 700; color: #fff; }
        .header-stat .label { font-size: 0.75rem; color: #8899aa; text-transform: uppercase; letter-spacing: 0.05em; }

        .freshness { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
        .freshness-tag {
            font-size: 0.7rem; padding: 2px 8px; border-radius: 10px;
            background: #1a1a2e; border: 1px solid #0f3460; color: #8899aa;
        }
        .freshness-tag.fresh { border-color: #00d25b; color: #00d25b; }

        /* ----- Section ----- */
        .section { margin-bottom: 32px; }
        .section-title { color: #e94560; }

        /* ----- Cards ----- */
        .card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 16px; }
        .card {
            background: #16213e; border-radius: 8px; padding: 20px;
            border: 1px solid #0f3460; transition: border-color 0.15s;
        }
        .card:hover { border-color: #e94560; }
        .card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
        .card-ticker { font-size: 1.3rem; font-weight: 700; color: #fff; }
        .card-company { font-size: 0.85rem; color: #8899aa; }
        .card-price { font-size: 0.95rem; color: #ccc; }

        /* Conviction badge */
        .conviction-badge {
            display: inline-block; padding: 4px 12px; border-radius: 4px;
            font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em;
        }
        .conviction-critical { background: #e94560; color: #fff; }
        .conviction-high { background: #ff6b35; color: #fff; }
        .conviction-medium { background: #f0a500; color: #1a1a2e; }
        .conviction-low { background: #3a3a5c; color: #aaa; }

        /* Signal dots */
        .signal-dots { display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0; }
        .signal-dot {
            font-size: 0.7rem; padding: 2px 8px; border-radius: 10px;
            border: 1px solid; font-weight: 600;
        }
        .signal-dot.active-insider { background: rgba(0,210,91,0.15); border-color: #00d25b; color: #00d25b; }
        .signal-dot.active-darkpool { background: rgba(83,168,255,0.15); border-color: #53a8ff; color: #53a8ff; }
        .signal-dot.active-options { background: rgba(233,69,96,0.15); border-color: #e94560; color: #e94560; }
        .signal-dot.active-congress { background: rgba(240,165,0,0.15); border-color: #f0a500; color: #f0a500; }
        .signal-dot.active-ftd { background: rgba(178,102,255,0.15); border-color: #b266ff; color: #b266ff; }
        .signal-dot.active-social { background: rgba(0,188,212,0.15); border-color: #00bcd4; color: #00bcd4; }
        .signal-dot.inactive { background: transparent; border-color: #2a2a4a; color: #3a3a5c; }

        /* Strength bars */
        .strength-row { display: flex; align-items: center; margin: 3px 0; }
        .strength-label { width: 80px; font-size: 0.7rem; color: #8899aa; }
        .strength-bar-bg { flex: 1; height: 6px; background: #1a1a2e; border-radius: 3px; overflow: hidden; }
        .strength-bar { height: 100%; border-radius: 3px; min-width: 2px; }
        .strength-bar.insider { background: #00d25b; }
        .strength-bar.darkpool { background: #53a8ff; }
        .strength-bar.options { background: #e94560; }
        .strength-bar.congress { background: #f0a500; }
        .strength-bar.ftd { background: #b266ff; }
        .strength-bar.social { background: #00bcd4; }
        .strength-val { width: 36px; text-align: right; font-size: 0.7rem; color: #8899aa; }

        /* Position sizing */
        .position-rec {
            margin-top: 10px; padding: 8px 12px; border-radius: 4px;
            background: rgba(0,210,91,0.08); border-left: 3px solid #00d25b;
            font-size: 0.85rem;
        }

        /* Risk warnings */
        .risk-warning {
            margin-top: 6px; font-size: 0.75rem; color: #ff4444;
            padding: 4px 0;
        }

        /* ----- Tables ----- */
        .table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }
        table {
            width: 100%; border-collapse: collapse; background: #16213e;
            border-radius: 8px; overflow: hidden; font-size: 0.85rem;
        }
        thead th {
            background: #0f3460; color: #ccc; padding: 10px 12px;
            text-align: left; font-weight: 600; font-size: 0.75rem;
            text-transform: uppercase; letter-spacing: 0.04em; white-space: nowrap;
        }
        tbody td { padding: 10px 12px; border-bottom: 1px solid #1a1a2e; color: #ddd; }
        tbody tr:last-child td { border-bottom: none; }
        tbody tr:hover { background: rgba(233,69,96,0.05); }

        .bullish { color: #00d25b; }
        .bearish { color: #ff4444; }
        .neutral { color: #8899aa; }
        .mono { font-family: 'SF Mono', 'Cascadia Code', Consolas, monospace; font-size: 0.8rem; }

        /* ----- Empty state ----- */
        .empty-state {
            text-align: center; padding: 32px; color: #555; font-style: italic;
            background: #16213e; border-radius: 8px;
        }

        /* ----- Timeline matrix ----- */
        .timeline-dot { display: inline-block; width: 14px; height: 14px; border-radius: 3px; }
        .timeline-dot.on { background: #e94560; }
        .timeline-dot.off { background: #1a1a2e; }

        /* ----- Footer ----- */
        .footer {
            margin-top: 40px; padding: 16px 0; border-top: 1px solid #0f3460;
            text-align: center; font-size: 0.8rem; color: #555;
        }

        /* ----- Responsive ----- */
        @media (max-width: 640px) {
            body { padding: 8px; }
            .card-grid { grid-template-columns: 1fr; }
            h1 { font-size: 1.4rem; }
            .header-stats { gap: 12px; }
        }
    </style>
</head>
<body>
    <a href="#main-content" class="skip-link">Skip to main content</a>

    <!-- ============ HEADER ============ -->
    <header class="report-header" role="banner">
        <h1>Dark Flow Intelligence Report</h1>
        <p class="subtitle">{{ date_display }} &mdash; Converging Signal Analysis</p>
        <div class="header-stats" aria-label="Report summary statistics">
            <div class="header-stat">
                <div class="value">{{ total_scanned }}</div>
                <div class="label">Stocks Scanned</div>
            </div>
            <div class="header-stat">
                <div class="value" style="color: #e94560;">{{ dark_flow_count }}</div>
                <div class="label">Dark Flow Alerts</div>
            </div>
            <div class="header-stat">
                <div class="value">{{ market_context }}</div>
                <div class="label">Market Context</div>
            </div>
        </div>
        {% if freshness %}
        <div class="freshness" aria-label="Data freshness indicators">
            {% for source, age in freshness.items() %}
            <span class="freshness-tag{% if 'h ago' in age or 'min' in age %} fresh{% endif %}">{{ source }}: {{ age }}</span>
            {% endfor %}
        </div>
        {% endif %}
    </header>

    <main id="main-content" role="main">

    <!-- ============ SECTION 1: DARK FLOW ALERTS ============ -->
    <section class="section" aria-label="Dark Flow Alerts">
        <h2 class="section-title">1. Dark Flow Alerts</h2>
        {% if dark_flow_alerts %}
        <div class="card-grid">
            {% for s in dark_flow_alerts %}
            <article class="card" aria-label="Dark Flow Alert for {{ s.ticker }}">
                <div class="card-header">
                    <div>
                        <span class="card-ticker">{{ s.ticker }}</span>
                        <div class="card-company">{{ s.company_name }}</div>
                        <div class="card-price">${{ "%.2f"|format(s.current_price) }}</div>
                    </div>
                    <div>
                        <span class="conviction-badge conviction-{{ s.conviction_level|lower }}">{{ s.conviction_level }}</span>
                        <div style="text-align:right; margin-top:4px; font-size:0.8rem; color:#8899aa;">Score: {{ s.conviction_score }}</div>
                    </div>
                </div>

                <!-- Signal dots -->
                <div class="signal-dots" aria-label="Active signals for {{ s.ticker }}">
                    <span class="signal-dot {{ 'active-insider' if s.insider_signal_score > 0 else 'inactive' }}" title="Insider Flow">INS</span>
                    <span class="signal-dot {{ 'active-darkpool' if s.darkpool_signal_score > 0 else 'inactive' }}" title="Dark Pool">DP</span>
                    <span class="signal-dot {{ 'active-options' if s.options_signal_score > 0 else 'inactive' }}" title="Options Flow">OPT</span>
                    <span class="signal-dot {{ 'active-congress' if s.congress_signal_score > 0 else 'inactive' }}" title="Congressional">CON</span>
                    <span class="signal-dot {{ 'active-ftd' if s.ftd_signal_score > 0 else 'inactive' }}" title="FTD / Short">FTD</span>
                    <span class="signal-dot {{ 'active-social' if s.social_signal_score > 0 else 'inactive' }}" title="Social Sentiment">SOC</span>
                </div>

                <!-- Strength bars -->
                <div style="margin-top:8px;" aria-label="Signal strength breakdown">
                    {% set bars = [
                        ('Insider', s.insider_signal_score, 'insider'),
                        ('Dark Pool', s.darkpool_signal_score, 'darkpool'),
                        ('Options', s.options_signal_score, 'options'),
                        ('Congress', s.congress_signal_score, 'congress'),
                        ('FTD/Short', s.ftd_signal_score, 'ftd'),
                        ('Social', s.social_signal_score, 'social'),
                    ] %}
                    {% for label, val, cls in bars %}
                    <div class="strength-row">
                        <span class="strength-label">{{ label }}</span>
                        <div class="strength-bar-bg" role="progressbar" aria-valuenow="{{ val }}" aria-valuemin="0" aria-valuemax="100" aria-label="{{ label }} signal strength">
                            <div class="strength-bar {{ cls }}" style="width: {{ val }}%;"></div>
                        </div>
                        <span class="strength-val">{{ val }}</span>
                    </div>
                    {% endfor %}
                </div>

                <!-- Position sizing -->
                <div class="position-rec">
                    Suggested position: <strong>{{ "%.1f"|format(s.position_size_pct) }}%</strong> of portfolio
                </div>

                {% if s.risk_warnings %}
                <div class="risk-warning" aria-label="Risk warnings">
                    {% for rw in s.risk_warnings %}
                    <div>&#9888; {{ rw }}</div>
                    {% endfor %}
                </div>
                {% endif %}
            </article>
            {% endfor %}
        </div>
        {% else %}
        <div class="empty-state" role="status">No Dark Flow Alerts this week. No stocks had 3+ converging dark signals.</div>
        {% endif %}
    </section>

    <!-- ============ SECTION 2: INSIDER CLUSTER BUYS ============ -->
    <section class="section" aria-label="Insider Cluster Buys">
        <h2 class="section-title">2. Insider Cluster Buys</h2>
        {% if insider_clusters %}
        <div class="table-wrap">
        <table>
            <caption class="sr-only">Recent insider buying clusters</caption>
            <thead>
                <tr>
                    <th scope="col">Ticker</th>
                    <th scope="col">Buyer</th>
                    <th scope="col">Role</th>
                    <th scope="col">Amount</th>
                    <th scope="col">Cluster Size</th>
                    <th scope="col">Days Since 1st</th>
                    <th scope="col">Buy Price</th>
                    <th scope="col">Current</th>
                    <th scope="col">Change</th>
                </tr>
            </thead>
            <tbody>
                {% for ic in insider_clusters %}
                <tr>
                    <td><strong>{{ ic.ticker }}</strong></td>
                    <td>{{ ic.buyer_name }}</td>
                    <td>{{ ic.buyer_role }}</td>
                    <td class="mono">{{ ic.amount_display }}</td>
                    <td>{{ ic.cluster_size }}</td>
                    <td>{{ ic.days_since_first }}</td>
                    <td class="mono">${{ "%.2f"|format(ic.buy_price) }}</td>
                    <td class="mono">${{ "%.2f"|format(ic.current_price) }}</td>
                    <td class="{{ 'bullish' if ic.price_change_pct >= 0 else 'bearish' }}">
                        {{ "%.1f"|format(ic.price_change_pct) }}%
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        </div>
        {% else %}
        <div class="empty-state" role="status">No insider cluster buys detected this period.</div>
        {% endif %}
    </section>

    <!-- ============ SECTION 3: UNUSUAL OPTIONS FLOW ============ -->
    <section class="section" aria-label="Unusual Options Flow">
        <h2 class="section-title">3. Unusual Options Flow</h2>
        {% if options_flow %}
        <div class="table-wrap">
        <table>
            <caption class="sr-only">Top unusual options activity</caption>
            <thead>
                <tr>
                    <th scope="col">Ticker</th>
                    <th scope="col">Contract</th>
                    <th scope="col">Vol / OI</th>
                    <th scope="col">Premium</th>
                    <th scope="col">Type</th>
                    <th scope="col">Direction</th>
                </tr>
            </thead>
            <tbody>
                {% for opt in options_flow %}
                <tr>
                    <td><strong>{{ opt.ticker }}</strong></td>
                    <td class="mono">{{ opt.contract }}</td>
                    <td class="mono">{{ opt.vol_oi_ratio }}</td>
                    <td class="mono">{{ opt.premium_display }}</td>
                    <td>{{ opt.trade_type }}</td>
                    <td class="{{ 'bullish' if opt.direction == 'Bullish' else ('bearish' if opt.direction == 'Bearish' else 'neutral') }}">
                        {{ opt.direction }}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        </div>
        {% else %}
        <div class="empty-state" role="status">No unusual options flow detected.</div>
        {% endif %}
    </section>

    <!-- ============ SECTION 4: CONGRESSIONAL TRADES ============ -->
    <section class="section" aria-label="Congressional Trades">
        <h2 class="section-title">4. Congressional Trades</h2>
        {% if congress_trades %}
        <div class="table-wrap">
        <table>
            <caption class="sr-only">Recent congressional stock trades</caption>
            <thead>
                <tr>
                    <th scope="col">Politician</th>
                    <th scope="col">Ticker</th>
                    <th scope="col">Type</th>
                    <th scope="col">Amount Range</th>
                    <th scope="col">Disclosure Date</th>
                    <th scope="col">Recency</th>
                </tr>
            </thead>
            <tbody>
                {% for ct in congress_trades %}
                <tr>
                    <td>{{ ct.politician }}</td>
                    <td><strong>{{ ct.ticker }}</strong></td>
                    <td class="{{ 'bullish' if ct.trade_type == 'Purchase' else 'bearish' }}">{{ ct.trade_type }}</td>
                    <td class="mono">{{ ct.amount_range }}</td>
                    <td>{{ ct.disclosure_date }}</td>
                    <td>{{ ct.recency }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        </div>
        {% else %}
        <div class="empty-state" role="status">No notable congressional trades this period.</div>
        {% endif %}
    </section>

    <!-- ============ SECTION 5: SHORT SQUEEZE WATCH ============ -->
    <section class="section" aria-label="Short Squeeze Watch">
        <h2 class="section-title">5. Short Squeeze Watch</h2>
        {% if squeeze_watch %}
        <div class="table-wrap">
        <table>
            <caption class="sr-only">Stocks with short squeeze potential</caption>
            <thead>
                <tr>
                    <th scope="col">Ticker</th>
                    <th scope="col">Short Interest %</th>
                    <th scope="col">Days to Cover</th>
                    <th scope="col">FTD Trend</th>
                    <th scope="col">Squeeze Potential</th>
                </tr>
            </thead>
            <tbody>
                {% for sq in squeeze_watch %}
                <tr>
                    <td><strong>{{ sq.ticker }}</strong></td>
                    <td class="mono">{{ "%.1f"|format(sq.short_interest_pct) }}%</td>
                    <td class="mono">{{ "%.1f"|format(sq.days_to_cover) }}</td>
                    <td class="{{ 'bearish' if sq.ftd_trend == 'Rising' else ('bullish' if sq.ftd_trend == 'Falling' else 'neutral') }}">
                        {{ sq.ftd_trend }}
                    </td>
                    <td>
                        <span class="conviction-badge conviction-{{ sq.squeeze_flag|lower }}">{{ sq.squeeze_flag }}</span>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        </div>
        {% else %}
        <div class="empty-state" role="status">No stocks on the Short Squeeze Watch list.</div>
        {% endif %}
    </section>

    <!-- ============ SECTION 6: TRADITIONAL ANALYSIS ============ -->
    <section class="section" aria-label="Traditional Analysis">
        <h2 class="section-title">6. Traditional Analysis</h2>
        {% if traditional_top %}
        <div class="table-wrap">
        <table>
            <caption class="sr-only">Top stocks by traditional VC scoring</caption>
            <thead>
                <tr>
                    <th scope="col">Rank</th>
                    <th scope="col">Ticker</th>
                    <th scope="col">Company</th>
                    <th scope="col">Technical</th>
                    <th scope="col">Fundamental</th>
                    <th scope="col">Conviction</th>
                    <th scope="col">Price</th>
                </tr>
            </thead>
            <tbody>
                {% for ts in traditional_top %}
                <tr>
                    <td>{{ loop.index }}</td>
                    <td><strong>{{ ts.ticker }}</strong></td>
                    <td>{{ ts.company_name }}</td>
                    <td class="mono">{{ ts.technical_score }}</td>
                    <td class="mono">{{ ts.fundamental_score }}</td>
                    <td>
                        <span class="conviction-badge conviction-{{ ts.conviction_level|lower }}">{{ ts.conviction_level }}</span>
                    </td>
                    <td class="mono">${{ "%.2f"|format(ts.current_price) }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        </div>

        {% if sector_allocation %}
        <h3 style="margin-top:20px; color:#8899aa;">Sector Allocation</h3>
        <div class="table-wrap" style="margin-top:8px;">
        <table>
            <caption class="sr-only">Sector allocation breakdown</caption>
            <thead>
                <tr>
                    <th scope="col">Sector</th>
                    <th scope="col">Count</th>
                    <th scope="col">Percentage</th>
                </tr>
            </thead>
            <tbody>
                {% for sec_name, sec_data in sector_allocation.items() %}
                <tr>
                    <td>{{ sec_name }}</td>
                    <td>{{ sec_data.count }}</td>
                    <td class="mono">{{ "%.1f"|format(sec_data.percentage) }}%</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        </div>
        {% endif %}
        {% else %}
        <div class="empty-state" role="status">No traditional analysis data available.</div>
        {% endif %}
    </section>

    <!-- ============ SECTION 7: SIGNAL TIMELINE ============ -->
    <section class="section" aria-label="Signal Timeline">
        <h2 class="section-title">7. Signal Timeline</h2>
        {% if timeline_rows %}
        <div class="table-wrap">
        <table>
            <caption class="sr-only">Which signals fired on which tickers</caption>
            <thead>
                <tr>
                    <th scope="col">Ticker</th>
                    <th scope="col">Insider</th>
                    <th scope="col">Dark Pool</th>
                    <th scope="col">Options</th>
                    <th scope="col">Congress</th>
                    <th scope="col">FTD/Short</th>
                    <th scope="col">Social</th>
                    <th scope="col">Signals</th>
                </tr>
            </thead>
            <tbody>
                {% for tr in timeline_rows %}
                <tr>
                    <td><strong>{{ tr.ticker }}</strong></td>
                    <td style="text-align:center;"><span class="timeline-dot {{ 'on' if tr.insider else 'off' }}" aria-label="{{ 'active' if tr.insider else 'inactive' }}" title="{{ 'Active' if tr.insider else 'Inactive' }}"></span></td>
                    <td style="text-align:center;"><span class="timeline-dot {{ 'on' if tr.darkpool else 'off' }}" aria-label="{{ 'active' if tr.darkpool else 'inactive' }}" title="{{ 'Active' if tr.darkpool else 'Inactive' }}"></span></td>
                    <td style="text-align:center;"><span class="timeline-dot {{ 'on' if tr.options else 'off' }}" aria-label="{{ 'active' if tr.options else 'inactive' }}" title="{{ 'Active' if tr.options else 'Inactive' }}"></span></td>
                    <td style="text-align:center;"><span class="timeline-dot {{ 'on' if tr.congress else 'off' }}" aria-label="{{ 'active' if tr.congress else 'inactive' }}" title="{{ 'Active' if tr.congress else 'Inactive' }}"></span></td>
                    <td style="text-align:center;"><span class="timeline-dot {{ 'on' if tr.ftd else 'off' }}" aria-label="{{ 'active' if tr.ftd else 'inactive' }}" title="{{ 'Active' if tr.ftd else 'Inactive' }}"></span></td>
                    <td style="text-align:center;"><span class="timeline-dot {{ 'on' if tr.social else 'off' }}" aria-label="{{ 'active' if tr.social else 'inactive' }}" title="{{ 'Active' if tr.social else 'Inactive' }}"></span></td>
                    <td class="mono" style="text-align:center;">{{ tr.count }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        </div>
        {% else %}
        <div class="empty-state" role="status">No signal data for timeline.</div>
        {% endif %}
    </section>

    </main>

    <footer class="footer" role="contentinfo">
        <p>Generated by Trade Sourcer &mdash; Dark Flow Intelligence Engine</p>
        <p style="margin-top:4px;">This report is for informational purposes only. Not financial advice.</p>
    </footer>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _safe_get(d: dict, key: str, default=0):
    """Get a value from dict/object with a default, handling None values."""
    val = d.get(key, default) if isinstance(d, dict) else getattr(d, key, default)
    return val if val is not None else default


def _format_dollar(amount) -> str:
    """Format a dollar amount for display (e.g. $1.2M, $450K)."""
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return "N/A"
    if abs(amount) >= 1_000_000_000:
        return f"${amount / 1_000_000_000:.1f}B"
    if abs(amount) >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    if abs(amount) >= 1_000:
        return f"${amount / 1_000:.0f}K"
    return f"${amount:,.0f}"


# ---------------------------------------------------------------------------
# Generator class
# ---------------------------------------------------------------------------

class DarkFlowReportGenerator:
    """Generate the weekly Dark Flow Intelligence Report as self-contained HTML."""

    def __init__(self, config: dict, output_dir: str = "reports"):
        """
        Args:
            config: Full application config dict (or subset).
            output_dir: Directory to write report files.
        """
        self.config = config or {}
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_dark_flow_report(
        self,
        all_stocks: list,
        dark_flow_alerts: list,
        sector_allocation: dict,
        analysis_date: datetime,
        data_freshness: dict = None,
    ) -> str:
        """
        Generate the Dark Flow Intelligence Report.

        Args:
            all_stocks: All analyzed stocks with signal data (list of dicts).
            dark_flow_alerts: Pre-filtered stocks with 3+ converging dark signals.
            sector_allocation: Dict of {sector_name: {count, percentage}}.
            analysis_date: Date/time of analysis.
            data_freshness: Optional dict like {'insider': '2h ago', 'finra': '1d ago'}.

        Returns:
            Absolute path to the generated HTML file.
        """
        # Normalise inputs
        all_stocks = all_stocks or []
        dark_flow_alerts = dark_flow_alerts or []
        sector_allocation = sector_allocation or {}
        data_freshness = data_freshness or {}

        # Prepare per-section data
        alert_cards = self._prepare_alert_cards(dark_flow_alerts)
        insider_clusters = self._extract_insider_clusters(all_stocks)
        options_flow = self._extract_options_flow(all_stocks)
        congress_trades = self._extract_congress_trades(all_stocks)
        squeeze_watch = self._extract_squeeze_watch(all_stocks)
        traditional_top = self._prepare_traditional_top(all_stocks)
        timeline_rows = self._build_timeline(all_stocks)

        # Determine market context string
        n_bullish = sum(1 for s in all_stocks if _safe_get(s, 'conviction_level', '').lower() in ('critical', 'high'))
        if n_bullish > len(all_stocks) * 0.3:
            market_context = "Bullish"
        elif n_bullish < len(all_stocks) * 0.1:
            market_context = "Cautious"
        else:
            market_context = "Mixed"

        # Render
        template = Template(_DARK_FLOW_TEMPLATE)
        html = template.render(
            date_display=analysis_date.strftime("%A, %B %d %Y &mdash; %H:%M"),
            total_scanned=len(all_stocks),
            dark_flow_count=len(dark_flow_alerts),
            market_context=market_context,
            freshness=data_freshness,
            dark_flow_alerts=alert_cards,
            insider_clusters=insider_clusters,
            options_flow=options_flow,
            congress_trades=congress_trades,
            squeeze_watch=squeeze_watch,
            traditional_top=traditional_top,
            sector_allocation=sector_allocation,
            timeline_rows=timeline_rows,
        )

        # Write file
        filename = f"dark_flow_report_{analysis_date.strftime('%Y%m%d')}.html"
        filepath = self.output_dir / filename
        filepath.write_text(html, encoding="utf-8")

        logger.info(f"Generated Dark Flow report: {filepath}")
        return str(filepath)

    # ------------------------------------------------------------------
    # Private data preparation helpers
    # ------------------------------------------------------------------

    def _prepare_alert_cards(self, alerts: list) -> list:
        """Prepare card data for Dark Flow Alert section."""
        cards = []
        for s in alerts:
            cards.append({
                'ticker': _safe_get(s, 'ticker', 'N/A'),
                'company_name': _safe_get(s, 'company_name', 'N/A'),
                'current_price': float(_safe_get(s, 'current_price', 0)),
                'conviction_score': _safe_get(s, 'conviction_score', 0),
                'conviction_level': _safe_get(s, 'conviction_level', 'low'),
                'insider_signal_score': _safe_get(s, 'insider_signal_score', 0),
                'darkpool_signal_score': _safe_get(s, 'darkpool_signal_score', 0),
                'options_signal_score': _safe_get(s, 'options_signal_score', 0),
                'congress_signal_score': _safe_get(s, 'congress_signal_score', 0),
                'ftd_signal_score': _safe_get(s, 'ftd_signal_score', 0),
                'social_signal_score': _safe_get(s, 'social_signal_score', 0),
                'position_size_pct': float(_safe_get(s, 'position_size_pct', 0)),
                'risk_warnings': _safe_get(s, 'risk_warnings', []),
            })
        return cards

    def _extract_insider_clusters(self, stocks: list) -> list:
        """Extract insider cluster buy rows from stock data."""
        rows = []
        for s in stocks:
            if not _safe_get(s, 'insider_cluster_detected', False):
                continue
            buyers = _safe_get(s, 'insider_notable_buyers', [])
            if not buyers:
                # Single summary row
                rows.append({
                    'ticker': _safe_get(s, 'ticker', 'N/A'),
                    'buyer_name': 'Multiple insiders',
                    'buyer_role': '-',
                    'amount_display': 'N/A',
                    'cluster_size': _safe_get(s, 'insider_cluster_size', 0),
                    'days_since_first': _safe_get(s, 'insider_days_since_first', '-'),
                    'buy_price': float(_safe_get(s, 'insider_avg_buy_price', 0)),
                    'current_price': float(_safe_get(s, 'current_price', 0)),
                    'price_change_pct': self._calc_pct_change(
                        _safe_get(s, 'insider_avg_buy_price', 0),
                        _safe_get(s, 'current_price', 0),
                    ),
                })
            else:
                for b in buyers:
                    rows.append({
                        'ticker': _safe_get(s, 'ticker', 'N/A'),
                        'buyer_name': _safe_get(b, 'name', 'Unknown'),
                        'buyer_role': _safe_get(b, 'role', '-'),
                        'amount_display': _format_dollar(_safe_get(b, 'amount', 0)),
                        'cluster_size': _safe_get(s, 'insider_cluster_size', len(buyers)),
                        'days_since_first': _safe_get(s, 'insider_days_since_first', '-'),
                        'buy_price': float(_safe_get(b, 'price', _safe_get(s, 'insider_avg_buy_price', 0))),
                        'current_price': float(_safe_get(s, 'current_price', 0)),
                        'price_change_pct': self._calc_pct_change(
                            _safe_get(b, 'price', _safe_get(s, 'insider_avg_buy_price', 0)),
                            _safe_get(s, 'current_price', 0),
                        ),
                    })
        return rows

    def _extract_options_flow(self, stocks: list) -> list:
        """Extract unusual options flow rows."""
        rows = []
        for s in stocks:
            if _safe_get(s, 'options_signal_score', 0) <= 0:
                continue
            trades = _safe_get(s, 'options_notable_trades', [])
            if trades:
                for t in trades:
                    rows.append({
                        'ticker': _safe_get(s, 'ticker', 'N/A'),
                        'contract': _safe_get(t, 'contract', '-'),
                        'vol_oi_ratio': _safe_get(t, 'vol_oi_ratio', '-'),
                        'premium_display': _format_dollar(_safe_get(t, 'premium', 0)),
                        'trade_type': _safe_get(t, 'trade_type', 'Block'),
                        'direction': _safe_get(t, 'direction', 'Neutral'),
                    })
            else:
                # Fallback summary row
                direction = 'Neutral'
                unusual = _safe_get(s, 'options_unusual_activity', {})
                if isinstance(unusual, dict):
                    direction = _safe_get(unusual, 'direction', 'Neutral')
                rows.append({
                    'ticker': _safe_get(s, 'ticker', 'N/A'),
                    'contract': '-',
                    'vol_oi_ratio': '-',
                    'premium_display': '-',
                    'trade_type': 'Summary',
                    'direction': direction,
                })
        # Sort by ticker, limit to top 20
        rows.sort(key=lambda r: r['ticker'])
        return rows[:20]

    def _extract_congress_trades(self, stocks: list) -> list:
        """Extract congressional trade rows."""
        rows = []
        for s in stocks:
            if _safe_get(s, 'congress_signal_score', 0) <= 0:
                continue
            trades = _safe_get(s, 'congress_trades', [])
            if trades:
                for ct in trades:
                    rows.append({
                        'ticker': _safe_get(s, 'ticker', 'N/A'),
                        'politician': _safe_get(ct, 'politician', 'Unknown'),
                        'trade_type': _safe_get(ct, 'type', 'Purchase'),
                        'amount_range': _safe_get(ct, 'amount_range', '-'),
                        'disclosure_date': _safe_get(ct, 'disclosure_date', '-'),
                        'recency': _safe_get(ct, 'recency', '-'),
                    })
            else:
                rows.append({
                    'ticker': _safe_get(s, 'ticker', 'N/A'),
                    'politician': '-',
                    'trade_type': '-',
                    'amount_range': '-',
                    'disclosure_date': '-',
                    'recency': '-',
                })
        return rows

    def _extract_squeeze_watch(self, stocks: list) -> list:
        """Extract short squeeze watchlist rows."""
        rows = []
        for s in stocks:
            potential = _safe_get(s, 'short_squeeze_potential', '')
            if not potential:
                continue
            rows.append({
                'ticker': _safe_get(s, 'ticker', 'N/A'),
                'short_interest_pct': float(_safe_get(s, 'short_interest_pct', 0)),
                'days_to_cover': float(_safe_get(s, 'days_to_cover', 0)),
                'ftd_trend': _safe_get(s, 'ftd_trend', 'Flat'),
                'squeeze_flag': str(potential).capitalize(),
            })
        # Sort by short interest descending
        rows.sort(key=lambda r: r['short_interest_pct'], reverse=True)
        return rows

    def _prepare_traditional_top(self, stocks: list) -> list:
        """Get top 10 stocks by combined technical + fundamental for traditional section."""
        scored = []
        for s in stocks:
            tech = float(_safe_get(s, 'technical_score', 0))
            fund = float(_safe_get(s, 'fundamental_score', 0))
            scored.append({
                'ticker': _safe_get(s, 'ticker', 'N/A'),
                'company_name': _safe_get(s, 'company_name', 'N/A'),
                'technical_score': tech,
                'fundamental_score': fund,
                'conviction_level': _safe_get(s, 'conviction_level', 'low'),
                'current_price': float(_safe_get(s, 'current_price', 0)),
                '_combined': tech + fund,
            })
        scored.sort(key=lambda r: r['_combined'], reverse=True)
        return scored[:10]

    def _build_timeline(self, stocks: list) -> list:
        """Build signal timeline matrix (all stocks with at least 1 signal)."""
        rows = []
        for s in stocks:
            insider = _safe_get(s, 'insider_signal_score', 0) > 0
            darkpool = _safe_get(s, 'darkpool_signal_score', 0) > 0
            options = _safe_get(s, 'options_signal_score', 0) > 0
            congress = _safe_get(s, 'congress_signal_score', 0) > 0
            ftd = _safe_get(s, 'ftd_signal_score', 0) > 0
            social = _safe_get(s, 'social_signal_score', 0) > 0
            count = sum([insider, darkpool, options, congress, ftd, social])
            if count == 0:
                continue
            rows.append({
                'ticker': _safe_get(s, 'ticker', 'N/A'),
                'insider': insider,
                'darkpool': darkpool,
                'options': options,
                'congress': congress,
                'ftd': ftd,
                'social': social,
                'count': count,
            })
        rows.sort(key=lambda r: r['count'], reverse=True)
        return rows

    @staticmethod
    def _calc_pct_change(old_price, new_price) -> float:
        """Calculate percentage change between two prices."""
        try:
            old_price = float(old_price)
            new_price = float(new_price)
        except (TypeError, ValueError):
            return 0.0
        if old_price == 0:
            return 0.0
        return ((new_price - old_price) / old_price) * 100
