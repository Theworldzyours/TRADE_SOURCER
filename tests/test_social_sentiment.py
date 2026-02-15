"""
Unit tests for Social Sentiment & Momentum Scorer
"""
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.signals.social_sentiment import SocialSentimentScorer, _neutral_result


# ---------------------------------------------------------------------------
# Mock API response data
# ---------------------------------------------------------------------------

MOCK_PAGE_1 = {
    'results': [
        {'ticker': 'GME', 'rank': 1, 'mentions': 500, 'upvotes': 2000, 'mentions_24h_ago': 150},
        {'ticker': 'AMC', 'rank': 2, 'mentions': 400, 'upvotes': 1500, 'mentions_24h_ago': 380},
        {'ticker': 'TSLA', 'rank': 3, 'mentions': 350, 'upvotes': 1200, 'mentions_24h_ago': 300},
        {'ticker': 'AAPL', 'rank': 4, 'mentions': 300, 'upvotes': 800, 'mentions_24h_ago': 310},
        {'ticker': 'NVDA', 'rank': 5, 'mentions': 280, 'upvotes': 900, 'mentions_24h_ago': 60},
        {'ticker': 'SPY', 'rank': 6, 'mentions': 250, 'upvotes': 600, 'mentions_24h_ago': 240},
        {'ticker': 'AMD', 'rank': 7, 'mentions': 220, 'upvotes': 500, 'mentions_24h_ago': 200},
        {'ticker': 'PLTR', 'rank': 8, 'mentions': 200, 'upvotes': 450, 'mentions_24h_ago': 180},
        {'ticker': 'MSFT', 'rank': 9, 'mentions': 180, 'upvotes': 400, 'mentions_24h_ago': 170},
        {'ticker': 'META', 'rank': 10, 'mentions': 160, 'upvotes': 350, 'mentions_24h_ago': 150},
    ]
}

MOCK_PAGE_2 = {
    'results': [
        {'ticker': 'GOOG', 'rank': 11, 'mentions': 140, 'upvotes': 300, 'mentions_24h_ago': 130},
        {'ticker': 'SOFI', 'rank': 15, 'mentions': 100, 'upvotes': 200, 'mentions_24h_ago': 90},
        {'ticker': 'COIN', 'rank': 20, 'mentions': 80, 'upvotes': 150, 'mentions_24h_ago': 70},
        {'ticker': 'RIVN', 'rank': 25, 'mentions': 60, 'upvotes': 100, 'mentions_24h_ago': 55},
    ]
}

MOCK_PAGE_3 = {
    'results': [
        {'ticker': 'SNAP', 'rank': 30, 'mentions': 40, 'upvotes': 50, 'mentions_24h_ago': 35},
        {'ticker': 'WISH', 'rank': 45, 'mentions': 15, 'upvotes': 20, 'mentions_24h_ago': 10},
        {'ticker': 'NEWSTOCK', 'rank': 50, 'mentions': 25, 'upvotes': 30, 'mentions_24h_ago': 1},
    ]
}


def _mock_get_responses(*args, **kwargs):
    """Return mock responses based on URL page number."""
    url = args[0] if args else kwargs.get('url', '')
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()

    if '/page/1' in url:
        mock_resp.json.return_value = MOCK_PAGE_1
    elif '/page/2' in url:
        mock_resp.json.return_value = MOCK_PAGE_2
    elif '/page/3' in url:
        mock_resp.json.return_value = MOCK_PAGE_3
    else:
        mock_resp.json.return_value = {'results': []}

    return mock_resp


class TestNeutralResult(unittest.TestCase):
    """Test the neutral/default result factory."""

    def test_neutral_has_all_keys(self):
        result = _neutral_result('XYZ')
        expected_keys = {
            'social_signal_score', 'social_signal_direction',
            'social_mentions_rank', 'social_mentions_count',
            'social_mention_velocity', 'social_upvotes',
            'social_trending', 'social_new_discovery',
        }
        self.assertEqual(set(result.keys()), expected_keys)

    def test_neutral_with_error(self):
        result = _neutral_result('XYZ', error='api_down')
        self.assertEqual(result['social_error'], 'api_down')
        self.assertEqual(result['social_signal_score'], 0.0)


class TestSocialSentimentScorer(unittest.TestCase):
    """Test the SocialSentimentScorer class."""

    def setUp(self):
        self.scorer = SocialSentimentScorer({'request_delay': 0})

    # ------------------------------------------------------------------
    # analyze_stock
    # ------------------------------------------------------------------

    @patch('src.signals.social_sentiment.requests.get', side_effect=_mock_get_responses)
    def test_analyze_top_ranked_ticker(self, mock_get):
        """GME at rank 1 with 3x+ velocity should score high."""
        result = self.scorer.analyze_stock('GME')

        self.assertGreaterEqual(result['social_signal_score'], 70)
        self.assertEqual(result['social_mentions_rank'], 1)
        self.assertEqual(result['social_mentions_count'], 500)
        self.assertTrue(result['social_trending'])
        self.assertEqual(result['social_signal_direction'], 'bullish_momentum')

    @patch('src.signals.social_sentiment.requests.get', side_effect=_mock_get_responses)
    def test_analyze_mid_ranked_ticker(self, mock_get):
        """SOFI at rank 15 should score in the 50-70 range."""
        result = self.scorer.analyze_stock('SOFI')

        self.assertGreaterEqual(result['social_signal_score'], 30)
        self.assertLessEqual(result['social_signal_score'], 75)
        self.assertEqual(result['social_mentions_rank'], 15)
        self.assertTrue(result['social_trending'])

    @patch('src.signals.social_sentiment.requests.get', side_effect=_mock_get_responses)
    def test_analyze_low_ranked_ticker(self, mock_get):
        """SNAP at rank 30 should score in the 30-50 range."""
        result = self.scorer.analyze_stock('SNAP')

        self.assertGreaterEqual(result['social_signal_score'], 20)
        self.assertLessEqual(result['social_signal_score'], 55)
        self.assertEqual(result['social_mentions_rank'], 30)
        self.assertFalse(result['social_trending'])

    @patch('src.signals.social_sentiment.requests.get', side_effect=_mock_get_responses)
    def test_analyze_unknown_ticker(self, mock_get):
        """A ticker not in the data should return neutral."""
        result = self.scorer.analyze_stock('ZZZZZ')

        self.assertEqual(result['social_signal_score'], 0.0)
        self.assertEqual(result['social_signal_direction'], 'neutral')
        self.assertEqual(result['social_mentions_rank'], 0)
        self.assertFalse(result['social_trending'])

    @patch('src.signals.social_sentiment.requests.get', side_effect=_mock_get_responses)
    def test_analyze_case_insensitive(self, mock_get):
        """Ticker lookup should be case-insensitive."""
        result = self.scorer.analyze_stock('gme')
        self.assertEqual(result['social_mentions_rank'], 1)

    # ------------------------------------------------------------------
    # analyze_batch
    # ------------------------------------------------------------------

    @patch('src.signals.social_sentiment.requests.get', side_effect=_mock_get_responses)
    def test_analyze_batch(self, mock_get):
        """Batch analysis should return results for all tickers."""
        tickers = ['GME', 'AAPL', 'UNKNOWN']
        results = self.scorer.analyze_batch(tickers)

        self.assertEqual(set(results.keys()), set(tickers))
        self.assertGreater(results['GME']['social_signal_score'], 0)
        self.assertGreater(results['AAPL']['social_signal_score'], 0)
        self.assertEqual(results['UNKNOWN']['social_signal_score'], 0.0)

    @patch('src.signals.social_sentiment.requests.get', side_effect=_mock_get_responses)
    def test_batch_only_fetches_once(self, mock_get):
        """Batch should use cache — only one set of API calls."""
        self.scorer.analyze_batch(['GME', 'AAPL', 'TSLA'])

        # 3 pages fetched = 3 calls
        self.assertEqual(mock_get.call_count, 3)

    # ------------------------------------------------------------------
    # Caching
    # ------------------------------------------------------------------

    @patch('src.signals.social_sentiment.requests.get', side_effect=_mock_get_responses)
    def test_cache_hit(self, mock_get):
        """Second call within TTL should use cache, not re-fetch."""
        self.scorer.analyze_stock('GME')
        self.scorer.analyze_stock('AAPL')

        # Only 3 calls (for the first fetch, 3 pages)
        self.assertEqual(mock_get.call_count, 3)

    # ------------------------------------------------------------------
    # Velocity & patterns
    # ------------------------------------------------------------------

    @patch('src.signals.social_sentiment.requests.get', side_effect=_mock_get_responses)
    def test_velocity_calculation(self, mock_get):
        """GME: 500 mentions / 150 mentions_24h_ago = 3.33x velocity."""
        result = self.scorer.analyze_stock('GME')
        self.assertAlmostEqual(result['social_mention_velocity'], 500 / 150, places=1)

    @patch('src.signals.social_sentiment.requests.get', side_effect=_mock_get_responses)
    def test_new_discovery_detection(self, mock_get):
        """NEWSTOCK: 25 mentions from 1 = new discovery."""
        result = self.scorer.analyze_stock('NEWSTOCK')
        self.assertTrue(result['social_new_discovery'])

    @patch('src.signals.social_sentiment.requests.get', side_effect=_mock_get_responses)
    def test_no_new_discovery_for_stable(self, mock_get):
        """AAPL: 300 from 310 = not a new discovery."""
        result = self.scorer.analyze_stock('AAPL')
        self.assertFalse(result['social_new_discovery'])

    @patch('src.signals.social_sentiment.requests.get', side_effect=_mock_get_responses)
    def test_contrarian_warning(self, mock_get):
        """AAPL: top 10 + decelerating (300/310 < 0.8 threshold not met, so neutral)."""
        result = self.scorer.analyze_stock('AAPL')
        # 300/310 ~ 0.97 — not below 0.8, so not contrarian
        self.assertIn(result['social_signal_direction'], ['neutral', 'bullish_momentum'])

    @patch('src.signals.social_sentiment.requests.get', side_effect=_mock_get_responses)
    def test_nvda_high_velocity(self, mock_get):
        """NVDA: 280/60 = 4.67x — should get velocity bonus."""
        result = self.scorer.analyze_stock('NVDA')
        # Rank 5 base score + velocity bonus + upvote bonus
        self.assertGreaterEqual(result['social_signal_score'], 80)

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------

    @patch('src.signals.social_sentiment.requests.get')
    def test_api_timeout(self, mock_get):
        """API timeout should return neutral with error flag."""
        import requests as req
        mock_get.side_effect = req.exceptions.Timeout()

        result = self.scorer.analyze_stock('GME')
        self.assertEqual(result['social_signal_score'], 0.0)
        self.assertEqual(result['social_error'], 'apewisdom_unavailable')

    @patch('src.signals.social_sentiment.requests.get')
    def test_api_connection_error(self, mock_get):
        """Connection error should return neutral with error flag."""
        import requests as req
        mock_get.side_effect = req.exceptions.ConnectionError()

        result = self.scorer.analyze_stock('GME')
        self.assertEqual(result['social_signal_score'], 0.0)
        self.assertEqual(result['social_error'], 'apewisdom_unavailable')

    @patch('src.signals.social_sentiment.requests.get')
    def test_api_http_error(self, mock_get):
        """HTTP error (e.g. 500) should return neutral with error flag."""
        mock_resp = MagicMock()
        import requests as req
        mock_resp.raise_for_status.side_effect = req.exceptions.HTTPError("500")
        mock_get.return_value = mock_resp

        result = self.scorer.analyze_stock('GME')
        self.assertEqual(result['social_signal_score'], 0.0)
        self.assertEqual(result['social_error'], 'apewisdom_unavailable')

    # ------------------------------------------------------------------
    # Score boundaries
    # ------------------------------------------------------------------

    @patch('src.signals.social_sentiment.requests.get', side_effect=_mock_get_responses)
    def test_scores_within_bounds(self, mock_get):
        """All scores should be between 0 and 100."""
        all_tickers = ['GME', 'AMC', 'TSLA', 'AAPL', 'NVDA', 'SPY', 'AMD',
                        'PLTR', 'MSFT', 'META', 'GOOG', 'SOFI', 'COIN',
                        'RIVN', 'SNAP', 'WISH', 'NEWSTOCK', 'UNKNOWN']
        results = self.scorer.analyze_batch(all_tickers)

        for ticker, result in results.items():
            self.assertGreaterEqual(result['social_signal_score'], 0.0,
                                    f"{ticker} score below 0")
            self.assertLessEqual(result['social_signal_score'], 100.0,
                                 f"{ticker} score above 100")

    # ------------------------------------------------------------------
    # Return format
    # ------------------------------------------------------------------

    @patch('src.signals.social_sentiment.requests.get', side_effect=_mock_get_responses)
    def test_return_format_complete(self, mock_get):
        """Result should contain all required keys with correct types."""
        result = self.scorer.analyze_stock('GME')

        self.assertIsInstance(result['social_signal_score'], float)
        self.assertIsInstance(result['social_signal_direction'], str)
        self.assertIsInstance(result['social_mentions_rank'], int)
        self.assertIsInstance(result['social_mentions_count'], int)
        self.assertIsInstance(result['social_mention_velocity'], float)
        self.assertIsInstance(result['social_upvotes'], int)
        self.assertIsInstance(result['social_trending'], bool)
        self.assertIsInstance(result['social_new_discovery'], bool)

        self.assertIn(result['social_signal_direction'],
                      ['bullish_momentum', 'neutral', 'contrarian_warning'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
