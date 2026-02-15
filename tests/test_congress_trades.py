"""
Unit tests for CongressTradesTracker
"""
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.signals.congress_trades import (
    CongressTradesTracker,
    _parse_amount_to_midpoint,
    _parse_date,
)


def _make_trade(
    representative: str = "Hon. Nancy Pelosi",
    ticker: str = "AAPL",
    tx_type: str = "purchase",
    amount: str = "$1,001 - $15,000",
    transaction_date: str = None,
    disclosure_date: str = None,
    days_ago_disclosure: int = 5,
    days_ago_transaction: int = 10,
):
    """Helper to build a mock HSW trade dict."""
    now = datetime.utcnow()
    if disclosure_date is None:
        disclosure_date = (now - timedelta(days=days_ago_disclosure)).strftime("%Y-%m-%d")
    if transaction_date is None:
        transaction_date = (now - timedelta(days=days_ago_transaction)).strftime("%Y-%m-%d")
    return {
        "representative": representative,
        "ticker": ticker,
        "type": tx_type,
        "amount": amount,
        "transaction_date": transaction_date,
        "disclosure_date": disclosure_date,
        "asset_description": f"{ticker} stock",
    }


class TestParseAmount(unittest.TestCase):
    """Test amount range parsing."""

    def test_known_ranges(self):
        self.assertEqual(_parse_amount_to_midpoint("$1,001 - $15,000"), 8_000)
        self.assertEqual(_parse_amount_to_midpoint("$100,001 - $250,000"), 175_000)

    def test_over_50m(self):
        self.assertEqual(_parse_amount_to_midpoint("Over $50,000,000"), 50_000_000)

    def test_empty(self):
        self.assertEqual(_parse_amount_to_midpoint(""), 0.0)
        self.assertEqual(_parse_amount_to_midpoint(None), 0.0)

    def test_unknown_format_two_figures(self):
        val = _parse_amount_to_midpoint("$5,000 - $10,000")
        self.assertEqual(val, 7_500)

    def test_single_figure(self):
        val = _parse_amount_to_midpoint("$50,000")
        self.assertEqual(val, 50_000)


class TestParseDate(unittest.TestCase):
    """Test date parsing."""

    def test_iso_format(self):
        dt = _parse_date("2024-06-15")
        self.assertEqual(dt, datetime(2024, 6, 15))

    def test_us_format(self):
        dt = _parse_date("06/15/2024")
        self.assertEqual(dt, datetime(2024, 6, 15))

    def test_none(self):
        self.assertIsNone(_parse_date(None))
        self.assertIsNone(_parse_date(""))

    def test_garbage(self):
        self.assertIsNone(_parse_date("not-a-date"))


class TestCongressTradesTracker(unittest.TestCase):
    """Test the main tracker class."""

    def setUp(self):
        self.tracker = CongressTradesTracker({'lookback_days': 45})

    # -- Neutral when no trades --

    @patch.object(CongressTradesTracker, '_fetch_all_trades', return_value=[])
    def test_no_trades_returns_neutral(self, _mock_fetch):
        result = self.tracker.analyze_stock("XYZ")
        self.assertEqual(result['congress_signal_score'], 0.0)
        self.assertEqual(result['congress_signal_direction'], 'neutral')
        self.assertEqual(result['congress_trade_count'], 0)
        self.assertFalse(result['congress_cluster_detected'])

    # -- Single small purchase --

    @patch.object(CongressTradesTracker, '_fetch_all_trades')
    def test_single_small_purchase(self, mock_fetch):
        mock_fetch.return_value = [
            _make_trade(ticker="AAPL", amount="$1,001 - $15,000", days_ago_disclosure=20),
        ]
        result = self.tracker.analyze_stock("AAPL")
        self.assertGreaterEqual(result['congress_signal_score'], 20)
        self.assertLessEqual(result['congress_signal_score'], 40)
        self.assertEqual(result['congress_signal_direction'], 'bullish')
        self.assertEqual(result['congress_trade_count'], 1)
        self.assertEqual(result['congress_unique_traders'], 1)
        self.assertFalse(result['congress_cluster_detected'])

    # -- Single large purchase ($100K+) --

    @patch.object(CongressTradesTracker, '_fetch_all_trades')
    def test_single_large_purchase(self, mock_fetch):
        mock_fetch.return_value = [
            _make_trade(
                ticker="MSFT",
                amount="$100,001 - $250,000",
                days_ago_disclosure=10,
            ),
        ]
        result = self.tracker.analyze_stock("MSFT")
        self.assertGreaterEqual(result['congress_signal_score'], 50)
        self.assertLessEqual(result['congress_signal_score'], 80)

    # -- Cluster detection (multiple politicians) --

    @patch.object(CongressTradesTracker, '_fetch_all_trades')
    def test_cluster_detected(self, mock_fetch):
        mock_fetch.return_value = [
            _make_trade(representative="Rep. A", ticker="NVDA", days_ago_disclosure=5),
            _make_trade(representative="Rep. B", ticker="NVDA", days_ago_disclosure=8),
        ]
        result = self.tracker.analyze_stock("NVDA")
        self.assertTrue(result['congress_cluster_detected'])
        self.assertGreaterEqual(result['congress_signal_score'], 70)
        self.assertEqual(result['congress_unique_traders'], 2)

    # -- Three-politician cluster --

    @patch.object(CongressTradesTracker, '_fetch_all_trades')
    def test_three_politician_cluster(self, mock_fetch):
        mock_fetch.return_value = [
            _make_trade(representative="Rep. A", ticker="GOOG", days_ago_disclosure=3),
            _make_trade(representative="Rep. B", ticker="GOOG", days_ago_disclosure=5),
            _make_trade(representative="Rep. C", ticker="GOOG", days_ago_disclosure=7),
        ]
        result = self.tracker.analyze_stock("GOOG")
        self.assertTrue(result['congress_cluster_detected'])
        self.assertGreaterEqual(result['congress_signal_score'], 90)

    # -- Recency bonus --

    @patch.object(CongressTradesTracker, '_fetch_all_trades')
    def test_recency_bonus(self, mock_fetch):
        # Trade 20 days ago -> no recency bonus
        mock_fetch.return_value = [
            _make_trade(ticker="TSLA", days_ago_disclosure=20),
        ]
        result_old = self.tracker.analyze_stock("TSLA")

        # Trade 3 days ago -> gets recency bonus
        mock_fetch.return_value = [
            _make_trade(ticker="TSLA", days_ago_disclosure=3),
        ]
        result_new = self.tracker.analyze_stock("TSLA")

        self.assertGreater(
            result_new['congress_signal_score'],
            result_old['congress_signal_score'],
        )

    # -- Ignores sales --

    @patch.object(CongressTradesTracker, '_fetch_all_trades')
    def test_ignores_sales(self, mock_fetch):
        mock_fetch.return_value = [
            _make_trade(ticker="META", tx_type="sale_full", days_ago_disclosure=5),
        ]
        result = self.tracker.analyze_stock("META")
        self.assertEqual(result['congress_signal_score'], 0.0)
        self.assertEqual(result['congress_trade_count'], 0)

    # -- Old trades outside lookback --

    @patch.object(CongressTradesTracker, '_fetch_all_trades')
    def test_old_trades_excluded(self, mock_fetch):
        mock_fetch.return_value = [
            _make_trade(ticker="AMZN", days_ago_disclosure=90),
        ]
        result = self.tracker.analyze_stock("AMZN")
        self.assertEqual(result['congress_signal_score'], 0.0)

    # -- Batch analysis --

    @patch.object(CongressTradesTracker, '_fetch_all_trades')
    def test_batch_analysis(self, mock_fetch):
        mock_fetch.return_value = [
            _make_trade(ticker="AAPL", days_ago_disclosure=5),
            _make_trade(ticker="MSFT", days_ago_disclosure=5),
        ]
        results = self.tracker.analyze_batch(["AAPL", "MSFT", "XYZ"])
        self.assertIn("AAPL", results)
        self.assertIn("MSFT", results)
        self.assertIn("XYZ", results)
        self.assertGreater(results["AAPL"]['congress_signal_score'], 0)
        self.assertEqual(results["XYZ"]['congress_signal_score'], 0.0)
        # Only one fetch call
        mock_fetch.assert_called_once()

    # -- API failure returns neutral with error --

    @patch.object(CongressTradesTracker, '_fetch_all_trades', side_effect=Exception("timeout"))
    def test_api_failure_returns_neutral(self, _mock):
        result = self.tracker.analyze_stock("AAPL")
        self.assertEqual(result['congress_signal_score'], 0.0)
        self.assertEqual(result['error'], "timeout")

    # -- Batch API failure --

    @patch.object(CongressTradesTracker, '_fetch_all_trades', side_effect=Exception("500"))
    def test_batch_api_failure(self, _mock):
        results = self.tracker.analyze_batch(["AAPL", "MSFT"])
        for ticker in ["AAPL", "MSFT"]:
            self.assertEqual(results[ticker]['congress_signal_score'], 0.0)
            self.assertIsNotNone(results[ticker]['error'])

    # -- Caching --

    @patch('src.signals.congress_trades.requests.get')
    def test_caching(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        self.tracker._fetch_all_trades()
        self.tracker._fetch_all_trades()

        # Should only call requests.get once due to cache
        mock_get.assert_called_once()

    # -- Case insensitive ticker --

    @patch.object(CongressTradesTracker, '_fetch_all_trades')
    def test_case_insensitive_ticker(self, mock_fetch):
        mock_fetch.return_value = [
            _make_trade(ticker="aapl", days_ago_disclosure=5),
        ]
        result = self.tracker.analyze_stock("AAPL")
        self.assertGreater(result['congress_signal_score'], 0)

    # -- Output shape --

    @patch.object(CongressTradesTracker, '_fetch_all_trades')
    def test_output_keys(self, mock_fetch):
        mock_fetch.return_value = [
            _make_trade(ticker="AAPL", days_ago_disclosure=5),
        ]
        result = self.tracker.analyze_stock("AAPL")
        expected_keys = {
            'ticker',
            'congress_signal_score',
            'congress_signal_direction',
            'congress_trades',
            'congress_trade_count',
            'congress_unique_traders',
            'congress_latest_trade_date',
            'congress_cluster_detected',
            'error',
        }
        self.assertEqual(set(result.keys()), expected_keys)

    # -- Trade detail shape --

    @patch.object(CongressTradesTracker, '_fetch_all_trades')
    def test_trade_detail_keys(self, mock_fetch):
        mock_fetch.return_value = [
            _make_trade(ticker="AAPL", days_ago_disclosure=5),
        ]
        result = self.tracker.analyze_stock("AAPL")
        trade = result['congress_trades'][0]
        for key in ['representative', 'date', 'type', 'amount_range', 'disclosure_date']:
            self.assertIn(key, trade)
        # No internal keys leaked
        for key in trade:
            self.assertFalse(key.startswith('_'), f"Internal key leaked: {key}")


if __name__ == '__main__':
    unittest.main()
