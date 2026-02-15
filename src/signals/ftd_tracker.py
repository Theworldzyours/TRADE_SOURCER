"""
Fail-to-Deliver & Short Interest tracker for Trade Sourcer

Fetches SEC FTD data and FINRA short sale volume to detect
squeeze setups, covering patterns, and delivery pressure signals.
"""
import io
import csv
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

import requests

from ..utils.logger import get_logger

logger = get_logger()

# SEC FTD file URL patterns
SEC_FTD_BASE_URL = "https://www.sec.gov/files/data/fails-deliver-data"
SEC_FTD_FIRST_HALF = "cnsfails{yyyymm}a.zip"
SEC_FTD_SECOND_HALF = "cnsfails{yyyymm}b.zip"

# FINRA short sale volume (daily, publicly available)
FINRA_SHORT_VOLUME_URL = (
    "https://cdn.finra.org/equity/regsho/daily/"
    "CNMSshvol{yyyymmdd}.txt"
)

# SEC requests require a User-Agent header
SEC_HEADERS = {
    "User-Agent": "TradeSourcer/1.0 (research@tradesourcer.local)",
    "Accept-Encoding": "gzip, deflate",
}

# FTD CSV columns (pipe-delimited)
FTD_COLUMNS = [
    "settlement_date",
    "cusip",
    "symbol",
    "quantity",
    "description",
    "price",
]

# Threshold list: 13+ consecutive settlement days of elevated FTDs
THRESHOLD_LIST_DAYS = 13


class FTDShortTracker:
    """
    Tracks Fail-to-Deliver data from the SEC and short sale volume
    from FINRA to detect squeeze setups and delivery pressure.
    """

    def __init__(self, config: Dict = None):
        """
        Initialize FTD/Short tracker.

        Args:
            config: Configuration dictionary with optional keys:
                - cache_dir: path for cached downloads
                - ftd_spike_threshold: multiplier for spike detection (default 5)
                - lookback_periods: number of SEC periods to fetch (default 2)
                - short_volume_days: days of FINRA data to fetch (default 10)
                - request_timeout: HTTP timeout in seconds (default 30)
        """
        self.config = config or {}
        self.cache_dir = Path(
            self.config.get("cache_dir", "data/cache/ftd")
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.spike_threshold = self.config.get("ftd_spike_threshold", 5.0)
        self.lookback_periods = self.config.get("lookback_periods", 2)
        self.short_volume_days = self.config.get("short_volume_days", 10)
        self.request_timeout = self.config.get("request_timeout", 30)

        # In-memory caches populated by fetch methods
        self._ftd_cache: Dict[str, List[Dict]] = defaultdict(list)
        self._short_volume_cache: Dict[str, List[Dict]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_stock(self, ticker: str) -> Dict:
        """
        Main entry point -- analyze FTD and short interest for a single ticker.

        Args:
            ticker: Stock ticker symbol (e.g. 'GME')

        Returns:
            Signal dictionary (see module docstring for schema)
        """
        ticker = ticker.upper()
        try:
            self._ensure_data_loaded()
            return self._build_signal(ticker)
        except Exception as e:
            logger.error(f"FTD analysis failed for {ticker}: {e}")
            return self._neutral_result(ticker)

    def analyze_batch(self, tickers: List[str]) -> Dict[str, Dict]:
        """
        Analyze multiple tickers -- fetches data once, filters per ticker.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dict mapping ticker -> signal dictionary
        """
        tickers = [t.upper() for t in tickers]
        try:
            self._ensure_data_loaded()
        except Exception as e:
            logger.error(f"FTD batch data load failed: {e}")
            return {t: self._neutral_result(t) for t in tickers}

        return {t: self._build_signal(t) for t in tickers}

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    def _ensure_data_loaded(self) -> None:
        """Load FTD and short volume data if not already cached."""
        if not self._ftd_cache:
            self._load_ftd_data()
        if not self._short_volume_cache:
            self._load_short_volume_data()

    def _load_ftd_data(self) -> None:
        """Download and parse SEC FTD zip files for recent periods."""
        periods = self._get_ftd_periods(self.lookback_periods)
        for yyyymm, half in periods:
            try:
                rows = self._fetch_ftd_period(yyyymm, half)
                for row in rows:
                    symbol = row.get("symbol", "").strip().upper()
                    if symbol:
                        self._ftd_cache[symbol].append(row)
            except Exception as e:
                logger.warning(f"Failed to load FTD {yyyymm}{half}: {e}")

        logger.info(
            f"FTD data loaded: {sum(len(v) for v in self._ftd_cache.values())} "
            f"records across {len(self._ftd_cache)} symbols"
        )

    def _fetch_ftd_period(self, yyyymm: str, half: str) -> List[Dict]:
        """
        Fetch and parse a single SEC FTD zip file.

        Args:
            yyyymm: Year-month string (e.g. '202601')
            half: 'a' (first half) or 'b' (second half)

        Returns:
            List of parsed FTD row dicts
        """
        filename = f"cnsfails{yyyymm}{half}.zip"
        cache_path = self.cache_dir / filename

        # Use disk cache if available
        if cache_path.exists():
            logger.debug(f"FTD cache hit: {filename}")
            return self._parse_ftd_zip(cache_path.read_bytes())

        url = f"{SEC_FTD_BASE_URL}/{filename}"
        logger.info(f"Downloading FTD data: {url}")

        resp = requests.get(
            url, headers=SEC_HEADERS, timeout=self.request_timeout
        )
        resp.raise_for_status()

        # Cache to disk
        cache_path.write_bytes(resp.content)
        return self._parse_ftd_zip(resp.content)

    def _parse_ftd_zip(self, zip_bytes: bytes) -> List[Dict]:
        """
        Extract and parse the pipe-delimited CSV inside an FTD zip.

        Args:
            zip_bytes: Raw zip file bytes

        Returns:
            List of row dicts with keys from FTD_COLUMNS
        """
        rows: List[Dict] = []
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            for name in zf.namelist():
                with zf.open(name) as f:
                    text = f.read().decode("latin-1")
                    reader = csv.reader(io.StringIO(text), delimiter="|")
                    header_skipped = False
                    for line in reader:
                        if not header_skipped:
                            header_skipped = True
                            continue
                        if len(line) < 6:
                            continue
                        try:
                            quantity = int(line[3].strip()) if line[3].strip() else 0
                            price_str = line[5].strip().replace("$", "").replace(",", "")
                            price = float(price_str) if price_str else 0.0
                            rows.append({
                                "settlement_date": line[0].strip(),
                                "cusip": line[1].strip(),
                                "symbol": line[2].strip(),
                                "quantity": quantity,
                                "description": line[4].strip(),
                                "price": price,
                            })
                        except (ValueError, IndexError) as e:
                            logger.debug(f"Skipping malformed FTD row: {e}")
        return rows

    def _load_short_volume_data(self) -> None:
        """Download FINRA short sale volume files for recent trading days."""
        dates = self._get_recent_trading_dates(self.short_volume_days)
        loaded = 0
        for dt in dates:
            try:
                rows = self._fetch_short_volume(dt)
                for row in rows:
                    symbol = row.get("symbol", "").strip().upper()
                    if symbol:
                        self._short_volume_cache[symbol].append(row)
                loaded += 1
            except Exception as e:
                logger.debug(f"Short volume unavailable for {dt}: {e}")

        logger.info(
            f"Short volume loaded: {loaded} days, "
            f"{sum(len(v) for v in self._short_volume_cache.values())} records"
        )

    def _fetch_short_volume(self, date: datetime) -> List[Dict]:
        """
        Fetch and parse a single FINRA short sale volume file.

        Args:
            date: Trading date

        Returns:
            List of row dicts with keys: date, symbol, short_volume,
            short_exempt_volume, total_volume
        """
        yyyymmdd = date.strftime("%Y%m%d")
        filename = f"CNMSshvol{yyyymmdd}.txt"
        cache_path = self.cache_dir / filename

        if cache_path.exists():
            text = cache_path.read_text(encoding="latin-1")
        else:
            url = FINRA_SHORT_VOLUME_URL.replace("{yyyymmdd}", yyyymmdd)
            resp = requests.get(
                url, headers=SEC_HEADERS, timeout=self.request_timeout
            )
            resp.raise_for_status()
            text = resp.text
            cache_path.write_text(text, encoding="latin-1")

        rows: List[Dict] = []
        for line in text.strip().splitlines():
            if line.startswith("Date") or line.startswith("date"):
                continue
            parts = line.split("|")
            if len(parts) < 5:
                continue
            try:
                rows.append({
                    "date": parts[0].strip(),
                    "symbol": parts[1].strip(),
                    "short_volume": int(parts[2].strip()),
                    "short_exempt_volume": int(parts[3].strip()),
                    "total_volume": int(parts[4].strip()),
                })
            except (ValueError, IndexError):
                continue
        return rows

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def _build_signal(self, ticker: str) -> Dict:
        """
        Build complete FTD/short signal for a single ticker.

        Args:
            ticker: Uppercased ticker symbol

        Returns:
            Signal dictionary
        """
        ftd_records = self._ftd_cache.get(ticker, [])
        short_records = self._short_volume_cache.get(ticker, [])

        ftd_analysis = self._analyze_ftd(ftd_records)
        short_analysis = self._analyze_short_interest(short_records)

        score = self._calculate_score(ftd_analysis, short_analysis)
        direction = self._determine_direction(ftd_analysis, short_analysis, score)
        squeeze = self._detect_squeeze_potential(ftd_analysis, short_analysis)

        return {
            "ftd_signal_score": round(score, 2),
            "ftd_signal_direction": direction,
            "ftd_current_quantity": ftd_analysis["current"],
            "ftd_average_quantity": round(ftd_analysis["average"], 2),
            "ftd_spike_ratio": round(ftd_analysis["spike_ratio"], 2),
            "ftd_trend": ftd_analysis["trend"],
            "ftd_on_threshold_list": ftd_analysis["on_threshold_list"],
            "short_ratio_trend": short_analysis["ratio_trend"],
            "short_estimated_days_to_cover": round(
                short_analysis["days_to_cover"], 2
            ),
            "short_squeeze_potential": squeeze,
        }

    def _analyze_ftd(self, records: List[Dict]) -> Dict:
        """
        Analyze FTD pattern for a ticker.

        Args:
            records: List of FTD row dicts for one symbol

        Returns:
            Dict with current, average, spike_ratio, trend, on_threshold_list
        """
        if not records:
            return {
                "current": 0,
                "average": 0.0,
                "spike_ratio": 0.0,
                "trend": "stable",
                "on_threshold_list": False,
            }

        # Sort by settlement date ascending
        sorted_recs = sorted(records, key=lambda r: r["settlement_date"])
        quantities = [r["quantity"] for r in sorted_recs]

        current = quantities[-1]
        average = sum(quantities) / len(quantities) if quantities else 0.0
        spike_ratio = current / average if average > 0 else 0.0

        # Trend: compare second half to first half
        trend = self._compute_trend(quantities)

        # Threshold list: 13+ consecutive days with quantity > 10000 shares
        on_threshold = self._check_threshold_list(quantities)

        return {
            "current": current,
            "average": average,
            "spike_ratio": spike_ratio,
            "trend": trend,
            "on_threshold_list": on_threshold,
        }

    def _analyze_short_interest(self, records: List[Dict]) -> Dict:
        """
        Analyze short sale volume patterns.

        Args:
            records: List of short volume row dicts for one symbol

        Returns:
            Dict with ratio_trend and days_to_cover
        """
        if not records:
            return {
                "ratio_trend": "neutral",
                "days_to_cover": 0.0,
            }

        # Sort by date ascending
        sorted_recs = sorted(records, key=lambda r: r["date"])

        # Short ratios per day
        ratios = []
        for r in sorted_recs:
            total = r.get("total_volume", 0)
            short = r.get("short_volume", 0)
            if total > 0:
                ratios.append(short / total)

        ratio_trend = self._compute_trend_from_values(ratios)

        # Estimated days to cover: avg short volume / avg total volume
        avg_short = (
            sum(r.get("short_volume", 0) for r in sorted_recs) / len(sorted_recs)
            if sorted_recs
            else 0
        )
        avg_total = (
            sum(r.get("total_volume", 0) for r in sorted_recs) / len(sorted_recs)
            if sorted_recs
            else 0
        )

        # Rough proxy: if 50%+ of daily volume is short, days_to_cover rises
        # Simple model: accumulated_short / (avg_total - avg_short)
        net_cover_rate = avg_total - avg_short
        if net_cover_rate > 0 and avg_short > 0:
            days_to_cover = avg_short / net_cover_rate
        else:
            days_to_cover = 0.0

        return {
            "ratio_trend": ratio_trend,
            "days_to_cover": days_to_cover,
        }

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _calculate_score(self, ftd: Dict, short: Dict) -> float:
        """
        Score FTD/short signals on 0-100 scale.

        Scoring bands:
          80-100: FTD spike 10x+ AND high short interest (squeeze potential)
          60-80:  FTD spike 5x+
          40-60:  Elevated FTDs + declining short ratio (covering)
          20-40:  Normal FTD levels
          0-20:   Low/no FTDs
        """
        score = 10.0  # baseline

        spike = ftd["spike_ratio"]
        on_threshold = ftd["on_threshold_list"]
        trend = ftd["trend"]
        dtc = short["days_to_cover"]
        ratio_trend = short["ratio_trend"]

        # FTD spike contribution
        if spike >= 10.0:
            score += 50
        elif spike >= 5.0:
            score += 35
        elif spike >= 2.0:
            score += 15
        elif spike >= 1.0:
            score += 5

        # Threshold list = persistent delivery failures
        if on_threshold:
            score += 15

        # FTD trend
        if trend == "increasing":
            score += 10
        elif trend == "decreasing":
            score -= 5

        # Short interest / days to cover
        if dtc >= 5.0:
            score += 15
        elif dtc >= 3.0:
            score += 10
        elif dtc >= 1.5:
            score += 5

        # Short ratio trend
        if ratio_trend == "increasing":
            score += 5
        elif ratio_trend == "decreasing":
            # Covering in progress -- moderate signal
            score += 0

        return max(0.0, min(100.0, score))

    def _determine_direction(
        self, ftd: Dict, short: Dict, score: float
    ) -> str:
        """
        Classify the signal direction.

        Returns one of:
          'squeeze_potential', 'covering', 'pressure', 'neutral'
        """
        squeeze = self._detect_squeeze_potential(ftd, short)
        if squeeze and score >= 70:
            return "squeeze_potential"

        if short["ratio_trend"] == "decreasing" and ftd["trend"] == "decreasing":
            return "covering"

        if ftd["spike_ratio"] >= self.spike_threshold or ftd["on_threshold_list"]:
            return "pressure"

        return "neutral"

    def _detect_squeeze_potential(self, ftd: Dict, short: Dict) -> bool:
        """
        Detect squeeze setup:
          - High FTDs (spike >= 5x)
          - High short ratio (days_to_cover >= 2)
          - Short ratio declining (shorts starting to cover)
        """
        high_ftd = ftd["spike_ratio"] >= self.spike_threshold
        high_short = short["days_to_cover"] >= 2.0
        covering = short["ratio_trend"] == "decreasing"

        return high_ftd and high_short and covering

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _compute_trend(self, quantities: List[int]) -> str:
        """Determine trend from a list of quantities (oldest to newest)."""
        if len(quantities) < 2:
            return "stable"
        return self._compute_trend_from_values(
            [float(q) for q in quantities]
        )

    @staticmethod
    def _compute_trend_from_values(values: List[float]) -> str:
        """
        Determine trend direction from a list of float values.

        Splits into first half and second half, compares averages.
        >20% change = trending, otherwise stable.
        """
        if len(values) < 2:
            return "stable"

        mid = len(values) // 2
        first_half = values[:mid] if mid > 0 else values[:1]
        second_half = values[mid:]

        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)

        if avg_first == 0:
            return "increasing" if avg_second > 0 else "stable"

        change = (avg_second - avg_first) / avg_first
        if change > 0.20:
            return "increasing"
        elif change < -0.20:
            return "decreasing"
        return "stable"

    @staticmethod
    def _check_threshold_list(quantities: List[int]) -> bool:
        """
        Check if the stock qualifies for SEC Threshold List.

        Requires 13+ consecutive settlement days with FTD quantity >= 10000.
        """
        if len(quantities) < THRESHOLD_LIST_DAYS:
            return False

        consecutive = 0
        for q in quantities:
            if q >= 10000:
                consecutive += 1
                if consecutive >= THRESHOLD_LIST_DAYS:
                    return True
            else:
                consecutive = 0
        return False

    @staticmethod
    def _get_ftd_periods(lookback: int) -> List[tuple]:
        """
        Generate (yyyymm, half) tuples for recent FTD periods.

        SEC data has ~30-day delay, so we look back further.
        Each month has two halves: 'a' (1st-15th) and 'b' (16th-end).

        Args:
            lookback: Number of half-month periods to fetch

        Returns:
            List of (yyyymm_str, half_letter) tuples
        """
        periods = []
        # Start 2 months back to account for SEC delay
        ref = datetime.now() - timedelta(days=60)

        for i in range(lookback * 2):
            dt = ref - timedelta(days=i * 15)
            yyyymm = dt.strftime("%Y%m")
            # Alternate between 'b' and 'a'
            half = "b" if i % 2 == 0 else "a"
            pair = (yyyymm, half)
            if pair not in periods:
                periods.append(pair)
            if len(periods) >= lookback:
                break

        return periods

    @staticmethod
    def _get_recent_trading_dates(days: int) -> List[datetime]:
        """
        Generate recent business dates (Mon-Fri) for FINRA data.

        Args:
            days: Number of trading days to look back

        Returns:
            List of datetime objects (most recent first)
        """
        dates = []
        dt = datetime.now() - timedelta(days=1)  # start from yesterday
        while len(dates) < days:
            if dt.weekday() < 5:  # Mon=0 ... Fri=4
                dates.append(dt)
            dt -= timedelta(days=1)
        return dates

    def _neutral_result(self, ticker: str = "") -> Dict:
        """Return a neutral/default signal dict."""
        return {
            "ftd_signal_score": 10.0,
            "ftd_signal_direction": "neutral",
            "ftd_current_quantity": 0,
            "ftd_average_quantity": 0.0,
            "ftd_spike_ratio": 0.0,
            "ftd_trend": "stable",
            "ftd_on_threshold_list": False,
            "short_ratio_trend": "neutral",
            "short_estimated_days_to_cover": 0.0,
            "short_squeeze_potential": False,
        }
