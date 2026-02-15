"""
SEC Insider Trading Detection Signal Detector

Fetches Form 4 filings from SEC EDGAR, detects cluster buys,
and scores insider activity to generate bullish/bearish signals.
"""
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from ..utils.logger import get_logger

logger = get_logger()

# Role weights for scoring insider significance.
# Order matters: longer / more-specific patterns are checked first so that
# e.g. "Director" (0.5) is not eclipsed by the "CTO" substring inside
# "DIRECTOR".  Tuples of (pattern, weight) checked in sequence.
ROLE_WEIGHTS = [
    ('Chief Executive Officer', 1.0),
    ('Chief Financial Officer', 0.9),
    ('Chief Operating Officer', 0.8),
    ('Chief Technology Officer', 0.8),
    ('10 Percent Owner', 0.7),
    ('Vice President', 0.6),
    ('10% Owner', 0.7),
    ('Director', 0.5),
    ('CEO', 1.0),
    ('CFO', 0.9),
    ('COO', 0.8),
    ('CTO', 0.8),
    ('SVP', 0.6),
    ('EVP', 0.6),
    ('VP', 0.6),
]

# Purchase size thresholds and weights
SIZE_THRESHOLDS = [
    (1_000_000, 1.0),
    (500_000, 0.8),
    (100_000, 0.6),
    (50_000, 0.4),
    (0, 0.2),
]

# Cluster detection parameters
CLUSTER_WINDOW_DAYS = 14
CLUSTER_STRONG_MIN = 3
CLUSTER_MODERATE_MIN = 2

# Scoring bonuses
CLUSTER_STRONG_BONUS = 30
CLUSTER_MODERATE_BONUS = 15
PRICE_DIP_BONUS = 10
PRICE_DIP_THRESHOLD = 0.10  # 10% off 52-week high


def _check_edgartools_available():
    """Check if edgartools is importable. Returns (module, error_msg)."""
    try:
        import edgar  # noqa: F811
        return edgar, None
    except ImportError:
        return None, "edgartools not installed (pip install edgartools)"


def _get_role_weight(role_title: str) -> float:
    """
    Map an insider's role/title string to a weight.

    Args:
        role_title: Raw role string from SEC filing

    Returns:
        Weight between 0.0 and 1.0
    """
    if not role_title:
        return 0.3  # Unknown role, low weight

    role_upper = role_title.upper()
    for key, weight in ROLE_WEIGHTS:
        if key.upper() in role_upper:
            return weight
    return 0.3


def _get_size_weight(value: float) -> float:
    """
    Map a transaction dollar value to a weight.

    Args:
        value: Absolute dollar value of the transaction

    Returns:
        Weight between 0.0 and 1.0
    """
    abs_value = abs(value) if value else 0
    for threshold, weight in SIZE_THRESHOLDS:
        if abs_value >= threshold:
            return weight
    return 0.2


def _is_planned_sale(transaction: Dict) -> bool:
    """
    Heuristic to detect 10b5-1 planned sales.

    Args:
        transaction: Parsed transaction dict

    Returns:
        True if the transaction appears to be a pre-planned 10b5-1 sale
    """
    footnotes = str(transaction.get('footnotes', '')).lower()
    code = str(transaction.get('transaction_code', '')).upper()
    if '10b5-1' in footnotes or 'rule 10b5' in footnotes:
        return True
    # Code 'S' with disposition + footnote mentioning "plan" or "automatic"
    if code == 'S' and ('plan' in footnotes or 'automatic' in footnotes):
        return True
    return False


def _is_routine_small_sale(transaction: Dict) -> bool:
    """
    Filter out routine small sales that are noise.

    Args:
        transaction: Parsed transaction dict

    Returns:
        True if the transaction is a routine small sale to ignore
    """
    if transaction.get('direction') != 'sell':
        return False
    value = abs(transaction.get('value', 0))
    return value < 25_000


def _neutral_result(error: Optional[str] = None) -> Dict:
    """Return a neutral/empty signal result."""
    result = {
        'insider_signal_score': 0.0,
        'insider_signal_direction': 'neutral',
        'insider_transactions': [],
        'insider_cluster_detected': False,
        'insider_cluster_size': 0,
        'insider_total_buy_value': 0.0,
        'insider_total_sell_value': 0.0,
        'insider_net_direction': 'neutral',
        'insider_notable_buyers': [],
    }
    if error:
        result['insider_error'] = error
    return result


class InsiderFlowDetector:
    """
    Detects and scores SEC insider trading activity from Form 4 filings.

    Uses edgartools to fetch EDGAR data, detects cluster buys,
    and produces a 0-100 signal score with direction.
    """

    def __init__(self, config: Dict = None):
        """
        Initialize the insider flow detector.

        Args:
            config: Configuration dictionary with optional overrides:
                - lookback_days (int): How far back to look for filings (default 30)
                - cluster_window_days (int): Window for cluster detection (default 14)
                - rate_limit_delay (float): Seconds between SEC requests (default 0.1)
                - price_dip_threshold (float): Pct off 52wk high for bonus (default 0.10)
        """
        self.config = config or {}
        self.lookback_days = self.config.get('lookback_days', 30)
        self.cluster_window_days = self.config.get('cluster_window_days', CLUSTER_WINDOW_DAYS)
        self.rate_limit_delay = self.config.get('rate_limit_delay', 0.1)
        self.price_dip_threshold = self.config.get('price_dip_threshold', PRICE_DIP_THRESHOLD)
        self._last_request_time = 0.0

    def _rate_limit(self):
        """Enforce SEC rate limiting (max 10 req/sec = 0.1s between requests)."""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = time.monotonic()

    def _fetch_form4_filings(self, ticker: str) -> List[Dict]:
        """
        Fetch recent Form 4 filings for a ticker from SEC EDGAR.

        Args:
            ticker: Stock ticker symbol

        Returns:
            List of parsed transaction dicts
        """
        edgar_mod, err = _check_edgartools_available()
        if edgar_mod is None:
            logger.warning(err)
            return []

        try:
            from edgar import set_identity, Company
            set_identity("tradesourcer@analysis.com")
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to configure edgartools identity: {e}")
            return []

        transactions = []
        cutoff_date = datetime.now() - timedelta(days=self.lookback_days)

        try:
            self._rate_limit()
            company = Company(ticker)
            self._rate_limit()
            filings = company.get_filings(form="4")

            if filings is None:
                logger.debug(f"No Form 4 filings object for {ticker}")
                return []

            # Iterate through recent filings
            for filing in filings:
                try:
                    filing_date = self._parse_filing_date(filing)
                    if filing_date and filing_date < cutoff_date:
                        break  # Filings are reverse-chronological

                    self._rate_limit()
                    parsed = self._parse_form4(filing, ticker)
                    transactions.extend(parsed)
                except (AttributeError, TypeError, ValueError, KeyError) as e:
                    logger.debug(f"Skipping malformed filing for {ticker}: {e}")
                    continue

        except (ConnectionError, TimeoutError, OSError) as e:
            logger.error(f"SEC connection error for {ticker}: {e}")
        except (AttributeError, TypeError, ValueError) as e:
            logger.error(f"Error fetching Form 4 for {ticker}: {e}")

        return transactions

    def _parse_filing_date(self, filing) -> Optional[datetime]:
        """
        Extract the filing date from a filing object.

        Args:
            filing: An edgartools filing object

        Returns:
            datetime or None
        """
        try:
            date_val = getattr(filing, 'filed', None) or getattr(filing, 'date', None)
            if date_val is None:
                return None
            if isinstance(date_val, datetime):
                return date_val
            if isinstance(date_val, str):
                for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%Y%m%d'):
                    try:
                        return datetime.strptime(date_val, fmt)
                    except ValueError:
                        continue
            # If it's a date object (not datetime)
            if hasattr(date_val, 'year'):
                return datetime(date_val.year, date_val.month, date_val.day)
        except (AttributeError, TypeError, ValueError):
            pass
        return None

    def _parse_form4(self, filing, ticker: str) -> List[Dict]:
        """
        Parse a single Form 4 filing into transaction records.

        Args:
            filing: An edgartools filing object
            ticker: Stock ticker for context

        Returns:
            List of transaction dicts
        """
        transactions = []
        filing_date = self._parse_filing_date(filing)

        try:
            # Try to get the structured XML object
            obj = filing.obj() if callable(getattr(filing, 'obj', None)) else filing
        except (AttributeError, TypeError, ValueError, OSError):
            obj = filing

        # Extract reporting owner info
        owner_name = self._extract_owner_name(obj, filing)
        owner_role = self._extract_owner_role(obj, filing)

        # Extract transactions from the filing
        raw_txns = self._extract_transactions(obj, filing)

        for txn in raw_txns:
            try:
                direction = self._determine_direction(txn)
                shares = self._safe_float(txn.get('shares', txn.get('amount', 0)))
                price_per_share = self._safe_float(txn.get('price', txn.get('price_per_share', 0)))
                value = shares * price_per_share if shares and price_per_share else 0

                transaction = {
                    'ticker': ticker,
                    'owner_name': owner_name or 'Unknown',
                    'owner_role': owner_role or 'Unknown',
                    'direction': direction,
                    'shares': shares,
                    'price_per_share': price_per_share,
                    'value': value,
                    'date': filing_date,
                    'transaction_code': txn.get('code', txn.get('transaction_code', '')),
                    'footnotes': txn.get('footnotes', ''),
                }

                # Filter out 10b5-1 planned sales and routine small sales
                if _is_planned_sale(transaction):
                    logger.debug(f"Filtered 10b5-1 planned sale: {owner_name}")
                    continue
                if _is_routine_small_sale(transaction):
                    logger.debug(f"Filtered routine small sale: {owner_name}")
                    continue

                transactions.append(transaction)
            except (TypeError, ValueError, KeyError) as e:
                logger.debug(f"Skipping malformed transaction: {e}")
                continue

        return transactions

    def _extract_owner_name(self, obj, filing) -> Optional[str]:
        """Extract the reporting owner name from a filing object."""
        for attr in ('owner_name', 'reporting_owner', 'owner', 'name'):
            val = getattr(obj, attr, None)
            if val and isinstance(val, str):
                return val
            if val and hasattr(val, 'name'):
                return str(val.name)
        # Fallback: try filing-level attributes
        for attr in ('owner_name', 'reporting_owner'):
            val = getattr(filing, attr, None)
            if val and isinstance(val, str):
                return val
        return None

    def _extract_owner_role(self, obj, filing) -> Optional[str]:
        """Extract the owner's role/title from a filing object."""
        for attr in ('owner_title', 'relationship', 'role', 'title',
                      'officer_title', 'reporting_owner_relationship'):
            val = getattr(obj, attr, None)
            if val and isinstance(val, str):
                return val
            if val and hasattr(val, 'title'):
                return str(val.title)
            if val and hasattr(val, 'officer_title'):
                return str(val.officer_title)
        # Check for relationship flags
        is_director = getattr(obj, 'is_director', None) or getattr(obj, 'isDirector', None)
        is_officer = getattr(obj, 'is_officer', None) or getattr(obj, 'isOfficer', None)
        is_ten_pct = getattr(obj, 'is_ten_percent_owner', None) or getattr(obj, 'isTenPercentOwner', None)
        if is_director:
            return 'Director'
        if is_officer:
            return 'Officer'
        if is_ten_pct:
            return '10% Owner'
        return None

    def _extract_transactions(self, obj, filing) -> List[Dict]:
        """
        Extract raw transaction data from a filing object.

        Returns a list of dicts with keys like 'shares', 'price', 'code'.
        """
        # Try common attribute names for transaction tables
        for attr in ('transactions', 'non_derivative_transactions',
                      'derivative_transactions', 'transaction_list'):
            txns = getattr(obj, attr, None)
            if txns and hasattr(txns, '__iter__'):
                return self._normalize_transactions(txns)

        # If the object itself looks like a single transaction
        if hasattr(obj, 'shares') or hasattr(obj, 'amount'):
            return [self._obj_to_dict(obj)]

        return []

    def _normalize_transactions(self, txns) -> List[Dict]:
        """Convert a list of transaction objects to dicts."""
        result = []
        for txn in txns:
            if isinstance(txn, dict):
                result.append(txn)
            else:
                result.append(self._obj_to_dict(txn))
        return result

    def _obj_to_dict(self, obj) -> Dict:
        """Convert an arbitrary transaction object to a dict."""
        d = {}
        for key in ('shares', 'amount', 'price', 'price_per_share',
                     'code', 'transaction_code', 'acquired_disposed',
                     'acquired_disposed_code', 'footnotes'):
            val = getattr(obj, key, None)
            if val is not None:
                d[key] = val
        return d

    def _determine_direction(self, txn: Dict) -> str:
        """Determine if a transaction is a buy or sell."""
        # Check transaction code: P=Purchase, S=Sale, A=Grant/Award
        code = str(txn.get('code', txn.get('transaction_code', ''))).upper()
        if code == 'P':
            return 'buy'
        if code in ('S', 'D', 'F'):
            return 'sell'

        # Check acquired/disposed flag
        ad = str(txn.get('acquired_disposed', txn.get('acquired_disposed_code', ''))).upper()
        if ad == 'A':
            return 'buy'
        if ad == 'D':
            return 'sell'

        return 'unknown'

    @staticmethod
    def _safe_float(val) -> float:
        """Safely convert a value to float."""
        if val is None:
            return 0.0
        try:
            return float(val)
        except (TypeError, ValueError):
            return 0.0

    def _detect_clusters(self, transactions: List[Dict]) -> Dict:
        """
        Detect cluster buying patterns among insiders.

        Args:
            transactions: List of parsed transaction dicts

        Returns:
            Dict with cluster_detected, cluster_size, cluster_buyers
        """
        buys = [t for t in transactions if t.get('direction') == 'buy' and t.get('date')]

        if len(buys) < 2:
            return {
                'cluster_detected': False,
                'cluster_size': len(buys),
                'cluster_buyers': [],
            }

        # Sort by date
        buys_sorted = sorted(buys, key=lambda t: t['date'])

        # Find the largest cluster within the window
        best_cluster = []
        for i, buy in enumerate(buys_sorted):
            cluster = [buy]
            window_end = buy['date'] + timedelta(days=self.cluster_window_days)
            for j in range(i + 1, len(buys_sorted)):
                if buys_sorted[j]['date'] <= window_end:
                    # Only count unique insiders
                    existing_names = {b['owner_name'] for b in cluster}
                    if buys_sorted[j]['owner_name'] not in existing_names:
                        cluster.append(buys_sorted[j])
                else:
                    break
            if len(cluster) > len(best_cluster):
                best_cluster = cluster

        unique_buyers = list({b['owner_name'] for b in best_cluster})

        return {
            'cluster_detected': len(unique_buyers) >= CLUSTER_MODERATE_MIN,
            'cluster_size': len(unique_buyers),
            'cluster_buyers': [
                {'name': b['owner_name'], 'role': b['owner_role']}
                for b in best_cluster
            ],
        }

    def _calculate_score(
        self,
        transactions: List[Dict],
        cluster_info: Dict,
        price_near_dip: bool = False,
    ) -> float:
        """
        Calculate the insider signal score (0-100).

        Args:
            transactions: List of parsed transaction dicts
            cluster_info: Cluster detection results
            price_near_dip: Whether current price is >10% off 52wk high

        Returns:
            Score between 0 and 100
        """
        if not transactions:
            return 0.0

        score = 0.0

        # Score each buy transaction
        buys = [t for t in transactions if t.get('direction') == 'buy']
        sells = [t for t in transactions if t.get('direction') == 'sell']

        for buy in buys:
            role_w = _get_role_weight(buy.get('owner_role', ''))
            size_w = _get_size_weight(buy.get('value', 0))
            # Each buy contributes up to ~10 points, scaled by weights
            score += 10.0 * role_w * size_w

        # Penalize for sells (less weight)
        for sell in sells:
            role_w = _get_role_weight(sell.get('owner_role', ''))
            size_w = _get_size_weight(sell.get('value', 0))
            score -= 5.0 * role_w * size_w

        # Cluster bonus
        cluster_size = cluster_info.get('cluster_size', 0)
        if cluster_size >= CLUSTER_STRONG_MIN:
            score += CLUSTER_STRONG_BONUS
        elif cluster_size >= CLUSTER_MODERATE_MIN:
            score += CLUSTER_MODERATE_BONUS

        # Price dip bonus
        if price_near_dip and buys:
            score += PRICE_DIP_BONUS

        # Clamp to 0-100
        return round(max(0.0, min(100.0, score)), 2)

    def _determine_direction_signal(
        self, transactions: List[Dict], score: float
    ) -> str:
        """
        Determine overall signal direction.

        Args:
            transactions: Parsed transactions
            score: Calculated signal score

        Returns:
            'bullish', 'bearish', or 'neutral'
        """
        total_buy_value = sum(
            t.get('value', 0) for t in transactions if t.get('direction') == 'buy'
        )
        total_sell_value = sum(
            t.get('value', 0) for t in transactions if t.get('direction') == 'sell'
        )

        if score >= 30 and total_buy_value > total_sell_value:
            return 'bullish'
        if total_sell_value > total_buy_value * 2 and score < 20:
            return 'bearish'
        return 'neutral'

    def _check_price_dip(self, ticker: str) -> bool:
        """
        Check if the stock is trading >10% below its 52-week high.
        Uses yfinance if available, otherwise returns False.

        Args:
            ticker: Stock ticker symbol

        Returns:
            True if price is in a dip
        """
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)
            info = stock.info
            current = info.get('currentPrice') or info.get('regularMarketPrice', 0)
            high_52w = info.get('fiftyTwoWeekHigh', 0)
            if current and high_52w and high_52w > 0:
                pct_off = (high_52w - current) / high_52w
                return pct_off >= self.price_dip_threshold
        except (ImportError, KeyError, TypeError, ValueError, ConnectionError):
            pass
        return False

    def analyze_stock(self, ticker: str) -> Dict:
        """
        Analyze insider trading activity for a single stock.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dict with insider signal score, direction, transactions, and metadata
        """
        edgar_mod, err = _check_edgartools_available()
        if edgar_mod is None:
            logger.warning(err)
            return _neutral_result(error=err)

        logger.info(f"Analyzing insider activity for {ticker}")

        # Fetch Form 4 filings
        transactions = self._fetch_form4_filings(ticker)

        if not transactions:
            logger.info(f"No insider transactions found for {ticker}")
            return _neutral_result()

        # Detect clusters
        cluster_info = self._detect_clusters(transactions)

        # Check price dip
        price_near_dip = self._check_price_dip(ticker)

        # Calculate score
        score = self._calculate_score(transactions, cluster_info, price_near_dip)

        # Determine direction
        direction = self._determine_direction_signal(transactions, score)

        # Aggregate values
        total_buy_value = sum(
            t.get('value', 0) for t in transactions if t.get('direction') == 'buy'
        )
        total_sell_value = sum(
            t.get('value', 0) for t in transactions if t.get('direction') == 'sell'
        )

        # Net direction
        if total_buy_value > total_sell_value:
            net_direction = 'net_buying'
        elif total_sell_value > total_buy_value:
            net_direction = 'net_selling'
        else:
            net_direction = 'neutral'

        # Notable buyers: significant buys by named insiders
        notable_buyers = []
        seen_names = set()
        for t in transactions:
            if t.get('direction') == 'buy' and t.get('value', 0) >= 50_000:
                name = t.get('owner_name', 'Unknown')
                if name not in seen_names:
                    notable_buyers.append({
                        'name': name,
                        'role': t.get('owner_role', 'Unknown'),
                        'value': t.get('value', 0),
                    })
                    seen_names.add(name)

        # Sort transactions for output (most recent first)
        sorted_txns = sorted(
            transactions,
            key=lambda t: t.get('date') or datetime.min,
            reverse=True,
        )

        # Serialize dates for JSON compatibility
        for t in sorted_txns:
            if isinstance(t.get('date'), datetime):
                t['date'] = t['date'].strftime('%Y-%m-%d')

        return {
            'insider_signal_score': score,
            'insider_signal_direction': direction,
            'insider_transactions': sorted_txns,
            'insider_cluster_detected': cluster_info['cluster_detected'],
            'insider_cluster_size': cluster_info['cluster_size'],
            'insider_total_buy_value': round(total_buy_value, 2),
            'insider_total_sell_value': round(total_sell_value, 2),
            'insider_net_direction': net_direction,
            'insider_notable_buyers': notable_buyers,
        }

    def analyze_batch(self, tickers: List[str]) -> Dict[str, Dict]:
        """
        Analyze insider trading activity for multiple stocks with rate limiting.

        Args:
            tickers: List of stock ticker symbols

        Returns:
            Dict mapping ticker -> insider signal result
        """
        results = {}
        for i, ticker in enumerate(tickers):
            try:
                results[ticker] = self.analyze_stock(ticker)
            except (ConnectionError, TimeoutError, OSError) as e:
                logger.error(f"Network error analyzing {ticker}: {e}")
                results[ticker] = _neutral_result(error=str(e))
            except (ValueError, TypeError, KeyError, AttributeError) as e:
                logger.error(f"Error analyzing {ticker}: {e}")
                results[ticker] = _neutral_result(error=str(e))

            # Extra delay between tickers to be polite to SEC
            if i < len(tickers) - 1:
                time.sleep(0.5)

        logger.info(f"Analyzed insider activity for {len(results)}/{len(tickers)} tickers")
        return results
