"""
Unusual Options Flow Scanner for Trade Sourcer

Detects unusual options activity via the Tradier API and classifies
signals as bullish, bearish, or neutral with a 0-100 conviction score.
"""
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from ..utils.logger import get_logger

logger = get_logger()

try:
    import requests
except ImportError:
    requests = None
    logger.warning("requests library not installed — options flow scanner disabled")

# Thresholds
UNUSUAL_VOL_OI_RATIO = 3.0
VERY_UNUSUAL_VOL_OI_RATIO = 5.0
NEAR_TERM_DAYS = 14
MAX_EXPIRATIONS = 4
SWEEP_MIN_STRIKES = 3
DEFAULT_RATE_LIMIT_DELAY = 0.5  # seconds between API calls


class OptionsFlowScanner:
    """
    Scan options chains for unusual activity and generate
    bullish/bearish/neutral signal scores.
    """

    BASE_URL = "https://api.tradier.com/v1/markets/options"

    def __init__(self, config: Dict = None):
        """
        Initialize scanner.

        Args:
            config: Configuration dictionary. Reads 'tradier_api_key' or
                    falls back to TRADIER_API_KEY env var.
        """
        self.config = config or {}
        self.api_key = self.config.get(
            'tradier_api_key', os.getenv('TRADIER_API_KEY', '')
        )
        self.rate_limit_delay = self.config.get(
            'rate_limit_delay', DEFAULT_RATE_LIMIT_DELAY
        )
        if not self.api_key:
            logger.warning(
                "TRADIER_API_KEY not set — options flow scanner will return neutral scores"
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_stock(self, ticker: str) -> Dict:
        """
        Main entry point. Analyze options flow for a single ticker.

        Args:
            ticker: Stock ticker symbol (e.g. 'AAPL')

        Returns:
            Dictionary with options signal data.
        """
        if not self.api_key or requests is None:
            return self._neutral_result()

        try:
            expirations = self._get_expirations(ticker)
            if not expirations:
                logger.info(f"{ticker}: no options expirations found")
                return self._neutral_result()

            # Limit to nearest MAX_EXPIRATIONS
            expirations = expirations[:MAX_EXPIRATIONS]

            all_contracts: List[Dict] = []
            for exp in expirations:
                time.sleep(self.rate_limit_delay)
                chain = self._get_chain(ticker, exp)
                if chain:
                    for contract in chain:
                        contract['expiration'] = exp
                    all_contracts.extend(chain)

            if not all_contracts:
                logger.info(f"{ticker}: empty options chain data")
                return self._neutral_result()

            return self._analyze_contracts(all_contracts)

        except Exception as e:
            logger.error(f"Options flow error for {ticker}: {e}")
            return self._neutral_result()

    def analyze_batch(self, tickers: List[str]) -> Dict[str, Dict]:
        """
        Analyze multiple tickers with rate limiting.

        Args:
            tickers: List of ticker symbols.

        Returns:
            Dict mapping ticker -> options signal data.
        """
        results = {}
        for ticker in tickers:
            results[ticker] = self.analyze_stock(ticker)
            time.sleep(self.rate_limit_delay)
        return results

    # ------------------------------------------------------------------
    # Tradier API helpers
    # ------------------------------------------------------------------

    def _headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/json',
        }

    def _get_expirations(self, ticker: str) -> List[str]:
        """Fetch available expiration dates for *ticker*."""
        url = f"{self.BASE_URL}/expirations"
        params = {'symbol': ticker, 'includeAllRoots': 'true'}
        try:
            resp = requests.get(url, headers=self._headers(), params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            dates = data.get('expirations', {})
            if dates is None:
                return []
            date_list = dates.get('date', [])
            if isinstance(date_list, str):
                date_list = [date_list]
            return sorted(date_list)
        except (requests.RequestException, ValueError, KeyError) as e:
            logger.error(f"Failed to fetch expirations for {ticker}: {e}")
            return []

    def _get_chain(self, ticker: str, expiration: str) -> List[Dict]:
        """Fetch the full options chain for one expiration."""
        url = f"{self.BASE_URL}/chains"
        params = {'symbol': ticker, 'expiration': expiration, 'greeks': 'false'}
        try:
            resp = requests.get(url, headers=self._headers(), params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            options = data.get('options', {})
            if options is None:
                return []
            option_list = options.get('option', [])
            if isinstance(option_list, dict):
                option_list = [option_list]
            return option_list
        except (requests.RequestException, ValueError, KeyError) as e:
            logger.error(f"Failed to fetch chain {ticker} {expiration}: {e}")
            return []

    # ------------------------------------------------------------------
    # Analysis engine
    # ------------------------------------------------------------------

    def _analyze_contracts(self, contracts: List[Dict]) -> Dict:
        """
        Crunch an aggregated options chain and produce a signal dict.
        """
        total_call_vol = 0
        total_put_vol = 0
        max_vol_oi_ratio = 0.0
        unusual_contracts: List[Dict] = []
        estimated_premium = 0.0

        # Per-expiration, per-side strike counts for sweep detection
        sweep_tracker: Dict[str, Dict[str, int]] = {}

        now = datetime.utcnow().date()

        for c in contracts:
            option_type = c.get('option_type', '').lower()  # 'call' or 'put'
            volume = c.get('volume', 0) or 0
            open_interest = c.get('open_interest', 0) or 0
            strike = c.get('strike', 0)
            last_price = c.get('last', 0) or 0
            expiration = c.get('expiration', '')

            # Accumulate totals
            if option_type == 'call':
                total_call_vol += volume
            elif option_type == 'put':
                total_put_vol += volume

            # Volume / OI ratio
            if open_interest > 0 and volume > 0:
                ratio = volume / open_interest
            else:
                ratio = 0.0

            if ratio > max_vol_oi_ratio:
                max_vol_oi_ratio = ratio

            # Unusual detection
            is_unusual = ratio >= UNUSUAL_VOL_OI_RATIO
            is_very_unusual = ratio >= VERY_UNUSUAL_VOL_OI_RATIO

            if is_unusual:
                contract_premium = volume * last_price * 100  # each contract = 100 shares
                estimated_premium += contract_premium
                unusual_contracts.append({
                    'strike': strike,
                    'expiry': expiration,
                    'type': option_type,
                    'volume': volume,
                    'oi': open_interest,
                    'ratio': round(ratio, 2),
                    'premium': round(contract_premium, 2),
                    'very_unusual': is_very_unusual,
                })

            # Sweep tracking
            if is_unusual:
                key = f"{expiration}|{option_type}"
                sweep_tracker.setdefault(key, {'strikes': 0, 'volume': 0})
                sweep_tracker[key]['strikes'] += 1
                sweep_tracker[key]['volume'] += volume

        # Detect sweeps (unusual activity on 3+ strikes, same side, same expiry)
        call_sweep = False
        put_sweep = False
        for key, info in sweep_tracker.items():
            if info['strikes'] >= SWEEP_MIN_STRIKES:
                if 'call' in key:
                    call_sweep = True
                elif 'put' in key:
                    put_sweep = True

        # Put/call ratio
        if total_call_vol > 0:
            put_call_ratio = total_put_vol / total_call_vol
        else:
            put_call_ratio = 1.0  # neutral when no call volume

        # Classify direction
        direction = self._classify_direction(
            put_call_ratio, unusual_contracts, call_sweep, put_sweep
        )

        # Near-term flag (any unusual contract expiring within NEAR_TERM_DAYS)
        near_term_unusual = False
        for uc in unusual_contracts:
            try:
                exp_date = datetime.strptime(uc['expiry'], '%Y-%m-%d').date()
                if (exp_date - now).days <= NEAR_TERM_DAYS:
                    near_term_unusual = True
                    break
            except (ValueError, TypeError):
                pass

        # Score
        score = self._calculate_score(
            direction=direction,
            max_ratio=max_vol_oi_ratio,
            unusual_contracts=unusual_contracts,
            estimated_premium=estimated_premium,
            near_term=near_term_unusual,
            call_sweep=call_sweep,
            put_sweep=put_sweep,
        )

        # Top 5 notable trades by ratio
        notable = sorted(unusual_contracts, key=lambda x: x['ratio'], reverse=True)[:5]
        # Strip internal keys from notable output
        notable_clean = [
            {k: v for k, v in t.items() if k != 'very_unusual'} for t in notable
        ]

        return {
            'options_signal_score': round(score, 2),
            'options_signal_direction': direction,
            'options_put_call_ratio': round(put_call_ratio, 4),
            'options_unusual_activity': len(unusual_contracts) > 0,
            'options_total_call_volume': total_call_vol,
            'options_total_put_volume': total_put_vol,
            'options_max_volume_oi_ratio': round(max_vol_oi_ratio, 2),
            'options_notable_trades': notable_clean,
            'options_estimated_premium': round(estimated_premium, 2),
        }

    def _classify_direction(
        self,
        put_call_ratio: float,
        unusual_contracts: List[Dict],
        call_sweep: bool,
        put_sweep: bool,
    ) -> str:
        """Classify overall flow as bullish / bearish / neutral."""
        bullish_points = 0
        bearish_points = 0

        # Put/call ratio
        if put_call_ratio < 0.7:
            bullish_points += 2
        elif put_call_ratio < 0.9:
            bullish_points += 1
        elif put_call_ratio > 1.3:
            bearish_points += 2
        elif put_call_ratio > 1.1:
            bearish_points += 1

        # Unusual contract bias
        unusual_calls = sum(1 for u in unusual_contracts if u['type'] == 'call')
        unusual_puts = sum(1 for u in unusual_contracts if u['type'] == 'put')
        if unusual_calls > unusual_puts * 1.5:
            bullish_points += 2
        elif unusual_calls > unusual_puts:
            bullish_points += 1
        elif unusual_puts > unusual_calls * 1.5:
            bearish_points += 2
        elif unusual_puts > unusual_calls:
            bearish_points += 1

        # Sweeps
        if call_sweep:
            bullish_points += 2
        if put_sweep:
            bearish_points += 2

        if bullish_points > bearish_points + 1:
            return 'bullish'
        elif bearish_points > bullish_points + 1:
            return 'bearish'
        return 'neutral'

    def _calculate_score(
        self,
        direction: str,
        max_ratio: float,
        unusual_contracts: List[Dict],
        estimated_premium: float,
        near_term: bool,
        call_sweep: bool,
        put_sweep: bool,
    ) -> float:
        """
        Score 0-100 where higher = more bullish conviction.

        Very unusual call (>5x OI, near-term): 80-100
        Unusual call (>3x OI):                 60-80
        Moderately bullish:                     40-60
        Neutral:                                30-50
        Bearish:                                 0-30
        """
        # Base score by direction
        if direction == 'bullish':
            score = 60.0
        elif direction == 'bearish':
            score = 20.0
        else:
            score = 40.0

        # Intensity from max vol/OI ratio
        if max_ratio >= VERY_UNUSUAL_VOL_OI_RATIO:
            score += 15.0
        elif max_ratio >= UNUSUAL_VOL_OI_RATIO:
            score += 8.0

        # Very unusual contracts count bonus
        very_unusual_count = sum(1 for u in unusual_contracts if u.get('very_unusual'))
        score += min(very_unusual_count * 3.0, 10.0)

        # Sweep bonus
        if direction == 'bullish' and call_sweep:
            score += 8.0
        elif direction == 'bearish' and put_sweep:
            score -= 8.0  # pushes bearish score lower

        # Premium bonus
        if estimated_premium > 5_000_000:
            score += 20.0
        elif estimated_premium > 1_000_000:
            score += 10.0

        # Near-term expiry bonus (higher conviction)
        if near_term:
            score += 10.0

        # Invert for bearish (lower score = more bearish)
        if direction == 'bearish':
            score = max(0.0, score)
        else:
            score = min(100.0, score)

        return max(0.0, min(100.0, score))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _neutral_result() -> Dict:
        """Return a neutral / empty result when data is unavailable."""
        return {
            'options_signal_score': 40.0,
            'options_signal_direction': 'neutral',
            'options_put_call_ratio': 1.0,
            'options_unusual_activity': False,
            'options_total_call_volume': 0,
            'options_total_put_volume': 0,
            'options_max_volume_oi_ratio': 0.0,
            'options_notable_trades': [],
            'options_estimated_premium': 0.0,
        }
