"""
Social Sentiment & Momentum Scorer

Fetches Reddit mention data from ApeWisdom (free, no auth) to gauge
retail sentiment and momentum. This is a LOW WEIGHT signal (5% in
conviction engine) — noisy but useful for detecting early momentum
and contrarian warnings.
"""
import time
import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from ..utils.logger import get_logger

logger = get_logger()

# ApeWisdom API
APEWISDOM_BASE_URL = "https://apewisdom.io/api/v1.0/filter/all-stocks/page"
PAGES_TO_FETCH = 3
CACHE_TTL_SECONDS = 3600  # 1 hour
REQUEST_DELAY_SECONDS = 1.0

# Scoring thresholds
RANK_TOP_10 = 10
RANK_TOP_25 = 25
RANK_TOP_50 = 50
VELOCITY_ACCELERATION_THRESHOLD = 3.0  # 3x = early signal
VELOCITY_BONUS_POINTS = 15


def _neutral_result(ticker: str, error: Optional[str] = None) -> Dict:
    """Return a neutral/default result for a ticker."""
    result = {
        'social_signal_score': 0.0,
        'social_signal_direction': 'neutral',
        'social_mentions_rank': 0,
        'social_mentions_count': 0,
        'social_mention_velocity': 0.0,
        'social_upvotes': 0,
        'social_trending': False,
        'social_new_discovery': False,
    }
    if error:
        result['social_error'] = error
    return result


class SocialSentimentScorer:
    """
    Score stocks based on Reddit social sentiment data from ApeWisdom.

    Tracks mention counts, velocity, upvotes, and rank to produce
    a 0-100 social signal score.
    """

    def __init__(self, config: Dict = None):
        """
        Initialize social sentiment scorer.

        Args:
            config: Configuration dictionary with optional overrides:
                - pages_to_fetch (int): Number of API pages (default 3)
                - cache_ttl (int): Cache duration in seconds (default 3600)
                - request_delay (float): Delay between API calls (default 1.0)
        """
        self.config = config or {}
        self.pages_to_fetch = self.config.get('pages_to_fetch', PAGES_TO_FETCH)
        self.cache_ttl = self.config.get('cache_ttl', CACHE_TTL_SECONDS)
        self.request_delay = self.config.get('request_delay', REQUEST_DELAY_SECONDS)

        # Cache: {'data': [...], 'timestamp': datetime}
        self._cache: Optional[Dict] = None
        # Historical mentions for velocity: {ticker: [(timestamp, count), ...]}
        self._history: Dict[str, List[tuple]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_stock(self, ticker: str) -> Dict:
        """
        Analyze social sentiment for a single ticker.

        Args:
            ticker: Stock ticker symbol (e.g. 'AAPL')

        Returns:
            Dictionary with social signal metrics.
        """
        data = self._get_social_data()
        if data is None:
            return _neutral_result(ticker, error='apewisdom_unavailable')
        return self._score_ticker(ticker, data)

    def analyze_batch(self, tickers: List[str]) -> Dict[str, Dict]:
        """
        Analyze social sentiment for multiple tickers efficiently.
        Fetches API data once, then scores each ticker.

        Args:
            tickers: List of ticker symbols.

        Returns:
            Dictionary mapping ticker -> social signal result.
        """
        data = self._get_social_data()
        results = {}
        for ticker in tickers:
            if data is None:
                results[ticker] = _neutral_result(ticker, error='apewisdom_unavailable')
            else:
                results[ticker] = self._score_ticker(ticker, data)
        return results

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    def _get_social_data(self) -> Optional[List[Dict]]:
        """
        Fetch social data from ApeWisdom, using cache when valid.

        Returns:
            List of ticker dicts from the API, or None on failure.
        """
        now = datetime.utcnow()

        # Return cached data if still fresh
        if self._cache is not None:
            age = (now - self._cache['timestamp']).total_seconds()
            if age < self.cache_ttl:
                return self._cache['data']

        # Fetch fresh data
        all_results: List[Dict] = []
        try:
            for page in range(1, self.pages_to_fetch + 1):
                url = f"{APEWISDOM_BASE_URL}/{page}"
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                payload = response.json()
                results = payload.get('results', [])
                all_results.extend(results)
                logger.debug(f"ApeWisdom page {page}: {len(results)} tickers")

                # Rate limit between pages
                if page < self.pages_to_fetch:
                    time.sleep(self.request_delay)

        except requests.exceptions.Timeout:
            logger.warning("ApeWisdom API timed out")
            return self._cache['data'] if self._cache else None
        except requests.exceptions.ConnectionError:
            logger.warning("ApeWisdom API connection error")
            return self._cache['data'] if self._cache else None
        except requests.exceptions.HTTPError as e:
            logger.warning(f"ApeWisdom API HTTP error: {e}")
            return self._cache['data'] if self._cache else None
        except (ValueError, KeyError) as e:
            logger.warning(f"ApeWisdom API parse error: {e}")
            return self._cache['data'] if self._cache else None

        if not all_results:
            logger.warning("ApeWisdom returned no data")
            return self._cache['data'] if self._cache else None

        # Update cache
        self._cache = {'data': all_results, 'timestamp': now}

        # Update historical mentions for velocity calculations
        self._update_history(all_results, now)

        return all_results

    def _update_history(self, data: List[Dict], timestamp: datetime) -> None:
        """
        Store current mention counts for velocity tracking.
        Keeps last 48 hours of snapshots.

        Args:
            data: List of ticker data from API.
            timestamp: Current fetch timestamp.
        """
        cutoff = timestamp - timedelta(hours=48)

        for item in data:
            ticker = item.get('ticker', '')
            if not ticker:
                continue
            mentions = item.get('mentions', 0)

            if ticker not in self._history:
                self._history[ticker] = []

            self._history[ticker].append((timestamp, mentions))

            # Prune old entries
            self._history[ticker] = [
                (ts, cnt) for ts, cnt in self._history[ticker]
                if ts > cutoff
            ]

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _score_ticker(self, ticker: str, data: List[Dict]) -> Dict:
        """
        Score a single ticker against the social data.

        Args:
            ticker: Stock ticker symbol.
            data: Full list of social data from API.

        Returns:
            Social signal result dictionary.
        """
        ticker_upper = ticker.upper()

        # Find this ticker in the data
        entry = None
        for idx, item in enumerate(data):
            if item.get('ticker', '').upper() == ticker_upper:
                entry = item
                break

        if entry is None:
            return _neutral_result(ticker)

        # Extract raw metrics
        rank = entry.get('rank', 0)
        mentions = entry.get('mentions', 0)
        upvotes = entry.get('upvotes', 0)
        mentions_24h_ago = entry.get('mentions_24h_ago', 0)

        # Calculate velocity
        velocity = self._calculate_velocity(ticker_upper, mentions, mentions_24h_ago)

        # Detect patterns
        new_discovery = self._detect_new_discovery(ticker_upper, mentions, mentions_24h_ago)
        trending = rank <= RANK_TOP_25
        accelerating = velocity >= VELOCITY_ACCELERATION_THRESHOLD

        # Calculate score
        score = self._calculate_score(rank, mentions, upvotes, velocity, accelerating)

        # Determine direction
        direction = self._determine_direction(rank, velocity, accelerating, score)

        return {
            'social_signal_score': round(score, 2),
            'social_signal_direction': direction,
            'social_mentions_rank': rank,
            'social_mentions_count': mentions,
            'social_mention_velocity': round(velocity, 2),
            'social_upvotes': upvotes,
            'social_trending': trending,
            'social_new_discovery': new_discovery,
        }

    def _calculate_velocity(
        self, ticker: str, current_mentions: int, mentions_24h_ago: int
    ) -> float:
        """
        Calculate mention velocity (rate of change).

        Uses API-provided mentions_24h_ago when available, falls back
        to stored history.

        Args:
            ticker: Stock ticker symbol.
            current_mentions: Current mention count.
            mentions_24h_ago: Previous mention count from API.

        Returns:
            Velocity as a ratio (e.g. 3.0 = 3x increase).
        """
        # Prefer API-provided previous count
        if mentions_24h_ago and mentions_24h_ago > 0:
            return current_mentions / mentions_24h_ago

        # Fall back to stored history
        history = self._history.get(ticker, [])
        if len(history) < 2:
            return 1.0  # No history = neutral velocity

        # Compare latest to oldest snapshot
        oldest_count = history[0][1]
        if oldest_count > 0:
            return current_mentions / oldest_count

        # Was zero before, now has mentions = big spike
        if current_mentions > 0:
            return float(current_mentions)

        return 1.0

    def _detect_new_discovery(
        self, ticker: str, current_mentions: int, mentions_24h_ago: int
    ) -> bool:
        """
        Detect sudden appearance from zero/near-zero baseline.

        Args:
            ticker: Stock ticker symbol.
            current_mentions: Current mention count.
            mentions_24h_ago: Previous mention count.

        Returns:
            True if this looks like a new discovery.
        """
        if current_mentions <= 0:
            return False

        # From near-zero to meaningful mentions
        if mentions_24h_ago <= 2 and current_mentions >= 10:
            return True

        # Check stored history for sudden appearance
        history = self._history.get(ticker, [])
        if len(history) >= 2:
            oldest_count = history[0][1]
            if oldest_count <= 2 and current_mentions >= 10:
                return True

        return False

    def _calculate_score(
        self,
        rank: int,
        mentions: int,
        upvotes: int,
        velocity: float,
        accelerating: bool,
    ) -> float:
        """
        Calculate social signal score (0-100).

        Scoring tiers:
          - Top 10 mentions + accelerating velocity: 70-90
          - Top 25 mentions + positive sentiment: 50-70
          - Top 50 mentions: 30-50
          - Not in top mentions: 0-20

        Args:
            rank: Mention rank (1 = most mentioned).
            mentions: Absolute mention count.
            upvotes: Total upvotes.
            velocity: Mention velocity ratio.
            accelerating: Whether velocity >= 3x threshold.

        Returns:
            Score between 0 and 100.
        """
        score = 0.0

        # Base score from rank
        if rank <= RANK_TOP_10:
            # Top 10: 70-90 base range
            # Rank 1 = 90, rank 10 = 70
            score = 90.0 - ((rank - 1) * 2.2)
        elif rank <= RANK_TOP_25:
            # Top 25: 50-70 range
            # Rank 11 = 68, rank 25 = 50
            score = 70.0 - ((rank - RANK_TOP_10) * 1.33)
        elif rank <= RANK_TOP_50:
            # Top 50: 30-50 range
            score = 50.0 - ((rank - RANK_TOP_25) * 0.8)
        else:
            # Below top 50: 5-30 range based on presence
            score = max(5.0, 30.0 - ((rank - RANK_TOP_50) * 0.5))

        # Velocity bonus
        if accelerating:
            score += VELOCITY_BONUS_POINTS

        # Upvote conviction bonus (high upvotes = strong retail agreement)
        if upvotes > 1000:
            score += 5.0
        elif upvotes > 500:
            score += 3.0
        elif upvotes > 100:
            score += 1.0

        return min(100.0, max(0.0, score))

    def _determine_direction(
        self, rank: int, velocity: float, accelerating: bool, score: float
    ) -> str:
        """
        Determine the social signal direction.

        Args:
            rank: Mention rank.
            velocity: Mention velocity.
            accelerating: Whether velocity is accelerating.
            score: Calculated score.

        Returns:
            One of 'bullish_momentum', 'neutral', 'contrarian_warning'.
        """
        # High score + accelerating = bullish momentum
        if score >= 50 and accelerating:
            return 'bullish_momentum'

        # Very top ranked + decelerating velocity = potential contrarian
        if rank <= RANK_TOP_10 and velocity < 0.8:
            return 'contrarian_warning'

        # Moderate social presence with positive velocity
        if score >= 30 and velocity > 1.0:
            return 'bullish_momentum'

        return 'neutral'
