"""
Conviction Engine — Multi-signal conviction scoring system.

Replaces the old VC scorer with weighted composite scoring across all
signal detectors (insider flow, dark pool, options, congress, FTD, social)
plus traditional technical/fundamental indicators.
"""
from typing import Dict, List, Optional
from ..utils.logger import get_logger

logger = get_logger()

# Default weights — must sum to 1.0
DEFAULT_WEIGHTS = {
    'insider_flow': 0.20,
    'dark_pool': 0.15,
    'options_flow': 0.15,
    'fundamental': 0.15,
    'technical': 0.10,
    'congress': 0.05,
    'social': 0.05,
    'ftd_short': 0.05,
    'whale_13f': 0.05,
    'volatility': 0.05,
}

# Maps config weight key -> stock_data score key
WEIGHT_TO_SCORE_KEY = {
    'insider_flow': 'insider_signal_score',
    'dark_pool': 'darkpool_signal_score',
    'options_flow': 'options_signal_score',
    'congress': 'congress_signal_score',
    'ftd_short': 'ftd_signal_score',
    'social': 'social_signal_score',
    'technical': 'technical_score',
    'fundamental': 'fundamental_score',
    'volatility': 'volatility_score',
    'whale_13f': 'whale_13f_signal_score',
}

# Dark signal keys used for confluence detection
DEFAULT_DARK_SIGNAL_KEYS = [
    'insider_flow',
    'dark_pool',
    'options_flow',
    'congress',
    'ftd_short',
]

NEUTRAL_SCORE = 50.0
ACTIVE_THRESHOLD = 60.0

# Conviction levels
DARK_FLOW_ALERT = 'DARK_FLOW_ALERT'
STRONG_SIGNAL = 'STRONG_SIGNAL'
SINGLE_SIGNAL = 'SINGLE_SIGNAL'
TECHNICAL_ONLY = 'TECHNICAL_ONLY'

# Confluence bonuses applied to composite score
CONFLUENCE_BONUS = {
    DARK_FLOW_ALERT: 15,
    STRONG_SIGNAL: 8,
    SINGLE_SIGNAL: 0,
    TECHNICAL_ONLY: 0,
}

# Position sizing ranges (min_pct, max_pct)
POSITION_SIZE_MAP = {
    DARK_FLOW_ALERT: (10.0, 15.0),
    STRONG_SIGNAL: (5.0, 10.0),
    SINGLE_SIGNAL: (3.0, 5.0),
    TECHNICAL_ONLY: (0.0, 0.0),
}

# Max allocation caps per conviction level
MAX_ALLOCATION_MAP = {
    DARK_FLOW_ALERT: 15.0,
    STRONG_SIGNAL: 10.0,
    SINGLE_SIGNAL: 5.0,
    TECHNICAL_ONLY: 0.0,
}


class ConvictionEngine:
    """
    Multi-signal conviction scoring engine.

    Calculates a weighted composite from all signal detectors and traditional
    indicators, detects signal confluence, and recommends position sizing.
    """

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.weights = self._load_weights()
        self.dark_signal_keys = self.config.get(
            'dark_signal_keys', DEFAULT_DARK_SIGNAL_KEYS
        )
        self.dark_flow_min = self.config.get('dark_flow_alert_min_signals', 3)
        self.strong_signal_min = self.config.get('strong_signal_min_signals', 2)

    # ------------------------------------------------------------------
    # Weight loading
    # ------------------------------------------------------------------

    def _load_weights(self) -> Dict[str, float]:
        """Load and normalize weights from config (or defaults)."""
        raw = self.config.get('weights', DEFAULT_WEIGHTS.copy())
        # Fill in any missing keys with defaults
        weights = {k: raw.get(k, DEFAULT_WEIGHTS.get(k, 0.0)) for k in DEFAULT_WEIGHTS}
        total = sum(weights.values())
        if total <= 0:
            logger.warning("Conviction weights sum to 0; using defaults")
            return DEFAULT_WEIGHTS.copy()
        if abs(total - 1.0) > 1e-6:
            logger.info(f"Normalizing conviction weights (sum={total:.4f})")
            weights = {k: v / total for k, v in weights.items()}
        return weights

    # ------------------------------------------------------------------
    # Core scoring
    # ------------------------------------------------------------------

    def _get_signal_score(self, stock_data: Dict, weight_key: str) -> float:
        """Extract a score from stock_data for a given weight key.

        Returns NEUTRAL_SCORE (50) if the signal is missing.
        Clamps the result to [0, 100].
        """
        score_key = WEIGHT_TO_SCORE_KEY.get(weight_key)
        if score_key is None:
            return NEUTRAL_SCORE
        raw = stock_data.get(score_key)
        if raw is None:
            return NEUTRAL_SCORE
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return NEUTRAL_SCORE
        return max(0.0, min(100.0, value))

    def calculate_conviction_score(self, stock_data: Dict) -> Dict:
        """Calculate conviction-weighted composite for one stock.

        Args:
            stock_data: Dict containing signal and indicator scores.

        Returns:
            Dict with conviction scoring results.
        """
        # 1. Compute individual weighted contributions
        signal_scores: Dict[str, float] = {}
        weighted_sum = 0.0

        for key, weight in self.weights.items():
            score = self._get_signal_score(stock_data, key)
            signal_scores[key] = round(score, 2)
            weighted_sum += score * weight

        # 2. Detect dark-signal confluence
        active_dark_signals = self._detect_active_dark_signals(signal_scores)
        active_count = len(active_dark_signals)

        conviction_level = self.get_conviction_level(weighted_sum, active_dark_signals)

        # 3. Apply confluence bonus (capped at 100)
        bonus = CONFLUENCE_BONUS.get(conviction_level, 0)
        conviction_score = min(100.0, max(0.0, weighted_sum + bonus))

        # 4. Position sizing and risk
        position_min, position_max = self.get_position_size(conviction_level)
        max_allocation = MAX_ALLOCATION_MAP.get(conviction_level, 0.0)
        risk_level = self.assess_risk(stock_data)

        return {
            'conviction_score': round(conviction_score, 2),
            'conviction_level': conviction_level,
            'conviction_label': self._build_label(conviction_level, active_count, active_dark_signals),
            'active_dark_signals': active_dark_signals,
            'active_dark_signal_count': active_count,
            'signal_scores': signal_scores,
            'position_size_pct': position_min,
            'max_allocation_pct': max_allocation,
            'risk_level': risk_level,
        }

    # ------------------------------------------------------------------
    # Confluence detection
    # ------------------------------------------------------------------

    def _detect_active_dark_signals(self, signal_scores: Dict[str, float]) -> List[str]:
        """Return list of dark signal keys scoring above ACTIVE_THRESHOLD."""
        active = []
        for key in self.dark_signal_keys:
            if signal_scores.get(key, NEUTRAL_SCORE) > ACTIVE_THRESHOLD:
                active.append(key)
        return active

    def get_conviction_level(self, score: float, active_signals: List[str]) -> str:
        """Classify conviction level based on active dark-signal count."""
        count = len(active_signals)
        if count >= self.dark_flow_min:
            return DARK_FLOW_ALERT
        if count >= self.strong_signal_min:
            return STRONG_SIGNAL
        if count >= 1:
            return SINGLE_SIGNAL
        return TECHNICAL_ONLY

    # ------------------------------------------------------------------
    # Position sizing
    # ------------------------------------------------------------------

    def get_position_size(self, conviction_level: str) -> tuple:
        """Return (min_pct, max_pct) for a conviction level."""
        return POSITION_SIZE_MAP.get(conviction_level, (0.0, 0.0))

    # ------------------------------------------------------------------
    # Risk assessment
    # ------------------------------------------------------------------

    def assess_risk(self, stock_data: Dict) -> str:
        """Assess risk based on volatility and signal direction conflicts.

        Heuristics:
        - High volatility_score (>70) raises risk.
        - Conflicting directions among bullish/bearish signals raise risk.
          e.g. insider bullish (>60) + options bearish (<40) = conflict.

        Returns:
            'low', 'medium', or 'high'
        """
        risk_points = 0

        # Volatility component
        vol_score = self._safe_float(stock_data.get('volatility_score'), NEUTRAL_SCORE)
        if vol_score > 70:
            risk_points += 2
        elif vol_score > 55:
            risk_points += 1

        # Direction conflict detection
        bullish_signals = []
        bearish_signals = []

        signal_pairs = [
            ('insider_signal_score', 'insider'),
            ('options_signal_score', 'options'),
            ('darkpool_signal_score', 'dark_pool'),
            ('congress_signal_score', 'congress'),
        ]

        for score_key, label in signal_pairs:
            val = self._safe_float(stock_data.get(score_key), None)
            if val is None:
                continue
            if val > 60:
                bullish_signals.append(label)
            elif val < 40:
                bearish_signals.append(label)

        if bullish_signals and bearish_signals:
            risk_points += 2  # Conflicting directions

        # Technical vs fundamental disagreement
        tech = self._safe_float(stock_data.get('technical_score'), None)
        fund = self._safe_float(stock_data.get('fundamental_score'), None)
        if tech is not None and fund is not None:
            if abs(tech - fund) > 30:
                risk_points += 1

        if risk_points >= 3:
            return 'high'
        elif risk_points >= 1:
            return 'medium'
        return 'low'

    # ------------------------------------------------------------------
    # Batch scoring
    # ------------------------------------------------------------------

    def score_batch(self, stocks_data: List[Dict]) -> List[Dict]:
        """Score multiple stocks, returning conviction results for each.

        Each input dict is passed through calculate_conviction_score.
        Items that fail are logged and skipped.
        """
        results = []
        for stock_data in stocks_data:
            ticker = stock_data.get('ticker', 'UNKNOWN')
            try:
                result = self.calculate_conviction_score(stock_data)
                result['ticker'] = ticker
                results.append(result)
            except Exception as e:
                logger.error(f"ConvictionEngine error scoring {ticker}: {e}")
        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_float(value, default):
        """Convert value to float, returning default on failure."""
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _build_label(level: str, count: int, active: List[str]) -> str:
        """Build a human-readable conviction label."""
        if level == DARK_FLOW_ALERT:
            return f"Dark Flow Alert - {count} signals converging"
        if level == STRONG_SIGNAL:
            names = ', '.join(active)
            return f"Strong Signal - {names}"
        if level == SINGLE_SIGNAL:
            names = ', '.join(active)
            return f"Single Signal - {names}"
        return "Technical Only - no dark flow signals active"
