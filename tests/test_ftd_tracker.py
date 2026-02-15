"""
Unit tests for FTD & Short Interest tracker
"""
import unittest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import BytesIO
import zipfile
import csv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.signals.ftd_tracker import FTDShortTracker


def _make_ftd_zip(rows: list) -> bytes:
    """
    Create a fake SEC FTD zip file from row data.

    Args:
        rows: List of (date, cusip, symbol, qty, desc, price) tuples

    Returns:
        Zip file bytes
    """
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        lines = "SETTLEMENT DATE|CUSIP|SYMBOL|QUANTITY (FAILS)|DESCRIPTION|PRICE\n"
        for r in rows:
            lines += "|".join(str(x) for x in r) + "\n"
        zf.writestr("cnsfails.txt", lines.encode("latin-1"))
    return buf.getvalue()


def _make_short_volume_text(rows: list) -> str:
    """
    Create fake FINRA short volume text.

    Args:
        rows: List of (date, symbol, short_vol, short_exempt, total) tuples

    Returns:
        Pipe-delimited text
    """
    lines = ["Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market"]
    for r in rows:
        lines.append("|".join(str(x) for x in r) + "|Q")
    return "\n".join(lines)


class TestFTDZipParsing(unittest.TestCase):
    """Test FTD zip file parsing"""

    def test_parse_ftd_zip_valid(self):
        tracker = FTDShortTracker()
        zip_bytes = _make_ftd_zip([
            ("20260101", "000000000", "AAPL", "50000", "APPLE INC", "150.00"),
            ("20260102", "000000000", "AAPL", "75000", "APPLE INC", "151.00"),
            ("20260101", "111111111", "GME", "200000", "GAMESTOP CORP", "25.00"),
        ])
        rows = tracker._parse_ftd_zip(zip_bytes)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["symbol"], "AAPL")
        self.assertEqual(rows[0]["quantity"], 50000)
        self.assertEqual(rows[2]["symbol"], "GME")
        self.assertEqual(rows[2]["quantity"], 200000)

    def test_parse_ftd_zip_empty(self):
        tracker = FTDShortTracker()
        zip_bytes = _make_ftd_zip([])
        rows = tracker._parse_ftd_zip(zip_bytes)
        self.assertEqual(rows, [])

    def test_parse_ftd_zip_malformed_row(self):
        """Malformed rows should be skipped, not crash."""
        tracker = FTDShortTracker()
        buf = BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            content = (
                "HEADER|LINE\n"
                "20260101|CUS|AAPL|notanumber|DESC|150\n"
                "20260101|CUS|GME|10000|DESC|25\n"
            )
            zf.writestr("test.txt", content.encode("latin-1"))
        rows = tracker._parse_ftd_zip(buf.getvalue())
        # First row malformed (quantity not int), second row valid
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["symbol"], "GME")


class TestFTDAnalysis(unittest.TestCase):
    """Test FTD pattern analysis"""

    def setUp(self):
        self.tracker = FTDShortTracker()

    def test_analyze_ftd_no_records(self):
        result = self.tracker._analyze_ftd([])
        self.assertEqual(result["current"], 0)
        self.assertEqual(result["average"], 0.0)
        self.assertEqual(result["trend"], "stable")
        self.assertFalse(result["on_threshold_list"])

    def test_analyze_ftd_spike(self):
        # Average of first 4 = 10k, last record = 100k => spike 5.88x
        records = [
            {"settlement_date": f"2026010{i}", "quantity": 10000}
            for i in range(1, 5)
        ] + [{"settlement_date": "20260105", "quantity": 100000}]

        result = self.tracker._analyze_ftd(records)
        self.assertEqual(result["current"], 100000)
        self.assertGreater(result["spike_ratio"], 3.0)

    def test_analyze_ftd_increasing_trend(self):
        records = [
            {"settlement_date": f"2026010{i}", "quantity": i * 10000}
            for i in range(1, 9)
        ]
        result = self.tracker._analyze_ftd(records)
        self.assertEqual(result["trend"], "increasing")

    def test_analyze_ftd_decreasing_trend(self):
        records = [
            {"settlement_date": f"2026010{i}", "quantity": (9 - i) * 10000}
            for i in range(1, 9)
        ]
        result = self.tracker._analyze_ftd(records)
        self.assertEqual(result["trend"], "decreasing")

    def test_threshold_list_detection(self):
        """13+ consecutive days with qty >= 10000 = on threshold list."""
        records = [
            {"settlement_date": f"202601{i:02d}", "quantity": 15000}
            for i in range(1, 16)
        ]
        result = self.tracker._analyze_ftd(records)
        self.assertTrue(result["on_threshold_list"])

    def test_threshold_list_broken_streak(self):
        """Break in streak means NOT on threshold list."""
        records = [
            {"settlement_date": f"202601{i:02d}", "quantity": 15000}
            for i in range(1, 13)
        ]
        # Day 13 drops below threshold
        records.append({"settlement_date": "20260113", "quantity": 5000})
        result = self.tracker._analyze_ftd(records)
        self.assertFalse(result["on_threshold_list"])


class TestShortInterestAnalysis(unittest.TestCase):
    """Test short sale volume analysis"""

    def setUp(self):
        self.tracker = FTDShortTracker()

    def test_no_records(self):
        result = self.tracker._analyze_short_interest([])
        self.assertEqual(result["ratio_trend"], "neutral")
        self.assertEqual(result["days_to_cover"], 0.0)

    def test_high_short_ratio(self):
        records = [
            {"date": f"2026010{i}", "short_volume": 800000, "total_volume": 1000000}
            for i in range(1, 6)
        ]
        result = self.tracker._analyze_short_interest(records)
        self.assertGreater(result["days_to_cover"], 1.0)

    def test_increasing_short_ratio(self):
        # First half: low short ratio, second half: high
        records = [
            {"date": f"2026010{i}", "short_volume": 100000, "total_volume": 1000000}
            for i in range(1, 4)
        ] + [
            {"date": f"2026010{i}", "short_volume": 700000, "total_volume": 1000000}
            for i in range(4, 7)
        ]
        result = self.tracker._analyze_short_interest(records)
        self.assertEqual(result["ratio_trend"], "increasing")


class TestScoring(unittest.TestCase):
    """Test signal scoring logic"""

    def setUp(self):
        self.tracker = FTDShortTracker()

    def test_neutral_score(self):
        ftd = {
            "current": 0, "average": 0.0, "spike_ratio": 0.0,
            "trend": "stable", "on_threshold_list": False,
        }
        short = {"ratio_trend": "neutral", "days_to_cover": 0.0}
        score = self.tracker._calculate_score(ftd, short)
        self.assertLessEqual(score, 20)

    def test_high_spike_score(self):
        ftd = {
            "current": 500000, "average": 50000.0, "spike_ratio": 10.0,
            "trend": "increasing", "on_threshold_list": True,
        }
        short = {"ratio_trend": "increasing", "days_to_cover": 6.0}
        score = self.tracker._calculate_score(ftd, short)
        self.assertGreaterEqual(score, 80)

    def test_moderate_spike_score(self):
        ftd = {
            "current": 100000, "average": 20000.0, "spike_ratio": 5.0,
            "trend": "stable", "on_threshold_list": False,
        }
        short = {"ratio_trend": "stable", "days_to_cover": 1.0}
        score = self.tracker._calculate_score(ftd, short)
        self.assertTrue(40 <= score <= 70)

    def test_score_clamped_0_100(self):
        ftd = {
            "current": 0, "average": 1.0, "spike_ratio": 0.0,
            "trend": "decreasing", "on_threshold_list": False,
        }
        short = {"ratio_trend": "decreasing", "days_to_cover": 0.0}
        score = self.tracker._calculate_score(ftd, short)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)


class TestDirection(unittest.TestCase):
    """Test signal direction classification"""

    def setUp(self):
        self.tracker = FTDShortTracker()

    def test_squeeze_potential(self):
        ftd = {
            "current": 500000, "average": 50000, "spike_ratio": 10.0,
            "trend": "increasing", "on_threshold_list": True,
        }
        short = {"ratio_trend": "decreasing", "days_to_cover": 5.0}
        direction = self.tracker._determine_direction(ftd, short, 85.0)
        self.assertEqual(direction, "squeeze_potential")

    def test_covering_direction(self):
        ftd = {
            "current": 5000, "average": 10000, "spike_ratio": 0.5,
            "trend": "decreasing", "on_threshold_list": False,
        }
        short = {"ratio_trend": "decreasing", "days_to_cover": 1.0}
        direction = self.tracker._determine_direction(ftd, short, 30.0)
        self.assertEqual(direction, "covering")

    def test_neutral_direction(self):
        ftd = {
            "current": 1000, "average": 1000, "spike_ratio": 1.0,
            "trend": "stable", "on_threshold_list": False,
        }
        short = {"ratio_trend": "stable", "days_to_cover": 0.5}
        direction = self.tracker._determine_direction(ftd, short, 20.0)
        self.assertEqual(direction, "neutral")

    def test_pressure_direction(self):
        ftd = {
            "current": 200000, "average": 20000, "spike_ratio": 10.0,
            "trend": "increasing", "on_threshold_list": False,
        }
        short = {"ratio_trend": "increasing", "days_to_cover": 1.0}
        direction = self.tracker._determine_direction(ftd, short, 50.0)
        self.assertEqual(direction, "pressure")


class TestAnalyzeStock(unittest.TestCase):
    """Test the main analyze_stock entry point with mocked data"""

    def setUp(self):
        self.tracker = FTDShortTracker()

    def test_analyze_stock_with_data(self):
        """Inject mock data and verify full pipeline."""
        self.tracker._ftd_cache["TEST"] = [
            {"settlement_date": f"2026010{i}", "quantity": i * 5000}
            for i in range(1, 6)
        ]
        self.tracker._short_volume_cache["TEST"] = [
            {"date": f"2026010{i}", "short_volume": 300000, "total_volume": 1000000}
            for i in range(1, 6)
        ]

        result = self.tracker.analyze_stock("TEST")

        # Verify all expected keys
        expected_keys = {
            "ftd_signal_score", "ftd_signal_direction",
            "ftd_current_quantity", "ftd_average_quantity",
            "ftd_spike_ratio", "ftd_trend", "ftd_on_threshold_list",
            "short_ratio_trend", "short_estimated_days_to_cover",
            "short_squeeze_potential",
        }
        self.assertEqual(set(result.keys()), expected_keys)

        # Score within valid range
        self.assertGreaterEqual(result["ftd_signal_score"], 0)
        self.assertLessEqual(result["ftd_signal_score"], 100)

        # Direction is one of the valid values
        self.assertIn(result["ftd_signal_direction"], [
            "squeeze_potential", "covering", "neutral", "pressure"
        ])

    def test_analyze_stock_no_data(self):
        """No data for ticker should return neutral."""
        # Mark data as loaded so it doesn't try to fetch
        self.tracker._ftd_cache["_LOADED"] = []
        self.tracker._short_volume_cache["_LOADED"] = []

        result = self.tracker.analyze_stock("UNKNOWN")
        self.assertEqual(result["ftd_signal_direction"], "neutral")
        self.assertEqual(result["ftd_current_quantity"], 0)

    def test_analyze_batch(self):
        """Batch analysis should return results for all tickers."""
        for sym in ["AAA", "BBB"]:
            self.tracker._ftd_cache[sym] = [
                {"settlement_date": "20260101", "quantity": 10000}
            ]
            self.tracker._short_volume_cache[sym] = [
                {"date": "20260101", "short_volume": 50000, "total_volume": 100000}
            ]

        results = self.tracker.analyze_batch(["AAA", "BBB", "CCC"])
        self.assertIn("AAA", results)
        self.assertIn("BBB", results)
        self.assertIn("CCC", results)
        # CCC has no data => neutral
        self.assertEqual(results["CCC"]["ftd_signal_direction"], "neutral")


class TestHelpers(unittest.TestCase):
    """Test helper methods"""

    def test_compute_trend_stable(self):
        result = FTDShortTracker._compute_trend_from_values([10, 10, 10, 10])
        self.assertEqual(result, "stable")

    def test_compute_trend_increasing(self):
        result = FTDShortTracker._compute_trend_from_values([10, 10, 20, 20])
        self.assertEqual(result, "increasing")

    def test_compute_trend_decreasing(self):
        result = FTDShortTracker._compute_trend_from_values([20, 20, 10, 10])
        self.assertEqual(result, "decreasing")

    def test_compute_trend_single_value(self):
        result = FTDShortTracker._compute_trend_from_values([42])
        self.assertEqual(result, "stable")

    def test_compute_trend_empty(self):
        result = FTDShortTracker._compute_trend_from_values([])
        self.assertEqual(result, "stable")

    def test_check_threshold_list_short_list(self):
        result = FTDShortTracker._check_threshold_list([15000] * 5)
        self.assertFalse(result)

    def test_get_ftd_periods(self):
        periods = FTDShortTracker._get_ftd_periods(2)
        self.assertEqual(len(periods), 2)
        for yyyymm, half in periods:
            self.assertEqual(len(yyyymm), 6)
            self.assertIn(half, ("a", "b"))

    def test_get_recent_trading_dates(self):
        dates = FTDShortTracker._get_recent_trading_dates(5)
        self.assertEqual(len(dates), 5)
        for dt in dates:
            self.assertLess(dt.weekday(), 5)  # Mon-Fri only


class TestNeutralResult(unittest.TestCase):
    """Test neutral/default result structure"""

    def test_neutral_result_keys(self):
        tracker = FTDShortTracker()
        result = tracker._neutral_result("TEST")
        expected_keys = {
            "ftd_signal_score", "ftd_signal_direction",
            "ftd_current_quantity", "ftd_average_quantity",
            "ftd_spike_ratio", "ftd_trend", "ftd_on_threshold_list",
            "short_ratio_trend", "short_estimated_days_to_cover",
            "short_squeeze_potential",
        }
        self.assertEqual(set(result.keys()), expected_keys)
        self.assertEqual(result["ftd_signal_direction"], "neutral")
        self.assertFalse(result["short_squeeze_potential"])


def run_tests():
    """Run all FTD tracker tests"""
    print("\n" + "=" * 60)
    print("Running FTD Tracker Unit Tests")
    print("=" * 60 + "\n")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestFTDZipParsing))
    suite.addTests(loader.loadTestsFromTestCase(TestFTDAnalysis))
    suite.addTests(loader.loadTestsFromTestCase(TestShortInterestAnalysis))
    suite.addTests(loader.loadTestsFromTestCase(TestScoring))
    suite.addTests(loader.loadTestsFromTestCase(TestDirection))
    suite.addTests(loader.loadTestsFromTestCase(TestAnalyzeStock))
    suite.addTests(loader.loadTestsFromTestCase(TestHelpers))
    suite.addTests(loader.loadTestsFromTestCase(TestNeutralResult))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"Success rate: {passed / total * 100:.1f}%" if total else "N/A")
    print("=" * 60 + "\n")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
