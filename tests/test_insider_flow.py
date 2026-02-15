"""
Unit tests for SEC Insider Trading Detection Signal Detector
Uses mock data — does not call real SEC API.
"""
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.signals.insider_flow import (
    InsiderFlowDetector,
    _get_role_weight,
    _get_size_weight,
    _is_planned_sale,
    _is_routine_small_sale,
    _neutral_result,
)


def _make_txn(
    owner_name='John Doe',
    owner_role='CEO',
    direction='buy',
    shares=1000,
    price=50.0,
    days_ago=5,
    transaction_code='P',
    footnotes='',
):
    """Helper to create a mock transaction dict."""
    return {
        'ticker': 'TEST',
        'owner_name': owner_name,
        'owner_role': owner_role,
        'direction': direction,
        'shares': shares,
        'price_per_share': price,
        'value': shares * price,
        'date': datetime.now() - timedelta(days=days_ago),
        'transaction_code': transaction_code,
        'footnotes': footnotes,
    }


class TestRoleWeights(unittest.TestCase):
    """Test role weight mapping."""

    def test_ceo_weight(self):
        self.assertEqual(_get_role_weight('CEO'), 1.0)
        self.assertEqual(_get_role_weight('Chief Executive Officer'), 1.0)

    def test_cfo_weight(self):
        self.assertEqual(_get_role_weight('CFO'), 0.9)

    def test_director_weight(self):
        self.assertEqual(_get_role_weight('Director'), 0.5)

    def test_ten_percent_owner(self):
        self.assertEqual(_get_role_weight('10% Owner'), 0.7)

    def test_unknown_role(self):
        self.assertEqual(_get_role_weight('Janitor'), 0.3)

    def test_none_role(self):
        self.assertEqual(_get_role_weight(None), 0.3)

    def test_case_insensitive(self):
        self.assertEqual(_get_role_weight('ceo'), 1.0)
        self.assertEqual(_get_role_weight('Vice President of Sales'), 0.6)


class TestSizeWeights(unittest.TestCase):
    """Test purchase size weight mapping."""

    def test_large_purchase(self):
        self.assertEqual(_get_size_weight(2_000_000), 1.0)

    def test_medium_purchase(self):
        self.assertEqual(_get_size_weight(600_000), 0.8)

    def test_small_purchase(self):
        self.assertEqual(_get_size_weight(75_000), 0.4)

    def test_tiny_purchase(self):
        self.assertEqual(_get_size_weight(10_000), 0.2)

    def test_zero_value(self):
        self.assertEqual(_get_size_weight(0), 0.2)

    def test_none_value(self):
        self.assertEqual(_get_size_weight(None), 0.2)


class TestFiltering(unittest.TestCase):
    """Test transaction filtering logic."""

    def test_planned_sale_10b5_1(self):
        txn = _make_txn(direction='sell', footnotes='Sold pursuant to 10b5-1 plan')
        self.assertTrue(_is_planned_sale(txn))

    def test_planned_sale_automatic(self):
        txn = _make_txn(
            direction='sell',
            transaction_code='S',
            footnotes='automatic sale per plan',
        )
        self.assertTrue(_is_planned_sale(txn))

    def test_normal_sale_not_planned(self):
        txn = _make_txn(direction='sell', footnotes='')
        self.assertFalse(_is_planned_sale(txn))

    def test_routine_small_sale(self):
        txn = _make_txn(direction='sell', shares=100, price=10.0)
        self.assertTrue(_is_routine_small_sale(txn))

    def test_large_sale_not_routine(self):
        txn = _make_txn(direction='sell', shares=10000, price=50.0)
        self.assertFalse(_is_routine_small_sale(txn))

    def test_buy_never_routine_sale(self):
        txn = _make_txn(direction='buy', shares=10, price=1.0)
        self.assertFalse(_is_routine_small_sale(txn))


class TestNeutralResult(unittest.TestCase):
    """Test neutral result structure."""

    def test_structure(self):
        result = _neutral_result()
        self.assertEqual(result['insider_signal_score'], 0.0)
        self.assertEqual(result['insider_signal_direction'], 'neutral')
        self.assertIsInstance(result['insider_transactions'], list)
        self.assertFalse(result['insider_cluster_detected'])

    def test_with_error(self):
        result = _neutral_result(error='test error')
        self.assertEqual(result['insider_error'], 'test error')


class TestClusterDetection(unittest.TestCase):
    """Test cluster buy detection."""

    def setUp(self):
        self.detector = InsiderFlowDetector()

    def test_no_cluster_single_buy(self):
        txns = [_make_txn(owner_name='Alice', days_ago=3)]
        result = self.detector._detect_clusters(txns)
        self.assertFalse(result['cluster_detected'])
        self.assertEqual(result['cluster_size'], 1)

    def test_moderate_cluster_two_buyers(self):
        txns = [
            _make_txn(owner_name='Alice', owner_role='CEO', days_ago=3),
            _make_txn(owner_name='Bob', owner_role='CFO', days_ago=5),
        ]
        result = self.detector._detect_clusters(txns)
        self.assertTrue(result['cluster_detected'])
        self.assertEqual(result['cluster_size'], 2)

    def test_strong_cluster_three_buyers(self):
        txns = [
            _make_txn(owner_name='Alice', owner_role='CEO', days_ago=1),
            _make_txn(owner_name='Bob', owner_role='CFO', days_ago=3),
            _make_txn(owner_name='Carol', owner_role='Director', days_ago=7),
        ]
        result = self.detector._detect_clusters(txns)
        self.assertTrue(result['cluster_detected'])
        self.assertEqual(result['cluster_size'], 3)

    def test_no_cluster_outside_window(self):
        txns = [
            _make_txn(owner_name='Alice', days_ago=1),
            _make_txn(owner_name='Bob', days_ago=20),
        ]
        result = self.detector._detect_clusters(txns)
        self.assertFalse(result['cluster_detected'])
        self.assertEqual(result['cluster_size'], 1)

    def test_same_insider_not_double_counted(self):
        txns = [
            _make_txn(owner_name='Alice', days_ago=1),
            _make_txn(owner_name='Alice', days_ago=3),
        ]
        result = self.detector._detect_clusters(txns)
        self.assertFalse(result['cluster_detected'])
        self.assertEqual(result['cluster_size'], 1)

    def test_sells_ignored_in_cluster(self):
        txns = [
            _make_txn(owner_name='Alice', direction='sell', days_ago=1),
            _make_txn(owner_name='Bob', direction='sell', days_ago=3),
            _make_txn(owner_name='Carol', direction='sell', days_ago=5),
        ]
        result = self.detector._detect_clusters(txns)
        self.assertFalse(result['cluster_detected'])


class TestScoring(unittest.TestCase):
    """Test insider signal scoring."""

    def setUp(self):
        self.detector = InsiderFlowDetector()

    def test_empty_transactions(self):
        score = self.detector._calculate_score([], {'cluster_size': 0})
        self.assertEqual(score, 0.0)

    def test_single_ceo_large_buy(self):
        txns = [_make_txn(owner_role='CEO', shares=20000, price=100.0)]
        cluster = {'cluster_size': 1}
        score = self.detector._calculate_score(txns, cluster)
        # CEO weight 1.0, >$1M size weight 1.0 => 10 * 1.0 * 1.0 = 10
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 100)

    def test_cluster_bonus_applied(self):
        txns = [
            _make_txn(owner_name='A', owner_role='CEO', shares=1000, price=100),
            _make_txn(owner_name='B', owner_role='CFO', shares=1000, price=100),
            _make_txn(owner_name='C', owner_role='Director', shares=1000, price=100),
        ]
        cluster_strong = {'cluster_size': 3}
        cluster_none = {'cluster_size': 1}

        score_with = self.detector._calculate_score(txns, cluster_strong)
        score_without = self.detector._calculate_score(txns, cluster_none)
        self.assertGreater(score_with, score_without)
        self.assertGreaterEqual(score_with - score_without, 25)  # At least +30 - some rounding

    def test_price_dip_bonus(self):
        txns = [_make_txn()]
        cluster = {'cluster_size': 1}
        score_dip = self.detector._calculate_score(txns, cluster, price_near_dip=True)
        score_no_dip = self.detector._calculate_score(txns, cluster, price_near_dip=False)
        self.assertEqual(score_dip - score_no_dip, PRICE_DIP_BONUS)

    def test_sells_reduce_score(self):
        buys = [_make_txn(direction='buy', shares=1000, price=100)]
        sells = [_make_txn(direction='sell', shares=1000, price=100)]
        cluster = {'cluster_size': 0}

        buy_score = self.detector._calculate_score(buys, cluster)
        mixed_score = self.detector._calculate_score(buys + sells, cluster)
        self.assertGreater(buy_score, mixed_score)

    def test_score_clamped_to_100(self):
        # Create many high-value buys to try to exceed 100
        txns = [
            _make_txn(owner_name=f'Insider{i}', owner_role='CEO', shares=100000, price=500)
            for i in range(20)
        ]
        cluster = {'cluster_size': 10}
        score = self.detector._calculate_score(txns, cluster, price_near_dip=True)
        self.assertLessEqual(score, 100.0)


# Import the constant for the dip bonus test
from src.signals.insider_flow import PRICE_DIP_BONUS


class TestDirectionSignal(unittest.TestCase):
    """Test signal direction determination."""

    def setUp(self):
        self.detector = InsiderFlowDetector()

    def test_bullish_signal(self):
        txns = [_make_txn(direction='buy', shares=10000, price=100)]
        direction = self.detector._determine_direction_signal(txns, score=50)
        self.assertEqual(direction, 'bullish')

    def test_bearish_signal(self):
        txns = [_make_txn(direction='sell', shares=50000, price=100)]
        direction = self.detector._determine_direction_signal(txns, score=5)
        self.assertEqual(direction, 'bearish')

    def test_neutral_signal(self):
        txns = [
            _make_txn(direction='buy', shares=1000, price=100),
            _make_txn(direction='sell', shares=1000, price=100),
        ]
        direction = self.detector._determine_direction_signal(txns, score=15)
        self.assertEqual(direction, 'neutral')


class TestAnalyzeStock(unittest.TestCase):
    """Test the main analyze_stock method with mocked EDGAR."""

    @patch('src.signals.insider_flow._check_edgartools_available')
    def test_edgartools_not_installed(self, mock_check):
        mock_check.return_value = (None, 'edgartools not installed')
        detector = InsiderFlowDetector()
        result = detector.analyze_stock('AAPL')
        self.assertEqual(result['insider_signal_score'], 0.0)
        self.assertEqual(result['insider_signal_direction'], 'neutral')
        self.assertIn('insider_error', result)

    @patch.object(InsiderFlowDetector, '_check_price_dip', return_value=False)
    @patch.object(InsiderFlowDetector, '_fetch_form4_filings')
    def test_no_filings_found(self, mock_fetch, mock_dip):
        mock_fetch.return_value = []
        detector = InsiderFlowDetector()
        # Need to bypass the edgartools check
        with patch('src.signals.insider_flow._check_edgartools_available') as mock_check:
            mock_check.return_value = (MagicMock(), None)
            result = detector.analyze_stock('XYZ')
        self.assertEqual(result['insider_signal_score'], 0.0)
        self.assertEqual(result['insider_signal_direction'], 'neutral')

    @patch.object(InsiderFlowDetector, '_check_price_dip', return_value=False)
    @patch.object(InsiderFlowDetector, '_fetch_form4_filings')
    def test_bullish_result(self, mock_fetch, mock_dip):
        mock_fetch.return_value = [
            _make_txn(owner_name='CEO A', owner_role='CEO', shares=50000, price=100, days_ago=2),
            _make_txn(owner_name='CFO B', owner_role='CFO', shares=20000, price=100, days_ago=4),
            _make_txn(owner_name='Dir C', owner_role='Director', shares=10000, price=100, days_ago=6),
        ]
        detector = InsiderFlowDetector()
        with patch('src.signals.insider_flow._check_edgartools_available') as mock_check:
            mock_check.return_value = (MagicMock(), None)
            result = detector.analyze_stock('BULL')

        self.assertGreater(result['insider_signal_score'], 30)
        self.assertEqual(result['insider_signal_direction'], 'bullish')
        self.assertTrue(result['insider_cluster_detected'])
        self.assertEqual(result['insider_cluster_size'], 3)
        self.assertGreater(result['insider_total_buy_value'], 0)
        self.assertEqual(result['insider_net_direction'], 'net_buying')
        self.assertGreater(len(result['insider_notable_buyers']), 0)

    @patch.object(InsiderFlowDetector, '_check_price_dip', return_value=False)
    @patch.object(InsiderFlowDetector, '_fetch_form4_filings')
    def test_bearish_result(self, mock_fetch, mock_dip):
        mock_fetch.return_value = [
            _make_txn(owner_name='CEO', owner_role='CEO', direction='sell',
                      shares=100000, price=100, days_ago=2),
        ]
        detector = InsiderFlowDetector()
        with patch('src.signals.insider_flow._check_edgartools_available') as mock_check:
            mock_check.return_value = (MagicMock(), None)
            result = detector.analyze_stock('BEAR')

        self.assertEqual(result['insider_net_direction'], 'net_selling')
        self.assertGreater(result['insider_total_sell_value'], 0)

    @patch.object(InsiderFlowDetector, '_check_price_dip', return_value=False)
    @patch.object(InsiderFlowDetector, '_fetch_form4_filings')
    def test_dates_serialized(self, mock_fetch, mock_dip):
        mock_fetch.return_value = [_make_txn(days_ago=1)]
        detector = InsiderFlowDetector()
        with patch('src.signals.insider_flow._check_edgartools_available') as mock_check:
            mock_check.return_value = (MagicMock(), None)
            result = detector.analyze_stock('SER')

        for txn in result['insider_transactions']:
            if txn.get('date'):
                self.assertIsInstance(txn['date'], str)


class TestAnalyzeBatch(unittest.TestCase):
    """Test batch analysis."""

    @patch.object(InsiderFlowDetector, 'analyze_stock')
    def test_batch_returns_all_tickers(self, mock_analyze):
        mock_analyze.return_value = _neutral_result()
        detector = InsiderFlowDetector()
        results = detector.analyze_batch(['AAPL', 'MSFT', 'GOOG'])
        self.assertEqual(len(results), 3)
        self.assertIn('AAPL', results)
        self.assertIn('MSFT', results)
        self.assertIn('GOOG', results)

    @patch.object(InsiderFlowDetector, 'analyze_stock')
    def test_batch_handles_errors(self, mock_analyze):
        mock_analyze.side_effect = [
            _neutral_result(),
            ConnectionError("timeout"),
            _neutral_result(),
        ]
        detector = InsiderFlowDetector()
        results = detector.analyze_batch(['A', 'B', 'C'])
        self.assertEqual(len(results), 3)
        self.assertIn('insider_error', results['B'])


class TestConstructor(unittest.TestCase):
    """Test constructor config handling."""

    def test_defaults(self):
        detector = InsiderFlowDetector()
        self.assertEqual(detector.lookback_days, 30)
        self.assertEqual(detector.cluster_window_days, 14)
        self.assertAlmostEqual(detector.rate_limit_delay, 0.1)

    def test_custom_config(self):
        detector = InsiderFlowDetector({
            'lookback_days': 60,
            'cluster_window_days': 21,
            'rate_limit_delay': 0.2,
        })
        self.assertEqual(detector.lookback_days, 60)
        self.assertEqual(detector.cluster_window_days, 21)
        self.assertAlmostEqual(detector.rate_limit_delay, 0.2)


class TestHelperMethods(unittest.TestCase):
    """Test internal helper methods."""

    def test_safe_float(self):
        self.assertEqual(InsiderFlowDetector._safe_float(42), 42.0)
        self.assertEqual(InsiderFlowDetector._safe_float('3.14'), 3.14)
        self.assertEqual(InsiderFlowDetector._safe_float(None), 0.0)
        self.assertEqual(InsiderFlowDetector._safe_float('not_a_number'), 0.0)

    def test_determine_direction_buy(self):
        detector = InsiderFlowDetector()
        self.assertEqual(detector._determine_direction({'code': 'P'}), 'buy')
        self.assertEqual(detector._determine_direction({'acquired_disposed': 'A'}), 'buy')

    def test_determine_direction_sell(self):
        detector = InsiderFlowDetector()
        self.assertEqual(detector._determine_direction({'code': 'S'}), 'sell')
        self.assertEqual(detector._determine_direction({'code': 'D'}), 'sell')
        self.assertEqual(detector._determine_direction({'code': 'F'}), 'sell')

    def test_determine_direction_unknown(self):
        detector = InsiderFlowDetector()
        self.assertEqual(detector._determine_direction({}), 'unknown')


def run_tests():
    """Run all insider flow tests."""
    print("\n" + "=" * 60)
    print("Running Insider Flow Detector Tests")
    print("=" * 60 + "\n")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestRoleWeights))
    suite.addTests(loader.loadTestsFromTestCase(TestSizeWeights))
    suite.addTests(loader.loadTestsFromTestCase(TestFiltering))
    suite.addTests(loader.loadTestsFromTestCase(TestNeutralResult))
    suite.addTests(loader.loadTestsFromTestCase(TestClusterDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestScoring))
    suite.addTests(loader.loadTestsFromTestCase(TestDirectionSignal))
    suite.addTests(loader.loadTestsFromTestCase(TestAnalyzeStock))
    suite.addTests(loader.loadTestsFromTestCase(TestAnalyzeBatch))
    suite.addTests(loader.loadTestsFromTestCase(TestConstructor))
    suite.addTests(loader.loadTestsFromTestCase(TestHelperMethods))

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
