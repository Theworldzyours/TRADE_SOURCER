"""
Tests for the Dark Flow Intelligence Report Generator
"""
import unittest
import sys
import tempfile
import os
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.reports.dark_flow_report import DarkFlowReportGenerator


def _make_stock(
    ticker="AAPL",
    company_name="Apple Inc.",
    current_price=185.50,
    conviction_score=78,
    conviction_level="high",
    active_dark_signals=4,
    position_size_pct=10.0,
    insider_signal_score=65,
    insider_cluster_detected=True,
    insider_notable_buyers=None,
    darkpool_signal_score=70,
    darkpool_signal_direction="bullish",
    options_signal_score=55,
    options_unusual_activity=None,
    options_notable_trades=None,
    congress_signal_score=40,
    congress_trades=None,
    ftd_signal_score=30,
    short_squeeze_potential="medium",
    short_interest_pct=12.5,
    days_to_cover=3.2,
    ftd_trend="Rising",
    social_signal_score=20,
    social_trending=True,
    technical_score=72,
    fundamental_score=68,
    risk_warnings=None,
    **overrides,
):
    """Build a stock dict with sensible defaults; override any key."""
    stock = {
        "ticker": ticker,
        "company_name": company_name,
        "current_price": current_price,
        "conviction_score": conviction_score,
        "conviction_level": conviction_level,
        "active_dark_signals": active_dark_signals,
        "position_size_pct": position_size_pct,
        "insider_signal_score": insider_signal_score,
        "insider_cluster_detected": insider_cluster_detected,
        "insider_notable_buyers": insider_notable_buyers or [
            {"name": "Tim Cook", "role": "CEO", "amount": 2_500_000, "price": 178.00},
            {"name": "Luca Maestri", "role": "CFO", "amount": 1_200_000, "price": 179.50},
        ],
        "insider_cluster_size": 2,
        "insider_days_since_first": 8,
        "insider_avg_buy_price": 178.75,
        "darkpool_signal_score": darkpool_signal_score,
        "darkpool_signal_direction": darkpool_signal_direction,
        "options_signal_score": options_signal_score,
        "options_unusual_activity": options_unusual_activity or {"direction": "Bullish"},
        "options_notable_trades": options_notable_trades or [
            {
                "contract": "AAPL 200C 03/21",
                "vol_oi_ratio": "5.2x",
                "premium": 3_400_000,
                "trade_type": "Sweep",
                "direction": "Bullish",
            }
        ],
        "congress_signal_score": congress_signal_score,
        "congress_trades": congress_trades or [
            {
                "politician": "Nancy Pelosi",
                "type": "Purchase",
                "amount_range": "$500K - $1M",
                "disclosure_date": "2026-02-10",
                "recency": "5 days ago",
            }
        ],
        "ftd_signal_score": ftd_signal_score,
        "short_squeeze_potential": short_squeeze_potential,
        "short_interest_pct": short_interest_pct,
        "days_to_cover": days_to_cover,
        "ftd_trend": ftd_trend,
        "social_signal_score": social_signal_score,
        "social_trending": social_trending,
        "technical_score": technical_score,
        "fundamental_score": fundamental_score,
        "risk_warnings": risk_warnings or [],
    }
    stock.update(overrides)
    return stock


def _make_minimal_stock(ticker="ZZZ", company_name="Minimal Corp"):
    """Stock with almost no signal data — tests graceful defaults."""
    return {
        "ticker": ticker,
        "company_name": company_name,
        "current_price": 10.00,
    }


class TestDarkFlowReportFull(unittest.TestCase):
    """Tests with fully populated data."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.gen = DarkFlowReportGenerator(config={}, output_dir=self.tmpdir)
        self.date = datetime(2026, 2, 15, 8, 0)
        self.stock_a = _make_stock(ticker="AAPL", conviction_level="critical")
        self.stock_b = _make_stock(
            ticker="NVDA",
            company_name="NVIDIA Corp",
            current_price=890.00,
            conviction_score=85,
            conviction_level="high",
            active_dark_signals=3,
            insider_notable_buyers=[
                {"name": "Jensen Huang", "role": "CEO", "amount": 5_000_000, "price": 850.00},
            ],
            congress_trades=[],
            congress_signal_score=0,
            short_squeeze_potential="",
            risk_warnings=["Elevated P/E ratio"],
        )
        self.stock_c = _make_stock(
            ticker="GME",
            company_name="GameStop Corp",
            current_price=22.00,
            conviction_score=45,
            conviction_level="medium",
            active_dark_signals=2,
            insider_signal_score=0,
            insider_cluster_detected=False,
            insider_notable_buyers=[],
            darkpool_signal_score=0,
            options_signal_score=60,
            congress_signal_score=0,
            congress_trades=[],
            ftd_signal_score=80,
            short_squeeze_potential="high",
            short_interest_pct=35.0,
            days_to_cover=6.5,
            ftd_trend="Rising",
        )
        # Dark flow alerts = stocks with 3+ signals (pre-filtered)
        self.dark_flow_alerts = [self.stock_a, self.stock_b]
        self.all_stocks = [self.stock_a, self.stock_b, self.stock_c]
        self.sector_alloc = {
            "Technology": {"count": 2, "percentage": 66.7},
            "Consumer Discretionary": {"count": 1, "percentage": 33.3},
        }
        self.freshness = {
            "insider": "2h ago",
            "finra": "1d ago",
            "options": "30min ago",
            "congress": "3d ago",
        }

    def test_generates_file(self):
        path = self.gen.generate_dark_flow_report(
            self.all_stocks, self.dark_flow_alerts, self.sector_alloc, self.date, self.freshness,
        )
        self.assertTrue(os.path.isfile(path))
        self.assertTrue(path.endswith(".html"))

    def test_html_is_valid_structure(self):
        path = self.gen.generate_dark_flow_report(
            self.all_stocks, self.dark_flow_alerts, self.sector_alloc, self.date,
        )
        html = Path(path).read_text(encoding="utf-8")
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("<html lang=\"en\">", html)
        self.assertIn("</html>", html)

    def test_all_seven_sections_present(self):
        path = self.gen.generate_dark_flow_report(
            self.all_stocks, self.dark_flow_alerts, self.sector_alloc, self.date,
        )
        html = Path(path).read_text(encoding="utf-8")
        self.assertIn("1. Dark Flow Alerts", html)
        self.assertIn("2. Insider Cluster Buys", html)
        self.assertIn("3. Unusual Options Flow", html)
        self.assertIn("4. Congressional Trades", html)
        self.assertIn("5. Short Squeeze Watch", html)
        self.assertIn("6. Traditional Analysis", html)
        self.assertIn("7. Signal Timeline", html)

    def test_dark_flow_alerts_shows_only_3plus(self):
        """Dark Flow Alerts section should only contain stocks with 3+ signals."""
        path = self.gen.generate_dark_flow_report(
            self.all_stocks, self.dark_flow_alerts, self.sector_alloc, self.date,
        )
        html = Path(path).read_text(encoding="utf-8")
        # AAPL and NVDA should be in alert cards, GME should NOT
        # Check the alert card section specifically (between section 1 and section 2 headings)
        alert_section_start = html.index("1. Dark Flow Alerts")
        alert_section_end = html.index("2. Insider Cluster Buys")
        alert_section = html[alert_section_start:alert_section_end]

        self.assertIn("AAPL", alert_section)
        self.assertIn("NVDA", alert_section)
        self.assertNotIn("GME", alert_section)

    def test_dark_theme_colors(self):
        path = self.gen.generate_dark_flow_report(
            self.all_stocks, self.dark_flow_alerts, self.sector_alloc, self.date,
        )
        html = Path(path).read_text(encoding="utf-8")
        # Verify dark theme CSS is present
        self.assertIn("#0f0f23", html)  # body background
        self.assertIn("#16213e", html)  # card background
        self.assertIn("#e94560", html)  # accent/highlight
        self.assertIn("#00d25b", html)  # bullish green

    def test_freshness_indicators(self):
        path = self.gen.generate_dark_flow_report(
            self.all_stocks, self.dark_flow_alerts, self.sector_alloc, self.date, self.freshness,
        )
        html = Path(path).read_text(encoding="utf-8")
        self.assertIn("insider: 2h ago", html)
        self.assertIn("finra: 1d ago", html)

    def test_conviction_badges(self):
        path = self.gen.generate_dark_flow_report(
            self.all_stocks, self.dark_flow_alerts, self.sector_alloc, self.date,
        )
        html = Path(path).read_text(encoding="utf-8")
        self.assertIn("conviction-critical", html)
        self.assertIn("conviction-high", html)

    def test_signal_dots_present(self):
        path = self.gen.generate_dark_flow_report(
            self.all_stocks, self.dark_flow_alerts, self.sector_alloc, self.date,
        )
        html = Path(path).read_text(encoding="utf-8")
        self.assertIn("active-insider", html)
        self.assertIn("active-darkpool", html)
        self.assertIn("active-options", html)

    def test_position_sizing_shown(self):
        path = self.gen.generate_dark_flow_report(
            self.all_stocks, self.dark_flow_alerts, self.sector_alloc, self.date,
        )
        html = Path(path).read_text(encoding="utf-8")
        self.assertIn("Suggested position", html)
        self.assertIn("of portfolio", html)

    def test_risk_warnings_shown(self):
        path = self.gen.generate_dark_flow_report(
            self.all_stocks, self.dark_flow_alerts, self.sector_alloc, self.date,
        )
        html = Path(path).read_text(encoding="utf-8")
        self.assertIn("Elevated P/E ratio", html)

    def test_insider_cluster_rows(self):
        path = self.gen.generate_dark_flow_report(
            self.all_stocks, self.dark_flow_alerts, self.sector_alloc, self.date,
        )
        html = Path(path).read_text(encoding="utf-8")
        self.assertIn("Tim Cook", html)
        self.assertIn("Jensen Huang", html)

    def test_options_flow_rows(self):
        path = self.gen.generate_dark_flow_report(
            self.all_stocks, self.dark_flow_alerts, self.sector_alloc, self.date,
        )
        html = Path(path).read_text(encoding="utf-8")
        self.assertIn("AAPL 200C 03/21", html)
        self.assertIn("Sweep", html)

    def test_congress_trades_rows(self):
        path = self.gen.generate_dark_flow_report(
            self.all_stocks, self.dark_flow_alerts, self.sector_alloc, self.date,
        )
        html = Path(path).read_text(encoding="utf-8")
        self.assertIn("Nancy Pelosi", html)

    def test_squeeze_watch_rows(self):
        path = self.gen.generate_dark_flow_report(
            self.all_stocks, self.dark_flow_alerts, self.sector_alloc, self.date,
        )
        html = Path(path).read_text(encoding="utf-8")
        self.assertIn("GME", html)
        # GME has 35% short interest
        self.assertIn("35.0%", html)

    def test_sector_allocation_rendered(self):
        path = self.gen.generate_dark_flow_report(
            self.all_stocks, self.dark_flow_alerts, self.sector_alloc, self.date,
        )
        html = Path(path).read_text(encoding="utf-8")
        self.assertIn("Technology", html)
        self.assertIn("66.7%", html)

    def test_timeline_rows(self):
        path = self.gen.generate_dark_flow_report(
            self.all_stocks, self.dark_flow_alerts, self.sector_alloc, self.date,
        )
        html = Path(path).read_text(encoding="utf-8")
        self.assertIn("timeline-dot", html)

    def test_accessibility_skip_link(self):
        path = self.gen.generate_dark_flow_report(
            self.all_stocks, self.dark_flow_alerts, self.sector_alloc, self.date,
        )
        html = Path(path).read_text(encoding="utf-8")
        self.assertIn("skip-link", html)
        self.assertIn('role="main"', html)
        self.assertIn('role="banner"', html)
        self.assertIn('role="contentinfo"', html)
        self.assertIn('aria-label=', html)

    def test_viewport_meta(self):
        path = self.gen.generate_dark_flow_report(
            self.all_stocks, self.dark_flow_alerts, self.sector_alloc, self.date,
        )
        html = Path(path).read_text(encoding="utf-8")
        self.assertIn('name="viewport"', html)

    def test_no_external_dependencies(self):
        """Report should be self-contained: no external CSS/JS links."""
        path = self.gen.generate_dark_flow_report(
            self.all_stocks, self.dark_flow_alerts, self.sector_alloc, self.date,
        )
        html = Path(path).read_text(encoding="utf-8")
        self.assertNotIn('<link rel="stylesheet"', html)
        self.assertNotIn("<script src=", html)
        self.assertNotIn("<script>", html)


class TestDarkFlowReportPartialData(unittest.TestCase):
    """Tests with partial / missing signal data."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.gen = DarkFlowReportGenerator(config={}, output_dir=self.tmpdir)
        self.date = datetime(2026, 2, 15, 8, 0)

    def test_missing_signals_defaults_gracefully(self):
        """Stock with only ticker and price should not crash."""
        minimal = _make_minimal_stock()
        path = self.gen.generate_dark_flow_report(
            all_stocks=[minimal],
            dark_flow_alerts=[],
            sector_allocation={},
            analysis_date=self.date,
        )
        html = Path(path).read_text(encoding="utf-8")
        self.assertIn("ZZZ", html)
        self.assertIn("<!DOCTYPE html>", html)

    def test_missing_insider_data(self):
        stock = _make_stock(
            insider_signal_score=0,
            insider_cluster_detected=False,
            insider_notable_buyers=[],
        )
        path = self.gen.generate_dark_flow_report(
            [stock], [], {}, self.date,
        )
        html = Path(path).read_text(encoding="utf-8")
        self.assertIn("AAPL", html)  # Stock still appears in timeline / traditional

    def test_missing_options_data(self):
        stock = _make_stock(
            options_signal_score=0,
            options_notable_trades=[],
            options_unusual_activity=None,
        )
        path = self.gen.generate_dark_flow_report(
            [stock], [], {}, self.date,
        )
        self.assertTrue(os.path.isfile(path))

    def test_missing_congress_data(self):
        stock = _make_stock(congress_signal_score=0, congress_trades=[])
        path = self.gen.generate_dark_flow_report(
            [stock], [], {}, self.date,
        )
        html = Path(path).read_text(encoding="utf-8")
        self.assertIn("No notable congressional trades", html)

    def test_missing_squeeze_data(self):
        stock = _make_stock(short_squeeze_potential="", ftd_signal_score=0)
        path = self.gen.generate_dark_flow_report(
            [stock], [], {}, self.date,
        )
        html = Path(path).read_text(encoding="utf-8")
        self.assertIn("No stocks on the Short Squeeze Watch", html)

    def test_none_freshness(self):
        path = self.gen.generate_dark_flow_report(
            [_make_stock()], [_make_stock()], {}, self.date, data_freshness=None,
        )
        self.assertTrue(os.path.isfile(path))

    def test_mixed_full_and_minimal(self):
        """Mix of fully populated and minimal stocks should render fine."""
        stocks = [_make_stock(), _make_minimal_stock("BBB"), _make_minimal_stock("CCC")]
        path = self.gen.generate_dark_flow_report(
            stocks, [_make_stock()], {}, self.date,
        )
        html = Path(path).read_text(encoding="utf-8")
        self.assertIn("AAPL", html)
        self.assertIn("BBB", html)


class TestDarkFlowReportEmpty(unittest.TestCase):
    """Tests with empty stock lists."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.gen = DarkFlowReportGenerator(config={}, output_dir=self.tmpdir)
        self.date = datetime(2026, 2, 15, 8, 0)

    def test_empty_all_stocks(self):
        path = self.gen.generate_dark_flow_report(
            all_stocks=[],
            dark_flow_alerts=[],
            sector_allocation={},
            analysis_date=self.date,
        )
        html = Path(path).read_text(encoding="utf-8")
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("0", html)  # total scanned = 0

    def test_empty_shows_empty_states(self):
        path = self.gen.generate_dark_flow_report([], [], {}, self.date)
        html = Path(path).read_text(encoding="utf-8")
        self.assertIn("No Dark Flow Alerts", html)
        self.assertIn("No insider cluster buys", html)
        self.assertIn("No unusual options flow", html)
        self.assertIn("No notable congressional trades", html)
        self.assertIn("No stocks on the Short Squeeze Watch", html)
        self.assertIn("No traditional analysis data", html)
        self.assertIn("No signal data for timeline", html)

    def test_none_inputs_treated_as_empty(self):
        path = self.gen.generate_dark_flow_report(
            all_stocks=None,
            dark_flow_alerts=None,
            sector_allocation=None,
            analysis_date=self.date,
            data_freshness=None,
        )
        self.assertTrue(os.path.isfile(path))

    def test_filename_includes_date(self):
        path = self.gen.generate_dark_flow_report([], [], {}, self.date)
        self.assertIn("dark_flow_report_20260215", path)


class TestDarkFlowReportAlertFilter(unittest.TestCase):
    """Verify the alert section only shows 3+ signal stocks."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.gen = DarkFlowReportGenerator(config={}, output_dir=self.tmpdir)
        self.date = datetime(2026, 2, 15, 8, 0)

    def test_two_signal_stock_not_in_alerts(self):
        """A stock with only 2 signals should not appear in alert cards when properly pre-filtered."""
        stock_2sig = _make_stock(
            ticker="TWO",
            active_dark_signals=2,
            insider_signal_score=50,
            darkpool_signal_score=60,
            options_signal_score=0,
            congress_signal_score=0,
            ftd_signal_score=0,
            social_signal_score=0,
        )
        stock_4sig = _make_stock(
            ticker="FOUR",
            active_dark_signals=4,
        )
        # Only stock_4sig is in alerts (pre-filtered)
        path = self.gen.generate_dark_flow_report(
            all_stocks=[stock_2sig, stock_4sig],
            dark_flow_alerts=[stock_4sig],
            sector_allocation={},
            analysis_date=self.date,
        )
        html = Path(path).read_text(encoding="utf-8")
        alert_start = html.index("1. Dark Flow Alerts")
        alert_end = html.index("2. Insider Cluster Buys")
        alert_html = html[alert_start:alert_end]

        self.assertIn("FOUR", alert_html)
        self.assertNotIn("TWO", alert_html)

    def test_three_signal_stock_in_alerts(self):
        stock_3sig = _make_stock(
            ticker="TRI",
            active_dark_signals=3,
            insider_signal_score=50,
            darkpool_signal_score=60,
            options_signal_score=40,
            congress_signal_score=0,
            ftd_signal_score=0,
            social_signal_score=0,
        )
        path = self.gen.generate_dark_flow_report(
            all_stocks=[stock_3sig],
            dark_flow_alerts=[stock_3sig],
            sector_allocation={},
            analysis_date=self.date,
        )
        html = Path(path).read_text(encoding="utf-8")
        alert_start = html.index("1. Dark Flow Alerts")
        alert_end = html.index("2. Insider Cluster Buys")
        self.assertIn("TRI", html[alert_start:alert_end])


class TestMarketContext(unittest.TestCase):
    """Verify market context determination."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.gen = DarkFlowReportGenerator(config={}, output_dir=self.tmpdir)
        self.date = datetime(2026, 2, 15, 8, 0)

    def test_bullish_context(self):
        """Mostly high conviction stocks -> Bullish."""
        stocks = [_make_stock(conviction_level="critical") for _ in range(5)]
        path = self.gen.generate_dark_flow_report(stocks, stocks, {}, self.date)
        html = Path(path).read_text(encoding="utf-8")
        self.assertIn("Bullish", html)

    def test_cautious_context(self):
        """All low conviction -> Cautious."""
        stocks = [_make_stock(conviction_level="low") for _ in range(5)]
        path = self.gen.generate_dark_flow_report(stocks, [], {}, self.date)
        html = Path(path).read_text(encoding="utf-8")
        self.assertIn("Cautious", html)

    def test_mixed_context(self):
        """Mix -> Mixed."""
        stocks = [
            _make_stock(conviction_level="high"),
            _make_stock(conviction_level="low", ticker="B"),
            _make_stock(conviction_level="low", ticker="C"),
            _make_stock(conviction_level="low", ticker="D"),
            _make_stock(conviction_level="medium", ticker="E"),
        ]
        path = self.gen.generate_dark_flow_report(stocks, [], {}, self.date)
        html = Path(path).read_text(encoding="utf-8")
        self.assertIn("Mixed", html)


if __name__ == "__main__":
    unittest.main()
