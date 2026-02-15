"""
Unit tests for the Unusual Options Flow Scanner
"""
import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.signals.options_flow import OptionsFlowScanner


# ---------------------------------------------------------------------------
# Mock Tradier API responses
# ---------------------------------------------------------------------------

MOCK_EXPIRATIONS = {
    'expirations': {
        'date': ['2026-02-20', '2026-02-27', '2026-03-06', '2026-03-20', '2026-04-17']
    }
}

MOCK_CHAIN_BULLISH = {
    'options': {
        'option': [
            # Very unusual call: volume 600, OI 100 => ratio 6.0
            {
                'option_type': 'call', 'strike': 150.0, 'volume': 600,
                'open_interest': 100, 'last': 5.0,
            },
            # Unusual call: volume 400, OI 100 => ratio 4.0
            {
                'option_type': 'call', 'strike': 155.0, 'volume': 400,
                'open_interest': 100, 'last': 3.0,
            },
            # Unusual call: ratio 3.5
            {
                'option_type': 'call', 'strike': 160.0, 'volume': 350,
                'open_interest': 100, 'last': 2.0,
            },
            # Normal put
            {
                'option_type': 'put', 'strike': 145.0, 'volume': 50,
                'open_interest': 200, 'last': 1.5,
            },
        ]
    }
}

MOCK_CHAIN_BEARISH = {
    'options': {
        'option': [
            # Very unusual put
            {
                'option_type': 'put', 'strike': 140.0, 'volume': 800,
                'open_interest': 100, 'last': 4.0,
            },
            # Unusual put
            {
                'option_type': 'put', 'strike': 135.0, 'volume': 500,
                'open_interest': 100, 'last': 3.0,
            },
            # Unusual put
            {
                'option_type': 'put', 'strike': 130.0, 'volume': 400,
                'open_interest': 100, 'last': 2.5,
            },
            # Normal call
            {
                'option_type': 'call', 'strike': 155.0, 'volume': 30,
                'open_interest': 500, 'last': 2.0,
            },
        ]
    }
}

MOCK_CHAIN_NEUTRAL = {
    'options': {
        'option': [
            {
                'option_type': 'call', 'strike': 150.0, 'volume': 100,
                'open_interest': 500, 'last': 3.0,
            },
            {
                'option_type': 'put', 'strike': 145.0, 'volume': 100,
                'open_interest': 500, 'last': 2.0,
            },
        ]
    }
}

MOCK_CHAIN_EMPTY = {'options': None}


def _make_response(json_data, status=200):
    """Build a mock requests.Response."""
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    if status >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status}")
    return resp


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestOptionsFlowNeutralFallback(unittest.TestCase):
    """Scanner returns neutral when API key is missing or API fails."""

    def test_no_api_key_returns_neutral(self):
        scanner = OptionsFlowScanner({'tradier_api_key': ''})
        result = scanner.analyze_stock('AAPL')

        self.assertEqual(result['options_signal_direction'], 'neutral')
        self.assertEqual(result['options_signal_score'], 40.0)
        self.assertFalse(result['options_unusual_activity'])

    @patch('src.signals.options_flow.requests')
    def test_api_error_returns_neutral(self, mock_requests):
        mock_requests.get.side_effect = Exception("connection error")
        scanner = OptionsFlowScanner({'tradier_api_key': 'test_key'})
        result = scanner.analyze_stock('AAPL')

        self.assertEqual(result['options_signal_direction'], 'neutral')

    @patch('src.signals.options_flow.requests')
    def test_no_expirations_returns_neutral(self, mock_requests):
        mock_requests.get.return_value = _make_response({'expirations': None})
        scanner = OptionsFlowScanner({'tradier_api_key': 'test_key'})
        result = scanner.analyze_stock('AAPL')

        self.assertEqual(result['options_signal_direction'], 'neutral')


class TestOptionsFlowBullish(unittest.TestCase):
    """Scanner correctly detects bullish flow."""

    @patch('src.signals.options_flow.requests')
    def test_bullish_detection(self, mock_requests):
        def side_effect(url, **kwargs):
            if 'expirations' in url:
                return _make_response(MOCK_EXPIRATIONS)
            return _make_response(MOCK_CHAIN_BULLISH)

        mock_requests.get.side_effect = side_effect
        mock_requests.RequestException = Exception

        scanner = OptionsFlowScanner({'tradier_api_key': 'test_key', 'rate_limit_delay': 0})
        result = scanner.analyze_stock('AAPL')

        self.assertEqual(result['options_signal_direction'], 'bullish')
        self.assertTrue(result['options_unusual_activity'])
        self.assertGreater(result['options_signal_score'], 50)
        self.assertGreater(result['options_total_call_volume'], result['options_total_put_volume'])
        self.assertGreater(result['options_max_volume_oi_ratio'], UNUSUAL_THRESHOLD)
        self.assertGreater(len(result['options_notable_trades']), 0)

    @patch('src.signals.options_flow.requests')
    def test_bullish_sweep_detected(self, mock_requests):
        """3+ unusual strikes on calls in same expiry = call sweep."""
        def side_effect(url, **kwargs):
            if 'expirations' in url:
                return _make_response({'expirations': {'date': ['2026-02-20']}})
            return _make_response(MOCK_CHAIN_BULLISH)

        mock_requests.get.side_effect = side_effect
        mock_requests.RequestException = Exception

        scanner = OptionsFlowScanner({'tradier_api_key': 'test_key', 'rate_limit_delay': 0})
        result = scanner.analyze_stock('AAPL')

        # Sweep should boost score
        self.assertEqual(result['options_signal_direction'], 'bullish')
        self.assertGreaterEqual(result['options_signal_score'], 60)


class TestOptionsFlowBearish(unittest.TestCase):
    """Scanner correctly detects bearish flow."""

    @patch('src.signals.options_flow.requests')
    def test_bearish_detection(self, mock_requests):
        def side_effect(url, **kwargs):
            if 'expirations' in url:
                return _make_response(MOCK_EXPIRATIONS)
            return _make_response(MOCK_CHAIN_BEARISH)

        mock_requests.get.side_effect = side_effect
        mock_requests.RequestException = Exception

        scanner = OptionsFlowScanner({'tradier_api_key': 'test_key', 'rate_limit_delay': 0})
        result = scanner.analyze_stock('AAPL')

        self.assertEqual(result['options_signal_direction'], 'bearish')
        self.assertTrue(result['options_unusual_activity'])
        self.assertLess(result['options_signal_score'], 50)
        self.assertGreater(result['options_put_call_ratio'], 1.0)


class TestOptionsFlowNeutral(unittest.TestCase):
    """Scanner returns neutral when activity is balanced."""

    @patch('src.signals.options_flow.requests')
    def test_neutral_detection(self, mock_requests):
        def side_effect(url, **kwargs):
            if 'expirations' in url:
                return _make_response(MOCK_EXPIRATIONS)
            return _make_response(MOCK_CHAIN_NEUTRAL)

        mock_requests.get.side_effect = side_effect
        mock_requests.RequestException = Exception

        scanner = OptionsFlowScanner({'tradier_api_key': 'test_key', 'rate_limit_delay': 0})
        result = scanner.analyze_stock('AAPL')

        self.assertEqual(result['options_signal_direction'], 'neutral')
        self.assertFalse(result['options_unusual_activity'])


class TestOptionsFlowEmptyChain(unittest.TestCase):
    """Scanner handles stocks with no options gracefully."""

    @patch('src.signals.options_flow.requests')
    def test_empty_chain(self, mock_requests):
        def side_effect(url, **kwargs):
            if 'expirations' in url:
                return _make_response(MOCK_EXPIRATIONS)
            return _make_response(MOCK_CHAIN_EMPTY)

        mock_requests.get.side_effect = side_effect
        mock_requests.RequestException = Exception

        scanner = OptionsFlowScanner({'tradier_api_key': 'test_key', 'rate_limit_delay': 0})
        result = scanner.analyze_stock('AAPL')

        self.assertEqual(result['options_signal_direction'], 'neutral')


class TestOptionsFlowScoring(unittest.TestCase):
    """Score boundary and premium bonus tests."""

    def test_neutral_result_shape(self):
        result = OptionsFlowScanner._neutral_result()
        expected_keys = {
            'options_signal_score', 'options_signal_direction',
            'options_put_call_ratio', 'options_unusual_activity',
            'options_total_call_volume', 'options_total_put_volume',
            'options_max_volume_oi_ratio', 'options_notable_trades',
            'options_estimated_premium',
        }
        self.assertEqual(set(result.keys()), expected_keys)

    def test_score_bounds(self):
        """Score must always be 0-100."""
        scanner = OptionsFlowScanner({'tradier_api_key': 'x'})
        # Extreme bullish
        score = scanner._calculate_score(
            direction='bullish', max_ratio=20.0,
            unusual_contracts=[{'very_unusual': True}] * 10,
            estimated_premium=10_000_000, near_term=True,
            call_sweep=True, put_sweep=False,
        )
        self.assertLessEqual(score, 100.0)
        self.assertGreaterEqual(score, 0.0)

        # Extreme bearish
        score = scanner._calculate_score(
            direction='bearish', max_ratio=20.0,
            unusual_contracts=[{'very_unusual': True}] * 10,
            estimated_premium=10_000_000, near_term=True,
            call_sweep=False, put_sweep=True,
        )
        self.assertLessEqual(score, 100.0)
        self.assertGreaterEqual(score, 0.0)

    def test_premium_bonus(self):
        scanner = OptionsFlowScanner({'tradier_api_key': 'x'})
        low = scanner._calculate_score(
            direction='bullish', max_ratio=4.0,
            unusual_contracts=[], estimated_premium=500_000,
            near_term=False, call_sweep=False, put_sweep=False,
        )
        high = scanner._calculate_score(
            direction='bullish', max_ratio=4.0,
            unusual_contracts=[], estimated_premium=6_000_000,
            near_term=False, call_sweep=False, put_sweep=False,
        )
        self.assertGreater(high, low)

    def test_near_term_bonus(self):
        scanner = OptionsFlowScanner({'tradier_api_key': 'x'})
        without = scanner._calculate_score(
            direction='bullish', max_ratio=4.0,
            unusual_contracts=[], estimated_premium=0,
            near_term=False, call_sweep=False, put_sweep=False,
        )
        with_near = scanner._calculate_score(
            direction='bullish', max_ratio=4.0,
            unusual_contracts=[], estimated_premium=0,
            near_term=True, call_sweep=False, put_sweep=False,
        )
        self.assertGreater(with_near, without)


class TestOptionsFlowBatch(unittest.TestCase):
    """Batch analysis test."""

    @patch('src.signals.options_flow.requests')
    def test_batch_returns_all_tickers(self, mock_requests):
        def side_effect(url, **kwargs):
            if 'expirations' in url:
                return _make_response(MOCK_EXPIRATIONS)
            return _make_response(MOCK_CHAIN_NEUTRAL)

        mock_requests.get.side_effect = side_effect
        mock_requests.RequestException = Exception

        scanner = OptionsFlowScanner({'tradier_api_key': 'test_key', 'rate_limit_delay': 0})
        results = scanner.analyze_batch(['AAPL', 'MSFT', 'GOOG'])

        self.assertEqual(set(results.keys()), {'AAPL', 'MSFT', 'GOOG'})
        for ticker, result in results.items():
            self.assertIn('options_signal_score', result)


# Constant used in assertions
UNUSUAL_THRESHOLD = 3.0


if __name__ == '__main__':
    unittest.main()
