"""
Unit tests for ConvictionEngine — multi-signal conviction scoring.
"""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scoring.conviction_engine import (
    ConvictionEngine,
    DEFAULT_WEIGHTS,
    DARK_FLOW_ALERT,
    STRONG_SIGNAL,
    SINGLE_SIGNAL,
    TECHNICAL_ONLY,
    NEUTRAL_SCORE,
    ACTIVE_THRESHOLD,
    CONFLUENCE_BONUS,
    POSITION_SIZE_MAP,
    MAX_ALLOCATION_MAP,
)


def _make_stock(overrides: dict = None) -> dict:
    """Build a stock_data dict with all neutral (50) scores, then apply overrides."""
    base = {
        'ticker': 'TEST',
        'insider_signal_score': 50,
        'darkpool_signal_score': 50,
        'options_signal_score': 50,
        'congress_signal_score': 50,
        'ftd_signal_score': 50,
        'social_signal_score': 50,
        'technical_score': 50,
        'fundamental_score': 50,
        'volatility_score': 50,
    }
    if overrides:
        base.update(overrides)
    return base


class TestWeightedScoring(unittest.TestCase):
    """Verify weighted composite math."""

    def setUp(self):
        self.engine = ConvictionEngine()

    def test_all_neutral_gives_50(self):
        """All signals at 50 -> composite = 50 (no confluence bonus)."""
        result = self.engine.calculate_conviction_score(_make_stock())
        self.assertAlmostEqual(result['conviction_score'], 50.0, places=1)

    def test_all_max_gives_100(self):
        """All signals at 100 -> composite capped at 100."""
        stock = _make_stock({
            'insider_signal_score': 100,
            'darkpool_signal_score': 100,
            'options_signal_score': 100,
            'congress_signal_score': 100,
            'ftd_signal_score': 100,
            'social_signal_score': 100,
            'technical_score': 100,
            'fundamental_score': 100,
            'volatility_score': 100,
        })
        result = self.engine.calculate_conviction_score(stock)
        # Weighted sum = 100, + 15 bonus (5 dark signals) -> capped at 100
        self.assertEqual(result['conviction_score'], 100.0)

    def test_all_zero_gives_near_zero(self):
        """All signals at 0 -> composite near 0 (whale_13f defaults to 50 neutral)."""
        stock = _make_stock({
            'insider_signal_score': 0,
            'darkpool_signal_score': 0,
            'options_signal_score': 0,
            'congress_signal_score': 0,
            'ftd_signal_score': 0,
            'social_signal_score': 0,
            'technical_score': 0,
            'fundamental_score': 0,
            'volatility_score': 0,
        })
        result = self.engine.calculate_conviction_score(stock)
        # whale_13f has no score key in stock_data, defaults to 50 * 0.05 = 2.5
        self.assertAlmostEqual(result['conviction_score'], 2.5, places=1)

    def test_individual_weight_contribution(self):
        """Verify a single signal contributes its weight * score."""
        stock = _make_stock({'insider_signal_score': 100})
        result = self.engine.calculate_conviction_score(stock)
        # Insider weight 0.20. Score delta from neutral: 100-50=50 extra * 0.20 = 10 extra.
        # Base (all 50): 50.0. One at 100: 50 + (100-50)*0.20 = 60.0
        # No confluence bonus (only 1 dark signal > 60 = insider at 100).
        # Actually 1 signal = SINGLE_SIGNAL = 0 bonus
        self.assertAlmostEqual(result['conviction_score'], 60.0, places=1)

    def test_weight_normalization(self):
        """If weights don't sum to 1.0, they get normalized."""
        config = {'weights': {'insider_flow': 0.40, 'dark_pool': 0.40}}
        engine = ConvictionEngine(config)
        total = sum(engine.weights.values())
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_zero_weights_fallback(self):
        """Weights summing to 0 fall back to defaults."""
        config = {'weights': {k: 0.0 for k in DEFAULT_WEIGHTS}}
        engine = ConvictionEngine(config)
        self.assertEqual(engine.weights, DEFAULT_WEIGHTS)


class TestConfluenceDetection(unittest.TestCase):
    """Verify dark signal confluence detection at 0-5 signal levels."""

    def setUp(self):
        self.engine = ConvictionEngine()

    def test_zero_dark_signals(self):
        """All dark signals at/below threshold -> TECHNICAL_ONLY."""
        stock = _make_stock()  # all at 50 (below 60 threshold)
        result = self.engine.calculate_conviction_score(stock)
        self.assertEqual(result['conviction_level'], TECHNICAL_ONLY)
        self.assertEqual(result['active_dark_signal_count'], 0)
        self.assertEqual(result['active_dark_signals'], [])

    def test_one_dark_signal(self):
        """One dark signal above threshold -> SINGLE_SIGNAL."""
        stock = _make_stock({'insider_signal_score': 75})
        result = self.engine.calculate_conviction_score(stock)
        self.assertEqual(result['conviction_level'], SINGLE_SIGNAL)
        self.assertEqual(result['active_dark_signal_count'], 1)
        self.assertIn('insider_flow', result['active_dark_signals'])

    def test_two_dark_signals(self):
        """Two dark signals above threshold -> STRONG_SIGNAL."""
        stock = _make_stock({
            'insider_signal_score': 75,
            'darkpool_signal_score': 80,
        })
        result = self.engine.calculate_conviction_score(stock)
        self.assertEqual(result['conviction_level'], STRONG_SIGNAL)
        self.assertEqual(result['active_dark_signal_count'], 2)

    def test_three_dark_signals(self):
        """Three dark signals -> DARK_FLOW_ALERT."""
        stock = _make_stock({
            'insider_signal_score': 75,
            'darkpool_signal_score': 80,
            'options_signal_score': 65,
        })
        result = self.engine.calculate_conviction_score(stock)
        self.assertEqual(result['conviction_level'], DARK_FLOW_ALERT)
        self.assertEqual(result['active_dark_signal_count'], 3)

    def test_four_dark_signals(self):
        """Four dark signals -> still DARK_FLOW_ALERT."""
        stock = _make_stock({
            'insider_signal_score': 75,
            'darkpool_signal_score': 80,
            'options_signal_score': 65,
            'congress_signal_score': 70,
        })
        result = self.engine.calculate_conviction_score(stock)
        self.assertEqual(result['conviction_level'], DARK_FLOW_ALERT)
        self.assertEqual(result['active_dark_signal_count'], 4)

    def test_five_dark_signals(self):
        """All five dark signals active."""
        stock = _make_stock({
            'insider_signal_score': 75,
            'darkpool_signal_score': 80,
            'options_signal_score': 65,
            'congress_signal_score': 70,
            'ftd_signal_score': 90,
        })
        result = self.engine.calculate_conviction_score(stock)
        self.assertEqual(result['conviction_level'], DARK_FLOW_ALERT)
        self.assertEqual(result['active_dark_signal_count'], 5)

    def test_confluence_bonus_dark_flow(self):
        """DARK_FLOW_ALERT adds +15 to composite."""
        stock = _make_stock({
            'insider_signal_score': 75,
            'darkpool_signal_score': 80,
            'options_signal_score': 65,
        })
        result = self.engine.calculate_conviction_score(stock)
        # Compute expected weighted sum manually
        expected_weighted = (
            75 * 0.20 +   # insider
            80 * 0.15 +   # dark_pool
            65 * 0.15 +   # options
            50 * 0.15 +   # fundamental
            50 * 0.10 +   # technical
            50 * 0.05 +   # congress
            50 * 0.05 +   # social
            50 * 0.05 +   # ftd_short
            50 * 0.05 +   # whale_13f
            50 * 0.05     # volatility
        )
        expected = min(100.0, expected_weighted + 15)
        self.assertAlmostEqual(result['conviction_score'], round(expected, 2), places=1)

    def test_confluence_bonus_strong_signal(self):
        """STRONG_SIGNAL adds +8 to composite."""
        stock = _make_stock({
            'insider_signal_score': 75,
            'darkpool_signal_score': 80,
        })
        result = self.engine.calculate_conviction_score(stock)
        expected_weighted = (
            75 * 0.20 +
            80 * 0.15 +
            50 * 0.15 +
            50 * 0.15 +
            50 * 0.10 +
            50 * 0.05 +
            50 * 0.05 +
            50 * 0.05 +
            50 * 0.05 +
            50 * 0.05
        )
        expected = min(100.0, expected_weighted + 8)
        self.assertAlmostEqual(result['conviction_score'], round(expected, 2), places=1)

    def test_threshold_boundary_at_60(self):
        """Score of exactly 60 is NOT above threshold (>60 required)."""
        stock = _make_stock({'insider_signal_score': 60})
        result = self.engine.calculate_conviction_score(stock)
        self.assertEqual(result['active_dark_signal_count'], 0)

    def test_threshold_boundary_at_61(self):
        """Score of 61 IS above threshold."""
        stock = _make_stock({'insider_signal_score': 61})
        result = self.engine.calculate_conviction_score(stock)
        self.assertEqual(result['active_dark_signal_count'], 1)


class TestPositionSizing(unittest.TestCase):
    """Verify position sizing per conviction level."""

    def setUp(self):
        self.engine = ConvictionEngine()

    def test_dark_flow_alert_sizing(self):
        self.assertEqual(self.engine.get_position_size(DARK_FLOW_ALERT), (10.0, 15.0))

    def test_strong_signal_sizing(self):
        self.assertEqual(self.engine.get_position_size(STRONG_SIGNAL), (5.0, 10.0))

    def test_single_signal_sizing(self):
        self.assertEqual(self.engine.get_position_size(SINGLE_SIGNAL), (3.0, 5.0))

    def test_technical_only_sizing(self):
        self.assertEqual(self.engine.get_position_size(TECHNICAL_ONLY), (0.0, 0.0))

    def test_unknown_level_sizing(self):
        self.assertEqual(self.engine.get_position_size('NONEXISTENT'), (0.0, 0.0))

    def test_max_allocation_dark_flow(self):
        stock = _make_stock({
            'insider_signal_score': 80,
            'darkpool_signal_score': 80,
            'options_signal_score': 80,
        })
        result = self.engine.calculate_conviction_score(stock)
        self.assertEqual(result['max_allocation_pct'], 15.0)

    def test_max_allocation_technical_only(self):
        result = self.engine.calculate_conviction_score(_make_stock())
        self.assertEqual(result['max_allocation_pct'], 0.0)


class TestMissingSignals(unittest.TestCase):
    """Verify handling of missing / malformed signal scores."""

    def setUp(self):
        self.engine = ConvictionEngine()

    def test_completely_empty_stock_data(self):
        """Empty dict uses neutral (50) for everything."""
        result = self.engine.calculate_conviction_score({})
        self.assertAlmostEqual(result['conviction_score'], 50.0, places=1)
        self.assertEqual(result['conviction_level'], TECHNICAL_ONLY)

    def test_partial_signals_missing(self):
        """Missing signals default to 50."""
        stock = {'insider_signal_score': 80}
        result = self.engine.calculate_conviction_score(stock)
        # Only insider differs from 50
        expected = 50 + (80 - 50) * 0.20  # = 56.0, single signal, 0 bonus
        self.assertAlmostEqual(result['conviction_score'], expected, places=1)

    def test_non_numeric_score_treated_as_neutral(self):
        """String / None values fall back to 50."""
        stock = _make_stock({
            'insider_signal_score': 'bad_value',
            'darkpool_signal_score': None,
        })
        result = self.engine.calculate_conviction_score(stock)
        self.assertAlmostEqual(result['conviction_score'], 50.0, places=1)

    def test_score_clamping_above_100(self):
        """Values above 100 are clamped."""
        stock = _make_stock({'insider_signal_score': 200})
        result = self.engine.calculate_conviction_score(stock)
        self.assertEqual(result['signal_scores']['insider_flow'], 100.0)

    def test_score_clamping_below_0(self):
        """Negative values are clamped to 0."""
        stock = _make_stock({'insider_signal_score': -50})
        result = self.engine.calculate_conviction_score(stock)
        self.assertEqual(result['signal_scores']['insider_flow'], 0.0)


class TestRiskAssessment(unittest.TestCase):
    """Verify risk assessment with conflicting signals."""

    def setUp(self):
        self.engine = ConvictionEngine()

    def test_low_risk_neutral(self):
        """All neutral signals -> low risk."""
        result = self.engine.assess_risk(_make_stock())
        self.assertEqual(result, 'low')

    def test_high_volatility_raises_risk(self):
        """High volatility_score -> medium risk."""
        stock = _make_stock({'volatility_score': 75})
        result = self.engine.assess_risk(stock)
        self.assertIn(result, ('medium', 'high'))

    def test_conflicting_signals_raise_risk(self):
        """Bullish insider + bearish options -> high risk."""
        stock = _make_stock({
            'insider_signal_score': 80,   # bullish
            'options_signal_score': 30,   # bearish
        })
        result = self.engine.assess_risk(stock)
        self.assertIn(result, ('medium', 'high'))

    def test_tech_fundamental_divergence(self):
        """Technical 90, fundamental 40 -> raised risk."""
        stock = _make_stock({
            'technical_score': 90,
            'fundamental_score': 40,
        })
        result = self.engine.assess_risk(stock)
        self.assertIn(result, ('medium', 'high'))

    def test_high_vol_plus_conflict_is_high(self):
        """High volatility + conflicting signals -> high risk."""
        stock = _make_stock({
            'volatility_score': 80,
            'insider_signal_score': 80,
            'options_signal_score': 30,
        })
        result = self.engine.assess_risk(stock)
        self.assertEqual(result, 'high')

    def test_all_bullish_aligned_low_risk(self):
        """All signals aligned bullish, low vol -> low risk."""
        stock = _make_stock({
            'insider_signal_score': 80,
            'options_signal_score': 80,
            'darkpool_signal_score': 80,
            'congress_signal_score': 80,
            'technical_score': 80,
            'fundamental_score': 80,
            'volatility_score': 40,
        })
        result = self.engine.assess_risk(stock)
        self.assertEqual(result, 'low')


class TestScoreBounds(unittest.TestCase):
    """Conviction score must always be in [0, 100]."""

    def setUp(self):
        self.engine = ConvictionEngine()

    def test_score_never_exceeds_100(self):
        stock = _make_stock({k: 100 for k in [
            'insider_signal_score', 'darkpool_signal_score',
            'options_signal_score', 'congress_signal_score',
            'ftd_signal_score', 'social_signal_score',
            'technical_score', 'fundamental_score', 'volatility_score',
        ]})
        result = self.engine.calculate_conviction_score(stock)
        self.assertLessEqual(result['conviction_score'], 100.0)

    def test_score_never_below_0(self):
        stock = _make_stock({k: 0 for k in [
            'insider_signal_score', 'darkpool_signal_score',
            'options_signal_score', 'congress_signal_score',
            'ftd_signal_score', 'social_signal_score',
            'technical_score', 'fundamental_score', 'volatility_score',
        ]})
        result = self.engine.calculate_conviction_score(stock)
        self.assertGreaterEqual(result['conviction_score'], 0.0)


class TestBatchScoring(unittest.TestCase):
    """Verify score_batch processes multiple stocks."""

    def setUp(self):
        self.engine = ConvictionEngine()

    def test_batch_multiple_stocks(self):
        stocks = [
            _make_stock({'ticker': 'AAPL', 'insider_signal_score': 80}),
            _make_stock({'ticker': 'MSFT', 'darkpool_signal_score': 90}),
            _make_stock({'ticker': 'GOOG'}),
        ]
        results = self.engine.score_batch(stocks)
        self.assertEqual(len(results), 3)
        tickers = [r['ticker'] for r in results]
        self.assertIn('AAPL', tickers)
        self.assertIn('MSFT', tickers)
        self.assertIn('GOOG', tickers)

    def test_batch_empty_list(self):
        results = self.engine.score_batch([])
        self.assertEqual(results, [])

    def test_batch_preserves_ticker(self):
        stocks = [_make_stock({'ticker': 'XYZ'})]
        results = self.engine.score_batch(stocks)
        self.assertEqual(results[0]['ticker'], 'XYZ')


class TestConvictionLabels(unittest.TestCase):
    """Verify human-readable labels."""

    def setUp(self):
        self.engine = ConvictionEngine()

    def test_dark_flow_alert_label(self):
        stock = _make_stock({
            'insider_signal_score': 80,
            'darkpool_signal_score': 80,
            'options_signal_score': 80,
        })
        result = self.engine.calculate_conviction_score(stock)
        self.assertIn('Dark Flow Alert', result['conviction_label'])
        self.assertIn('3', result['conviction_label'])

    def test_technical_only_label(self):
        result = self.engine.calculate_conviction_score(_make_stock())
        self.assertIn('Technical Only', result['conviction_label'])


class TestReturnFormat(unittest.TestCase):
    """Verify all expected keys in return dict."""

    def test_all_keys_present(self):
        engine = ConvictionEngine()
        result = engine.calculate_conviction_score(_make_stock())
        expected_keys = {
            'conviction_score',
            'conviction_level',
            'conviction_label',
            'active_dark_signals',
            'active_dark_signal_count',
            'signal_scores',
            'position_size_pct',
            'max_allocation_pct',
            'risk_level',
        }
        self.assertEqual(set(result.keys()), expected_keys)

    def test_signal_scores_dict_has_all_weights(self):
        engine = ConvictionEngine()
        result = engine.calculate_conviction_score(_make_stock())
        for key in DEFAULT_WEIGHTS:
            self.assertIn(key, result['signal_scores'])


if __name__ == '__main__':
    unittest.main()
