"""
Dark Pool & Short Sale Volume Analyzer

Fetches FINRA short sale volume data (free, no auth) and calculates
accumulation/distribution signals from off-exchange activity patterns.

Data source: FINRA CNMS Short Volume files
URL: https://cdn.finra.org/equity/regsho/daily/CNMSshvol{YYYYMMDD}.txt
"""
import io
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import requests

from ..utils.logger import get_logger

logger = get_logger()

# Signal direction constants
DIRECTION_ACCUMULATION = 'accumulation'
DIRECTION_DISTRIBUTION = 'distribution'
DIRECTION_NEUTRAL = 'neutral'

# Trend constants
TREND_DECLINING = 'declining'
TREND_RISING = 'rising'
TREND_STABLE = 'stable'

# FINRA CDN base URL
FINRA_BASE_URL = 'https://cdn.finra.org/equity/regsho/daily/CNMSshvol{date}.txt'

# US market holidays (2024-2026) — static list, good enough for 20-day lookback
_US_MARKET_HOLIDAYS = {
    # 2025
    datetime(2025, 1, 1), datetime(2025, 1, 20), datetime(2025, 2, 17),
    datetime(2025, 4, 18), datetime(2025, 5, 26), datetime(2025, 6, 19),
    datetime(2025, 7, 4), datetime(2025, 9, 1), datetime(2025, 11, 27),
    datetime(2025, 12, 25),
    # 2026
    datetime(2026, 1, 1), datetime(2026, 1, 19), datetime(2026, 2, 16),
    datetime(2026, 4, 3), datetime(2026, 5, 25), datetime(2026, 6, 19),
    datetime(2026, 7, 3), datetime(2026, 9, 7), datetime(2026, 11, 26),
    datetime(2026, 12, 25),
    # 2024
    datetime(2024, 1, 1), datetime(2024, 1, 15), datetime(2024, 2, 19),
    datetime(2024, 3, 29), datetime(2024, 5, 27), datetime(2024, 6, 19),
    datetime(2024, 7, 4), datetime(2024, 9, 2), datetime(2024, 11, 28),
    datetime(2024, 12, 25),
}


class DarkPoolAnalyzer:
    """
    Analyzes FINRA short sale volume data to detect accumulation and
    distribution patterns from dark pool / off-exchange activity.

    Constructor accepts a config dict with optional keys:
        - lookback_days (int): Number of trading days for trend analysis. Default 20.
        - std_dev_threshold (float): Std dev threshold for anomaly detection. Default 2.0.
        - cache_dir (str): Path to cache directory. Default 'data/cache/finra'.
        - request_timeout (int): HTTP timeout in seconds. Default 10.
        - batch_delay (float): Seconds between batch requests. Default 0.5.
    """

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.lookback_days = self.config.get('lookback_days', 20)
        self.std_dev_threshold = self.config.get('std_dev_threshold', 2.0)
        self.request_timeout = self.config.get('request_timeout', 10)
        self.batch_delay = self.config.get('batch_delay', 0.5)

        # Resolve cache dir relative to project root
        base_dir = Path(__file__).parent.parent.parent
        cache_path = self.config.get('cache_dir', str(base_dir / 'data' / 'cache' / 'finra'))
        self.cache_dir = Path(cache_path)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Internal cache of parsed DataFrames keyed by date string
        self._daily_frames: Dict[str, pd.DataFrame] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_stock(self, ticker: str) -> Dict:
        """
        Main entry point. Analyze dark pool signals for a single ticker.

        Args:
            ticker: US equity ticker symbol (e.g. 'AAPL').

        Returns:
            Dict with dark pool signal metrics (see module docstring).
        """
        ticker = ticker.upper().strip()
        try:
            trading_days = self._get_trading_days(self.lookback_days)
            daily_data = self._collect_ticker_data(ticker, trading_days)

            if daily_data.empty or len(daily_data) < 3:
                logger.warning(f"Insufficient FINRA data for {ticker}")
                return self._neutral_result(ticker, error='insufficient_data')

            return self._score_signals(ticker, daily_data)

        except requests.RequestException as exc:
            logger.error(f"Network error fetching FINRA data for {ticker}: {exc}")
            return self._neutral_result(ticker, error='network_error')
        except Exception as exc:
            logger.error(f"Unexpected error analyzing {ticker}: {exc}")
            return self._neutral_result(ticker, error=str(exc))

    def analyze_batch(self, tickers: List[str]) -> Dict[str, Dict]:
        """
        Analyze multiple tickers with rate limiting.

        Args:
            tickers: List of ticker symbols.

        Returns:
            Dict mapping ticker -> signal result dict.
        """
        results = {}
        # Pre-fetch all FINRA daily files once (shared across tickers)
        trading_days = self._get_trading_days(self.lookback_days)
        for day in trading_days:
            self._fetch_finra_data(day)

        for i, ticker in enumerate(tickers):
            results[ticker.upper()] = self.analyze_stock(ticker)
            if i < len(tickers) - 1:
                time.sleep(self.batch_delay)

        return results

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    def _fetch_finra_data(self, date: datetime) -> Optional[pd.DataFrame]:
        """
        Fetch and cache a single day's FINRA short volume file.

        Args:
            date: Trading day to fetch.

        Returns:
            DataFrame with columns [Date, Symbol, ShortVolume,
            ShortExemptVolume, TotalVolume, Market] or None on failure.
        """
        date_str = date.strftime('%Y%m%d')

        # Check in-memory cache first
        if date_str in self._daily_frames:
            return self._daily_frames[date_str]

        # Check disk cache
        cache_file = self.cache_dir / f'CNMSshvol{date_str}.txt'
        if cache_file.exists():
            df = self._parse_finra_file(cache_file.read_text())
            if df is not None:
                self._daily_frames[date_str] = df
                return df

        # Download from FINRA CDN
        url = FINRA_BASE_URL.format(date=date_str)
        try:
            resp = requests.get(url, timeout=self.request_timeout)
            if resp.status_code == 404:
                logger.debug(f"No FINRA file for {date_str} (404)")
                return None
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning(f"Failed to download FINRA file for {date_str}: {exc}")
            return None

        # Cache to disk
        cache_file.write_text(resp.text)

        df = self._parse_finra_file(resp.text)
        if df is not None:
            self._daily_frames[date_str] = df
        return df

    @staticmethod
    def _parse_finra_file(text: str) -> Optional[pd.DataFrame]:
        """Parse pipe-delimited FINRA short volume text into a DataFrame."""
        try:
            df = pd.read_csv(
                io.StringIO(text),
                sep='|',
                dtype={
                    'ShortVolume': 'Int64',
                    'ShortExemptVolume': 'Int64',
                    'TotalVolume': 'Int64',
                },
                on_bad_lines='skip',
            )
            # Normalise column names (some files have trailing spaces)
            df.columns = df.columns.str.strip()
            required = {'Date', 'Symbol', 'ShortVolume', 'TotalVolume'}
            if not required.issubset(set(df.columns)):
                return None
            df['Symbol'] = df['Symbol'].str.strip().str.upper()
            return df
        except Exception as exc:
            logger.warning(f"Failed to parse FINRA file: {exc}")
            return None

    # ------------------------------------------------------------------
    # Trading day helpers
    # ------------------------------------------------------------------

    def _get_trading_days(self, n: int = 20) -> List[datetime]:
        """
        Return the last *n* trading day dates (skipping weekends & US holidays).

        Walks backwards from today (or yesterday if before market close).
        """
        days: List[datetime] = []
        current = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Start from yesterday to ensure data availability
        current -= timedelta(days=1)

        max_lookback = n * 3  # safety cap
        attempts = 0
        while len(days) < n and attempts < max_lookback:
            if self._is_trading_day(current):
                days.append(current)
            current -= timedelta(days=1)
            attempts += 1

        return list(reversed(days))  # oldest first

    @staticmethod
    def _is_trading_day(dt: datetime) -> bool:
        """Return True if *dt* is a weekday and not a US market holiday."""
        if dt.weekday() >= 5:  # Saturday / Sunday
            return False
        return dt.replace(hour=0, minute=0, second=0, microsecond=0) not in _US_MARKET_HOLIDAYS

    # ------------------------------------------------------------------
    # Per-ticker data collection
    # ------------------------------------------------------------------

    def _collect_ticker_data(self, ticker: str, trading_days: List[datetime]) -> pd.DataFrame:
        """
        Gather short volume rows for *ticker* across all *trading_days*.

        Returns a DataFrame sorted by date with columns:
            [Date, ShortVolume, ShortExemptVolume, TotalVolume, short_volume_ratio]
        """
        rows = []
        for day in trading_days:
            df = self._fetch_finra_data(day)
            if df is None:
                continue
            match = df[df['Symbol'] == ticker]
            if match.empty:
                continue
            # Aggregate across markets for the same symbol/date
            agg = match.groupby('Date').agg({
                'ShortVolume': 'sum',
                'TotalVolume': 'sum',
            }).reset_index()
            if 'ShortExemptVolume' in match.columns:
                exempt = match.groupby('Date')['ShortExemptVolume'].sum().reset_index()
                agg = agg.merge(exempt, on='Date', how='left')
            else:
                agg['ShortExemptVolume'] = 0
            rows.append(agg)

        if not rows:
            return pd.DataFrame()

        result = pd.concat(rows, ignore_index=True)
        result['TotalVolume'] = result['TotalVolume'].replace(0, np.nan)
        result['short_volume_ratio'] = result['ShortVolume'] / result['TotalVolume']
        result = result.sort_values('Date').reset_index(drop=True)
        return result

    # ------------------------------------------------------------------
    # Signal scoring
    # ------------------------------------------------------------------

    def _score_signals(self, ticker: str, data: pd.DataFrame) -> Dict:
        """
        Calculate all dark pool metrics and produce a 0-100 signal score.
        """
        ratios = data['short_volume_ratio'].dropna()
        volumes = data['TotalVolume'].dropna()

        current_ratio = ratios.iloc[-1]
        avg_ratio = ratios.mean()
        std_ratio = ratios.std() if len(ratios) > 1 else 0.0
        ratio_deviation = (current_ratio - avg_ratio) / std_ratio if std_ratio > 0 else 0.0

        avg_volume = volumes.mean()
        current_volume = volumes.iloc[-1]
        volume_vs_avg = current_volume / avg_volume if avg_volume > 0 else 1.0

        # Trend: count consecutive declining/rising short-ratio days
        consecutive_decline, consecutive_rise = self._consecutive_trend(ratios)

        # Determine trend label
        if consecutive_decline >= 3:
            trend = TREND_DECLINING
        elif consecutive_rise >= 3:
            trend = TREND_RISING
        else:
            trend = TREND_STABLE

        # Anomaly detection
        anomaly = False
        threshold = self.std_dev_threshold

        accumulation_anomaly = ratio_deviation < -threshold
        distribution_anomaly = ratio_deviation > threshold
        volume_surge = volume_vs_avg > 2.0
        sustained_decline = consecutive_decline >= 5

        if accumulation_anomaly or distribution_anomaly or volume_surge or sustained_decline:
            anomaly = True

        # ------ Score calculation (0-100) ------
        # Baseline: 30 (neutral center)
        score = 30.0

        # Deviation component (-2 std = +40, +2 std = -20)
        # Negative deviation (low short ratio) is bullish
        deviation_component = -ratio_deviation * 15.0
        deviation_component = max(-20.0, min(40.0, deviation_component))
        score += deviation_component

        # Trend component
        if trend == TREND_DECLINING:
            score += min(consecutive_decline * 3.0, 15.0)
        elif trend == TREND_RISING:
            score -= min(consecutive_rise * 3.0, 15.0)

        # Sustained accumulation bonus
        if sustained_decline:
            score += 10.0

        # Anomaly + volume surge combo bonus
        if volume_surge and accumulation_anomaly:
            score += 15.0
        elif volume_surge and distribution_anomaly:
            score -= 10.0

        score = round(max(0.0, min(100.0, score)), 2)

        # Direction
        if score >= 55:
            direction = DIRECTION_ACCUMULATION
        elif score <= 25:
            direction = DIRECTION_DISTRIBUTION
        else:
            direction = DIRECTION_NEUTRAL

        return {
            'ticker': ticker,
            'darkpool_signal_score': score,
            'darkpool_signal_direction': direction,
            'darkpool_short_ratio_current': round(float(current_ratio), 4),
            'darkpool_short_ratio_avg': round(float(avg_ratio), 4),
            'darkpool_short_ratio_deviation': round(float(ratio_deviation), 4),
            'darkpool_volume_vs_avg': round(float(volume_vs_avg), 4),
            'darkpool_trend': trend,
            'darkpool_consecutive_decline_days': consecutive_decline,
            'darkpool_anomaly_detected': anomaly,
        }

    @staticmethod
    def _consecutive_trend(series: pd.Series) -> tuple:
        """
        Count consecutive declining and rising days from the end of *series*.

        Returns:
            (consecutive_decline_count, consecutive_rise_count)
        """
        if len(series) < 2:
            return 0, 0

        diffs = series.diff().dropna()
        decline = 0
        rise = 0

        # Walk backward from most recent diff
        for val in reversed(diffs.values):
            if val < 0:
                decline += 1
            else:
                break

        for val in reversed(diffs.values):
            if val > 0:
                rise += 1
            else:
                break

        return decline, rise

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _neutral_result(ticker: str, error: str = None) -> Dict:
        """Return a neutral / fallback result dict."""
        result = {
            'ticker': ticker,
            'darkpool_signal_score': 30.0,
            'darkpool_signal_direction': DIRECTION_NEUTRAL,
            'darkpool_short_ratio_current': 0.0,
            'darkpool_short_ratio_avg': 0.0,
            'darkpool_short_ratio_deviation': 0.0,
            'darkpool_volume_vs_avg': 0.0,
            'darkpool_trend': TREND_STABLE,
            'darkpool_consecutive_decline_days': 0,
            'darkpool_anomaly_detected': False,
        }
        if error:
            result['error'] = error
        return result
