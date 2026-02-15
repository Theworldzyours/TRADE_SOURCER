"""
Unit tests for Dark Pool & Short Sale Volume Analyzer
"""
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import tempfile
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.signals.dark_pool import (
    DarkPoolAnalyzer,
    DIRECTION_ACCUMULATION,
    DIRECTION_DISTRIBUTION,
    DIRECTION_NEUTRAL,
    TREND_DECLINING,
    TREND_RISING,
    TREND_STABLE,
)


def _make_finra_text(date_str: str, rows: list) -> str:
    """
    Build a fake FINRA pipe-delimited file.

    rows: list of (Symbol, ShortVolume, ShortExemptVolume, TotalVolume, Market)
    """
    header = 'Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market'
    lines = [header]
    for symbol, sv, sev, tv, mkt in rows:
        lines.append(f'{date_str}|{symbol}|{sv}|{sev}|{tv}|{mkt}')
    return '\n'.join(lines)


def _build_multi_day_data(
    ticker: str,
    n_days: int = 20,
    base_short: int = 500000,
    base_total: int = 1000000,
    short_trend: str = 'flat',
):
    """
    Build a dict mapping date_str -> finra text for *n_days*.
    short_trend: 'flat', 'declining', 'rising'
    """
    data = {}
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    day = today - timedelta(days=1)
    count = 0
    while count < n_days:
        if day.weekday() < 5:
            date_str = day.strftime('%Y%m%d')
            if short_trend == 'declining':
                sv = base_short - count * 15000
            elif short_trend == 'rising':
                sv = base_short + count * 15000
            else:
                sv = base_short + int(np.random.normal(0, 5000))
            sv = max(sv, 10000)
            data[date_str] = _make_finra_text(date_str, [
                (ticker, sv, 1000, base_total, 'Q'),
                ('OTHER', 300000, 500, 600000, 'Q'),
            ])
            count += 1
        day -= timedelta(days=1)
    return data


class TestDarkPoolAnalyzerParsing(unittest.TestCase):
    """Test FINRA file parsing."""

    def test_parse_valid_file(self):
        text = _make_finra_text('20250210', [
            ('AAPL', 500000, 1000, 1000000, 'Q'),
            ('TSLA', 300000, 500, 700000, 'N'),
        ])
        df = DarkPoolAnalyzer._parse_finra_file(text)
        self.assertIsNotNone(df)
        self.assertEqual(len(df), 2)
        self.assertIn('AAPL', df['Symbol'].values)
        self.assertIn('TSLA', df['Symbol'].values)

    def test_parse_missing_columns(self):
        text = 'Foo|Bar\n1|2'
        df = DarkPoolAnalyzer._parse_finra_file(text)
        self.assertIsNone(df)

    def test_parse_empty_string(self):
        df = DarkPoolAnalyzer._parse_finra_file('')
        self.assertIsNone(df)


class TestTradingDays(unittest.TestCase):
    """Test trading day generation."""

    def test_returns_correct_count(self):
        analyzer = DarkPoolAnalyzer({'cache_dir': tempfile.mkdtemp()})
        days = analyzer._get_trading_days(10)
        self.assertEqual(len(days), 10)

    def test_no_weekends(self):
        analyzer = DarkPoolAnalyzer({'cache_dir': tempfile.mkdtemp()})
        days = analyzer._get_trading_days(20)
        for d in days:
            self.assertLess(d.weekday(), 5, f"{d} is a weekend")

    def test_oldest_first(self):
        analyzer = DarkPoolAnalyzer({'cache_dir': tempfile.mkdtemp()})
        days = analyzer._get_trading_days(5)
        for i in range(1, len(days)):
            self.assertGreater(days[i], days[i - 1])

    def test_is_trading_day_weekend(self):
        # Find next Saturday
        sat = datetime(2025, 2, 15)  # Saturday
        self.assertFalse(DarkPoolAnalyzer._is_trading_day(sat))

    def test_is_trading_day_holiday(self):
        mlk = datetime(2025, 1, 20)
        self.assertFalse(DarkPoolAnalyzer._is_trading_day(mlk))

    def test_is_trading_day_normal(self):
        tue = datetime(2025, 2, 11)  # Tuesday, not a holiday
        self.assertTrue(DarkPoolAnalyzer._is_trading_day(tue))


class TestConsecutiveTrend(unittest.TestCase):
    """Test the consecutive trend counter."""

    def test_declining_series(self):
        s = pd.Series([0.5, 0.48, 0.45, 0.42, 0.40, 0.38])
        decline, rise = DarkPoolAnalyzer._consecutive_trend(s)
        self.assertEqual(decline, 5)
        self.assertEqual(rise, 0)

    def test_rising_series(self):
        s = pd.Series([0.3, 0.32, 0.35, 0.38])
        decline, rise = DarkPoolAnalyzer._consecutive_trend(s)
        self.assertEqual(decline, 0)
        self.assertEqual(rise, 3)

    def test_mixed_series(self):
        s = pd.Series([0.5, 0.48, 0.50, 0.47, 0.45])
        decline, rise = DarkPoolAnalyzer._consecutive_trend(s)
        self.assertEqual(decline, 2)  # last two are declining
        self.assertEqual(rise, 0)

    def test_short_series(self):
        s = pd.Series([0.5])
        decline, rise = DarkPoolAnalyzer._consecutive_trend(s)
        self.assertEqual(decline, 0)
        self.assertEqual(rise, 0)

    def test_flat_series(self):
        s = pd.Series([0.5, 0.5, 0.5])
        decline, rise = DarkPoolAnalyzer._consecutive_trend(s)
        self.assertEqual(decline, 0)
        self.assertEqual(rise, 0)


class TestNeutralResult(unittest.TestCase):
    """Test the neutral fallback result."""

    def test_structure(self):
        result = DarkPoolAnalyzer._neutral_result('AAPL')
        self.assertEqual(result['ticker'], 'AAPL')
        self.assertEqual(result['darkpool_signal_score'], 30.0)
        self.assertEqual(result['darkpool_signal_direction'], DIRECTION_NEUTRAL)
        self.assertFalse(result['darkpool_anomaly_detected'])
        self.assertNotIn('error', result)

    def test_with_error(self):
        result = DarkPoolAnalyzer._neutral_result('AAPL', error='network_error')
        self.assertEqual(result['error'], 'network_error')


class TestScoreSignals(unittest.TestCase):
    """Test signal scoring with synthetic data."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.analyzer = DarkPoolAnalyzer({'cache_dir': self.tmp_dir})

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _make_data(self, ratios, volumes=None):
        n = len(ratios)
        if volumes is None:
            volumes = [1000000] * n
        dates = [f'2025020{i+1}' if i < 9 else f'202502{i+1}' for i in range(n)]
        short_vols = [int(r * v) for r, v in zip(ratios, volumes)]
        return pd.DataFrame({
            'Date': dates,
            'ShortVolume': short_vols,
            'TotalVolume': volumes,
            'ShortExemptVolume': [0] * n,
            'short_volume_ratio': ratios,
        })

    def test_accumulation_signal(self):
        """Declining short ratio should produce accumulation score."""
        ratios = [0.55, 0.54, 0.53, 0.52, 0.50, 0.48, 0.45, 0.42, 0.40, 0.38]
        data = self._make_data(ratios)
        result = self.analyzer._score_signals('TEST', data)
        self.assertGreater(result['darkpool_signal_score'], 50)
        self.assertEqual(result['darkpool_trend'], TREND_DECLINING)

    def test_distribution_signal(self):
        """Rising short ratio should produce distribution score."""
        ratios = [0.35, 0.37, 0.40, 0.43, 0.47, 0.50, 0.54, 0.58, 0.62, 0.66]
        data = self._make_data(ratios)
        result = self.analyzer._score_signals('TEST', data)
        self.assertLess(result['darkpool_signal_score'], 30)
        self.assertEqual(result['darkpool_trend'], TREND_RISING)

    def test_neutral_signal(self):
        """Flat short ratio should stay near neutral."""
        np.random.seed(42)
        ratios = [0.45 + np.random.normal(0, 0.005) for _ in range(20)]
        data = self._make_data(ratios)
        result = self.analyzer._score_signals('TEST', data)
        self.assertGreaterEqual(result['darkpool_signal_score'], 15)
        self.assertLessEqual(result['darkpool_signal_score'], 55)

    def test_volume_surge_anomaly(self):
        """Volume surge should trigger anomaly flag."""
        ratios = [0.45] * 19 + [0.30]
        volumes = [1000000] * 19 + [3000000]
        data = self._make_data(ratios, volumes)
        result = self.analyzer._score_signals('TEST', data)
        self.assertTrue(result['darkpool_anomaly_detected'])
        self.assertGreater(result['darkpool_volume_vs_avg'], 2.0)

    def test_sustained_decline_bonus(self):
        """5+ consecutive declining days should boost score."""
        ratios = [0.50, 0.50, 0.50, 0.50, 0.50,
                  0.49, 0.48, 0.47, 0.46, 0.45,
                  0.44, 0.43, 0.42, 0.41, 0.40]
        data = self._make_data(ratios)
        result = self.analyzer._score_signals('TEST', data)
        self.assertGreaterEqual(result['darkpool_consecutive_decline_days'], 5)
        self.assertTrue(result['darkpool_anomaly_detected'])

    def test_result_keys(self):
        """Verify all expected keys are present."""
        ratios = [0.45] * 10
        data = self._make_data(ratios)
        result = self.analyzer._score_signals('TEST', data)
        expected_keys = {
            'ticker', 'darkpool_signal_score', 'darkpool_signal_direction',
            'darkpool_short_ratio_current', 'darkpool_short_ratio_avg',
            'darkpool_short_ratio_deviation', 'darkpool_volume_vs_avg',
            'darkpool_trend', 'darkpool_consecutive_decline_days',
            'darkpool_anomaly_detected',
        }
        self.assertEqual(set(result.keys()), expected_keys)

    def test_score_bounds(self):
        """Score should always be in [0, 100]."""
        # Extreme accumulation
        ratios = [0.60, 0.55, 0.50, 0.40, 0.30, 0.20, 0.15, 0.10, 0.08, 0.05]
        data = self._make_data(ratios, [1000000] * 9 + [5000000])
        result = self.analyzer._score_signals('TEST', data)
        self.assertGreaterEqual(result['darkpool_signal_score'], 0)
        self.assertLessEqual(result['darkpool_signal_score'], 100)

        # Extreme distribution
        ratios = [0.20, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.80, 0.85, 0.90]
        data = self._make_data(ratios, [1000000] * 9 + [5000000])
        result = self.analyzer._score_signals('TEST', data)
        self.assertGreaterEqual(result['darkpool_signal_score'], 0)
        self.assertLessEqual(result['darkpool_signal_score'], 100)


class TestAnalyzeStock(unittest.TestCase):
    """Integration-level tests using mocked HTTP."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.analyzer = DarkPoolAnalyzer({
            'cache_dir': self.tmp_dir,
            'lookback_days': 10,
        })
        self.mock_data = _build_multi_day_data('AAPL', n_days=10)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    @patch('src.signals.dark_pool.requests.get')
    def test_analyze_stock_success(self, mock_get):
        """Full analyze_stock path with mocked HTTP."""
        def side_effect(url, timeout=None):
            # Extract date from URL
            date_str = url.split('shvol')[-1].replace('.txt', '')
            resp = MagicMock()
            if date_str in self.mock_data:
                resp.status_code = 200
                resp.text = self.mock_data[date_str]
                resp.raise_for_status = MagicMock()
            else:
                resp.status_code = 404
            return resp

        mock_get.side_effect = side_effect
        result = self.analyzer.analyze_stock('AAPL')

        self.assertEqual(result['ticker'], 'AAPL')
        self.assertIn('darkpool_signal_score', result)
        self.assertGreaterEqual(result['darkpool_signal_score'], 0)
        self.assertLessEqual(result['darkpool_signal_score'], 100)
        self.assertNotIn('error', result)

    @patch('src.signals.dark_pool.requests.get')
    def test_analyze_stock_ticker_not_found(self, mock_get):
        """Ticker not in FINRA data should return neutral."""
        def side_effect(url, timeout=None):
            date_str = url.split('shvol')[-1].replace('.txt', '')
            resp = MagicMock()
            if date_str in self.mock_data:
                resp.status_code = 200
                resp.text = self.mock_data[date_str]
                resp.raise_for_status = MagicMock()
            else:
                resp.status_code = 404
            return resp

        mock_get.side_effect = side_effect
        result = self.analyzer.analyze_stock('ZZZZZ')

        self.assertEqual(result['darkpool_signal_direction'], DIRECTION_NEUTRAL)
        self.assertEqual(result['error'], 'insufficient_data')

    @patch('src.signals.dark_pool.requests.get')
    def test_analyze_stock_network_error(self, mock_get):
        """Network failure should return neutral with error."""
        import requests as req
        mock_get.side_effect = req.ConnectionError("cdn down")
        result = self.analyzer.analyze_stock('AAPL')

        self.assertEqual(result['darkpool_signal_direction'], DIRECTION_NEUTRAL)
        self.assertIn('error', result)

    @patch('src.signals.dark_pool.requests.get')
    def test_disk_cache_used(self, mock_get):
        """Second call should use disk cache, not HTTP."""
        date_str = list(self.mock_data.keys())[0]
        resp = MagicMock()
        resp.status_code = 200
        resp.text = self.mock_data[date_str]
        resp.raise_for_status = MagicMock()
        mock_get.return_value = resp

        day = datetime.strptime(date_str, '%Y%m%d')
        # First fetch — hits network
        self.analyzer._fetch_finra_data(day)
        call_count_1 = mock_get.call_count

        # Clear in-memory cache to force disk read
        self.analyzer._daily_frames.clear()

        # Second fetch — should use disk cache
        self.analyzer._fetch_finra_data(day)
        self.assertEqual(mock_get.call_count, call_count_1)


class TestAnalyzeBatch(unittest.TestCase):
    """Test batch analysis."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.analyzer = DarkPoolAnalyzer({
            'cache_dir': self.tmp_dir,
            'lookback_days': 5,
            'batch_delay': 0,  # no delay in tests
        })

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    @patch('src.signals.dark_pool.requests.get')
    def test_batch_returns_all_tickers(self, mock_get):
        mock_data = _build_multi_day_data('AAPL', n_days=5)
        # Add MSFT rows to each day
        for date_str, text in list(mock_data.items()):
            mock_data[date_str] = text + f'\n{date_str}|MSFT|400000|800|900000|Q'

        def side_effect(url, timeout=None):
            date_str = url.split('shvol')[-1].replace('.txt', '')
            resp = MagicMock()
            if date_str in mock_data:
                resp.status_code = 200
                resp.text = mock_data[date_str]
                resp.raise_for_status = MagicMock()
            else:
                resp.status_code = 404
            return resp

        mock_get.side_effect = side_effect
        results = self.analyzer.analyze_batch(['AAPL', 'MSFT'])

        self.assertIn('AAPL', results)
        self.assertIn('MSFT', results)
        self.assertEqual(results['AAPL']['ticker'], 'AAPL')
        self.assertEqual(results['MSFT']['ticker'], 'MSFT')


def run_tests():
    """Run all dark pool tests."""
    print("\n" + "=" * 60)
    print("Running Dark Pool Analyzer Unit Tests")
    print("=" * 60 + "\n")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestDarkPoolAnalyzerParsing))
    suite.addTests(loader.loadTestsFromTestCase(TestTradingDays))
    suite.addTests(loader.loadTestsFromTestCase(TestConsecutiveTrend))
    suite.addTests(loader.loadTestsFromTestCase(TestNeutralResult))
    suite.addTests(loader.loadTestsFromTestCase(TestScoreSignals))
    suite.addTests(loader.loadTestsFromTestCase(TestAnalyzeStock))
    suite.addTests(loader.loadTestsFromTestCase(TestAnalyzeBatch))

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


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
