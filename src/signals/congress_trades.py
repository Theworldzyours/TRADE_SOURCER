"""
Congressional & Political Trading Tracker

Fetches and analyzes congressional stock trading data from
House Stock Watcher (free, no auth required).
"""
import time
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests

from ..utils.logger import get_logger

logger = get_logger()

# House Stock Watcher public S3 endpoint
HSW_ALL_TRANSACTIONS_URL = (
    "https://house-stock-watcher-data.s3-us-west-2.amazonaws.com"
    "/data/all_transactions.json"
)

# Amount range midpoints for scoring
AMOUNT_MIDPOINTS = {
    "$1,001 - $15,000": 8_000,
    "$15,001 - $50,000": 32_500,
    "$50,001 - $100,000": 75_000,
    "$100,001 - $250,000": 175_000,
    "$250,001 - $500,000": 375_000,
    "$500,001 - $1,000,000": 750_000,
    "$1,000,001 - $5,000,000": 3_000_000,
    "$5,000,001 - $25,000,000": 15_000_000,
    "$25,000,001 - $50,000,000": 37_500_000,
    "$50,000,001 - ": 50_000_000,
    "Over $50,000,000": 50_000_000,
}


def _parse_amount_to_midpoint(amount_str: str) -> float:
    """Parse House Stock Watcher amount range string to estimated midpoint.

    Args:
        amount_str: Range string like "$1,001 - $15,000"

    Returns:
        Estimated dollar midpoint, or 0 if unparseable.
    """
    if not amount_str:
        return 0.0

    amount_str = amount_str.strip()

    # Direct lookup
    if amount_str in AMOUNT_MIDPOINTS:
        return float(AMOUNT_MIDPOINTS[amount_str])

    # Try to extract two dollar figures and average them
    figures = re.findall(r'[\$]?([\d,]+)', amount_str)
    if len(figures) >= 2:
        try:
            low = float(figures[0].replace(',', ''))
            high = float(figures[1].replace(',', ''))
            return (low + high) / 2.0
        except ValueError:
            pass
    elif len(figures) == 1:
        try:
            return float(figures[0].replace(',', ''))
        except ValueError:
            pass

    return 0.0


def _parse_date(date_str: str) -> Optional[datetime]:
    """Parse date string from HSW data, trying common formats.

    Args:
        date_str: Date string like "2024-01-15" or "01/15/2024"

    Returns:
        datetime or None
    """
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


class CongressTradesTracker:
    """Track and score congressional stock trading activity.

    Fetches the full House Stock Watcher dataset, caches it for 24h,
    then filters/scores per ticker on demand.
    """

    def __init__(self, config: Dict = None):
        """
        Initialize tracker.

        Args:
            config: Optional configuration dict. Keys:
                - cache_ttl_seconds (int): Cache lifetime, default 86400 (24h)
                - lookback_days (int): How far back to consider, default 45
                - cluster_window_days (int): Window for cluster detection, default 30
                - request_timeout (int): HTTP timeout in seconds, default 30
        """
        self.config = config or {}
        self.cache_ttl = self.config.get('cache_ttl_seconds', 86400)
        self.lookback_days = self.config.get('lookback_days', 45)
        self.cluster_window_days = self.config.get('cluster_window_days', 30)
        self.request_timeout = self.config.get('request_timeout', 30)

        # In-memory cache
        self._cached_trades: Optional[List[Dict]] = None
        self._cache_timestamp: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_stock(self, ticker: str) -> Dict:
        """Analyze congressional trading activity for a single ticker.

        Args:
            ticker: Stock ticker symbol (e.g. "AAPL")

        Returns:
            Dict with congress signal data (see module docstring).
        """
        ticker = ticker.upper().strip()
        try:
            all_trades = self._fetch_all_trades()
        except Exception as e:
            logger.error(f"Failed to fetch congressional trades: {e}")
            return self._neutral_result(ticker, error=str(e))

        return self._score_ticker(ticker, all_trades)

    def analyze_batch(self, tickers: List[str]) -> Dict[str, Dict]:
        """Analyze congressional trading for multiple tickers (single fetch).

        Args:
            tickers: List of ticker symbols

        Returns:
            Dict mapping ticker -> analysis result
        """
        try:
            all_trades = self._fetch_all_trades()
        except Exception as e:
            logger.error(f"Failed to fetch congressional trades: {e}")
            return {
                t.upper().strip(): self._neutral_result(t.upper().strip(), error=str(e))
                for t in tickers
            }

        return {
            t.upper().strip(): self._score_ticker(t.upper().strip(), all_trades)
            for t in tickers
        }

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    def _fetch_all_trades(self) -> List[Dict]:
        """Fetch full transaction dataset from House Stock Watcher.

        Results are cached in memory for ``cache_ttl`` seconds.

        Returns:
            List of raw transaction dicts.

        Raises:
            requests.RequestException: On network/HTTP errors.
        """
        now = time.time()
        if self._cached_trades is not None and (now - self._cache_timestamp) < self.cache_ttl:
            logger.debug("Using cached congressional trades data")
            return self._cached_trades

        logger.info("Fetching congressional trades from House Stock Watcher")
        resp = requests.get(HSW_ALL_TRANSACTIONS_URL, timeout=self.request_timeout)
        resp.raise_for_status()
        data = resp.json()

        self._cached_trades = data
        self._cache_timestamp = time.time()
        logger.info(f"Cached {len(data)} congressional transactions")
        return data

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _score_ticker(self, ticker: str, all_trades: List[Dict]) -> Dict:
        """Filter trades for *ticker* and compute signal scores.

        Args:
            ticker: Uppercase ticker symbol.
            all_trades: Full dataset from HSW.

        Returns:
            Signal result dict.
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(days=self.lookback_days)
        cluster_cutoff = now - timedelta(days=self.cluster_window_days)
        recency_cutoff = now - timedelta(days=7)

        purchases: List[Dict] = []

        for t in all_trades:
            # Match ticker
            raw_ticker = (t.get('ticker') or '').upper().strip()
            if raw_ticker != ticker:
                continue

            # Only purchases
            tx_type = (t.get('type') or '').lower()
            if 'purchase' not in tx_type:
                continue

            # Parse disclosure_date for recency filter
            disclosure_dt = _parse_date(t.get('disclosure_date'))
            if disclosure_dt is None:
                continue
            if disclosure_dt < cutoff:
                continue

            transaction_dt = _parse_date(t.get('transaction_date'))

            purchases.append({
                'representative': t.get('representative', 'Unknown'),
                'date': (transaction_dt or disclosure_dt).strftime('%Y-%m-%d'),
                'type': t.get('type', ''),
                'amount_range': t.get('amount', ''),
                'amount_midpoint': _parse_amount_to_midpoint(t.get('amount', '')),
                'disclosure_date': disclosure_dt.strftime('%Y-%m-%d'),
                '_disclosure_dt': disclosure_dt,
                '_transaction_dt': transaction_dt,
            })

        if not purchases:
            return self._neutral_result(ticker)

        # Unique politicians
        unique_traders = set(p['representative'] for p in purchases)

        # Cluster detection: multiple politicians within cluster window
        cluster_trades = [
            p for p in purchases
            if p['_disclosure_dt'] >= cluster_cutoff
        ]
        cluster_unique = set(p['representative'] for p in cluster_trades)
        cluster_detected = len(cluster_unique) >= 2

        # Latest trade
        latest_dt = max(p['_disclosure_dt'] for p in purchases)
        latest_trade_date = latest_dt.strftime('%Y-%m-%d')

        # Recency flag
        has_recent = latest_dt >= recency_cutoff

        # Max estimated amount
        max_amount = max(p['amount_midpoint'] for p in purchases)

        # ------ Score calculation ------
        score = 0.0

        if cluster_detected:
            cluster_size = len(cluster_unique)
            if cluster_size >= 3:
                score = 90.0
            else:
                score = 75.0
        elif max_amount >= 100_000:
            score = 60.0
        elif len(purchases) >= 1:
            score = 30.0

        # Recency bonus
        if has_recent:
            score = min(100.0, score + 10.0)

        # Activity volume bonus (many trades = stronger signal)
        if len(purchases) >= 5:
            score = min(100.0, score + 5.0)

        direction = 'bullish' if score >= 20 else 'neutral'

        # Clean output trades (drop internal keys)
        clean_trades = [
            {k: v for k, v in p.items() if not k.startswith('_')}
            for p in sorted(purchases, key=lambda x: x['disclosure_date'], reverse=True)
        ]

        return {
            'ticker': ticker,
            'congress_signal_score': round(score, 2),
            'congress_signal_direction': direction,
            'congress_trades': clean_trades,
            'congress_trade_count': len(purchases),
            'congress_unique_traders': len(unique_traders),
            'congress_latest_trade_date': latest_trade_date,
            'congress_cluster_detected': cluster_detected,
            'error': None,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _neutral_result(ticker: str, error: Optional[str] = None) -> Dict:
        """Return a neutral / empty result dict.

        Args:
            ticker: Ticker symbol.
            error: Optional error message.

        Returns:
            Dict with zeroed-out signal fields.
        """
        return {
            'ticker': ticker,
            'congress_signal_score': 0.0,
            'congress_signal_direction': 'neutral',
            'congress_trades': [],
            'congress_trade_count': 0,
            'congress_unique_traders': 0,
            'congress_latest_trade_date': None,
            'congress_cluster_detected': False,
            'error': error,
        }
